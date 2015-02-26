import dendropy
import numpy as np
from io_util import *

def color_BioTree_by_attribute(T,attribute, vmin=None, vmax = None, missing_val='min', transform = lambda x:x, cmap=None):
	'''
	simple function that assigns a color to each node in a biopython tree
	the color can be determined by any attribute of the nodes. missing attributes will be
	determined from the children, all children are assumed to have the attribute
	in addition, the attribute can be transformed for example by taking the log
	parameters:
	T				-- BioPython tree
	attribute		-- name of the attribute that is to be used to color the tree.
	vmin			-- lower offset that is subtracted
	vmax			-- values are scaled as (val-vmin)/(vmax-vmin)
	missing val		-- if the attribute does not exist is a particular node,
					   the min, max, or mean of the children is used
	transform		-- function mapping float to float, e.g. log
	cmap			-- colormap to be used
	'''
	import numpy as np
	# make a list of tranformed data
	vals = [transform(t.__getattribute__(attribute)) for t in
			T.get_terminals()+T.get_nonterminals() if attribute in t.__dict__]
	if vmin is None:  # if vmin or vmax is not provided, use min or max of data
		vmin = min(vals)
		print "Set vmin to",vmin
	if vmax is None:
		vmax = max(vals)
		print "Set vmax to",vmax
	if cmap is None:
		from matplotlib.cm import jet
		cmap=jet

	# assign function used to determine missing values from children
	if missing_val=='min':
		missing_val_func = min
	elif missing_val=='mean':
		missing_val_func = mean
	elif missing_val=='max':
		missing_val_func = max
	else:
		missing_val_func = min

	# loop over all nodes, catch missing values and assign
	for node in T.get_nonterminals(order='postorder'):
		if attribute not in node.__dict__:
			node.__setattr__(attribute, missing_val_func([c.__getattribute__(attribute) for c in node.clades]))
			print "node", node,"has no",attribute,"Setting to min:", node.__getattribute__(attribute)

	# map value to color for each node
	for node in T.get_terminals()+T.get_nonterminals():
		node.color = map(int, np.array(cmap((transform(node.__getattribute__(attribute))-vmin)/(vmax-vmin))[:-1])*255)

def to_Biopython(tree):
	from Bio import Phylo
	from StringIO import StringIO
	from itertools import izip
	bT	= Phylo.read(StringIO(tree.as_newick_string()), 'newick')

	for new_leaf, old_leaf in izip(bT.get_terminals(), tree.leaf_nodes()):
		for attr,val in old_leaf.__dict__.iteritems():
			try:
				new_leaf.__setattr__(attr, float(val))
			except:
				new_leaf.__setattr__(attr, val)

	for new_leaf, old_leaf in izip(bT.get_nonterminals(order='postorder'), tree.postorder_internal_node_iter()):
		for attr,val in old_leaf.__dict__.iteritems():
			try:
				new_leaf.__setattr__(attr, float(val))
			except:
				new_leaf.__setattr__(attr, val)
	return bT

def tip_descendants(node):
	"""Take node, ie. dict, and return a flattened list of all tips descending from this node"""
	if 'children' in node:
		for child in node['children']:
			for desc in tip_descendants(child):
				yield desc
	else:
		yield node

def all_descendants(node):
	"""Take node, ie. dict, and return a flattened list of all nodes descending from this node"""
	yield node
	if 'children' in node:
		for child in node['children']:
			for desc in all_descendants(child):
				yield desc

def get_dates(node):
	"""Return ordered list of dates of descendants of a node"""
	return sorted([n['date'] for n in tip_descendants(node)])

