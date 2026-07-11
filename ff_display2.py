import sys, json, datetime
sys.stdout.reconfigure(encoding='utf-8')
with open('ff_calendar.json', 'r') as f:
    days = json.load(f)

now = datetime.datetime.now()
today_ts = int(datetime.datetime(now.year, now.month, now.day).timestamp())

for day in days:
    dl = day.get('dateline', 0)
    dt = datetime.datetime.fromtimestamp(dl)
    evs = day.get('events', [])
    is_today = dl == today_ts
    marker = ' <<< TODAY' if is_today else ''
    high = sum(1 for e in evs if e.get('impactName') == 'high')
    med = sum(1 for e in evs if e.get('impactName') == 'medium')
    print(f'{dt.strftime("%Y-%m-%d")} [{dl}] ev={len(evs)} high={high} med={med}{marker}')
