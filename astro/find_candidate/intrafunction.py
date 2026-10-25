import json
import os
import re
import sys

from lib.contractfile import make_contract_file
from lib.dic_and_file import *
# from split_function.find_function import *
from lib.timeout_decorator import timeout

# Define the regular expression pattern to search for
#  transferFrom     
#    pattern，                
# pattern = r".*require\(.*msg.sender.* == "
pattern = r"(?<=\s)(\S*?)msg\.sender\]"    # transferFrom       msg.sender   
pattern_transferfrom = r'function\s+transferFrom\s*\(([^()]*)\)\s*([^()]*)\s*\(([^()]*)\)\s*\{((?!function).)+\}'    #       transferFrom   
# pattern_transferfrom = r"function\s+transferfrom\s*\(.*\).*?\{((?!function).)+\}"

# pattern = r"requird\(.*from.*"

#              

# Loop through all files in the current directory and its subdirectories
def find_intrafunction_canditate(filePath, csv_to_write):
    for dirpath, _, filenames in os.walk(filePath):
        # has_find = 0
        for filename in filenames:
            # if filename != "d97.json" and filename != "3b9.json":
            #     continue
            filepath = os.path.join(dirpath, filename)
            
            with open(filepath, "r") as load_f:
                try:
                    load_dict = json.load(load_f)
                except ValueError as e:
                    print("filename: ", filename)
                    continue
                for address, contract in load_dict.items():
                    source_code = contract["SourceCode"]
                    contract_name = contract["ContractName"]
                    
                    # if str.lower(address) == str.lower("0xd97579Cea3fE2473682a4C42648134BB982433B9") or str.lower(address) == str.lower("0x3b912FB1B5B9e07E50E43F0404feE038f9a0353C"):
                    if re_candidate(source_code, csv_to_write=csv_to_write):
                            make_dir(dataset_dic + contract_name + address)
                            make_contract_file(source_code, dataset_dic + contract_name + address, contract_name)
                            print("filepath: ", filepath, "contract_name: ", contract_name)
                            csv_to_write.write(filepath + "," + contract_name + "\n")
            #             has_find += 1
            # if has_find > 1:
            #     break
def re_candidate(source_code, csv_to_write):
    transfrom_result = re.search(pattern_transferfrom, source_code, re.I|re.DOTALL)
    # transfrom_result =  get_function_by_name(source_code, "transferFrom")
    if not transfrom_result:
        return False
    transfrom_result = transfrom_result.group()
    re_result = re.search(pattern, transfrom_result)
    if re_result:
        #  msg.sender    
        prefix = re_result.group(1)
        prefix_nums = candidates_nums(transfrom_result, prefix)
        sender_nums = candidates_nums(transfrom_result, prefix + "msg.sender")
        if prefix_nums > sender_nums:
            print("transfrom_result: ", transfrom_result)
            print("re_result: ", re_result.group(1), end="\t")
            csv_to_write.write(re_result.group().strip() + ",")
            print("prefix_nums: ", prefix_nums, "sender_nums: ", sender_nums)
            return True
    return False

def candidates_nums(source_code, prefix):
    #              ，         
    regex = re.escape(prefix)
    pattern = re.compile(regex)
    return len(pattern.findall(source_code))

def find_intra_function(filePath,csv_path):
    make_file(csv_path)
    intra_function_csv = open(csv_path, "w", encoding='UTF-8')
    find_intrafunction_canditate(filePath, intra_function_csv)
    intra_function_csv.close()


if __name__ == "__main__":

    dataset_dic = "/root/research/acinfer/acinfer/python/test/dataset/intrafunction/"
    filePath = "/mnt/e/dataset/xblock/verfiedContract"
    find_intra_function(filePath ,csv_path="/root/research/acinfer/acinfer/python/test/analysis/intrafunction.csv")

