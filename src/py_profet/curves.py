'''
Copyright (C) 2023 Isaac Boixaderas - All Rights Reserved
You may use, distribute and modify this code under the
terms of the BSD-3 license.

You should have received a copy of the BSD-3 license with
this file. If not, please visit: https://opensource.org/licenses/BSD-3-Clause
'''

import os
import numpy as np
import math
import warnings
import json

class BadFileFormatError(Exception):
    def __init__(self, file):
        self.file = file

    def __str__(self):
        return f'Bandwidth-latency file {self.file} has incorrect format'

class OvershootError(Exception):
    def __init__(self, read_ratio, requested_bw):
        self.read_ratio = read_ratio
        self.write_ratio = 100 - read_ratio
        self.requested_bw = requested_bw

    def __str__(self):
        return f'Cannot estimate latency for bandwidth {round(self.requested_bw, 2)} using bandwidth-latency curve for a write ratio of {self.write_ratio}%. ' +\
                'Provided bandwidth larger than the largest recorded bandwidth for said curve.'

class RatioRangesError(Exception):
    def __init__(self, read_ratio):
        self.read_ratio = read_ratio
        self.write_ratio = 100 - read_ratio

    def __str__(self):
        if self.write_ratio % 2 != 0:
            return f'Write ratio has to be an even value. The given write ratio is {self.write_ratio}%.'
        # elif self.write_ratio > 50:
        #     return f'Write ratios over 50% are not currently supported. The given write ratio is {self.write_ratio}%.'
        elif self.write_ratio < 0:
            return f'Write ratios under 0% are not possible. The given write ratio is {self.write_ratio}%.'
        else:
            return f'Unknown error for the given write ratio of {self.write_ratio}%.'

def bw_overshoot_warning(read_ratio, requested_bw, bw_units):
    write_ratio = 100 - read_ratio
    warn = f'Cannot estimate latency for bandwidth {round(requested_bw, 2)} {bw_units} using bandwidth-latency curve for a write ratio of {write_ratio}%. ' +\
           f'Provided bandwidth larger than the largest recorded bandwidth for said curve.'
    warnings.warn(warn)

def bw_low_warning(requested_bw, bw_units, lead_off_latency):
    warn = f'Provided bandwidth {round(requested_bw, 2)} {bw_units} smaller than the smallest recorded bandwidth for the curve. ' +\
           f'Using latency of {round(lead_off_latency, 2)} cycles, corresponding to the lead-off-latency.'
    warnings.warn(warn)

def read_ratio_mismatch_warning(read_ratio: float, curve_read_ratio: float) -> None:
    warn = f'The given read ratio of {read_ratio}% may be too far from the ones computed in the curves. ' +\
           f'Using closest read ratio of {curve_read_ratio}%.'
    warnings.warn(warn)

def check_ratio(read_ratio):
    if read_ratio > 100 or read_ratio < 0:
        raise RatioRangesError(read_ratio)
    return True

def check_units(bw_units: str) -> bool:
    if bw_units not in ['GB/s', 'MB/s', 'kB/s', 'B/s']:
        raise Exception(f'Bandwidth units {bw_units} not supported. Supported units are GB/s, MB/s, kB/s, and B/s.')
    return True

def get_closest_read_ratio(read_ratio: float, curves_read_ratios: list, display_warnings: bool = True):
    closest_curve_read_ratio = min(curves_read_ratios, key=lambda x: abs(x - read_ratio))

    # TODO hardcoded difference of 2% between ratios
    if abs(closest_curve_read_ratio - read_ratio) > 2 and display_warnings:
        read_ratio_mismatch_warning(read_ratio, closest_curve_read_ratio)

    return int(closest_curve_read_ratio)

def get_bws_lats_old_file(curves_path: str, filename: str):
    with open(os.path.join(curves_path, filename)) as f:
        bws = []
        lats = []
        for line in f.readlines():
            tokens = line.split()
            if len(tokens) >= 2 and tokens[0][0] != '#':
                bws.append(float(tokens[0]))
                lats.append(float(tokens[1]))
        if not len(bws) == len(lats) or len(bws) == 0 or len(lats) == 0:
            raise BadFileFormatError(curves_path)
    return list(reversed(bws)), list(reversed(lats))

