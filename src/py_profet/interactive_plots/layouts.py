import pandas as pd
import numpy as np
from dash import dcc, html
import dash_bootstrap_components as dbc
import summary_info
import utils


def get_summary_row(summary: dict, summary_table_attrs: dict):
    # Create rows for each table
    cpu_rows = utils.get_dash_table_rows(summary['platform']['cpu'])
    memory_profile_rows = utils.get_dash_table_rows(summary['memory_profile'])
    trace_info_rows = utils.get_dash_table_rows(summary['trace_info'])

    return dbc.Row([
        html.H2('Operational Overview', className='summary-section-title'),
        # CPU
        dbc.Col([
            dbc.Table([
                html.Thead([
                    html.Tr([
                        html.Th('CPU', className='fixed-width-header'),
                    ])
                ], className='no-border-thead'),
                html.Tbody(cpu_rows)
            ], **summary_table_attrs, id='summary-table-server'),
        ], md=4),
        # Memory profile
        dbc.Col([
            dbc.Table([
                html.Thead([
                    html.Tr([
                        html.Th('Memory Profile', className='fixed-width-header'),
                    ])
                ], className='no-border-thead'),
                html.Tbody(memory_profile_rows)
            ], **summary_table_attrs, id='summary-table-cpu'),
        ], md=4),
        # Trace
        dbc.Col([
            dbc.Table([
                html.Thead([
                    html.Tr([
                        html.Th('Trace', className='fixed-width-header'),
                    ])
                ], className='no-border-thead'),
                html.Tbody(trace_info_rows)
            ], **summary_table_attrs, id='summary-table-memory')
        ], md=4),
    ])


def get_summary_tab(df: pd.DataFrame, config: dict, system_arch: dict):
    summary_table_attrs = {'bordered': True, 'hover': False, 'responsive': True,
                           'striped': True, 'className': 'summary-table'}
    summary = summary_info.get_summary_info(df, config, system_arch)

    return html.Div([
        # Summary of application and system
        get_summary_row(summary, summary_table_attrs),
    ], id='summary-tab-content')

def get_curve_graphs_sidebar(df: pd.DataFrame):
    node_names = sorted(df['node_name'].unique())
    # Define marks for sliders
    marks_time = {i: str(round(i, 1)) for i in np.linspace(df['timestamp'].min()/1e9, df['timestamp'].max()/1e9, 5)}
    marks_opacity = {i: str(i) for i in np.linspace(0, 1, 5)}

    marks_time_sampling = {i: f'{i}' for i in np.arange(0, 1.25, 0.25)}

    sidebar = html.Div([
        dbc.Row([
            html.P("Configuration:"),
            dcc.Upload(
                id='upload-config',
                children=dbc.Button("Load", id='upload-config-button', n_clicks=0, className=['sidebar-button', 'corporative-button']),
            ),
            dcc.Download(id='download-config'),
            dbc.Button("Save", id='save-config', n_clicks=0, className=['sidebar-button', 'corporative-button'], style={'margin-top': '1rem'}),
        ], className='sidebar-element'),
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
        ], id='node-selection-section', className='sidebar-element'),
        dbc.Row([
            html.P("Curves Color:"),
            dcc.Dropdown(
                id='curves-color-dropdown',
                options=[
                    {'label': 'Black', 'value': 'black'},
                    {'label': 'Red', 'value': 'red'},
                    {'label': 'Green', 'value': 'green'},
                    {'label': 'Blue', 'value': 'blue'},
                ],
                value='black',
                searchable=True,
                clearable=False,
            ),
        ], id='curves-color-dropdown-section', className='sidebar-element'),
        dbc.Row([
            html.P("Curves Transparency:"),
            dcc.Slider(0, 1, 0.01, value=1, id='curves-transparency-slider', marks=marks_opacity),
        ], id='curves-transparency-section', className='sidebar-element'),
        dbc.Row([
            html.P("Timestamp (s):"),
            dcc.RangeSlider(
                id='time-range-slider',
                min=df['timestamp'].min()/1e9, max=df['timestamp'].max()/1e9, step=0.1,
                marks=marks_time,
                value=[df['timestamp'].min()/1e9, df['timestamp'].max()/1e9]
            ),
        ], id='timestamp-section', className='sidebar-element'),
        dbc.Row([
            html.P("Stress Score Sampling:"),
            dcc.Dropdown(
                id='overview-sampling-mode',
                options=[
                    {'label': 'Maximum', 'value': 'stress'},
                    {'label': 'Mean', 'value': 'mean'},
                    {'label': 'Median', 'value': 'median'},
                    {'label': 'Mode', 'value': 'mode'},
                ],
                value='stress',
                searchable=True,
                clearable=False,
            ),
        ], id='overview-sampling-mode-section', className='sidebar-element'),
        dbc.Row([
            html.P("Sampling (500ms):", id='sampling-label'),
            dcc.RangeSlider(
                id='sampling-range-slider',
                min=0,
                max=1,
                step=0.005,
                marks=marks_time_sampling,
                value=[0.5],
            ),
        ], id='sampling-section', className='sidebar-element'),
        dbc.Row([
            html.P("Markers Color:"),
            dcc.Dropdown(
                id='markers-color-dropdown',
                options=[
                    {'label': 'Stress score', 'value': 'stress_score'},
                    {'label': 'Black', 'value': 'black'},
                    {'label': 'Red', 'value': 'red'},
                    {'label': 'Green', 'value': 'green'},
                    {'label': 'Blue', 'value': 'blue'},
                ],
                value='stress_score',
                searchable=True,
                clearable=False,
            ),
        ], id='marker-color-section', className='sidebar-element'),
        dbc.Row([
            html.P("Markers Transparency:"),
            dcc.Slider(0, 1, 0.01, value=1, id='markers-transparency-slider', marks=marks_opacity),
        ], id='marker-transparency-section', className='sidebar-element'),
    ], className='sidebar')

    # Keep the side bar in a collapsed state, so we can hide it when the charts tab is not selected
    return dbc.Collapse([sidebar], id="sidebar")


