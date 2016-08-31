#!/usr/bin/env python
import os
import os.path as op
import argparse
import time

import MySQLdb
import pandas as pd

pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)

DB_SCHEMA = 'elaspic_webserver'

PROTEIN_SEQUENCE_TABLE = 'elaspic_protein_sequence_local'
CORE_MODEL_TABLE = 'elaspic_core_model_local'
CORE_MUTATION_TABLE = 'elaspic_core_mutation_local'
INTERFACE_MODEL_TABLE = 'elaspic_interface_model_local'
INTERFACE_MUTATION_TABLE = 'elaspic_interface_mutation_local'


# %% Helper functions
def parse_args():
    """
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--unique_id')
    parser.add_argument('-m', '--mutations')
    parser.add_argument('-t', '--run_type')
    parser.add_argument('-d', '--data_dir', nargs='?', default=os.getcwd())
    args = parser.parse_args()
    return args


def validate_args(args):
    assert op.split(args.data_dir)[-1] == args.unique_id


def apply_notnull(df, column, fn):
    df.loc[df[column].notnull(), column] = df.loc[df[column].notnull(), column].apply(fn)


def upload_data(connection, df, table_name):
    with connection.cursor() as cur:
        columns = ','.join(df.columns)
        db_command = (
            "replace into {}.{} ({}) values ({});".format(
                DB_SCHEMA,
                table_name, columns,
                ','.join(['%s' for _ in range(len(df.columns))]))
        )
        print(db_command)
        cur.executemany(db_command, list(df.to_records(index=False)))
        print('Uploaded data.')
    connection.commit()


def finalize_mutation(connection, unique_id, mutation):
    mutation = mutation.split('_')[-1]
    with connection.cursor() as cur:
        sql_command = "CALL update_muts('{}', '{}');".format(unique_id, mutation)
        print(sql_command)
        cur.execute(sql_command)
    connection.commit()
    print('Finalized mutation!')


def get_domain_id_lookup(connection, unique_id):
    sql_query = """\
select protein_id, domain_idx, domain_id
from {}.{}
where protein_id = '{}';
""".format(DB_SCHEMA, CORE_MODEL_TABLE, unique_id)
    with connection.cursor() as cur:
        cur.execute(sql_query)
        result = cur.fetchall()
    print('result:\n{}'.format(result))
    domain_id_lookup = {tuple(x[:2]): x[2] for x in result}
    print('domain_id_lookup:\n{}'.format(domain_id_lookup))
    return domain_id_lookup


def get_interface_id_lookup(connection, unique_id):
    sql_query = """\
