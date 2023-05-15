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
    return parser.parse_args()


def test_with_parameters(raw_file: str, processed_file: str, config_file: str, precision: int, nnodes: int, nsockets: int, nmcs: int,
                         no_warnings: bool = True, no_text: bool = True, per_socket: bool = True):
    # perform functional test with the given parameters
    # raw_file: raw trace file path (file with memory read and write counters, the one we use for processing in PROFET)
    # processed_file: processed file path after running PROFET
    # config_file: config file path

    # processed_file_name = os.path.basename(processed_file)
    # correct_out_traces_dir = 'correct_out_traces'
    
    flags = '--no_dash '
    if no_warnings:
        flags += '--no_warnings '
    if no_text:
        flags += '--no_text '
    if not per_socket:
        flags += '--memory_channel '
        # correct_out_traces_dir = 'correct_out_traces_per_socket'

    profet_command = f'./bin/profet {raw_file} {processed_file} {config_file} {flags}'
    print(profet_command)
    profet_exit_code = os.system(profet_command)
    if profet_exit_code != 0:
        sys.exit(-1)

    # # automatically prints the difference if there is any
    # os.system(f'diff "{processed_file}" "tests/{correct_out_traces_dir}/{processed_file_name}"')

    # run with command instead of importing the module. It is much better like this because of the way unittests work.
    tests_exit_code = os.system(f'python3 tests/functional_test.py {raw_file} {processed_file} {precision} {nnodes} {nsockets} {nmcs}')


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
        print(f'{trace_config["trace_file"]}')
        test_with_parameters(f'tests/traces/{trace_config["trace_file"]}', f'tests/out_traces_per_mc/{trace_config["trace_file"]}',
                             f'configs/{trace_config["config"]}', trace_config["precision"], trace_config["nnodes"],
                             trace_config["nsockets"], trace_config["nmcs"], per_socket=False)
        print('\n')
            
    # process traces per socket
    print('=====================================================')
    print('                      SOCKET')
    print('=====================================================\n')
    for trace_config in test_traces:
        print(f'{trace_config["trace_file"]}')
        test_with_parameters(f'tests/traces/{trace_config["trace_file"]}', f'tests/out_traces_per_socket/{trace_config["trace_file"]}',
                             f'configs/{trace_config["config"]}', trace_config["precision"], trace_config["nnodes"],
                             trace_config["nsockets"], -1, per_socket=True)
        # test_with_parameters(f'tests/traces/{in_traces[i]}', f'tests/out_traces_per_socket/{in_traces[i]}', f'configs/{configs[i]}',
        #                      precision, nnodes[i], nsockets[i], -1, per_socket=True)
        print('\n')