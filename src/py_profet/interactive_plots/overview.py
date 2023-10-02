import numpy as np
import plotly.graph_objects as go
import pandas as pd


def plot(df: pd.DataFrame = None, graph_title=''):
    
    fig = go.Figure(data=[go.Scatter(x=df['timestamp'], y=df['stress_score'], mode='lines+markers')])
    fig.update_layout(title='Stress Score Over Time', xaxis_title='Seconds (Timestamps)', yaxis_title='Stress Score')


    return fig