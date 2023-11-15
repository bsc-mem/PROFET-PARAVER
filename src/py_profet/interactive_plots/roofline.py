import math
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import curve_utils
import os
from hw_counter_parser import parse_cpu_info_from_file

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

def get_hw_counter_data(file_path):

    current_path = os.path.dirname(os.path.abspath(__file__))

    parsed_data = parse_cpu_info_from_file(current_path + "/" + file_path)

    return parsed_data

def convert_to_units(value, unit):
    units = {'': 1, 'K': 1000, 'M': 1000000, 'G': 1000000000, 'T': 1000000000000, 'P': 1000000000000000}

    if unit not in units:
        print("ERROR: Unknown unit: " + unit)
        return f'{value} {unit}'

    converted_value = value * units[unit]

    for u in ['P', 'T', 'G', 'M', 'K']:
        if converted_value >= units[u]:
            return f'{round(converted_value / units[u], 3)} {u}'

    return f'{round(converted_value, 2)}'

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

    L1 = float(L1)      * 100
    L2 = float(L2)      * 100
    L3 = float(L3)      * 100
    dram = float(dram)  * 100

    return {
        'name': name,
        'nominal_frequency': float(freq),
        'l1_cache': float(l1_size),
        'l2_cache': float(l2_size),
        'l3_cache': float(l3_size),
        'fp': float(fp),
        'fp_unit': f'{convert_to_units(float(fp), "G")}FLOPS/s',
        'bw': [
            {
                'level': 'L1',
                'value': float(L1),
                'unit': f'{convert_to_units(float(L1), "G")}B/s'
            },
            {
                'level': 'L2',
                'value': float(L2),
                'unit': f'{convert_to_units(float(L2), "G")}B/s'
            },
            {
                'level': 'L3',
                'value': float(L3),
                'unit': f'{convert_to_units(float(L3), "G")}B/s'
            },
            {
                'level': 'DRAM',
                'value': float(dram),
                'unit': f'{convert_to_units(float(dram), "G")}B/s'
            },
            
        ]
    }


def carm_eq(ai, bw, fp):
    return np.minimum(ai*bw, fp)

def get_roofline_markers_dots_fig(x_data, y_data, color, opacity=0.01):
    # # Create the roofline markers
    # if color == 'stress_score':
    #     dots_fig = go.Scatter(x=x_data, y=y_data, mode='markers', showlegend=False, marker=dict(
    #             size=5,
    #             opacity=opacity, 
    #             color=df['stress_score'], 
    #             colorscale=stress_score_scale['colorscale'],
    #             colorbar=dict(
    #                 title='Stress score',
    #             ),
    #             cmin=stress_score_scale['min'],
    #             cmax=stress_score_scale['max'],
    #         ),
    #         xaxis='x', 
    #         yaxis='y',
    #         name='Data',
    #         hovertemplate='<b>Stress score</b>: %{marker.color:.2f}<br><b>Operational Intensity</b>: %{x:.2f} (FLOPS/Byte)<br><b>Performance</b>: %{y:.2f} (GFLOPS/s)<br><b>Bandwidth</b>: %{customdata[3]:.2f} GB/s<br><b>Latency</b>: %{customdata[4]:.2f} ns<br><b>Timestamp</b>: %{text}<br><b>Node</b>: %{customdata[0]}<br><b>Socket</b>: %{customdata[1]}<br><b>MC</b>: %{customdata[2]}<extra></extra>', customdata=df[['node_name', 'socket', 'mc', 'bw', 'lat', 'stress_score']], text=df['timestamp'])
    # else:

    if color == 'stress_score':
        color = 'red'

    hover_data = np.column_stack((x_data, y_data))


    dots_fig = go.Scatter(x=x_data, y=y_data, mode='markers', showlegend=False, marker=dict(size=5, opacity=opacity, color=color), 
                        xaxis='x', 
                        yaxis='y',
                        hoverlabel=dict(namelength=0),
                        customdata=hover_data,
                        hovertemplate='<b>Operational Intensity</b>: %{customdata[0]} (FLOPS/Byte)<br><b>Performance</b>: %{customdata[1]} (GFLOPS/s)',
    )

    return dots_fig


