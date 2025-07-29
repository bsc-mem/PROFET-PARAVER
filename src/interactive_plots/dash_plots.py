"""
Copyright (C) 2023 Isaac Boixaderas - All Rights Reserved
You may use, distribute and modify this code under the
terms of the BSD-3 license.

You should have received a copy of the BSD-3 license with
this file. If not, please visit: https://opensource.org/licenses/BSD-3-Clause
"""

import argparse
import json
import os
import inspect, os, sys, pathlib, platform
from collections import defaultdict

import socket


def _add_private_wheels():
    arch = (
        "python_libs_x86_64" if platform.machine() == "x86_64" else "python_libs_arm64"
    )
    script_dir = pathlib.Path(__file__).resolve().parent
    base_dir = script_dir.parent.parent
    wheel = base_dir / "bin" / arch
    if wheel.is_dir():
        sys.path.insert(0, str(wheel))


_add_private_wheels()

import curve_utils
import dash_bootstrap_components as dbc
import layouts
import numpy as np
import pandas as pd
import utils
from callbacks import register_callbacks
from dash import Dash
from plotly.subplots import make_subplots

# Define a custom continuous color scale for stress score
stress_score_config = {
    "min": 0,
    "max": 1,
    "colorscale": [
        (0.0, "green"),
        (0.5, "yellow"),
        (1.0, "red"),
    ],
}


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(dest="trace_file", default="", help="Trace file path.")
    parser.add_argument(
        dest="curves_path",
        default="",
        help="Directory of the bandwidth-latency curves.",
    )
    parser.add_argument(
        dest="config_file", default=None, help="Configuration JSON file path."
    )
    parser.add_argument(
        "-k",
        "--keep-original",
        dest="keep_original",
        action="store_true",
        help="If original trace data is kept from the given trace file.",
    )
    parser.add_argument(
        "--pdf",
        dest="plot_pdf",
        action="store_true",
        help="If plot (store) pdf with curves and memory stress.",
    )
    parser.add_argument(
        "--save-feather",
        dest="save_feather",
        action="store_true",
        help="Save processed .prv data to a .feather file.",
    )

    parser.add_argument(
        "-e",
        "--expert",
        dest="expert",
        action="store_true",
        help="If expert mode is enabled.",
    )

    return parser.parse_args()


def get_config(config_file_path: str):
    with open(config_file_path, "r") as f:
        config = json.load(f)
    return config


def find_free_port(start_port=8050, max_port=8100):
    """
    Try binding to ports [start_port, start_port+1, ..., max_port].
    Return the first port that isn’t in use. Raise RuntimeError if none free.
    """
    for port in range(start_port, max_port + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            # SO_REUSEADDR lets us rebind in TIME_WAIT, but the main check is if bind() fails
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
                # If bind succeeds, that port is free. Close and return it.
                return port
            except OSError:
                # Port is in use, try the next one
                continue

    raise RuntimeError(f"No free ports in range {start_port}–{max_port}.")


def get_dash_app(
    df, config_json: dict, system_arch: dict, max_elements: int, expert: bool
):
    app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], title="Mess")
    app.layout = layouts.get_layout(df, config_json, system_arch, max_elements, expert)
    return app


def save_pdf(trace_file: str):
    store_pdf_path = os.path.dirname(os.path.abspath(trace_file))
    if trace_file.endswith(".prv"):
        pdf_filename = os.path.basename(os.path.abspath(trace_file)).replace(
            ".prv", ".pdf"
        )
    elif trace_file.endswith(".feather"):
        pdf_filename = os.path.basename(os.path.abspath(trace_file)).replace(
            ".feather", ".pdf"
        )
    else:
        raise Exception(
            f'Unkown trace file extension ({trace_file.split(".")[-1]}) from {trace_file}.'
        )
    store_pdf_file_path = os.path.join(store_pdf_path, pdf_filename)
    default_fig = make_subplots(rows=1, cols=1)
    default_fig = curve_utils.get_curves_fig(curves, default_fig)
    # Get application plot memory dots with default options
    dots_fig = utils.get_application_memory_dots_fig(
        df, stress_score_config["colorscale"]
    )
    default_fig.add_trace(dots_fig.data[0])
    default_fig.update_xaxes(title=labels["bw"])
    default_fig.update_yaxes(title=labels["lat"])
    color_bar = utils.get_color_bar(labels, stress_score_config)
    default_fig.update_coloraxes(**color_bar)
    default_fig.write_image(store_pdf_file_path)
    print("PDF chart file:", store_pdf_file_path)
    print()


