'''
Copyright (C) 2023 Isaac Boixaderas - All Rights Reserved
You may use, distribute and modify this code under the
terms of the BSD-3 license.

You should have received a copy of the BSD-3 license with
this file. If not, please visit: https://opensource.org/licenses/BSD-3-Clause
'''

import os
import sys
import inspect
import json
import pandas as pd

# Need to add parent folder to path for relative import 
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

from py_profet.curves import Curve



def check_param_types(params: dict):
    for name, values in params.items():
        if not isinstance(values[0], values[1]):
            raise Exception(f'{name} parameter should be of type {values[1].__name__}, {values[0]} was given.')

def check_non_negative(params: dict):
    for name, value in params.items():
        if value < 0:
            raise Exception(f'{name} parameter cannot be a negative number, {value} was given.')

def check_cpu_supported(df: pd.DataFrame, cpu_model: str):
    if not any(df['cpu_model'] == cpu_model):
        # TODO Add to message: check currently supported models with "program -flag"
        raise Exception(f'Unkown CPU model {cpu_model}. You can check the supported configuration options with the --supported_systems flag.')

def check_memory_supported(df: pd.DataFrame, memory_system: str):
    if not any(df['memory_system'] == memory_system):
        # TODO Add to message: check currently supported models with "program -flag"
        raise Exception(f'Unkown memory system {memory_system}. You can check the supported configuration options with the --supported_systems flag.')

def check_curves_exist(df: pd.DataFrame, cpu_model: str, memory_system: str):
    # check if curves exist for the specified system
    check_cpu_supported(df, cpu_model)
    check_memory_supported(df, memory_system)

# def check_non_negative(cache_line_bytes: int, n_reads: int, n_writes: int, elapsed_secs):
#     # check that the parameters are non-negative
#     err_msg = None
#     if cache_line_bytes < 0:
#         err_msg = f'Cache line bytes parameter cannot be a negative number, {cache_line_bytes} was given.'
#     elif n_reads < 0:
#         err_msg = f'Number of reads parameter cannot be a negative number, {n_reads} was given.'
#     elif n_writes < 0:
#         err_msg = f'Number of writes parameter cannot be a negative number, {n_writes} was given.'
#     elif elapsed_secs < 0:
#         err_msg = f'Elapsed seconds parameter cannot be a negative number, {elapsed_secs} was given.'

#     if err_msg:
#         raise Exception(err_msg)


def read_db(py_profet_path: str) -> pd.DataFrame:
    # read DB
    df = pd.read_csv(os.path.join(py_profet_path, 'cpu_memory_db.csv'))
    return df


def print_supported_systems(py_profet_path: str) -> None:
    # print supported systems from DB
    df = read_db(py_profet_path)
    print('CPU - DRAM')
    print('-----------------')
    for _, row in df.iterrows():
        print(f"{row['pmu_type']} {row['cpu_microarchitecture']} {row['cpu_model']} - {row['memory_system']}")


def get_row_from_db(py_profet_path: str, cpu_model: str, memory_system: str) -> dict:
    # get PMU type and microarchitecture from DB
    df = read_db(py_profet_path)
    check_curves_exist(df, cpu_model, memory_system)

    filt_df = df[(df['cpu_model'] == cpu_model) & (df['memory_system'] == memory_system)]
    if len(filt_df) > 1:
        raise Exception(f'There are multiple instances in the database with {cpu_model} CPU model and {memory_system} memory system.')

    return filt_df.iloc[0].to_dict()


def get_curves_path(py_profet_path: str, cpu_model: str, memory_system: str, pmu_type: str = None, cpu_microarch: str = None) -> str:
    if pmu_type is None or cpu_microarch is None:
        # Get data from DB
        row = get_row_from_db(py_profet_path, cpu_model, memory_system)
        pmu_type = row["pmu_type"]
        cpu_microarch = row["cpu_microarchitecture"]
    else:
        # check it here because get_row_from_db also checks it, so if this function is not executed on the previous if,
        # we have to make the check here
        df = pd.read_csv(os.path.join(py_profet_path, 'cpu_memory_db.csv'))
        check_curves_exist(df, cpu_model, memory_system)

    # build curves path
    bw_lats_folder = 'bw_lat_curves'
    curves_folder = f'{memory_system}__{pmu_type}__{cpu_microarch}__{cpu_model}'
    return os.path.join(py_profet_path, bw_lats_folder, curves_folder)


