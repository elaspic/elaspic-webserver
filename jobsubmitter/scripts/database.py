#!/usr/bin/env python
import MySQLdb
import argparse

DB_SCHEMA = 'elaspic_webserver'

SQL_COMMAND = """\
LOCK TABLES muts AS web_muts WRITE,
            elaspic_core_mutation AS ecm READ,
            elaspic_core_mutation_local AS ecml READ,
            elaspic_interface_mutation AS eim READ,
            elaspic_interface_mutation_local eiml READ;

UPDATE muts web_muts
LEFT JOIN elaspic_core_mutation ecm ON (
    web_muts.protein = ecm.protein_id and web_muts.mut = ecm.mutation)
LEFT JOIN elaspic_core_mutation_local ecml ON (
    web_muts.protein = ecml.protein_id and web_muts.mut = ecml.mutation)
SET web_muts.affectedType='CO', web_muts.status='error', web_muts.dateFinished = now(),
    web_muts.error='1: ddG not calculated'
WHERE web_muts.protein = '{protein_id}' and web_muts.mut = '{mutation}' AND
      ecm.ddg IS NULL AND ecml.ddg IS NULL;

UPDATE muts web_muts
LEFT JOIN elaspic_core_mutation ecm ON (
    web_muts.protein = ecm.protein_id and web_muts.mut = ecm.mutation)
LEFT JOIN elaspic_core_mutation_local ecml ON (
    web_muts.protein = ecml.protein_id and web_muts.mut = ecml.mutation)
SET web_muts.affectedType='CO', web_muts.status='done', web_muts.dateFinished = now(),
    web_muts.error=Null
WHERE web_muts.protein = '{protein_id}' and web_muts.mut = '{mutation}' AND
    (ecm.ddg IS NOT NULL OR ecml.ddg IS NOT NULL);

UPDATE muts web_muts
LEFT JOIN elaspic_interface_mutation eim ON (
    web_muts.protein = eim.protein_id and web_muts.mut = eim.mutation)
LEFT JOIN elaspic_interface_mutation_local eiml ON (
    web_muts.protein = eiml.protein_id and web_muts.mut = eiml.mutation)
SET web_muts.affectedType='IN', web_muts.status='done', web_muts.dateFinished = now(),
    web_muts.error=Null
WHERE web_muts.protein = '{protein_id}' and web_muts.mut = '{mutation}' AND
    (eim.ddg IS NOT NULL OR eiml.ddg IS NOT NULL);

UNLOCK TABLES;
"""


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--uniprot_id')
    parser.add_argument('-m', '--mutations')
    parser.add_argument('-t', '--run_type')
    args = parser.parse_args()
    return args


def upload_mutation(uniprot_id, mutation):
    connection = MySQLdb.connect(
        host='192.168.6.19', port=3306, user='elaspic-web', passwd='elaspic', db=DB_SCHEMA,
    )
    try:
        with connection.cursor() as cur:
            cur.execute(SQL_COMMAND.format(protein_id=uniprot_id, mutation=mutation))
        connection.commit()
        print('Success!')
    finally:
        connection.close()


if __name__ == '__main__':
    args = parse_args()
    if args.run_type == 'mutations':
        for mutation in args.mutations.split(','):
            upload_mutation(args.uniprot_id, mutation)
    else:
        print(
            "This script is only applicable for run_type == 'mutations'!\n"
            "(args = '{}')".format(args))
