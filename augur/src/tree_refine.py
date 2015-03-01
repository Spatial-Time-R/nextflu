# clean, reroot, ladderize newick tree
# output to tree.json

import os, re, time
import dendropy
from io_util import *
from seq_util import *
from date_util import *
from tree_util import *

class tree_refine(object):
	def __init__(self,cds = (0,None), **kwargs):
		self.cds = cds

	def refine_generic(self):
		self.node_lookup = {node.taxon.label:node for node in self.tree.leaf_iter()}
		self.remove_outgroup()
		self.ladderize()
		self.collapse()
		self.translate_all()
		self.add_node_attributes()
		self.reduce()
		self.define_trunk()

		# make an amino acid aligment
		from Bio.Align import MultipleSeqAlignment
		from Bio.Seq import Seq
		from Bio.SeqRecord import SeqRecord
		tmp_aaseqs = [SeqRecord(Seq(node.aa_seq), id=node.strain, annotations = {'num_date':node.num_date}) for node in self.tree.leaf_iter()]
		tmp_aaseqs.sort(key = lambda x:x.annotations['num_date'])
		self.aa_aln = MultipleSeqAlignment(tmp_aaseqs)


	def remove_outgroup(self):
		"""Reroot tree to outgroup"""
		if self.outgroup['strain'] in self.node_lookup:
			outgroup_node = self.node_lookup[self.outgroup['strain']]
			self.tree.prune_subtree(outgroup_node)
			print "removed outgroup",self.outgroup['strain']
		else:
			print "outgroup",self.outgroup['strain'], "not found"
		if len(self.tree.seed_node.child_nodes())==1:
			self.tree.seed_node = self.tree.seed_node.child_nodes()[0]
			self.tree.seed_node.parent_node = None
			self.tree.seed_node.edge_length = 0.002

	def collapse(self):
		"""Collapse edges without mutations to polytomies"""
		for edge in self.tree.postorder_edge_iter():
			if edge.tail_node is not None:
				if edge.is_internal() and edge.head_node.seq==edge.tail_node.seq:
					edge.collapse()

	def reduce(self, max_length =0.01):
		"""
		Remove outlier tips
		Remove internal nodes left as orphan tips
		"""
		for node in self.tree.postorder_node_iter():
			if node.edge_length > max_length and node.is_leaf():
				parent = node.parent_node
				parent.remove_child(node)
		for node in self.tree.postorder_node_iter():
			if node.is_leaf() and not hasattr(node, 'strain'):
				parent = node.parent_node
				parent.remove_child(node)

	def ladderize(self):
		"""Sorts child nodes in terms of the length of subtending branches each child node has"""
		for node in self.tree.postorder_node_iter():
			if node.is_leaf():
				node.tree_length = node.edge_length
			else:
				node.tree_length = node.edge_length
				for child in node.child_nodes():
					node.tree_length += child.tree_length
				node._child_nodes.sort(key=lambda n:n.tree_length, reverse=True)

	def translate_all(self):
		for node in self.tree.postorder_node_iter():
			node.aa_seq = translate(node.seq[self.cds[0]:self.cds[1]])


	def get_yvalue(self, node):
		"""Return y location based on recursive mean of daughter locations"""
		if hasattr(node, 'yvalue'):
			return node.yvalue
		if node.child_nodes():
			return np.mean([n.yvalue for n in node.child_nodes()])

	def add_node_attributes(self):
		"""Add clade, xvalue, yvalue, mutation and trunk attributes to all nodes in tree"""
		clade = 0
		yvalue = 0
		for node in self.tree.postorder_node_iter():
			node.clade = clade
			clade += 1
			if node.is_leaf():
				node.yvalue = yvalue
				yvalue += 1
		for node in self.tree.postorder_node_iter():
			node.yvalue = self.get_yvalue(node)
			node.xvalue = node.distance_from_root()

		for v in self.viruses:
			if v.strain in self.node_lookup:
				node = self.node_lookup[v.strain]
				for attr in ['strain', 'date', 'accession', 'num_date', 'db', 'region', 'country']:
					node.__setattr__(attr, v.__getattribute__(attr))

	def define_trunk(self, dt = 1):
		"""Trace current lineages backward to define trunk"""

		# Find most recent tip
		most_recent_date = -1e10
		for node in self.tree.leaf_iter():
			if node.num_date>most_recent_date:
				most_recent_date=node.num_date
		for node in self.tree.postorder_node_iter():
			node.trunk_count=0		

		# Mark ancestry of recent tips
		number_recent = 0
		for node in self.tree.leaf_iter():
			if most_recent_date -  node.num_date<dt:
				number_recent += 1
				parent = node.parent_node
				while (parent != None):
					parent.trunk_count += 1
					parent = parent.parent_node

		# Mark trunk nodes
		for node in self.tree.postorder_node_iter():
			if node.trunk_count == number_recent:
				node.trunk = True;
			else:
				node.trunk = False
