import sys
import json
import os
from pathlib import Path

from Bio import Entrez, SeqIO
from Bio.SeqRecord import SeqRecord
from Bio.Seq import Seq

from src.bowtie import build
from src.advanced_parameters import minimum_intergenic_region_length

def get_from_cache(genbank_id):
	root_dir = Path(__file__).parent.parent
	genbank_assets_path = os.path.join(root_dir, 'assets', 'genbank')
	os.makedirs(genbank_assets_path, exist_ok=True)

	genbank_file = os.path.join(genbank_assets_path, f'{genbank_id}.gb')
	if Path(genbank_file).exists():
		with open(genbank_file, 'r') as f:
			return SeqIO.read(f, 'gb')
	return False

def save_to_cache(genbank_id, record):
	root_dir = Path(__file__).parent.parent
	genbank_assets_path = os.path.join(root_dir, 'assets', 'genbank')
	os.makedirs(genbank_assets_path, exist_ok=True)

	genbank_file = os.path.join(genbank_assets_path,  f'{genbank_id}.gb')
	with open(genbank_file, 'w') as f:
		SeqIO.write(record, f, 'gb')
	genbank_fasta = os.path.join(genbank_assets_path,  f'{genbank_id}.fasta')
	with open(genbank_fasta, 'w') as f:
		SeqIO.write(record, f, 'fasta')
	build(genbank_id)

def retrieve_annotation(genbank_id, email):
	# *Always* tell NCBI who you are
	Entrez.email = email

	cached = get_from_cache(genbank_id)
	if cached:
		return cached	
	"""
	Annotates Entrez Gene IDs using Bio.Entrez, in particular epost (to
	submit the data to NCBI) and esummary to retrieve the information.
	Returns a list of dictionaries with the annotations.
	"""
	print(f"Fetching genbank info for {genbank_id}")
	handle = Entrez.efetch("nucleotide", id=genbank_id, rettype="gb", retmode="text")
	try:
		result = SeqIO.read(handle, 'gb')
	except RuntimeError as e:
		print(e)
		sys.exit(-1)
	save_to_cache(genbank_id, result)
	return result

def get_noncoding_regions_from_genes(genes, genome, nonessential):
	genome_end = len(genome)
	noncoding_regions = []
	
	gene_index = 0
	prev_gene = {'end': -1, 'direction': 'none'}
	while gene_index < len(genes):
		next_gene = genes[gene_index]
		if (int(next_gene['start']) - int(prev_gene['end'])) > minimum_intergenic_region_length:
			# add check for essentiality, if it's a parameter only use noncoding regions with 
			# C term on each side (aka, prev gene orientation is 'fw' and next gene orientation is 'rv')
			if not nonessential or (prev_gene['direction'] == 'fw' and next_gene['direction'] == 'rv'):
				start = int(prev_gene['end'])+1
				end = int(next_gene['start'])-1
				new_region = {
					'name': f'noncoding_{str(len(noncoding_regions)+1)}-{start}-{end}',
					'start': start,
					'end': end,
					'direction': 'fw'
				}
				noncoding_regions.append(new_region)
		prev_gene = next_gene
		gene_index += 1
	return noncoding_regions

def basic_gene_info(gene):
	# Returns a structure in which direction is explicitly stated, and
	# start is always before end in the refseq
	genbank_start = int(gene.location.start)+1
	genbank_end = int(gene.location.end)
	direction = 'fw' if gene.location.strand == 1 else 'rv'
	try:
		locus_tag = gene.qualifiers['locus_tag'][0]
	except:
		locus_tag = f'Unknown_Name_{min(genbank_start, genbank_end)}'
	return {
		"name": locus_tag,
		"start": min(genbank_start, genbank_end),
		"end":  max(genbank_start, genbank_end),
		"direction": direction
	}

def get_regions(genbank, region='coding'):
	genes = [feat for feat in genbank.features if feat.type == 'gene']
	genes = [basic_gene_info(g) for g in genes]
	if region != 'coding':
		genome = annotation_result['GBSeq_sequence']
		noncoding_regions = get_noncoding_regions_from_genes(genes, genome, region=='nonessential')
		return noncoding_regions
	return genes