if __name__ == "__main__":
    # Read and process arguments
    args = parse_args()
    labels = {
        "bw": "Bandwidth (GB/s)",
        "lat": "Latency (ns)",
        "timestamp": "Timestamp (ns)",
        "stress_score": "Stress score",
    }
    config_json = get_config(args.config_file)

    # Load and process trace
    # trace_file = '../prv_profet_visualizations/traces/petar_workshop/xhpcg.mpich-x86-64_10ms.chop1.profet.prv'
    current_dir = os.path.dirname(os.path.realpath(__file__))
    # store_df_path = os.path.join(current_dir, 'dash_traces/')
    # TODO replace only the extension! .prv could be included in the middle of the file as a name
    # Do it for all other cases (e.g. .pdf below)
    row_file_path = args.trace_file.replace(".prv", ".row")

    if args.trace_file.endswith(".prv"):
        df = utils.prv_to_df(
            args.trace_file,
            row_file_path,
            config_json,
            args.keep_original,
            args.save_feather,
        )
    elif args.trace_file.endswith(".feather"):
        df = pd.read_feather(args.trace_file)
    else:
        raise Exception(
            f'Unkown trace file extension ({args.trace_file.split(".")[-1]}) from {args.trace_file}.'
        )

    # Get system architecture (nodes, sockets per node, mcs per socket) in a dict form
    grouped = df.groupby(["node_name", "socket"])["mc"].unique()
    system_arch = defaultdict(dict)
    for (a, b), unique_c in grouped.items():
        system_arch[a][b] = sorted(unique_c.tolist())

    # Print all node names:
    # Allow a maximum of elements to display. Randomly undersample if there are more elements than the limit

    # Reset index to avoid problems with the sampling
    df = df.reset_index(drop=True)

    # Save a copy of the original dataframe
    df_overview = df.copy()

    max_elements = 10000
    # Check if the length of the DataFrame exceeds the maximum limit
    if len(df) > max_elements:
        total_sockets = 0

        # Calculate the total number of sockets in the system architecture
        for node_name, sockets in system_arch.items():
            total_sockets += len(sockets)

        # Calculate the desired number of data points per socket
        data_points = max_elements // total_sockets

        sampled_node_socket_indices = []

        for node_name, sockets in system_arch.items():
            for s in sockets:
                # Sort stress scores to select representative data points
                node_socket_data = df[
                    (df["node_name"] == node_name) & (df["socket"] == s)
                ]

                # Check if there are enough data points to sample
                if len(node_socket_data) >= data_points:
                    stress_scores = node_socket_data["stress_score"].sort_values()

                    # Calculate 'k' as the ceiling of the ratio of the total data points to the desired data points per socket, ensuring at least one data point is sampled.
                    # ensuring at least one data point is sampled.
                    k = max((len(stress_scores) + data_points - 1) // data_points, 1)

                    # Select indices for sampling
                    indices_to_select = np.arange(0, len(stress_scores), k)
                    sampled_indices = node_socket_data.iloc[indices_to_select].index

                    # Extend the list of sampled indices
                    sampled_node_socket_indices.extend(sampled_indices)
                else:
                    # If there are not enough data points, include all available indices
                    sampled_node_socket_indices.extend(node_socket_data.index)

        # Update the DataFrame with the sampled indices
        df = df.loc[sampled_node_socket_indices]
    else:
        max_elements = None

    # Load and process curves
    curves = curve_utils.get_curves(args.curves_path, config_json["cpu_freq"])
    # Save a pdf file with a default chart
    if args.plot_pdf:
        save_pdf(args.trace_file)

    # TODO: If the expert argument changes change it here.
    app = get_dash_app(df, config_json, system_arch, max_elements, args.expert)
    register_callbacks(
        app,
        df,
        df_overview,
        curves,
        config_json,
        system_arch,
        args.trace_file,
        labels,
        stress_score_config,
        max_elements,
        args.expert,
    )
    try:
        port_to_use = find_free_port(start_port=8050, max_port=8100)
    except RuntimeError as e:
        print("ERROR:", e)
        exit(1)

    # ---- Run the app on that port ----
    print(f"Starting server on http://127.0.0.1:{port_to_use}/")
    app.run(host="127.0.0.1", port=port_to_use, debug=False, use_reloader=False)
    # app.run(debug=False)
    # app.run_server(debug=True)
