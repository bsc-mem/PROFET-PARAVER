"""
Copyright (C) 2023 Isaac Boixaderas - All Rights Reserved
You may use, distribute and modify this code under the
terms of the BSD-3 license.

You should have received a copy of the BSD-3 license with
this file. If not, please visit: https://opensource.org/licenses/BSD-3-Clause
"""

import inspect, os, sys, pathlib, platform
from pathlib import Path
from collections import deque


def _add_private_wheels():
    exe_dir = Path(sys.executable).resolve().parent
    arch = (
        "python_libs_x86_64" if platform.machine() == "x86_64" else "python_libs_arm64"
    )
    wheel = exe_dir / arch
    if wheel.is_dir():
        sys.path.insert(0, str(wheel))


_add_private_wheels()


# Need to add parent folder to path for relative import
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

import pandas as pd

from profet.curves import Curves, OvershootError
from profet.metrics import Bandwidth

# Curves global variable. Set it with set_curves() function
curves = None
display_warnings = True


def check_param_types(params: dict):
    for name, values in params.items():
        if not isinstance(values[0], values[1]):
            raise Exception(
                f"{name} parameter should be of type {values[1].__name__}, {values[0]} was given."
            )


def check_non_negative(params: dict):
    for name, value in params.items():
        if value < 0:
            raise Exception(
                f"{name} parameter cannot be a negative number, {value} was given."
            )


def check_cpu_supported(df: pd.DataFrame, cpu_model: str):

    if not any(df["cpu_model"] == cpu_model):
        # TODO Add to message: check currently supported models with "program -flag"
        raise Exception(
            f"Unkown CPU model {cpu_model}. You can check the supported configuration options with the --supported_systems flag."
        )


def check_memory_supported(df: pd.DataFrame, memory_system: str):
    if not any(df["memory_system"] == memory_system):
        # TODO Add to message: check currently supported models with "program -flag"
        raise Exception(
            f"Unkown memory system {memory_system}. You can check the supported configuration options with the --supported_systems flag."
        )


def check_curves_exist(df: pd.DataFrame, cpu_model: str, memory_system: str):
    # check if curves exist for the specified system
    # Check if df is of type string:
    if not isinstance(df, pd.DataFrame):
        df = read_db(df)

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


def _find_mp_root(base: Path, bfs_depth: int = 2) -> Path | None:
    """
    Look for an existing “Mess-Paraver” directory by:
      1. Checking each existing ancestor for name == "Mess-Paraver"
      2. BFS under each existing ancestor up to bfs_depth levels
      3. If still not found, full rglob for “Mess-Paraver” under the nearest existing parent
    """
    for anc in (base, *base.parents):
        if not (anc.exists() and anc.is_dir()):
            continue

        if anc.name.lower() == "mess-paraver":
            return anc

        queue = deque([(anc, 0)])
        while queue:
            curr, depth = queue.popleft()
            if depth >= bfs_depth:
                continue
            for child in curr.iterdir():
                if child.is_dir():
                    if child.name.lower() == "mess-paraver":
                        return child
                    queue.append((child, depth + 1))

    search_root = next(
        (anc for anc in (base, *base.parents) if anc.exists()), Path.cwd()
    )
    for candidate in search_root.rglob("Mess-Paraver"):
        if candidate.is_dir():
            return candidate

    return None


def read_db(data_path: str) -> pd.DataFrame:
    """
    Robust cpu_memory_db.csv loader.

    1) Normalize input (strip, expanduser, resolve).
    2) If it’s a .csv file and exists, load it immediately.
    3) If it’s a directory, try <dir>/cpu_memory_db.csv.
    4) ONLY if both fail, climb/search for the real 'Mess-Paraver' install root:
         – Check ancestors & BFS up to 2 levels
         – Then full rglob for a 'Mess-Paraver' folder
       Then load <MP_root>/data/cpu_memory_db.csv.
    5) If that still fails, error out listing every path we tried.
    """
    filename = "cpu_memory_db.csv"
    p = Path(data_path.strip()).expanduser().resolve()

    if p.suffix.lower() == ".csv":
        if p.is_file():
            return pd.read_csv(p)

    if p.is_dir():
        direct = p / filename
        if direct.is_file():
            return pd.read_csv(direct)

    mp_root = _find_mp_root(p)
    if mp_root:
        data_path = mp_root / "data" / filename
        if data_path.is_file():
            return pd.read_csv(data_path)

    tried = []
    if p.suffix.lower() == ".csv":
        tried.append(f"  • direct file: {p}")
    if p.is_dir():
        tried.append(f"  • in directory: {p/filename}")
    tried.append("  • searched ancestors & BFS & rglob for 'Mess-Paraver'")
    raise FileNotFoundError(
        "cpu_memory_db.csv not found; attempted:\n" + "\n".join(tried)
    )


