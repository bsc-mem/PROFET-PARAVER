import colorsys
import os

import numpy as np
import pandas as pd  # Ensure pandas is imported
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def get_color_bar(labels, stress_score_config, font_size=25):
    return {
        "colorbar": {
            "title": labels["stress_score"],
            "title_font": {"size": font_size},
            "tickfont": {"size": font_size},
        },
        "colorscale": stress_score_config["colorscale"],
        "cmin": stress_score_config["min"],
        "cmax": stress_score_config["max"],
    }


def filter_df(
    df,
    node_name=None,
    i_socket=None,
    i_mc=None,
    time_range=(),
    bw_range=(),
    lat_range=(),
):
    mask = np.ones(len(df), dtype=bool)
    if node_name is not None:
        mask &= df["node_name"] == node_name
    if i_socket is not None:
        mask &= df["socket"] == int(i_socket)
    if i_mc is not None:
        mask &= df["mc"] == int(i_mc)
    if len(time_range):
        mask &= (df["timestamp"] >= time_range[0] * 1e9) & (
            df["timestamp"] < time_range[1] * 1e9
        )
    if len(bw_range):
        mask &= (df["bw"] >= bw_range[0]) & (df["bw"] < bw_range[1])
    if len(lat_range):
        mask &= (df["lat"] >= lat_range[0]) & (df["lat"] < lat_range[1])
    return df[mask]


def get_graph_fig(
    df,
    curves,
    curves_color,
    curves_transparency,
    markers_color,
    markers_transparency,
    graph_title,
    x_title,
    y_title,
    stress_score_scale=None,
    color_bar=None,
    font_size=25,
    showAll=False,
    showRdWrBar=False,
):
    fig = make_subplots(rows=1, cols=1)

    try:
        fig = get_curves_fig(
            curves,
            fig,
            curves_color,
            curves_transparency,
            font_size,
            showAll,
            showRdWrBar,
        )

        # Plot application bw-lat dots
        dots_fig = get_application_memory_dots_fig(
            df, markers_color, stress_score_scale, markers_transparency
        )
        if dots_fig is None:
            return None
        fig.add_trace(dots_fig.data[0])

        fig.update_xaxes(title=x_title, title_font=dict(size=font_size))
        fig.update_yaxes(title=y_title, title_font=dict(size=font_size))
        if color_bar is not None:
            fig.update_coloraxes(**color_bar)

        # Update the layout with a title
        fig.update_layout(
            margin=dict(t=50),
            title={
                "text": graph_title,
                "font": {
                    "size": font_size,
                    "color": "black",
                    "family": "Arial, sans-serif",
                },
                "x": 0.5,
                "xanchor": "center",
            },
        )

        # Ensure the background is white, and there is a box around the plot
        fig.update_layout(
            paper_bgcolor="white",
            plot_bgcolor="white",
            xaxis=dict(
                showgrid=False,
                linecolor="black",
                tickcolor="black",
                tickfont=dict(size=font_size),
                mirror=True,
            ),
            yaxis=dict(
                showgrid=False,
                linecolor="black",
                tickcolor="black",
                tickfont=dict(size=font_size),
                mirror=True,
            ),
        )
        return fig
    except Exception as e:
        # print(f"Error in get_graph_fig: {e}")
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
        if "bwlat_" in curve_file:
            with open(os.path.join(curves_path, curve_file)) as f:
                bws = []
                lats = []
                read_ratio = int(curve_file.split("_")[1].replace(".txt", ""))
                for line in f.readlines():
                    sp = line.split()
                    # bw MB/s to GB/s
                    bws.append(float(sp[0]) / 1000)
                    lats.append(float(sp[1]))
                # Add special case of bw = 0 (then latency is the minimum recorded).
                bws.append(0)
                lats.append(lats[-1])
                curves[100 - read_ratio] = {
                    "bandwidths": bws[::-1],
                    "latencies": np.array(lats[::-1]) / cpu_freq,
                }
    return curves


def get_shades(color_name_or_hex, num_shades):
    # Custom dictionary mapping color names to hex codes
    color_mapping = {
        "black": "#000000",
        "red": "#FF0000",
        "green": "#008000",
        "blue": "#0000FF",
    }

    # Convert the color name to hex
    if color_name_or_hex.startswith("#"):
        hex_color = color_name_or_hex
    else:
        color_name = color_name_or_hex.lower()
        hex_color = color_mapping.get(color_name)
        if hex_color is None:
            raise ValueError(f"Color name '{color_name}' not recognized.")

    # Convert hex to RGB
    hex_color = hex_color.lstrip("#")
    r_base = int(hex_color[0:2], 16)
    g_base = int(hex_color[2:4], 16)
    b_base = int(hex_color[4:6], 16)

    # Generate shades from base color to white
    shades = []
    for i in range(num_shades):
        ratio = i / (num_shades - 1)
        r = int(r_base + (250 - r_base) * ratio)
        g = int(g_base + (250 - g_base) * ratio)
        b = int(b_base + (250 - b_base) * ratio)
        new_hex = "#{:02x}{:02x}{:02x}".format(r, g, b)
        shades.append(new_hex)
    return shades


