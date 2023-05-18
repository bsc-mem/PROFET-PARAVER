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

def write_ratio_mismatch_warning(write_ratio: float, curve_write_ratio: float) -> None:
    warn = f'The given write ratio of {write_ratio}% may be too far from the ones computed in the curves. ' +\
           f'Using closest write ratio of {curve_write_ratio}%.'
    warnings.warn(warn)

def check_ratio(read_ratio):
    if read_ratio > 100 or read_ratio < 0:
        raise RatioRangesError(read_ratio)
    return True

def check_units(bw_units: str) -> bool:
    if bw_units not in ['GB/s', 'MB/s', 'kB/s', 'B/s']:
        raise Exception(f'Bandwidth units {bw_units} not supported. Supported units are GB/s, MB/s, kB/s, and B/s.')
    return True


class Curve:
    def __init__(self, curves_path: str, read_ratio: float, display_warnings: bool = True):
        check_ratio(read_ratio)
        self.read_ratio = read_ratio
        self.display_warnings = display_warnings
        # computed curves do not have all read ratios. Find the closest one.
        # get the computed read ratios for the curves
        # sort them for guaranteeing that we will always obtain the same results
        curves_read_ratios = sorted([int(f.split('_')[1].replace('.txt', '')) for f in os.listdir(curves_path) if 'bwlat' in f])
        # calculate the closest ratio in the files
        # TODO bisection method would be faster
        self.closest_curve_read_ratio = min(curves_read_ratios, key=lambda x: abs(x - read_ratio))

        # TODO hardcoded difference of 2% between ratios
        if abs(self.closest_curve_read_ratio - read_ratio) > 2:
            write_ratio = 100 - read_ratio
            closest_curve_write_ratio = 100 - self.closest_curve_read_ratio
            if self.display_warnings:
                write_ratio_mismatch_warning(write_ratio, closest_curve_write_ratio)

        self.bws = []
        self.lats = []

        filename = os.path.join(curves_path, f'bwlat_{self.closest_curve_read_ratio}.txt')
        with open(filename) as f:
            for line in reversed(f.readlines()):
                tokens = line.split()
                if len(tokens) >= 2 and tokens[0][0] != '#':
                    self.bws.append(float(tokens[0]))
                    self.lats.append(float(tokens[1]))
            if not len(self.bws) == len(self.lats) or len(self.bws) == 0 or len(self.lats) == 0:
                raise BadFileFormatError(filename)


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
                bw_overshoot_warning(self.closest_curve_read_ratio, bw_mbps, bw_units='MB/s')
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
    

    def get_stress_score(self, bandwidth, bw_units):
        check_units(bw_units)

        if bandwidth == 0:
            return 0

        idx = self._get_bw_posterior_index(bandwidth, bw_units)
        if idx >= len(self.bws):
            return None

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