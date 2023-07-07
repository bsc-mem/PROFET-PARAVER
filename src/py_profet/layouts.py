import pandas as pd
from dash import Dash, dcc, html, Input, Output
import dash_daq as daq
import dash_bootstrap_components as dbc


def get_sidebar(df: pd.DataFrame):
    # styling the sidebar
    style = {
        # "position": "fixed",
        "top": 0,
        "left": 0,
        "bottom": 0,
        # "width": "16rem",
        "padding": "2rem 1rem",
        "background-color": "#f8f9fa",
    }

    return html.Div([
        html.P("Show curves:"),
        daq.ToggleSwitch(
            id='toggle-curves',
            value=True
        ),
        html.Div(id='toggle-curves-output'),
        # html.P("Color time dimension:"),
        # daq.ToggleSwitch(
        #     id='toggle-time',
        #     value=False
        # ),
        # html.Div(id='dropdown-toggle-node'),
        # html.P("Node:"),
        # dcc.Dropdown(['All'] + sorted(list(df['node_name'].unique())),
        #             'All',
        #             id='dropdown-node'),
        # html.Div(id='dropdown-toggle-socket'),
        # html.P("Socket:"),
        # dcc.Dropdown(['All'] + sorted(list(df['socket'].unique())),
        #             'All',
        #             id='dropdown-socket'),
        # html.Div(id='dropdown-toggle-mc'),
        # html.P("Memory controller:"),
        # dcc.Dropdown(['All'] + sorted(list(df['mc'].unique())) if df['mc'].nunique() > 1 else ['-'],
        #             'All' if df['mc'].nunique() > 1 else '-',
        #             id='dropdown-mc'),
        html.Div(id='toggle-time-output'),
        html.P("Filter by timestamp:"),
        dcc.RangeSlider(
            id='range-slider-time',
            min=df['timestamp'].min(), max=df['timestamp'].max(), step=1000000,
            marks=None,
            value=[df['timestamp'].min(), df['timestamp'].max()]
        ),
        html.P("Filter by bandwidth:"),
        dcc.RangeSlider(
            id='range-slider-bw',
            min=df['bw'].min(), max=df['bw'].max(), step=1,
            marks=None,
            value=[df['bw'].min(), df['bw'].max()]
        ),
        html.P("Filter by latency:"),
        dcc.RangeSlider(
            id='range-slider-lat',
            min=df['lat'].min(), max=df['lat'].max(), step=1,
            marks=None,
            value=[df['lat'].min(), df['lat'].max()]
        ),
        html.P("Transparecy:"),
        dcc.Slider(0, 1, 0.01, value=0.1, id='slider-opacity'),
    ], style=style)


def get_main_content(node_names: list, num_sockets_per_node: int,
                     num_mc_per_socket: int = None, undersample: int = None):
    content_style = {
        "margin-left": "1rem",
        "margin-right": "2rem",
        "padding": "2rem 1rem",
    }

    tab_style = {
        "margin-top": "2rem",
    }

    system_info_tab = html.Div([
        html.H4('System Info'),
    ])

    chart_rows = []
    if undersample is not None:
        # add warning text
        chart_rows.append(dbc.Row([
            html.H5(f'Warning: Data is undersampled to {undersample:,} elements.', style={"color": "red"}),
            html.Br(),
            html.Br(),
            html.Br(),
        ]))

    for node_name in node_names:
        chart_cols = []
        for i_socket in range(num_sockets_per_node):
            if num_mc_per_socket is None:
                chart_cols.append(dbc.Col([
                    html.H4(f'Node {node_name} - Socket {i_socket}'),
                    dcc.Graph(id=f"node-{node_name}-socket-{i_socket}"),
                ], sm=12, md=6))
        chart_rows.append(dbc.Row(chart_cols))

    charts_tab = dbc.Container(chart_rows, id='graph-container', fluid=True)
    #     dbc.Row([
    #         dbc.Col([
    #             # html.H4('App\'s Bandwidth-Latency'),
    #             dcc.Graph(id="scatter-plot"),
    #             # dcc.Graph(id="scatter-plot", style={'width': '80%', 'height': '700px'}),
    #         ]),
    #         dbc.Col([
    #             dcc.Graph(id="scatter-plot2"),
    #         ]),
    #     ])
    # ])

    tabs = dbc.Tabs([
        dbc.Tab(system_info_tab, label="System Info", tab_id="system-tab", style=tab_style),
        dbc.Tab(charts_tab, label="Charts", tab_id="charts-tab", style=tab_style),
    ], id="tabs", active_tab="charts-tab")

    return html.Div([
        tabs,
    ], style=content_style)


def get_layout(df: pd.DataFrame, num_nodes: int, num_sockets_per_node: int,
               num_mc_per_socket: int = None, undersample: int = None):
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                get_sidebar(df),
            ], width=2),
            dbc.Col([
                get_main_content(num_nodes, num_sockets_per_node, num_mc_per_socket, undersample),
            ], width=10),
        ]),
    ], fluid=True)