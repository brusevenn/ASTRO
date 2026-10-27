'''
python3              
  python  Python2     
'''

import json
import os
import re

import numpy as np
from scipy.optimize import linear_sum_assignment

def call_hungarian(Metrix, arg_dir=None):
    """Return row-to-column and row-index mappings for a square cost matrix.

    arg_dir is retained for caller compatibility; assignment is now solved
    in-process with SciPy rather than a hard-coded external Python 2 runtime.
    """
    row_indices, column_indices = linear_sum_assignment(Metrix)
    inverse = [None] * len(column_indices)
    for row, column in zip(row_indices.tolist(), column_indices.tolist()):
        inverse[column] = row
    return [column_indices.tolist(), inverse]

def from3to2(metrix):
    row = len(metrix)
    column = len(metrix[0])
    metrix_str = ""
    for i in range(0, row):
        for j in range(0, column):
            metrix_str = metrix_str + str(metrix[i][j]) + ","
    return row, column, metrix_str[0: len(metrix_str) - 1]

def fromstrtolist(row, column, metrix_str):
      metrix_set = [int(node.strip()) for node in str.split(metrix_str, ",")]
      return np.array(metrix_set).reshape(row, column).tolist()

if __name__ == "__main__":
    metrix = [[0.0, 0.5, 0.5, 0.0, 0.5, 0.5, 0.0, 1.0], [0.5, 0.08482503578087186, 0.06820208177929055, 0.5, 0.513523138347365, 0.15377495513506234, 0.5, 1.0], [0.5, 0.0, 0.07822591691231034, 0.5, 0.5122022120425378, 0.16948788678091042, 0.5, 1.0], [0.5, 0.07822591691231034, 0.0, 0.5, 0.5015197708371077, 0.18321781899521272, 0.5, 1.0], [0.0, 0.5, 0.5, 0.0, 0.5, 0.5, 0.0, 1.0], [0.5, 0.5122022120425378, 0.5015197708371077, 0.5, 0.0, 0.5386751345948129, 0.5, 1.0], [0.5, 0.16948788678091042, 0.18321781899521272, 0.5, 0.5386751345948129, 0.0, 0.5, 1.0], [0.0, 0.5, 0.5, 0.0, 0.5, 0.5, 0.0, 1.0]]
    mapping = call_hungarian(metrix)
    print("mapping: ", mapping)
    # metrix_str = python2_json(metrix)
    # print(metrix_str)
    # result = call_hungarian(metrix)
    # splitresult = result.strip().split(";")
    # mapping = fromstrtolist(int(splitresult[0]), int(splitresult[1]), splitresult[2])
    # print(mapping)



# import execnet

# def call_hungarian(Metrix):
#     call_python_version("2", "hungarian.hungarian", "call_hungarian", Metrix)

# def call_python_version(Version, Module, Function, ArgumentList):
#     gw      = execnet.makegateway("popen//python=python%s" % Version)
#     channel = gw.remote_exec("""
#         from %s import %s as the_function
#         channel.send(the_function(*channel.receive()))
#     """ % (Module, Function))
#     channel.send(ArgumentList)
#     return channel.receive()

# if __name__ == "__main__":
#     metrix = [[0.0, 0.5, 0.5, 0.0, 0.5, 0.5, 0.0, 1.0], [0.5, 0.08482503578087186, 0.06820208177929055, 0.5, 0.513523138347365, 0.15377495513506234, 0.5, 1.0], [0.5, 0.0, 0.07822591691231034, 0.5, 0.5122022120425378, 0.16948788678091042, 0.5, 1.0], [0.5, 0.07822591691231034, 0.0, 0.5, 0.5015197708371077, 0.18321781899521272, 0.5, 1.0], [0.0, 0.5, 0.5, 0.0, 0.5, 0.5, 0.0, 1.0], [0.5, 0.5122022120425378, 0.5015197708371077, 0.5, 0.0, 0.5386751345948129, 0.5, 1.0], [0.5, 0.16948788678091042, 0.18321781899521272, 0.5, 0.5386751345948129, 0.0, 0.5, 1.0], [0.0, 0.5, 0.5, 0.0, 0.5, 0.5, 0.0, 1.0]]
#     result = call_hungarian(metrix)
#     # result = call_python_version("2.7", "my_module", "my_function",
#     #                          ["Mr", "Bear"])
#     print(result)
