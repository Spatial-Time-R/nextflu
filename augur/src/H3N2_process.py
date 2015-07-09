import time, argparse,re,os
from virus_filter import flu_filter, fix_name
from virus_clean import virus_clean
from tree_refine import tree_refine
from tree_titer import HI_tree
from fitness_model import fitness_model
from process import process, virus_config
from Bio import SeqIO
from Bio.Seq import Seq
from Bio.Align import MultipleSeqAlignment
import numpy as np
from itertools import izip


# numbering starting at HA1 start, adding sp to obtain numbering from methionine
sp = 16
epitope_mask = np.fromstring(sp*"0"+"000000000000000000000000000000000000000000011111011011001010011000100000001001011110011100110101000001100000100000001000110101011111101011010111110001010011111000101011011111111010010001111101110111001010001110011111111000000111110000000101010101110000000000011100100000001011011100000000000001001011000110111111000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000", dtype='S1')
receptor_binding_sites = map(lambda x:x+sp-1, [145, 155, 156, 158, 159, 189, 193])


virus_config.update({
	# data source and sequence parsing/cleaning/processing
	'virus':'H3N2',
	'alignment_file':'data/H3N2_gisaid_epiflu_sequence.fasta.gz',
	'outgroup':'A/Beijing/32/1992',
	'force_include':'source-data/H3N2_HI_strains.txt',
	'force_include_all':True,
	'max_global':True,   # sample as evenly as possible from different geographic regions 
	'cds':[0,None], # define the HA1 start i n 0 numbering
	'n_iqd':6,
	'min_mutation_frequency':0.05,
	# define relevant clades in canonical HA1 numbering (+1)
	# numbering starting at HA1 start, adding sp to obtain numbering from methionine
	'clade_designations': { "3c3.a":[('HA1', 128,'A'), ('HA1',142,'G'), ('HA1',159,'S')],
						   "3c3":   [('HA1', 128,'A'), ('HA1',142,'G'), ('HA1',159,'F')],
						   "3c2.a": [('HA1', 144,'S'), ('HA1',159,'Y'), ('HA1',225,'D'), ('HA1', 311,'H'), ('HA2', 160,'N')],
						   "3c2":   [('HA1', 144,'N'), ('HA1',159,'F'), ('HA1',225,'N'), ('HA2', 160,'N'), ('HA1', 142, 'R')],
						   "3c3.b": [('HA1',  83,'R'), ('HA1',261,'Q'), ('HA1',62,'K'),  ('HA1', 122,'D')]
							},
	'HI_fname':'source-data/H3N2_HI_titers.txt',
	'auspice_prefix':'H3N2_',
	'html_vars': {'coloring': 'ep, ne, rb, lbi, dfreq, region, date, cHI, HI_dist',
				   'gtplaceholder': 'HA1 positions...',
					'freqdefault': '3c2.a, 3c3.a'},
	'js_vars': {'LBItau': 0.0005, 'LBItime_window': 0.5, 'dfreq_dn':2},
	})