def read_curves_file(curves_path: str, display_warnings: bool = True) -> dict:
    """
    Reads bandwidth-latency curves from a file.

    Args:
        curves_path (str): path to the file containing the curves
        display_warnings (bool): whether to display warnings or not

    Returns:
        dictionary of curves, where keys are read ratios and values are Curve objects
    """
    # TODO keep it hybrid between new format and old format for now. In future, remove the non-json part
    curves = {}
    if curves_path.endswith('.json'):
        with open(curves_path, 'r') as f:
            curves_json = json.load(f)
        for read_ratio, curve_raw in curves_json.items():
            read_ratio = int(read_ratio)
            bws, lats = zip(*curve_raw)
            curves[read_ratio] = Curve(read_ratio, bws=bws, lats=lats, display_warnings=display_warnings)
    else:
        if not os.path.isdir(curves_path):
            raise Exception(f'Path {curves_path} should be a directory or a json file.')
        # read all curve files in the directory
        filenames = [f for f in os.listdir(curves_path) if 'bwlat' in f and f.endswith('.txt')]
        for filename in filenames:
            bws, lats = get_bws_lats_old_file(curves_path, filename)
            read_ratio = int(filename.split('_')[1].replace('.txt', ''))
            curves[read_ratio] = Curve(read_ratio, bws=bws, lats=lats, display_warnings=display_warnings)
    return curves


