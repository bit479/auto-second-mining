# -*- coding: utf-8 -*-
import pyodbc
f = r"D:/WK/N CRT/北部山头3940平台2026/2、北部山头3940平台炮孔数据库-2026.mdb"
cn = pyodbc.connect(r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=%s;" % f)
cur = cn.cursor()
for t in ['定位表','测斜表','pit_blast']:
    print("=== table", t)
    for st in cur.statistics(table=t):
        print("   idx:", st.index_name, "unique=", st.unique, "col=", st.column_name)
    try:
        print("   pkeys:", [(p.column_name, p.key_seq) for p in cur.primaryKeys(table=t)])
    except Exception as e:
        print("   pkeys ERR", e)
cn.close()