class H3N2_filter(flu_filter):
	def __init__(self,min_length = 987, **kwargs):
		'''
		parameters
		min_length  -- minimal length for a sequence to be acceptable
		'''
		flu_filter.__init__(self, **kwargs)
		self.min_length = min_length
		self.vaccine_strains =[
				{ 
					"strain": "A/Wisconsin/67/2005",
					"db": "IRD",
					"accession": "CY163984",
					"date": "2005-08-31",
					"seq": "ATGAAGACTATCATTGCTTTGAGCTACATTCTATGTCTGGTTTTCGCTCAAAAACTTCCCGGAAATGACAACAGCACGGCAACGCTGTGCCTTGGGCACCATGCAGTACCAAACGGAACGATAGTGAAAACAATCACGAATGACCAAATTGAAGTTACTAATGCTACTGAGCTGGTTCAGAGTTCCTCAACAGGTGGAATATGCGACAGTCCTCATCAGATCCTTGATGGAGAAAACTGCACACTAATAGATGCTCTATTGGGAGACCCTCAGTGTGATGGCTTCCAAAATAAGAAATGGGACCTTTTTGTTGAACGCAGCAAAGCCTACAGCAACTGTTACCCTTATGATGTGCCGGATTATGCCTCCCTTAGGTCACTAGTTGCCTCATCCGGCACACTGGAGTTTAACGATGAAAGCTTCAATTGGACTGGAGTCACTCAAAATGGAACAAGCTCTTCTTGCAAAAGGAGATCTAATAACAGTTTCTTTAGTAGATTGAATTGGTTGACCCACTTAAAATTCAAATACCCAGCATTGAACGTGACTATGCCAAACAATGAAAAATTTGACAAATTGTACATTTGGGGGGTTCACCACCCGGTTACGGACAATGACCAAATCTTCCTGTATGCTCAAGCATCAGGAAGAATCACAGTCTCTACCAAAAGAAGCCAACAAACTGTAATCCCGAATATCGGATCTAGACCCAGAATAAGGAATATCCCCAGCAGAATAAGCATCTATTGGACAATAGTAAAACCGGGAGACATACTTTTGATTAACAGCACAGGGAATCTAATTGCTCCTAGGGGTTACTTCAAAATACGAAGTGGGAAAAGCTCAATAATGAGATCAGATGCACCCATTGGCAAATGCAATTCTGAATGCATCACTCCAAATGGAAGCATTCCCAATGACAAACCATTTCAAAATGTAAACAGGATCACATATGGGGCCTGTCCCAGATATGTTAAGCAAAACACTCTGAAATTGGCAACAGGGATGCGAAATGTACCAGAGAAACAAACTAGAGGCATATTTGGCGCAATCGCGGGTTTCATAGAAAATGGTTGGGAGGGAATGGTGGATGGTTGGTACGGTTTCAGGCATCAAAATTCTGAGGGAATAGGACAAGCAGCAGATCTCAAAAGCACTCAAGCAGCAATCAATCAAATCAATGGGAAGCTGAATAGGTTGATCGGGAAAACCAACGAGAAATTCCATCAGATTGAAAAAGAATTCTCAGAAGTAGAAGGGAGAATTCAGGACCTCGAGAAATATGTTGAGGACACTAAAATAGATCTCTGGTCATACAACGCGGAGCTTCTTGTTGCCCTGGAGAACCAACATACAATTGATCTAACTGACTCAGAAATGAACAAACTGTTTGAAAGAACAAAGAAGCAACTGAGGGAAAATGCTGAGGATATGGGCAATGGTTGTTTCAAAATATACCACAAATGTGACAATGCCTGCATAGGATCAATCAGAAATGGAACTTATGACCATGATGTATACAGAGATGAAGCATTAAACAACCGGTTCCAGATCAAAGGCGTTGAGCTGAAGTCAGGATACAAAGATTGGATCCTATGGATTTCCTTTGCCATATCATGTTTTTTGCTTTGTGTTGCTTTGTTGGGGTTCATCATGTGGGCCTGCCAAAAAGGCAACATTAGGTGCAACATTTGCATTTGA"
				},	{
					"strain": "A/Brisbane/10/2007",
					"db": "IRD",
					"accession": "CY113005",
					"date": "2007-02-06",
					"seq": "ATGAAGACTATCATTGCTTTGAGCTACATTCTATGTCTGGTTTTCACTCAAAAACTTCCCGGAAATGACAACAGCACGGCAACGCTGTGCCTTGGGCACCATGCAGTACCAAACGGAACGATAGTGAAAACAATCACGAATGACCAAATTGAAGTTACTAATGCTACTGAGCTGGTTCAGAGTTCCTCAACAGGTGAAATATGCGACAGTCCTCATCAGATCCTTGATGGAGAAAACTGCACACTAATAGATGCTCTATTGGGAGACCCTCAGTGTGATGGCTTCCAAAATAAGAAATGGGACCTTTTTGTTGAACGCAGCAAAGCCTACAGCAACTGTTACCCTTATGATGTGCCGGATTATGCCTCCCTTAGGTCACTAGTTGCCTCATCCGGCACACTGGAGTTTAACAATGAAAGCTTCAATTGGACTGGAGTCACTCAAAACGGAACAAGCTCTGCTTGCATAAGGAGATCTAATAACAGTTTCTTTAGTAGATTGAATTGGTTGACCCACTTAAAATTCAAATACCCAGCATTGAACGTGACTATGCCAAACAATGAAAAATTTGACAAATTGTACATTTGGGGGGTTCACCACCCGGGTACGGACAATGACCAAATCTTCCCGTATGCTCAAGCATCAGGAAGAATCACAGTCTCTACCAAAAGAAGCCAACAAACTGTAATCCCGAATATCGGATCTAGACCCAGAGTAAGGAATATCCCCAGCAGAATAAGCATCTATTGGACAATAGTAAAACCGGGAGACATACTTTTGATTAACAGCACAGGGAATCTAATTGCTCCTAGGGGTTACTTCAAAATACGAAGTGGGAAAAGCTCAATAATGAGATCAGATGCACCCATTGGCAAATGCAATTCTGAATGCATCACTCCAAACGGAAGCATTCCCAATGACAAACCATTCCAAAATGTAAACAGGATCACATACGGGGCCTGTCCCAGATATGTTAAGCAAAACACTCTGAAATTGGCAACAGGGATGCGAAATGTACCAGAGAAACAAACTAGAGGCATATTTGGCGCAATCGCGGGTTTCATAGAAAATGGTTGGGAGGGAATGGTGGATGGTTGGTACGGTTTCAGGCATCAAAATTCTGAGGGAATAGGACAAGCAGCAGATCTCAAAAGCACTCAAGCAGCAATCGATCAAATCAATGGGAAGCTGAATAGGTTGATCGGGAAAACCAACGAGAAATTCCATCAGATTGAAAAAGAATTCTCAGAAGTCGAAGGGAGAATTCAGGACCTTGAGAAATATGTTGAGGACACCAAAATAGATCTCTGGTCATACAACGCGGAGCTTCTTGTTGCCCTGGAGAACCAACATACAATTGATCTAACTGACTCAGAAATGAACAAACTGTTTGAAAAAACAAAGAAGCAACTGAGGGAAAATGCTGAGGATATGGGCAATGGTTGTTTCAAAATATACCACAAATGTGACAATGCCTGCATAGGATCAATCAGAAATGGAACTTATGACCACAATGTATACAGAGATGAAGCATTAAACAACCGGTTCCAGATCAAGGGCGTTGAGCTGAAGTCAGGATACAAAGATTGGATCCTATGGATTTCCTTTGCCATATCATGTTTTTTGCTTTGTGTTGCTTTGTTGGGGTTCATCATGTGGGCCTGCCAAAAAGGCAACATTAGGTGCAACATTTGCATTTGA"
				},	{
					"strain": "A/Perth/16/2009",
					"db": "IRD",
					"accession": "GQ293081",
					"date": "2009-04-07",
					"seq": "ATGAAGACTATCATTGCTTTGAGCTACATTCTATGTCTGGTTTTCGCTCAAAAACTTCCTGGAAATGACAACAGCACGGCAACGCTGTGCCTTGGGCACCATGCAGTACCAAACGGAACGATAGTGAAAACAATCACGAATGACCAAATTGAAGTTACTAATGCTACTGAGCTGGTTCAGAGTTCCTCAACAGGTGAAATATGCGACAGTCCTCATCAGATCCTTGATGGAAAAAACTGCACACTAATAGATGCTCTATTGGGAGACCCTCAGTGTGATGGCTTCCAAAATAAGAAATGGGACCTTTTTGTTGAACGCAGCAAAGCCTACAGCAACTGTTACCCTTATGATGTGCCGGATTATGCCTCCCTTAGGTCACTAGTTGCCTCATCCGGCACACTGGAGTTTAACAATGAAAGCTTCAATTGGACTGGAGTCACTCAAAACGGAACAAGCTCTGCTTGCATAAGGAGATCTAAAAACAGTTTCTTTAGTAGATTGAATTGGTTGACCCACTTAAACTTCAAATACCCAGCATTGAACGTGACTATGCCAAACAATGAACAATTTGACAAATTGTACATTTGGGGGGTTCACCACCCGGGTACGGACAAAGACCAAATCTTCCTGTATGCTCAAGCATCAGGAAGAATCACAGTCTCTACCAAAAGAAGCCAACAAACCGTAAGCCCGAATATCGGATCTAGACCCAGAGTAAGGAATATCCCTAGCAGAATAAGCATCTATTGGACAATAGTAAAACCGGGAGACATACTTTTGATTAACAGCACAGGGAATCTAATTGCTCCTAGGGGTTACTTCAAAATACGAAGTGGGAAAAGCTCAATAATGAGATCAGATGCACCCATTGGCAAATGCAATTCTGAATGCATCACTCCAAATGGAAGCATTCCCAATGACAAACCATTCCAAAATGTAAACAGGATCACATACGGGGCCTGTCCCAGATATGTTAAGCAAAACACTCTGAAATTGGCAACAGGGATGCGAAATGTACCAGAGAAACAAACTAGAGGCATATTTGGCGCAATCGCGGGTTTCATAGAAAATGGTTGGGAGGGAATGGTGGATGGTTGGTACGGTTTCAGGCATCAAAATTCTGAGGGAAGAGGACAAGCAGCAGATCTCAAAAGCACTCAAGCAGCAATCGATCAAATCAATGGGAAGCTGAATAGATTGATCGGGAAAACCAACGAGAAATTCCATCAGATTGAAAAAGAATTCTCAGAAGTCGAAGGGAGAATTCAGGACCTTGAGAAATATGTTGAGGACACTAAAATAGATCTCTGGTCATACAACGCGGAGCTTCTTGTTGCCCTGGAGAACCAACATACAATTGATCTAACTGACTCAGAAATGAACAAACTGTTTGAAAAAACAAAGAAGCAACTGAGGGAAAATGCTGAGGATATGGGCAATGGTTGTTTCAAAATATACCACAAATGTGACAATGCCTGCATAGGATCAATCAGAAATGGAACTTATGACCACGATGTATACAGAGATGAAGCATTAAACAACCGGTTTCAGATCAAGGGAGTTGAGCTGAAGTCAGGGTACAAAGATTGGATCCTATGGATTTCCTTTGCCATATCATGTTTTTTGCTTTGTGTTGCTTTGTTGGGGTTCATCATGTGGGCCTGCCAAAAAGGCAACATTAGGTGCAACATTTGCATTTGA"
				},	{
					"strain": "A/Victoria/361/2011",
					"db": "IRD",
					"accession": "GQ293081",
					"date": "2011-10-24",
					"seq": "ATGAAGACTATCATTGCTTTGAGCCACATTCTATGTCTGGTTTTCGCTCAAAAACTTCCTGGAAATGACAACAGCACGGCAACGCTGTGCCTTGGGCACCATGCAGTACCAAACGGAACGATAGTGAAAACAATCACGAATGACCAAATTGAAGTTACTAATGCTACTGAGCTGGTTCAGAATTCCTCAATAGGTGAAATATGCGACAGTCCTCATCAGATCCTTGATGGAGAAAACTGCACACTAATAGATGCTCTATTGGGAGACCCTCAGTGTGATGGCTTCCAAAATAAGAAATGGGACCTTTTTGTTGAACGAAGCAAAGCCTACAGCAACTGTTACCCTTATGATGTGCCGGATTATGCCTCCCTTAGGTCACTAGTTGCCTCATCCGGCACACTGGAGTTTAACAATGAAAGCTTCAATTGGACTGGAGTCACTCAAAACGGAACAAGTTCTGCTTGCATAAGGAGATCTAATAATAGTTTCTTTAGTAGATTAAATTGGTTGACCCGCTTAAACTTCAAATACCCAGCATTGAACGTGACTATGCCAAACAATGAACAATTTGACAAATTGTACATTTGGGGGGTTCACCACCCGGTTACGGACAAGGAACAAATCTTCCTGTATGCTCAATCATCAGGAAGAATCACAGTATCTACCAAAAGAAGCCAACAAGCTGTAATCCCGAATATCGGATATAGACCCAGAATAAGGAATATCCCTAGCAGAATAAGCATCTATTGGACAATAGTAAAACCGGGAGACATACTTTTGATTAACAGCACAGGGAATCTAATTGCTCCTAGGGGTTACTTCAAAATACGAAGTGGGAAAAGCTCAATAATGAGATCAGATGCACCCATTGGCAAATGCAATTCTGAATGCATCACTCCAAATGGAAGCATTCCCAATGACAAACCATTCCAAAATGTAAACAGGATCACATACGGGGCCTGTCCCAGATATGTTAAGCAAAGCACTCTGAAATTGGCAACAGGAATGCGAAATGTACCAGAGAAACAAACTAGAGGCATATTTGGCGCAATAGCGGGTTTCATAGAAAATGGTTGGGAGGGAATGGTGGATGGTTGGTACGGTTTCAGGCATCAAAATTCTGAGGGAAGAGGACAAGCAGCAGATCTCAAAAGCACTCAAGCAGCAATCGATCAAATCAATGGGAAGCTGAATCGATTGATCGGGAAAACCAACGAGAAATTCCATCAGATTGAAAAAGAATTCTCAGAAGTCGAAGGGAGAATTCAGGACCTTGAGAAATATGTTGAGGACACTAAAATAGATCTCTGGTCATACAACGCGGAGCTTCTTGTTGCCCTGGAGAACCAACATACAATTGATCTAACTGACTCAGAAATGAACAAACTGTTTGAAAAAACAAAGAAGCAACTAAGGGAAAATGCTGAGGATATGGGCAATGGTTGTTTCAAAATATACCACAAATGTGACAATGCCTGCATAGGATCAATCAGAAATGGAACTTATGACCACGATGTATACAGAGATGAAGCATTAAACAACCGGTTCCAGATCAAGGGAGTTGAGCTGAAGTCAGGGTACAAAGATTGGATCCTATGGATTTCCTTTGCCATATCATGTTTTTTGCTTTGTGTTGCTTTGTTGGGGTTCATCATGTGGGCCTGCCAAAAGGGCAACATTAGGTGCAACATTTGCATTTGA"
				},	{
					"strain": "A/Texas/50/2012",
					"db": "GISAID",
					"isolate_id": "EPI_ISL_129858",
					"date": "2012-04-15",
					"seq": "ATGAAGACTATCATTGCTTTGAGCTACATTCTATGTCTGGTTTTCGCTCAAAAACTTCCTGGAAATGACAATAGCACGGCAACGCTGTGCCTTGGGCACCATGCAGTACCAAACGGAACGATAGTGAAAACAATCACGAATGACCGAATTGAAGTTACTAATGCTACTGAACTGGTTCAGAATTCCTCAATAGGTGAAATATGCGACAGTCCTCATCAGATCCTTGATGGAGAAAACTGCACACTAATAGATGCTCTATTGGGAGACCCTCAGTGTGATGGCTTCCAAAATAAGAAATGGGACCTTTTTGTTGAACGAAGCAAAGCCTACAGCAACTGTTACCCTTATGATGTGCCGGATTATGCCTCCCTTAGGTCACTAGTTGCCTCATCCGGCACACTGGAGTTTAACAATGAAAGCTTCAATTGGAATGGAGTCACTCAAAACGGAACAAGTTCTGCTTGCATAAGGAGATCTAATAATAGTTTCTTTAGTAGATTAAATTGGTTGACCCACTTAAACTTCAAATACCCAGCATTGAACGTGACTATGCCAAACAATGAACAATTTGACAAATTGTACATTTGGGGGGTTCACCACCCGGGTACGGACAAGGACCAAATCTTCCTGTATGCTCAACCATCAGGAAGAATCACAGTATCTACCAAAAGAAGCCAACAAGCTGTAATCCCGAATATCGGATCTAGACCCAGAATAAGGAATATCCCTAGCAGAATAAGCATCTATTGGACAATAGTAAAACCGGGAGACATACTTTTGATTAACAGCACAGGGAATCTAATTGCTCCTAGGGGTTACTTCAAAATACGAAGTGGGAAAAGCTCAATAATGAGATCAGATGCACCCATTGGCAAATGCAAGTCTGAATGCATCACTCCAAATGGAAGCATTCCCAATGACAAACCATTCCAAAATGTAAACAGGATCACATACGGGGCCTGTCCCAGATATGTTAAGCAAAGCACTCTGAAATTGGCAACAGGAATGCGGAATGTACCAGAGAAACAAACTAGAGGCATATTTGGCGCAATAGCGGGTTTCATAGAAAATGGTTGGGAGGGAATGGTGGATGGTTGGTACGGTTTCAGGCATCAAAATTCTGAGGGAAGAGGACAAGCAGCAGATCTCAAAAGCACTCAAGCAGCAATCGATCAAATCAATGGGAAGCTGAATCGATTGATCGGGAAAACCAACGAGAAATTCCATCAGATTGAAAAAGAATTCTCAGAAGTAGAAGGGAGAATTCAGGACCTTGAGAAATATGTTGAGGACACTAAAATAGATCTCTGGTCATACAACGCGGAGCTTCTTGTTGCCCTGGAGAACCAACATACAATTGATCTAACTGACTCAGAAATGAACAAACTGTTTGAAAAAACAAAGAAGCAACTGAGGGAAAATGCTGAGGATATGGGCAATGGTTGTTTCAAAATATACCACAAATGTGACAATGCCTGCATAGGATCAATCAGAAATGGAACTTATGACCACGATGTATACAGAGATGAAGCATTAAACAACCGGTTCCAGATCAAGGGAGTTGAGCTGAAGTCAGGGTACAAAGATTGGATCCTATGGATTTCCTTTGCCATATCATGTTTTTTGCTTTGTGTTGCTTTGTTGGGGTTCATCATGTGGGCCTGCCAAAAGGGCAACATTAGGTGCAACATTTGCATTTGA",
				},	{
					"strain": "A/Switzerland/9715293/2013",
					"db": "GISAID",
					"isolate_id": "EPI_ISL_162149",
					"date": "2013-12-06",
					"seq": "ATGAAGACTATCATTGCTTTGAGCTACATTCTATGTCTGGTTTTCGCTCAAAAACTTCCTGGAAATGACAATAGCACGGCAACGCTGTGCCTTGGGCACCATGCAGTACCAAACGGAACGATAGTGAAAACAATCACGAATGACCGAATTGAAGTTACTAATGCTACTGAGCTGGTTCAGAATTCCTCAATAGGTGAAATATGCGACAGTCCTCATCAGATCCTTGATGGAGAAAACTGCACACTAATAGATGCTCTATTGGGAGACCCTCAGTGTGATGGCTTTCAAAATAAGAAATGGGACCTTTTTGTTGAACGAAGCAAAGCCTACAGCAACTGTTACCCTTATGATGTGCCGGATTATGCCTCCCTTAGGTCACTAGTTGCCTCATCCGGCACACTGGAGTTTAACAATGAAAGCTTCAATTGGGCTGGAGTCACTCAAAACGGAACAAGTTCTTCTTGCATAAGGGGATCTAATAGTAGTTTCTTTAGTAGATTAAATTGGTTGACCCACTTAAACTCCAAATACCCAGCATTAAACGTGACTATGCCAAACAATGAACAATTTGACAAATTGTACATTTGGGGGGTTCACCACCCGGGTACGGACAAGGACCAAATCTTCCTGTATGCACAATCATCAGGAAGAATCACAGTATCTACCAAAAGAAGCCAACAAGCTGTAATCCCGAATATCGGATCTAGACCCAGAATAAGGGATATCCCTAGCAGAATAAGCATCTATTGGACAATAGTAAAACCGGGAGACATACTTTTGATTAACAGCACAGGGAATCTAATTGCTCCTAGGGGTTACTTCAAAATACGAAGTGGGAAAAGCTCAATAATGAGATCAGATGCACCCATTGGCAAATGCAAGTCTGAATGCATCACTCCAAATGGAAGCATTCCCAATGACAAACCATTCCAAAATGTAAACAGGATCACATACGGGGCCTGTCCCAGATATGTTAAGCAAAGCACTCTGAAATTGGCAACAGGAATGCGAAATGTACCAGAGAGACAAACTAGAGGCATATTTGGCGCAATAGCGGGTTTCATAGAAAATGGTTGGGAGGGAATGGTGGATGGTTGGTACGGCTTCAGGCATCAAAATTCTGAGGGAAGAGGACAAGCAGCAGATCTCAAAAGCACTCAAGCAGCAATCGATCAAATCAATGGGAAGCTGAATCGATTGATCGGGAAAACCAACGAGAAATTCCATCAGATTGAAAAAGAATTCTCAGAAGTAGAAGGGAGAATTCAGGACCTTGAGAAATATGTTGAGGACACAAAAATAGATCTCTGGTCATACAACGCGGAGCTTCTTGTTGCCCTGGAGAACCAACATACAATTGATCTAACTGACTCAGAAATGAACAAACTGTTTGAAAAAACAAAGAAGCAACTGAGGGAAAATGCTGAGGATATGGGCAATGGTTGTTTCAAAATATACCACAAATGTGACAATGCCTGCATAGGATCAATCAGAAATGGAACTTATGACCACGATGTATACAGGGATGAAGCATTAAACAACCGGTTCCAGATCAAGGGAGTTGAGCTGAAGTCAGGGTACAAAGATTGGATCCTATGGATTTCCTTTGCCATATCATGTTTTTTGCTTTGTGTTGCTTTGTTGGGGTTCATCATGTGGGCCTGCCAAAAGGGCAACATTAGGTGCAACATTTGCATTTGA",
				}
			]
		tmp_outgroup = SeqIO.read('source-data/H3N2_outgroup.gb', 'genbank')
		genome_annotation = tmp_outgroup.features
		self.cds = {x.qualifiers['gene'][0]:x for x in genome_annotation
				if 'gene' in x.qualifiers and x.type=='CDS' and 
				x.qualifiers['gene'][0] in ['SigPep', 'HA1', 'HA2']}
		self.outgroup = {
			'strain': 'A/Beijing/32/1992',
			'db': 'IRD',
			'accession': 'U26830',
			'date': '1992-01-01',
			'country': 'China',
			'region': 'China',
			'seq': str(tmp_outgroup.seq).upper()
		}

