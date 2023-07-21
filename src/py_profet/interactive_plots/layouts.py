import pandas as pd
import numpy as np
from dash import Dash, dcc, html, Input, Output
import dash_daq as daq
import dash_bootstrap_components as dbc


def get_sidebar(df: pd.DataFrame):
    node_names = sorted(df['node_name'].unique())
    # Define marks for sliders
    marks_time = {i: str(round(i, 1)) for i in np.linspace(df['timestamp'].min()/1e9, df['timestamp'].max()/1e9, 5)}
    marks_bw = {i: str(int(i)) for i in np.linspace(df['bw'].min(), df['bw'].max(), 5)}
    marks_lat = {i: str(int(i)) for i in np.linspace(df['lat'].min(), df['lat'].max(), 5)}
    marks_opacity = {i: str(i) for i in np.linspace(0, 1, 5)}

    sidebar = html.Div([
        dbc.Row([
            html.P("Configuration:"),
            dcc.Upload(
                id='upload-config',
                children=dbc.Button("Load", id='upload-config-button', n_clicks=0, className='sidebar-button'),
            ),
            dcc.Download(id='download-config'),
            dbc.Button("Save", id='save-config', n_clicks=0, className='sidebar-button', style={'margin-top': '1rem'}),
        ], className='sidebar-element'),
        # dbc.Row([
        #     # html.P("Save Configuration:"),
        #     dcc.Download(id='download-config'),
        #     dbc.Button("Save", id='save-config', n_clicks=0, className='sidebar-button'),
        # ], className='sidebar-element'),
        dbc.Row([
            html.P("Node selection:"),
            dcc.Dropdown(
                id='node-selection-dropdown',
                # options=[{'label': 'All', 'value': 'all'}] + node_options,
                options=[{'label': node_name, 'value': node_name} for node_name in node_names],
                value=[node_name for node_name in node_names],
                searchable=True,
                clearable=True,
                multi=True,
            ),
        ], className='sidebar-element'),
        dbc.Row([
            html.P("Curves Color:"),
            dcc.Dropdown(
                id='curves-color-dropdown',
                options=[
                    {'label': 'Black', 'value': 'black'},
                    {'label': 'Red', 'value': 'red'},
                    {'label': 'Green', 'value': 'green'},
                    {'label': 'Blue', 'value': 'blue'},
                    # {'label': 'Rainbow', 'value': 'rainbow'},
                    # {'label': 'None', 'value': 'none'},
                ],
                value='black',
            ),
            # daq.ColorPicker(
            #     id='curves-color-picker',
            #     value=dict(hex='#000000')
            # ),
        ], className='sidebar-element'),
        dbc.Row([
            html.P("Curves Transparency:"),
            dcc.Slider(0, 1, 0.01, value=1, id='curves-transparency-slider', marks=marks_opacity),
        ], className='sidebar-element'),
        # dbc.Row([
        #     html.P("Show curves:"),
        #     daq.ToggleSwitch(
        #         id='toggle-curves',
        #         value=True
        #     ),
        #     html.Div(id='toggle-curves-output'),
        #     html.Div(id='toggle-time-output'),
        # ], className='sidebar-element'),
        dbc.Row([
            html.P("Timestamp (s):"),
            dcc.RangeSlider(
                id='time-range-slider',
                min=df['timestamp'].min()/1e9, max=df['timestamp'].max()/1e9, step=0.1,
                marks=marks_time,
                value=[df['timestamp'].min()/1e9, df['timestamp'].max()/1e9]
            ),
        ], className='sidebar-element'),
        dbc.Row([
            html.P("Bandwidth (GB/s):"),
            dcc.RangeSlider(
                id='bw-range-slider',
                min=df['bw'].min(), max=df['bw'].max(), step=1,
                marks=marks_bw,
                value=[df['bw'].min(), df['bw'].max()]
            ),
        ], className='sidebar-element'),
        dbc.Row([
            html.P("Latency (ns):"),
            dcc.RangeSlider(
                id='lat-range-slider',
                min=df['lat'].min(), max=df['lat'].max(), step=1,
                marks=marks_lat,
                value=[df['lat'].min(), df['lat'].max()]
            ),
        ], className='sidebar-element'),
        dbc.Row([
            html.P("Markers Transparency:"),
            dcc.Slider(0, 1, 0.01, value=0.1, id='markers-transparency-slider', marks=marks_opacity),
        ], className='sidebar-element'),
    ], className='sidebar')

    # keep the side bar in a collapsed state, so we can hide it when the charts tab is not selected
    return dbc.Collapse([sidebar], id="sidebar")