def get_graphs_container(system_arch: dict, id_prefix: str, max_elements: int = None):
    # Create per socket o per MC graphs (e.g. curves or roofline)
    chart_rows = []

    if max_elements is not None:
        # add warning text
        chart_rows.append(dbc.Row([
            html.H5(f'Warning: Data is undersampled to {max_elements:,} elements.', style={"color": "red"}),
        ], style={'padding-bottom': '1rem', 'padding-top': '2rem'}))

    for node_name, sockets in system_arch.items():
        # Create a new container for each node
        node_container = dbc.Container([], id=f'{id_prefix}-node-{node_name}-container', fluid=True)
        node_container.children.append(html.H2(f'Node {node_name}', style={'padding-top': '3rem'}))
        node_rows = dbc.Row([], id=f'{id_prefix}-node-{node_name}-row')

        for i_socket, mcs in sockets.items():
            bw_balance_str = 'Socket bandwidth balance: %'
            if len(mcs) > 1:
                # Create a new container for each socket within the node container
                socket_container = dbc.Container([], id=f'{id_prefix}-node-{node_name}-socket-{i_socket}-container', fluid=True)
                socket_container.children.append(html.H3(f'Socket {i_socket}', style={'padding-top': '2rem'}))
                socket_rows = dbc.Row([], id=f'{id_prefix}-node-{node_name}-socket-{i_socket}-row')
                bw_balance_str = 'Memory channel bandwidth balance: '

            for id_mc in mcs:
                metadata = {
                    'node_name': node_name,
                    'socket': i_socket,
                    'mc': id_mc,
                }
                col = dbc.Col([
                    html.Br(),
                    dcc.Graph(id=f'{id_prefix}-node-{node_name}-socket-{i_socket}-mc-{id_mc}'),
                    dcc.Store(id=f'{id_prefix}-node-{node_name}-socket-{i_socket}-mc-{id_mc}-store', data=metadata),
                    html.H6(children=bw_balance_str,
                            style={'padding-left': '5rem'},
                            id=f'{id_prefix}-node-{node_name}-socket-{i_socket}-mc-{id_mc}-bw-balance'),
                ], sm=12, md=6, id=f'{id_prefix}-node-{node_name}-socket-{i_socket}-mc-{id_mc}-col')
                if len(mcs) > 1:
                    # Add graph to MC container if there are multiple MCs
                    socket_rows.children.append(col)
                else:
                    # Add the graph to the socket container
                    node_rows.children.append(col)
            
            if len(mcs) > 1:
                # Add the completed socket container to the node container's row
                socket_container.children.append(socket_rows)
                node_container.children.append(socket_container)

        if len(mcs) == 1:
            node_container.children.append(node_rows)
        # Add the completed node container to the overall layout
        chart_rows.append(node_container)

    return dbc.Container(chart_rows, id=f'{id_prefix}-graphs-container', fluid=True)


def get_overview_container():
    container = dbc.Container([], id=f'app-overview-container', fluid=True)

    col = dbc.Col([
        html.Br(),
        dcc.Graph(id='overview-chart', style={'height': '800px'}),
    ])

    hidden_div = html.Div(id='overview-hidden-div', style={'display': 'none'})

    container.children.append(col)
    container.children.append(hidden_div)

    return container


def get_curve_graphs_tab(system_arch: dict, max_elements: int = None):
    return get_graphs_container(system_arch, "curves", max_elements)

def get_overview_tab():
    return get_overview_container()

def get_main_content(df: pd.DataFrame, config: dict, system_arch: dict, max_elements: int = None, expert: bool = False):
    system_info_tab = get_summary_tab(df, config, system_arch)
    curves_tab = get_curve_graphs_tab(system_arch, max_elements)
    overview_tab = get_overview_tab()

    t = [
        dbc.Tab(system_info_tab, label="Summary", tab_id="summary-tab"),
        dbc.Tab(overview_tab, label="Application Overview", tab_id="app-overview-tab"),
    ]

    # Add expert tabs
    if expert:
        t.append(dbc.Tab(curves_tab, label="Curves", tab_id="curves-tab"))
    tabs = dbc.Tabs(t, id="tabs", active_tab="summary-tab")

    return html.Div([
        dbc.Button("Export to PDF", id="btn-pdf-export", className=["corporative-button", "pdf-button"]),
        dcc.Download(id="download-pdf"),
        tabs,
    ], className='tab-content')

# Update the layout function
def get_layout(df: pd.DataFrame, config: dict, system_arch: dict, max_elements: int = None, expert: bool = False):
    return dcc.Loading(
        id="loading",
        type="default",  # changes the loading spinner
        children=[dbc.Container([
            dbc.Row([
                dbc.Col([get_curve_graphs_sidebar(df)], width=2),
                dbc.Col([get_main_content(df, config, system_arch, max_elements, expert)], width=10),
            ]),
        ], fluid=True)],
        fullscreen=True,
    )

