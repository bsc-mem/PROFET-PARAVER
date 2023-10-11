'''
Copyright (C) 2023 Isaac Boixaderas - All Rights Reserved
You may use, distribute and modify this code under the
terms of the BSD-3 license.

You should have received a copy of the BSD-3 license with
this file. If not, please visit: https://opensource.org/licenses/BSD-3-Clause
'''

from plotly.subplots import make_subplots
import pandas as pd
import os
import argparse
import json
from collections import defaultdict
from dash import Dash
import dash_bootstrap_components as dbc
from callbacks import register_callbacks
import numpy as np
import layouts
import utils
import curve_utils

# define a custom continuous color scale for stress score
stress_score_config = {
    'min': 0,
    'max': 1,
    'colorscale': [
        (0.0, 'green'),
        (0.5, 'yellow'),
        (1.0, 'red'),
    ],
}

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(dest='trace_file', default='', help='Trace file path.')
    parser.add_argument(dest='curves_path', default='', help='Directory of the bandwidth-latency curves.')
    parser.add_argument(dest='config_file', default=None, help='Configuration JSON file path.')
    parser.add_argument('-e', '--excluded-original', dest='excluded_original',
                        action='store_true', help='If original trace data is excluded from the given trace file.')
    parser.add_argument('--pdf', dest='plot_pdf',
                        action='store_true', help='If plot (store) pdf with curves and memory stress.')
    parser.add_argument('--save-feather', dest='save_feather',
                        action='store_true', help='Save processed .prv data to a .feather file.')
    
    return parser.parse_args()

def get_config(config_file_path: str):
    with open(config_file_path, 'r') as f:
        config = json.load(f)
    return config

def get_dash_app(df, config_json: dict, system_arch: dict, max_elements: int):
    app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
    app.layout = layouts.get_layout(df, config_json, system_arch, max_elements)
    return app

def save_pdf(trace_file: str):
    store_pdf_path = os.path.dirname(os.path.abspath(trace_file))
    if trace_file.endswith('.prv'):
        pdf_filename = os.path.basename(os.path.abspath(trace_file)).replace('.prv', '.pdf')
    elif trace_file.endswith('.feather'):
        pdf_filename = os.path.basename(os.path.abspath(trace_file)).replace('.feather', '.pdf')
    else:
        raise Exception(f'Unkown trace file extension ({trace_file.split(".")[-1]}) from {trace_file}.')
    store_pdf_file_path = os.path.join(store_pdf_path, pdf_filename)
    default_fig = make_subplots(rows=1, cols=1)
    default_fig = curve_utils.get_curves_fig(curves, default_fig)
    # get application plot memory dots with default options
    dots_fig = utils.get_application_memory_dots_fig(df, stress_score_config['colorscale'])
    default_fig.add_trace(dots_fig.data[0])
    default_fig.update_xaxes(title=labels['bw'])
    default_fig.update_yaxes(title=labels['lat'])
    color_bar = utils.get_color_bar(labels, stress_score_config)
    default_fig.update_coloraxes(**color_bar)
    default_fig.write_image(store_pdf_file_path)
    print('PDF chart file:', store_pdf_file_path)
    print()

if __name__ == '__main__':
    # read and process arguments
    args = parse_args()
    labels = {'bw': 'Bandwidth (GB/s)', 'lat': 'Latency (ns)',
              'timestamp': 'Timestamp (ns)', 'stress_score': 'Stress score'}
    config_json = get_config(args.config_file)

    # load and process trace
    # trace_file = '../prv_profet_visualizations/traces/petar_workshop/xhpcg.mpich-x86-64_10ms.chop1.profet.prv'
    current_dir = os.path.dirname(os.path.realpath(__file__))
    # store_df_path = os.path.join(current_dir, 'dash_traces/')
    # TODO replace only the extension! .prv could be included in the middle of the file as a name
    # do it for all other cases (e.g. .pdf below)
    row_file_path = args.trace_file.replace('.prv', '.row')
    if args.trace_file.endswith('.prv'):
        df = utils.prv_to_df(args.trace_file, row_file_path, config_json, args.excluded_original, args.save_feather)
    elif args.trace_file.endswith('.feather'):
        df = pd.read_feather(args.trace_file)
    else:
        raise Exception(f'Unkown trace file extension ({args.trace_file.split(".")[-1]}) from {args.trace_file}.')
    
    # get system architecture (nodes, sockets per node, mcs per socket) in a dict form
    grouped = df.groupby(['node_name', 'socket'])['mc'].unique()
    system_arch = defaultdict(dict)
    for (a, b), unique_c in grouped.items():
        system_arch[a][b] = sorted(unique_c.tolist())
    # print(dict(system_arch))
    
    # allow a maximum of elements to display. Randomly undersample if there are more elements than the limit
    '''
    # Ordering by timestamp after undersampling
    max_elements = 10000
    if len(df) > max_elements:
        df = df.sort_values(by='stress_score')
        k = len(df) // max_elements
        indices_to_select = np.arange(0, len(df), k)

        sampled_df = df.iloc[indices_to_select].copy()
        sampled_df = sampled_df.append(df.nsmallest(3, 'stress_score'))
        sampled_df = sampled_df.append(df.nlargest(3, 'stress_score'))
        df = sampled_df
        df = df.sort_values(by='timestamp')
    else:
        max_elements = None
    '''

    max_elements = 10000
    # TODO make each socket have the same number of elements
    if len(df) > max_elements:
        total_sockets = 0
        for node_name, sockets in system_arch.items():
            total_sockets += len(sockets)
        data_points = max_elements // total_sockets

        sampled_data = pd.DataFrame()

        for node_name, sockets in system_arch.items():
            for socket in sockets:
                node_socket_data = df[(df['node_name'] == node_name) & (df['socket'] == socket)]

                if len(node_socket_data) >= data_points:
                    stress_scores = node_socket_data['stress_score'].sort_values()
                    k = len(stress_scores) // data_points
                    indices_to_select = np.arange(0, len(stress_scores), k)
                    sampled_node_socket_data = node_socket_data.iloc[indices_to_select]
                else:
                    sampled_node_socket_data = node_socket_data

                sampled_data = sampled_data._append(sampled_node_socket_data)

        df = sampled_data
    else:
        max_elements = None

    # load and process curves
    curves = curve_utils.get_curves(args.curves_path, config_json['cpu_freq'])

    # save a pdf file with a default chart
    if args.plot_pdf:
        save_pdf(args.trace_file)

    app = get_dash_app(df, config_json, system_arch, max_elements)
    register_callbacks(app, df, curves, config_json, system_arch, args.trace_file, labels, stress_score_config, max_elements)
    app.run_server(debug=False)
    #app.run_server(debug=True)