select domain_id_1, domain_id_2, interface_id
from {0}.{1}
where protein_id_1 = '{2}' or protein_id_2 = '{2}';
""".format(DB_SCHEMA, INTERFACE_MODEL_TABLE, unique_id)
    with connection.cursor() as cur:
        cur.execute(sql_query)
        result = cur.fetchall()
    print('result:\n{}'.format(result))
    interface_id_lookup = {tuple(x[:2]): x[2] for x in result}
    print('interface_id_lookup:\n{}'.format(interface_id_lookup))
    return interface_id_lookup


def format_columns(df, column_dict):
    for to_column, mod in column_dict.items():
        if mod:
            from_columns, fn = mod
            if from_columns == '':
                df[to_column] = fn()
            elif from_columns and fn:
                df[to_column] = df[from_columns].apply(fn)
            elif from_columns:
                df[to_column] = df[from_columns]
            elif fn:
                df[to_column] = df[to_column].apply(fn)
            else:
                raise RuntimeError
        if to_column not in df.columns:
            print("Missing: '{}'".format(to_column))


def drop_columns(df, column_dict):
    df = df.drop([c for c in df.columns if c not in column_dict], axis=1)
    df = df.where(df.notnull(), None)
    return df


# %% Sequence
def upload_sequence(unique_id, data_dir):
    """
    """
    print('upload_sequence({}, {})'.format(unique_id, data_dir))
    #
    elaspic_sequence_columns = dict(
        protein_id=None,
        protein_name=None,
        description=None,
        organism_name=None,
        # gene_name=None,
        # isoforms=None,
        # sequence_version=None,
        # db=None,
        sequence=None,
        provean_supset_file=None,
        provean_supset_length=None,
    )
    #
    sequence_result = pd.read_json(op.join(data_dir, '.elaspic', 'sequence.json'))
    print("sequence_result:\n'{}'".format(sequence_result))
    sequence_result = sequence_result.rename(columns={'protein_id': 'protein_name'})
    sequence_result['protein_id'] = unique_id
    sequence_result['description'] = 'User submitted'
    sequence_result['organism_name'] = 'unknown'

    sequence_result = sequence_result.drop(
        [c for c in sequence_result.columns if c not in elaspic_sequence_columns], axis=1)
    sequence_result = sequence_result.where(sequence_result.notnull(), None)
    print(sequence_result)

    # Save to database
    connection = MySQLdb.connect(
        host='192.168.6.19', port=3306, user='elaspic-web', passwd='elaspic', db=DB_SCHEMA,
    )
    try:
        with connection.cursor() as cur:
            db_command = (
                "replace into {}.elaspic_sequence_local ({}) values ({});"
                .format(
                    DB_SCHEMA,
                    ','.join(sequence_result.columns),
                    ','.join(['%s' for _ in range(len(sequence_result.columns))]))
            )
            print(db_command)
            cur.executemany(db_command, args=list(sequence_result.to_records(index=False)))
        connection.commit()
    finally:
        connection.close()


# %% Model
def upload_model(unique_id, data_dir):
    """
    """
    print('upload_model({}, {})'.format(unique_id, data_dir))
    #
    core_model_columns = dict(
        # domain
        protein_id=None,  # unique_id
        domain_id=None,  # autoincrement
        domain_idx=('idx', None),
        #
        pfam_clan=('structure_id', None),
        pdbfam_name=('structure_id', None),
        alignment_def=('model_domain_defs', lambda x: ':'.join(str(i) for i in x[0])),
        path_to_data=('structure_file', lambda x: op.join(op.dirname(op.abspath(x)), '.elaspic')),

        # template
        template_errors=('', lambda: None),
        domain_def=('model_domain_defs', lambda x: ':'.join(str(i) for i in x[0])),
        cath_id=('structure_id', None),
        alignment_identity=('alignment_stats', lambda x: x[0][0]),
        alignment_coverage=('alignment_stats', lambda x: x[0][1]),
        alignment_score=('alignment_stats', lambda x: x[0][2]),

        # model
        model_errors=('', lambda: None),
        norm_dope=None,
        model_filename=('model_file', None),
        alignment_filename=('alignment_files', lambda x: x[0]),
        chain=('chain_ids', lambda x: x[0]),
        model_domain_def=('model_domain_defs', lambda x: ':'.join(str(i) for i in x[0])),
    )

    interface_model_columns = dict(
        interface_id=None,
        protein_id_1=('protein_id', None),
        domain_id_1=None,
        # domain_idx_1=('idxs', lambda x: x[0]),
        protein_id_2=('protein_id', None),
        domain_id_2=None,
        # domain_idx_2=('idxs', lambda x: x[1]),

        # domain pair
        path_to_data=('structure_file', lambda x: op.join(op.dirname(op.abspath(x)), '.elaspic')),

        # template
        template_errors=('', lambda: None),
        cath_id_1=('structure_id', lambda x: x[:-1]),
        cath_id_2=('structure_id', lambda x: x[:-2] + x[-1]),
        alignment_identity_1=('alignment_stats', lambda x: x[0][0]),
        alignment_identity_2=('alignment_stats', lambda x: x[1][0]),
        alignment_coverage_1=('alignment_stats', lambda x: x[0][1]),
        alignment_coverage_2=('alignment_stats', lambda x: x[1][1]),
        alignment_score_1=('alignment_stats', lambda x: x[0][2]),
        alignment_score_2=('alignment_stats', lambda x: x[1][2]),

        # model
        model_errors=('', lambda: None),
        norm_dope=None,
        model_filename=('model_file', None),
        alignment_filename_1=('alignment_files', lambda x: x[0]),
        alignment_filename_2=('alignment_files', lambda x: x[0]),
        interacting_aa_1=(None, lambda x: ','.join(str(i) for i in x)),
        interacting_aa_2=(None, lambda x: ','.join(str(i) for i in x)),
        chain_1=('chain_ids', lambda x: x[0]),
        chain_2=('chain_ids', lambda x: x[1]),
        interface_area_hydrophobic=None,
        interface_area_hydrophilic=None,
        interface_area_total=None,
        model_domain_def_1=('model_domain_defs', lambda x: ':'.join(str(i) for i in x[0])),
        model_domain_def_2=('model_domain_defs', lambda x: ':'.join(str(i) for i in x[1])),
    )
    # Load data
    model_result = pd.read_json(op.join(data_dir, '.elaspic', 'model.json'))
    print("model_result:\n'{}'".format(model_result))
    model_result['protein_id'] = unique_id

    if 'idxs' in model_result.columns:
        model_result_core = model_result[model_result['idxs'].isnull()].copy()
        print("model_result_core:\n'{}'".format(model_result_core))
        model_result_interface = model_result[model_result['idxs'].notnull()].copy()
        print("model_result_interface:\n'{}'".format(model_result_interface))
    else:
        model_result_core = model_result
        model_result_interface = pd.DataFrame()

    # Connect to DB
    connection = MySQLdb.connect(
        host='192.168.6.19', port=3306, user='elaspic-web', passwd='elaspic', db=DB_SCHEMA,
    )

    # CORE Upload
    format_columns(model_result_core, core_model_columns)

    model_result_core = drop_columns(model_result_core, core_model_columns)
    upload_data(connection, model_result_core, CORE_MODEL_TABLE)

    if model_result_interface.empty:
        connection.close()
        return

    # INTERFACE
    format_columns(model_result_interface, interface_model_columns)

    domain_id_lookup = get_domain_id_lookup(connection, unique_id)

    model_result_interface['domain_idx_1'] = (
        model_result_interface['idxs'].apply(lambda x: x[0])
    )
    model_result_interface['domain_idx_2'] = (
        model_result_interface['idxs'].apply(lambda x: x[1])
    )

    model_result_interface['domain_id_1'] = (
        model_result_interface[['protein_id_1', 'domain_idx_1']]
        .apply(lambda x: domain_id_lookup[tuple(x)], axis=1)
    )
    model_result_interface['domain_id_2'] = (
        model_result_interface[['protein_id_2', 'domain_idx_2']]
        .apply(lambda x: domain_id_lookup[tuple(x)], axis=1)
    )

    # Upload
    model_result_interface = drop_columns(model_result_interface, interface_model_columns)
    upload_data(connection, model_result_interface, INTERFACE_MODEL_TABLE)

    connection.close()
    return


# %% Mutation
def upload_mutation(unique_id, mutation, data_dir):
    """
    """
    print('upload_mutation({}, {}, {})'.format(unique_id, mutation, data_dir))
    #
    core_mutation_columns = dict(
        domain_id=None,
        protein_id=None,  # unique_id
        domain_idx=('idx', None),
        mutation=None,

        # mutation
        model_filename_wt=('model_file_wt', None),
        model_filename_mut=('model_file_mut', None),
        mutation_errors=('', lambda: None),
        chain_modeller=None,
        mutation_modeller=None,
        stability_energy_wt=None,
        stability_energy_mut=None,
        physchem_wt=None,
        physchem_wt_ownchain=None,
        physchem_mut=None,
        physchem_mut_ownchain=None,
        secondary_structure_wt=None,
        secondary_structure_mut=None,
        solvent_accessibility_wt=None,
        solvent_accessibility_mut=None,
        matrix_score=None,
        provean_score=None,
        ddg=None,
        mut_date_modified=('', lambda: time.strftime('%Y-%m-%d %H:%M:%S')),
    )
    interface_mutation_columns = dict(
        interface_id=None,
        # protein_id_1=None,
        # domain_id_1=None,
        # domain_idx_1=('idxs', lambda x: x[0]),
        # protein_id_2=None,
        # domain_id_2=None,
        # domain_idx_2=('idxs', lambda x: x[1]),
        protein_id=None,  # unique_id
        chain_idx=None,
        mutation=None,

        # mutation
        model_filename_wt=('model_file_wt', None),
        model_filename_mut=('model_file_mut', None),
        mutation_errors=('', lambda: None),
        chain_modeller=None,
        mutation_modeller=None,
        stability_energy_wt=None,
        stability_energy_mut=None,
        analyse_complex_energy_wt=None,
        analyse_complex_energy_mut=None,
        physchem_wt=None,
        physchem_wt_ownchain=None,
        physchem_mut=None,
        physchem_mut_ownchain=None,
        secondary_structure_wt=None,
        secondary_structure_mut=None,
        solvent_accessibility_wt=None,
        solvent_accessibility_mut=None,
        contact_distance_wt=None,
        contact_distance_mut=None,
        matrix_score=None,
        provean_score=None,
        ddg=None,
        mut_date_modified=('', lambda: time.strftime('%Y-%m-%d %H:%M:%S')),
    )
    # Load data
    mutation_result = pd.read_json(
        op.join(data_dir, '.elaspic', 'mutation_{}.json'.format(mutation)))
    print("mutation_result:\n'{}'".format(mutation_result))

    if 'idxs' in mutation_result.columns:
        mutation_result_core = mutation_result[mutation_result['idxs'].isnull()].copy()
        mutation_result_core['protein_id'] = unique_id
        print("mutation_result_core:\n'{}'".format(mutation_result_core))

        mutation_result_interface = mutation_result[mutation_result['idxs'].notnull()].copy()
        mutation_result_interface['protein_id'] = unique_id
        print("mutation_result_interface:\n'{}'".format(mutation_result_interface))
    else:
        mutation_result_core = mutation_result
        mutation_result_core['protein_id'] = unique_id
        print("mutation_result_core:\n'{}'".format(mutation_result_core))

        mutation_result_interface = pd.DataFrame()

    # Connect to DB
    connection = MySQLdb.connect(
        host='192.168.6.19', port=3306, user='elaspic-web', passwd='elaspic', db=DB_SCHEMA,
    )

    # CORE
    format_columns(mutation_result_core, core_mutation_columns)

    domain_id_lookup = get_domain_id_lookup(connection, unique_id)
    mutation_result_core['domain_id'] = (
        mutation_result_core[['protein_id', 'domain_idx']]
        .apply(lambda x: domain_id_lookup[tuple(x)], axis=1)
    )

    # Upload
    mutation_result_core = drop_columns(mutation_result_core, core_mutation_columns)
    upload_data(connection, mutation_result_core, CORE_MUTATION_TABLE)

    if mutation_result_interface.empty:
        finalize_mutation(connection, unique_id, mutation)
        connection.close()
        return

    # INTERFACE
    def get_chain_idx(x):
        idx, idxs = x
        if idx == idxs[0]:
            return 0
        elif idx == idxs[1]:
            return 1
        else:
            raise ValueError("idx '{}' not in idxs '{}'".format(idx, idxs))

    mutation_result_interface['chain_idx'] = (
        mutation_result_interface[['idx', 'idxs']].apply(get_chain_idx, axis=1)
    )
    format_columns(mutation_result_interface, interface_mutation_columns)

    interface_id_lookup = get_interface_id_lookup(connection, unique_id)

    # protein id
    mutation_result_interface['protein_id_1'] = unique_id
    mutation_result_interface['protein_id_2'] = unique_id
    # protein idx
    mutation_result_interface['domain_idx_1'] = (
        mutation_result_interface['idxs'].apply(lambda x: x[0])
    )
    mutation_result_interface['domain_idx_2'] = (
        mutation_result_interface['idxs'].apply(lambda x: x[1])
    )
    # domain id
    mutation_result_interface['domain_id_1'] = (
        mutation_result_interface[['protein_id_1', 'domain_idx_1']]
        .apply(lambda x: domain_id_lookup[tuple(x)], axis=1)
    )
    mutation_result_interface['domain_id_2'] = (
        mutation_result_interface[['protein_id_2', 'domain_idx_2']]
        .apply(lambda x: domain_id_lookup[tuple(x)], axis=1)
    )
    # interface id
    mutation_result_interface['interface_id'] = (
        mutation_result_interface
        [['domain_id_1', 'domain_id_2']]
        .apply(lambda x: interface_id_lookup[tuple(x)], axis=1)
    )

    # Upload
    mutation_result_interface = drop_columns(mutation_result_interface, interface_mutation_columns)
    upload_data(connection, mutation_result_interface, INTERFACE_MUTATION_TABLE)

    finalize_mutation(connection, unique_id, mutation)
    connection.close()
    return


# %%
if __name__ == '__main__':
    args = parse_args()
    validate_args(args)

    if args.run_type == 'sequence':
        upload_sequence(args.unique_id, args.data_dir)
    elif args.run_type == 'model':
        upload_model(args.unique_id, args.data_dir)
    elif args.run_type == 'mutations':
        for mutation in args.mutations.split(','):
            upload_mutation(args.unique_id, mutation, args.data_dir)
    else:
        raise RuntimeError('Incorrent run_type: {}'.format(args.run_type))