def print_supported_systems(data_path: str) -> None:
    df = read_db(data_path)
    print("CPU - DRAM")
    print("-----------------")
    for _, row in df.iterrows():
        print(
            f"{row['pmu_type']} {row['cpu_microarchitecture']} {row['cpu_model']} - {row['memory_system']}"
        )


def get_row_from_db(data_path: str, cpu_model: str, memory_system: str) -> dict:
    # get PMU type and microarchitecture from DB
    df = read_db(data_path)
    check_curves_exist(df, cpu_model, memory_system)

    filt_df = df[
        (df["cpu_model"] == cpu_model) & (df["memory_system"] == memory_system)
    ]
    if len(filt_df) > 1:
        raise Exception(
            f"There are multiple instances in the database with {cpu_model} CPU model and {memory_system} memory system."
        )

    return filt_df.iloc[0].to_dict()


def get_curves_path(
    data_path: str,
    cpu_model: str,
    memory_system: str,
    pmu_type: str = None,
    cpu_microarch: str = None,
) -> str:
    if pmu_type is None or cpu_microarch is None:
        # Get data from DB
        row = get_row_from_db(data_path, cpu_model, memory_system)
        pmu_type = row["pmu_type"]
        cpu_microarch = row["cpu_microarchitecture"]
    else:
        # check it here because get_row_from_db also checks it, so if this function is not executed on the previous if,
        # we have to make the check here
        df = pd.read_csv(os.path.join(data_path, "cpu_memory_db.csv"))
        check_curves_exist(df, cpu_model, memory_system)

    # build curves path
    bw_lats_folder = os.path.join(data_path, "bw_lat_curves")
    curves_folder = f"{memory_system}__{pmu_type}__{cpu_microarch}__{cpu_model}"
    return os.path.join(data_path, bw_lats_folder, curves_folder)


def set_curves(data_path: str, cpu_model: str, memory_system: str) -> bool:
    global curves
    curves_path = get_curves_path(data_path, cpu_model, memory_system)
    curves = Curves(curves_path, display_warnings=display_warnings)
    return True


def set_display_warnings(display_w: int) -> bool:
    global display_warnings
    if display_w == 0:
        display_warnings = False
    else:
        display_warnings = True
    return True


def get_curves_available_read_ratios() -> list:
    if curves is None:
        raise Exception("Curves are not set. Please call set_curves() function first.")
    return curves.get_read_ratios()


def get_curve(read_ratio: float):
    return curves.get_curve(read_ratio)