def dendropy_to_json(node):
	json = {}
	if hasattr(node, 'clade'):
		json['clade'] = node.clade
	if hasattr(node, 'taxon'):
		if node.taxon != None:
			json['strain'] = str(node.taxon).replace("'", '')
	if hasattr(node, 'xvalue'):
		json['xvalue'] = round(node.xvalue, 5)
	if hasattr(node, 'yvalue'):
		json['yvalue'] = round(node.yvalue, 5)
	if hasattr(node, 'ep'):
		json['ep'] = node.ep
	if hasattr(node, 'ne'):
		json['ne'] = node.ne
	if hasattr(node, 'rb'):
		json['rb'] = node.rb
	if hasattr(node, 'date'):
		json['date'] = node.date
	if hasattr(node, 'num_date'):
		json['num_date'] = node.num_date
	if hasattr(node, 'country'):
		json['country'] = node.country
	if hasattr(node, 'region'):
		json['region'] = node.region
	if hasattr(node, 'seq'):
		json['seq'] = node.seq
	if hasattr(node, 'aa_seq'):
		json['aa_seq'] = node.aa_seq
	if hasattr(node, 'gt'):
		json['gt'] = node.gt
	if hasattr(node, 'gt_pos'):
		json['gt_pos'] = list(node.gt_pos)
	if hasattr(node, 'tip_index'):
		json['tip_index'] = node.tip_index
	if hasattr(node, 'LBI'):
		json['LBI'] = round(node.LBI, 5)
	if hasattr(node, 'tol'):
		json['tol'] = round(node.tol, 5)		
	if hasattr(node, 'fitness'):
		json['fitness'] = round(node.fitness, 5)		
	try:
		if hasattr(node, 'freq') and node.freq is not None:
			json['freq'] = {reg: [round(x, 3) for x in freq]  if freq is not None else "undefined" for reg, freq in node.freq.iteritems()}		
		if hasattr(node, 'logit_freq') and node.logit_freq is not None:
			json['logit_freq'] = {reg: [round(x,3) for x in freq]  if freq is not None else "undefined" for reg, freq in node.logit_freq.iteritems()}
		if hasattr(node, 'pivots'):
			json['pivots'] = [round(x,3) for x in node.pivots]
		if hasattr(node, 'virus_count'):
			json['virus_count'] = {reg: [round(x,3) for x in vc[0]]  if vc is not None else "undefined" for reg, vc in node.virus_count.iteritems()}
	except:
		import pdb; pdb.set_trace()
	if node.child_nodes():
		json["children"] = []
		for ch in node.child_nodes():
			json["children"].append(dendropy_to_json(ch))
	return json

def BioPhylo_to_json(node):
	json = {}
	if hasattr(node, 'clade'):
		json['clade'] = node.clade
	if node.name:
		json['strain'] = str(node.name).replace("'", '')
	if hasattr(node, 'branch_length'):
		json['branch_length'] = round(node.branch_length, 5)
	if hasattr(node, 'xvalue'):
		json['xvalue'] = round(node.xvalue, 5)
	if hasattr(node, 'yvalue'):
		json['yvalue'] = round(node.yvalue, 5)
	if hasattr(node, 'ep'):
		json['ep'] = node.ep
	if hasattr(node, 'ne'):
		json['ne'] = node.ne
	if hasattr(node, 'rb'):
		json['rb'] = node.rb
	if hasattr(node, 'date'):
		json['date'] = node.date
	if hasattr(node, 'seq'):
		json['seq'] = str(node.seq)
	if hasattr(node, 'LBI'):
		json['LBI'] = round(node.LBI,5)
	if len(node.clades):
		json["children"] = []
		for ch in node.clades:
			json["children"].append(BioPhylo_to_json(ch))
	return json


def json_to_dendropy(json):
	'''
	read a json dictionary and make a dendropy tree from it.
	'''
	tree = dendropy.Tree()
	tree.get_from_string(';', 'newick')
	root = tree.seed_node
	json_to_dendropy_sub(json, root)
	root.edge_length=0.0
	return tree

def json_to_dendropy_sub(json, node):
	'''
	recursively calls itself for all children of node and
	builds up the tree. entries in json are added as node attributes
	'''
	if 'xvalue' in json:
		node.xvalue = float(json['xvalue'])
	for attr,val in json.iteritems():
		if attr=='children':
			for sub_json in val:
				child_node = dendropy.Node()
				json_to_dendropy_sub(sub_json, child_node)
				if hasattr(child_node, 'xvalue'):
					node.add_child(child_node, edge_length = child_node.xvalue - node.xvalue)
				elif hasattr(child_node, 'branch_length'):
					node.add_child(child_node, edge_length = child_node.branch_length)
				else:
					node.add_child(child_node, edge_length = 1.0)
		else:
			try:
				node.__setattr__(attr, float(val))
			except:
				node.__setattr__(attr, val)
	if len(node.child_nodes())==0:
		node.taxon = json['strain']

def main():

	tree = read_json('tree.json')

#	print "Whole tree"
#	for tip in descendants(tree):
#		print tip['date']

#	node = tree['children'][0]

#	dates = get_dates(tree)
#	print dates

	for node in all_descendants(tree):
		dates = get_dates(node)
		print str(node['clade']) + ": " + str(len(dates))

if __name__ == "__main__":
	main()
