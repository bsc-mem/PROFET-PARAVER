'''
Copyright (C) 2023 Isaac Boixaderas - All Rights Reserved
You may use, distribute and modify this code under the
terms of the BSD-3 license.

You should have received a copy of the BSD-3 license with
this file. If not, please visit: https://opensource.org/licenses/BSD-3-Clause
'''

import unittest
import io
import sys
import numpy as np
import pandas as pd


def metric_val(line_sp, metric_id, precision):
    offs = 6 # offset where metric ids start in the line split
    metric_ids = [line_sp[offs:][i] for i in range(0, len(line_sp[offs:]), 2)]
    
    if metric_id not in metric_ids:
        return np.nan
    
    # position of the metric value in the line split
    pos = np.where(np.array(metric_ids) == metric_id)[0][0]*2 + offs + 1
    if line_sp[pos] < 0:
        return line_sp[pos]
    return line_sp[pos] / 10**precision


def prv_out_to_df(prv_path, precision, base_evt, exclude_original_trace):
    df = []
    with open(prv_path, 'r') as f:
        # skip header
        for line in f.readlines()[1:]:
            # skip comments and communicator lines
            if line[0] == '#' or line[0] == 'c':
                continue

            l = list(map(lambda i: int(i), line.split(':')))
            app_id = l[2]
            if not exclude_original_trace and app_id == 1:
                pass
                # df.append({'node': 1, 'time': l[5]})
            else:
                df.append({
                    'node': l[2],
                    'socket': l[3],
                    'mc': l[4],
                    'time': l[5],
                    'wratio': metric_val(l, base_evt + 1, precision),
                    'bw': metric_val(l, base_evt + 2, precision),
                    'max_bw': metric_val(l, base_evt + 3, precision),
                    'lat': metric_val(l, base_evt + 4, precision),
                    'min_lat': metric_val(l, base_evt + 5, precision),
                    'max_lat': metric_val(l, base_evt + 6, precision),
                    'stress_score': metric_val(l, base_evt + 7, precision),
                    'mean_reads': metric_val(l, base_evt + 8, precision),
                    'mean_writes': metric_val(l, base_evt + 9, precision),
                })

    df = pd.DataFrame(df).ffill()
    # replace negative numbers for nan
    df[df < 0] = np.nan
    return df


def get_raw_prv_timestamps(prv_path):
    with open(prv_path) as f:
        # ignore lines starting with c or #
        times = [int(line.split(':')[5]) for line in f.readlines() if line[0] not in ['c', '#'] and len(line.split(':')) >= 6]
    return times