class H3N2_clean(virus_clean):
	def __init__(self,**kwargs):
		virus_clean.__init__(self, **kwargs)

	def clean_outbreaks(self):
		"""Remove duplicate strains, where the geographic location, date of sampling and sequence are identical"""
		virus_hashes = set()
		new_viruses = []
		for v in self.viruses:
			geo = re.search(r'A/([^/]+)/', v.strain).group(1)
			if geo:
				vhash = (geo, v.date, str(v.seq))
				if vhash not in virus_hashes:
					new_viruses.append(v)
					virus_hashes.add(vhash)

		self.viruses = MultipleSeqAlignment(new_viruses)

	def clean_reassortants(self):
		from seq_util import hamming_distance as distance
		"""Remove viruses from the outbreak of triple reassortant pH1N1"""
		remove_viruses = []
		
		reassortant_seqs = [
			"ATGAAGACTATCATTGCTTTTAGCTGCATTTTATGTCTGATTTTCGCTCAAAAACTTCCCGGAAGTGACAACAGCATGGCAACGCTGTGCCTGGGACACCATGCAGTGCCAAACGGAACATTAGTGAAAACAATCACGGATGACCAAATTGAAGTGACTAATGCTACTGAGCTGGTCCAGAGTTCCTCAACAGGTGGAATATGCAACAGTCCTCACCAAATCCTTGATGGGAAAAATTGCACACTGATAGATGCTCTATTGGGGGACCCTCATTGTGATGACTTCCAAAACAAGGAATGGGACCTTTTTGTTGAACGAAGCACAGCCTACAGCAACTGTTACCCTTATTACGTGCCGGATTATGCCACCCTTAGATCATTAGTTGCCTCATCCGGCAACCTGGAATTTACCCAAGAAAGCTTCAATTGGACTGGAGTTGCTCAAGGCGGATCAAGCTATGCCTGCAGAAGGGGATCTGTTAACAGTTTCTTTAGTAGATTGAATTGGTTGTATAACTTGAATTACAAGTATCCAGAGCAGAACGTAACTATGCCAAACAATGACAAATTTGACAAATTGTACATTTGGGGGGTTCACCACCCGGGTACGGACAAGGACCAAACCAACCTATATGTCCAAGCATCAGGGAGAGTTATAGTCTCTACCAAAAGAAGCCAACAAACTGTAATCCCGAATATCGGGTCTAGACCCTGGGTAAGGGGTGTCTCCAGCATAATAAGCATCTATTGGACGATAGTAAAACCGGGAGACATACTTTTGATTAACAGCACAGGGAATCTAATTGCCCCTCGGGGTTACTTCAAAATACAAAGTGGGAAAAGCTCAATAATGAGATCAGATGCACACATTGATGAATGCAATTCTGAATGCATTACTCCAAATGGAAGCATTCCCAATGACAAACCTTTTCAAAATGTAAACAAGATCACATATGGAGCCTGTCCCAGATATGTTAAGCAAAACACCCTGAAATTGGCAACAGGAATGCGGAATGTACCAGAGAAACAAACTAGAGGCATATTCGGCGCAATTGCAGGTTTCATAGAAAATGGTTGGGAGGGAATGGTAGACGGTTGGTACGGTTTCAGGCATCAGAATTCTGAAGGCACAGGACAAGCAGCAGATCTTAAAAGCACTCAAGCAGCAATCAACCAAATCACCGGGAAACTAAATAGAGTAATCAAGAAAACAAACGAGAAATTCCATCAAATCGAAAAAGAATTCTCAGAAGTAGAAGGAAGAATTCAGGACCTAGAGAAATACGTTGAAGACACTAAAATAGATCTCTGGTCTTACAACGCTGAGATTCTTGTTGCCCTGGAGAACCAACATACAATTGATTTAACCGACTCAGAGATGAGCAAACTGTTCGAAAGAACAAGAAGGCAACTGCGGGAAAATGCTGAGGACATGGGCAATGGTTGCTTCAAAATATACCACAAATGTGACAATGCCTGCATAGGATCAATCAGAAATGGAACTTATGACCATGATATATACAGAAACGAGGCATTAAACAATCGGTTCCAGATCAAAGGTGTTCAGCTAAAGTCAGGATACAAAGATTGGATCCTATGGATTTCCTTTGCCATATCATGCTTTTTGCTTTGTGTTGTTCTGCTGGGGTTCATTATGTGGGCCTGCCAAAAAGGCAACATTAGGTGCAACATTTGCATTTGA", 
			"ATGAAGACTATCATTGCTTTTAGCTGCATCTTATGTCAGATCTCCGCTCAAAAACTCCCCGGAAGTGACAACAGCATGGCAACGCTGTGCCTGGGGCATCACGCAGTACCAAACGGAACGTTAGTGAAAACAATAACAGATGACCAAATTGAAGTGACTAATGCTACTGAGCTGGTCCAGAGTACCTCAAAAGGTGAAATATGCAGTAGTCCTCACCAAATCCTTGATGGAAAAAATTGTACACTGATAGATGCTCTATTGGGAGACCCTCATTGTGATGACTTCCAAAACAAGAAATGGGACCTTTTTGTTGAACGAAGCACAGCTTACAGCAACTGTTACCCTTATTATGTGCCGGATTATGCCTCCCTTAGGTCACTAGTTGCCTCATCCGGCACCCTGGAATTTACTCAAGAAAGCTTCAATTGGACTGGGGTTGCTCAAGACGGAGCAAGCTATTCTTGCAGAAGGGAATCTGAAAACAGTTTCTTTAGTAGATTGAATTGGTTATATAGTTTGAATTACAAATATCCAGCGCTGAACGTAACTATGCCAAACAATGACAAATTTGACAAATTGTACATTTGGGGGGTACACCACCCGGGTACGGACAAGGACCAAACCAGTCTATATATTCAAGCATCAGGGAGAGTTACAGTCTCCACCAAATGGAGCCAACAAACTGTAATCCCGAATATCGGGTCTAGACCCTGGATAAGGGGTGTCTCCAGCATAATAAGCATCTATTGGACAATAGTAAAACCGGGAGACATACTTTTGATTAACAGCACAGGGAATCTAATTGCCCCTCGGGGTTACTTCAAAATACAAAGTGGGAAAAGCTCAATAATGAGGTCAGATGCACACATTGGCAACTGCAACTCTGAATGCATTACCCCAAATGGAAGCATTCCCAACGACAAACCTTTTCAAAATGTAAACAGAATAACATATGGGGCCTGTCCCAGATATGTTAAGCAAAACACTCTGAAATTAGCAACAGGAATGCGGAATGTACCAGAGAAACAAACTAGAGGCATATTCGGCGCAATCGCAGGTTTCATAGAAAATGGTTGGGAAGGGATGGTGGACGGTTGGTATGGTTTCAGGCATCAAAACTCTGAAGGCACAGGGCAAGCAGCAGATCTTAAAAGCACTCAAGCGGCAATCAACCAAATCACCGGGAAACTAAATAGAGTAATCAAGAAGACGAATGAAAAATTCCATCAGATCGAAAAAGAATTCTCAGAAGTAGAAGGGAGAATTCAGGACCTAGAGAGATACGTTGAAGACACTAAAATAGACCTCTGGTCTTACAACGCGGAGCTTCTTGTTGCCCTGGAGAACCAACATACAATTGATTTAACTGACTCAGAAATGAACAAACTGTTCGAAAGGACAAGGAAGCAACTGCGGGAAAATGCTGAGGACATGGGCAATGGATGCTTTAAAATATATCACAAATGTGACAATGCCTGCATAGGATCAATCAGAAATGGAACTTATGACCATGATGTATACAGAGACGAAGCAGTAAACAATCGGTTCCAGATCAAAGGTGTTCAGCTGAAGTTAGGATACAAAGATTGGATCCTATGGATTTCCTTTGCCATATCATGCTTTTTGCTTTGTGCTGTTCTGCTAGGATTCATTATGTGGGCATGCCAAAAAGGCAACATTAGGTGCAACATTTGCATTTGA",
			"ATGAAGACTAGTAGTTCTGCTATATACATTGCAA------------------------CCGCAAATG---------CAGACACATTATGTATAGGTTATCATGCAGTACTAGAAAAGAATGTAACAGTAACACACTCTGTTAACCAAACTGAGAGGGGTAGCCCCATTGCATTTG--------------------GGTAAATGTAACATTGCTGGCTGGATCC------------------------------------TGGGAAATCCAGAGTGTGACACTCTCCACAGCAAGCTCATGGTCCTACATCGTGGAAACATCTAAGACAATGGAACGTGCTACCCAGGAGATTTCATCAATTATGAGGAGCTAAGGTCATCATTTGAAAGGTTTGAGATATTACAAGTTCATGGCCCAATCATGACTCGAACAAAGGTTCCTCAAGCTGGAGCAA---------------------------AAAGCTTCTACAAAAATTTAATATGGCTAGTTAAAAAAGGAAATTCATACCCAA------------------------------AGCTCAGCAAATCCTACATTTGGGGCATTCACCATCCATCTACTAGTGCTGACCAA-------CAAAGTCTCTATCAGAGTGCAGATGCATATGTTTTATCAAAATACAGCAAGAAGTTCAAG--CCGGAAATAGCAGTAAGACCCAAAGTGAGGGATCAAGAAGGGAGAATGAACTATTACTGGACACTAGTAGAGCCGGGAGACAAAATAACATTCGAAGCAACTGGAAATCTATTGGTACCGAGATATGCATTCGCAATGGAAA----GAAATGCTGGATTATCATTTCAGATACACCAGTCCACGATTGCAATACAACTTGTCAGACACCCAAGGGTGCTATAAACACCAGCCTCCCATTTCAGAATATACATCCGATCACAATTGGAAAATGTCCCAAATATGTAAAAAGCACAAAATTGAGACTGGCCACAGGATTGAGGAATGTCCCGTCTATTCAATCTAGAGGCCTATTTGGGGCCATTGCCGGTTTCATTGAAGGGGGGTGGACAGGGATGGTAGATGGATGGTACGGTTATCACCATCAAAATGCGCAGGGGTCAGGATATGCAGCCGACCTGAAGAGCACACAGAATGCCATTGACAAGATTACTAACAAAGTAAATTCTGTTATTGAAAAGATGAATACACAGTTCACAGCAGTAGGTAAAGAGTTCAACCACCTGGAAAAAAGAATAGAGAATTTAAATAAAAAAGTTGATGATGGTTTCCTGGACATTTGGACTTACAATGCCGAACTGTTGGTTCTATTGGAAAATGAAAGAACTTTGGACTACCACGATTCAAATGTGAAAAACTTATATGAAAAGGTAAGAAGCCAGTTAAAAAACAATGCCAAGGAAATTGGAAACGGCTGCTTTGAATTTTACCACAAATGCGATAACACGTGCATGGAAAGTGTCAAAAATGGGACTTATGACTACCCAAAATACTCAGAGGAAGCAAAATTAAACAGAGAAGAAATAGATGGGGTAAAGCTGGAATCAACAAGGATTTACCAGATTTTGGCGATCTATTCAACTGTCGCCAGTTCATTGGTACTGGTAGTCTCCCTGGGGGCAATCATCTGGATGTGCTCTAATGGGTCTCTACAGTGTAGAATATGTATTTAA",		
			"ATGAAGACTATCATTGCTTTGAGCTACATTTTATGTCTGGTTTTCGCTCAAAAACTTCCCGGAAATGACAACAGCACGGCAACGCTGTGCCTGGGGCACCATGCAGTGCCAAACGGAACGCTAGTGAAAACAATCACGAATGACCAAATTGAAGTAACTAATGCTACTGAGCTGGTTCAGAGTTCCTCAACAGGTAGAATATGCGACAGTCCTCACCAAATCCTTGATGGAGAAAACTGCACACTAATAGATGCTCTATTGGGAGACCCTCATTGTGATGGCTTCCAAAACAAGGAATGGGACCTTTTTGTTGAACGCAGCAAAGCCTACAGCAACTGTTACCCTTATGATGTGCCGGATTATGTCTCCCTTAGGTCACTAGTTGCCTCATCAGGCACGCTGGAGTTTAACAATGAAAGCTTCAATTGGACTGGAGTCGCTCAGAATGGAACAAGCTCTGCTTGCAAAAGGAGATCCGATAAAAGTTTCTTTAGTAGATTGAATTGGTTGCACCAATTAAAATACAAATATCCAGCACTGAACGTGACTATGCCAAACAATGAAAAATTTGACAAATTGTACATTTGGGGGGTTCACCACCCGGGTACAGACAGTGACCAAATCAGCCTATATGCTCAAGCATCAGGGAGAGTCACAGTCTCTACCAAAAGAAGCCAACAAACTGTAATCCCGAATATCGGATCTGGACCCTGGGTAAGGGGTGTCTCCAGCAGAATAAGCATCTATTGGACAATAGTAAAACCGGGAGACATACTTTTGATTAACAGCACAGGGAATCTAATTGCTCCTCGGGGTTACTTCAAAATACGAAGTGGGAAAAGCTCAATAATGAGGTCAGATGCACCCATTGGCAAATGCAATTCTGAATGCATCACTCCAAATGGAAGCATTCCCAATGGCAAACCATTTCAAAATGTAAACAGGATCACATATGGGGCCTGTCCCAGATATGTTAAGCAAAACACTCTGAAATTGGCAACAGGGATGCGGAATGTGCCAGAGAAACAAACTAGAGGCATATTCGGTGCAATCGCGGGCTTCATAGAAAATGGTTGGGAGGGAATGATGGACGGTTGGTACGGTTTCAGGCATCAGAATTCTGAGGGCACAGGGCAAGCAGCAGATCTTAAAAGCACTCAAGCAGCAATCAACCAAATCAACGGGAAACTGAATAGGTTAATCGAGAAAACGAACGAGAAATTCCATCAAATTGAAAAAGAATTCTCAGAAGTAGAAGGGAGAATTCAGGACCTCGAGAAATATGTCGAGGACACTAAAATAGATCTCTGGTCGTACAATGCGGAGCTTCTTGTTGCCCTGGAGAACCAACATACAATTGATCTAACTGACTCAGAAATGAACAAACTGTTTGAAAGAACAAAGAAGCAACTGAGGGAAAATGCTGAGGATATGGGCAATGGTTGTTTCAAAATATACCACAAATGTGACAATGCCTGCATAGGGTCAATCAGAAATGGAACTTATGACCATGATGTATACAGAGACGAAGCATTGAACAACCGGTTCCAGATCAAAGGTGTTGAGCTGAAGTCAGGATACAAAGATTGGATCCTATGGATTTCCTTTGCCATATCATGTTTTTTGCTTTGTATTGTTTTACTGGGGTTCATCATGTGGGCCTGCCAAAAAGGCAACATTAGGTGCAACATTTGCATTTGA",
			"--------------------------------------------------------------------------------AACGCTATGCCTGGGACACCATGCAGTACCAAATGGAACGTTAGTGAAAACAATCACGGATGACCAAATTGAAGTGACTAATGCTACTGAGCTGGTTCAAAGTTCCTCAACAGGTAGAATATGTAACAGTCCTCACCACATCCTTGATGGGAAAAATTGCACACTGATAGATGCTCTATTGGGAGACCCTCATTGTGATGACTTCCAAAACAAGGAATGGGACCTTTTTGTTGAACGAAGCACAGCCTACAGCAACTGCTACCCTTATTATGTGCCGGATTATGCCTCCCTTAGGTCACTAGTTGCCTCATCCGGCACCCTGGAATTCACCCAAGAAAGCTTCAATTGGACCGGAGTTACTCAAGATGGATCAAGCTATACTTGCAGAAGGAAATCTGTTAACAGTTTCTTTAGTAGATTAAATTGGTTGCATAATTTGGACTACAAATATCCAGCGCTGAACGTAACTATGCCAAACAATGACAAATTTGACAAATTGTACATTTGGGGGGTTCACCACCCGGGTACGGACAGGGACCAAACCAACCTATATGTTCAAGCATCAGGGAGAGTTACAGTCTCCACAAAAAGAAGCCAACAAACTGTAATCCCGAACATCGGATCTAGACCCTGGGTAAGGGGTGTCTCCAGCATAATAAGCATCTATTGGACAATAGTAAAACCGGGAGACATACTTTTGATTAACAGCACAGGAAATCTAATTGCCCCTCGGGGTTACTTCAAAATACAAAGTGGGAAAAGCTCAATAATGAGATCAGATGCACCCATTGGCAACTGCAATTCTGAATGCATTACTCCAAATGGAAGCATTCCCAATGACAAACCTTTTCAAAATGTAAACAGGATCACATATGGGGCCTGTCCAAGATATGTTAAGCAAAACACTCTGAAATTGGCAACAGGGATGCGGAATGTACCAGAGAAACAAACTAGAGGCATATTCGGCGCAATCGCAGGCTTCATAGAAAATGGTTGGGAGGGGATGGTGGACGGTTGGTACGGTTTCAGGCATCAAAATTCTGAAGGCACAGGACAAGCAGCAGATCTTAAAAGTACTCAAGCAGCAATCAACCAAATCACCGGGAAACTGAATAGAGTAATCAAGAAAACGAACGAGAAATTCCATCAAATCGAAAAAGAATTCTCAGAAGTAGAAGGGAGAATTCAGGACCTAGAGAAATACGTTGAAGACACTAAAATAGATCTCTGGTCTTACAACGCGGAGCTTCTTGTTGCCCTGGAGAACCAACATACAATTGATTTAACTGACTCAGAAATGAACAAACTGTTCGAAAGAACAAGGAAGCAACTGCGGGAAAATGCTGAGGACATGGGCAATGGTTGCTTCAAAATATACCACAAATGTGACAATGCCTGCATAGGATCAATCAGAAATGGAACTTATGACCATGATGTATACAGAGACGAGGCATTAAACAATCGGTTCCAGATCAAAAGTGTTCAGCTGAAGTCAGGATACAAAGATTGGATCCTATGGATTTCCTTTGCCATGTCATGCTTTTTGCTTTGTGTTGTTCTGCTGGGGTTCATTATGTGGACCTGCCAAAAAGGCAACATTAAGTGCAACATTTGCATTTGA"
			]
	
		for reassortant_seq in reassortant_seqs:
			for v in self.viruses:
				dist = distance(Seq(reassortant_seq), v)
				if (dist < 0.02):
					remove_viruses.append(v)
					if self.verbose>1:
						print "\tremoving", v.strain				

		self.viruses = MultipleSeqAlignment([v for v in self.viruses if v not in remove_viruses])
		
	def clean_outliers(self):
		"""Remove single outlying viruses"""
		remove_viruses = []
		outlier_strains = ["A/Helsinki/942/2013", "A/India/6352/2012", "A/Pennsylvania/14/2010", "A/HuNan/01/2014", "A/OSAKA/31/2005", "A/Sari/388/2006", "A/Busan/15453/2009"]
		for outlier_strain in outlier_strains:
			for v in self.viruses:
				if (v.strain == outlier_strain):
					remove_viruses.append(v)
					if self.verbose > 1:
						print "\tremoving", v.strain					
		self.viruses = MultipleSeqAlignment([v for v in self.viruses if v not in remove_viruses])
		
	def clean(self):
		self.clean_generic()
		self.clean_outbreaks()
		print "Number of viruses after outbreak filtering:",len(self.viruses)
		self.clean_reassortants()
		print "Number of viruses after reassortant filtering:",len(self.viruses)
		self.clean_outliers()
		print "Number of viruses after outlier filtering:",len(self.viruses)

