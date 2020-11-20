from typing import List, Dict


def construct_mut_dbs_html(databases: List[Dict]) -> str:
    if databases:
        mut_dbs_html = f"Mutation in database{'s' if databases else ''}: "
        for i, db in enumerate(databases):
            if i > 0:
                mut_dbs_html += ", "
            mut_dbs_html += '<a target="_blank" href="' + db["url"] + '">' + db["name"] + "</a>"
    else:
        mut_dbs_html = "Mutation run by user"
    return mut_dbs_html