class TestOutput(unittest.TestCase):
    # trace file with memory read and write counters (the one processed with PROFET)
    RAW_FILE = None
    # PROFET processed trace file
    PROCESSED_FILE = None
    PRECISION = 2
    N_NODES = None
    N_SOCKETS = None
    N_MCS = None
    
    @classmethod
    def setUpClass(self):
        if self.PROCESSED_FILE == None:
            raise Exception('Required file for testing has not been set up yet.')
        self.out_df = prv_out_to_df(self.PROCESSED_FILE, self.PRECISION, self.PROFET_BASE_EVENT_TYPE, self.EXCLUDE_ORIGINAL_TRACE)

    def test_same_prv_output(self):
        # assert that the output prv file is equal to the previously correct one
        with io.open(self.PROCESSED_FILE) as f1:
            correct_file = self.PROCESSED_FILE.replace('out_traces', 'correct_out_traces')
            with io.open(correct_file) as f2:
                i = 1
                for l1, l2 in zip(f1.readlines(), f2.readlines()):
                    if l1 != l2:
                        print(f'Line {i} is different:')
                        print(f'Processed Line: {l1}')
                        print(f'Correct Line: {l2}')
                    i += 1
                self.assertListEqual(list(f1), list(f2))

    def test_same_pcf_output(self):
        # assert that the output pcf file is equal to the previously correct one
        out_pcf = self.PROCESSED_FILE.replace('.prv', '.pcf')
        with io.open(out_pcf) as f1:
            correct_file = out_pcf.replace('out_traces', 'correct_out_traces')
            with io.open(correct_file) as f2:
                self.assertListEqual(list(f1), list(f2))

    def test_same_row_output(self):
        # assert that the output row file is equal to the previously correct one
        out_pcf = self.PROCESSED_FILE.replace('.prv', '.row')
        with io.open(out_pcf) as f1:
            correct_file = out_pcf.replace('out_traces', 'correct_out_traces')
            with io.open(correct_file) as f2:
                self.assertListEqual(list(f1), list(f2))

    def test_consecutive_timestamps(self):
        # assert that timestamps are ascendingly sorted
        all_diffs = self.out_df['time'].diff().dropna() < 0
        if any(all_diffs):
            first_diff_idx = np.where(all_diffs)[0][0]
            print(f'First unsorted timestamp: {self.out_df["time"].iloc[first_diff_idx]}, out of {sum(all_diffs)} unsorted elements.')
        self.assertEqual(list(self.out_df['time']), list(self.out_df['time'].sort_values()))

    def test_contained_timestamps(self):
        # assert that all output timestamps are contained in input
        times = get_raw_prv_timestamps(self.RAW_FILE)
        self.assertTrue(set(times).issuperset(set(self.out_df['time'])))

    def test_same_n_nodes(self):
        # assert that the generated file has the correct number of nodes
        test_df = self.out_df
        if 'exclude_original' not in self.PROCESSED_FILE:
            test_df = self.out_df[self.out_df['node'] > 1]
        self.assertEqual(self.N_NODES, test_df['node'].nunique())

    def test_same_n_sockets(self):
        # assert that the generated file has the correct number of socket per node
        ignore_app0_df = self.out_df[self.out_df['node'] > 1]
        for i_node in ignore_app0_df['node'].unique():
            df_node = self.out_df[self.out_df['node'] == i_node]
            self.assertEqual(self.N_SOCKETS, df_node['socket'].nunique())

    def test_same_n_mcs(self):
        # assert that the generated file has the correct number of mc per socket
        ignore_app0_df = self.out_df[self.out_df['node'] > 1]
        if self.N_MCS != -1:
            for i_node in ignore_app0_df['node'].unique():
                df_node = self.out_df[self.out_df['node'] == i_node]
                for i_skt in df_node['socket'].unique():
                    df_skt = df_node[df_node['socket'] == i_skt]
                    self.assertEqual(self.N_MCS, df_skt['mc'].nunique())

    def test_equal_write_ratio(self):
        # assert that the given write ratio equals the number of writes divided by the total number of accesses
        calc_wratio = self.out_df['mean_writes'] * 100 / (self.out_df['mean_writes'] + self.out_df['mean_reads'])
        # replace nan values with 0, as in some cases there are no reads or writes (they are all 0)
        calc_wratio = calc_wratio.fillna(0).round(self.PRECISION)
        comp = self.out_df['wratio'] == calc_wratio
        if not all(comp):
            idxs = np.where(~comp)[0]
            diffs = abs(self.out_df.iloc[idxs]['wratio'] - calc_wratio.iloc[idxs])
            # allow a difference of 1% between the calculated and the given write ratio (due to rounding errors)
            if not all(diffs <= 1):
                print(f'Number of elements with wrong write ratio: {sum(~comp)}')
                return False
        return True


if __name__ == '__main__':
    # TODO usage

    # base event type for Profet events in Paraver
    TestOutput.PROFET_BASE_EVENT_TYPE = 94000000

    # receive output file path as argument
    # NOTE: use sys.argv.pop(), as sys.argv[i] does not work properly
    TestOutput.EXCLUDE_ORIGINAL_TRACE = bool(int(sys.argv.pop()))
    TestOutput.N_MCS = int(sys.argv.pop())
    TestOutput.N_SOCKETS = int(sys.argv.pop())
    TestOutput.N_NODES = int(sys.argv.pop())
    TestOutput.PRECISION = int(sys.argv.pop())
    TestOutput.PROCESSED_FILE = sys.argv.pop()
    TestOutput.RAW_FILE = sys.argv.pop()

    runner = unittest.TextTestRunner(failfast=True)
    unittest.main(testRunner=runner)
