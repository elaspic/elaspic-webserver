# Monkey-patching

from kmtools import structure_tools


def get_chain_sequence(chain):
    return ''.join(structure_tools.AAA_DICT[r.resname] for r in chain.get_residues())

structure_tools.get_chain_sequence = get_chain_sequence

