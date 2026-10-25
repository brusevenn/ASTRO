#     ：
# https://gist.github.com/nuthanmunaiah/523a5e112f1e1f458e2c

import sys

import jsonpickle
import networkx
import networkx as nx
from lib.timing_decorator import timing_decorator_print
from networkx.readwrite import json_graph

# def store_wfg(call_graph, file_path):
#     '''Function to serialize a NetworkX DiGraph to a JSON file.'''
#     if not isinstance(call_graph, networkx.DiGraph):
#         raise Exception('call_graph has be an instance of networkx.DiGraph')

#     with open(file_path, 'w+') as _file:
#         _file.write(jsonpickle.encode(
#             json_graph.adjacency_data(call_graph))
#         )

# def load_wfg(file_path):
#     '''Function to deserialize a NetworkX DiGraph from a JSON file.'''
#     call_graph = None
#     with open(file_path, 'r+') as _file:
#         call_graph = json_graph.adjacency_graph(
#             jsonpickle.decode(_file.read()), 
#             directed=True
#         )
#     return call_graph

def graph2dict(graph):
	graph_dict = {}
	nodes = graph.nodes()
	edges = graph.edges()
	node_dict = {}
	for node_id in nodes: 
		node_dict[node_id] = graph.nodes[node_id]
	nodes_list = []
	for node in nodes:
		nodes_list.append(node)
	edges_list = []
	for edge in edges:
		edges_list.append([edge[0], edge[1]])
	graph_dict['nodes'] = nodes_list
	graph_dict['edges'] = edges_list
	graph_dict['node_dicts'] = node_dict
	return graph_dict


def dict2graph(line):
	graph = nx.MultiDiGraph() 
	graph_dict = eval(line)
	nodes = graph_dict['nodes']
	edges = graph_dict['edges']
	node_dict = graph_dict['node_dicts']
	
	graph.add_nodes_from(nodes) 
	graph.add_edges_from(edges) 
	for node_id in nodes: 
		graph.nodes[node_id].update(node_dict[node_id])
	return graph

def store_wfg(wfg, wfg_file):
	wfg_dict = graph2dict(wfg)
	with open(wfg_file, 'w') as fd:
		fd.write(repr(wfg_dict))

def load_wfg(wfg_file):
	try:
		with open(wfg_file, 'r') as fd:
			wfg_dict = fd.readline()
			wfg = dict2graph(wfg_dict)
			return wfg
	except Exception as e:
		return None