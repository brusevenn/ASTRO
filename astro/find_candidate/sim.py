import csv
import filecmp
import json
import os
import re
import subprocess
import sys
import traceback
from concurrent.futures import (ALL_COMPLETED, FIRST_COMPLETED,
                                ProcessPoolExecutor, as_completed, wait)

sys.path.append("/root/astro_submit/astro")
from find_candidate.candidate_filter import main as filter
from find_candidate.cmp import main as cmp
from lib import config
from lib.timing_decorator import timing_decorator_print
from wfg.wfgcmp import main as wfgcmp


def main(target_function_dir, root_directory, function_files, result_writer, openzeppelin_filter_path=None):
    if openzeppelin_filter_path:
        if config.get_count_time():
            function_files, filter_compare_times = filter(target_function_dir, openzeppelin_filter_path, function_files, result_writer)
        else:
            function_files = filter(target_function_dir, openzeppelin_filter_path, function_files, result_writer)
    if config.get_count_time():
        cmp_result, cmp_compare_times = cmp(target_function_dir, root_directory, function_files, result_writer)
    else:
        return cmp(target_function_dir, root_directory, function_files, result_writer)
    
    assert isinstance(filter_compare_times, int)
    assert isinstance(cmp_compare_times, int)
    
    return cmp_result, filter_compare_times + cmp_compare_times


if __name__ == "__main__":

    if len(sys.argv) != 3:
        print("Usage: python script.py target_function_dir root_directory")
        sys.exit(1)

    target_function_dir = sys.argv[1]
    root_directory = sys.argv[2]

    function_files = [
        file for file in os.listdir(root_directory) if file.endswith("_wfg.dot")
    ]

    result_csv_path = "result.csv"
    with open(result_csv_path, "w", newline="") as result_file:
        result_writer = csv.writer(result_file)
        print(main(target_function_dir, root_directory, function_files, result_writer))
    
    