def get_curves_fig(
    curves,
    fig,
    color="black",
    transparency=1,
    font_size=25,
    showAll=False,
    showRdWrBar=False,
):
    if showAll:
        # Take the curve write ratios (keys) in descending order
        rang = sorted(curves.keys(), reverse=True)
    else:
        # Show N curves only
        n_curves_to_show = 5
        step = max(1, int(len(curves) / n_curves_to_show))
        indices = list(range(0, len(curves), step))
        selected_keys = [list(sorted(curves.keys()))[i] for i in indices]
        rang = sorted(selected_keys, reverse=True)

    num_curves = len(rang)
    curve_opacity_step = (transparency - 0.1) / (num_curves)

    # Generate shades of the color

    shades = get_shades(color, num_curves)

    for i, (w_ratio, shade) in enumerate(zip(rang, shades)):
        # Determine if the legend should be shown
        show_in_legend = (
            ((i == 0) or (i == num_curves - 1)) and showAll and not showRdWrBar
        )

        curve_transparency = transparency - curve_opacity_step * i

        # Use go.Scatter to create the curve
        curve_fig = go.Scatter(
            x=curves[w_ratio]["bandwidths"],
            y=curves[w_ratio]["latencies"],
            mode="lines",
            line=dict(color=color),
            opacity=max(0, curve_transparency),
            hovertemplate="Bandwidth (BW): %{x}<br>Latency: %{y}<br>Write Ratio (WR): "
            + str(w_ratio)
            + "%<extra></extra>",
            showlegend=show_in_legend,
            name=f"Rd:Wr {100 - w_ratio}:{w_ratio}",
        )

        # Convert the trace to a dictionary before adding to the figure
        curve_trace_dict = curve_fig.to_plotly_json()
        fig.add_trace(curve_trace_dict)

        if not showAll:
            curve_text = f"{w_ratio}%" if curve_transparency > 0 else ""
            fig.add_annotation(
                x=curves[w_ratio]["bandwidths"][-1],
                y=curves[w_ratio]["latencies"][-1] + 15,
                text=curve_text,
                showarrow=False,
                arrowhead=1,
            )

    if showRdWrBar:
        # Prepare data for the color bar
        min_wr = min(rang)
        max_wr = max(rang)
        num_curves = len(rang)
        colorscale = [[(i / (num_curves - 1)), shade] for i, shade in enumerate(shades)]

        # Add an invisible trace to display the color bar
        colorbar_trace = go.Scatter(
            x=[None],
            y=[None],
            mode="markers",
            marker=dict(
                colorscale=colorscale,
                showscale=True,
                cmin=min_wr,
                cmax=max_wr,
                color=[min_wr, max_wr],
                colorbar=dict(
                    title="Write Ratio (Rd:Wr)",
                    title_font=dict(size=font_size - 4),
                    titleside="top",
                    tickfont=dict(size=font_size - 4),
                    tickvals=[min_wr, (min_wr + max_wr) / 2, max_wr],
                    ticktext=["0:100", "50:50", "100:0"],
                    orientation="h",
                    x=0.18,
                    xanchor="center",
                    # Formula to scale the position of the colorbar according to the font size
                    y=max(0, -0.005 * font_size + 0.98),
                    yanchor="bottom",
                    lenmode="fraction",
                    len=0.3,
                    thickness=15,
                ),
            ),
            hoverinfo="none",
            showlegend=False,
        )

        # Convert the colorbar trace to a dictionary before adding
        colorbar_trace_dict = colorbar_trace.to_plotly_json()
        fig.add_trace(colorbar_trace_dict)

    elif showAll:
        fig.update_layout(
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01,
                orientation="h",
                font=dict(size=font_size),
                bordercolor="black",
                borderwidth=2,
            ),
        )

    return fig


def get_application_memory_dots_fig(df, color, stress_score_scale=None, opacity=0.01):
    if "bw" not in df.columns or "lat" not in df.columns:
        print("Error: bw or lat not in df.columns")
        return None

    if color == "stress_score":
        dots_fig = px.scatter(
            df,
            x="bw",
            y="lat",
            color="stress_score",
            color_continuous_scale=stress_score_scale,
        )
    else:
        dots_fig = px.scatter(df, x="bw", y="lat", color_discrete_sequence=[color])

    marker_opts = dict(size=14, opacity=opacity)
    dots_fig.update_traces(marker=marker_opts)
    return dots_fig
