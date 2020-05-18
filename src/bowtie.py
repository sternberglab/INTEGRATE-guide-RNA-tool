import sys
import subprocess
import multiprocessing
import os
from pathlib import Path

mismatch_threshold = 5

def build(genbankId):
	root_dir = Path(__file__).parent.parent
	bowtie_exec_dir = os.path.join(root_dir, 'assets', 'bowtie', 'pkg')
	bowtie_genome_dir = os.path.join(root_dir, 'assets', 'bowtie', genbankId)
	os.makedirs(bowtie_genome_dir, exist_ok=True)

	build_output_name = os.path.join(bowtie_genome_dir, 'index')
	# if index exists no need to rebuild
	if Path.exists(f'{build_output_name}.1.bt2'):
		return

	# build the index file for bowtie to use
	bowtie_build_exec = os.path.join(bowtie_exec_dir, 'bowtie2-build')
	
	fasta_file = os.path.join(root_dir, 'assets', 'genbank', f'{genbankId}.fasta')
	build_command = f'{bowtie_build_exec} {fasta_file} {build_output_name} -q'
	subprocess.run(build_command, shell=True)

def find_offtargets(genbankId, fasta_name):
	root_dir = Path(__file__).parent.parent
	bowtie_exec = os.path.join(root_dir, 'assets', 'bowtie', 'pkg', 'bowtie2')
	index_location = os.path.join(root_dir, 'assets', 'bowtie', genbankId, 'index')
	# Run the bowtie2 alignment command
	# -x {} : the name of the genome index file (already built by bowtie2-build)
	# -a : return all results, not just highest match
	# -f : read is a fasta file
	# -t : include time in the command line output
	# -p {} : use multiple cores for faster processing
	# -S {} : output reads to SAM file at this path
	# --no-1mm-upfront : "no 1 mismatch upfront", normally bowtie2 will return if it finds an exact or 1 mismatch read before doing a deeper search
	# --np 0 --n-ceil 5 : No penalty for ambiguous base pairs in the sequence ("N"), and allow up to 5
	# --score-min : scoring equation, for us just flat min score of (-6 per mismatch X mismatch_threshold) or greater is a pass
	# -N 0 -L 5 -i S,6,0 -D 10: Sets the multiseed alignment rules. 0 mismatches allowed, seed length 5, and skip 6bp between seeds. Search up to 10 seeds before failing
	# (This means there must be one fully matching 5bp sequence between a set of ambiguous characters to pass the seed filtering)
	cores = multiprocessing.cpu_count()
	output_name = fasta_name.split('.')[0] + '-offtarget-matches.sam'
	output_location = os.path.join(root_dir, 'assets', 'bowtie', genbankId, output_name)

	root_dir = Path(__file__).parent.parent
	bowtie_exec = os.path.join(root_dir, 'assets', 'bowtie', 'pkg', 'bowtie2')
	index_location = os.path.join(root_dir, 'assets', 'bowtie', genbankId, 'index')

	align_command = f'{bowtie_exec} -x {index_location} -a -f -t {fasta_name} -p {cores - 1} -S {output_location} --no-1mm-upfront --np 0 --n-ceil 5 --score-min L,-{6*mismatch_threshold+1},0 -N 0 -L 5 -i S,6,0 -D 6'
	subprocess.run(align_command, shell=True)
	return output_location