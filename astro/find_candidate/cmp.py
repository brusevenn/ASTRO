import json
import os
import re
import sys
import traceback
from concurrent.futures import (ProcessPoolExecutor, as_completed)

from lib import config
from wfg.wfgcmp import main as wfgcmp


def main(target_function_dir, root_directory, function_files, result_writer):
    sim_result = False
    burn_dot_paths_dict = find_cmp_candidate_parallel(root_directory, function_files)
    burn_dot_paths_list = convert_dict_to_list(burn_dot_paths_dict, target_function_dir)
    
    function_sim_result_dict = {}


    print("burn_dot_paths_list: ", len(burn_dot_paths_list))
    with ProcessPoolExecutor(max_workers=config.SINGLE_MAX_WORKER) as executor:
        all_task = (executor.submit(wfgcmp, row[0], row[1]) for row in burn_dot_paths_list)

        for task in as_completed(all_task):
            try:
                data = task.result()
                if isinstance(data, list) and len(data) == 5:
                    if data[1] in function_sim_result_dict:
                        function_sim_result_dict[data[1]].append(data)
                    else:
                        function_sim_result_dict[data[1]] = [data]
                else:
                    pass
                    # print("un sim result: ", data)
            except Exception as exc:
                data = exc
                traceback.print_exc()
                sys.exit
            finally:
                pass
    
    for key, value in function_sim_result_dict.items():
        if len(value) % 2 == 0:
            sorted_value = sorted(value, key=lambda x: (-x[3], x[0]))[:-1]
        else:
            sorted_value = value
        false_count = len([x for x in sorted_value if x[0] == False])
        true_count = len([x for x in sorted_value if x[0] == True])
        if true_count > false_count:
            sim_result = True
            result_writer.writerow(value)
            # break
    
    print(f"{target_function_dir} sim result: {sim_result}")
    for key, value  in function_sim_result_dict.items():
        print(f"target dir: {key} compare: {value}")

    if config.get_count_time():
        return sim_result, len(burn_dot_paths_list)
    
    return sim_result

def convert_dict_to_list(paths_dict, target_function_dir):
    paths_list = []
    for function_name, paths in paths_dict.items():
        target_function_dot = os.path.join(target_function_dir, function_name)
        for path in paths:
            paths_list.append([target_function_dot, path])
    return paths_list

#       ，           ，              
def find_cmp_candidate_parallel(root_directorys, function_files) -> dict:
    function_dot_2_burn_dot_paths_dict = {}
    if len(root_directorys) == 0:
        return function_dot_2_burn_dot_paths_dict
    # print(f"root_directorys: {root_directorys}")
    with ProcessPoolExecutor(max_workers=config.SINGLE_MAX_WORKER) as executor:
        all_task = (executor.submit(find_cmp_candidate, root_directorys, row) for row in function_files)

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
                sys.exit
            finally:
                pass
    return function_dot_2_burn_dot_paths_dict
    
    
def find_cmp_candidate(root_directorys, function_file) -> dict:
    if config.get_levenshtein_sim():
        from Levenshtein import ratio
        return find_cmp_candidate_sim_pick(root_directorys, function_file, distance=ratio)
    elif config.get_bert_sim():
        from find_candidate.bert_sim import SimilarityModel
        sim_model = SimilarityModel()
        return find_cmp_candidate_sim_pick(root_directorys, function_file, distance=sim_model.compute_similarity)
    else:
        return find_cmp_candidate_real(root_directorys, function_file)

def find_cmp_candidate_real(root_directorys, function_file):
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
        if isinstance(root_directorys, str):
            pass
        else:
            raise RuntimeError(f"{root_directorys} is not str")
        functionname_directorys = os.listdir(root_directorys)
        for functionname_directory in functionname_directorys:
            if target_function_name in str.lower(functionname_directory):
                sub_root_directory = os.path.join(root_directorys, functionname_directory)
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
        filenames = os.listdir(root_directorys)
        for filename in filenames:
            if not filename.endswith("_wfg.dot"):
                continue
            function_filename = filename.split("_wfg.dot")
            try:
                function_filename = str.lower(function_filename[0])
            except Exception as exc:
                print(f"{target_function_name} split error because: \n {exc}")
                
            if target_function_name in function_filename:
                burn_dot_path = os.path.join(root_directorys, filename)
                burn_dot_paths.append(burn_dot_path)
    return function_file, burn_dot_paths