def get_memory_properties_from_bw(
    cpu_freq_ghz: float,
    write_ratio: float,
    curve_read_ratio: float,
    bandwidth_gbs: float,
    group_by_mc: bool,
    mcs_per_socket: int,
) -> dict:
    # bws: list of bandwidths in MB/s
    # lats: list of latencies in CPU cycles
    # write_ratio:
    # bandwidth_gbs: bandwidth in GB/s

    # Validate parameters
    check_param_types(
        {
            # 'Memory system': (memory_system, str),
            "Write ratio": (write_ratio, float),
            "Bandwidth": (bandwidth_gbs, float),
        }
    )
    check_non_negative(
        {
            "Write ratio": write_ratio,
            "Bandwidth": bandwidth_gbs,
        }
    )

    stress_score = -1

    # print(f'Write ratio: {write_ratio}')
    # print(f'Bandwidth: {round(bandwidth, 2)} GB/s')

    # The following 2 commented lines are now executed on profet.cpp.
    # Keep them here for now until we reach a final decision on where this should go.
    # specific_curves_path = f'{memory_system}__{pmu_type}__{cpu_microarch}__{cpu_model}'
    # full_curves_path = os.path.join(project_path, 'py_profet', 'bw_lat_curves', specific_curves_path)
    # get latencies and bandwidths from curve (in CPU cycles and GB/s, respectively)

    curve_obj = curves.get_curve(curve_read_ratio)

    # predicted latency in curve
    current_bw_gbs = Bandwidth(
        bandwidth_gbs * mcs_per_socket if group_by_mc else bandwidth_gbs, "GBps"
    )

    # if current_bw_gbs > curve_obj.get_max_bw("GBps"):
    #     bandwidth_gbs = curve_obj.get_max_bw("GBps").value
    #     current_bw_gbs = Bandwidth(bandwidth_gbs, "GBps")

    if current_bw_gbs > curve_obj.get_max_bw("GBps"):
        current_bw_gbs = curve_obj.get_max_bw("GBps")
        bandwidth_gbs = (
            current_bw_gbs.value / mcs_per_socket
            if group_by_mc
            else current_bw_gbs.value
        )
        pred_lat = curve_obj.get_lat(current_bw_gbs)
        stress_score = 1
    else:
        try:
            pred_lat = curve_obj.get_lat(current_bw_gbs)
        except OvershootError as e:
            print(f"WARNING: Overshoot error: {e}")
            max_bw_gbs = curve_obj.get_max_bw("GBps")
            print(f"Maximum bandwidth: {max_bw_gbs}")
            print(f"Current bandwidth: {current_bw_gbs}")
            print(f"Maximum latency: { curve_obj.get_max_lat()}")
            print()
            # bandwidth_gbs = max_bw_gbs
            # current_bw_gbs = max_bw_gbs
            # pred_lat = curve_obj.get_lat(current_bw_gbs)
            try:
                current_bw_gbs = curve_obj.get_max_bw("GBps")
                bandwidth_gbs = (
                    current_bw_gbs.value / mcs_per_socket
                    if group_by_mc
                    else current_bw_gbs.value
                )
                pred_lat = curve_obj.get_lat(current_bw_gbs)
                pred_lat = curve_obj.get_lat(
                    current_bw_gbs / mcs_per_socket if group_by_mc else current_bw_gbs
                )
            except:
                print("Warning, something happened")
                pred_lat = None
                # return None

    # maximum bw
    max_bw_gbs = curve_obj.get_max_bw("GBps")
    # maximum latency (in CPU cycles) and bandwidth (GB/s) for the given read ratio
    max_lat = curve_obj.get_max_lat()
    # lead-off latency
    lead_off_lat = curve_obj.get_lead_off_lat()
    # stress score
    # print(curve_obj.lats)
    # print(max_lat, lead_off_lat)
    if stress_score == -1:
        stress_score = curve_obj.get_stress_score(
            current_bw_gbs, pred_lat, lead_off_lat, max_lat
        )
        if stress_score is None:
            stress_score = 1

    if pred_lat is not None:
        if isinstance(pred_lat, int):
            print(f"WARNING: Predicted latency is {pred_lat}. This is likely an error.")
            # pred_lat = Latency(pred_lat, "cycles")
        if pred_lat.value == 0:
            print(f"WARNING: Predicted latency is 0. This is likely an error.")

    # print(f'Write ratio: {round(write_ratio, 2)}; Curve RR: {curve_read_ratio}, Bw: {current_bw_gbs}; Max. BW: {max_bw_gbs}')
    # print(f'Lat: {pred_lat}; Max. Lat: {max_lat}; Lead-off Lat: {lead_off_lat}')
    # print(f'Stress score: {round(stress_score, 2)}')
    # print()

    return {
        "write_ratio": write_ratio,
        "bandwidth": bandwidth_gbs,
        "max_bandwidth": max_bw_gbs.value,
        "latency": -1 if pred_lat is None else pred_lat.value / cpu_freq_ghz,
        "lead_off_latency": lead_off_lat.value / cpu_freq_ghz,
        "max_latency": max_lat.value / cpu_freq_ghz,
        "stress_score": stress_score,
    }
