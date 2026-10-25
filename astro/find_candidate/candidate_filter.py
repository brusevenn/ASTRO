import filecmp
import json
import os
import re
import subprocess
import sys
import traceback
from concurrent.futures import (ALL_COMPLETED, FIRST_COMPLETED,
                                ProcessPoolExecutor, as_completed, wait)

from lib import config
from lib.timing_decorator import timing_decorator_print
from wfg.wfgcmp import main as wfgcmp


def main(target_function_dir, openzeppelin_filter_path, function_files, result_writer):
    sim_result = False
    burn_dot_paths_dict = find_filter_candidate_parallel(openzeppelin_filter_path, function_files)
    burn_dot_paths_list = convert_dict_to_list(burn_dot_paths_dict, target_function_dir)
    
    openzeppelin_filter = []

    burn_dot_paths_list_length = len(burn_dot_paths_list)
    print("openzeppelin fileter:: burn_dot_paths_list: ", len(burn_dot_paths_list))
    #         ，           
    PROCESS_NUMBER = int(len(burn_dot_paths_list) / 3)
    if PROCESS_NUMBER < 1:
        PROCESS_NUMBER = 1
    with ProcessPoolExecutor(max_workers=PROCESS_NUMBER) as executor:
        all_task = (executor.submit(wfgcmp, row[0], row[1]) for row in burn_dot_paths_list)

        for task in as_completed(all_task):
            try:
                data = task.result()
                if isinstance(data, list) and len(data) == 5:
                    filter_function_file = os.path.basename(data[1])
                    if filter_function_file == "approve(address,uint256)_wfg.dot":
                        print(f"approve: {data}")
                    if data[0] == False and data[3] == 1.0:
                        filter_function_file = os.path.basename(data[1])
                        openzeppelin_filter.append(filter_function_file)
                else:
                    pass
            except Exception as exc:
                data = exc
                traceback.print_exc()
                sys.exit()
            finally:
                pass
    cmp_files = []

    for function_file in function_files:
        if function_file not in openzeppelin_filter:
            cmp_files.append(function_file)

    if config.get_count_time():
        return cmp_files, burn_dot_paths_list_length

    return cmp_files

def convert_dict_to_list(paths_dict, target_function_dir):
    paths_list = []
    for function_name, paths in paths_dict.items():
        target_function_dot = os.path.join(target_function_dir, function_name)
        for path in paths:
            paths_list.append([target_function_dot, path])
    return paths_list

#       ，           ，              
def find_filter_candidate_parallel(openzeppelin_filter_path, function_files) -> dict:
    function_dot_2_burn_dot_paths_dict = {}
    if len(openzeppelin_filter_path) == 0:
        return function_dot_2_burn_dot_paths_dict
    # print(f"openzeppelin_filter_path: {openzeppelin_filter_path}")
    with ProcessPoolExecutor(max_workers=config.SINGLE_MAX_WORKER) as executor:
        all_task = (executor.submit(find_cmp_candidate, openzeppelin_filter_path, row) for row in function_files)

        for task in as_completed(all_task):
            try:
                data = task.result()
                if len(data) == 2:
                    function_file, burn_dot_path_lists = data[0], data[1]
                    # print("sim result: ", data)
                    if isinstance(function_file, str) and isinstance(burn_dot_path_lists, list):
                        function_dot_2_burn_dot_paths_dict[function_file] = burn_dot_path_lists
                    else:
                        raise RuntimeError(f"find_cmp_candidate      ： function_file: {function_file} \ttype: {type(function_file)} \n \
                            burn_dot_path_list: {burn_dot_path_lists} \t type: {type(burn_dot_path_lists)}")
                else:
                    raise RuntimeError(f"       2： {data}")
                    # print("un sim result: ", data)
            except Exception as exc:
                data = exc
                traceback.print_exc()
                sys.exit()
            finally:
                pass
    return function_dot_2_burn_dot_paths_dict
    
    
def find_cmp_candidate(openzeppelin_filter_path, function_file) -> dict:
    return find_cmp_candidate_real(openzeppelin_filter_path, function_file)

