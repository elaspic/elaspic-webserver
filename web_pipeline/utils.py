import os
from contextlib import contextmanager
from typing import Dict, List


def construct_mut_dbs_html(databases: List[Dict]) -> str:
    if databases:
        mut_dbs_html = f"Mutation in database{'s' if len(databases) > 1 else ''}: "
        for i, db in enumerate(databases):
            if i > 0:
                mut_dbs_html += ", "
            mut_dbs_html += '<a target="_blank" href="' + db["url"] + '">' + db["name"] + "</a>"
    else:
        mut_dbs_html = "Mutation run by user"
    return mut_dbs_html


@contextmanager
def set_umask(umask=0o002):
    original_umask = os.umask(umask)
    try:
        yield
    finally:
        os.umask(original_umask)
