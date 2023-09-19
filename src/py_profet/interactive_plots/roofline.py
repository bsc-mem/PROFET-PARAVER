import numpy as np
import plotly.graph_objects as go


def plot(peak_bw_gbs, peak_flopss, x_data=[], y_data=[], graph_title=''):
    x_data = np.array(x_data)
    y_data = np.array(y_data)
    operational_intensity = np.logspace(0, 4, 400)
    
    mem_bound_performance = operational_intensity * peak_bw_gbs
    mem_bound_performance = np.minimum(mem_bound_performance, peak_flopss)

    # TODO: decide what to do with the following. Do we have this kind of data? It looks weird on the chart
    filter_x_idxs = np.where(x_data >= 0)[0]
    filter_y_idxs = np.where(y_data >= mem_bound_performance[0])[0]
    filter_idxs = np.intersect1d(filter_x_idxs, filter_y_idxs)
    x_data = x_data[filter_idxs]
    y_data = y_data[filter_idxs]

    # Create figure
    fig = go.Figure()

    # Add roofs
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
    
    # x_pos_compute = 7 * peak_flopss / peak_bw_gbs
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
        # xgrid=True,
        # ygrid=True
    )

    return fig



def plotCARM(peak_bw_gbs, peak_flopss, cache_bw, x_data=[], y_data=[], graph_title=''):
    x_data = np.array(x_data)
    y_data = np.array(y_data)
    operational_intensity = np.logspace(0, 4, 400)
    
    mem_bound_performance = operational_intensity * peak_bw_gbs

    mem_bound_performance = np.minimum(mem_bound_performance, peak_flopss)
    
    cache_bound_performance = []
    for i in range(len(cache_bw)):
        cache_bound_performance.append(operational_intensity * cache_bw[i])
        cache_bound_performance[i] = np.minimum(cache_bound_performance[i], peak_flopss)
        #TODO: Uncomment this to remove the slight separation between roofs. 
        cache_bound_performance[i] = cache_bound_performance[i][~np.isin(cache_bound_performance[i], mem_bound_performance)]


    # TODO: decide what to do with the following. Do we have this kind of data? It looks weird on the chart
    filter_x_idxs = np.where(x_data >= 0)[0]
    filter_y_idxs = np.where(y_data >= mem_bound_performance[0])[0]
    filter_idxs = np.intersect1d(filter_x_idxs, filter_y_idxs)
    x_data = x_data[filter_idxs]
    y_data = y_data[filter_idxs]

    # Create figure
    fig = go.Figure()

    dash_type = ['dot', 'dash', 'longdash', 'dashdot', 'longdashdot']

    # Add data
    fig.add_trace(go.Scatter(x=x_data, y=y_data, 
                             mode='markers', marker=dict(color='red'),
                             name='Data', showlegend=False))
    
    # Add roofs
    fig.add_trace(go.Scatter(x=operational_intensity, y=mem_bound_performance, 
                             mode='lines', line=dict(color='black', width=2),
                             name='Roofline'))
    for i in range(len(cache_bound_performance)):
        fig.add_trace(go.Scatter(x=operational_intensity, y=cache_bound_performance[i],
                                mode='lines', line=dict(color='black', width=2, dash=dash_type[i]),
                                #TODO: Decidir si es vol posar el valor de cada bw o no
                                #name=f'L{i+1} Roofline', showlegend=True))
                                name=f'L{i+1} ({cache_bw[i]:.1f} GB/s)', showlegend=True))
            
    fig.update_layout(
        legend=dict(
            orientation="h",
            y=1.12,
            yref="paper",
        )
    )


    # Annotations for Memory and Compute Roofs
    # Memory roof values
    mem_roof_values = np.unique(mem_bound_performance)
    # Operational intensity values for which the memory roof discurs
    mem_bound_x_values = operational_intensity[:len(mem_roof_values)]

    memory_angles = np.arctan(peak_bw_gbs / operational_intensity) * 180 / np.pi
    memory_angle = memory_angles[int(len(memory_angles) * 0.45)]

    fig.add_annotation(
        # We later set x and y axis to log scale, so we need to set x and y in log10 scale
        # Set x at 1/3 of the operational intensity values corresponding to the memory roof
        x=np.log10(mem_bound_x_values[len(mem_bound_x_values) // 2]),
        # Set y to be 65% of the memory roof values
        y=np.log10(mem_roof_values[int(len(mem_roof_values) * 0.65)]),
        text=f"<b>Memory BW roof<br>({peak_bw_gbs:.1f} GB/s)</b>",
        showarrow=False,
        font=dict(size=10, color='black'),
        textangle=-memory_angle,
    )

    
    # x_pos_compute = 7 * peak_flopss / peak_bw_gbs
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
        showlegend=True,
        # xgrid=True,
        # ygrid=True
    )

    return fig