import numpy as np
import pandas as pd
from collections import defaultdict
import os
from plotly.subplots import make_subplots
import plotly.express as px

def get_node_names(row_file_path):
    # get the name of the nodes specified in the .row file
    node_counter = 0
    n_nodes = None
    node_names = []
    with open(row_file_path, 'r') as f:
        for l in f.readlines():
            if 'LEVEL APPL SIZE' in l:
                n_nodes = int(l.strip().split(' ')[-1])
                node_counter = 1
                continue
            if node_counter:
                node_names.append(l.strip())
                node_counter += 1
                if node_counter > n_nodes:
                    # all node names have been read
                    break
    return node_names

def prv_to_df(trace_file_path, row_file_path, config_json, excluded_original, save_feather=False):
    node_names = get_node_names(row_file_path)
    num_lines = sum(1 for _ in open(trace_file_path))

    rand_lines = []
    file_stats = os.stat(trace_file_path)
    file_mb = file_stats.st_size / (1024 ** 2)
    # directly undersample if file is big
    if file_mb > 100:
        # lines to undersample to have close to 100 MB
        undersample_n_lines = int((100 / file_mb) * num_lines)
        print(f'File size is {file_mb:.2f} MB, with {num_lines:,} lines. Undersampling to {10000/file_mb:.0f}% of original file.')
        # take random rows sample. Sort them in descending order to then process it using pop() for efficiency
        rand_lines = sorted(np.random.choice(num_lines, size=undersample_n_lines, replace=False), reverse=True)

    df = []
    metric_keys = ['wr', 'bw', 'max_bw', 'lat', 'min_lat', 'max_lat', 'stress_score']
    with open(trace_file_path) as f:
        first_line = True
        # all_lines = f.readlines()
        # do not read all lines at once, read them line by line to save memory
        for i, line in enumerate(f):
            if i % 100000 == 0:
                print(f'Loading is {i/num_lines*100:.2f}% complete.', end='\r')

            if len(rand_lines):
                if i == rand_lines[-1]:
                    rand_lines.pop()
                else:
                    # skip line if it is not in the random sample
                    continue

            if first_line or line.startswith('#') or line.startswith('c'):
                # skip header, comments and communicator lines
                first_line = False
                continue

            sp = line.split(':')
            row = defaultdict()
            row['node'] = int(sp[2])
            
            if not excluded_original and row['node'] == 1:
                # skip first application (original trace values) when it is excluded
                continue

            row['node_name'] = node_names[row['node'] - 1]
            row['socket'] = int(sp[3])
            row['mc'] = int(sp[4])
            row['timestamp'] = int(sp[5])

            # process subsequent metric IDs and values after the timestamp
            for i in range(6, len(sp)-1, 2):
                metric_id = int(sp[i])
                last_metric_digit = int(metric_id % 10)

                if last_metric_digit > len(metric_keys):
                    # we're over the desired metrics, no need to continue
                    break

                metric_key = metric_keys[last_metric_digit - 1]
                val = float(sp[i+1].strip())

                # negative values are set for identifying irregular data, include all of them for now and remove whole negative rows later (see next lines)
                if val != -1:
                    # apply precision of the prv file.
                    # if it is negative but different than -1, apply precision as well, as
                    # we stored the calculated metric as a negative number for identifying it as an error or an irregularity.
                    val = float(val / 10**config_json['precision'])
                row[metric_key] = val

                if metric_key == metric_keys[-1]:
                    # we've processed the last metric key we want, no need to continue (even if there are other events pending)
                    break

            df.append(row)
        df = pd.DataFrame(df)
        # perform a forward fill for copying above values of NaN (prvparser is purpously omitting equal consecutive values of a metric)
        df = df.ffill()
        # keep only rows with non-negative values, which means we logged erroneous or irregular data
        # also, keep NaN values for performing a forward-fill
        df = df[(pd.isnull(df[metric_keys]).any(axis=1)) | (df[metric_keys] >= 0).all(axis=1)].reset_index(drop=True)
        # calculate read ratio
        df['rr'] = 100 - df['wr']

        # TODO hard-coded drop 0s. Decide what to do with them in the output trace
        df = df[~((df['bw'] == 0) & (df['lat'] == 0))].reset_index(drop=True)

        if save_feather:
            trace_feather_path = trace_file_path.replace('.prv', '.feather')
            df.to_feather(trace_feather_path)

        return df

