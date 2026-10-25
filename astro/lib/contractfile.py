import json
import os

from lib.dic_and_file import *


def make_contract_file(source_code, file_name, contract_name):
    try:
    # if  ： 0x2058ddf9cb982b7bdfe1caebeceb2310f376e129 
        res = json.loads(source_code)
        for key in res:
            # print(key)
            sol_file = open(
                file_name+"/"+key, 'w', encoding='UTF-8')
            sol_file.write(res[key]["content"])
            sol_file.close()
    except:
        if source_code[0] == source_code[1] == "{":
        # elif  : 0xACC6c1e48Beca93F1343eBDc0DEc8467a0656484
            new_code = source_code[1:-1]
            res = json.loads(new_code)
            sources = res["sources"]
            for name_a in sources:
                # print(name_a)
                _dir, _file = os.path.split(
                    file_name+"/"+name_a)
                # print(_dir)
                make_dir(_dir)
                sol_file = open(
                    file_name+"/"+name_a, 'w', encoding='UTF-8')
                sol_file.write(sources[name_a]["content"])
                sol_file.close()
        else:
            sol_file = open(file_name + "/" +
                            contract_name + ".sol", 'w', encoding='UTF-8')
            sol_file.write(source_code)
            sol_file.close()