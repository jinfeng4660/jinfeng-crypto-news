import sys, json, re, requests

sys.stdout.reconfigure(encoding='utf-8')

proxies = {'http': 'http://127.0.0.1:10020', 'https': 'http://127.0.0.1:10020'}
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,*/*',
}

url = 'https://www.forexfactory.com/calendar'
resp = requests.get(url, headers=headers, proxies=proxies, timeout=15)
text = resp.text
print('Status:', resp.status_code)
print('Length:', len(text))

# Extract the JSON data from the calendarComponentStates
# Pattern: window.calendarComponentStates = ...
idx = text.find('window.calendarComponentStates')
if idx < 0:
    print('Could not find calendarComponentStates')
    sys.exit(1)

# Find the JSON array/object
start = text.find('[{', idx)
if start < 0:
    start = text.find('[', idx)
    
# Find the end of the variable assignment
semi = text.find(';', idx)
if semi > 0:
    js_part = text[idx:semi]
else:
    js_part = text[idx:idx+5000]

print(f'Found at idx={idx}, start={start}')
print('Raw snippet:', repr(js_part[:300]))
print('---')

# Try extracting the array directly
# Pattern: calendarComponentStates = [ ... ];
state_start = js_part.find('= [')
if state_start < 0:
    state_start = js_part.find('= [')
    
if state_start > 0:
    arr_start = idx + state_start + 2  # skip '= '
    # Find matching bracket
    depth = 0
    arr_end = arr_start
    in_str = False
    esc = False
    for i in range(arr_start, len(text)):
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
    
    arr_json = text[arr_start:arr_end]
    print(f'Array found: {len(arr_json)} chars')
    
    try:
        data = json.loads(arr_json)
        print(f'Parsed: {len(data)} days of data')
        
        total_events = 0
        for day in data:
            if 'events' in day:
                total_events += len(day['events'])
        print(f'Total events: {total_events}')
        
        # Show first event
        if data and 'events' in data[0] and len(data[0]['events']) > 0:
            ev = data[0]['events'][0]
            print(f'Sample event keys: {list(ev.keys())[:15]}')
            print(f'Sample: {json.dumps(ev, indent=2, ensure_ascii=False)[:500]}')
            
    except json.JSONDecodeError as e:
        print(f'JSON parse error: {e}')
        print(arr_json[:2000])
        print('---')
        print(arr_json[-200:])
