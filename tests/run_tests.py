#!/usr/bin/env python3

'''
Copyright (C) 2023 Isaac Boixaderas - All Rights Reserved
You may use, distribute and modify this code under the
terms of the BSD-3 license.

You should have received a copy of the BSD-3 license with
this file. If not, please visit: https://opensource.org/licenses/BSD-3-Clause
'''

import os
import sys
import argparse
import json


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-nc', '--no-compile', dest='no_compile', action='store_true',
                        help='Do not compile before running tests.')
    parser.add_argument('-ff', '--fail-fast', dest='fail_fast', action='store_true',
                        help='Make tests fail fast with an exception.')
    parser.add_argument('-nt', '--no-tests', dest='no_tests', action='store_true',
                        help='Do not execute tests, only run PROFET on test files.')
    return parser.parse_args()


def test_with_parameters(raw_file: str, processed_file: str, config_file: str, precision: int, nnodes: int, nsockets: int, nmcs: int,
                         no_warnings: bool = True, no_text: bool = True, per_socket: bool = True, fail_fast: bool = True, no_tests: bool = False,
                         omit_original_trace: bool = False):
    # perform functional test with the given parameters
    # raw_file: raw trace file path (file with memory read and write counters, the one we use for processing in PROFET)
    # processed_file: processed file path after running PROFET
    # config_file: config file path

    # processed_file_name = os.path.basename(processed_file)
    # correct_out_traces_dir = 'correct_out_traces'
    
    flags = ''
    if no_warnings:
        flags += '--no-warnings '
    if no_text:
        flags += '--quiet '
    if not per_socket:
        flags += '--memory-channel '
    if not omit_original_trace:
        flags += '--keep-original '

    profet_command = f'./bin/profet-prv {raw_file} {processed_file} {config_file} {flags}'
    print(profet_command)
    profet_exit_code = os.system(profet_command)
    if profet_exit_code != 0:
        sys.exit(-1)

    # # automatically prints the difference if there is any
    # os.system(f'diff "{processed_file}" "tests/{correct_out_traces_dir}/{processed_file_name}"')

    if not no_tests:
        # run with command instead of importing the module. It is much better like this because of the way unittests work.
        tests_exit_code = os.system(f'python3 tests/functional_test.py {raw_file} {processed_file} {precision} {nnodes} {nsockets} {nmcs} {int(omit_original_trace)}')
        if fail_fast and tests_exit_code != 0:
            raise Exception('Functional tests failed.')


if __name__ == "__main__":
    args = parse_args()

    if not args.no_compile:
        # compile the program in order to make sure we test with latest changes in the code
        print('Compiling PROFET...')
        os.system('make')

    with open('tests/test_traces.json') as json_file:
        test_traces = json.load(json_file)

    # process traces per MC
    print('\n=====================================================')
    print('                   Memory Channel')
    print('=====================================================\n')
    for trace_config in test_traces:
        out_trace_file = trace_config["trace_file"]
        omit_original = False
        if 'omit_original' in trace_config and trace_config['omit_original']:
            omit_original = True
            out_trace_file = trace_config["trace_file"].replace('.prv', '.omit_original.prv')

        print(trace_config["trace_file"])
        test_with_parameters(f'tests/traces/{trace_config["trace_file"]}', f'tests/out_traces_per_mc/{out_trace_file}',
                             f'configs/{trace_config["config"]}', trace_config["precision"], trace_config["nnodes"],
                             trace_config["nsockets"], trace_config["nmcs"], per_socket=False, fail_fast=args.fail_fast,
                             no_tests=args.no_tests, omit_original_trace=omit_original)
        print('\n')
            
    # process traces per socket
    print('=====================================================')
    print('                      SOCKET')
    print('=====================================================\n')
    for trace_config in test_traces:
        out_trace_file = trace_config["trace_file"]
        omit_original = False
        if 'omit_original' in trace_config and trace_config['omit_original']:
            omit_original = True
            out_trace_file = trace_config["trace_file"].replace('.prv', '.omit_original.prv')

        print(trace_config["trace_file"])
        test_with_parameters(f'tests/traces/{trace_config["trace_file"]}', f'tests/out_traces_per_socket/{out_trace_file}',
                             f'configs/{trace_config["config"]}', trace_config["precision"], trace_config["nnodes"],
                             trace_config["nsockets"], -1, per_socket=True, fail_fast=args.fail_fast,
                             no_tests=args.no_tests, omit_original_trace=omit_original)
        print('\n')