import os
import json
import base64
import numpy as np
import dash
from dash import html, Input, Output, State, callback_context
from dash.exceptions import PreventUpdate

import curve_utils
import utils
import roofline
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

def register_callbacks(app, system_data, df, df_overview, curves, config, system_arch, trace_file, labels, stress_score_config, max_elements=None, expert=False):

    # toggle sidebar, showing it when the curves tab is selected and hidding it otherwise
    @app.callback(
        Output("sidebar", "is_open"),
        Input("tabs", "active_tab"),
    )
    def toggle_sidebar(active_tab):
        return active_tab != "summary-tab"
    
    # Hide the curve specific options when the roofline tab is active. 
    @app.callback(
        Output(f'curves-color-dropdown-section', 'style'),
        Output(f'curves-transparency-section', 'style'),
        Input("tabs", "active_tab"),
    )
    def hide_curves_sidebar_options(active_tab):
        # Static number of outputs. If we add more options, we need to update this number
        num_outputs = 2
        return [{'display': 'none'}]*num_outputs if active_tab == "mem-roofline-tab" or active_tab == "single-roofline-tab" else [{}]*num_outputs

    # Hide the roofline specific options when the curves tab or overview tab is active.
    @app.callback(
        Output(f'test-mem-id', 'style'),
        Input("tabs", "active_tab"),
    )
    def hide_memory_sidebar_options(active_tab):
        return {'display': 'none'} if active_tab == "curves-tab" or active_tab == "app-overview-tab" else {}

    # Hide the overview tab specific options when the tab is not active.
    @app.callback(
        Output(f'sampling-section', 'style'),
        Input("tabs", "active_tab"),
    )
    def hide_only_overview_sidebar_options(active_tab):
        return {'display': 'none'} if active_tab == "curves-tab" or active_tab == "mem-roofline-tab" or active_tab == "single-roofline-tab" else {}

    # There is no node selection in the overview tab. This is why it's hidden when the tab is active.
    @app.callback(
        Output(f'node-selection-section', 'style'),
        Input("tabs", "active_tab"),
    )
    def hide_overview_sidebar_options(active_tab):
        return {'display': 'none'} if active_tab == "app-overview-tab" or "single-roofline-tab" else {}


    # Since the expert mode requires two differente callback definitions, but the same export to pdf function, we declare it separately
    def generic_pdf_export(n, selected_nodes, figures):
        pdf_string = pdf_gen.generate_pdf(df, config, system_arch, selected_nodes, figures, expert)
        pdf_base64 = base64.b64encode(pdf_string).decode('utf-8')
        return dict(content=pdf_base64, filename="my_report.pdf", type="application/pdf", base64=True)
    
    if expert:
        # If expert mode is enabled, we need to add the memory roofline and curves figures to the pdf export
        @app.callback(
            Output("download-pdf", "data"),
            Input("btn-pdf-export", "n_clicks"),
            State('node-selection-dropdown', 'value'),
            State('overview-chart', 'figure'),
            apply_to_hierarchy(lambda n, s, m: State(f'curves-node-{n}-socket-{s}-mc-{m}', 'figure'), system_arch),
            apply_to_hierarchy(lambda n, s, m: State(f'mem-roofline-node-{n}-socket-{s}-mc-{m}', 'figure'), system_arch),
            prevent_initial_call=True,
        )
        def export_to_pdf(n, selected_nodes, *figures):
            return generic_pdf_export(n, selected_nodes, figures)
    else:
        # If expert mode is disabled, we only need the overview figures to the pdf export
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
        # If expert is enabled, we need to add the logic of the node selection for the curves.
        @app.callback(
            # The style attribute is used to hide the container of the curves of the nodes that are not selected
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
        # If expert is enabled, we want the curves and rooflines to be created and instanciated
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
            # Define the Output components dynamically based on the system architecture
            apply_to_hierarchy(lambda n, s, m: Output(f'mem-roofline-node-{n}-socket-{s}-mc-{m}', 'figure'), system_arch),
            State('node-selection-dropdown', 'value'),
            Input('time-range-slider', 'value'),
            Input('markers-color-dropdown', 'value'),
            Input('markers-transparency-slider', 'value'),
            apply_to_hierarchy(lambda n, s, m: State(f'mem-roofline-node-{n}-socket-{s}-mc-{m}', 'figure'), system_arch),
            apply_to_hierarchy(lambda n, s, m: State(f'mem-roofline-node-{n}-socket-{s}-mc-{m}-store', 'data'), system_arch),
            prevent_initial_call=True,
        )
        def update_memory_roofline_graphs(selected_nodes, time_range, markers_color, markers_transparency, *states):

            # Get the figures and metadata from the states
            halves = len(states) // 2
            current_figures = states[:halves]
            figs_metadata = states[halves+1:]

            #TODO: Read the correct BW
            cache_bw = curve_utils.get_cache_bandwidth(curves)

            # Get the peak bandwidth
            peak_bw_gbs = max([cache_bw[i]['value'] for i in range(len(cache_bw))])

            # TODO: Define peak flops (peak_flopss) - Not implemented in the provided code
            peak_flopss = 11150000

            # Handle callback logic. This is triggered by a single input.
            if len(callback_context.triggered) > 1:
                figures = []
                for node_name, sockets in system_arch.items():
                    # TODO: the filtering of the DF should not be in curve_utils
                    df_node = utils.filter_df(df, node_name, time_range=time_range)
                    for i_socket, mcs in sockets.items():
                        df_socket = utils.filter_df(df_node, i_socket=i_socket)
                        for _, id_mc in enumerate(mcs):
                            # Filter the dataframe to only include the selected node, socket and MC
                            filt_df = utils.filter_df(df_socket, i_mc=id_mc)
                            graph_title = f'Memory channel {id_mc}' if len(mcs) > 1 else f'Socket {i_socket}'
                            fig = roofline.plotCARM(filt_df, peak_bw_gbs, peak_flopss, cache_bw, markers_color,markers_transparency, labels, stress_score_config, graph_title=graph_title)
                            figures.append(fig)

                return figures
            
            # Get the ID of the input that triggered the callback
            input_id = callback_context.triggered[0]['prop_id'].split('.')[0]

            if input_id == 'markers-color-dropdown':
                for fig in current_figures:
                    if markers_color == 'stress_score':
                        mask = (df['timestamp'] >= time_range[0] * 1e9) & (df['timestamp'] < time_range[1] * 1e9)
                        filt_df = df.loc[mask]
                        fig['data'][0]['marker']['color'] = filt_df['stress_score']
                        fig['data'][0]['hovertemplate'] = '<b>Stress score</b>: %{marker.color:.2f}<br><b>Operational Intensity</b>: %{x:.2f} (FLOPS/Byte)<br><b>Performance</b>: %{y:.2f} (GFLOPS/s)<br><b>Bandwidth</b>: %{customdata[3]:.2f} GB/s<br><b>Latency</b>: %{customdata[4]:.2f} ns<br><b>Timestamp</b>: %{text}<br><b>Node</b>: %{customdata[0]}<br><b>Socket</b>: %{customdata[1]}<br><b>MC</b>: %{customdata[2]}<extra></extra>'
                        fig['data'][-1]['visible'] = True
                    else:
                        fig['data'][0]['marker']['color'] = markers_color
                        fig['data'][0]['hovertemplate'] = '<b>Operational Intensity</b>: %{x:.2f} (FLOPS/Byte)<br><b>Performance</b>: %{y:.2f} (GFLOPS/s)<br><b>Bandwidth</b>: %{customdata[3]:.2f} GB/s<br><b>Latency</b>: %{customdata[4]:.2f} ns<br><b>Timestamp</b>: %{text}<br><b>Node</b>: %{customdata[0]}<br><b>Socket</b>: %{customdata[1]}<br><b>MC</b>: %{customdata[2]}<extra></extra>'
                        fig['data'][-1]['visible'] = False
            elif input_id == 'time-range-slider':
                for metadata, fig in zip(figs_metadata, current_figures):
                    mask = (df['timestamp'] >= time_range[0] * 1e9) & (df['timestamp'] < time_range[1] * 1e9)
                    filt_df = utils.filter_df(df, metadata['node_name'], metadata['socket'], time_range=time_range)

                    # TODO: Implement logic for handling time-range-slider input - Not fully implemented in the provided code

                    if markers_color == 'stress_score':
                        fig['data'][0]['marker']['color'] = filt_df['stress_score']
            elif input_id == 'markers-transparency-slider':
                for fig in current_figures:
                    fig['data'][0]['marker']['opacity'] = markers_transparency


            return current_figures


    @app.callback(
        Output('single-roofline-chart', 'figure'),
        Input('time-range-slider', 'value'),
        Input('roofline-opts-checklist', 'value'),
        Input('region-transparency-slider', 'value'),
        State('single-roofline-chart', 'figure')
    )
    def update_single_roofline_chart(time_range, roofline_opts, region_transparency, current_figure):
        # Get the figures and metadata from the states

        # input_id = callback_context.triggered[0]['prop_id'].split('.')[0]
        
        #TODO: Read the correct BW
        cache_bw = system_data['bw']

        # Get the peak bandwidth
        peak_bw_gbs = max([cache_bw[i]['value'] for i in range(len(cache_bw))])

        # TODO: Define peak flops (peak_flopss) - Not implemented in the provided code
        peak_flopss = system_data["fp"]

        
        graph_title = "Cache Aware Roofline Model"
        fig = roofline.singleRoofline(df, peak_bw_gbs, peak_flopss, cache_bw, roofline_opts, region_transparency, labels, stress_score_config, graph_title=graph_title)
        
        return fig
    


    @app.callback(
        Output('overview-chart', 'figure'),
        Input('sampling-range-slider', 'value'),
        Input('curves-color-dropdown', 'value'),
        Input('curves-transparency-slider', 'value'),
        Input('time-range-slider', 'value'),
        Input('markers-color-dropdown', 'value'),
        Input('markers-transparency-slider', 'value'),
        State('overview-chart', 'figure'),
    )
    def update_overview_graph(sample_range, curves_color, curves_transparency, time_range, markers_color, markers_transparency, *states):
        
        # Get the current state of the overview chart
        overview_fig = states[0]

        # Get the ID of the input that triggered the callback
        input_id = callback_context.triggered[0]['prop_id'].split('.')[0]
        
        # Handle callback logic when triggered by multiple inputs or the sampling range slider
        if len(callback_context.triggered) > 1 or input_id == 'sampling-range-slider':
            # Check if the sample_range is not zero
            if sample_range[0] != 0:
                # Sample the dataframe to the specified sample range
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
            # Apply a mask to filter data within the specified time range
            mask = (df_overview['timestamp'] >= time_range[0] * 1e9) & (df_overview['timestamp'] < time_range[1] * 1e9)
            
            # Check if the sample_range is not zero
            if sample_range != 0:
                # Sample the dataframe to the specified sample range
                df_copy = df_overview[mask].copy()
                df_copy['timestamp'] = df_copy['timestamp'] // (sample_range[0] * 10 ** 9)
                result_df = df_copy.groupby('timestamp', as_index=False).apply(
                    lambda x: x.loc[x['stress_score'].idxmax()]).reset_index(drop=True)
            else:
                result_df = df_overview[mask]
            
            # Update the x, y, and marker color of the last data trace in the overview figure
            overview_fig['data'][-1]['x'] = result_df['bw']
            overview_fig['data'][-1]['y'] = result_df['lat']
            if markers_color == 'stress_score':
                overview_fig['data'][-1]['marker']['color'] = result_df['stress_score']

            # update the bw balance
        elif input_id == 'markers-color-dropdown':
            if markers_color == 'stress_score':
                # Apply a mask to filter data within the specified time range
                mask = (df_overview['timestamp'] >= time_range[0] * 1e9) & (df_overview['timestamp'] < time_range[1] * 1e9)
                filt_df = df_overview.loc[mask]
                overview_fig['data'][-1]['marker']['color'] = filt_df['stress_score']
            else:
                overview_fig['data'][-1]['marker']['color'] = markers_color
        elif input_id == 'markers-transparency-slider':
            overview_fig['data'][-1]['marker']['opacity'] = markers_transparency
        
        return overview_fig
