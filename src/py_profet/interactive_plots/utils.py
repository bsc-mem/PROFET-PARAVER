import os
import numpy as np
import pandas as pd
from collections import defaultdict
from dash import html


def get_node_names(row_file_path):
    # get the name of the nodes specified in the .row file
    node_counter = 0
    n_nodes = None
    node_names = []
    with open(row_file_path, 'r') as f:
        for l in f.readlines():
            if 'LEVEL APPL SIZE' in l:
                n_nodes = int(l.strip().split(' ')[-1])
                node_counter = 1
                continue
            if node_counter:
                node_names.append(l.strip())
                node_counter += 1
                if node_counter > n_nodes:
                    # all node names have been read
                    break
    return node_names


def prv_to_df(trace_file_path, row_file_path, config_json, excluded_original, save_feather=False):
    node_names = get_node_names(row_file_path)
    num_lines = sum(1 for _ in open(trace_file_path))

    rand_lines = []
    file_stats = os.stat(trace_file_path)
    file_mb = file_stats.st_size / (1024 ** 2)
    # directly undersample if file is big
    if file_mb > 100:
        # lines to undersample to have close to 100 MB
        undersample_n_lines = int((100 / file_mb) * num_lines)
        print(
            f'File size is {file_mb:.2f} MB, with {num_lines:,} lines. Undersampling to {10000 / file_mb:.0f}% of original file.')
        # take random rows sample. Sort them in descending order to then process it using pop() for efficiency
        rand_lines = sorted(np.random.choice(num_lines, size=undersample_n_lines, replace=False), reverse=True)

    df = []
    metric_keys = ['wr', 'bw', 'max_bw', 'lat', 'min_lat', 'max_lat', 'stress_score', 'mean_reads', 'mean_writes']
    with open(trace_file_path) as f:
        first_line = True
        # all_lines = f.readlines()
        # do not read all lines at once, read them line by line to save memory
        for i, line in enumerate(f):
            if i % 100000 == 0:
                print(f'Loading is {i / num_lines * 100:.2f}% complete.', end='\r')

            if len(rand_lines):
                if i == rand_lines[-1]:
                    rand_lines.pop()
                else:
                    # skip line if it is not in the random sample
                    continue

            if first_line or line.startswith('#') or line.startswith('c'):
                # skip header, comments and communicator lines
                first_line = False
                continue

            sp = line.split(':')
            row = defaultdict()
            row['node'] = int(sp[2])

            if not excluded_original and row['node'] == 1:
                # skip first application (original trace values) when it is excluded
                continue

            row['node_name'] = node_names[row['node'] - 1]
            row['socket'] = int(sp[3])
            row['mc'] = int(sp[4])
            row['timestamp'] = int(sp[5])

            # process subsequent metric IDs and values after the timestamp
            for i in range(6, len(sp) - 1, 2):
                metric_id = int(sp[i])
                last_metric_digit = int(metric_id % 10)

                if last_metric_digit > len(metric_keys):
                    # we're over the desired metrics, no need to continue
                    break

                metric_key = metric_keys[last_metric_digit - 1]
                val = float(sp[i + 1].strip())

                # negative values are set for identifying irregular data, include all of them for now and remove whole negative rows later (see next lines)
                if val != -1:
                    # apply precision of the prv file.
                    # if it is negative but different than -1, apply precision as well, as
                    # we stored the calculated metric as a negative number for identifying it as an error or an irregularity.
                    val = float(val / 10 ** config_json['precision'])
                row[metric_key] = val

                if metric_key == metric_keys[-1]:
                    # we've processed the last metric key we want, no need to continue (even if there are other events pending)
                    break

            df.append(row)

        print('Loading is 100% complete.')
        df = pd.DataFrame(df)
        # perform a forward fill for copying above values of NaN (prvparser is purpously omitting equal consecutive values of a metric)
        df = df.ffill()
        # keep only rows with non-negative values, which means we logged erroneous or irregular data
        # also, keep NaN values for performing a forward-fill
        df = df[(pd.isnull(df[metric_keys]).any(axis=1)) | (df[metric_keys] >= 0).all(axis=1)].reset_index(drop=True)
        # calculate read ratio
        df['rr'] = 100 - df['wr']

        # TODO hard-coded drop 0s. Decide what to do with them in the output trace
        df = df[~((df['bw'] == 0) & (df['lat'] == 0))].reset_index(drop=True)

        if save_feather:
            trace_feather_path = trace_file_path.replace('.prv', '.feather')
            df.to_feather(trace_feather_path)

        return df