class H3N2_refine(tree_refine):
	def __init__(self, **kwargs):
		tree_refine.__init__(self, **kwargs)

	def refine(self):
		self.refine_generic()  # -> all nodes now have aa_seq, xvalue, yvalue, trunk, and basic virus properties
		self.add_H3N2_attributes()

	def epitope_sites(self, aa):
		aaa = np.fromstring(aa, 'S1')
		return ''.join(aaa[epitope_mask[:len(aa)]=='1'])

	def nonepitope_sites(self, aa):
		aaa = np.fromstring(aa, 'S1')
		return ''.join(aaa[epitope_mask[:len(aa)]=='0'])

	def receptor_binding_sites(self, aa):
		'''
		Receptor binding site mutations from Koel et al. 2014
		These are (145, 155, 156, 158, 159, 189, 193) in canonical HA numbering
		need to subtract one since python arrays start at 0
		'''
		return ''.join([aa[pos] for pos in receptor_binding_sites])

	def get_total_peptide(self, node):
		'''
		the concatenation of signal peptide, HA1, HA1
		'''
		return node.aa_seq['SigPep']+node.aa_seq['HA1'] + node.aa_seq['HA2']

	def epitope_distance(self, aaA, aaB):
		"""Return distance of sequences aaA and aaB by comparing epitope sites"""
		epA = self.epitope_sites(aaA)
		epB = self.epitope_sites(aaB)
		distance = sum(a != b for a, b in izip(epA, epB))
		return distance

	def nonepitope_distance(self, aaA, aaB):
		"""Return distance of sequences aaA and aaB by comparing non-epitope sites"""
		neA = self.nonepitope_sites(aaA)
		neB = self.nonepitope_sites(aaB)
		distance = sum(a != b for a, b in izip(neA, neB))
		return distance

	def receptor_binding_distance(self, aaA, aaB):
		"""Return distance of sequences aaA and aaB by comparing receptor binding sites"""
		neA = self.receptor_binding_sites(aaA)
		neB = self.receptor_binding_sites(aaB)
		distance = sum(a != b for a, b in izip(neA, neB))
		return distance

	def add_H3N2_attributes(self):
		root = self.tree.seed_node
		root_total_aa_seq = self.get_total_peptide(root)
		for node in self.tree.postorder_node_iter():
			total_aa_seq = self.get_total_peptide(node)
			node.ep = self.epitope_distance(total_aa_seq, root_total_aa_seq)
			node.ne = self.nonepitope_distance(total_aa_seq, root_total_aa_seq)
			node.rb = self.receptor_binding_distance(total_aa_seq, root_total_aa_seq)



