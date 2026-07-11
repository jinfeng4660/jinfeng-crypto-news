import sqlite3, os
conn = sqlite3.connect(os.path.join(os.path.dirname(__file__), 'data', 'calendar_history.db'))
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print('Tables:', [t[0] for t in tables])
for t in tables:
    count = conn.execute(f'SELECT COUNT(*) FROM [{t[0]}]').fetchone()[0]
    print(f'  {t[0]}: {count} rows')
    if count > 0:
        sample = conn.execute(f'SELECT * FROM [{t[0]}] LIMIT 2').fetchall()
        print(f'    cols: {[d[0] for d in conn.execute(f"PRAGMA table_info([{t[0]}])").fetchall()]}')
        print(f'    first: {sample[0]}')
