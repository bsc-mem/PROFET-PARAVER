import numpy as np
import plotly.graph_objects as go
import pandas as pd


def plot(df: pd.DataFrame = None, division: float = 1.0):
    
    fig = go.Figure(data=[go.Scatter(x=division*df['timestamp'], y=df['stress_score'], mode='lines+markers')])
    fig.update_layout(title=f'Stress Score Over Time | Intervals of {division}s', xaxis_title='Seconds (Timestamps)', yaxis_title='Max. Stress Score')
    fig.update_yaxes(range=[0, 1])
    fig.update_traces(hovertemplate=(
        '<b>Max Stress Score</b><br>' +
        'Stress Score: %{y}<br>' +
        'Timestamp: %{x} seconds<extra></extra>'
    ))


    return fig