class H3N2_process(process, H3N2_filter, H3N2_clean, H3N2_refine, HI_tree, fitness_model):
	"""docstring for H3N2_process, H3N2_filter"""
	def __init__(self,verbose = 0, force_include = None, 
				force_include_all = False, max_global= True, **kwargs):
		self.force_include = force_include
		self.force_include_all = force_include_all
		self.max_global = max_global
		process.__init__(self, **kwargs)
		H3N2_filter.__init__(self,**kwargs)
		H3N2_clean.__init__(self,**kwargs)
		H3N2_refine.__init__(self,**kwargs)
		HI_tree.__init__(self,**kwargs)
		fitness_model.__init__(self,**kwargs)
		self.verbose = verbose

	def run(self, steps, viruses_per_month=50, raxml_time_limit = 1.0, lam_HI=2, lam_avi=2, lam_pot=.1):
		if 'filter' in steps:
			print "--- Virus filtering at " + time.strftime("%H:%M:%S") + " ---"
			self.filter()
			if self.force_include is not None and os.path.isfile(self.force_include):
				with open(self.force_include) as infile:
					forced_strains = [fix_name(line.strip()).upper() for line in infile]
			else:
				forced_strains = []
			self.subsample(viruses_per_month, 
				prioritize=forced_strains, all_priority=self.force_include_all, 
				region_specific = self.max_global)
			self.dump()
		else:
			self.load()
		if 'align' in steps:
			self.align()   	# -> self.viruses is an alignment object
		if 'clean' in steps:
			print "--- Clean at " + time.strftime("%H:%M:%S") + " ---"
			self.clean()   # -> every node as a numerical date
			self.dump()
		if 'tree' in steps:
			print "--- Tree	 infer at " + time.strftime("%H:%M:%S") + " ---"
			self.infer_tree(raxml_time_limit)  # -> self has a tree
			self.dump()
		if 'ancestral' in steps:
			print "--- Infer ancestral sequences " + time.strftime("%H:%M:%S") + " ---"
			self.infer_ancestral()  # -> every node has a sequence
			self.dump()
		if 'refine' in steps:
			print "--- Tree refine at " + time.strftime("%H:%M:%S") + " ---"
			self.refine()
			self.dump()
		if 'frequencies' in steps:
			print "--- Estimating frequencies at " + time.strftime("%H:%M:%S") + " ---"
			self.determine_variable_positions()
			self.estimate_frequencies(tasks = ["mutations", "tree"])
			if 'genotype_frequencies' in steps: 
					self.estimate_frequencies(tasks = ["genotypes"])
			self.dump()
		if 'HI' in steps:
			print "--- Adding HI titers to the tree " + time.strftime("%H:%M:%S") + " ---"
			self.determine_variable_positions()
			self.map_HI(training_fraction=1.0, method = 'nnl1reg', 
					lam_HI=lam_HI, lam_avi=lam_avi, lam_pot=lam_pot, map_to_tree=True)
			self.map_HI(training_fraction=1.0, method = 'nnl1reg', force_redo=True,
					lam_HI=lam_HI, lam_avi=lam_avi, lam_pot=lam_pot, map_to_tree=False)
			if not self.map_to_tree:
				self.cHI_mutations()
			self.dump()

		if 'export' in steps:
			self.add_titers()
			self.temporal_regional_statistics()
			# exporting to json, including the H3N2 specific fields
			self.export_to_auspice(tree_fields = [
				'ep', 'ne', 'rb', 'aa_muts','accession','isolate_id', 'lab','db', 'country',
				'dHI', 'cHI', 'mean_HI_titers','HI_titers','HI_titers_raw', 'serum', 'HI_info', 'avidity', 
				 'potency', 'mean_potency'], 
	               annotations = ['3c2.a', '3c3.a'])
			self.generate_indexHTML()

		if 'HIvalidate' in steps:
			print "--- generating validation figures " + time.strftime("%H:%M:%S") + " ---"
			import matplotlib.pyplot as plt
			htmlpath = '../auspice/'
			if self.virus_type is not None: 
				htmlpath+=self.virus_type+'/'
			if self.resolution is not None: 
				htmlpath+=self.resolution+'/'

			self.check_symmetry(plot=True)
			plt.savefig(htmlpath+'HI_symmetry.png')

			self.map_HI(training_fraction=0.9, method='nnl1reg',lam_HI=lam_HI, lam_avi=lam_avi, 
						lam_pot = lam_pot, force_redo=True, map_to_tree=False)
			self.validate(plot=True)
			plt.savefig(htmlpath+'HI_prediction.png')

			unexplained_variance = []
			cvals = np.linspace(0,2,40)
			for cutoff in cvals:
				self.validate(plot=False, cutoff=cutoff)
				unexplained_variance.append([cutoff,self.rms_error**2, np.var(self.validation.values())])
				print cutoff, unexplained_variance[-1]
			unexplained_variance=np.array(unexplained_variance)
			plt.figure()
			plt.plot(unexplained_variance[:,0], unexplained_variance[:,1]/unexplained_variance[:,2])
			plt.savefig(htmlpath+'HI_cutoff.png')

