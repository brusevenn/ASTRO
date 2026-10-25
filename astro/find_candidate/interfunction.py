import csv
import gc
import json
import os
import pickle
import re
import subprocess
import sys

import psutil
from analysis import contractlint
from lib import arg_parser, config
from lib.call_contractlint import *
from lib.dic_and_file import *
from split_function.re_function import *
# from util.timeout import timeout
from timeout_decorator import timeout


def show_memory_info(hint):
    pid = os.getpid()
    p = psutil.Process(pid)

    info = p.memory_full_info()
    memory = info.uss / 1024. / 1024
    print('{} memory used: {} MB'.format(hint, memory))

def find_interfunction_canditate(filePath, csv_to_write, **kwargs):
    cmds = []
    for dirpath, _, filenames in os.walk(filePath):
        for filename in filenames:
            # gc.collect()
            # show_memory_info(filename)
            #                  
            # if filename < "700.json" or filename > "8ff.json":
            #     continue
            if config.TEST and filename != "199.json":
                # print("skip filename: ", filename)
                continue
            filepath = os.path.join(dirpath, filename)
            print("filepath: ", filepath)
            with open(filepath, "r") as load_f:
                try:
                    load_dict = json.load(load_f)
                except ValueError as e:
                    print("filename: ", filename, "error: ", e)
                    continue
                for address, contract in load_dict.items():
                    source_code = contract["SourceCode"]
                    contract_name = contract["ContractName"]
                    if analyze_function(source_code, contract_name, address, csv_to_write):
                        print("address: ", address)
                        kwargs["contract"] = address
                        kwargs["contract_name"] = contract_name

                        file_path = file_basepath + "/" + contract_name + address
                        with open(file_path, "wb") as f:
                            pickle.dump(contract, f)
                        cmd = collect_kwargs(**kwargs)
                        cmds.append(cmd)
    call_contractlints(cmds)




def find_inter_function(filePath, csv_path, **kwargs):
    make_file(csv_path)
    inter_function_csv = open(csv_path, "w", encoding="UTF-8")
    find_interfunction_canditate(filePath, inter_function_csv, **kwargs)
    sorted_function_names = sorted(config.function_names.items(), key=lambda x:x[1], reverse=True)
    inter_function_csv.close()




def main():
    global file_basepath
    args = arg_parser.parse_args()
    kwargs = vars(args)
    name = kwargs.get("sname", None)
    test = kwargs.get("test", False)

    if name:
        config.set_function_name_pattern(args.sname)
    
    if test:
        config.TEST = True
    
    file_basepath = kwargs.get("xdir", None)
    if file_basepath == None:
        raise RuntimeError("        ")
    if not os.path.exists(file_basepath):
        os.makedirs(file_basepath)

    dataset_dic = "/root/research/acinfer/acinfer/python/test/dataset/interfunction_test/"
    filePath = "/mnt/e/dataset/xblock/verfiedContract"
    find_inter_function(filePath, csv_path="/root/research/acinfer/acinfer/python/test/analysis/interfunction_test.csv", **kwargs)


if __name__ == "__main__":
    main()