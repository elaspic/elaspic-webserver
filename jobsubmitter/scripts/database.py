#!/usr/bin/env python
import MySQLdb

connection = MySQLdb.connect(
    host='192.168.6.19', port=3306, user='elaspic-web', passwd='elaspic',
    db='elaspic_webserver_2',
)
try:
    with connection.cursor() as cur:
        cur.execute("CALL update_muts('${uniprot_id}', '${mutations}')")
        print('success')
finally:
    connection.close()
