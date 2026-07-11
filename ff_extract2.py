import sys, json, re, requests

sys.stdout.reconfigure(encoding='utf-8')

proxies = {'http': 'http://127.0.0.1:10020', 'https': 'http://127.0.0.1:10020'}
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
}
url = 'https://www.forexfactory.com/calendar'
resp = requests.get(url, headers=headers, proxies=proxies, timeout=15)
text = resp.text

# Find the state object
idx = text.find('calendarComponentStates[1] = {')
if idx < 0:
    print('not found')
    sys.exit(1)

# Start after the = {
brace_start = text.find('{', idx)
depth = 0
in_str = False
esc = False
obj_end = brace_start

for i in range(brace_start, len(text)):
    c = text[i]
    if esc:
        esc = False
        continue
    if c == '\\' and in_str:
        esc = True
        continue
    if c == '"' and not esc:
        in_str = not in_str
        continue
    if not in_str:
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                obj_end = i + 1
                break

raw_json = text[brace_start:obj_end]
print(f'Raw object: {len(raw_json)} chars')

# Clean escaped slashes
raw_json = raw_json.replace('\\/', '/')

try:
    obj = json.loads(raw_json)
    days = obj.get('days', [])
    print(f'Days: {len(days)}')
    
    total = 0
    for day in days:
        if day.get('events'):
            total += len(day['events'])
    print(f'Total events: {total}')
    
    # Print all days with events
    for day in days:
        date_str = day.get('date', '').replace('<span>', '').replace('</span>', '').strip()
        evs = day.get('events', [])
        print(f'\n=== {date_str} ({len(evs)} events) ===')
        for ev in evs[:5]:  # first 5 per day
            name = ev.get('name', 'N/A')
            time_str = ''
            if 'time' in ev:
                time_str = ev['time']
            elif 'dateline' in ev:
                import datetime
                time_str = datetime.datetime.fromtimestamp(ev['dateline']).strftime('%H:%M')
            impact = ev.get('impact', '')
            currency = ev.get('country', '')
            prev = ev.get('previous', '')
            forecast = ev.get('forecast', '')
            print(f'  {time_str} [{impact}] {currency} {name} (前值:{prev} 预测:{forecast})')
except Exception as e:
    print(f'Error: {e}')
    print(raw_json[:1000])
