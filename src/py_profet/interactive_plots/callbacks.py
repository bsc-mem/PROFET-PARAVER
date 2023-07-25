import os
import json
import base64
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from dash import dcc, html, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate

import utils
import pdf_gen

def register_callbacks(app, df, curves, config, system_arch, trace_file, labels, stress_score_config, max_elements=None):

    # toggle sidebar, showing it when the charts tab is selected and hidding it otherwise
    @app.callback(
        Output("sidebar", "is_open"),
        Input("tabs", "active_tab")
    )
    def toggle_sidebar(active_tab):
        return active_tab == "charts-tab"
    
    @app.callback(
        Output("download-pdf", "data"),
        Input("btn-export", "n_clicks"),
        prevent_initial_call=True
    )
    def export_to_pdf(n):
        # Extract graphs
        # print(app.layout)
        graphs = utils.extract_graphs(app.layout)
        # print('Graphs size:', len(graphs))
        # Generate PDF
        pdf_string = pdf_gen.generate_pdf(df, config, system_arch, graphs)
        # Convert to Base64
        pdf_base64 = base64.b64encode(pdf_string).decode('utf-8')

        return dict(content=pdf_base64, filename="my_report.pdf", type="application/pdf", base64=True)



    # we need all the elements as outputs for updating them in case of loading a json file
    # if a json file is not loaded, the callback has still to return the real values
    # for plotting the graphs, so that's why need the States here
    @app.callback(
        Output('node-selection-dropdown', 'value'),
        Output('curves-color-dropdown', 'value'),
        Output('curves-transparency-slider', 'value'),
        Output('time-range-slider', 'value'),
        Output('markers-transparency-slider', 'value'),
        Input('upload-config', 'contents'),
        State('node-selection-dropdown', 'value'),
        State('curves-color-dropdown', 'value'),
        State('curves-transparency-slider', 'value'),
        State('time-range-slider', 'value'),
        State('markers-transparency-slider', 'value'),
    )
    def load_config(contents, selected_nodes, curves_color, curves_transparency, time_range, 
                    markers_transparency):
        if contents is None:
            return selected_nodes, curves_color, curves_transparency, time_range, markers_transparency
        
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        try:
            if 'json' in content_type:
                # assume that the user uploaded a JSON file
                json_file = json.loads(decoded)
                return_order = ['selected_nodes', 'curves_color', 'curves_transparency', 'time_range',
                                'markers_transparency']
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
        State('markers-transparency-slider', 'value'),
    )
    def save_config(save_n_clicks, selected_nodes, curves_color, curves_transparency, time_range, 
                    markers_transparency):
        if save_n_clicks is None or save_n_clicks == 0:
            raise PreventUpdate

        # Generate the configuration data
        config_json = json.dumps({
            'curves_color': curves_color,
            'curves_transparency': curves_transparency,
            'time_range': time_range,
            # 'bw_range': bw_range,
            # 'lat_range': lat_range,
            'markers_transparency': markers_transparency,
            'selected_nodes': selected_nodes,
        }, indent=2)

        # You can choose a default filename, but the user will still
        # have the option to choose their own filename in the download dialog
        # basename gets the filename with the extension, and splitext removes the extension
        filename = os.path.splitext(os.path.basename(trace_file))[0] + '.dash.config.json'

        return dict(content=config_json, filename=filename)

    # @app.callback(
    #     Output('graph-container', 'children'),
    #     Input('node-selection-dropdown', 'value'),
    #     Input('curves-color-dropdown', 'value'),
    #     Input('curves-transparency-slider', 'value'),
    #     Input('time-range-slider', 'value'),
    #     # Input('bw-range-slider', 'value'),
    #     # Input('lat-range-slider', 'value'),
    #     Input('markers-color-dropdown', 'value'),
    #     Input('markers-transparency-slider', 'value'),
    # )
    # def update_chart(selected_nodes, curves_color, curves_transparency, time_range, 
    #                  markers_color, markers_transparency):
    #     # built graphs for each node, socket and mc
    #     updated_graph_rows = []

    #     if max_elements is not None:
    #         # add warning text
    #         updated_graph_rows.append(dbc.Row([
    #             html.H5(f'Warning: Data is undersampled to {max_elements:,} elements.', style={"color": "red"}),
    #         ], style={'padding-bottom': '1rem', 'padding-top': '2rem'}))

    #     color_bar = None
    #     if markers_color == 'stress_score':        
    #         color_bar = utils.get_color_bar(labels, stress_score_config)

    #     bw_per_socket = df.groupby(['node_name', 'socket'])['bw'].mean()

    #     for node_name, sockets in system_arch.items():
    #         if node_name not in selected_nodes:
    #             continue

    #         # Create a new container for each node
    #         node_container = dbc.Container([], id=f'node-{node_name}-container', fluid=True)
    #         node_container.children.append(html.H2(f'Node {node_name}', style={'padding-top': '3rem'}))
    #         # Create a row for the sockets to sit in. This variable is unused if len(mcs) == 1 (visualization is per socket)
    #         sockets_row = dbc.Row([])

    #         for i_socket, mcs in sockets.items():
    #             if len(mcs) > 1:
    #                 # Create a new container for each socket within the node container
    #                 socket_container = dbc.Container([], id=f'node-{node_name}-socket-{i_socket}-container', fluid=True)
    #                 socket_container.children.append(html.H3(f'Socket {i_socket}', style={'padding-top': '0rem'}))
    #                 mcs_row = dbc.Row([])

    #             for id_mc in mcs:
    #                 # Filter the dataframe to only include the selected node, socket and MC
    #                 filt_df = utils.filter_df(df, node_name, i_socket, id_mc, time_range, bw_range=(), lat_range=())
    #                 graph_title = f'Memory channel {id_mc}' if len(mcs) > 1 else f'Socket {i_socket}'
    #                 fig = utils.get_graph_fig(filt_df, curves, curves_color, curves_transparency, markers_color, markers_transparency,
    #                                           graph_title, labels['bw'], labels['lat'], stress_score_config['colorscale'], color_bar)

    #                 bw_socket_balance = filt_df['bw'].mean() * 100 / bw_per_socket.sum()
    #                 # print(f'Node {node_name}, socket {i_socket}, MC {id_mc}: BW balance: {bw_balance:.2f} ({filt_df["bw"].mean():.2f}, {filt_df["bw"].max():.2f}); std = {filt_df["bw"].std():.2f}')
    #                 # print(f'Node {node_name}, socket {i_socket}, MC {id_mc}: Lat balance: {lat_balance:.2f} ({filt_df["lat"].mean():.2f}, {filt_df["lat"].max():.2f}); std = {filt_df["lat"].std():.2f}')
    #                 col = dbc.Col([
    #                     html.Br(),
    #                     dcc.Graph(id=f'node-{node_name}-socket-{i_socket}-mc-{id_mc}', figure=fig),
    #                     html.H6(f'Socket bandwidth balance: {bw_socket_balance:.0f}%', style={'padding-left': '5rem'}),
    #                 ], sm=12, md=6)
    #                 if len(mcs) > 1:
    #                     # Add graph to MC container if there are multiple MCs
    #                     mcs_row.children.append(col)
    #                 else:
    #                     # Add the graph to the socket container
    #                     sockets_row.children.append(col)

    #             if len(mcs) > 1:
    #                 # Add the completed socket container to the node container's row
    #                 socket_container.children.append(mcs_row)
    #                 node_container.children.append(socket_container)
                
    #         if len(mcs) == 1:
    #             node_container.children.append(sockets_row)
    #         # Add the completed node container to the overall layout
    #         updated_graph_rows.append(node_container)

    #     return updated_graph_rows

    # @app.callback(
    #     [Output(f'node-{node_name}-socket-{i_socket}-mc-{id_mc}', 'figure') for node_name, sockets in system_arch.items() for i_socket, mcs in sockets.items() for id_mc in mcs],
    #     Input('curves-color-dropdown', 'value'),
    #     [State(f'node-{node_name}-socket-{i_socket}-mc-{id_mc}', 'figure') for node_name, sockets in system_arch.items() for i_socket, mcs in sockets.items() for id_mc in mcs],
    #     prevent_initial_call=True,
    # )
    # def update_graph_curves_color(curves_color, *current_figures):
    #     updated_figures = []
    #     print(current_figures[0]['data'][0])
    #     # for fig in current_figures:
    #     #     print(fig['data'][0])
    #         # fig['data'][0] = 
    #         # updated_figures.append(fig)

    #     return updated_figures
    
    @app.callback(
        [Output(f'node-{node_name}-socket-{i_socket}-mc-{id_mc}', 'figure') for node_name, sockets in system_arch.items() for i_socket, mcs in sockets.items() for id_mc in mcs],
        Input('node-selection-dropdown', 'value'),
        Input('curves-color-dropdown', 'value'),
        Input('curves-transparency-slider', 'value'),
        Input('time-range-slider', 'value'),
        Input('markers-color-dropdown', 'value'),
        Input('markers-transparency-slider', 'value'),
        [State(f'node-{node_name}-socket-{i_socket}-mc-{id_mc}', 'figure') for node_name, sockets in system_arch.items() for i_socket, mcs in sockets.items() for id_mc in mcs],
    )
    def update_chart(selected_nodes, curves_color, curves_transparency, time_range, 
                     markers_color, markers_transparency, *current_figures):
        if len(callback_context.triggered) > 1:
            # Handle initial call logic here. This is not triggered by a specific input, just by the page loading.
            # All inputs are being passed as context
            figures = []

            # Generate graphs for each node, socket and mc
            color_bar = None
            if markers_color == 'stress_score':        
                color_bar = utils.get_color_bar(labels, stress_score_config)

            for node_name, sockets in system_arch.items():
                if node_name not in selected_nodes:
                    continue
                for i_socket, mcs in sockets.items():
                    if len(mcs) > 1:
                        # Create a new container for each socket within the node container
                        socket_container = dbc.Container([], id=f'node-{node_name}-socket-{i_socket}-container', fluid=True)
                        socket_container.children.append(html.H3(f'Socket {i_socket}', style={'padding-top': '0rem'}))
                    for id_mc in mcs:
                        # Filter the dataframe to only include the selected node, socket and MC
                        filt_df = utils.filter_df(df, node_name, i_socket, id_mc, time_range, bw_range=(), lat_range=())
                        graph_title = f'Memory channel {id_mc}' if len(mcs) > 1 else f'Socket {i_socket}'
                        fig = utils.get_graph_fig(filt_df, curves, curves_color, curves_transparency, markers_color, markers_transparency,
                                                graph_title, labels['bw'], labels['lat'], stress_score_config['colorscale'], color_bar)
                        figures.append(fig)
            return figures
        
        # Handle callback logic. This is triggered by a specific input.
        input_id = callback_context.triggered[0]['prop_id'].split('.')[0]

        if input_id == 'node-selection-dropdown':
            pass
        elif input_id == 'curves-color-dropdown':
            for fig in current_figures:
                # do not process the dots figure, which is the last one. The rest (first ones) are curves
                for curve in fig['data'][:-1]:
                    curve['line']['color'] = curves_color
        elif input_id == 'curves-transparency-slider':
            for fig in current_figures:
                # do not process the dots figure, which is the last one. The rest (first ones) are curves
                for curve in fig['data'][:-1]:
                    curve['opacity'] = curves_transparency
        elif input_id == 'time-range-slider':
            for fig in current_figures:
                # process the dots figure, which is the last one.
                mask = (df['timestamp'] >= time_range[0] * 1e9) & (df['timestamp'] < time_range[1] * 1e9)
                filt_df = df.loc[mask]
                fig['data'][-1]['x'] = filt_df['bw']
                fig['data'][-1]['y'] = filt_df['lat']
                if markers_color == 'stress_score':
                    fig['data'][-1]['marker']['color'] = filt_df['stress_score']
        elif input_id == 'markers-color-dropdown':
            for fig in current_figures:
                if markers_color == 'stress_score':
                    mask = (df['timestamp'] >= time_range[0] * 1e9) & (df['timestamp'] < time_range[1] * 1e9)
                    filt_df = df.loc[mask]
                    fig['data'][-1]['marker']['color'] = filt_df['stress_score']
                else:
                    fig['data'][-1]['marker']['color'] = markers_color
        elif input_id == 'markers-transparency-slider':
            for fig in current_figures:
                fig['data'][-1]['marker']['opacity'] = markers_transparency
        
        return current_figures