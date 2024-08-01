import os
import numpy as np
import plotly.express as px
from plotly.subplots import make_subplots


def get_color_bar(labels, stress_score_config, font_size=25):
    # if toggled_time:
    #     return {
    #         'colorbar': {'title': labels['timestamp'],},
    #         'colorscale': 'burg',
    #     }
    return {
        'colorbar': {
            'title': labels['stress_score'],
            'title_font': {'size': font_size},
            'tickfont': {'size': font_size}, 
                     },
        'colorscale': stress_score_config['colorscale'],
        'cmin': stress_score_config['min'],
        'cmax': stress_score_config['max'],
    }


def filter_df(df, node_name=None, i_socket=None, i_mc=None, time_range=(), bw_range=(), lat_range=()):
    mask = np.ones(len(df), dtype=bool)
    if node_name is not None:
        mask &= df['node_name'] == node_name
    if i_socket is not None:
        mask &= df['socket'] == int(i_socket)
    if i_mc is not None:
        mask &= df['mc'] == int(i_mc)
    if len(time_range):
        mask &= (df['timestamp'] >= time_range[0]*1e9) & (df['timestamp'] < time_range[1]*1e9)
    if len(bw_range):
        mask &= (df['bw'] >= bw_range[0]) & (df['bw'] < bw_range[1])
    if len(lat_range):
        mask &= (df['lat'] >= lat_range[0]) & (df['lat'] < lat_range[1])
    return df[mask]


def get_graph_fig(df, curves, curves_color, curves_transparency, markers_color, markers_transparency,
                  graph_title, x_title, y_title, stress_score_scale=None, color_bar=None, font_size=25, showAll=False):
    fig = make_subplots(rows=1, cols=1)

    try:
        fig = get_curves_fig(curves, fig, curves_color, curves_transparency, font_size, showAll)

        # Plot application bw-lat dots
        dots_fig = get_application_memory_dots_fig(df, markers_color, stress_score_scale, markers_transparency)
        if dots_fig is None:
            return None
        fig.add_trace(dots_fig.data[0])

        fig.update_xaxes(title=x_title, title_font=dict(size=font_size))
        fig.update_yaxes(title=y_title, title_font=dict(size=font_size))
        if color_bar is not None:
            fig.update_coloraxes(**color_bar)

        # Update the layout with a title
        fig.update_layout(
            title={
                'text': graph_title,
                'font': {
                    'size': font_size,
                    'color': 'black',
                    'family': 'Arial, sans-serif',
                },
                'x':0.5,
                'xanchor': 'center',
            }
        )     

        # These liens ensure the background is white, and there is a box around the plot   
        fig.update_layout(
            paper_bgcolor='white', 
            plot_bgcolor='white',  
            xaxis=dict(
                showgrid=False,          
                linecolor='black',       
                tickcolor='black',       
                tickfont=dict(size=font_size),
                mirror=True
            ),
            yaxis=dict(
                showgrid=False,          
                linecolor='black',       
                tickcolor='black',       
                tickfont=dict(size=font_size),
                mirror=True
            ),

        )
        return fig
    except Exception:
        fig.add_annotation(
                text="Something went wrong<br><sup>Please reload the page</sup>",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
                font=dict(
                    size=font_size,
                    color="black",
                    family="Arial, sans-serif",
                ),
            )
        return fig


def get_curves(curves_path, cpu_freq):
    curves = {}
    # Load and process curves
    for curve_file in os.listdir(curves_path):
    # for curve_file in os.listdir(curves_dir):
        if 'bwlat_' in curve_file:
            # with open( os.path.join(curves_dir, curve_file) ) as f:
            with open( os.path.join(curves_path, curve_file) ) as f:
                bws = []
                lats = []
                for line in f.readlines():
                    sp = line.split()
                    # bw MB/s to GB/s
                    bws.append(float(sp[0]) / 1000)
                    lats.append(float(sp[1]))
                # Add special case of bw = 0 (then latency is the minimum recorded).
                # TODO it'd be better to use the Curve module instead of hardcoding a bw of 0 to the lowest latency (this behavior might change at some point)
                bws.append(0)
                lats.append(lats[-1])
                read_ratio = int(curve_file.split('_')[1].replace('.txt', ''))
                curves[100 - read_ratio] = {
                    'bandwidths': bws[::-1],
                    'latencies': np.array(lats[::-1]) / cpu_freq
                }
    return curves


def get_curves_fig(curves, fig, color='black', transparency=1, font_size=25, showAll=False):
    if showAll:
        # Take the curve write ratios (keys) in descending order
        rang = sorted(curves.keys(), reverse=True)
    else:
        # Show N curves only
        n_curves_to_show = 5
        step = int(len(curves) / n_curves_to_show)
        rang = sorted([list(curves.keys())[i] for i in range(0, len(curves)-1, step)], reverse=True)

    curve_opacity_step = transparency / len(curves)
    for i, w_ratio in enumerate(rang):
        # This chooses which values are shown in the legend.
        # Right now the legend includes the first and last curve.
        show_in_legend = ((i == 0) or (i == len(rang) - 1)) and showAll

        curve_fig = px.line(x=curves[w_ratio]['bandwidths'], y=curves[w_ratio]['latencies'], color_discrete_sequence=[color])
        curve_transparency = transparency - curve_opacity_step * i
        curve_fig.update_traces(
            hovertemplate="Bandwidth (BW): %{x}<br>Latency: %{y}<br>Write Ratio (WR): " + str(w_ratio) + "%<extra></extra>",
            opacity=max(0, curve_transparency),
            showlegend=show_in_legend,
            name=f'Rd:Wr {100-w_ratio}:{w_ratio}',
        )
        curve_text = f'{w_ratio}%' if curve_transparency > 0 else ''
        fig.add_trace(curve_fig.data[0])
        if not showAll:
            fig.add_annotation(x=curves[w_ratio]['bandwidths'][-1], y=curves[w_ratio]['latencies'][-1] + 15,
                            text=curve_text, showarrow=False, arrowhead=1)

    if showAll:
        fig.update_layout(
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01,
                orientation='h',
                font=dict(
                    size=font_size
                ),
                bordercolor="black",
                borderwidth=2     
            ),
        )
    
    return fig


def get_application_memory_dots_fig(df, color, stress_score_scale=None, opacity=0.01):
    if 'bw' not in df.columns or 'lat' not in df.columns:
        print('Error: bw or lat not in df.columns')
        return None

    if color == 'stress_score':
        dots_fig = px.scatter(df, x='bw', y='lat', color='stress_score', color_continuous_scale=stress_score_scale, )
    else:
        dots_fig = px.scatter(df, x='bw', y='lat', color_discrete_sequence=[color])

    marker_opts = dict(size=14, opacity=opacity)
    dots_fig.update_traces(marker=marker_opts)
    return dots_fig