import sys
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3, json
from datetime import datetime

db = sqlite3.connect('data/calendar_history.db')
cur = db.cursor()
cur.execute("SELECT COUNT(*), MIN(date), MAX(date) FROM calendar_events")
cnt, mn, mx = cur.fetchone()
print(f'Total events: {cnt}, date range: {mn} ~ {mx}')
cur.execute("SELECT date, COUNT(*) FROM calendar_events GROUP BY date ORDER BY date")
rows = cur.fetchall()
for r in rows:
    print(f'  {r[0]}: {r[1]} events')
db.close()