def get_color_bar(labels, stress_score_config):
    # if toggled_time:
    #     return {
    #         'colorbar': {'title': labels['timestamp'],},
    #         'colorscale': 'burg',
    #     }
    return {
        'colorbar': {'title': labels['stress_score'],},
        'colorscale': stress_score_config['colorscale'],
        'cmin': stress_score_config['min'],
        'cmax': stress_score_config['max'],
    }

def filter_df(df, node_name=None, i_socket=None, i_mc=None, time_range=(), bw_range=(), lat_range=()):
    mask = [True] * len(df)
    if node_name is not None:
        mask &= df['node_name'] == node_name
    if i_socket is not None:
        mask &= df['socket'] == int(i_socket)
    if i_mc is not None:
        mask &= df['mc'] == int(i_mc)
    # if mc != '-' and mc != 'All':
    #     mask &= df['mc'] == int(mc)
    if len(time_range):
        mask &= (df['timestamp'] >= time_range[0]*1e9) & (df['timestamp'] < time_range[1]*1e9)
    if len(bw_range):
        mask &= (df['bw'] >= bw_range[0]) & (df['bw'] < bw_range[1])
    if len(lat_range):
        mask &= (df['lat'] >= lat_range[0]) & (df['lat'] < lat_range[1])
    return df[mask]

def get_graph_fig(df, curves, curves_color, curves_transparency, markers_color, markers_transparency,
                  graph_title, x_title, y_title, stress_score_scale=None, color_bar=None):
    fig = make_subplots(rows=1, cols=1)
    # if curves_color != "none":
    fig = get_curves_fig(curves, fig, curves_color, curves_transparency)

    # plot application bw-lat dots
    dots_fig = get_application_memory_dots_fig(df, markers_color, stress_score_scale, markers_transparency)
    fig.add_trace(dots_fig.data[0])

    fig.update_xaxes(title=x_title)
    fig.update_yaxes(title=y_title)
    if color_bar is not None:
        fig.update_coloraxes(**color_bar)

    # update the layout with a title
    fig.update_layout(
        title={
            'text': graph_title,
            'font': {
                'size': 24,
                'color': 'black',
                'family': 'Arial, sans-serif',
            },
            'x':0.5,
            'xanchor': 'center'
        }
    )
    return fig

def get_curves(curves_path, cpu_freq):
    curves = {}
    # load and process curves
    for curve_file in os.listdir(curves_path):
    # for curve_file in os.listdir(curves_dir):
        if 'bwlat_' in curve_file:
            # with open( os.path.join(curves_dir, curve_file) ) as f:
            with open( os.path.join(curves_path, curve_file) ) as f:
                bws = []
                lats = []
                for line in f.readlines():
                    sp = line.split()
                    # bw MB/s to GB/s
                    bws.append(float(sp[0]) / 1000)
                    lats.append(float(sp[1]))
                # add special case of bw = 0 (then latency is the minimum recorded).
                # TODO it'd be better to use the Curve module instead of hardcoding a bw of 0 to the lowest latency (this behavior might change at some point)
                bws.append(0)
                lats.append(lats[-1])
                read_ratio = int(curve_file.split('_')[1].replace('.txt', ''))
                curves[100 - read_ratio] = {
                    'bandwidths': bws[::-1],
                    'latencies': np.array(lats[::-1]) / cpu_freq
                }
    return curves

def get_curves_fig(curves, fig, color='black', transparency=1):
    for i, w_ratio in enumerate(range(0, 51, 10)):
        curve_fig = px.line(x=curves[w_ratio]['bandwidths'], y=curves[w_ratio]['latencies'], color_discrete_sequence=[color])
        curve_opacity_step = transparency / len(range(0, 51, 10))
        curve_transparency = transparency - curve_opacity_step * i
        curve_fig.update_traces(opacity=max(0, curve_transparency))
        curve_text = f'{w_ratio}%' if curve_transparency > 0 else ''
        fig.add_trace(curve_fig.data[0])
        fig.add_annotation(x=curves[w_ratio]['bandwidths'][-1], y=curves[w_ratio]['latencies'][-1] + 15,
                            text=curve_text, showarrow=False, arrowhead=1)
    return fig

def get_application_memory_dots_fig(df, color, stress_score_scale=None, opacity=0.01):
    if color == 'stress_score':
        dots_fig = px.scatter(df, x='bw', y='lat', color='stress_score', color_continuous_scale=stress_score_scale)
    else:
        dots_fig = px.scatter(df, x='bw', y='lat', color_discrete_sequence=[color])

    marker_opts = dict(size=10, opacity=opacity)
    dots_fig.update_traces(marker=marker_opts)
    return dots_fig