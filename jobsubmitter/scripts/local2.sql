
-- === elaspic_sequence_local ===

CREATE OR REPLACE VIEW uniprot_sequence AS 
SELECT 
protein_id,
protein_name,
description,
organism_name,
gene_name,
protein_existence isoforms,
sequence_version,
db,
uniprot_sequence seq


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
udt.template_errors,
udt.domain_def,
udt.cath_id,
udt.alignment_identity,

-- model
udm.model_errors,
udm.norm_dope,
udm.model_filename,
udm.alignment_filename,
udm.chain,
udm.model_domain_def

FROM elaspic.uniprot_domain ud
JOIN elaspic.uniprot_domain_template udt USING (uniprot_domain_id)
JOIN elaspic.uniprot_domain_model udm USING (uniprot_domain_id);


-- === elaspic_core_mutation ===

CREATE OR REPLACE VIEW elaspic_core_mutation AS
SELECT 
ud.uniprot_domain_id domain_id,
ud.uniprot_id protein_id,
udmut.mutation,

-- mutation
udmut.mut_date_modified,
udmut.model_filename_wt,
udmut.model_filename_mut,
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
udmut.ddg

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
-- 
udp.path_to_data data_path,

-- template
udpt.score_1,
udpt.score_2,
udpt.cath_id_1,
udpt.cath_id_2,
udpt.identical_1,
udpt.identical_2,
udpt.template_errors,

-- model
udpm.model_errors,
udpm.norm_dope,
udpm.model_filename,
udpm.alignment_filename_1,
udpm.alignment_filename_2,
udpm.interacting_aa_1 text,  -- interacting_residues_1
udpm.interacting_aa_2 text,  -- interacting_residues_2
udpm.chain_1,
udpm.chain_2,
udpm.interface_area_hydrophobic double,
udpm.interface_area_hydrophilic double,
udpm.interface_area_total double,
udpm.model_domain_def_1 varchar(255),  -- domain_def_offset
udpm.model_domain_def_2 varchar(255)   -- domain_def_offset_2

FROM elaspic.uniprot_domain_pair udp
JOIN elaspic.uniprot_domain_pair_template udpt USING (uniprot_domain_pair_id)
JOIN elaspic.uniprot_domain_pair_model udpm USING (uniprot_domain_pair_id);


udpmut.model_filename_wt,  -- xxx
udpmut.model_filename_mut,  -- xxx 



-- === elaspic_interface_mutation ===

CREATE OR REPLACE VIEW elaspic_interface_mutation AS 
SELECT
udp.uniprot_domain_pair_id interface_id int,
# udp.uniprot_id_1 protein_id_1,
# udp.uniprot_domain_id_1 domain_id_1,
# udp.uniprot_id_2 protein_id_2,
# udp.uniprot_domain_id_2 domain_id_2,
udpmut.uniprot_id protein_id varchar(255),
udpmut.mutation varchar(15),

-- mutation
udpmut.mutation_errors text,
udpmut.chain_modeller varchar(15),
udpmut.mutation_modeller varchar(15),
udpmut.stability_energy_wt text,
udpmut.stability_energy_mut text,
udpmut.analyse_complex_energy_wt text,
udpmut.analyse_complex_energy_mut text,
udpmut.physchem_wt varchar(255),
udpmut.physchem_wt_ownchain varchar(255),
udpmut.physchem_mut varchar(255),
udpmut.physchem_mut_ownchain varchar(255),
udpmut.secondary_structure_wt char(1),
udpmut.secondary_structure_mut char(1),
udpmut.solvent_accessibility_wt double,
udpmut.solvent_accessibility_mut double,
udpmut.contact_distance_wt double,
udpmut.contact_distance_mut double,
udpmut.matrix_score double,
udpmut.provean_score double,
udpmut.ddg double,
udpmut.mut_date_modified DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP

FROM elaspic.uniprot_domain_pair udp
JOIN elaspic.uniprot_domain_pair_mutation udpmut USING (uniprot_domain_pair_id);
