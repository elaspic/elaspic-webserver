
-- === uniprot_kb ===

-- ClinVar
CREATE OR REPLACE VIEW clinvar_mutation AS 
SELECT * FROM elaspic_mutation.clinvar_mutation;

-- Uniprot
CREATE OR REPLACE VIEW uniprot_mutation AS 
SELECT * FROM elaspic_mutation.uniprot_mutation;

-- COSMIC
CREATE OR REPLACE VIEW cosmic_mutation AS 
SELECT * FROM elaspic_mutation.cosmic_mutation;


-- === elaspic_mutation ===

-- hgnc_identifiers
CREATE OR REPLACE VIEW hgnc_identifiers AS 
SELECT * FROM uniprot_kb.hgnc_identifiers;

-- uniprot_identifier
CREATE OR REPLACE VIEW uniprot_identifier AS 
SELECT * FROM uniprot_kb.uniprot_identifier;

-- uniprot_sequence
CREATE OR REPLACE VIEW elaspic_sequence AS 
SELECT 
uniprot_id protein_id,
uniprot_name protein_name,
protein_name description,
organism_name,
# gene_name,
# protein_existence isoforms,
# sequence_version,
# db,
uniprot_sequence sequence,
provean_supset_filename provean_supset_file,
provean_supset_length
FROM uniprot_kb.uniprot_sequence us
LEFT JOIN elaspic.provean USING (uniprot_id);


-- === elaspic_core_model ===

CREATE OR REPLACE VIEW elaspic_core_model AS
SELECT 
-- domain
ud.uniprot_id protein_id,
ud.uniprot_domain_id domain_id,
ud.pfam_clan,
ud.pdbfam_name,
ud.alignment_def,
ud.path_to_data,

-- template
udt.alignment_score,
udt.alignment_coverage,
udt.template_errors,
udt.domain_def,
udt.cath_id,
udt.alignment_identity,

-- model
udmut.model_filename_wt model_file_wt,
udmut.model_filename_mut model_file_mut,
udm.model_errors,
udm.norm_dope,
udm.model_filename,
udm.alignment_filename,
udm.chain,
udm.model_domain_def

FROM elaspic.uniprot_domain ud
JOIN elaspic.uniprot_domain_template udt USING (uniprot_domain_id)
LEFT JOIN elaspic.uniprot_domain_model udm USING (uniprot_domain_id);


-- === elaspic_core_mutation ===

CREATE OR REPLACE VIEW elaspic_core_mutation AS
SELECT 
ud.uniprot_domain_id domain_id,
ud.uniprot_id protein_id,
udmut.mutation,

-- mutation
udmut.mut_date_modified,
udmut.mutation_errors,
udmut.chain_modeller,
udmut.mutation_modeller,
udmut.stability_energy_wt,
udmut.stability_energy_mut,
udmut.physchem_wt,
udmut.physchem_wt_ownchain,
udmut.physchem_mut,
udmut.physchem_mut_ownchain,
udmut.secondary_structure_wt,
udmut.secondary_structure_mut,
udmut.solvent_accessibility_wt,
udmut.solvent_accessibility_mut,
udmut.matrix_score,
udmut.provean_score,
udmut.ddG

FROM elaspic.uniprot_domain ud
JOIN elaspic.uniprot_domain_mutation udmut USING (uniprot_id, uniprot_domain_id);


-- === elaspic_interface_model ===

CREATE OR REPLACE VIEW elaspic_interface_model AS 
SELECT
-- interface
udp.uniprot_domain_pair_id interface_id,
udp.uniprot_id_1 protein_id_1,
udp.uniprot_domain_id_1 domain_id_1,
udp.uniprot_id_2 protein_id_2,
udp.uniprot_domain_id_2 domain_id_2,

udp.path_to_data data_path,

-- template
udpt.score_1 alignment_score_1,
udpt.score_2 alignment_score_2,
udpt.coverage_1 alignment_coverage_1,
udpt.coverage_2 alignment_coverage_2,

udpt.cath_id_1,
udpt.cath_id_2,
udpt.identical_1 alignment_identity_1,
udpt.identical_2 alignment_identity_2,
udpt.template_errors,

-- model
udpmut.model_filename_wt model_file_wt,
udpmut.model_filename_mut model_file_mut,
udpm.model_errors,
udpm.norm_dope,
udpm.model_filename,
udpm.alignment_filename_1,
udpm.alignment_filename_2,
udpm.interacting_aa_1,
udpm.interacting_aa_2,
udpm.chain_1,
udpm.chain_2,
udpm.interface_area_hydrophobic,
udpm.interface_area_hydrophilic,
udpm.interface_area_total,
udpm.model_domain_def_1,
udpm.model_domain_def_2

FROM elaspic.uniprot_domain_pair udp
JOIN elaspic.uniprot_domain_pair_template udpt USING (uniprot_domain_pair_id)
LEFT JOIN elaspic.uniprot_domain_pair_model udpm USING (uniprot_domain_pair_id);


-- === elaspic_interface_mutation ===

CREATE OR REPLACE VIEW elaspic_interface_mutation AS 
SELECT
udp.uniprot_domain_pair_id interface_id,
# udp.uniprot_id_1 protein_id_1,
# udp.uniprot_domain_id_1 domain_id_1,
# udp.uniprot_id_2 protein_id_2,
# udp.uniprot_domain_id_2 domain_id_2,
udpmut.uniprot_id protein_id,
udpmut.mutation,
IF(udpmut.chain_modeller = 'A', 0, 1) chain_idx,

-- mutation
udpmut.mut_date_modified,
udpmut.mutation_errors,
udpmut.chain_modeller,
udpmut.mutation_modeller,
udpmut.stability_energy_wt,
udpmut.stability_energy_mut,
udpmut.analyse_complex_energy_wt,
udpmut.analyse_complex_energy_mut,
udpmut.physchem_wt,
udpmut.physchem_wt_ownchain,
udpmut.physchem_mut,
udpmut.physchem_mut_ownchain,
udpmut.secondary_structure_wt,
udpmut.secondary_structure_mut,
udpmut.solvent_accessibility_wt,
udpmut.solvent_accessibility_mut,
udpmut.contact_distance_wt,
udpmut.contact_distance_mut,
udpmut.matrix_score,
udpmut.provean_score,
udpmut.ddg

FROM elaspic.uniprot_domain_pair udp
JOIN elaspic.uniprot_domain_pair_mutation udpmut USING (uniprot_domain_pair_id);
