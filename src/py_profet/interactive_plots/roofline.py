import numpy as np
import plotly.graph_objects as go


def plot(peak_bandwidth, peak_performance):
    operational_intensity = np.logspace(0, 4, 400)
    
    mem_bound_performance = operational_intensity * peak_bandwidth
    mem_bound_performance = np.minimum(mem_bound_performance, peak_performance)

    # Create figure
    fig = go.Figure()

    # Add traces for the rooflines
    fig.add_trace(go.Scatter(x=operational_intensity, y=mem_bound_performance, 
                             mode='lines', line=dict(color='black', width=2), 
                             name='Memory Roofline'))

    # Annotations for Memory and Compute Roofs
    # Memory roof values
    mem_roof_values = np.unique(mem_bound_performance)
    # Operational intensity values for which the memory roof discurs
    mem_bound_x_values = operational_intensity[:len(mem_roof_values)]
    fig.add_annotation(
        # We later set x and y axis to log scale, so we need to set x and y in log10 scale
        # Set x at 1/3 of the operational intensity values corresponding to the memory roof
        x=np.log10(mem_bound_x_values[len(mem_bound_x_values) // 3]),
        # Set y to be 55% of the memory roof values
        y=np.log10(mem_roof_values[int(len(mem_roof_values) * 0.55)]),
        text=f"<b>Memory Roof<br>({peak_bandwidth} GB/s)</b>",
        showarrow=False,
        font=dict(size=12, color='black')
    )
    
    # x_pos_compute = 7 * peak_performance / peak_bandwidth
    fig.add_annotation(
        # Set x at 50% (indicated as 0.5 and 'paper')
        x=0.5,
        xref='paper',
        # Set y to be above the top y value (remember y is in log scale)
        y=np.log10(peak_performance * 1.15),
        text=f"<b>Compute Roof ({peak_performance} GFLOPS/s)</b>",
        showarrow=False,
        font=dict(size=12, color='black'),
    )

    # Set labels, title, and layout
    fig.update_layout(
        title="Roofline Model",
        xaxis_type="log",
        yaxis_type="log",
        xaxis_title="Operational Intensity (FLOPS/Byte)",
        yaxis_title="Performance (GFLOPS/s)",
        showlegend=False,
        # xgrid=True,
        # ygrid=True
    )

    return fig