if __name__=="__main__":
	all_steps = ['filter', 'align', 'clean', 'tree', 'ancestral', 'refine', 
				 'frequencies','HI', 'export']
	from process import parser

	params = parser.parse_args()

	lt = time.localtime()
	num_date = round(lt.tm_year+(lt.tm_yday-1.0)/365.0,2)
	params.time_interval = (num_date-params.years_back, num_date) 
	if params.interval is not None and len(params.interval)==2 and params.interval[0]<params.interval[1]:
		params.time_interval = (params.interval[0], params.interval[1])
	dt= params.time_interval[1]-params.time_interval[0]
	params.pivots_per_year = 12.0 if dt<5 else 6.0 if dt<10 else 3.0
	steps = all_steps[all_steps.index(params.start):(all_steps.index(params.stop)+1)] + ['HIvalidate']
	if params.skip is not None:
		for tmp_step in params.skip:
			if tmp_step in steps:
				print "skipping",tmp_step
				steps.remove(tmp_step)

	# add all arguments to virus_config (possibly overriding)
	virus_config.update(params.__dict__)
	# pass all these arguments to the processor: will be passed down as kwargs through all classes
	myH3N2 = H3N2_process(**virus_config) 
	if params.test:
		myH3N2.load()
	else:
		myH3N2.run(steps, viruses_per_month = virus_config['viruses_per_month'], 
			raxml_time_limit = virus_config['raxml_time_limit'])

	from random import sample
	leaf_sample = sample([leaf for leaf in myH3N2.tree.leaf_iter() 
						  if leaf.num_date>2014], 10)

	trunk_effects = []
	trunk_muts = []
	trunk_mut_effects = []
	for node in leaf_sample:
		tmp_muts = []
		tmp_effects = []
		while node.parent_node is not None:
			tmp_effects.append(node.dHI)
			tmp_muts.extend(node.aa_muts.items())
			node = node.parent_node

		tmp_muts = [x for x in tmp_muts if x[1]!='']
		tmp_mut_effects = {}
		for muts in tmp_muts:
			gene = muts[0]
			for pos in muts[1].split(','):
				tmp_mut = (gene, pos)
				if tmp_mut in myH3N2.mutation_effects:
					tmp_mut_effects[tmp_mut] = myH3N2.mutation_effects[tmp_mut]
				else:
					tmp_mut_effects[tmp_mut] = 0

		trunk_effects.append(tmp_effects)
		trunk_muts.append(tmp_muts)
		trunk_mut_effects.append(tmp_mut_effects)

	plt.figure()
	for eff in trunk_effects:
		plt.plot(sorted(eff), np.linspace(1,0,len(eff)))

	plt.figure()
	for eff in trunk_mut_effects:
		plt.plot(sorted(eff.values()), np.linspace(1,0,len(eff)))