def filter_df(df, node_name=None, i_socket=None, i_mc=None, time_range=(), bw_range=(), lat_range=()):
    mask = np.ones(len(df), dtype=bool)
    if node_name is not None:
        mask &= df['node_name'] == node_name
    if i_socket is not None:
        mask &= df['socket'] == int(i_socket)
    if i_mc is not None:
        mask &= df['mc'] == int(i_mc)
    if len(time_range):
        mask &= (df['timestamp'] >= time_range[0] * 1e9) & (df['timestamp'] < time_range[1] * 1e9)
    if len(bw_range):
        mask &= (df['bw'] >= bw_range[0]) & (df['bw'] < bw_range[1])
    if len(lat_range):
        mask &= (df['lat'] >= lat_range[0]) & (df['lat'] < lat_range[1])
    return df[mask]


def get_dash_table_rows(rows_info: list):
    # rows_info is a list of dicts with the following keys: label, value
    return [html.Tr([html.Td(row['label']), html.Td(row['value'])]) for _, row in rows_info.items()]

# def extract_graphs(layout_element):
#     """Recursively extract all dcc.Graph objects from a given layout element."""
#     graphs = []

#     if isinstance(layout_element, list):
#         for elem in layout_element:
#             graphs.extend(extract_graphs(elem))
#     elif hasattr(layout_element, 'children'):
#         graphs.extend(extract_graphs(layout_element.children))
#     elif isinstance(layout_element, dcc.Graph) and hasattr(layout_element, 'figure'):
#         graphs.append(layout_element.figure)

#     return graphs

# def find_component_by_id(layout, component_id):
#     """Recursively search for a component with the given ID in the layout."""

#     # Base case: if the component is a dictionary and has an 'id' key
#     if hasattr(layout, 'id') and layout.id == component_id:
#         return layout

#     # If the component has 'children', search inside them
#     if hasattr(layout, 'children'):
#         children = layout.children
#         if isinstance(children, (list, tuple)):
#             for child in children:
#                 result = find_component_by_id(child, component_id)
#                 if result:
#                     return result
#         else:
#             return find_component_by_id(children, component_id)

#     return None


# def components_to_html_str(components):
#     """Convert a list of Dash components to an HTML string."""
#     html_list = []

#     for component in components:
#         if not hasattr(component, 'type') or not hasattr(component, 'props'):
#             continue

#         if component.type == 'Table':
#             html_list.append(table_to_html_str(component))
#         elif component.type == 'H1':
#             html_list.append(f"<h1>{component.props['children']}</h1>")
#         elif component.type == 'P':
#             html_list.append(f"<p>{component.props['children']}</p>")
#         # Add other types as needed...

#     return ''.join(html_list)

# def table_to_html_str(table_component):
#     """Convert a Dash dbc.Table component into an HTML string."""

#     # Convert Dash components to HTML strings
#     children_str = ''.join([dash_component_to_html_str(child) for child in table_component.children])

#     return f"<table>{children_str}</table>"

# def dash_component_to_html_str(component):
#     """Recursive function to convert Dash components to HTML strings."""

#     # Base case: if component is just a string, return it
#     if isinstance(component, (str, int, float)):
#         return str(component)

#     # Convert component type to string tag name
#     tag = component.__class__.__name__.lower()

#     children = getattr(component, "children", "")

#     # If children is a list, recursively convert each child
#     if isinstance(children, list):
#         children_str = ''.join([dash_component_to_html_str(child) for child in children])
#     else:
#         children_str = dash_component_to_html_str(children)

#     return f"<{tag}>{children_str}</{tag}>"
