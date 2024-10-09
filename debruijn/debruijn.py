#!/bin/env python3
# -*- coding: utf-8 -*-
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#    A copy of the GNU General Public License is available at
#    http://www.gnu.org/licenses/gpl-3.0.html

"""Perform assembly based on debruijn graph."""

import argparse
import os
import sys
from pathlib import Path
from networkx import (
    DiGraph,
    all_simple_paths,
    lowest_common_ancestor,
    has_path,
    random_layout,
    draw,
    spring_layout,
)
import networkx as nx
import matplotlib
from operator import itemgetter
import random

random.seed(9001)
from random import randint
import statistics
import textwrap
import matplotlib.pyplot as plt
from typing import Iterator, Dict, List

matplotlib.use("Agg")

__author__ = "Stéphanie Gnanalingam"
__copyright__ = "Universite Paris Cité"
__credits__ = ["Stéphanie Gnanalingam"]
__license__ = "GPL"
__version__ = "1.0.0"
__maintainer__ = "Stéphanie Gnanalingam"
__email__ = "stephanie.gnanalingam@etu.u-paris.fr"
__status__ = "Developpement"


def isfile(path: str) -> Path:  # pragma: no cover
    """Check if path is an existing file.

    :param path: (str) Path to the file

    :raises ArgumentTypeError: If file does not exist

    :return: (Path) Path object of the input file
    """
    myfile = Path(path)
    if not myfile.is_file():
        if myfile.is_dir():
            msg = f"{myfile.name} is a directory."
        else:
            msg = f"{myfile.name} does not exist."
        raise argparse.ArgumentTypeError(msg)
    return myfile


def get_arguments():  # pragma: no cover
    """Retrieves the arguments of the program.

    :return: An object that contains the arguments
    """
    # Parsing arguments
    parser = argparse.ArgumentParser(
        description=__doc__, usage="{0} -h".format(sys.argv[0])
    )
    parser.add_argument(
        "-i", dest="fastq_file", type=isfile, required=True, help="Fastq file"
    )
    parser.add_argument(
        "-k", dest="kmer_size", type=int, default=22, help="k-mer size (default 22)"
    )
    parser.add_argument(
        "-o",
        dest="output_file",
        type=Path,
        default=Path(os.curdir + os.sep + "contigs.fasta"),
        help="Output contigs in fasta file (default contigs.fasta)",
    )
    parser.add_argument(
        "-f", dest="graphimg_file", type=Path, help="Save graph as an image (png)"
    )
    return parser.parse_args()


def read_fastq(fastq_file: Path) -> Iterator[str]:
    """Extract reads from fastq files.

    :param fastq_file: (Path) Path to the fastq file.
    :return: A generator object that iterate the read sequences.
    """
    with open(fastq_file, "r") as file_read:
        file_iter = iter(file_read)
        while True:
            try:
                next(file_iter)
                sequence = next(file_iter).strip()
                next(file_iter)
                next(file_iter)
                yield sequence
            except:
                return

def cut_kmer(read: str, kmer_size: int) -> Iterator[str]:
    """Cut read into kmers of size kmer_size.

    :param read: (str) Sequence of a read.
    :return: A generator object that provides the kmers (str) of size kmer_size.
    """
    for i in range(len(read)-kmer_size+1):
        yield read[i:i+kmer_size]


def build_kmer_dict(fastq_file: Path, kmer_size: int) -> Dict[str, int]:
    """Build a dictionnary object of all kmer occurrences in the fastq file

    :param fastq_file: (str) Path to the fastq file.
    :return: A dictionnary object that identify all kmer occurrences.
    """
    kmer_dict = {}
    for reads in read_fastq(fastq_file):
        for kmer in cut_kmer(reads, kmer_size):
            kmer_dict[kmer] = kmer_dict.get(kmer, 0)+1
    return kmer_dict

def build_graph(kmer_dict: Dict[str, int]) -> DiGraph:
    """Build the debruijn graph

    :param kmer_dict: A dictionnary object that identify all kmer occurrences.
    :return: A directed graph (nx) of all kmer substring and weight (occurrence).
    """
    graph = DiGraph()
    for kmer, weight in kmer_dict.items():
        graph.add_edge(kmer[:-1], kmer[1:], weight=weight)
    return graph


def remove_paths(
    graph: DiGraph,
    path_list: List[List[str]],
    delete_entry_node: bool,
    delete_sink_node: bool,
) -> DiGraph:
    """Remove a list of path in a graph. A path is set of connected node in
    the graph

    :param graph: (nx.DiGraph) A directed graph object
    :param path_list: (list) A list of path
    :param delete_entry_node: (boolean) True->We remove the first node of a path
    :param delete_sink_node: (boolean) True->We remove the last node of a path
    :return: (nx.DiGraph) A directed graph object
    """
    for path in path_list:
        if delete_entry_node is True and delete_sink_node is True:
                graph.remove_nodes_from(path)
        elif delete_entry_node is True:
            for node in path[:-1]:
                graph.remove_node(node)
        elif delete_sink_node is True:
            for node in path[1:]:
                graph.remove_node(node)
        elif delete_entry_node is False and delete_sink_node is False:
            for node in path[1:-1]:
                graph.remove_node(node)
    return graph

