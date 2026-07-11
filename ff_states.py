import sys, json, requests, re

sys.stdout.reconfigure(encoding='utf-8')
proxies = {'http': 'http://127.0.0.1:10020', 'https': 'http://127.0.0.1:10020'}
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
}

# The page uses calendarComponentStates[1] for main week, check other indices
url = 'https://www.forexfactory.com/calendar'
resp = requests.get(url, headers=headers, proxies=proxies, timeout=15)
text = resp.text

# Find all state objects with their content
import json5

# Find all calendarComponentStates assignments
index = 0
while True:
    pattern = 'calendarComponentStates[' + str(index) + '] = {'
    idx = text.find(pattern)
    if idx < 0:
        break
    # Extract the full object
    brace = text.find('{', idx + len(pattern) - 1)
    depth = 0
    in_str = False
    esc = False
    end = brace
    for i in range(brace, len(text)):
        c = text[i]
        if esc: esc = False; continue
        if c == '\\' and in_str: esc = True; continue
        if c == '"' and not esc: in_str = not in_str; continue
        if not in_str:
            if c == '{': depth += 1
            elif c == '}': depth -= 1
            if depth == 0: end = i + 1; break
    js = text[brace:end]
    
    try:
        obj = json5.loads(js)
        days = obj.get('days', [])
        total_ev = sum(len(d.get('events', [])) for d in days)
        import datetime
        for d in days:
            dl = d.get('dateline', 0)
            dt = datetime.datetime.fromtimestamp(dl) if dl else None
            ds = dt.strftime('%Y-%m-%d %A') if dt else 'N/A'
            ev = len(d.get('events', []))
            high = sum(1 for e in d.get('events', []) if e.get('impactName') == 'high')
            print(f'  {ds}  ev={ev}  high={high}')
        print(f'  [State {index}: {len(days)} days, {total_ev} events]')
    except Exception as e:
        print(f'  [State {index}: error: {str(e)[:50]}]')
    
    index += 1
    
    if index > 5:
        break
