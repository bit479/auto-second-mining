# -*- coding: utf-8 -*-
import pyodbc, os
files = [
 r"D:/WK/N CRT/北部山头3940平台2026/7、单日数据/北部山头3940平台-1008/2、3940平台炮孔数据库1008.mdb",
 r"D:/WK/N CRT/北部山头3940平台2026/2、北部山头3940平台炮孔数据库-2026.mdb",
]
for f in files:
    print("="*100)
    print("FILE:", f, "exists=", os.path.exists(f), "size=", os.path.getsize(f) if os.path.exists(f) else -1)
    dsn = r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=%s;" % f
    try:
        cn = pyodbc.connect(dsn)
    except Exception as e:
        print("  CONN ERR:", e); continue
    cur = cn.cursor()
    tables = [r.table_name for r in cur.tables(tableType='TABLE')]
    print("  tables:", tables)
    for t in tables:
        try:
            cur.execute("SELECT COUNT(*) FROM [%s]" % t)
            n = cur.fetchone()[0]
        except Exception as e:
            n = "ERR %s" % e
        cols = [(c.column_name, c.type_name, c.column_size) for c in cur.columns(table=t)]
        print("  --- table [%s] rows=%s" % (t, n))
        print("      cols:", cols)
        try:
            cur.execute("SELECT TOP 3 * FROM [%s]" % t)
            for row in cur.fetchall():
                print("      ", [str(v) for v in row])
        except Exception as e:
            print("      sample ERR", e)
    cn.close()
