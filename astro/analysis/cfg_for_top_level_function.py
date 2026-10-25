import copy
import os
from collections import OrderedDict, defaultdict

import matplotlib.pyplot as plt
import networkx as nx
import pydot
from analysis.util import *
from analysis.basic_block import *
from analysis.cfg import CFG
from crytic_compile.localize import config as compile_config
from lib import config
from slither.core.cfg.node import Node, NodeType
from slither.core.declarations.function import Function
from slither.core.declarations.solidity_variables import SolidityFunction
from slither.core.variables.variable import Variable
from slither.printers.call.call_graph import *
from slither.slithir.operations.assignment import Assignment
from slither.slithir.operations.condition import Condition
from slither.slithir.operations.nop import Nop
from slither.slithir.operations.solidity_call import SolidityCall
from slither.slithir.variables.temporary import TemporaryVariable
from slither.visitors.expression.export_values import ExportValues
from analysis.varnode import *


class CFGTopLevel:
    """
        Builds a per function cfg
    """
    function_cfg = {}
    lvalue_vars = {}
    member_ir_var_left = []
    refvar_names = {}
    

    def __init__(self, slither_obj, function, graph_dir, dump_graph, log):
        self._slither = slither_obj
        self._return_values = {}
        self._pre_dominators = {}
        self._conditional_pre_dominators = {}
        self._all_predecessors = {}
        self._ir_to_block = {}
        self._node_to_block_mapping = defaultdict(list)
        self._function_basic_blocks = None
        self._next_block_to_node = {}
        self._match_ENDIF_to_IF = {}
        self._root_basic_block = None
        self._dump_graph = dump_graph
        self._log = log
        self._cfg = None
        self.state_vars_written = OrderedDict()
        self._ircall_to_bb = {}
        self._function = function
        self.blockid = {}
        self._condition_to_sons = defaultdict(dict)
        self.leaf_nodes = []
        self._result_dir = graph_dir
        self._return_to_phi = {}
        self._phi_return_variable = None
        self._new_phi_return = []
        self._returns_irs = []
        self._return_summary = {}
        self.build_cfg()

    
    def get_root_node(self):
        nodes = [x for x in self._cfg.nodes if self._cfg.in_degree(x) == 0]
        for node in nodes:
            basic_block = list(node)[0]
            if node.NodeType == NodeType.ENTRYPOINT:
                self._root_basic_block = node

    def get_leaf_basic_blocks(self):
        self.leaf_nodes = [x for x in self._cfg.nodes if self._cfg.out_degree(x)== 0 and self._cfg.in_degree(x) >= 1]

    # Builds CFG for every function outside the contract
    def build_cfg(self):
        self._cfg = nx.MultiDiGraph()
        self.generate_graph_nodes()
        self.get_pre_dominators()
        self.get_conditional_pre_dominators()
        self.generate_phi_var_for_return(self._function)
        get_all_predecessors_per_node(self._cfg, self.leaf_nodes, self._all_predecessors)
        compute_ancesters_decendents(self._cfg, self.leaf_nodes, [], self._all_predecessors, {})
        convert_set_to_list(self._all_predecessors)


        if self._dump_graph == True:
            self.print_cfg_dot(self._result_dir, self._function, self._cfg)

    def generate_graph_nodes(self):
        # if self._function.name == "transfer":
        #     print("  debug")
        all_nodes = self._function.nodes

        if len(all_nodes) > 0:
            root_node = all_nodes[0]
            visited_nodes = self.get_basic_blocks(root_node, self._function)
            if config.get_normalize():
                self.connect_all_basic_blocks_withconvert(self._function, visited_nodes, self._cfg)
            else:
                self.connect_all_basic_blocks(self._function, visited_nodes, self._cfg)

    def generate_phi_var_for_return(self, function):
        if len(function.nodes) != 0:
            phi_var = TemporaryVariable(function.nodes[0])
            self._phi_return_variable = phi_var
            return_values = []
            return_values.extend(function.returns)
            return_values.extend(function.return_values)
            return_values = list(set(return_values))
            effective_values = []
            
            for return_value in return_values:
                if return_value in CFG.lvalue_vars.keys():
                    effective_values.append(return_value)

            vars_used = []
            for return_ir in self._returns_irs:
                variable = return_ir.used[0]
                vars_used.append(variable)
                new_ir = Assignment(phi_var, variable, variable.type)
                self._return_to_phi[return_ir] = new_ir
            
            values_notin_rtnirs = []
            for effective_value in effective_values:
                if effective_value not in vars_used:
                    values_notin_rtnirs.append(effective_value)
            
            for value in values_notin_rtnirs:
                new_ir = Assignment(phi_var, value, value.type)
                self._new_phi_return.append(new_ir)

    # Checks to see whether the ir is an conditional instruction
    def is_conditional_ir(self, ir):
        if type(ir).__name__ == 'Condition' :
            return True
        if type(ir).__name__ == 'SolidityCall' and (ir.function.name.startswith('require') or ir.function.name.startswith('assert')):
            return True

        return False
    
    # Conditional predominators are those which are necessary conditions that need to be satisfied
    # in order to reach this block, they are the strong constraints. i.e, if a conditional IF is present
    # in its predominators but the matching END-IF is not present, then that conditional IF is a strong contraint
    def get_conditional_pre_dominators(self):
        end_if_blocks = set(self._match_ENDIF_to_IF.keys())
        
        for block in self._pre_dominators.keys():
            self._conditional_pre_dominators[block] = [x for x in self._pre_dominators[block] if self.is_conditional_ir(x._instructions[-1])]
            common_end_ifs = end_if_blocks.intersection(set(self._pre_dominators[block]))
            matching_ifs = [self._match_ENDIF_to_IF[x] for x in common_end_ifs if len(list(self._cfg.predecessors(x))) == 2]
            self._conditional_pre_dominators[block] = list(set(self._conditional_pre_dominators[block]) - set(matching_ifs))



    # Get all predominators (by definition) of every basic block 
    def get_pre_dominators(self):
        root_nodes = []

        for x in self._cfg.nodes:
            if self._cfg.in_degree(x) == 0:
                root_nodes.append(x)
            
            if self._cfg.out_degree(x) == 0:
                self.leaf_nodes.append(x)

            self._pre_dominators[x] = []
            self._conditional_pre_dominators[x] = []

        bfs_stack = []
        visited_blocks = []

        for root_node in root_nodes:
            bfs_stack.append(root_node)

            while len(bfs_stack) != 0:
                node = bfs_stack.pop(0)
                
                successors = list(self._cfg.successors(node))
                if node not in visited_blocks:
                    visited_blocks.append(node)
                    
                    for successor in successors:
                        try:
                            ir = successor._instructions[-1]
                        except:
                            pass
                        pre_dominator = node
                        
                        if type(ir).__name__ == 'Node':
                            
                            if ir.type == NodeType.ENDIF:
                                if self._match_ENDIF_to_IF.get(successor) != None:
                                    predecessors = list(self._cfg.predecessors(successor))
                                
                                    if len(predecessors) > 1:
                                        pre_dominator  = self._match_ENDIF_to_IF[successor]
                                    
                                    else:
                                        del self._match_ENDIF_to_IF[successor]
                            
                            if ir.type == NodeType.ENDLOOP:
                                if self._match_ENDIF_to_IF.get(successor) != None:
                                    predecessors = list(self._cfg.predecessors(successor))
                                
                                    if len(predecessors) > 1:
                                        pre_dominator  = self._match_ENDIF_to_IF[successor]
                                    
                                    else:
                                        del self._match_ENDIF_to_IF[successor]
                        
                        self._pre_dominators[successor].append(pre_dominator)
                        
                        if len(self._pre_dominators[pre_dominator]) != 0:                      
                            self._pre_dominators[successor].extend(self._pre_dominators[pre_dominator])
                            self._pre_dominators[successor] = list(set(self._pre_dominators[successor]))

                        bfs_stack.append(successor)
                else:
                    for successor in successors:
                        ir = successor._instructions[-1]
                        pre_dominator = node
                        
                        if type(ir).__name__ == 'Node':
                            if ir.type == NodeType.ENDIF:
                                predecessors = list(self._cfg.predecessors(successor))
                                if self._match_ENDIF_to_IF.get(successor) != None:
                                    if len(predecessors) > 1:
                                        pre_dominator  = self._match_ENDIF_to_IF[successor]
                                    
                                    else:
                                        del self._match_ENDIF_to_IF[successor]
                            
                            if ir.type == NodeType.ENDLOOP:
                                if self._match_ENDIF_to_IF.get(successor) != None:
                                    predecessors = list(self._cfg.predecessors(successor))
                                
                                    if len(predecessors) > 1:
                                        pre_dominator  = self._match_ENDIF_to_IF[successor]
                                    
                                    else:
                                        del self._match_ENDIF_to_IF[successor]

                        old_len = len(self._pre_dominators[successor])
                        
                        self._pre_dominators[successor].append(pre_dominator)
                        
                        if len(self._pre_dominators[pre_dominator]) != 0:                      
                            self._pre_dominators[successor].extend(self._pre_dominators[pre_dominator])
                            self._pre_dominators[successor] = list(set(self._pre_dominators[successor]))

                        new_len = len(self._pre_dominators[successor])
                        
                        if old_len < new_len and successor not in bfs_stack:
                             bfs_stack.append(successor)           


    # Check whether a particular instruction is a call instruction.
    # Returns True if Yes, False otherwise
    def is_ir_call(self, ir):
        if type(ir).__name__ == 'LowLevelCall':
            return True
        elif type(ir).__name__ == 'HighLevelCall':
            return True
        elif type(ir).__name__ == 'InternalCall':
            return True
        elif type(ir).__name__ == 'LibraryCall':
            return True
        elif type(ir).__name__ == 'EventCall':
            return True
        elif type(ir).__name__ == 'Send':
            return True
        elif type(ir).__name__ == 'Transfer':
            return True
        else:
            return False

    def is_call_present(self, node):
        if node.internal_calls:
            return True
        elif node.solidity_calls:
            return True
        elif node.low_level_calls:
            return True
        elif node.high_level_calls:
            return True
        elif node.library_calls:
            return True
        else:
            return False
    
    def is_lvalue_storage(self, lvalue):
        if type(lvalue).__name__ == 'StateVariableSolc' or type(lvalue).__name__ == 'StateVariable':
            return True
        
        else:
            if type(lvalue).__name__ == 'ReferenceVariable':
                origin_var = lvalue.points_to_origin
                # first place
                if type(origin_var).__name__ == 'StateVariableSolc' or type(origin_var).__name__ == 'StateVariable':
                    return True
                else:
                    return False
            else:
                return False


    def get_refvar_names(self, instr):
        str_instr = str(instr)
        instr_tokens = str_instr.split(" ")
        
        if instr_tokens[0].startswith('REF_') and instr_tokens[1] == '->':
            CFG.refvar_names[instr_tokens[0]] = instr_tokens[2]
    
    # This function adds the IR instructions to the current basic block.
    # If the instruction is a call instruction, it ends the basic block there
    # and start a new one for the next instruction to be added.
    # It inserts the newly created basic block after the previous one
    # in the list. It returns the running basic block.
    def node_to_irssa(self, function, node, basic_block):
        basic_block._expressions.append((node.expression, node.type))
        variable_add_nodetype = False
        call_add_nodetype = False
        if node.type != NodeType.ENTRYPOINT:
            if node.irs:
                if node.type == NodeType.VARIABLE:
                    variable_add_nodetype = True
                for ir in node.irs:
                    if call_add_nodetype:
                        basic_block._expressions.append((node.expression, node.type))
                        call_add_nodetype= False
                    self.get_refvar_names(ir)
                    
                    if hasattr(ir, 'lvalue'):
                        if ir.lvalue not in CFG.lvalue_vars.keys():
                            CFG.lvalue_vars[ir.lvalue] = []
                        
                        if self.is_lvalue_storage(ir.lvalue):
                            self.state_vars_written[ir] = basic_block

                        if ir not in CFG.lvalue_vars[ir.lvalue]:
                            CFG.lvalue_vars[ir.lvalue].append(ir)

                        if type(ir).__name__ == 'Member' or type(ir).__name__ == 'Index':
                            if type(ir.variable_left).__name__ == 'ReferenceVariable':
                                CFG.member_ir_var_left.append(ir.variable_left)
                            
                            if type(ir.variable_right).__name__ == 'ReferenceVariable':
                                CFG.member_ir_var_left.append(ir.variable_right)

                    if type(ir).__name__ == 'Return':
                        self._returns_irs.append(ir)

                    # If the basic block is not added already to the node -> basic block list, add it now.
                    # This situation can arise if a new basic block is created in the previous iteration 
                    # and it has not been added to the node -> basic block list
                    if basic_block not in self._node_to_block_mapping[node]:
                        self._node_to_block_mapping[node].append(basic_block)
                    
                    # If the IR is a call instruction, end the running basic block and create a new one,
                    # add it to the function block list
                    if self.is_ir_call(ir) or type(ir).__name__ == 'NewContract':
                        if type(ir).__name__ == 'InternalCall' or type(ir).__name__ == 'HighLevelCall' or type(ir).__name__ == 'LibraryCall':
                            self._ircall_to_bb[ir] = basic_block

                        basic_block._instructions.append(ir)
                        self._ir_to_block[ir] = basic_block
                        basic_block._ir_to_node_map[ir] = node
                        
                        if basic_block not in self._function_basic_blocks:
                            self._function_basic_blocks.append(basic_block)

                        # Get the index of the previous basic block  
                        next_index = self._function_basic_blocks.index(basic_block) + 1
                        #        expression
                        basic_block._expressions = basic_block._expressions[:-1]
                        if not variable_add_nodetype:
                            basic_block._expressions.append((node.expression, NodeType.EXPRESSION))
                        call_add_nodetype = True
                        basic_block = BasicBlock([])
                        # Adds the newly created basic block after the previous one
                        self._function_basic_blocks.insert(next_index, basic_block)
                    
                    else:
                        self._ir_to_block[ir] = basic_block
                        basic_block._instructions.append(ir)
                        basic_block._ir_to_node_map[ir] = node
            else:
                # If the node is a placeholder we should end the basic block
                # here and start a new from the next instruction because the execution
                # will start from the different function instead of executinf the immediate 
                # next instruction
                if node.type == NodeType.PLACEHOLDER:
                    basic_block._instructions.append(node)
                    self._ir_to_block[node] = basic_block
                    basic_block._ir_to_node_map[node] = node
                    
                    if basic_block not in self._function_basic_blocks:
                        self._function_basic_blocks.append(basic_block)

                    # Get the index of the previous basic block  
                    next_index = self._function_basic_blocks.index(basic_block) + 1
                    basic_block = BasicBlock([])
                    # Adds the newly created basic block after the previous one
                    self._function_basic_blocks.insert(next_index, basic_block)
                
                else:
                    self._ir_to_block[node] = basic_block
                    basic_block._instructions.append(node)
                    basic_block._ir_to_node_map[node] = node
        else:
            basic_block._instructions.append(node)
            basic_block._ir_to_node_map[node] = node
            self._ir_to_block[node] = basic_block
        if variable_add_nodetype:
            basic_block._expressions.append((node.expression, NodeType.EXPRESSION))
        if call_add_nodetype:
            basic_block._expressions.append((node.expression, node.type))
        
        return basic_block
    

    def remove_empty_basic_blocks(self):

        node_to_blocks = copy.copy(self._function_basic_blocks)

        for block in node_to_blocks:
            if len(block._instructions) == 0:
                self._function_basic_blocks.remove(block)
        
        '''
        for node, blocks in node_to_blocks.items():
            for block in blocks:
                if len(block._instructions) == 0:
                    self._node_to_block_mapping[node].remove(block)
                    self._function_basic_blocks.remove(block)
        '''
    

    # Adds an edge between two blocks
    def connect_blocks(self, graph, src_block, dest_block):
        if not isinstance(src_block, BasicBlock) or not isinstance(dest_block, BasicBlock):
            raise RuntimeError("src: ", str(src_block), "dest: ", str(dest_block))
        if graph.has_edge(src_block, dest_block):
            return
        graph.add_edge(src_block, dest_block)
    
    
    def consecutive_event_calls(self, node, latest_son):
        for son in node.sons:
            if son.type == NodeType.EXPRESSION and \
                len(son.irs) != 0 and type(son.irs[-1]).__name__ == 'EventCall':
                latest_son.extend(self.consecutive_event_calls(son, latest_son))
            else:
                latest_son.append(son)
        return latest_son
    
    def consecutive_placeholder(self, node, latest_son):
        for son in node.sons:
            if son.type == NodeType.PLACEHOLDER:
                latest_son.extend(self.consecutive_placeholder(son, latest_son))
            else:
                latest_son.append(son)
        return latest_son
    
    '''
        This function builds the CFG given all the basic blocks. It adds two types of edges:
            1. Adds an edge between every two basic blocks originating from the same node.
            2. Adds an edge from the last basic block of the father node to the first basic block of the son node
    '''
    def connect_all_basic_blocks(self, function, cfg_nodes, cfg):

        for node in cfg_nodes:
            if self._node_to_block_mapping.get(node) != None:
            # Get the first basic block originating from a node
                start_block = self._node_to_block_mapping[node][0]
            
            else:
                continue
            
            if node.type == NodeType.PLACEHOLDER and config.get_normalize():
                continue
            
            if node.type == NodeType.EXPRESSION and \
              len(node.irs) != 0 and type(node.irs[-1]).__name__ == 'EventCall' and config.get_prune():
                continue
            
            # Get the id of the basic block
            block_id = self.blockid[start_block]
            #if block_id == 23:

            # Get all the basic blocks for that node
            blocks = self._node_to_block_mapping[node]

            for block in blocks:
                # Adds the basic block as a node in the graph if not added already
                if not cfg.has_node(block):
                    cfg.add_node(block, shape='box')

                # Adds an edge between every two basic blocks originating from the same node.
                if start_block != block:
                    self.connect_blocks(cfg, start_block, block)
                start_block = block
            
            # Adds an edge from the last basic block of the father node 
            # to the first basic block of the son node
            for son in node.sons:
                # If the function is revert then do not add any edge from that basic block, since revert() means 
                # that the transaction should be reverted and execution should not continue to the next basic block
                if type(self._node_to_block_mapping[node][-1]._instructions[-1]).__name__ == 'SolidityCall' \
                        and (self._node_to_block_mapping[node][-1]._instructions[-1].function.name == 'revert()'\
                            or type(self._node_to_block_mapping[node][-1]._instructions[-1].function).__name__ == "SolidityCustomRevert" \
                                or "revert(" in self._node_to_block_mapping[node][-1]._instructions[-1].function.name):
                    continue
                
                if son.type == NodeType.PLACEHOLDER and config.get_normalize():
                    for new_son in self.consecutive_placeholder(son, []):
                        if type(self._node_to_block_mapping[new_son][-1]._instructions[-1]).__name__ == 'SolidityCall' \
                                and self._node_to_block_mapping[new_son][-1]._instructions[-1].function.name in ["require(bool)", "require(bool,string)", "assert(bool)"]:
                                    pass
                        
                        new_son_block = self._node_to_block_mapping[new_son][0]
                        end_block = self._node_to_block_mapping[node][-1]

                        index = self.blockid[end_block]

                        if new_son_block != end_block:
                            self.connect_blocks(cfg, end_block, new_son_block)
                
                elif son.type == NodeType.EXPRESSION and \
                    len(son.irs) != 0 and type(son.irs[-1]).__name__ == 'EventCall' and config.get_prune():
                        for new_son in self.consecutive_event_calls(son, []):
                            if type(self._node_to_block_mapping[new_son][-1]._instructions[-1]).__name__ == 'SolidityCall' \
                                    and self._node_to_block_mapping[new_son][-1]._instructions[-1].function.name in ["require(bool)", "require(bool,string)", "assert(bool)"]:
                                        pass
                            
                            new_son_block = self._node_to_block_mapping[new_son][0]
                            end_block = self._node_to_block_mapping[node][-1]

                            index = self.blockid[end_block]

                            if new_son_block != end_block:
                                self.connect_blocks(cfg, end_block, new_son_block)
                
                else:
                    if type(self._node_to_block_mapping[son][-1]._instructions[-1]).__name__ == 'SolidityCall' \
                            and self._node_to_block_mapping[son][-1]._instructions[-1].function.name in ["require(bool)", "require(bool,string)", "assert(bool)"]:
                                pass
                    
                    son_block = self._node_to_block_mapping[son][0]
                    end_block = self._node_to_block_mapping[node][-1]

                    index = self.blockid[end_block]

                    if son_block != end_block:
                        self.connect_blocks(cfg, end_block, son_block)

    def connect_all_basic_blocks_withconvert(self, function, cfg_nodes, cfg):
        self.connect_all_basic_blocks(function, cfg_nodes, cfg)
            
        require_nodes = []
        nodescope = None
        filescope = None
        for node in cfg.nodes:
            if len(node._expressions):
                _, nodetype = node._expressions[0]
                if nodetype == NodeType.ENTRYPOINT:
                    nodescope = node._instructions[-1].scope
                    filescope = node._instructions[-1].file_scope


            if type(node._instructions[-1]).__name__ == "SolidityCall" \
                and node._instructions[-1].function.name in ["require(bool)", "require(bool,string)", "assert(bool)"]:
                require_nodes.append(node)
        
        for node in require_nodes:
            predecessors_copy = list(cfg.predecessors(node))
            successors_copy = list(cfg.successors(node))

            require_if_block = BasicBlock(node._instructions[:-1])
            require_instr = node._instructions[-1]
            if node._instructions[-1].function.name == "require(bool,string)":
                try:
                    require_if_block._expressions.append((node._instructions[-2], NodeType.IF))
                except IndexError:
                    require_if_block._expressions.append(("qiantao require", NodeType.IF))
                require_condition_temp = require_instr.arguments[0]
                cond = Condition(require_condition_temp)
                cond.set_expression("")
                require_if_block._instructions.append(cond)
            elif node._instructions[-1].function.name == "require(bool)":
                try:
                    require_if_block._expressions.append((str(node._instructions[-2]), NodeType.IF))
                except IndexError:
                    require_if_block._expressions.append((str(node._instructions[-1]), NodeType.IF))
                require_condition_temp = require_instr.arguments[0]
                cond = Condition(require_condition_temp)
                cond.set_expression("")
                # cond.set_node()
                require_if_block._instructions.append(cond)
            elif node._instructions[-1].function.name == "assert(bool)":
                try:
                    require_if_block._expressions.append((str(node._instructions[-2]), NodeType.IF))
                except IndexError:
                    require_if_block._expressions.append((str(node._instructions[-1]), NodeType.IF))
                require_condition_temp = require_instr.arguments[0]
                cond = Condition(require_condition_temp)
                cond.set_expression("")
                # cond.set_node()
                require_if_block._instructions.append(cond)

            for predcessor in predecessors_copy:
                self.connect_blocks(cfg, predcessor, require_if_block)

            # revert Block
            require_revert_block = BasicBlock([])
            require_revert_block._is_True = True
            revert_sol_func = SolidityFunction("revert()")
            revert_call = SolidityCall(
                revert_sol_func,
                0,
                require_instr.lvalue,
                "tuple()"
            )
            require_revert_block._instructions.append(revert_call)
            require_revert_block._expressions.append(("revert()()", NodeType.EXPRESSION))
            self.connect_blocks(cfg, require_if_block, require_revert_block)
            # SOLIDITYCALL revert()

            # ENDIF Block
            require_endif_block = BasicBlock([])
            require_endif_block._is_True = False
            endif_node = Node(NodeType.ENDIF, 0, nodescope, filescope)
            require_endif_block._instructions.append(endif_node)
            require_endif_block._expressions.append((None, NodeType.ENDIF))
            self.connect_blocks(cfg, require_if_block, require_endif_block)

            for successor in successors_copy:
                self.connect_blocks(cfg, require_endif_block, successor)
            
            cfg.remove_node(node)                     

    '''
        This function extracts the basic blocks from the function node and Slither IR.
        Every basic block should end after either a conditional statement or a call instruction.
        A Slither entry node should always be in a separate basic block.
    '''
    def get_basic_blocks(self, root_node, function):
        self._function_basic_blocks = []
        if_stack = []
        node_stack = []
        if_loop_stack = []
        visited_nodes = []
        
        block = []
        basic_block = BasicBlock(block)
            #import ipdb; ipdb.set_trace()

        if len(function.nodes) > 0:
            node = root_node
            node_stack.append(node)
            
            while len(node_stack) > 0:
                empty_nodestack = False
                node = node_stack.pop()
                visited_nodes.append(node)
                
                for son in node.sons:
                    if son not in visited_nodes:
                        node_stack.append(son)
                        
                
                if config.get_normalize():
                    while node.type == NodeType.PLACEHOLDER:
                        if len(node_stack) > 0:
                            node = node_stack.pop()
                            visited_nodes.append(node)
                            
                            for son in node.sons:
                                if son not in visited_nodes:
                                    node_stack.append(son)
                        else:
                            empty_nodestack = True
                            break
                
                if config.get_prune():
                    while node.type == NodeType.EXPRESSION and \
                        len(node.irs) != 0 and type(node.irs[-1]).__name__ == 'EventCall':
                        
                        if len(node_stack) > 0:
                            node = node_stack.pop()
                            visited_nodes.append(node)
                            
                            for son in node.sons:
                                if son not in visited_nodes:
                                    node_stack.append(son)
                        else:
                            empty_nodestack = True
                            break
                    
                if empty_nodestack:
                    continue
                        
            #for node in function.nodes:    

                # If this is an entry node, start a fresh basic block
                # from the next node onwards
                if node.type == NodeType.ENTRYPOINT:
                    # Add the corresponding ir to the basic block
                    basic_block = self.node_to_irssa(function, node, basic_block)

                    self._root_basic_block = basic_block

                    # Add this block to the list of function basic blocks
                    self._function_basic_blocks.append(basic_block)

                    # Add this block to the list of all basic blocks for this node
                    self._node_to_block_mapping[node] = [basic_block]

                    # Mark this node as the running basic block for the node
                    self._next_block_to_node[node] = basic_block

                    # Start a fresh block for the next node
                    block = []
                    basic_block = BasicBlock(block)

                
                # If the node is conditional we know that the current basic block should end at this node
                # and a ne should start from the next node onwards
                elif node.is_conditional():
                    # If the node is already present in the node to mapping list, this can happend due to sons
                    # block getting created a priori
                    if node in self._node_to_block_mapping.keys():
                        basic_block = self._next_block_to_node[node]
                    
                    # Otherwise add this block to the list of all basic blocks for this node
                    # Add the corresponding ir to the basic block
                    # Mark this node as the running basic block for the node
                    else:
                        self._node_to_block_mapping[node].append(basic_block)
                        basic_block = self.node_to_irssa(function, node, basic_block)
                        self._next_block_to_node[node] = basic_block
                    
                    # Add the block to the list of function basic blocks if not already added
                    if basic_block not in self._function_basic_blocks:
                        self._function_basic_blocks.append(basic_block)

                    
                    if node.type == NodeType.IFLOOP:
                        if_loop_stack.append(basic_block)
                    
                    # This is to track IF-ENDIF
                    elif len(node.sons) > 1:
                        if_stack.append(basic_block)
                    
                    condition = "true"
                    parent_basic_block = basic_block

                    # For every sons of the node start a fresh basic block , add irs to the block,
                    # add that block to the list of basic blocks
                    # map the running basic block to that node
                    for son in node.sons:
                        # If son is alread added as a basic block, just retrieve it, it may happene
                        # if say require() is the last statement of if/else block
                        if son in self._node_to_block_mapping.keys():
                            basic_block = self._next_block_to_node[son]

                            # This is to track whether a path constraint need to true or false to reach the son block
                            if condition == "true":
                                basic_block._is_True = True
                                self._condition_to_sons[parent_basic_block][condition] = basic_block
                                condition = "false"
                            
                            else:
                                self._condition_to_sons[parent_basic_block][condition] = basic_block
                                basic_block._is_True = False
                        else:
                            block = []
                            basic_block = BasicBlock(block)
                            self._node_to_block_mapping[son].append(basic_block)
                            
                            # This is to track whether a path constraint need to true or false to reach the son block
                            if condition == "true":
                                basic_block._is_True = True
                                self._condition_to_sons[parent_basic_block][condition] = basic_block
                                condition = "false"
                            
                            else:
                                basic_block._is_True = False
                                self._condition_to_sons[parent_basic_block][condition] = basic_block
                            
                            basic_block = self.node_to_irssa(function, son, basic_block)
                            self._next_block_to_node[son] = basic_block

                        if basic_block not in self._function_basic_blocks:
                            self._function_basic_blocks.append(basic_block)
                        
                elif node.type == NodeType.STARTLOOP:
                    
                    if node in self._node_to_block_mapping.keys():
                        basic_block = self._next_block_to_node[node]
                    
                    else:
                        block = []
                        basic_block = BasicBlock(block)
                        self._node_to_block_mapping[node].append(basic_block)
                        basic_block = self.node_to_irssa(function, node, basic_block)
                        self._next_block_to_node[node] = basic_block
                    
                    if basic_block not in self._function_basic_blocks:
                        self._function_basic_blocks.append(basic_block)
                
                else:
                    # If it is a phi node , that is it has more than one father either start a fresh block or
                    # extract the block from the node to block mapping if present.
                    # add that block to the list of basic blocks
                    # map the running basic block to that node
                    if len(node.fathers) > 1 or (len(node.fathers) == 1 and node.type == NodeType.ENDIF) or (len(node.fathers) == 1 and node.type == NodeType.ENDLOOP):
                        
                        if node in self._node_to_block_mapping.keys():
                            basic_block = self._next_block_to_node[node]
                        
                        else:
                            block = []
                            basic_block = BasicBlock(block)
                            self._node_to_block_mapping[node].append(basic_block)
                            basic_block = self.node_to_irssa(function, node, basic_block)
                            self._next_block_to_node[node] = basic_block
                        
                        if basic_block not in self._function_basic_blocks:
                            self._function_basic_blocks.append(basic_block)
                        
                        if len(if_stack) != 0 and (node.type == NodeType.ENDIF):
                            if_basic_block = if_stack.pop()
                            self._match_ENDIF_to_IF[basic_block] = if_basic_block
                        
                        if node.type == NodeType.ENDLOOP:
                            if len(if_loop_stack) != 0:
                                if_loop = if_loop_stack.pop()
                                self._match_ENDIF_to_IF[basic_block] = if_loop
                        
                        # The node which has more than one father should be a phi node and
                        # next node should start from a seprate basic block
                        block = []
                        basic_block = BasicBlock(block)

                    # Otherwise add the instruction to the running basic block for that node 
                    # add that block to the list of basic blocks
                    # map the running basic block to that node
                    elif len(node.fathers) == 1:
                        
                        if node in self._node_to_block_mapping.keys():
                            basic_block = self._next_block_to_node[node]
                        else:
                            self._node_to_block_mapping[node].append(basic_block)
                            basic_block = self.node_to_irssa(function, node, basic_block)
                            self._next_block_to_node[node] = basic_block
                        
                        if len(if_stack) != 0 and (node.type == NodeType.ENDIF):
                            if_basic_block = if_stack.pop()
                            self._match_ENDIF_to_IF[basic_block] = if_basic_block 

                        if node.type == NodeType.ENDLOOP:
                            if len(if_loop_stack) != 0:
                                if_loop = if_loop_stack.pop()
                                self._match_ENDIF_to_IF[basic_block] = if_loop
                        
                        if basic_block not in self._function_basic_blocks:
                            self._function_basic_blocks.append(basic_block)
                    else:
                        # This is mainly for modifiers, which do not have any fathers, they should
                        # not be connected why any basic blocks
                        if len(basic_block._instructions) != 0:
                            block = []
                            basic_block = BasicBlock(block)
                        
                        if node in self._node_to_block_mapping.keys():
                            basic_block = self._next_block_to_node[node]
                        else:
                            self._node_to_block_mapping[node].append(basic_block)
                            basic_block = self.node_to_irssa(function, node, basic_block)
                            self._next_block_to_node[node] = basic_block
                            
                        if basic_block not in self._function_basic_blocks:
                            self._function_basic_blocks.append(basic_block)
                        

            self.remove_empty_basic_blocks()
            # Get the block id's from the function blocks
            for basic_block in self._function_basic_blocks:
                self.blockid[basic_block] = self._function_basic_blocks.index(basic_block)
            
        return visited_nodes
        
    # Print the CFG in a dot file
    def print_cfg_dot(self, graph_dir, function, graph):
        if config.skip_dump_file(function.name):
            return
        if len(list(graph.nodes())) == 0:
            return
        
        if config.get_dappScan():
            graph_dir = config.get_dapp_graph_dir(graph_dir, function.full_name)
        
        content = ''
        # Ref: https://stackoverflow.com/questions/33722809/nx-write-dot-generates-redundant-nodes-when-input-nodes-have-a-colon
        dot_file_name = function.full_name + "_cfg.dot"
        dot_file_path = os.path.join(graph_dir, dot_file_name)
        with open(dot_file_path, 'w', encoding='utf8') as fp:
            nx.drawing.nx_pydot.write_dot(graph, fp)

        if config.get_scale():
            return
        (graph, ) = pydot.graph_from_dot_file(dot_file_path)

        png_file_name = function.name + "_cfg.png"
        png_file_path = os.path.join(graph_dir, png_file_name)
        try:
            graph.write_png(png_file_path)
        except:
            print("    ：", png_file_path)