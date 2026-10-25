import copy
import datetime
import glob
import json
import logging
import multiprocessing
import os
import subprocess
import sys
import time
import traceback
from shutil import rmtree

import networkx as nx
from callgraph import *
from cfg import *
from compose import *
from crytic_compile.localize import config as compile_config
from detection import *
from icfg_for_top_level_function import *
from instr_block import *
from lib import *
from lib import config
from range_graph import *
from sdg import *
from slither.core.declarations.solidity_variables import \
    SolidityVariableComposed
from slither.slither import Slither
from slither.slithir.operations.low_level_call import LowLevelCall
from slither.visitors.expression.export_values import ExportValues
from slither_globals import *
from state_var import *
from symex_helper import output_ir_paths_new
from util import *
from vdg import *

function_visibility = ['public', 'external']
SYMDIR = "../../symbolic_execution"
racket_executable = os.path.join(SYMDIR, "reentrancy")
racket_tod_executable = os.path.join(SYMDIR, "tod")
racket_tod_executable_comp = os.path.join(SYMDIR, "tod-complement")

def generate_top_level_icfg(slither_obj, graph_dir, dump_graph, log):
    icfg_objects = {}
    # Initialize icfg
    ICFGTopLevel.initialize_icfg(slither_obj.compilation_units)
    
    for compilation_unit in slither_obj.compilation_units:      
        for function in compilation_unit._functions_top_level:
            if not config.get_scale():  info('Interprocedural CFG generation started for modifier %s' % function.name)
            funtion_top_level_cfg = ICFGTopLevel(slither_obj, compilation_unit, function, graph_dir, dump_graph, log)
            if not config.get_scale():  info('Interprocedural CFG generated for modifer %s' % function.name)
            # icfg_objects[function] = funtion_top_level_cfg

