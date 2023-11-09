import math
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import curve_utils
import os

def plot(peak_bw_gbs, peak_flopss, x_data=[], y_data=[], graph_title=''):
    # Convert input data to NumPy arrays
    x_data = np.array(x_data)
    y_data = np.array(y_data)
    operational_intensity = np.logspace(0, 4, 400)
    
    # Calculate memory-bound performance
    mem_bound_performance = operational_intensity * peak_bw_gbs
    # Clip memory-bound performance to the compute roof
    mem_bound_performance = np.minimum(mem_bound_performance, peak_flopss)

    # TODO: decide what to do with the following. Do we have this kind of data? It looks weird on the chart
    filter_x_idxs = np.where(x_data >= 0)[0]
    filter_y_idxs = np.where(y_data >= mem_bound_performance[0])[0]
    filter_idxs = np.intersect1d(filter_x_idxs, filter_y_idxs)
    x_data = x_data[filter_idxs]
    y_data = y_data[filter_idxs]

    # Create figure
    fig = go.Figure()

    # Add memory and compute roofs
    fig.add_trace(go.Scatter(x=operational_intensity, y=mem_bound_performance, 
                             mode='lines', line=dict(color='black', width=2),
                             name='Roofline'))
    
    # Add data
    fig.add_trace(go.Scatter(x=x_data, y=y_data, 
                             mode='markers', marker=dict(color='red'),
                             name='Data'))

    # Annotations for Memory and Compute Roofs
    # Memory roof values
    mem_roof_values = np.unique(mem_bound_performance)
    # Operational intensity values for which the memory roof discurs
    mem_bound_x_values = operational_intensity[:len(mem_roof_values)]
    fig.add_annotation(
        # We later set x and y axis to log scale, so we need to set x and y in log10 scale
        # Set x at 1/3 of the operational intensity values corresponding to the memory roof
        x=np.log10(mem_bound_x_values[len(mem_bound_x_values) // 3]),
        # Set y to be 65% of the memory roof values
        y=np.log10(mem_roof_values[int(len(mem_roof_values) * 0.65)]),
        text=f"<b>Memory BW roof<br>({peak_bw_gbs:.1f} GB/s)</b>",
        showarrow=False,
        font=dict(size=12, color='black')
    )
    
    fig.add_annotation(
        # Set x at 50% (indicated as 0.5 and 'paper')
        x=0.5,
        xref='paper',
        # Set y to be above the top y value (remember y is in log scale)
        y=np.log10(peak_flopss * 1.11),
        text=f"<b>Compute roof ({peak_flopss:.1f} GFLOPS/s)</b>",
        showarrow=False,
        font=dict(size=12, color='black'),
    )

    # Set labels, title, and layout
    fig.update_layout(
        title={
            'text': graph_title,
            'font': {
                'size': 24,
                'color': 'black',
                'family': 'Arial, sans-serif',
            },
            'x':0.5,
            'xanchor': 'center'
        },
        xaxis_type="log",
        yaxis_type="log",
        xaxis_title="Operational Intensity (FLOPS/Byte)",
        yaxis_title="Performance (GFLOPS/s)",
        showlegend=False,
    )

    return fig

def sigmoid(x):
    return 1 / (1 + np.exp(-x))

def softplus(x):
    return np.log(1 + np.exp(x))

def plotCARM(df, peak_bw_gbs, peak_flopss, cache_bw, markers_color, markers_transparency, labels, stress_score_scale, graph_title=''):

    # Creating random data for flops/s
    num_rows = len(df)
    df['flops/s'] = np.random.uniform(0, peak_flopss, num_rows)

    # Calculate 'flops/byte' based on random 'flops/s' and 'bw' values
    # TODO: The '* 40' multiplier is arbitrary and may need revision
    df['flops/byte'] = df['flops/s'] / (df['bw'] * 40) 

    # Filter out non-finite values and calculate 'max_x_value'
    filtered_values = df['flops/byte'][np.isfinite(df['flops/byte'])]

    if len(filtered_values) > 0:
        max_x_value = round(filtered_values.max())+10000
    else:
        max_x_value = 10000

    fig = go.Figure()

    # Calculate the deviation of 'flops/s' from the peak value
    distance_compute = peak_flopss - df['flops/s']

    #Normalize the distance
    normalized_distance_compute = distance_compute / peak_flopss
    stress_score_compute = np.clip(1 - normalized_distance_compute, 0, 1)

    # Calculate proximity to memory-bound performance
    operational_intensity = np.linspace(0, max_x_value, max_x_value)
    mem_perf = operational_intensity * peak_bw_gbs
    mem_bound_performance = np.minimum(mem_perf, peak_flopss)
    proximity_memory = 1 - (df['flops/byte'] / mem_bound_performance[df.index])

    # Define weights for the contributions of compute and memory
    weight_compute = 0.7 
    weight_memory = 0.3  

    # Combine compute and memory factors to calculate the final 'stress_score'
    df['stress_score'] = (weight_compute * stress_score_compute + weight_memory * proximity_memory)

    # Apply a decay function to 'stress_score' for smoothing, if desired
    #decay_factor = 1
    #df['stress_score'] = 1 - np.exp(-decay_factor * df['stress_score'])

    x_data = np.array(df['flops/byte'])
    y_data = np.array(df['flops/s'])

    # Create roofline markers using a function from 'curve_utils' module
    dots_fig = curve_utils.get_roofline_markers_dots_fig(df, x_data, y_data, markers_color, stress_score_scale, markers_transparency);
    fig.add_trace(dots_fig)
    
    # Add a roofline line to the figure
    fig.add_trace(go.Scatter(x=[0, peak_flopss/peak_bw_gbs, max_x_value], y=[0, peak_flopss, peak_flopss], mode='lines', line=dict(color='black', width=2),
                             name=f'Roofline',
                             hoverlabel=dict(namelength=0),
                             
                             hovertemplate=f'<b>Roofline</b><br>' +
                                            'Operational Intensity: %{x} (FLOPS/Byte)<br>' +
                                            'Performance: %{y} (GFLOPS/s)<br>'))

    
    #Defining different dash types for each cache level
    dash_type = ['dot', 'dash', 'longdash', 'dashdot', 'longdashdot']

    #Adding cache BW roofs
    for i in range(len(cache_bw)):
        cache_elbow = peak_flopss/cache_bw[i]['value']
        level= cache_bw[i]['level']
        fig.add_trace(go.Scatter(x=[0, cache_elbow], y=[0, peak_flopss], mode='lines', line=dict(color='black', width=2, dash=dash_type[i]),
            hoverlabel=dict(namelength=0),
                                hovertemplate=f'<b>{f"Cache BW roof ({level})" if level != "DRAM" else level}</b><br>BW: {cache_bw[i]["unit"]}<br>' +
                                          'Operational Intensity: %{x} (FLOPS/Byte)<br>' +
                                          'Performance: %{y} (GFLOPS/s)<br>',
                                name=f'{cache_bw[i]["level"]} ({cache_bw[i]["unit"]})', showlegend=True))


    #Makes legend responsive so that it doesn't overlap with the chart when window is resized.
    fig.update_layout(
        legend=dict(
            orientation="h",
            y=1,
            yref="paper",
            yanchor="bottom",
            x=0.5,
            xref="paper",
            xanchor="center",
        )
    )

    #Adding color bar
    if markers_color == 'stress_score':
        color_bar_trace = go.Scatter(x=[None], y=[None], mode='markers', 
            name='stress_score_trace',
            marker=dict(
                colorscale=stress_score_scale['colorscale'], 
                colorbar=dict(
                    title=labels['stress_score'],
                ),
                cmax=stress_score_scale['max'],
                cmin=stress_score_scale['min'],
            ), 
            showlegend=False)

        fig.add_trace(color_bar_trace)

    # Annotations for Memory and Compute Roofs
    fig.add_annotation(
        x=3*(np.log10(peak_flopss/peak_bw_gbs + max_x_value)/4),
        y=np.log10(peak_flopss * 1.25),
        text=f"<b>Compute roof ({(0.000001*peak_flopss):.2f} TFLOPS/s)</b>",
        showarrow=False,
        font=dict(size=12, color='black'),
    )

    # Angle calculation for the memory roof annotation
    angle = math.atan2(np.log10(peak_flopss), np.log10(peak_flopss/peak_bw_gbs)) * 180 / math.pi

    fig.add_annotation(
        x=np.log10((peak_flopss/peak_bw_gbs)/9),
        y=np.log10(peak_flopss/9)+0.3,
        text=f"<b>Memory BW roof<br>({peak_bw_gbs:.1f} GB/s)</b>",
        showarrow=False,
        textangle=-angle*0.75,
        font=dict(size=12, color='black')
    )

    fig.update_layout(
        title={
            'text': graph_title,
            'font': {
                'size': 24,
                'color': 'black',
                'family': 'Arial, sans-serif',
            },
            'x':0.5,
            'xanchor': 'center'
        },
        xaxis_type="log",
        yaxis_type="log",
        xaxis_title="Operational Intensity (FLOPS/Byte)",
        yaxis_title="Performance (GFLOPS/s)",
        showlegend=True,
    )

    
    return fig


def read_config(config_file):
    f = open(config_file, "r")

    for line in f:
        l = line.split('=')
        if(l[0] == 'name'):
            name = l[1].rstrip()

        if(l[0] == 'nominal_frequency'):
            freq = l[1].rstrip()

        if(l[0] == 'l1_cache'):
            l1_size = l[1].rstrip()

        if(l[0] == 'l2_cache'):
            l2_size = l[1].rstrip()
        
        if(l[0] == 'l3_cache'):
            l3_size = l[1].rstrip()

    return name, freq, l1_size, l2_size, l3_size

def get_system_properties(file_path):

    current_path = os.path.dirname(os.path.abspath(__file__))

    f = open(current_path + "/" + file_path, "r")

    for line in f:
        l = line.split('=')
        if(l[0] == 'name'):
            name = l[1].rstrip()
        if(l[0] == 'nominal_frequency'):
            freq = l[1].rstrip()

        if(l[0] == 'l1_cache'):
            l1_size = l[1].rstrip()

        if(l[0] == 'l2_cache'):
            l2_size = l[1].rstrip()
        
        if(l[0] == 'l3_cache'):
            l3_size = l[1].rstrip()
        
        if(l[0] == 'L1'):
            L1 = l[1].rstrip()
        
        if(l[0] == 'L2'):
            L2 = l[1].rstrip()
        
        if(l[0] == 'L3'):
            L3 = l[1].rstrip()
        
        if(l[0] == 'DRAM'):
            dram = l[1].rstrip()
        
        if(l[0] == 'FP'):
            fp = l[1].rstrip()
        

    return {
        'name': name,
        'nominal_frequency': float(freq),
        'l1_cache': float(l1_size),
        'l2_cache': float(l2_size),
        'l3_cache': float(l3_size),
        'fp': float(fp),
        'bw': [
            {
                'level': 'L1',
                'value': float(L1),
                'unit': f'{round(float(L1), 2)} GB/s'
            },
            {
                'level': 'L2',
                'value': float(L2),
                'unit': f'{round(float(L2), 2)} GB/s'
            },
            {
                'level': 'L3',
                'value': float(L3),
                'unit': f'{round(float(L3), 2)} GB/s'
            },
            {
                'level': 'DRAM',
                'value': float(dram),
                'unit': f'{round(float(dram), 2)} GB/s'
            },
            
        ]
    }


def carm_eq(ai, bw, fp):
    return np.minimum(ai*bw, fp)


def singleRoofline(df, peak_bw_gbs, peak_flopss, cache_bw, roofline_opts, region_transparency, labels, stress_score_scale, graph_title=''):


     # Creating random data for flops/s
    num_rows = len(df)
    df['flops/s'] = np.random.uniform(0, peak_flopss, num_rows)

    df['flops/byte'] = df['flops/s'] / (df['bw'] * 40) 

    fig = go.Figure()

    ai = np.logspace(-3, 5, 100)


    max_x_value = round(ai.max())


    # Create roofline markers using a function from 'curve_utils' module
    # dots_fig = curve_utils.get_roofline_markers_dots_fig(df, x_data, y_data, markers_color, stress_score_scale, markers_transparency);
    # fig.add_trace(dots_fig)
    
    # Add a roofline line to the figure

    
    #Defining different dash types for each cache level
    dash_type = ['dot', 'dash', 'longdash', 'dashdot', 'longdashdot']


    if 'regions' in roofline_opts:
        # Add the bound regions so that the user can see the different regions
        opacity = region_transparency

        cache_elbows = [peak_flopss / bw['value'] for bw in cache_bw]

        min_cache_elbow = min(cache_elbows)
        max_cache_elbow = max(cache_elbows)

        # Memory bound region
        fig.add_trace(go.Scatter(x=[0, peak_flopss/peak_bw_gbs, max_x_value, 0], 
                                y=[0, peak_flopss, 0, 0], 
                                fill="toself", 
                                line=dict(width=0),
                                fillcolor=f"rgba(135, 206, 250, {opacity})",
                                marker=dict(color='rgba(0,0,0,0)'),
                                hoverlabel=dict(namelength=0),
                                hoverinfo='none',
                                name=f'Memory Bound',
                                showlegend=False))

        fig.add_annotation(
            x=np.log10((peak_flopss/peak_bw_gbs)/10),
            y=-2,
            xref="x",
            yref="y",
            text="<b>Memory Bound</b>",
            showarrow=False,
            font=dict(size=20, color=f"rgba(0, 0, 0, {opacity})", family="Arial, sans-serif"),
            align="center"
        )

        if 'cache' in roofline_opts:

            x_value_compute = [max_cache_elbow, max_x_value, max_x_value, max_cache_elbow]
            x_value_compute_annotation = np.log10((max_cache_elbow+ max_x_value)/100)

            # Mixed region
            fig.add_trace(go.Scatter(x=[min_cache_elbow, max_cache_elbow, max_cache_elbow, min_cache_elbow], 
                                    y=[peak_flopss, peak_flopss, 0, 0], 
                                fill="toself", 
                                line=dict(width=0),
                                fillcolor=f"rgba(248,216,145, {opacity})",
                                marker=dict(color='rgba(0,0,0,0)'),
                                hoverlabel=dict(namelength=0),
                                hoverinfo='none',
                                name=f'Mixed Region',
                                showlegend=False))
            
            fig.add_annotation(
                x=np.log10(max_cache_elbow/5),
                y=-2,
                xref="x",
                yref="y",
                text="<b>Mixed</b>",
                showarrow=False,
                font=dict(size=20, color=f"rgba(0, 0, 0, {opacity})", family="Arial, sans-serif"),
                align="center"
            )

        else:
            x_value_compute = [min_cache_elbow, max_x_value, max_x_value, min_cache_elbow]
            x_value_compute_annotation = np.log10((min_cache_elbow+ max_x_value)/100)

        # Compute bound region
        fig.add_trace(go.Scatter(x=x_value_compute,
                                y=[peak_flopss, peak_flopss, 0, 0], 
                                fill="toself", 
                                line=dict(width=0),
                                fillcolor=f"rgba(250, 17, 17, {opacity})", 
                                marker=dict(color='rgba(0,0,0,0)'),
                                hoverinfo='none',
                                name='Compute Bound',
                                showlegend=False))

        fig.add_annotation(
            x=x_value_compute_annotation,
            y=-2,
            xref="x",
            yref="y",
            text="<b>Compute Bound</b>",
            showarrow=False,
            font=dict(size=20, color=f"rgba(0, 0, 0, {opacity})", family="Arial, sans-serif"),
            align="center"
        )

    if 'cache' in roofline_opts:
        #Adding cache BW roofs
        for i in range(len(cache_bw)):
            level= cache_bw[i]['level']
            fig.add_trace(go.Scatter(x=ai, y=carm_eq(ai, cache_bw[i]['value'], peak_flopss), mode='lines', line=dict(color='black', width=1.5, dash=dash_type[i]),
                hoverlabel=dict(namelength=0),
                                    hovertemplate=f'<b>{f"Cache BW roof ({level})" if level != "DRAM" else level}</b><br>BW: {cache_bw[i]["unit"]}<br>' +
                                            'Operational Intensity: %{x} (FLOPS/Byte)<br>' +
                                            'Performance: %{y} (GFLOPS/s)<br>',
                                    name=f'{cache_bw[i]["level"]} ({cache_bw[i]["unit"]})', showlegend=True))


    fig.add_trace(go.Scatter(x=ai, y=carm_eq(ai, peak_bw_gbs, peak_flopss), mode='lines', line=dict(color='black', width=2),
                             name=f'Roofline',
                             hoverlabel=dict(namelength=0),
                             
                             hovertemplate=f'<b>Roofline</b><br>' +
                                            'Operational Intensity: %{x} (FLOPS/Byte)<br>' +
                                            'Performance: %{y} (GFLOPS/s)<br>'))


    #Makes legend responsive so that it doesn't overlap with the chart when window is resized.
    fig.update_layout(
        legend=dict(
            orientation="h",
            y=1,
            yref="paper",
            yanchor="bottom",
            x=0.5,
            xref="paper",
            xanchor="center",
        )
    )
    # Annotations for Memory and Compute Roofs
    fig.add_annotation(
        x=np.log10(max_x_value)/3,  
        y=np.log10(peak_flopss+5),           
        text=f"<b>Compute roof ({(peak_flopss):.2f} GFLOPS/s)</b>",
        showarrow=False,
        font=dict(size=12, color='black'),
        xref="x",
        yref="y"
    )


    # Angle calculation for the memory roof annotation
    angle = math.atan2(np.log10(peak_flopss*(1/3)), np.log10((peak_flopss/peak_bw_gbs)/ 5)) * 180 / math.pi

    fig.add_annotation(
        x=np.log10((peak_flopss/peak_bw_gbs) / 5),
        y=np.log10(peak_flopss*(1/3)),
        text=f"<b>Memory BW roof ({peak_bw_gbs:.1f} GB/s)</b>",
        showarrow=False,
        textangle=angle + 180,
        font=dict(size=12, color='black'),
        xref="x",
        yref="y"
    )


    fig.update_layout(
        title={
            'text': graph_title,
            'font': {
                'size': 24,
                'color': 'black',
                'family': 'Arial, sans-serif',
            },
            'x':0.5,
            'xanchor': 'center'
        },
        xaxis=dict(
            type="log",
            title="Operational Intensity (FLOPS/Byte)",
        ),
        yaxis=dict(
            type="log",
            title="Performance (GFLOPS/s)",
        ),
        showlegend=True,
    )

    
    return fig