def get_curves_available_read_ratios(curves_path: str) -> list:
    if curves_path.endswith('.json'):
        with open(curves_path, 'r') as f:
            curves_json = json.load(f)
            return list(curves_json.keys())
    else:
        if not os.path.isdir(curves_path):
            raise Exception(f'Path {curves_path} should be a directory or a json file.')
        read_ratios = [float(f.split('_')[1].replace('.txt', '')) for f in os.listdir(curves_path) if 'bwlat_' in f and f.endswith('.txt')]
        return read_ratios
    

def get_curve(curves_path: str, read_ratio: float):
    return Curve(read_ratio, curves_path)


def get_memory_properties_from_bw(bws: list, lats: list, cpu_freq: float, write_ratio: float,
                                  bandwidth: float, display_warnings: int) -> dict:
    # bws: list of bandwidths in MB/s
    # lats: list of latencies in CPU cycles
    # write_ratio:
    # bandwidth: bandwidth in GB/s

    # Validate parameters
    check_param_types({
        # 'Memory system': (memory_system, str),
        'Write ratio': (write_ratio, float),
        'Bandwidth': (bandwidth, float),
    })
    check_non_negative({
        'Write ratio': write_ratio,
        'Bandwidth': bandwidth,
    })

    # convert display_warnings to boolean
    if (display_warnings == 0):
        display_warnings = False
    else:
        display_warnings = True
    
    # print(f'Write ratio: {write_ratio}')
    # print(f'Bandwidth: {round(bandwidth, 2)} GB/s')

    # The following 2 commented lines are now executed on profet.cpp.
    # Keep them here for now until we reach a final decision on where this should go.
    # specific_curves_path = f'{memory_system}__{pmu_type}__{cpu_microarch}__{cpu_model}'
    # full_curves_path = os.path.join(project_path, 'py_profet', 'bw_lat_curves', specific_curves_path)
    # set read ratio as float between 0 and 100
    read_ratio = 100 - write_ratio * 100
    # get latencies and bandwidths from curve (in CPU cycles and GB/s, respectively)
    curve_obj = Curve(read_ratio, bws=bws, lats=lats, display_warnings=display_warnings)

    # predicted latency in curve
    pred_lat = curve_obj.get_lat(bandwidth, bw_units='GB/s')
    # maximum latency (in CPU cycles) and bandwidth (GB/s) for the given read ratio
    max_bw = curve_obj.get_max_bw()
    max_lat = curve_obj.get_max_lat()
    # lead-off latency
    lead_off_lat = curve_obj.get_lead_off_lat()
    stress_score = curve_obj.get_stress_score(bandwidth, bw_units='GB/s', lat=pred_lat,
                                              lead_off_lat=lead_off_lat, max_lat=max_lat)
    if stress_score is None:
        stress_score = -1

    # print(f'Write ratio: {write_ratio}; Bw: {round(bandwidth, 2)} GB/s; Max. BW: {max_bw}')
    # print(f'Lat: {pred_lat}; Max. Lat: {max_lat}; Lead-off Lat: {lead_off_lat}')
    # print(f'Stress score: {stress_score}')
    # print()

    return {
        'write_ratio': write_ratio,
        'bandwidth': bandwidth,
        'max_bandwidth': max_bw,
        'latency': pred_lat if pred_lat == -1 else pred_lat / cpu_freq,
        'lead_off_latency': lead_off_lat / cpu_freq,
        'max_latency': max_lat / cpu_freq,
        'stress_score': stress_score,
    }

