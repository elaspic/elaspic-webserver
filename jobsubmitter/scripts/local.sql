drop table if exists elaspic.local_sequence;

create table elaspic.local_sequence (
    s_id int NOT NULL AUTO_INCREMENT,
    unique_id varchar(255) NOT NULL,
    idx int NOT NULL,
    protein_id varchar(255),
    provean_supset_exists bool,
    provean_supset_file text,
    provean_supset_length int,
    sequence text,
    sequence_file text,
    primary key (s_id)
);

create unique index a on elaspic.local_sequence (unique_id, idx);


drop table if exists elaspic.local_model;

create table elaspic.local_model (
    m_id int NOT NULL AUTO_INCREMENT,
    unique_id varchar(255) NOT NULL,
    idx int NOT NULL,  
    idx_2 int NOT NULL default -1,
    alignment_file text,
    alignment_file_2 text,
    chain_ids varchar(255),  # ','.join
    core_or_interface varchar(255),
    domain_def_offset varchar(255),
    domain_def_offset_2 varchar(255),
    interacting_residues_1 text,  # ','.join
    interacting_residues_2 text,  # ','.join
    interface_area_hydrophilic double,
    interface_area_hydrophobic double,
    interface_area_total double,
    knotted bool,
    model_file text,
    model_id varchar(255),
    modeller_chain_ids varchar(255),  # ','.join
    modeller_results text,  # json.dumps
    modeller_results_file text,
    model_sequence_file text,
    model_sequence_id varchar(255),
    model_structure_file text,
    model_structure_id varchar(255),
    pir_alignment_file text,
    raw_model_file text,
    sasa_score text,
    primary key (m_id)
);

create unique index a on elaspic.local_model (unique_id, idx, idx_2);


drop table if exists elaspic.local_mutation;

create table elaspic.local_mutation (
    mut_id int NOT NULL AUTO_INCREMENT,
    unique_id varchar(255) NOT NULL,
    idx int NOT NULL,
    idx_2 int NOT NULL default -1,
    mutation varchar(255),
    alignment_coverage double,
    alignment_identity double,
    alignment_score double,
    analyse_complex_energy_mut text,
    analyse_complex_energy_wt text,
    contact_distance_mut double,
    contact_distance_wt double,
    ddg double,
    matrix_score double,
    model_filename_mut text,
    model_filename_wt text,
    norm_dope double,
    physchem_mut varchar(255),
    physchem_mut_ownchain varchar(255),
    physchem_wt varchar(255),
    physchem_wt_ownchain varchar(255),
    provean_score double,
    secondary_structure_mut char(1),
    secondary_structure_wt char(1),
    solvent_accessibility_mut double,
    solvent_accessibility_wt double,
    stability_energy_mut text,
    stability_energy_wt text,
    primary key (mut_id)
);

create unique index a on elaspic.local_mutation (unique_id, idx, idx_2, mutation);



drop view if exists elaspic.local_sequence_2;

create view elaspic.local_sequence_2 as (
select
s_id s_id_2,
unique_id,
idx idx_2,
protein_id protein_id_2,
provean_supset_exists provean_supset_exists_2,
provean_supset_file provean_supset_file_2,
provean_supset_length provean_supset_length_2,
sequence sequence_2,
sequence_file sequence_file_2
from elaspic.local_sequence
);


drop view if exists elaspic.local_all;

create view elaspic.local_all as (
select *
from elaspic.local_model m
join elaspic.local_mutation mut using (unique_id, idx, idx_2)
join elaspic.local_sequence s1 using (unique_id, idx)
join elaspic.local_sequence_2 s2 using (unique_id, idx_2)
);