def find_cmp_candidate_real(openzeppelin_filter_path, function_file):
    burn_dot_paths = []
    target_function_name = str.lower(function_file)
    if target_function_name == "fallback_wfg.dot" or target_function_name == "fallback()_wfg.dot" or "constructor(" in target_function_name:
        return function_file, burn_dot_paths
    if target_function_name.endswith("_wfg.dot"):
        try:
            target_function_name = target_function_name.split("_wfg.dot")[0]
            # target_function_name = re.sub(r'[^a-zA-Z]', '', target_function_name)
        except Exception as exc:
            print(f"{target_function_name} split error because: \n {exc}")
    
    if config.get_dappScan():
        # for root_directory in openzeppelin_filter_path:
        if isinstance(openzeppelin_filter_path, str):
            pass
        else:
            raise RuntimeError(f"{openzeppelin_filter_path} is not str")
        functionname_directorys = []
        for basic_openzeppelin_filter_path in os.listdir(openzeppelin_filter_path):
            openzeppelin_filter_path2 = os.path.join(openzeppelin_filter_path, basic_openzeppelin_filter_path)
            part_functionname_directorys = os.listdir(openzeppelin_filter_path2)
            part_functionname_directorys = [os.path.join(basic_openzeppelin_filter_path, part_functionname_directory) for part_functionname_directory in part_functionname_directorys]
            functionname_directorys.extend(part_functionname_directorys)
        for functionname_directory in functionname_directorys:
            if target_function_name in str.lower(functionname_directory):
                sub_root_directory = os.path.join(openzeppelin_filter_path, functionname_directory)
                for dirpath, dirnames, filenames in os.walk(sub_root_directory):
                    #        'burn.dot'   
                    if dirpath != sub_root_directory:
                        for filename in filenames:
                            if not filename.endswith("_wfg.dot"):
                                continue
                            function_filename = filename.split("_wfg.dot")
                            try:
                                function_filename = str.lower(function_filename[0])
                                # function_filename = re.sub(r'[^a-zA-Z]', '', function_filename)
                            except Exception as exc:
                                print(f"{target_function_name} split error because: \n {exc}")
                                
                            if target_function_name == function_filename:
                                burn_dot_path = os.path.join(dirpath, filename)
                                burn_dot_paths.append(burn_dot_path)
    else:
        functionname_directorys = os.listdir(openzeppelin_filter_path)
        for functionname_directory in functionname_directorys:
            if target_function_name in str.lower(functionname_directory):
                sub_root_directory = os.path.join(openzeppelin_filter_path, functionname_directory)
                for dirpath, dirnames, filenames in os.walk(sub_root_directory):
                    #        'burn.dot'   
                    if dirpath != sub_root_directory:
                        for filename in filenames:
                            if not filename.endswith("_wfg.dot"):
                                continue
                            function_filename = filename.split("_wfg.dot")
                            try:
                                function_filename = str.lower(function_filename[0])
                                # function_filename = re.sub(r'[^a-zA-Z]', '', function_filename)
                            except Exception as exc:
                                print(f"{target_function_name} split error because: \n {exc}")
                                
                            if target_function_name in function_filename:
                                burn_dot_path = os.path.join(dirpath, filename)
                                burn_dot_paths.append(burn_dot_path)
    return function_file, burn_dot_paths

def find_cmp_candidate_single(openzeppelin_filter_path, function_files) -> dict:
    function_dot_2_burn_dot_paths_dict = {}
    if len(openzeppelin_filter_path) == 0:
        return function_dot_2_burn_dot_paths_dict
    # print(f"openzeppelin_filter_path: {openzeppelin_filter_path}")
    for function_file in function_files:
        target_function_name = str.lower(function_file)
        if target_function_name.endswith("_wfg.dot"):
            try:
                target_function_name = target_function_name.split("_wfg.dot")[0]
            except Exception as exc:
                print(f"{target_function_name} split error because: \n {exc}")
        burn_dot_paths = []
        if config.get_dappScan():
            # for root_directory in openzeppelin_filter_path:
            if isinstance(openzeppelin_filter_path, str):
                pass
            else:
                raise RuntimeError(f"{openzeppelin_filter_path} is not str")
            for dirpath, dirnames, filenames in os.walk(openzeppelin_filter_path):
                #        'burn.dot'   
                if dirpath != openzeppelin_filter_path:
                    for filename in filenames:
                        if not filename.endswith("_wfg.dot"):
                            continue
                        function_filename = filename.split("_wfg.dot")
                        if len(function_filename):
                            function_filename = str.lower(function_filename[0])
                        if target_function_name in function_filename:
                            burn_dot_path = os.path.join(dirpath, filename)
                            burn_dot_paths.append(burn_dot_path)
        else:
            for dirpath, dirnames, filenames in os.walk(openzeppelin_filter_path):
                #        'burn.dot'   
                if dirpath != openzeppelin_filter_path:
                    for filename in filenames:
                        if not filename.endswith("_wfg.dot"):
                            continue
                        function_filename = filename.split("_wfg.dot")
                        if len(function_filename):
                            function_filename = str.lower(function_filename[0])
                        if function_file in function_filename:
                            burn_dot_path = os.path.join(dirpath, filename)
                            burn_dot_paths.append(burn_dot_path)
        function_dot_2_burn_dot_paths_dict[function_file] = burn_dot_paths
    return function_dot_2_burn_dot_paths_dict
            
