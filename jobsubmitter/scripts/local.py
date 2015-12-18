#!/usr/bin/env python
import os
import os.path as op
import argparse
import json

import MySQLdb
import numpy as np
import pandas as pd

pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)


def parse_args():
    """
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--unique_id')
    parser.add_argument('-m', '--mutations')
    parser.add_argument('-t', '--run_type')
    parser.add_argument('-d', '--data_dir',  nargs='?', default=os.getcwd())
    args = parser.parse_args()
    return args


def validate_args(args):
    assert op.split(args.data_dir)[-1] == args.unique_id


def apply_notnull(df, column, fn):
    df.loc[df[column].notnull(), column] = df.loc[df[column].notnull(), column].apply(fn)


def upload_sequence(unique_id, data_dir):
    """
    """
    print('upload_sequence({}, {})'.format(unique_id, data_dir))
    db_columns = dict(
        unique_id=None,
        idx=None,
        protein_id=None,
        provean_supset_exists=int,
        provean_supset_file=None,
        provean_supset_length=None,
        sequence=None,
        sequence_file=None,
    )
    #
    sequence_result = pd.read_json(op.join(data_dir, 'sequence.json'))
    sequence_result['unique_id'] = unique_id
    for column, fn in db_columns.items():
        if fn is not None:
            apply_notnull(sequence_result, column, fn)
    sequence_result = sequence_result.drop(
        [c for c in sequence_result.columns if c not in db_columns], axis=1)
    sequence_result = sequence_result.where(sequence_result.notnull(), None)
    print(sequence_result)

    # Save to database
    connection = MySQLdb.connect(
        host='192.168.6.19', port=3306, user='elaspic-web', passwd='elaspic',
        db='elaspic_webserver_2',
    )
    try:
        with connection.cursor() as cur:
            db_command = (
                "replace into elaspic.local_sequence ({}) values ({});".format(
                    ','.join(sequence_result.columns),
                    ','.join(['%s' for _ in range(len(sequence_result.columns))]))
            )
            print(db_command)
            cur.executemany(db_command, args=list(sequence_result.to_records(index=False)))
        connection.commit()
    finally:
        connection.close()


def upload_model(unique_id, data_dir):
    """
    """
    print('upload_model({}, {})'.format(unique_id, data_dir))
    db_columns = dict(
        unique_id=None,
        chain_ids=','.join,
        idx=None,
        idx_2=None,
        interacting_residues_1=lambda x: ','.join(str(i) for i in x),
        interacting_residues_2=lambda x: ','.join(str(i) for i in x),
        interface_area_hydrophilic=None,
        interface_area_hydrophobic=None,
        interface_area_total=None,
        model_id=None,
        modeller_chain_ids=','.join,
        modeller_results=json.dumps,
        modeller_results_file=None,
        model_sequence_file=None,  # model.sequence_file
        model_sequence_id=None,  # model.sequence_id
        model_structure_file=None,  # model.structure_file
        model_structure_id=None,  # model.structure_id
        #
        core_or_interface=None,
        knotted=int,
        model_file=None,
        raw_model_file=None,
        sasa_score=lambda x: ','.join(str(f) for f in x),
        pir_alignment_file=None,
        #
        alignment_file=lambda x: x[0],  # alignment_files
        alignment_file_2=lambda x: x[1] if len(x) > 1 else None,  # alignment_files
        domain_def_offset=lambda x:
            ':'.join(str(i) for i in x[0]),  # domain_def_offsets
        domain_def_offset_2=lambda x:
            ':'.join(str(i) for i in x[1]) if len(x) > 1 else None,  # domain_def_offsets
    )

    #
    model_result = pd.read_json(op.join(data_dir, 'model.json'))
    model_result['unique_id'] = unique_id
    model_result['alignment_file'] = model_result['alignment_files']
    model_result['alignment_file_2'] = model_result['alignment_files']
    model_result['domain_def_offset'] = model_result['domain_def_offsets']
    model_result['domain_def_offset_2'] = model_result['domain_def_offsets']
    if 'idxs' in model_result.columns:
        model_result['idx_2'] = model_result['idxs'].apply(
            lambda x: x[1] if pd.notnull(x) and len(x) > 1 else -1)
    else:
        model_result['idx_2'] = -1

    for column in ['sequence_file', 'sequence_id', 'structure_file', 'structure_id']:
        model_result['model_' + column] = model_result[column]
    for column, fn in db_columns.items():
        if column in model_result.columns:
            if fn is not None:
                apply_notnull(model_result, column, fn)
        else:
            model_result[column] = None
    print(model_result)

    model_result = model_result.drop(
        [c for c in model_result.columns if c not in db_columns], axis=1)
    model_result = model_result.where(model_result.notnull(), None)

    # Save to database
    connection = MySQLdb.connect(
        host='192.168.6.19', port=3306, user='elaspic-web', passwd='elaspic',
        db='elaspic_webserver_2',
    )
    try:
        with connection.cursor() as cur:
            columns = ','.join(model_result.columns)
            db_command = (
                "replace into elaspic.local_model ({}) values ({});".format(
                    columns,
                    ','.join(['%s' for _ in range(len(model_result.columns))]))
            )
            cur.executemany(db_command, list(model_result.to_records(index=False)))
        connection.commit()
    finally:
        connection.close()


def upload_mutation(unique_id, mutation, data_dir):
    """
    """
    print('upload_mutation({}, {}, {})'.format(unique_id, mutation, data_dir))
    db_columns = dict(
        unique_id=None,
        idx=None,
        idx_2=None,
        mutation=None,
        alignment_coverage=None,
        alignment_identity=None,
        alignment_score=None,
        analyse_complex_energy_mut=None,
        analyse_complex_energy_wt=None,
        contact_distance_mut=None,
        contact_distance_wt=None,
        ddg=None,
        matrix_score=None,
        model_filename_mut=None,
        model_filename_wt=None,
        norm_dope=None,
        physchem_mut=None,
        physchem_mut_ownchain=None,
        physchem_wt=None,
        physchem_wt_ownchain=None,
        provean_score=None,
        secondary_structure_mut=None,
        secondary_structure_wt=None,
        solvent_accessibility_mut=None,
        solvent_accessibility_wt=None,
        stability_energy_mut=None,
        stability_energy_wt=None,
    )

    #
    mutation_result = pd.read_json(op.join(data_dir, 'mutation_{}.json'.format(mutation)))
    mutation_result['unique_id'] = unique_id
    mutation_result['mutation'] = mutation
    if 'idxs' in mutation_result.columns:
        mutation_result['idx_2'] = mutation_result['idxs'].apply(
            lambda x: x[1] if pd.notnull(x) and len(x) > 1 else -1)
    else:
        mutation_result['idx_2'] = -1

    for column, fn in db_columns.items():
        if fn is not None:
            apply_notnull(mutation_result, column, fn)
    mutation_result = mutation_result.drop(
        [c for c in mutation_result.columns if c not in db_columns], axis=1)
    mutation_result = mutation_result.where(mutation_result.notnull(), None)
    print(mutation_result)

    # Save to database
    connection = MySQLdb.connect(
        host='192.168.6.19', port=3306, user='elaspic-web', passwd='elaspic',
        db='elaspic_webserver_2',
    )
    try:
        with connection.cursor() as cur:
            # core
            columns = ','.join(mutation_result.columns)
            db_command = (
                "replace into elaspic.local_mutation ({}) values ({});".format(
                    columns,
                    ','.join(['%s' for _ in range(len(mutation_result.columns))]))
            )
            cur.executemany(db_command, list(mutation_result.to_records(index=False)))
        connection.commit()
    finally:
        connection.close()


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
