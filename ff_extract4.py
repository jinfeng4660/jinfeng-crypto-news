import sys, json, re, requests

sys.stdout.reconfigure(encoding='utf-8')

proxies = {'http': 'http://127.0.0.1:10020', 'https': 'http://127.0.0.1:10020'}
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
}
url = 'https://www.forexfactory.com/calendar'
resp = requests.get(url, headers=headers, proxies=proxies, timeout=15)
text = resp.text

# Use a different approach: extract the JSON-like array from the script using regex
# Look for: days: [{ ... }]
match = re.search(r'(?<=days:\s)\[\s*\{', text)
if not match:
    print('Could not find days array start')
    sys.exit(1)

start = match.start()
depth = 0
in_str = False
esc = False
arr_end = start

for i in range(start, len(text)):
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
        if c == '[':
            depth += 1
        elif c == ']':
            depth -= 1
            if depth == 0:
                arr_end = i + 1
                break

raw_arr = text[start:arr_end].replace('\\/', '/')
print(f'Array: {len(raw_arr)} chars')

# Convert to valid JSON: it's a JS array where prop names are unquoted
# We only need to quote the TOP LEVEL property names inside each event object
# Actually, let's use a proper JS parser - eval in python-like approach
# Simplest: wrap in a JS object and use demjson3 or similar
# But let's try: clean approach - use the JSON5 library
try:
    import json5
    obj = json5.loads('{"days":' + raw_arr + '}')
    days = obj.get('days', [])
except ImportError:
    # Fallback: use Python's ast.literal_eval approach won't work for JS
    print('json5 not available, trying another approach')
    
    # Replace unquoted property names at all levels
    # Pattern: word followed by colon, where word is not already quoted and not a value
    # More careful regex
    def fix_js_keys(js_str):
        # Quote all JS property names that aren't already quoted
        # Match word: pattern where word is standalone
        result = re.sub(r'(?<=[{,])\s*([a-zA-Z_$][a-zA-Z0-9_$]*)\s*:', r'"\1":', js_str)
        return result
    
    fixed = fix_js_keys(raw_arr)
    # Try to find issue
    try:
        obj = json.loads('{"days":' + fixed + '}')
        days = obj.get('days', [])
    except json.JSONDecodeError as e:
        print(f'Still failing at offset {e.pos}')
        print(fixed[max(0,e.pos-100):e.pos+100])
        sys.exit(1)

print(f'Days: {len(days)}')

# Save to file for reference
with open('ff_calendar.json', 'w', encoding='utf-8') as f:
    json.dump(days, f, ensure_ascii=False, indent=2)
    print('Saved to ff_calendar.json')

total = sum(len(d.get('events', [])) for d in days)
print(f'Total events: {total}')

import datetime
now = datetime.datetime.now()
today_start = datetime.datetime(now.year, now.month, now.day)
today_ts = int(today_start.timestamp())

# Filter events from today onwards (skip past)
today_idx = None
for i, day in enumerate(days):
    dl = day.get('dateline', 0)
    if dl >= today_ts:
        today_idx = i
        break

if today_idx is None:
    print('No upcoming days found')
    sys.exit(1)

print(f'\n=== CALENDAR FROM TODAY ===')
shown = 0
for i in range(today_idx, len(days)):
    day = days[i]
    dl = day.get('dateline', 0)
    date_obj = datetime.datetime.fromtimestamp(dl)
    date_str = date_obj.strftime('%Y-%m-%d')
    weekday_cn = ['一','二','三','四','五','六','日'][date_obj.weekday()]
    evs = day.get('events', [])
    
    if not evs:
        continue
    
    print(f'\n📅 {date_str} 星期{weekday_cn} ({len(evs)} events)')
    for ev in evs:
        name = ev.get('name', '')
        tstr = ev.get('timeLabel', '')
        impact = ev.get('impactName', '')
        currency = ev.get('currency', '')
        actual = ev.get('actual', '')
        prev = ev.get('previous', '')
        forecast = ev.get('forecast', '')
        imp_icon = '🔴' if impact == 'high' else '🟡' if impact == 'medium' else '⚪'
        print(f'  {tstr} {imp_icon} [{currency}] {name}')
        if actual or prev or forecast:
            print(f'       实:{actual} 前:{prev} 预:{forecast}')
        shown += 1
        if shown >= 60:  # limit display
            break
    if shown >= 60:
        print('\n...(truncated, showing first 60 events)')
        break