def find_cmp_candidate_sim_pick(root_directorys, function_file, sim_score_threshold=0.8, distance=None):
    burn_dot_paths = []
    target_function_name = str.lower(function_file)
    if target_function_name == "fallback_wfg.dot" or target_function_name == "fallback()_wfg.dot" or "constructor(" in target_function_name:
        return function_file, burn_dot_paths
    if target_function_name.endswith("_wfg.dot"):
        try:
            target_function_name = target_function_name.split("_wfg.dot")[0]
            target_function_name_without_para = target_function_name.split("(")[0]
            # target_function_name = re.sub(r'[^a-zA-Z]', '', target_function_name)
        except Exception as exc:
            print(f"{target_function_name} split error because: \n {exc}")
    
    if config.get_dappScan():
        if isinstance(root_directorys, str):
            pass
        else:
            raise RuntimeError(f"{root_directorys} is not str")
        functionname_directorys = os.listdir(root_directorys)
        for functionname_directory in functionname_directorys:
            functionname_directory_without_para = str.lower(functionname_directory).split("(")[0]
            sim_score = distance(target_function_name_without_para, functionname_directory_without_para)
            # if target_function_name in str.lower(functionname_directory):
            if sim_score >= sim_score_threshold:
                sub_root_directory = os.path.join(root_directorys, functionname_directory)
                for dirpath, dirnames, filenames in os.walk(sub_root_directory):
                    #        'burn.dot'   
                    if dirpath != sub_root_directory:
                        for filename in filenames:
                            if not filename.endswith("_wfg.dot"):
                                continue
                            function_filename = filename.split("_wfg.dot")
                            try:
                                function_filename = str.lower(function_filename[0])
                                function_filename_without_para = function_filename.split("(")[0]
                                # function_filename = re.sub(r'[^a-zA-Z]', '', function_filename)
                            except Exception as exc:
                                print(f"{target_function_name} split error because: \n {exc}")
                            

                            if function_filename_without_para == functionname_directory_without_para:
                                burn_dot_path = os.path.join(dirpath, filename)
                                burn_dot_paths.append(burn_dot_path)
                            else: 
                                sim_score = distance(target_function_name_without_para, function_filename_without_para)
                                if sim_score >= sim_score_threshold:
                                    burn_dot_path = os.path.join(dirpath, filename)
                                    burn_dot_paths.append(burn_dot_path)
    else:
        functionname_directorys = os.listdir(root_directorys)
        for functionname_directory in functionname_directorys:
            if target_function_name in str.lower(functionname_directory):
                sub_root_directory = os.path.join(root_directorys, functionname_directory)
                for dirpath, dirnames, filenames in os.walk(sub_root_directory):
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


def find_cmp_candidate_single(root_directorys, function_files) -> dict:
    function_dot_2_burn_dot_paths_dict = {}
    if len(root_directorys) == 0:
        return function_dot_2_burn_dot_paths_dict
    # print(f"root_directorys: {root_directorys}")
    for function_file in function_files:
        target_function_name = str.lower(function_file)
        if target_function_name.endswith("_wfg.dot"):
            try:
                target_function_name = target_function_name.split("_wfg.dot")[0]
            except Exception as exc:
                print(f"{target_function_name} split error because: \n {exc}")
        burn_dot_paths = []
        if config.get_dappScan():
            # for root_directory in root_directorys:
            if isinstance(root_directorys, str):
                pass
            else:
                raise RuntimeError(f"{root_directorys} is not str")
            for dirpath, dirnames, filenames in os.walk(root_directorys):
                #        'burn.dot'   
                if dirpath != root_directorys:
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
            for dirpath, dirnames, filenames in os.walk(root_directorys):
                #        'burn.dot'   
                if dirpath != root_directorys:
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
            
