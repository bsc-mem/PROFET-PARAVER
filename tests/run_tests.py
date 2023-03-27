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


def test_with_parameters(raw_file: str, processed_file: str, config_file: str, precision: int, nnodes: int, nsockets: int, nmcs: int,
                         no_warnings: bool = True, no_text: bool = True, per_socket: bool = False):
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
    if per_socket:
        flags += '--socket '
        # correct_out_traces_dir = 'correct_out_traces_per_socket'

    print(f'./bin/profet {raw_file} {processed_file} {config_file} {flags}')
    profet_exit_code = os.system(f'./bin/profet {raw_file} {processed_file} {config_file} {flags}')
    if profet_exit_code != 0:
        sys.exit(-1)

    # # automatically prints the difference if there is any
    # os.system(f'diff "{processed_file}" "tests/{correct_out_traces_dir}/{processed_file_name}"')

    # run with command instead of importing the module. It is much better like this because of the way unittests work.
    tests_exit_code = os.system(f'python3 tests/functional_test.py {raw_file} {processed_file} {precision} {nnodes} {nsockets} {nmcs}')


if __name__ == "__main__":
    # compile the program in order to make sure we test with latest changes in the code
    print('Compiling PROFET...')
    os.system('make')

    in_traces = [
        'test1.prv',
        'test2.prv',
        'test3.prv',
        'lulesh_4+4_with_uncores_sockets1+2.chop_5it.prv',
        'lulesh_7+1_with_uncores_sockets1+2.chop8.prv',
    ]
    configs = [
        'epeec.json',
        'epeec.json',
        'epeec.json',
        'epeec.json',
        'epeec.json',
    ]

    nnodes = [1, 1, 1, 1, 1]
    nsockets = [1, 1, 1, 2, 2]
    nmcs = [3, 3, 3, 6, 6]
    # decimal precision
    precision = 2

    # process traces per MC
    print('\n=====================================================')
    print('                   Memory Channel')
    print('=====================================================\n')
    for i in range(len(in_traces)):
        print(f'{in_traces[i]}')
        test_with_parameters(f'tests/traces/{in_traces[i]}', f'tests/out_traces/{in_traces[i]}', f'configs/{configs[i]}',
                             precision, nnodes[i], nsockets[i], nmcs[i], per_socket=False)
        print('\n')
            
    # process traces per socket
    print('=====================================================')
    print('                      SOCKET')
    print('=====================================================\n')
    for i in range(len(in_traces)):
        print(f'{in_traces[i]}')
        test_with_parameters(f'tests/traces/{in_traces[i]}', f'tests/out_traces_per_socket/{in_traces[i]}', f'configs/{configs[i]}',
                             precision, nnodes[i], nsockets[i], -1, per_socket=True)
        print('\n')