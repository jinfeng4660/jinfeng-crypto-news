import sys, json, datetime
sys.stdout.reconfigure(encoding='utf-8')
with open('ff_calendar.json', 'r') as f:
    days = json.load(f)
for d in days:
    dl = d.get('dateline', 0)
    dt = datetime.datetime.fromtimestamp(dl) if dl else None
    ds = dt.strftime('%Y-%m-%d %A') if dt else 'N/A'
    ev = len(d.get('events', []))
    print(f'  {ds}  events={ev}')
