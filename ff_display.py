import sys, json, datetime

sys.stdout.reconfigure(encoding='utf-8')

with open('ff_calendar.json', 'r', encoding='utf-8') as f:
    days = json.load(f)

now = datetime.datetime.now()
today_ts = int(datetime.datetime(now.year, now.month, now.day).timestamp())

# Weekday labels
wd_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
wd_cn = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

for day in days:
    dl = day.get('dateline', 0)
    dt = datetime.datetime.fromtimestamp(dl)
    ds = dt.strftime('%Y-%m-%d')
    evs = day.get('events', [])
    if dl < today_ts:
        continue
    if not evs:
        continue
    
    wd_idx = dt.weekday()
    print(f'\n===== {ds}  {wd_cn[wd_idx]} ({wd_names[wd_idx]}) =====')
    
    high_count = sum(1 for e in evs if e.get('impactName') == 'high')
    med_count = sum(1 for e in evs if e.get('impactName') == 'medium')
    low_count = sum(1 for e in evs if e.get('impactName') == 'low')
    print(f'  共{len(evs)}项 | 🔴{high_count} 🟡{med_count} ○{low_count}')
    
    for ev in evs:
        name = ev.get('name', '')
        tstr = ev.get('timeLabel', '') or ev.get('time', '')
        imp = ev.get('impactName', 'low')
        cur = ev.get('currency', '')
        
        act = ev.get('actual', '')
        prev = ev.get('previous', '')
        fcast = ev.get('forecast', '')
        
        imp_icon = '🔴' if imp == 'high' else '  🟡' if imp == 'medium' else '    ○'
        
        details = []
        if act: details.append('实:' + act)
        if prev: details.append('前:' + prev)
        if fcast: details.append('预:' + fcast)
        detail_str = ' | ' + ' '.join(details) if details else ''
        
        print(f'  {tstr or "??:??"} {imp_icon} [{cur}] {name}{detail_str}')
