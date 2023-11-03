import os
import json
import base64
import numpy as np
import dash
from dash import html, Input, Output, State, callback_context
from dash.exceptions import PreventUpdate

import curve_utils
import utils
import overview
import pdf_gen

def apply_to_hierarchy(func, system_arch):
    # apply func to each node, socket and mc
    results = []
    for node_name, sockets in system_arch.items():
        for i_socket, mcs in sockets.items():
            for id_mc in mcs:
                results.append(func(node_name, i_socket, id_mc))
    return results

def replace_after_char(s, char, replacement):
    """ Replaces everything after the first occurence of a character with a replacement string """
    # Find the position of the character
    index = s.find(char)

    # If character is not found, return the original string
    if index == -1:
        return s

    # Replace everything after the character with the replacement string
    return s[:index + 1] + replacement

def register_callbacks(app, df, df_overview, curves, config, system_arch, trace_file, labels, stress_score_config, max_elements=None, expert=False):

    # toggle sidebar, showing it when the curves tab is selected and hidding it otherwise
    @app.callback(
        Output("sidebar", "is_open"),
        Input("tabs", "active_tab"),
    )
    def toggle_sidebar(active_tab):
        return active_tab != "summary-tab"

    @app.callback(
        Output(f'curves-color-dropdown-section', 'style'),
        Output(f'curves-transparency-section', 'style'),
        Input("tabs", "active_tab"),
    )
    def hide_curves_sidebar_options(active_tab):
        num_outputs = 2
        return [{'display': 'none'}]*num_outputs if active_tab == "app-overview-tab" else [{}]*num_outputs

    @app.callback(
        Output(f'sampling-section', 'style'),
        Input("tabs", "active_tab"),
    )
    def hide_only_overview_sidebar_options(active_tab):
        return {'display': 'none'} if active_tab == "curves-tab" else {}

    @app.callback(
        Output(f'node-selection-section', 'style'),
        Input("tabs", "active_tab"),
    )
    def hide_overview_sidebar_options(active_tab):
        return {'display': 'none'} if active_tab == "app-overview-tab" else {}


    def generic_pdf_export(n, selected_nodes, figures):
        pdf_string = pdf_gen.generate_pdf(df, config, system_arch, selected_nodes, figures, expert)
        pdf_base64 = base64.b64encode(pdf_string).decode('utf-8')
        return dict(content=pdf_base64, filename="my_report.pdf", type="application/pdf", base64=True)

    if expert:
        @app.callback(
            Output("download-pdf", "data"),
            Input("btn-pdf-export", "n_clicks"),
            State('node-selection-dropdown', 'value'),
            State('overview-chart', 'figure'),
            apply_to_hierarchy(lambda n, s, m: State(f'curves-node-{n}-socket-{s}-mc-{m}', 'figure'), system_arch),
            prevent_initial_call=True,
        )
        def export_to_pdf(n, selected_nodes, *figures):
            return generic_pdf_export(n, selected_nodes, figures)
    else:
        @app.callback(
            Output("download-pdf", "data"),
            Input("btn-pdf-export", "n_clicks"),
            State('node-selection-dropdown', 'value'),
            State('overview-chart', 'figure'),
            prevent_initial_call=True,
        )
        def export_to_pdf(n, selected_nodes, *figures):
            return generic_pdf_export(n, selected_nodes, figures)

    # we need all the elements as outputs for updating them in case of loading a json file
    # if a json file is not loaded, the callback has still to return the real values
    # for plotting the graphs, so that's why need the States here
    @app.callback(
        Output('node-selection-dropdown', 'value'),
        Output('curves-color-dropdown', 'value'),
        Output('curves-transparency-slider', 'value'),
        Output('time-range-slider', 'value'),
        Output('markers-color-dropdown', 'value'),
        Output('markers-transparency-slider', 'value'),
        Input('upload-config', 'contents'),
        State('node-selection-dropdown', 'value'),
        State('curves-color-dropdown', 'value'),
        State('curves-transparency-slider', 'value'),
        State('time-range-slider', 'value'),
        State('markers-color-dropdown', 'value'),
        State('markers-transparency-slider', 'value'),
        # prevent_initial_call=True,
    )
    def load_config(contents, selected_nodes, curves_color, curves_transparency, time_range, 
                    markers_color, markers_transparency):
        if contents is None:
            return selected_nodes, curves_color, curves_transparency, time_range, markers_color, markers_transparency
        
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        try:
            if 'json' in content_type:
                # assume that the user uploaded a JSON file
                json_file = json.loads(decoded)
                return_order = ['selected_nodes', 'curves_color', 'curves_transparency', 'time_range',
                                'markers_color', 'markers_transparency']
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
        State('markers-color-dropdown', 'value'),
        State('markers-transparency-slider', 'value'),
        # prevent_initial_call=True,
    )
    def save_config(save_n_clicks, selected_nodes, curves_color, curves_transparency, time_range, 
                    markers_color, markers_transparency):
        if save_n_clicks is None or save_n_clicks == 0:
            raise PreventUpdate

        # Generate the configuration data
        config_json = json.dumps({
            'curves_color': curves_color,
            'curves_transparency': curves_transparency,
            'time_range': time_range,
            'markers_color': markers_color,
            'markers_transparency': markers_transparency,
            'selected_nodes': selected_nodes,
        }, indent=2)

        # You can choose a default filename, but the user will still
        # have the option to choose their own filename in the download dialog
        # basename gets the filename with the extension, and splitext removes the extension
        filename = os.path.splitext(os.path.basename(trace_file))[0] + '.dash.config.json'

        return dict(content=config_json, filename=filename)

    if expert:
        @app.callback(
            [Output(f'curves-node-{node_name}-container', 'style') for node_name in system_arch.keys()],
            Input('node-selection-dropdown', 'value'),
            prevent_initial_call=True,
        )
        def show_hide_node(selected_nodes):
            # TODO the problem with this approach is that these blocked rows will still be processed in update_chart
            if selected_nodes is None:
                raise PreventUpdate
            return [{'display': 'none'} if node_name not in selected_nodes else {} for node_name in system_arch.keys()]
    
    if expert:
        #TODO: Passar a modo expert / normal
        @app.callback(
            apply_to_hierarchy(lambda n, s, m: Output(f'curves-node-{n}-socket-{s}-mc-{m}', 'figure'), system_arch),
            apply_to_hierarchy(lambda n, s, m: Output(f'curves-node-{n}-socket-{s}-mc-{m}-bw-balance', 'children'), system_arch),
            State('node-selection-dropdown', 'value'),
            Input('curves-color-dropdown', 'value'),
            Input('curves-transparency-slider', 'value'),
            Input('time-range-slider', 'value'),
            Input('markers-color-dropdown', 'value'),
            Input('markers-transparency-slider', 'value'),
            apply_to_hierarchy(lambda n, s, m: State(f'curves-node-{n}-socket-{s}-mc-{m}', 'figure'), system_arch),
            apply_to_hierarchy(lambda n, s, m: State(f'curves-node-{n}-socket-{s}-mc-{m}-store', 'data'), system_arch),
            apply_to_hierarchy(lambda n, s, m: State(f'curves-node-{n}-socket-{s}-mc-{m}-bw-balance', 'children'), system_arch),
            prevent_initial_call=True,
        )
        def update_curve_graphs(selected_nodes, curves_color, curves_transparency, time_range,
                                markers_color, markers_transparency, *states):
            third = len(states) // 3
            current_figures = states[:third]
            figs_metadata = states[third:third*2]
            bw_balances = states[third*2:]

            if len(callback_context.triggered) > 1:
                # Reprocess all charts. This can happen in multiple circumstances:
                # - Initial call (all inputs are passed as context)
                # - Loading a new config file (all inputs are passed as context)
                color_bar = None
                if markers_color == 'stress_score':
                    color_bar = curve_utils.get_color_bar(labels, stress_score_config)

                figures = []
                new_bw_balances = []
                for node_name, sockets in system_arch.items():
                    # if node_name not in selected_nodes:
                    #     figures.append(dash.no_update)
                    #     new_bw_balances.append(dash.no_update)
                    #     continue
                    df_node = curve_utils.filter_df(df, node_name, time_range=time_range)
                    bw_per_socket = df_node.groupby('socket')['bw'].mean()
                    for i_socket, mcs in sockets.items():
                        df_socket = curve_utils.filter_df(df_node, i_socket=i_socket)
                        if len(mcs) > 1:
                            bw_per_mc = df_socket.groupby('mc')['bw'].mean()
                        for k, id_mc in enumerate(mcs):
                            # Filter the dataframe to only include the selected node, socket and MC
                            filt_df = curve_utils.filter_df(df_socket, i_mc=id_mc)
                            if len(mcs) > 1:
                                bw_balance = filt_df['bw'].mean() * 100 / bw_per_mc.sum()
                            else:
                                bw_balance = filt_df['bw'].mean() * 100 / bw_per_socket.sum()
                            new_bw_balances.append(replace_after_char(bw_balances[k], ':', f' {bw_balance:.1f}%'))
                            graph_title = f'Memory channel {id_mc}' if len(mcs) > 1 else f'Socket {i_socket}'
                            fig = curve_utils.get_graph_fig(filt_df, curves, curves_color, curves_transparency, markers_color, markers_transparency,
                                                            graph_title, labels['bw'], labels['lat'], stress_score_config['colorscale'], color_bar)
                            figures.append(fig)
                return tuple(np.append(figures, new_bw_balances))

            new_bw_balances = [dash.no_update for _ in bw_balances]
            input_id = callback_context.triggered[0]['prop_id'].split('.')[0]

            # Handle callback logic. This is triggered by a single input.
            if input_id == 'curves-color-dropdown':
                for fig in current_figures:
                    # process curves figures, which are all but the last one.
                    for curve in fig['data'][:-1]:
                        curve['line']['color'] = curves_color
            elif input_id == 'curves-transparency-slider':
                for fig in current_figures:
                    # process curves figures, which are all but the last one.
                    for curve in fig['data'][:-1]:
                        curve['opacity'] = curves_transparency
            elif input_id == 'time-range-slider':
                # update figures
                for metadata, fig in zip(figs_metadata, current_figures):
                    # process the dots figure, which is the last one.
                    mask = (df['timestamp'] >= time_range[0] * 1e9) & (df['timestamp'] < time_range[1] * 1e9)
                    filt_df = curve_utils.filter_df(df, metadata['node_name'], metadata['socket'],
                                            metadata['mc'], time_range=time_range)
                    fig['data'][-1]['x'] = filt_df['bw']
                    fig['data'][-1]['y'] = filt_df['lat']
                    if markers_color == 'stress_score':
                        fig['data'][-1]['marker']['color'] = filt_df['stress_score']

                # update the bw balance
                new_bw_balances = []
                for node_name, sockets in system_arch.items():
                    # if node_name not in selected_nodes:
                    #     new_bw_balances.append(dash.no_update)
                    #     continue
                    df_node = curve_utils.filter_df(df, node_name, time_range=time_range)
                    bw_per_socket = df_node.groupby('socket')['bw'].mean()
                    for i_socket, mcs in sockets.items():
                        df_socket = curve_utils.filter_df(df_node, i_socket=i_socket)
                        if len(mcs) > 1:
                            bw_per_mc = df_socket.groupby('mc')['bw'].mean()
                        for k, id_mc in enumerate(mcs):
                            # Filter the dataframe to only include the selected node, socket and MC
                            filt_df = curve_utils.filter_df(df_socket, i_mc=id_mc)
                            if len(mcs) > 1:
                                bw_balance = filt_df['bw'].mean() * 100 / bw_per_mc.sum()
                            else:
                                bw_balance = filt_df['bw'].mean() * 100 / bw_per_socket.sum()
                            new_bw_balances.append(replace_after_char(bw_balances[k], ':', f' {bw_balance:.1f}%'))
            elif input_id == 'markers-color-dropdown':
                for fig in current_figures:
                    # process the dots figure, which is the last one.
                    if markers_color == 'stress_score':
                        mask = (df['timestamp'] >= time_range[0] * 1e9) & (df['timestamp'] < time_range[1] * 1e9)
                        filt_df = df.loc[mask]
                        fig['data'][-1]['marker']['color'] = filt_df['stress_score']
                    else:
                        fig['data'][-1]['marker']['color'] = markers_color
            elif input_id == 'markers-transparency-slider':
                for fig in current_figures:
                    # process the dots figure, which is the last one.
                    fig['data'][-1]['marker']['opacity'] = markers_transparency

            return tuple(np.append(current_figures, new_bw_balances))

    @app.callback(
        Output('overview-chart', 'figure'),
        Input('sampling-range-slider', 'value'),
        Input('curves-color-dropdown', 'value'),
        Input('curves-transparency-slider', 'value'),
        Input('time-range-slider', 'value'),
        Input('markers-color-dropdown', 'value'),
        Input('markers-transparency-slider', 'value'),
        State('overview-chart', 'figure'),
        # prevent_initial_call=True,
    )
    def update_overview_graph(sample_range, curves_color, curves_transparency, time_range, markers_color, markers_transparency, *states):

        overview_fig = states[0]

        input_id = callback_context.triggered[0]['prop_id'].split('.')[0]

        if len(callback_context.triggered) > 1 or input_id == 'sampling-range-slider':
            if sample_range[0] != 0:
                df_copy = df_overview.copy()
                df_copy['timestamp'] = df_copy['timestamp'] // (sample_range[0] * 10 ** 9)
                result_df = df_copy.groupby('timestamp', as_index=False).apply(
                    lambda x: x.loc[x['stress_score'].idxmax()]).reset_index(drop=True)
            else:
                result_df = df_overview

            if markers_color == 'stress_score':
                color_bar = curve_utils.get_color_bar(labels, stress_score_config)

            graph_title = 'Application Curves'
            overview_fig = curve_utils.get_graph_fig(result_df, curves, curves_color, curves_transparency, markers_color, markers_transparency,
                                            graph_title, labels['bw'], labels['lat'], stress_score_config['colorscale'], color_bar)

            return overview_fig


        # Handle callback logic. This is triggered by a single input.
        if input_id == 'curves-color-dropdown':
            for curve in overview_fig['data'][:-1]:
                curve['line']['color'] = curves_color
        elif input_id == 'curves-transparency-slider':
            for curve in overview_fig['data'][:-1]:
                curve['opacity'] = curves_transparency
        elif input_id == 'time-range-slider':

            mask = (df_overview['timestamp'] >= time_range[0] * 1e9) & (df_overview['timestamp'] < time_range[1] * 1e9)

            if sample_range != 0:
                df_copy = df_overview[mask].copy()
                df_copy['timestamp'] = df_copy['timestamp'] // (sample_range[0] * 10 ** 9)
                result_df = df_copy.groupby('timestamp', as_index=False).apply(
                    lambda x: x.loc[x['stress_score'].idxmax()]).reset_index(drop=True)
            else:
                result_df = df_overview[mask]

            overview_fig['data'][-1]['x'] = result_df['bw']
            overview_fig['data'][-1]['y'] = result_df['lat']
            if markers_color == 'stress_score':
                overview_fig['data'][-1]['marker']['color'] = result_df['stress_score']

        elif input_id == 'markers-color-dropdown':
            if markers_color == 'stress_score':
                mask = (df_overview['timestamp'] >= time_range[0] * 1e9) & (df_overview['timestamp'] < time_range[1] * 1e9)
                filt_df = df_overview.loc[mask]
                overview_fig['data'][-1]['marker']['color'] = filt_df['stress_score']
            else:
                overview_fig['data'][-1]['marker']['color'] = markers_color
        elif input_id == 'markers-transparency-slider':
            overview_fig['data'][-1]['marker']['opacity'] = markers_transparency

        return overview_fig
