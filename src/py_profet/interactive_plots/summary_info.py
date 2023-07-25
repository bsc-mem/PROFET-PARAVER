import pandas as pd


def get_platform(config: dict):
    return {
        'server': {
            'name': {
                'label': 'Name',
                'value': 'TODO',
            },
            'num_nodes': {
                'label': 'Number of nodes',
                'value': 'TODO',
            },
            'sockets_per_node': {
                'label': 'Socket per node',
                'value': 'TODO',
            },
        },
        'cpu': {
            'model': {
                'label': 'Model',
                'value': 'TODO',
            },
            'n_cores': {
                'label': 'Number of cores',
                'value': 'TODO',
            },
            'freq': {
                'label': 'Frequency',
                'value': f'{config["cpu_freq"]:.1f} GHz',
            },
            'hyper': {
                'label': 'Hyper-threading',
                'value': 'TODO: ON/OFF',
            },
        },
        'memory': {
            'model': {
                'label': 'Model',
                'value': 'TODO',
            },
            'n_channels': {
                'label': 'Number of channels',
                'value': 'TODO',
            },
            'freq': {
                'label': 'Frequency',
                'value': 'TODO',
            },
        },
    }

def get_memory_profile(df: pd.DataFrame):
    return {
        'lead_off_lat': {
            'label': 'Lead-off latency',
            'value': f'{df["lat"].min():.1f} ns',
        },
        'max_bw': {
            'label': 'Max. measured bandwidth',
            'value': f'{df["bw"].max():.1f} GB/s',
        }
    }

def get_trace_info(df: pd.DataFrame, system_arch: dict):
    execution_duration_sec = (df['timestamp'].max() - df['timestamp'].min()) / 1e9

    sockets_per_node = [len(sockets) for sockets in system_arch.values()]
    if len(set(sockets_per_node)) == 1:
        # each node has the same number of sockets
        sockets_per_node_str = sockets_per_node[0]
    else:
        # show the number of sockets per node individually
        sockets_per_node_str = ', '.join([str(n) for n in sockets_per_node])

    return {
        'duration': {
            'label': 'Duration',
            'value': f'{execution_duration_sec:.1f} s',
        },
        'num_nodes': {
            'label': 'Number of nodes',
            'value': len(system_arch.keys()),
        },
        'node_labels': {
            'label': 'Node labels',
            'value': ', '.join(system_arch.keys()),
        },
        'sockets_per_node': {
            'label': 'Sockets per node',
            'value': sockets_per_node_str,
        },
        'n_cores': {
            'label': 'Number of cores',
            'value': 'TODO',
        },
    }

def get_summary_info(df: pd.DataFrame, config: dict, system_arch: dict):
    return {
        'platform': get_platform(config),
        'memory_profile': get_memory_profile(df),
        'trace_info': get_trace_info(df, system_arch),
    }