def find_max_leading_zeros_value(data):
    max_leading_zeros = -1
    max_leading_zeros_value = None

    for value in data:
        num_str = f'{value:.16f}'
        leading_zeros = 0
        start = False
        if value != 0:
            for char in num_str:
                
                if start:
                    if char == '0':
                        leading_zeros += 1
                    else:
                        break
                elif char == '.':
                    start = True

            if leading_zeros > max_leading_zeros:
                max_leading_zeros = leading_zeros
                max_leading_zeros_value = value

    return max_leading_zeros*-1, max_leading_zeros_value


def orders_of_magnitude_apart(x, y):
    if x == 0 or y == 0:
        return abs(int(math.log10(max(abs(x), abs(y)))))
    
    order_of_magnitude = math.log10(abs(x) / abs(y))

    if x < 1:
        return order_of_magnitude + 1
    else:
        return order_of_magnitude + 1.5

def findMiddleLogPoint(first_power, second_power):

    orders_of_mag = orders_of_magnitude_apart(first_power, second_power)

    return np.log10(((10**first_power) + (10**second_power))/(10**(orders_of_mag)))


def singleRoofline(hw_counter, peak_bw_gbs, peak_bw_gbs_text, peak_flopss, peak_flopss_text, cache_bw, roofline_opts, region_transparency, markers_color, markers_transparency, leftOffset, rightOffset,  labels, stress_score_scale, graph_title=''):

    x_data = []
    y_data = []

    cache_elbows = [peak_flopss / bw['value'] for bw in cache_bw]

    min_cache_elbow = min(cache_elbows)
    max_cache_elbow = max(cache_elbows)
    
    minTest = np.log10(min_cache_elbow)

    if 'cache' in roofline_opts:
        min_cache_index = min(range(len(cache_bw)), key=lambda i: cache_bw[i]['value'])
    else:
        min_cache_index = 0
    
    if 'cache' in roofline_opts:
        max_cache_index = max(range(len(cache_bw)), key=lambda i: cache_bw[i]['value'])
    else:
        max_cache_index = 0
    
    fig = go.Figure()
    
    if len(hw_counter["Data"]) != 0 and 'showData' in roofline_opts:
        for i in range(len(hw_counter["Data"])):
            x_data.append(hw_counter["Data"][i]['TOTAL_FLOPS'] / hw_counter["Data"][i]['TOTAL_BYTES'])
            y_data.append((hw_counter["Data"][i]['TOTAL_FLOPS'] / 1000 / 1000) / hw_counter["Data"][i]['Total runtime [s]'])
            #TODO: Remove this correction
            if y_data[-1] > peak_flopss:
                y_data[-1] = peak_flopss / 2

        max_leading_zeros, l = find_max_leading_zeros_value(x_data)

        max_value = max(x_data)
        max_power_of_10 = math.ceil(math.log10(max_value))

        # TODO: Add a slider to modify the offset of X axis where the roofline starts
        ai = np.logspace(max_leading_zeros-1 + leftOffset, max_power_of_10 + rightOffset, 100)

        min_y_power, min_y_value = find_max_leading_zeros_value(y_data)

        max_cache_ai_y_value = carm_eq(ai[0], cache_bw[max_cache_index]['value'], peak_flopss)

        while min_y_value < carm_eq(ai[0], cache_bw[min_cache_index]['value'], peak_flopss):
            leftOffset -= 0.25
            ai = np.logspace(max_leading_zeros-1 + leftOffset, max_power_of_10 + rightOffset, 100)

        max_x_power = max_power_of_10 + rightOffset
        min_x_power = max_leading_zeros-1 + leftOffset
    else:
        ai = np.logspace(min_cache_elbow-5 + leftOffset, min_cache_elbow+3 + rightOffset, 100)
        max_x_power = min_cache_elbow+3 + rightOffset
        min_x_power = min_cache_elbow-5 + leftOffset
        min_y_power = carm_eq(ai[0], cache_bw[min_cache_index]['value'], peak_flopss)-1
        max_cache_ai_y_value = carm_eq(ai[0], cache_bw[max_cache_index]['value'], peak_flopss)

    max_x_value = round(ai.max())
    min_x_value = round(ai.min())

    #Defining different dash types for each cache level
    dash_type = ['dot', 'dash', 'longdash', 'dashdot', 'longdashdot']


    if 'regions' in roofline_opts:
        # Add the bound regions so that the user can see the different regions
        opacity = region_transparency

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
            x=findMiddleLogPoint(min_x_power, minTest),
            y=min_y_power-0.5,
            xref="x",
            yref="y",
            text="<b>Memory Bound</b>",
            showarrow=False,
            font=dict(size=20, color=f"rgba(0, 0, 0, {opacity})", family="Arial, sans-serif"),
            align="center"
        )

        if 'guides' in roofline_opts:
            fig.add_trace(go.Scatter(x=[min_x_value, max_x_value],
                                    y=[peak_flopss, peak_flopss], 
                                    mode='lines', 
                                    line=dict(color='grey', width=1, dash='dash'),
                                    hoverinfo='none',
                                    showlegend=False))
            fig.add_trace(go.Scatter(x=[peak_flopss/peak_bw_gbs, peak_flopss/peak_bw_gbs],
                                    y=[0, peak_flopss], 
                                    mode='lines', 
                                    line=dict(color='grey', width=1, dash='dash'),
                                    hoverinfo='none',
                                    showlegend=False))

        if 'cache' in roofline_opts:

            x_value_compute = [max_cache_elbow, max_x_value, max_x_value, max_cache_elbow]

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
            
            if 'guides' in roofline_opts:
                fig.add_trace(go.Scatter(x=[max_cache_elbow, max_cache_elbow],
                                        y=[0, peak_flopss], 
                                        mode='lines', 
                                        line=dict(color='grey', width=1, dash='dash'),
                                        hoverinfo='none',
                                        showlegend=False))
            
           

            fig.add_annotation(
                #x=x_pos,
                x=np.log10(max_cache_elbow/5),
                y=min_y_power-0.5,
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
            x=findMiddleLogPoint(max_cache_elbow, max_x_power),
            y=min_y_power-0.5,
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

    if 'showData' in roofline_opts:
        dots_fig = get_roofline_markers_dots_fig(x_data, y_data, markers_color, markers_transparency);
        fig.add_trace(dots_fig)
    
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
            font = dict(size = 15, color = "black")
        )
    )
    if 'roofLabels' in roofline_opts:
        # Annotations for Memory and Compute Roofs
        fig.add_annotation(
            #x=np.log10(max_x_value/3),  
            x=findMiddleLogPoint(max_cache_elbow, max_x_power)-1,
            y=np.log10(peak_flopss)*1.05,           
            text=f"<b>Compute roof ({peak_flopss_text})</b>",
            showarrow=False,
            font=dict(size=12, color='black'),
            xref="x",
            yref="y"
        )
        
        # Angle calculation for the memory roof annotation
        #angle = math.atan2(np.log10(peak_flopss*(1/3)), np.log10((peak_flopss/peak_bw_gbs)/ 5)) * 180 / math.pi

        fig.add_annotation(
            x=findMiddleLogPoint(min_x_power, min_cache_elbow)-1,
            y=findMiddleLogPoint(max_cache_ai_y_value, np.log10(peak_flopss))-1,
            text=f"<b>Memory BW roof ({peak_bw_gbs_text})</b>",
            showarrow=False,
            #textangle=angle + 180,
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