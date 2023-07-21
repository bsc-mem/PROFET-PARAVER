import os
import json
import base64
from dash import dcc, html, no_update, Input, Output, State
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate

import utils

def register_callbacks(app, df, curves, system_arch, trace_file, labels, stress_score_config, max_elements=None):

    # toggle sidebar, showing it when the charts tab is selected and hidding it otherwise
    @app.callback(
        Output("sidebar", "is_open"),
        Input("tabs", "active_tab")
    )
    def toggle_sidebar(active_tab):
        return active_tab == "charts-tab"

    # we need all the elements as outputs for updating them in case of loading a json file
    # if a json file is not loaded, the callback has still to return the real values
    # for plotting the graphs, so that's why need the States here
    @app.callback(
        Output('node-selection-dropdown', 'value'),
        Output('curves-color-dropdown', 'value'),
        Output('curves-transparency-slider', 'value'),
        Output('time-range-slider', 'value'),
        Output('bw-range-slider', 'value'),
        Output('lat-range-slider', 'value'),
        Output('markers-transparency-slider', 'value'),
        Input('upload-config', 'contents'),
        State('node-selection-dropdown', 'value'),
        State('curves-color-dropdown', 'value'),
        State('curves-transparency-slider', 'value'),
        State('time-range-slider', 'value'),
        State('bw-range-slider', 'value'),
        State('lat-range-slider', 'value'),
        State('markers-transparency-slider', 'value'),
    )
    def load_config(contents, selected_nodes, curves_color, curves_transparency, time_range, 
                    bw_range, lat_range, markers_transparency):
        if contents is None:
            return selected_nodes, curves_color, curves_transparency, time_range, bw_range, lat_range, markers_transparency
        
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        try:
            if 'json' in content_type:
                # assume that the user uploaded a JSON file
                json_file = json.loads(decoded)
                return_order = ['selected_nodes', 'curves_color', 'curves_transparency', 'time_range',
                                'bw_range', 'lat_range', 'markers_transparency']
                return [json_file.get(key) for key in return_order]
        except Exception as e:
            print(e)
            return html.Div([
                'There was an error processing this file.'
            ])
                     
    @app.callback(
        Output('download-config', 'data'),
        Input('save-config', 'n_clicks'),
        State('node-selection-dropdown', 'value'),
        State('curves-color-dropdown', 'value'),
        State('curves-transparency-slider', 'value'),
        State('time-range-slider', 'value'),
        State('bw-range-slider', 'value'),
        State('lat-range-slider', 'value'),
        State('markers-transparency-slider', 'value'),
    )
    def save_config(save_n_clicks, selected_nodes, curves_color, curves_transparency, time_range, 
                    bw_range, lat_range, markers_transparency):
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
            'selected_nodes': selected_nodes,
        }, indent=2)

        # You can choose a default filename, but the user will still
        # have the option to choose their own filename in the download dialog
        # basename gets the filename with the extension, and splitext removes the extension
        filename = os.path.splitext(os.path.basename(trace_file))[0] + '.dash.config.json'

        return dict(content=config_json, filename=filename)

    @app.callback(
        Output('graph-container', 'children'),
        Input('node-selection-dropdown', 'value'),
        Input('curves-color-dropdown', 'value'),
        Input('curves-transparency-slider', 'value'),
        Input('time-range-slider', 'value'),
        Input('bw-range-slider', 'value'),
        Input('lat-range-slider', 'value'),
        Input('markers-transparency-slider', 'value'),
    )
    def update_chart(selected_nodes, curves_color, curves_transparency, time_range, 
                     bw_range, lat_range, markers_transparency):
        # built graphs for each node, socket and mc
        updated_graph_rows = []

        if max_elements is not None:
            # add warning text
            updated_graph_rows.append(dbc.Row([
                html.H5(f'Warning: Data is undersampled to {max_elements:,} elements.', style={"color": "red"}),
            ], style={'padding-bottom': '1rem', 'padding-top': '2rem'}))

        color_bar = utils.get_color_bar(labels, stress_score_config)

        bw_per_socket = df.groupby(['node_name', 'socket'])['bw'].mean()

        for node_name, sockets in system_arch.items():
            if node_name not in selected_nodes:
                continue

            # Create a new container for each node
            node_container = dbc.Container([], id=f'node-{node_name}-container', fluid=True)
            node_container.children.append(html.H2(f'Node {node_name}', style={'padding-top': '3rem'}))
            # Create a row for the sockets to sit in. This variable is unused if len(mcs) == 1 (visualization is per socket)
            sockets_row = dbc.Row([])

            for i_socket, mcs in sockets.items():
                if len(mcs) > 1:
                    # Create a new container for each socket within the node container
                    socket_container = dbc.Container([], id=f'node-{node_name}-socket-{i_socket}-container', fluid=True)
                    socket_container.children.append(html.H3(f'Socket {i_socket}', style={'padding-top': '0rem'}))
                    mcs_row = dbc.Row([])

                for id_mc in mcs:
                    # Filter the dataframe to only include the selected node, socket and MC
                    filt_df = utils.filter_df(df, node_name, i_socket, id_mc, time_range, bw_range, lat_range)
                    graph_title = f'Memory channel {id_mc}' if len(mcs) > 1 else f'Socket {i_socket}'
                    fig = utils.get_graph_fig(filt_df, curves, curves_color, curves_transparency, markers_transparency,
                                        graph_title, labels['bw'], labels['lat'], stress_score_config['colorscale'], color_bar)

                    bw_socket_balance = filt_df['bw'].mean() * 100 / bw_per_socket.sum()
                    # print(f'Node {node_name}, socket {i_socket}, MC {id_mc}: BW balance: {bw_balance:.2f} ({filt_df["bw"].mean():.2f}, {filt_df["bw"].max():.2f}); std = {filt_df["bw"].std():.2f}')
                    # print(f'Node {node_name}, socket {i_socket}, MC {id_mc}: Lat balance: {lat_balance:.2f} ({filt_df["lat"].mean():.2f}, {filt_df["lat"].max():.2f}); std = {filt_df["lat"].std():.2f}')
                    col = dbc.Col([
                        html.Br(),
                        dcc.Graph(id=f'node-{node_name}-socket-{i_socket}-mc-{id_mc}', figure=fig),
                        html.H6(f'Socket bandwidth balance: {bw_socket_balance:.0f}%', style={'padding-left': '5rem'}),
                    ], sm=12, md=6)
                    if len(mcs) > 1:
                        # Add graph to MC container if there are multiple MCs
                        mcs_row.children.append(col)
                    else:
                        # Add the graph to the socket container
                        sockets_row.children.append(col)

                if len(mcs) > 1:
                    # Add the completed socket container to the node container's row
                    socket_container.children.append(mcs_row)
                    node_container.children.append(socket_container)
                
            if len(mcs) == 1:
                node_container.children.append(sockets_row)
            # Add the completed node container to the overall layout
            updated_graph_rows.append(node_container)

        return updated_graph_rows
    