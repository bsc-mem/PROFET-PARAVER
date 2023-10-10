import os
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

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
    mask = np.ones(len(df), dtype=bool)
    if node_name is not None:
        mask &= df['node_name'] == node_name
    if i_socket is not None:
        mask &= df['socket'] == int(i_socket)
    if i_mc is not None:
        mask &= df['mc'] == int(i_mc)
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

def get_roofline_markers_dots_fig(df, x_data, y_data, color, stress_score_scale=None, opacity=0.01):
    if color == 'stress_score':
        dots_fig = go.Scatter(x=x_data, y=y_data, mode='markers', showlegend=False, marker=dict(
                size=5,
                opacity=opacity, 
                color=df['stress_score'], 
                colorscale=stress_score_scale['colorscale'],
                colorbar=dict(
                    title='Stress score',
                ),
                cmin=stress_score_scale['min'],
                cmax=stress_score_scale['max'],
            ),
            xaxis='x', 
            yaxis='y',
            name='Data',
            hovertemplate='<b>Stress score</b>: %{marker.color:.2f}<br><b>Operational Intensity</b>: %{x:.2f} (FLOPS/Byte)<br><b>Performance</b>: %{y:.2f} (GFLOPS/s)<br><b>Bandwidth</b>: %{customdata[3]:.2f} GB/s<br><b>Latency</b>: %{customdata[4]:.2f} ns<br><b>Timestamp</b>: %{text}<br><b>Node</b>: %{customdata[0]}<br><b>Socket</b>: %{customdata[1]}<br><b>MC</b>: %{customdata[2]}<extra></extra>', customdata=df[['node_name', 'socket', 'mc', 'bw', 'lat', 'stress_score']], text=df['timestamp'])
    else:
        dots_fig = go.Scatter(x=x_data, y=y_data, mode='markers', showlegend=False, marker=dict(size=5, opacity=opacity, color=color), 
                            xaxis='x', 
                            yaxis='y',
                              hovertemplate='<b>Operational Intensity</b>: %{x:.2f} (FLOPS/Byte)<br><b>Performance</b>: %{y:.2f} (GFLOPS/s)<br><b>Bandwidth</b>: %{customdata[3]:.2f} GB/s<br><b>Latency</b>: %{customdata[4]:.2f} ns<br><b>Timestamp</b>: %{text}<br><b>Node</b>: %{customdata[0]}<br><b>Socket</b>: %{customdata[1]}<br><b>MC</b>: %{customdata[2]}<extra></extra>', customdata=df[['node_name', 'socket', 'mc', 'bw', 'lat']], text=df['timestamp'] )

    return dots_fig

def get_peak_bandwidth(curves):
    # Maximum bandwidth of all curves
    peak_bandwidth = 0
    for w_ratio in curves:
        peak_bandwidth = max(peak_bandwidth, max(curves[w_ratio]['bandwidths']))
    return peak_bandwidth

def get_cache_bandwidth(curves):
    #TODO: How to get cache bandwidth? Which values should we use?
    return [
        {
            'level': 'L1',
            'value': 1286.4,
            'unit': '1.28 TB/s'
        },
        {
            'level': 'L2',
            'value': 864,
            'unit': '864 GB/s'
        },
        {
            'level': 'L3',
            'value': 536.8,
            'unit': '536.8 GB/s'
        },
        {
            'level': 'DRAM',
            'value': 115.5,
            'unit': '115.5 GB/s'
        },
    ]
