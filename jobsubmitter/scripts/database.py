#!/usr/bin/env python
import MySQLdb
import argparse


def parse_args():
    """
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--uniprot_id')
    parser.add_argument('-m', '--mutations')
    parser.add_argument('-t', '--run_type')
    args = parser.parse_args()
    return args


def upload_mutation(uniprot_id, mutation):
    connection = MySQLdb.connect(
        host='192.168.6.19', port=3306, user='elaspic-web', passwd='elaspic',
        db='elaspic_webserver_2',
    )
    try:
        with connection.cursor() as cur:
            cur.execute("CALL update_muts('{}', '{}');".format(uniprot_id, mutation))
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
        raise RuntimeError('Incorrent run_type: {}'.format(args.run_type))
