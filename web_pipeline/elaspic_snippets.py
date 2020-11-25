_names_stability = [
    ("dg", 1),  # totalEnergy
    ("backbone_hbond", 2),
    ("sidechain_hbond", 3),
    ("van_der_waals", 4),
    ("electrostatics", 5),
    ("solvation_polar", 6),
    ("solvation_hydrophobic", 7),
    ("van_der_waals_clashes", 8),
    ("entropy_sidechain", 9),
    ("entropy_mainchain", 10),
    ("sloop_entropy", 11),
    ("mloop_entropy", 12),
    ("cis_bond", 13),
    ("torsional_clash", 14),
    ("backbone_clash", 15),
    ("helix_dipole", 16),
    ("water_bridge", 17),
    ("disulfide", 18),
    ("electrostatic_kon", 19),
    ("partial_covalent_bonds", 20),
    ("energy_ionisation", 21),
    ("entropy_complex", 22),
    ("number_of_residues", 23),
]
names_stability_wt = [name + "_wt" for name, position in _names_stability[:-1]] + [
    "number_of_residues"
]
names_stability_mut = [name + "_mut" for name, position in _names_stability[:-1]] + [
    "number_of_residues"
]

_names_stability_complex = [
    ("intraclashes_energy_1", 3),
    ("intraclashes_energy_2", 4),
] + [(name, position + 4) for name, position in _names_stability]
names_stability_complex_wt = [name + "_wt" for name, position in _names_stability_complex[:-1]] + [
    "number_of_residues"
]
names_stability_complex_mut = [
    name + "_mut" for name, position in _names_stability_complex[:-1]
] + ["number_of_residues"]
