import argparse
import json
import os
import re
import sys

sys.path.append("/root/acinfer/acinfer/acinfer")
import csv
import traceback

import numpy as np
import pandas as pd
from find_candidate.sim import main as sim
from lib import arg_parser, config
from lib.call_contractlint import *
from lib.csv_manage import *
from lib.dic_and_file import *
from lib.timing_decorator import *
from split_function.re_function import *
from tqdm import tqdm

@timing_decorator_print
def main():
    global DirPath, CSVPath
    args = arg_parser.parse_args()
    kwargs = vars(args)
    name = kwargs.get("sname", None)
    test = kwargs.get("test", False)
    dataset_cve = kwargs.get("dataset_latest", False)
    datacsv_dir = kwargs.get("csvdir", None)
    dataset_dir = kwargs.get("setdir", None)
    is_dappscan = kwargs.get("dappscan", False)
    count_time = kwargs.get("count_time", None)
    levenshtein_sim = kwargs.get("levenshtein_sim", False)
    bert_sim = kwargs.get("bert_sim", False)

    if levenshtein_sim:
        config.set_levenshtein_sim()
    
    if bert_sim:
        config.set_bert_sim()

    if count_time:
        config.set_count_time()

    if dataset_cve:
        config.set_dataset_latest()
    
    if test:
        config.TEST = True
    
    if is_dappscan:
        config.set_dappScan()
        
    if dataset_cve:
        if datacsv_dir == None or dataset_dir == None:
            raise RuntimeError("need dir")
        DirPath = dataset_dir
        CSVPath = datacsv_dir
        process_all(DirPath, CSVPath, **kwargs)
        
def process_all(datasetdir, csvdir2, **kwargs):
    csvpath = os.path.join(csvdir2, "sampled_result.csv")
    df = pd.read_csv(csvpath)
    target_output_dir = os.path.join(csvdir2, "result_test")
    if not os.path.exists(target_output_dir):
        make_dir(target_output_dir)
        
    if 'address' not in df.columns:
        raise RuntimeError("csv      ")
    default_values = {
        'levenshtein_sim_result': None
    }

    #    default_values，             
    for col, default in default_values.items():
        if col not in df.columns:
            df[col] = default


    try:
        for index, row in tqdm(df.iloc[0:].iterrows(), desc="Processing rows"):
            try:
                if not pd.isna(row['levenshtein_sim_result']):
                    print(f"Skipping row {index + 1}: Already processed.")
                    continue

                result_tuple, compare_time = process_single(row, datasetdir, csvdir2, **kwargs)
                result = result_tuple[0]
                compare_times = result_tuple[1]

                df.at[index, 'levenshtein_sim_result'] = result

            except Exception as e:
                print(f"Error processing row {index}: {e}")
                continue

            finally:
                df.to_csv(csvpath, index=False)
    finally:
        df.to_csv(csvpath, index=False)


def compile_all(address, target_output_dir, csvdir2, **kwargs):
    target_cmd = find_target_wfg(address, target_output_dir, **kwargs)
    if config.get_count_time():
        invoke_call_contractlints = timing_decorator_return(call_contractlint)
        _, exec_time = invoke_call_contractlints(target_cmd)
        return exec_time
    else:
        return 0

def process_single(row, datasetdir, csvdir2, **kwargs):
    sim_check_path = os.path.join(csvdir2, "sim_check.csv")
    if not os.path.exists(sim_check_path):
        make_file(sim_check_path)
    return access_control_check(row['address'], datasetdir, csvdir2, **kwargs)

def access_control_check(address, datasetdir, csvdir2, **kwargs):
    target_output_dir = "/root/acinfer/acinfer/dataset/latestContracts/result_test"
    result_dataset_dir = kwargs.get("output", None)
    openzeppelin_filter_path = kwargs.get("openfilter", None)
    return call_sim(address, target_output_dir, openzeppelin_filter_path, result_dataset_dir, csvdir2)

@timing_decorator_print
def find_target_wfg(address, target_output_dir, **kwargs) -> list:
    kwargs["contract"] = address
    
    kwargs["dappscan"] = False
    cmd = collect_kwargs(**kwargs)
    cmd.extend(["-actarget", "--target-output", target_output_dir])
    print("target contract cmd: ", " ".join(cmd))
    return cmd

@timing_decorator_return
def call_sim(address, target_out_dir, openzeppelin_filter_path, result_dataset_dir, result_csv_dir):
    target_function_dir = os.path.join(target_out_dir, address)
    if not os.path.exists(target_function_dir):
        print("sim error: ",  f"file {target_function_dir} doesn't exist")
        return False, 0
    function_files = os.listdir(target_function_dir)
    wfg_function_files = []
    for function_file in function_files:
        if function_file.endswith("_wfg.dot"):
            wfg_function_files.append(function_file)
    if len(wfg_function_files) == 0:
        print("sim error: ", f"file {target_function_dir} does have no functions")
        return False, 0
    result_csv_file_path = os.path.join(result_csv_dir, "sim_check.csv")
    with open(result_csv_file_path, "a", encoding="utf-8") as result_csv_file_fp:
        result_writer = csv.writer(result_csv_file_fp)
        sim_result = sim(target_function_dir, result_dataset_dir, wfg_function_files, result_writer, openzeppelin_filter_path=openzeppelin_filter_path)
    return sim_result
    

if __name__ == "__main__":
    main()