def get_summary_platform_row(cpu_freq: float, summary_table_attrs: dict):
    return dbc.Row([
        html.H2('Platform', className='summary-section-title'),
        # Server
        dbc.Col([
            dbc.Table([
                html.Thead([
                    html.Tr([
                        html.Th('Server', className='fixed-width-header'),
                    ])
                ], className='no-border-thead'),
                html.Tbody([
                    html.Tr([html.Td('Name'), html.Td(f'TODO')]),
                    html.Tr([html.Td('Number of nodes'), html.Td('TODO')]),
                    html.Tr([html.Td('Sockets per node'), html.Td('TODO')]),
                    html.Tr([html.Td('Hyper-threading'), html.Td('TODO: ON/OFF')]),
                ])
            ], **summary_table_attrs),
        ], md=4),
        # CPU
        dbc.Col([
            dbc.Table([
                html.Thead([
                    html.Tr([
                        html.Th('CPU', className='fixed-width-header'),
                    ])
                ], className='no-border-thead'),
                html.Tbody([
                    html.Tr([html.Td('Name'), html.Td('TODO')]),
                    html.Tr([html.Td('Number of cores'), html.Td('TODO')]),
                    html.Tr([html.Td('Frequency'), html.Td(f'{cpu_freq} GHz')]),
                ])
            ], **summary_table_attrs)
        ], md=4),
        # Memory
        dbc.Col([
            dbc.Table([
                html.Thead([
                    html.Tr([
                        html.Th('Memory', className='fixed-width-header'),
                    ])
                ], className='no-border-thead'),
                html.Tbody([
                    html.Tr([html.Td('Name'), html.Td('TODO')]),
                    html.Tr([html.Td('Number of channels'), html.Td('TODO')]),
                    html.Tr([html.Td('Frequency'), html.Td(f'TODO')]),
                ])
            ], **summary_table_attrs)
        ], md=4),
    ])

def get_summary_memory_row(df: pd.DataFrame, summary_table_attrs: dict):
    return dbc.Row([
        html.H2('Memory profile', className='summary-section-title'),
        dbc.Col([
            dbc.Table([
                html.Thead([
                    html.Tr([
                        html.Th('Header?', className='fixed-width-header'),
                    ])
                ], className='no-border-thead'),
                html.Tbody([
                    html.Tr([html.Td('Lead-off latency'), html.Td(f'{df["lat"].min():.1f} ns')]),
                    html.Tr([html.Td('Max. measured bandwidth'), html.Td(f'{df["bw"].max():.1f} GB/s')]),
                    html.Tr([html.Td('Stream bandwidth'), html.Td('TODO')]),
                ])
            ], **summary_table_attrs),
        ], md=4),
    ])

def get_summary_trace_row(df: pd.DataFrame, system_arch: dict, summary_table_attrs: dict):
    execution_duration_sec = (df['timestamp'].max() - df['timestamp'].min()) / 1e9

    sockets_per_node = [len(sockets) for sockets in system_arch.values()]
    if len(set(sockets_per_node)) == 1:
        # each node has the same number of sockets
        sockets_per_node_str = sockets_per_node[0]
    else:
        # show the number of sockets per node individually
        sockets_per_node_str = ', '.join([str(n) for n in sockets_per_node])

    return dbc.Row([
        html.H2('Trace', className='summary-section-title'),
        dbc.Col([
            dbc.Table([
                html.Thead([
                    html.Tr([
                        html.Th('Header?', className='fixed-width-header'),
                    ])
                ], className='no-border-thead'),
                html.Tbody([
                    html.Tr([html.Td('Duration'), html.Td(f'{execution_duration_sec:.1f} s')]),
                    html.Tr([html.Td('Number of nodes'), html.Td(len(system_arch.keys()))]),
                    html.Tr([html.Td('Node labels'), html.Td(', '.join(system_arch.keys()))]),
                    html.Tr([html.Td('Sockets per node'), html.Td(sockets_per_node_str)]),
                    html.Tr([html.Td('Cores'), html.Td('TODO')]),
                ])
            ], **summary_table_attrs),
        ], md=4),
    ])

def get_summary_tab(df: pd.DataFrame, cpu_freq: float, system_arch: dict):
    summary_table_attrs = {'bordered': True, 'hover': False, 'responsive': True,
                           'striped': True, 'className': 'summary-table'}

    return html.Div([
        # Platform summary
        get_summary_platform_row(cpu_freq, summary_table_attrs),
        # Memory profile summary
        get_summary_memory_row(df, summary_table_attrs),
        # Trace summary
        get_summary_trace_row(df, system_arch, summary_table_attrs),
    ], className='tab-content')

def get_charts_tab(system_arch: dict):
    # there is no need to do this processing, but doing it (similarly to how we build the graphs when updated)
    # makes the loading spinner appear right when the page is loaded, without delay
    chart_rows = []
    for node_name, sockets in system_arch.items():
        chart_cols = []
        for i_socket, mcs in sockets.items():
            for id_mc in mcs:
                chart_cols.append(dbc.Col([
                    html.Br(),
                    dcc.Graph(),
                ], sm=12, md=6))
        # Add row for each node
        chart_rows.append(dbc.Row(chart_cols))

    return dcc.Loading(
        id="loading",
        type="default",  # changes the loading spinner
        children=[dbc.Container(chart_rows, id='graph-container', fluid=True)],
        fullscreen=True,
    )

def get_main_content(df: pd.DataFrame, cpu_freq: float, system_arch: dict):
    system_info_tab = get_summary_tab(df, cpu_freq, system_arch)
    charts_tab = get_charts_tab(system_arch)

    # Reordering tabs to make them right-aligned
    tabs = dbc.Tabs([
        dbc.Tab(system_info_tab, label="Summary", tab_id="summary-tab"),
        dbc.Tab(charts_tab, label="Charts", tab_id="charts-tab"),
    ], id="tabs", active_tab="summary-tab")

    return html.Div([
        tabs,
    ], className='tab-content')

# Update the layout function
def get_layout(df: pd.DataFrame, cpu_freq: float, system_arch: dict):
    return dbc.Container([
        dbc.Row([
            dbc.Col([get_sidebar(df)], width=2),
            dbc.Col([get_main_content(df, cpu_freq, system_arch)], width=10),
        ]),
    ], fluid=True)


