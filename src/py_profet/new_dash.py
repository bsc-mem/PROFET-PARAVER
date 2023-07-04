'''
Copyright (C) 2023 Isaac Boixaderas - All Rights Reserved
You may use, distribute and modify this code under the
terms of the BSD-3 license.

You should have received a copy of the BSD-3 license with
this file. If not, please visit: https://opensource.org/licenses/BSD-3-Clause
'''

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np
import pandas as pd
import os
import argparse
from collections import defaultdict
from dash import Dash, dcc, html, Input, Output
import matplotlib.pyplot as plt
import dash_daq as daq
import dash_bootstrap_components as dbc

import layouts


# define a custom continuous color scale for stress score
stress_score_min, stress_score_max = 0, 1
stress_score_scale = [
    (0.0, 'green'),
    (0.5, 'yellow'),
    (1.0, 'red'),
]


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-tf', '--trace-file', dest='trace_file',
                        default='', help='Trace file path.')
    parser.add_argument('--bw-lat-curves-dir', dest='curves_path',
                        default='', help='Directory of the bandwidth-latency curves.')
    parser.add_argument('-e', '--excluded-original', dest='excluded_original',
                        action='store_true', help='If original trace data is excluded from the given trace file.')
    parser.add_argument('-p', '--precision', dest='precision',
                        default=None, type=int, help='Decimal precision of the .prv file.')
    parser.add_argument('--cpufreq', dest='cpu_freq',
                        default=None, type=float, help='CPU frequency in GHz.')
    parser.add_argument('--pdf', dest='plot_pdf',
                        action='store_true', help='If plot (store) pdf with curves and memory stress.')
    parser.add_argument('--save-feather', dest='save_feather',
                        action='store_true', help='Save processed .prv data to a .feather file.')
    
    return parser.parse_args()


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


def prv_to_df(trace_file_path, row_file_path, precision, excluded_original, save_feather=False):
    node_names = get_node_names(row_file_path)

    df = []
    metric_keys = ['wr', 'bw', 'max_bw', 'lat', 'min_lat', 'max_lat', 'stress_score']
    with open(trace_file_path) as f:
        first_line = True
        # all_lines = f.readlines()
        # do not read all lines at once, read them line by line to save memory
        for i, line in enumerate(f):
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
                metric_key = metric_keys[last_metric_digit - 1]
                val = float(sp[i+1].strip())

                # negative values are set for identifying irregular data, include all of them for now and remove whole negative rows later (see next lines)
                if val != -1:
                    # apply precision of the prv file.
                    # if it is negative but different than -1, apply precision as well, as
                    # we stored the calculated metric as a negative number for identifying it as an error or an irregularity.
                    val = float(val / 10**precision)
                row[metric_key] = val

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


def get_color_bar_update(toggled_time, labels):
    if toggled_time:
        return {
            'colorbar': {'title': labels['timestamp'],},
            'colorscale': 'burg',
        }
    return {
        'colorbar': {'title': labels['stress_score'],},
        'colorscale': stress_score_scale,
        'cmin': stress_score_min,
        'cmax': stress_score_max,
    }


def get_dash_app(df, node_names: list, num_sockets_per_node: int, num_mc_per_socket: int = None, is_undersampled: bool = False):
    app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
    app.layout = layouts.get_layout(df, node_names, num_sockets_per_node, num_mc_per_socket, is_undersampled)
    return app


def get_curves_fig(curves, fig):
    curve_opacity_step = 0.1666
    for i, w_ratio in enumerate(range(0, 51, 10)):
        curve_fig = px.line(x=curves[w_ratio]['bandwidths'], y=curves[w_ratio]['latencies'])
        curve_fig.update_traces(opacity=1-curve_opacity_step*i)
        fig.add_trace(curve_fig.data[0])
        fig.add_annotation(x=curves[w_ratio]['bandwidths'][-1], y=curves[w_ratio]['latencies'][-1] + 15,
                            text=f"{w_ratio}%", showarrow=False, arrowhead=1)
    return fig


def get_application_memory_dots_fig(df, node_name=None, i_socket=None, time_range=(), bw_range=(), lat_range=(), opacity=0.01):
    mask = [True] * len(df)
    if node_name is not None:
        mask &= df['node_name'] == node_name
    if i_socket is not None:
        mask &= df['socket'] == int(i_socket)
    # if mc != '-' and mc != 'All':
    #     mask &= df['mc'] == int(mc)
    if len(time_range):
        mask &= (df['timestamp'] >= time_range[0]) & (df['timestamp'] < time_range[1])
    if len(bw_range):
        mask &= (df['bw'] >= bw_range[0]) & (df['bw'] < bw_range[1])
    if len(lat_range):
        mask &= (df['lat'] >= lat_range[0]) & (df['lat'] < lat_range[1])

    # if show_time:
        # use rainbow color map
        # import matplotlib as mpl
        # import matplotlib.colors as mcolors
        # cmap = mpl.colormaps['rainbow']
        # color_list = [mcolors.rgb2hex(cmap(i)) for i in range(cmap.N)]
        # print(color_list)
        # dots_fig = px.scatter(df[mask], x='bw', y='lat', color='timestamp', color_discrete_map=color_list)
        # dots_fig = px.scatter(df[mask], x='bw', y='lat', color='timestamp')
    # else:
    dots_fig = px.scatter(df[mask], x='bw', y='lat', color='stress_score', color_continuous_scale=stress_score_scale)

    marker_opts = dict(size=10, opacity=opacity)
    dots_fig.update_traces(marker=marker_opts)
    return dots_fig