def select_best_path(
    graph: DiGraph,
    path_list: List[List[str]],
    path_length: List[int],
    weight_avg_list: List[float],
    delete_entry_node: bool = False,
    delete_sink_node: bool = False,
) -> DiGraph:
    """Select the best path between different paths

    :param graph: (nx.DiGraph) A directed graph object
    :param path_list: (list) A list of path
    :param path_length_list: (list) A list of length of each path
    :param weight_avg_list: (list) A list of average weight of each path
    :param delete_entry_node: (boolean) True->We remove the first node of a path
    :param delete_sink_node: (boolean) True->We remove the last node of a path
    :return: (nx.DiGraph) A directed graph object
    """
    if statistics.stdev(weight_avg_list) > 0:
        best_path_index = weight_avg_list.index(max(weight_avg_list))
    else:
        std_lengths = statistics.stdev(path_length)
        if std_lengths > 0:
            best_path_index = path_length.index(max(path_length))
        elif std_lengths == 0:
            best_path_index = random.randint(0, len(path_length)-1)
    paths_to_remove = [path for i, path in enumerate(path_list) if i != best_path_index]
    graph = remove_paths(graph, paths_to_remove, delete_entry_node, delete_sink_node)
    return graph

def path_average_weight(graph: DiGraph, path: List[str]) -> float:
    """Compute the weight of a path

    :param graph: (nx.DiGraph) A directed graph object
    :param path: (list) A path consist of a list of nodes
    :return: (float) The average weight of a path
    """
    return statistics.mean(
        [d["weight"] for (u, v, d) in graph.subgraph(path).edges(data=True)]
    )


def solve_bubble(graph: DiGraph, ancestor_node: str, descendant_node: str) -> DiGraph:
    """Explore and solve bubble issue

    :param graph: (nx.DiGraph) A directed graph object
    :param ancestor_node: (str) An upstream node in the graph
    :param descendant_node: (str) A downstream node in the graph
    :return: (nx.DiGraph) A directed graph object
    """
    path_list = list(all_simple_paths(graph, ancestor_node, descendant_node))
    weight_avg_list = [path_average_weight(graph, a_path) for a_path in path_list]
    path_length = [len(a_path) for a_path in path_list]
    return select_best_path(graph, path_list, path_length, weight_avg_list)

def simplify_bubbles(graph: DiGraph) -> DiGraph:
    """Detect and explode bubbles

    :param graph: (nx.DiGraph) A directed graph object
    :return: (nx.DiGraph) A directed graph object
    """
    bubble = False
    for node in graph.nodes():
        list_predecessors = list(graph.predecessors(node))
        if len(list_predecessors) > 1:
            for i in range(len(list_predecessors)):
                for j in range(i+1, len(list_predecessors)):
                    ancestor_node = lowest_common_ancestor(graph, list_predecessors[i], list_predecessors[j])
                    if ancestor_node != None:
                        bubble = True
                        break
        if bubble is True:
            break
    if bubble:
        graph = simplify_bubbles(solve_bubble(graph, ancestor_node, node))
    return graph


def solve_entry_tips(graph: DiGraph, starting_nodes: List[str]) -> DiGraph:
    """Remove entry tips

    :param graph: (nx.DiGraph) A directed graph object
    :param starting_nodes: (list) A list of starting nodes
    :return: (nx.DiGraph) A directed graph object
    """
    point = False
    for node in graph.nodes():
        if node not in starting_nodes:
            predecessors = list(graph.predecessors(node))
            if len(predecessors) > 1:
                path_list = []
                for start_node in starting_nodes:
                    if has_path(graph, start_node, node):
                        path_list += list(all_simple_paths(graph, start_node, node))
                point = True
            if point is True:
                break
    if point is True and len(path_list) > 1:
        weight_avg_list = [path_average_weight(graph, a_path) for a_path in path_list]
        path_length = [len(a_path) for a_path in path_list]
        graph = select_best_path(graph, path_list, path_length, weight_avg_list, delete_entry_node=True,
                        delete_sink_node=False)
        new_starting_point = get_starting_nodes(graph)
        graph = solve_entry_tips(graph, new_starting_point)
    return graph


def solve_out_tips(graph: DiGraph, ending_nodes: List[str]) -> DiGraph:
    """Remove out tips

    :param graph: (nx.DiGraph) A directed graph object
    :param ending_nodes: (list) A list of ending nodes
    :return: (nx.DiGraph) A directed graph object
    """
    point = False
    for node in graph.nodes():
        if node not in ending_nodes:
            successors = list(graph.successors(node))
            if len(successors) > 1:
                path_list = []
                for end_node in ending_nodes:
                    if has_path(graph, node, end_node):
                        path_list += list(all_simple_paths(graph, node, end_node))
                point = True
            if point is True:
                break
    if point is True and len(path_list) > 1:
        weight_avg_list = [path_average_weight(graph, a_path) for a_path in path_list]
        path_length = [len(a_path) for a_path in path_list]
        graph = select_best_path(graph, path_list, path_length, weight_avg_list, delete_entry_node=False,
                        delete_sink_node=True)
        new_ending_nodes = get_sink_nodes(graph)
        graph = solve_out_tips(graph, new_ending_nodes)
    return graph