class Curve:
    # def __init__(self, curves_path: str, read_ratio: float, display_warnings: bool = True):
    #     check_ratio(read_ratio)
    #     self.read_ratio = read_ratio
    #     self.display_warnings = display_warnings
    #     # computed curves do not have all read ratios. Find the closest one.
    #     # get the computed read ratios for the curves
    #     # sort them for guaranteeing that we will always obtain the same results
    #     curves_read_ratios = sorted([int(f.split('_')[1].replace('.txt', '')) for f in os.listdir(curves_path) if 'bwlat' in f])
    #     # calculate the closest ratio in the files
    #     # TODO bisection method would be faster
    #     self.closest_curve_read_ratio = min(curves_read_ratios, key=lambda x: abs(x - read_ratio))

    #     # TODO hardcoded difference of 2% between ratios
    #     if abs(self.closest_curve_read_ratio - read_ratio) > 2:
    #         write_ratio = 100 - read_ratio
    #         closest_curve_write_ratio = 100 - self.closest_curve_read_ratio
    #         if self.display_warnings:
    #             write_ratio_mismatch_warning(write_ratio, closest_curve_write_ratio)

    #     self.bws = []
    #     self.lats = []

    #     filename = os.path.join(curves_path, f'bwlat_{self.closest_curve_read_ratio}.txt')
    #     with open(filename) as f:
    #         for line in reversed(f.readlines()):
    #             tokens = line.split()
    #             if len(tokens) >= 2 and tokens[0][0] != '#':
    #                 self.bws.append(float(tokens[0]))
    #                 self.lats.append(float(tokens[1]))
    #         if not len(self.bws) == len(self.lats) or len(self.bws) == 0 or len(self.lats) == 0:
    #             raise BadFileFormatError(filename)

    def __init__(self, read_ratio: float, curves_path: str = None, bws: list = [],
                 lats: list = [], display_warnings: bool = True):
        # BWS in MB/s and lats in cycles
        check_ratio(read_ratio)

        if len(bws) != len(lats):
            raise Exception(f'Number of bandwidths ({len(bws)}) and latencies ({len(lats)}) do not match.')

        # round read ratio to the closest integer
        self.read_ratio = int(round(read_ratio, 0))
        self.display_warnings = display_warnings
        if curves_path is not None:
            if display_warnings and (len(bws) != 0 or len(lats) != 0):
                warnings.warn('Curves_path, bws and lats were provided. Reading from curves_path and ignoring the given values for bandwidths and latencies.')
            # TODO keep it hybrid between new format and old format for now. In future, remove the non-json part
            # TODO a lot of repeated code with read_curves_file
            if curves_path.endswith('.json'):
                with open(curves_path, 'r') as f:
                    curves_json = json.load(f)
                    if self.read_ratio not in curves_json:
                        # raise Exception(f'No curve for read ratio {self.read_ratio}%.')
                        self.read_ratio = get_closest_read_ratio(self.read_ratio, list(curves_json.keys()), display_warnings)
                    curve_raw = curves_json[self.read_ratio]
                    self.bws, self.lats = zip(*curve_raw)
            else:
                if not os.path.isdir(curves_path):
                    raise Exception(f'Path {curves_path} should be a directory or a json file.')
                read_ratios = [float(f.split('_')[1].replace('.txt', '')) for f in os.listdir(curves_path) if 'bwlat_' in f and f.endswith('.txt')]
                if self.read_ratio not in read_ratios:
                    # raise Exception(f'No curve for read ratio {self.read_ratio}%.')
                    self.read_ratio = get_closest_read_ratio(self.read_ratio, read_ratios, display_warnings)
                filename = f'bwlat_{int(self.read_ratio)}.txt'
                self.bws, self.lats = get_bws_lats_old_file(curves_path, filename)
        else:
            if len(bws) == 0 or len(lats) == 0:
                raise Exception('Curves_path was not provided and no bandwidths and latencies were given.')
            self.bws = bws
            self.lats = lats


    def get_lat(self, bw, bw_units):
        """
        Returns latency for provided bandwidth.
        Linear interpolation is used to calculate latency between two recorded points.

        If provided bandwidth is smaller than the smallest recorded sample, the latency corresponding to the smallest recorded bandwidth is returned.
        The rationale is that curve at this point is usually constant.

        If provided banwdith is larger than the largest recorded sample, an exception is thrown.
        The rationale is that the curve beyond the max bandwidth is exponential and it is difficult to find a good estimate for latency.
        """
        check_units(bw_units)

        if bw == 0:
            # special case when bandwidth equals 0, latency is undefined
            return -1

        # transform bandwidth to MB/s for the curves
        bw_mbps = self._bw_units_converter(bw, from_unit=bw_units, to_unit='MB/s')

        if bw_mbps < self.bws[0]:
            # show warning and return lead-off latency when bandwidth is below-off the curve
            if self.display_warnings:
                bw_low_warning(bw_mbps, bw_units='MB/s', lead_off_latency=self.lats[0])
            return self.lats[0]

        # i = bisect.bisect_left(self.bws, bw)
        i = self._get_bw_posterior_index(bw_mbps, bw_units='MB/s')
        if i + 1 >= len(self.bws):
            # show warning and return -1 when bandwidth is above-off the curve
            if self.display_warnings:
                bw_overshoot_warning(self.read_ratio, bw_mbps, bw_units='MB/s')
            return -1
            # raise OvershootError(self.closest_curve_read_ratio, bw)

        # renaming variables to easily read the linear interpolation formula
        x = bw_mbps
        x1 = self.bws[i - 1]
        y1 = self.lats[i - 1]
        x2 = self.bws[i]
        y2 = self.lats[i]
        # linear interpolation
        return y1 + (x - x1) / (x2 - x1) * (y2 - y1)


    def get_max_bw(self):
        # bandwidth in GB/s (curves are in MB/s)
        return max(self.bws) / 1000


    def get_max_lat(self):
        return max(self.lats)


    def get_lead_off_lat(self):
        # return latency for minimum bandwidth
        min_bw_idx = np.argmin(self.bws)
        return self.lats[min_bw_idx]
    

    def get_stress_score(self, bandwidth, bw_units, lat=None, lead_off_lat=None, max_lat=None):
        check_units(bw_units)

        at_least_one_none = lat is None or lead_off_lat is None or max_lat is None
        all_none = lat is None and lead_off_lat is None and max_lat is None
        if at_least_one_none and not all_none:
            raise Exception('lat, lead_off_lat, and max_lat must be either all None or all have values.')

        if bandwidth == 0:
            return 0

        idx = self._get_bw_posterior_index(bandwidth, bw_units)
        if idx >= len(self.bws):
            return None

        if at_least_one_none:
            lat, lead_off_lat, max_lat = self.get_lat(bandwidth, bw_units), self.get_lead_off_lat(), self.get_max_lat()
        # Couldn't we assume that idx - 1 has lower BW and latency than idx?
        bw_prev, bw_post, lat_prev, lat_post = self._get_pre_and_post_bw_and_lat(idx)
        # prev and post bw are in MB/s
        return self._score_computation(max_lat, lead_off_lat, lat, bw_prev, bw_post, 'MB/s', lat_prev, lat_post)


    def _get_bw_posterior_index(self, bandwidth, bw_units):
        check_units(bw_units)

        # transform bandwidth to MB/s for the curves
        bandwidth = self._bw_units_converter(bandwidth, from_unit=bw_units, to_unit='MB/s')
        # get the index of the first bandwidth in the curve that is greater than the given bandwidth
        i = 0
        # assuming self.bws are sorted in ascending order
        while i < len(self.bws) and self.bws[i] < bandwidth:
            i += 1
        return i


    def _score_computation(self, max_latency, lead_off_latency, latency, bw_prev, bw_post, bw_units, lat_prev, lat_post):
        # prev and post BWs are expected in GB/s for properly calculating the angle
        bw_prev = self._bw_units_converter(bw_prev, from_unit=bw_units, to_unit='GB/s')
        bw_post = self._bw_units_converter(bw_post, from_unit=bw_units, to_unit='GB/s')
        angle = math.degrees(math.atan2((lat_post - lat_prev), (bw_post - bw_prev)))
        score_angle = angle / 90
        score_latency = (latency - lead_off_latency) / (max_latency - lead_off_latency)
        latency_factor = 0.8
        score = latency_factor * score_latency + (1 - latency_factor) * score_angle
        # score 1 is the worst and 0 is the best
        return score


    def _get_pre_and_post_bw_and_lat(self, idx):
        # get the bandwidth and latency of the point before and after the given index.
        # the returned values are in MB/s (like in the curves)
        if idx == 0:
            # if idx is 0, there is no point before it
            return self.bws[0], self.bws[0], self.lats[0], self.lats[0]

        x1 = self.bws[idx]
        x2 = self.bws[idx - 1]

        xmin, xmax = min(x1, x2), max(x1, x2)
        imin, imax = 0, 0

        if xmin == x1:
            imin, imax = idx, idx - 1
        else:
            imin, imax = idx - 1, idx

        ymin, ymax = self.lats[imin], self.lats[imax]
        return xmin, xmax, ymin, ymax


    def _bw_units_converter(self, bw, from_unit, to_unit):
        check_units(from_unit)
        check_units(to_unit)

        units = {
            'B/s': 1,
            'kB/s': 1e3,
            'MB/s': 1e6,
            'GB/s': 1e9,
        }

        # Convert the input value to bytes per second (B/s)
        value_bps = bw * units[from_unit]
        # Convert the value in bps to the desired output unit
        converted_value = value_bps / units[to_unit]

        return converted_value