if __name__ == '__main__':
    # read and process arguments
    args = parse_args()
    labels = {'bw': 'Bandwidth (GB/s)', 'lat': 'Latency (ns)', 'timestamp': 'Timestamp (ns)', 'stress_score': 'Stress score'}

    # load and process trace
    # trace_file = '../prv_profet_visualizations/traces/petar_workshop/xhpcg.mpich-x86-64_10ms.chop1.profet.prv'
    current_dir = os.path.dirname(os.path.realpath(__file__))
    # store_df_path = os.path.join(current_dir, 'dash_traces/')
    # TODO replace only the extension! .prv could be included in the middle of the file as a name
    # do it for all other cases (e.g. .pdf below)
    row_file_path = args.trace_file.replace('.prv', '.row')
    if args.trace_file.endswith('.prv'):
        df = prv_to_df(args.trace_file, row_file_path, args.precision, args.excluded_original, args.save_feather)
    elif args.trace_file.endswith('.feather'):
        df = pd.read_feather(args.trace_file)
    else:
        raise Exception(f'Unkown trace file extension ({args.trace_file.split(".")[-1]}) from {args.trace_file}.')
    
    node_names = sorted(df['node_name'].unique())
    num_nodes =  len(node_names)
    num_sockets_per_node = df.groupby(['node_name', 'socket']).ngroups // num_nodes
    
    # allow a maximum of elements to display. Randomly undersample if there are more elements than the limit
    max_elements = 2000
    is_undersampled = False
    if len(df) > max_elements:
        # TODO make each socket have the same number of elements
        df = df.sample(max_elements)
        is_undersampled = True

    # load and process curves
    curves = get_curves(args.curves_path, args.cpu_freq)
    # get color bar update options
    color_bar_update = get_color_bar_update(toggled_time=False, labels=labels)

    # save a pdf file with a default chart
    if args.plot_pdf:
        store_pdf_path = os.path.dirname(os.path.abspath(args.trace_file))
        if args.trace_file.endswith('.prv'):
            pdf_filename = os.path.basename(os.path.abspath(args.trace_file)).replace('.prv', '.pdf')
        elif args.trace_file.endswith('.feather'):
            pdf_filename = os.path.basename(os.path.abspath(args.trace_file)).replace('.feather', '.pdf')
        else:
            raise Exception(f'Unkown trace file extension ({args.trace_file.split(".")[-1]}) from {args.trace_file}.')
        store_pdf_file_path = os.path.join(store_pdf_path, pdf_filename)
        default_fig = make_subplots(rows=1, cols=1)
        default_fig = get_curves_fig(curves, default_fig)
        # get application plot memory dots with default options
        dots_fig = get_application_memory_dots_fig(df)
        default_fig.add_trace(dots_fig.data[0])
        default_fig.update_xaxes(title=labels['bw'])
        default_fig.update_yaxes(title=labels['lat'])
        default_fig.update_coloraxes(**color_bar_update)
        default_fig.write_image(store_pdf_file_path)
        print('PDF chart file:', store_pdf_file_path)
        print()

    app = get_dash_app(df, node_names, num_sockets_per_node, num_mc_per_socket=None, is_undersampled=is_undersampled)

    @app.callback(
        Output('graph-container', 'children'),
        # Output("scatter-plot", "figure"),
        # Input('graph-container', 'id'),
        Input('toggle-curves', 'value'),
        # Input('toggle-time', 'value'),
        # Input('dropdown-node', 'value'),
        # Input('dropdown-socket', 'value'),
        # Input('dropdown-mc', 'value'),
        Input("range-slider-time", "value"),
        Input("range-slider-bw", "value"),
        Input("range-slider-lat", "value"),
        Input("slider-opacity", "value"))
    def update_chart(toggled_curves, slider_range_time, slider_range_bw, slider_range_lat, slider_opacity):
        # Warning: this function must exactly match the layout defined for the graph-container,
        # including text, the order of the inputs, etc.
        updated_graph_rows = []

        if is_undersampled:
            # add warning text
            updated_graph_rows.append(dbc.Row([
                html.H5('Warning: Data is undersampled to 2000 elements.', style={"color": "red"}),
                html.Br(),
                html.Br(),
                html.Br(),
            ]))

        for node_name in node_names:
            updated_graph_cols = []
            for i_socket in range(1, num_sockets_per_node + 1):
                fig = make_subplots(rows=1, cols=1)

                if toggled_curves:
                    # plot curves
                    fig = get_curves_fig(curves, fig)

                # plot application bw-lat dots
                dots_fig = get_application_memory_dots_fig(df, node_name, i_socket, slider_range_time, 
                                                           slider_range_bw, slider_range_lat, slider_opacity)
                fig.add_trace(dots_fig.data[0])

                # labels = {'bw': 'Bandwidth (GB/s)', 'lat': 'Latency (ns)', 'timestamp': 'Timestamp (ns)'}
                fig.update_xaxes(title=labels['bw'])
                fig.update_yaxes(title=labels['lat'])
                # color_bar_update = get_color_bar_update(toggled_time, labels)
                fig.update_coloraxes(**color_bar_update)

                # update graph
                graph_id = f"node-{node_name}-socket-{i_socket}"
                col = dbc.Col([
                    html.H4(f'Node {node_name} - Socket {i_socket}'),
                    dcc.Graph(id=graph_id, figure=fig)
                ], sm=12, md=6)
                updated_graph_cols.append(col)
            updated_graph_rows.append(dbc.Row(updated_graph_cols))
        return updated_graph_rows

    app.run_server(debug=True)