def get_starting_nodes(graph: DiGraph) -> List[str]:
    """Get nodes without predecessors

    :param graph: (nx.DiGraph) A directed graph object
    :return: (list) A list of all nodes without predecessors
    """
    list_starting_nodes = []
    for node in graph.nodes():
        if len(list(graph.predecessors(node))) == 0:
            list_starting_nodes.append(node)
    return list_starting_nodes


def get_sink_nodes(graph: DiGraph) -> List[str]:
    """Get nodes without successors

    :param graph: (nx.DiGraph) A directed graph object
    :return: (list) A list of all nodes without successors
    """
    list_ending_nodes = []
    for node in graph.nodes():
        if len(list(graph.successors(node))) == 0:
            list_ending_nodes.append(node)
    return list_ending_nodes


def get_contigs(
    graph: DiGraph, starting_nodes: List[str], ending_nodes: List[str]
) -> List:
    """Extract the contigs from the graph

    :param graph: (nx.DiGraph) A directed graph object
    :param starting_nodes: (list) A list of nodes without predecessors
    :param ending_nodes: (list) A list of nodes without successors
    :return: (list) List of [contiguous sequence and their length]
    """
    list_contigs = []
    for node_start in starting_nodes:
        for node_end in ending_nodes:
            if has_path(graph, node_start, node_end):
                for a_path in all_simple_paths(graph, node_start, node_end):
                    contig_i = a_path[0]
                    for node in a_path[1:]:
                        contig_i += node[-1]
                    list_contigs.append([contig_i, len(contig_i)])
    return list_contigs


def save_contigs(contigs_list: List[str], output_file: Path) -> None:
    """Write all contigs in fasta format

    :param contig_list: (list) List of [contiguous sequence and their length]
    :param output_file: (Path) Path to the output file
    """
    with open(output_file, "w") as fw:
        for counter, each_contig_info in enumerate(contigs_list):
            fw.write(f">contig_{str(counter)} len={str(each_contig_info[1])}\n")
            for i in range(0, each_contig_info[1], 80):
                fw.write(f"{each_contig_info[0][i:i+80]}\n")


def draw_graph(graph: DiGraph, graphimg_file: Path) -> None:  # pragma: no cover
    """Draw the graph

    :param graph: (nx.DiGraph) A directed graph object
    :param graphimg_file: (Path) Path to the output file
    """
    fig, ax = plt.subplots()
    elarge = [(u, v) for (u, v, d) in graph.edges(data=True) if d["weight"] > 3]
    # print(elarge)
    esmall = [(u, v) for (u, v, d) in graph.edges(data=True) if d["weight"] <= 3]
    # print(elarge)
    # Draw the graph with networkx
    # pos=nx.spring_layout(graph)
    pos = nx.random_layout(graph)
    nx.draw_networkx_nodes(graph, pos, node_size=6)
    nx.draw_networkx_edges(graph, pos, edgelist=elarge, width=6)
    nx.draw_networkx_edges(
        graph, pos, edgelist=esmall, width=6, alpha=0.5, edge_color="b", style="dashed"
    )
    # nx.draw_networkx(graph, pos, node_size=10, with_labels=False)
    # save image
    plt.savefig(graphimg_file.resolve())


# ==============================================================
# Main program
# ==============================================================
def main() -> None:  # pragma: no cover
    """
    Main program function
    """
    # Get arguments
    args = get_arguments()
    
    dict_file_kmer = build_kmer_dict(args.fastq_file, kmer_size=args.kmer_size)
    graph = build_graph(dict_file_kmer)
    starting_nodes = get_starting_nodes(graph)
    ending_nodes = get_sink_nodes(graph)
    
    graph = simplify_bubbles(graph)
    
    starting_nodes = get_starting_nodes(graph)
    graph = solve_entry_tips(graph, starting_nodes)
    
    ending_nodes = get_sink_nodes(graph)
    graph = solve_out_tips(graph, ending_nodes)
    
    starting_nodes = get_starting_nodes(graph)
    ending_nodes = get_sink_nodes(graph)
    
    list_contigs_from_fastq = get_contigs(graph, starting_nodes, ending_nodes)
    save_contigs(list_contigs_from_fastq, args.output_file)

    # Fonctions de dessin du graphe
    # A decommenter si vous souhaitez visualiser un petit
    # graphe
    # Plot the graph
    if args.graphimg_file:
        draw_graph(graph, args.graphimg_file)


if __name__ == "__main__":  # pragma: no cover
    main()

