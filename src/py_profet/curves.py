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
        return f'''Cannot estimate latency for bandwidth {self.requested_bw} using bandwidth-latency curve for a write ratio of {self.write_ratio}%.
                Provided bandwidth larger than the largest recorded bandwidth for said curve.'''

class OvershootError(Exception):
    def __init__(self, read_ratio, requested_bw):
        self.read_ratio = read_ratio
        self.write_ratio = 100 - read_ratio
        self.requested_bw = requested_bw

    def __str__(self):
        return f'''Cannot estimate latency for bandwidth {self.requested_bw} using bandwidth-latency curve for write ratio of {self.write_ratio}%.
                Provided bandwidth larger than the largest recorded bandwidth for said curve.'''

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

def overshoot_warning(read_ratio, requested_bw):
    write_ratio = 100 - read_ratio
    warn = f'''Cannot estimate latency for bandwidth {requested_bw/1000} GB/s using bandwidth-latency curve for a write ratio of {write_ratio}%.
            Provided bandwidth larger than the largest recorded bandwidth for said curve.'''
    warnings.warn(warn)

def write_ratio_mismatch_warning(write_ratio: float, curve_write_ratio: float) -> None:
    warn = f'The given write ratio of {write_ratio}% may be too far from the ones computed in the curves. ' +\
           f'Using closest write ratio of {curve_write_ratio}%.'
    warnings.warn(warn)

def check_ratio(read_ratio):
    if read_ratio > 100 or read_ratio < 0:
        raise RatioRangesError(read_ratio)
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

    def get_lat(self, bw):
        """
        Returns latency for provided bandwidth in GB/s.
        Linear interpolation is used to calculate latency between two recorded points.

        If provided bandwidth is smaller than the smallest recorded sample, the latency corresponding to the smallest recorded bandwidth is returned.
        The rationale is that curve at this point is usually constant.

        If provided banwdith is larger than the largest recorded sample, an exception is thrown.
        The rationale is that the curve beyond the max bandwidth is exponential and it is difficult to find a good estimate for latency.
        """
        if bw == 0:
            # special case when bandwidth equals 0, latency is undefined
            return -1

        # given bandwidth in GB/s, transform it to MB/s for the curves
        bw *= 1000
        if bw < self.bws[0]:
            # TODO this message should be logged as a warning
            # print("Lower BW than recorded in curve")
            return self.lats[0]

        # # find the interval that contains the provided bandwidth
        # i = 0
        # while i < len(self.bws) and self.bws[i] < bw:
        #     i += 1

        # i = bisect.bisect_left(self.bws, bw)
        i = self._get_bw_posterior_index(bw)
        if i + 1 >= len(self.bws):
            # show warning and return -1 when bandwidth is off the curve
            if self.display_warnings:
                overshoot_warning(self.closest_curve_read_ratio, bw)
            return -1
            # raise OvershootError(self.closest_curve_read_ratio, bw)

        # renaming variables to easily read the linear interpolation formula
        x = bw
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
    
    def get_stress_score(self, bandwidth):
        lat = self.get_lat(bandwidth)
        # given bandwidth in GB/s, transform it to MB/s for the curves
        bandwidth *= 1000
        # i = 0
        # # assuming self.bws are sorted in ascending order
        # while i < len(self.bws) and self.bws[i] < bandwidth:
        #     i += 1

        # if i >= len(self.bws):
        #     return None
        
        # print(bandwidth, self.get_lat(bandwidth))
        idx = self._get_bw_posterior_index(bandwidth)

        if idx >= len(self.bws):
            return None

        # x_prev, y_prev = self.bws[idx - 1], self.lats[idx - 1]
        # x_post, y_post = self.bws[idx], self.lats[idx]
        # print(bandwidth, idx, 'X', x_prev, x_post, y_prev, y_post)
        # return self._score_computation(self.get_max_lat(), self.get_lead_off_lat(), self.get_lat(bandwidth),
        #                                x_prev, x_post, y_prev, y_post)
        # TODO this is not line computation anymore, it is a point computation
        # Couldn't we assume that idx - 1 has lower BW and latency than idx?
        x_prev, x_post, y_prev, y_post = self._line_computation(idx)
        # print(latency, lat)
        return self._score_computation(self.get_max_lat(), self.get_lead_off_lat(),
                                       lat, x_prev, x_post, y_prev, y_post)

    def _get_bw_posterior_index(self, bandwidth):
        # get the index of the first bandwidth in the curve that is greater than the given bandwidth
        i = 0
        # assuming self.bws are sorted in ascending order
        while i < len(self.bws) and self.bws[i] < bandwidth:
            i += 1
        return i

    def _score_computation(self, max_latency, lead_off_latency, latency, x_prev, x_post, y_prev, y_post):
        angle = math.degrees(math.atan2((y_post - y_prev), (x_post - x_prev)))
        # score 1 is the worst and 0 is the best
        score_angle = angle / 90
        score_latency = (latency - lead_off_latency) / (max_latency - lead_off_latency)
        score = (score_angle + score_latency) / 2
        # print(latency, lead_off_latency, max_latency, score_latency, score_angle, score)
        return score

    def _line_computation(self, idx):
        # print(i, len(self.bws), bandwidth, self.bws[0], self.bws[-1])
        x1 = self.bws[idx]
        # y1 = self.lats[idx]
        x2 = self.bws[idx - 1]
        # y2 = self.lats[idx - 1]
        # x_coords, y_coords = (x1, x2), (y1, y2)
        # A = np.vstack([x_coords, np.ones(len(x_coords))]).T
        # m, c = np.linalg.lstsq(A, y_coords, rcond=None)[0]
        # # print("Line Solution is y = {m}x + {c}".format(m=m,c=c))

        xmin, xmax = min(x1, x2), max(x1, x2)
        imin, imax = 0, 0

        if xmin == x1:
            imin, imax = idx, idx + 1
        else:
            imin, imax = idx + 1, idx

        ymin, ymax = self.lats[imin], self.lats[imax]
        # latency = (m * bandwidth) + c

        # return xmin, xmax, ymin, ymax, latency
        return xmin, xmax, ymin, ymax