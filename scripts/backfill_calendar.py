"""从FF按月提取所有事件并存入SQLite"""
import requests, re, json5, sys, sqlite3, hashlib, os
from datetime import datetime, timedelta
sys.stdout.reconfigure(encoding='utf-8')
proxies = {'http': 'http://127.0.0.1:10020', 'https': 'http://127.0.0.1:10020'}
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, 'data', 'calendar_history.db')

os.makedirs(os.path.dirname(DB), exist_ok=True)
conn = sqlite3.connect(DB)
conn.executescript("""
CREATE TABLE IF NOT EXISTS calendar_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ev_key TEXT UNIQUE NOT NULL,
    date TEXT NOT NULL,
    weekday TEXT,
    time TEXT,
    impact TEXT,
    currency TEXT,
    title TEXT,
    actual TEXT DEFAULT '',
    previous TEXT DEFAULT '',
    forecast TEXT DEFAULT '',
    ai_analysis TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_cal_date ON calendar_events(date);
""")

def ev_key(ev):
    raw = f'{ev.get("date","")}|{ev.get("title","")}|{ev.get("currency","")}'
    return hashlib.md5(raw.encode()).hexdigest()

def extract_events_from_page(text):
    idx = text.find('days: [')
    if idx < 0:
        return []
    start = idx + 6
    depth = 0
    in_str = False
    esc = False
    end = start
    for i in range(start, len(text)):
        c = text[i]
        if esc: esc = False; continue
        if c == '\\' and in_str: esc = True; continue
        if c == '"' and not esc: in_str = not in_str; continue
        if not in_str:
            if c == '[': depth += 1
            elif c == ']': depth -= 1
            if depth == 0: end = i + 1; break
    arr_js = text[start:end].replace('\\/', '/')
    days = json5.loads(arr_js)
    return days

def days_to_events(days):
    events = []
    now_ts = int(datetime.now().timestamp())
    today_ts = int(datetime(datetime.now().year, datetime.now().month, datetime.now().day).timestamp())
    
    for day in days:
        dl = day.get('dateline', 0)
        if not dl:
            continue
        dt = datetime.fromtimestamp(dl)
        date_str = dt.strftime('%Y-%m-%d')
        weekday_cn = ['一','二','三','四','五','六','日'][dt.weekday()]
        is_today = (abs(dl - today_ts) < 86400)
        
        for ev in day.get('events', []):
            impact = ev.get('impactName', 'low')
            if impact not in ('high', 'medium'):
                continue
            tstr = ev.get('timeLabel', '') or ev.get('time', '') or ''
            events.append({
                'source': 'forexfactory',
                'date': date_str,
                'weekday': weekday_cn,
                'isToday': is_today,
                'time': tstr,
                'impact': impact,
                'currency': ev.get('currency', ''),
                'title': ev.get('name', ''),
                'actual': ev.get('actual', '') or '',
                'previous': ev.get('previous', '') or '',
                'forecast': ev.get('forecast', '') or '',
            })
    return events

# Collect past 2 months + current month
months = []
now = datetime.now()
for offset in [-2, -1, 0, 1]:
    m = now.month + offset
    y = now.year
    while m < 1:
        m += 12
        y -= 1
    while m > 12:
        m -= 12
        y += 1
    months.append(f'{y}-{m:02d}')

for month_key in months:
    y, m = month_key.split('-')
    month_names = ['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec']
    mn = month_names[int(m)-1]
    url = f'https://www.forexfactory.com/calendar?month={mn}.{y}'
    print(f'\nFetching {url}...', end=' ')
    
    try:
        resp = requests.get(url, headers=headers, proxies=proxies, timeout=30)
        if resp.status_code != 200:
            print(f'HTTP {resp.status_code}')
            continue
        days = extract_events_from_page(resp.text)
        if not days:
            print('no days data')
            continue
        events = days_to_events(days)
        print(f'{len(events)} events')
        
        added = 0; updated = 0
        for ev in events:
            key = ev_key(ev)
            cur = conn.cursor()
            cur.execute("SELECT id FROM calendar_events WHERE ev_key=?", (key,))
            row = cur.fetchone()
            if row:
                cur.execute("UPDATE calendar_events SET actual=?, previous=?, forecast=?, updated_at=CURRENT_TIMESTAMP WHERE ev_key=?", 
                          (ev.get('actual',''), ev.get('previous',''), ev.get('forecast',''), key))
                updated += 1
            else:
                cur.execute("INSERT INTO calendar_events (ev_key, date, weekday, time, impact, currency, title, actual, previous, forecast) VALUES (?,?,?,?,?,?,?,?,?,?)",
                          (key, ev.get('date',''), ev.get('weekday',''), ev.get('time',''), ev.get('impact',''), ev.get('currency',''), ev.get('title',''), ev.get('actual',''), ev.get('previous',''), ev.get('forecast','')))
                added += 1
        print(f'  SQLite: +{added} new, {updated} updated')
    except Exception as e:
        print(f'ERROR: {e}')

conn.commit()
total = conn.execute("SELECT COUNT(*) FROM calendar_events").fetchone()[0]
print(f'\nTotal in DB: {total} events')

# Show date range
dates = conn.execute("SELECT MIN(date), MAX(date) FROM calendar_events").fetchone()
print(f'Date range: {dates[0]} ~ {dates[1]}')

conn.close()