class Curves:
    """ Curves class for loading all the curve objects (bandwidth and latency points) from the curve files. """

    def __init__(self, curves_path: str, display_warnings: bool = True):
        self.curves = read_curves_file(curves_path, display_warnings)

    def get_curve(self, read_ratio: float) -> Curve:
        """
        Returns Curve object for the given read-write ratio

        Args:
            read_ratio (float): read ratio
        """
        if read_ratio not in self.curves:
            # raise Exception(f'No curve for read ratio {read_ratio}%.')
            read_ratio = get_closest_read_ratio(read_ratio, list(self.curves.keys()), display_warnings=True)
        return self.curves[read_ratio]

    def get_lat(self, read_ratio: float, bw: float, bw_units: str):
        """
        Returns latency (in cycles) for given read-write ratio and bandwidth

        Args:
            read_ratio (float): read ratio
            bw (float): bandwidth
            bw_units (str): units of bandwidth (check supported_bw_units in utils.py) of the given bandwith
        """
        # assert(read_ratio >= 50 and read_ratio <= 100 and read_ratio % 2 == 0)
        if read_ratio not in self.curves:
            # raise Exception(f'No curve for read ratio {read_ratio}%.')
            read_ratio = get_closest_read_ratio(read_ratio, list(self.curves.keys()), display_warnings=True)
        return self.curves[read_ratio].get_lat(bw, bw_units)

    def get_max_bw(self, read_ratio: float) -> float:
        """
        Returns maximum recorded bandwidth (in GB/s) for the given read-write ratio

        Args:
            read_ratio (float): read ratio
        """
        if read_ratio not in self.curves:
            # raise Exception(f'No curve for read ratio {read_ratio}%.')
            read_ratio = get_closest_read_ratio(read_ratio, list(self.curves.keys()), display_warnings=True)
        return self.curves[read_ratio].get_max_bw()

    def get_max_lat(self, read_ratio: float) -> float:
        """
        Returns maximum recorded latency (in cycles) for the given read-write ratio

        Args:
            read_ratio (float): read ratio
            lat_units (str): units of latency (check supported_lat_units in utils.py) of the returned latency
            freq_ghz (float): memory frequency in GHz (only needed when latency units are in time units, e.g. ns, us, s)
        """
        if read_ratio not in self.curves:
            # raise Exception(f'No curve for read ratio {read_ratio}%.')
            read_ratio = get_closest_read_ratio(read_ratio, list(self.curves.keys()), display_warnings=True)
        return self.curves[read_ratio].get_max_lat()

    def get_lead_off_lat(self, read_ratio: float) -> float:
        """
        Returns lead-off (minimum) latency (in cycles) for the given read-write ratio

        Args:
            read_ratio (float): read ratio
        """
        if read_ratio not in self.curves:
            # raise Exception(f'No curve for read ratio {read_ratio}%.')
            read_ratio = get_closest_read_ratio(read_ratio, list(self.curves.keys()), display_warnings=True)
        return self.curves[read_ratio].get_lead_off_lat()

    def get_stress_score(self, read_ratio: float, bandwidth: float, bw_units: str) -> float:
        """
        Returns stress score for the given read-write ratio and bandwidth

        Args:
            read_ratio (float): read ratio
            bandwidth (float): bandwidth
            bw_units (str): units of bandwidth (check supported_bw_units in utils.py) of the given bandwith
        """
        if read_ratio not in self.curves:
            # raise Exception(f'No curve for read ratio {read_ratio}%.')
            read_ratio = get_closest_read_ratio(read_ratio, list(self.curves.keys()), display_warnings=True)
        return self.curves[read_ratio].get_stress_score(bandwidth, bw_units)
    
    # def get_bws(self, bw_units: str) -> dict:
    #     """
    #     Returns bandwidths of the curves

    #     Args:
    #         bw_units (str): units of bandwidth (check supported_bw_units in utils.py) of the returned bandwidths
    #     """
    #     curves = {}
    #     for read_ratio, curve in self.curves.items():
    #         curves[read_ratio] = curve.get_bws(bw_units)
    #     return curves
    
    # def get_lats(self) -> dict:
    #     """
    #     Returns latencies (in cycles) of the curves

    #     Args:
    #     """
    #     curves = {}
    #     for read_ratio, curve in self.curves.items():
    #         curves[read_ratio] = curve.get_lats()
    #     return curves
    
    # def get_curves_bws_lats(self, bw_units: str, lat_units: str, freq_ghz: float = None) -> dict:
    #     """
    #     Returns bandwidths and latencies in a list of tuples (bw-lat pairs) of the curves

    #     Args:
    #         bw_units (str): units of bandwidth (check supported_bw_units in utils.py) of the returned bandwidths
    #         lat_units (str): units of latency (check supported_lat_units in utils.py) of the returned latencies
    #         freq_ghz (float): memory frequency in GHz (only needed when latency units are in time units, e.g. ns, us, s)
    #     """
    #     curves = {}
    #     for read_ratio, curve in self.curves.items():
    #         curves[read_ratio] = curve.get_curve_bws_lats(bw_units, lat_units, freq_ghz)
    #     return curves