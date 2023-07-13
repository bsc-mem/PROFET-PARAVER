import os
import json
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate

import utils

def register_callbacks(app, df, curves, system_arch, trace_file, labels, stress_score_config, max_elements=None):
    @app.callback(
        Output('download-config', 'data'),
        Input('save-config', 'n_clicks'),
        State('curves-color-dropdown', 'value'),
        State('curves-transparency-slider', 'value'),
        State('time-range-slider', 'value'),
        State('bw-range-slider', 'value'),
        State('lat-range-slider', 'value'),
        State('markers-transparency-slider', 'value')
    )
    def save_config(save_n_clicks, curves_color, curves_transparency, 
                    time_range, bw_range, lat_range, markers_transparency):
        if save_n_clicks is None or save_n_clicks == 0:
            raise PreventUpdate

        # Generate the configuration data
        config_json = json.dumps({
            'curves_color': curves_color,
            'curves_transparency': curves_transparency,
            'time_range': time_range,
            'bw_range': bw_range,
            'lat_range': lat_range,
            'markers_transparency': markers_transparency,
        }, indent=2)

        # You can choose a default filename, but the user will still
        # have the option to choose their own filename in the download dialog
        # basename gets the filename with the extension, and splitext removes the extension
        filename = os.path.splitext(os.path.basename(trace_file))[0] + '.dash.config.json'

        return dict(content=config_json, filename=filename)

    @app.callback(
        Output('graph-container', 'children'),
        # Input('upload-config', 'filename'),
        Input('curves-color-dropdown', 'value'),
        Input('curves-transparency-slider', 'value'),
        Input('time-range-slider', 'value'),
        Input('bw-range-slider', 'value'),
        Input('lat-range-slider', 'value'),
        Input('markers-transparency-slider', 'value')
    )
    def update_chart(curves_color, curves_transparency, 
                     time_range, bw_range, lat_range, markers_transparency):
        # built graphs for each node, socket and mc
        updated_graph_rows = []

        if max_elements is not None:
            # add warning text
            updated_graph_rows.append(dbc.Row([
                html.H5(f'Warning: Data is undersampled to {max_elements:,} elements.', style={"color": "red"}),
            ], style={'padding-bottom': '1rem', 'padding-top': '2rem'}))

        color_bar = utils.get_color_bar(labels, stress_score_config)

        for node_name, sockets in system_arch.items():
            # Create a new container for each node
            node_container = dbc.Container([], id=f'node-{node_name}-container', fluid=True)
            node_container.children.append(html.H2(f'Node {node_name}', style={'padding-top': '2rem'}))
            # Create a row for the sockets to sit in. This variable is unused if len(mcs) == 1 (visualization is per socket)
            sockets_row = dbc.Row([])

            for i_socket, mcs in sockets.items():
                if len(mcs) > 1:
                    # Create a new container for each socket within the node container
                    socket_container = dbc.Container([], id=f'node-{node_name}-socket-{i_socket}-container', fluid=True)
                    socket_container.children.append(html.H3(f'Socket {i_socket}', style={'padding-top': '1rem'}))
                    mcs_row = dbc.Row([])

                for id_mc in mcs:
                    # Filter the dataframe to only include the selected node, socket and MC
                    filt_df = utils.filter_df(df, node_name, i_socket, id_mc, time_range, bw_range, lat_range)
                    graph_title = f'MC {id_mc}' if len(mcs) > 1 else f'Socket {i_socket}'
                    fig = utils.get_graph_fig(filt_df, curves, curves_color, curves_transparency, markers_transparency,
                                        graph_title, labels['bw'], labels['lat'], stress_score_config['colorscale'], color_bar)

                    bw_balance = filt_df['bw'].mean() / filt_df['bw'].max()
                    lat_balance = filt_df['lat'].mean() / filt_df['lat'].max()
                    # print(f'Node {node_name}, socket {i_socket}, MC {id_mc}: BW balance: {bw_balance:.2f} ({filt_df["bw"].mean():.2f}, {filt_df["bw"].max():.2f})')
                    # print(f'Node {node_name}, socket {i_socket}, MC {id_mc}: Lat balance: {lat_balance:.2f} ({filt_df["lat"].mean():.2f}, {filt_df["lat"].max():.2f})')
                    col = dbc.Col([
                        html.Br(),
                        dcc.Graph(id=f'node-{node_name}-socket-{i_socket}-mc-{id_mc}', figure=fig),
                        html.H6(f'BW balance: {bw_balance:.2f}', style={'padding-left': '5rem'}),
                        html.H6(f'Lat. balance: {lat_balance:.2f}', style={'padding-left': '5rem'}),
                    ], sm=12, md=6)
                    if len(mcs) > 1:
                        # Add graph to MC container if there are multiple MCs
                        mcs_row.children.append(col)
                    else:
                        # Add the graph to the socket container
                        sockets_row.children.append(col)

                    # mc_bw_balance = filt_df['bw'].groupby('timestamp').mean() / filt_df['bw'].groupby('timestamp').max()
                    # mc_lat_balance = filt_df['lat'].groupby('timestamp').mean() / filt_df['lat'].groupby('timestamp').max()
                if len(mcs) > 1:
                    # Add the completed socket container to the node container's row
                    socket_container.children.append(mcs_row)
                    node_container.children.append(socket_container)
                
            if len(mcs) == 1:
                node_container.children.append(sockets_row)
            # Add the completed node container to the overall layout
            updated_graph_rows.append(node_container)

        return updated_graph_rows
    