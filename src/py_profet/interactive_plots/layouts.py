import pandas as pd
import numpy as np
from dash import Dash, dcc, html, Input, Output
import dash_daq as daq
import dash_bootstrap_components as dbc

# Define global style variables
BODY_STYLE = {
    "font-family": "Arial, sans-serif",  # Use Arial as default font
    "background-color": "#F5F5F5",  # Soft gray color for page background
    "margin": "2rem 1rem",  # Space from top and sides of the page
}

SIDEBAR_STYLE = {
    "padding": "2rem 1rem",
    "background-color": "white",
    "border-radius": "10px",
    "margin-bottom": "1rem",
    "margin-top": "2rem",
}

CONTENT_STYLE = {
    "background-color": "white",
    "margin-left": "2rem",
    "margin-right": "2rem",
    "padding": "2rem 1rem",
}

TAB_STYLE = {
    "borderTop": "1px solid #d6d6d6",
    "backgroundColor": "white",
    "color": "#6c757d",
    "padding": ".5rem",
}

TAB_ACTIVE_STYLE = {
    "borderTop": "1px solid #d6d6d6",
    "backgroundColor": "#1f3970",
    "color": "white",
    "padding": ".5rem",
}



def get_sidebar(df: pd.DataFrame):
    # Define marks for sliders
    marks_time = {i: str(int(i)) for i in np.linspace(df['timestamp'].min(), df['timestamp'].max(), 5)}
    marks_bw = {i: str(int(i)) for i in np.linspace(df['bw'].min(), df['bw'].max(), 5)}
    marks_lat = {i: str(int(i)) for i in np.linspace(df['lat'].min(), df['lat'].max(), 5)}
    marks_opacity = {i: str(i) for i in np.linspace(0, 1, 5)}

    return html.Div([
        dbc.Row([
            html.P("Show curves:"),
            daq.ToggleSwitch(
                id='toggle-curves',
                value=True
            ),
            html.Div(id='toggle-curves-output'),
            html.Div(id='toggle-time-output'),
        ], style={'padding-bottom': '1rem'}),
        dbc.Row([
            html.P("Timestamp (ns):"),
            dcc.RangeSlider(
                id='range-slider-time',
                min=df['timestamp'].min(), max=df['timestamp'].max(), step=1000000,
                marks=marks_time,
                value=[df['timestamp'].min(), df['timestamp'].max()]
            ),
        ], style={'padding-bottom': '1rem'}),
        dbc.Row([
            html.P("Bandwidth (GB/s):"),
            dcc.RangeSlider(
                id='range-slider-bw',
                min=df['bw'].min(), max=df['bw'].max(), step=1,
                marks=marks_bw,
                value=[df['bw'].min(), df['bw'].max()]
            ),
        ], style={'padding-bottom': '1rem'}),
        dbc.Row([
            html.P("Latency (ns):"),
            dcc.RangeSlider(
                id='range-slider-lat',
                min=df['lat'].min(), max=df['lat'].max(), step=1,
                marks=marks_lat,
                value=[df['lat'].min(), df['lat'].max()]
            ),
        ], style={'padding-bottom': '1rem'}),
        dbc.Row([
            html.P("Transparecy:"),
            dcc.Slider(0, 1, 0.01, value=0.1, id='slider-opacity', marks=marks_opacity),
        ], style={'padding-bottom': '1rem'}),
    ], style=SIDEBAR_STYLE)  # Apply the sidebar style


def get_system_info_tab(cpu_freq: float, node_names: list, num_sockets_per_node: int, num_mc_per_socket: int = None):
    return html.Div([
        html.H4('System Information', style={'margin-bottom': '1rem'}),
        dbc.Table([
            html.Thead([
                html.Tr([
                    html.Th('Header 1'),
                    html.Th('Header 2'),
                ])
            ]),
            html.Tbody([
                html.Tr([html.Td('CPU frequency'), html.Td(f'{cpu_freq} GHz')]),
                html.Tr([html.Td('Number of nodes'), html.Td(len(node_names))]),
                html.Tr([html.Td('Node labels'), html.Td(', '.join(node_names))]),
                html.Tr([html.Td('Sockets per node'), html.Td(num_sockets_per_node)]),
                # html.Tr([html.Td('Data 9'), html.Td('Data 10')]),
            ])
        ], bordered=True, hover=False, responsive=True, striped=True, className='system-info-table')
    ], style=CONTENT_STYLE)


def get_charts_tab(node_names: list, num_sockets_per_node: int,
                   num_mc_per_socket: int = None, undersample: int = None):
    chart_rows = []
    if undersample is not None:
        # add warning text
        chart_rows.append(dbc.Row([
            html.H5(f'Warning: Data is undersampled to {undersample:,} elements.', style={"color": "red"}),
        ], style={'padding-bottom': '1rem', 'padding-top': '2rem'}))

    for node_name in node_names:
        chart_cols = []
        for i_socket in range(num_sockets_per_node):
            chart_cols.append(dbc.Col([
                html.Br(),
                dcc.Graph(id=f"node-{node_name}-socket-{i_socket + 1}",
                            figure={
                                'data': [],
                                'layout': {
                                    'title': {
                                        'text': f'Node {node_name} - Socket {i_socket + 1}',
                                        'font': {
                                            'size': 24,  # Increase size
                                            'color': 'black',  # Or any other color you prefer
                                            'family': 'Arial, sans-serif',  # Specify font family
                                        }
                                    },
                                }
                            }),
            ], sm=12, md=6))
        # Add row for each node
        chart_rows.append(dbc.Row(chart_cols))

    return dcc.Loading(
        id="loading",
        type="default",  # changes the loading spinner
        children=[dbc.Container(chart_rows, id='graph-container', fluid=True)],
        fullscreen=True,
    )


def get_main_content(cpu_freq: float, node_names: list, num_sockets_per_node: int,
                     num_mc_per_socket: int = None, undersample: int = None):
    system_info_tab = get_system_info_tab(cpu_freq, node_names, num_sockets_per_node, num_mc_per_socket)
    charts_tab = get_charts_tab(node_names, num_sockets_per_node, num_mc_per_socket, undersample)

    # Reordering tabs to make them right-aligned
    tabs = dbc.Tabs([
        dbc.Tab(system_info_tab, label="System", tab_id="system-tab"),
        dbc.Tab(charts_tab, label="Charts", tab_id="charts-tab"),
    ], id="tabs", active_tab="charts-tab")

    return html.Div([
        tabs,
    ], style=CONTENT_STYLE)


# Update the layout function
def get_layout(df: pd.DataFrame, cpu_freq: float, node_names: list, num_sockets_per_node: int,
               num_mc_per_socket: int = None, undersample: int = None):
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                get_sidebar(df),
            ], width=2),
            dbc.Col([
                get_main_content(cpu_freq, node_names, num_sockets_per_node, num_mc_per_socket, undersample),
            ], width=10),
        ]),
    ], fluid=True, style=BODY_STYLE)  # Applying the page style to the layout