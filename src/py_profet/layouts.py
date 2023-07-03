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
        html.P("Color time dimension:"),
        daq.ToggleSwitch(
            id='toggle-time',
            value=False
        ),
        html.Div(id='dropdown-toggle-node'),
        html.P("Node:"),
        dcc.Dropdown(['All'] + sorted(list(df['node_name'].unique())),
                    'All',
                    id='dropdown-node'),
        html.Div(id='dropdown-toggle-socket'),
        html.P("Socket:"),
        dcc.Dropdown(['All'] + sorted(list(df['socket'].unique())),
                    'All',
                    id='dropdown-socket'),
        html.Div(id='dropdown-toggle-mc'),
        html.P("Memory controller:"),
        dcc.Dropdown(['All'] + sorted(list(df['mc'].unique())) if df['mc'].nunique() > 1 else ['-'],
                    'All' if df['mc'].nunique() > 1 else '-',
                    id='dropdown-mc'),
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


def get_main_content():
    content_style = {
        "margin-left": "1rem",
        "margin-right": "2rem",
        "padding": "2rem 1rem",
    }

    system_info_tab = html.Div([
        html.H4('System Info'),
    ])

    charts_tab = html.Div([
        html.H4('App\'s Bandwidth-Latency'),
        dcc.Graph(id="scatter-plot", style={'width': '80%', 'height': '700px'}),
    ])

    tabs = dbc.Tabs([
        dbc.Tab(system_info_tab, label="System Info", tab_id="system-tab"),
        dbc.Tab(charts_tab, label="Charts", tab_id="charts-tab"),
    ], id="tabs", active_tab="system-tab")

    return html.Div([
        tabs,
    ], style=content_style)


def get_layout(df: pd.DataFrame):
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                get_sidebar(df),
            ], width=2),
            dbc.Col([
                get_main_content(),
            ], width=10),
        ]),
    ], fluid=True)