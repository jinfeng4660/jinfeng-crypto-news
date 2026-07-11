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

# Skip to the brace
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

raw_js = text[brace_start:obj_end]
print(f'Raw: {len(raw_js)} chars')

# Convert JS object to valid JSON by quoting property names
# The format is: {days: [...], ...} -> {"days": [...], ...}
# Use regex to add quotes around unquoted property names
fixed = re.sub(r'(?<!")([{,]\s*)([a-zA-Z_$][a-zA-Z0-9_$]*)(\s*:)', r'\1"\2"\3', raw_js)
fixed = fixed.replace('\\/', '/')
print(f'Fixed: {len(fixed)} chars')

try:
    obj = json.loads(fixed)
except json.JSONDecodeError as e:
    print(f'JSON parse error: {e}')
    print(fixed[:500])
    sys.exit(1)

days = obj.get('days', [])
print(f'Days: {len(days)}')

total = 0
for day in days:
    if day.get('events'):
        total += len(day['events'])
print(f'Total events: {total}')

# Print all events for today and upcoming days
import datetime
now = datetime.datetime.now()
today_ts = int(datetime.datetime(now.year, now.month, now.day).timestamp())

for day in days:
    dl = day.get('dateline', 0)
    date_obj = datetime.datetime.fromtimestamp(dl)
    date_str = date_obj.strftime('%Y-%m-%d')
    evs = day.get('events', [])
    
    if dl < today_ts - 86400:
        continue  # skip past days
    
    importance = 'HIGH' if dl == today_ts else 'MEDIUM'
    if not evs:
        continue
    
    print(f'\n📅 {date_str} ({len(evs)} events)')
    for ev in evs:
        name = ev.get('name', '')
        tstr = ev.get('timeLabel', '')
        impact = ev.get('impactName', '')
        country = ev.get('country', '')
        currency = ev.get('currency', '')
        actual = ev.get('actual', '')
        prev = ev.get('previous', '')
        forecast = ev.get('forecast', '')
        imp_icon = '🔴' if impact == 'high' else '🟡' if impact == 'medium' else '⚪'
        print(f'  {tstr} {imp_icon} [{currency}] {name}')
        if actual or prev or forecast:
            print(f'       实际:{actual} 前值:{prev} 预测:{forecast}')
