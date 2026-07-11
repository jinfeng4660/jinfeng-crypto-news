import sys, json, re, requests
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

def fetch_calendar(proxies=None):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
    }
    url = 'https://www.forexfactory.com/calendar'
    resp = requests.get(url, headers=headers, proxies=proxies, timeout=15)
    if resp.status_code != 200:
        print(f'FF status {resp.status_code}')
        return []
    
    text = resp.text
    
    # Method: Extract the days array directly from calendarComponentStates[1]
    # Pattern: days: [...]
    match = re.search(r'(?<=days:\s)\[(.*?)\];', text, re.DOTALL)
    if not match:
        print('days array not found')
        return []
    
    raw = match.group(0)
    # This is the full array including the ]; terminator
    # Let's find exact boundaries
    idx = text.find('days: [')
    if idx < 0:
        return []
    
    start = idx + 6  # 'days: [' starts with '['
    # Find the matching ] that ends the days array
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
    print(f'Array extracted: {len(arr_js)} chars')
    
    # Now clean JS-isms and parse as JSON
    # 1. Remove trailing commas
    arr_js = re.sub(r',\s*([}\]])', r'\1', arr_js)
    # 2. Quote all property names (word: -> "word":)
    # But only outside of strings
    # Since the array is deeply nested and properly formatted, let's try json5
    try:
        import json5
        # For json5, Object.freeze should be the only issue, and that's outside the days array
        # Since we only extracted the days array, there shouldn't be Object.freeze
        days = json5.loads(arr_js)
        print(f'Parsed {len(days)} days')
        return days
    except:
        pass
    
    # Fallback: manual parse
    print('json5 failed, trying manual...')
    try:
        # Actually the raw array might still have Object.freeze in values
        # Let's check
        if 'Object.freeze' in arr_js:
            print('Object.freeze found inside days array!')
            # Strip all Object.freeze(...) calls
            arr_js = re.sub(r'Object\.freeze\(([^)]*)\)', r'\1', arr_js)
            arr_js = re.sub(r'Object\.freeze\(', '', arr_js)
            # Balance parentheses... too hard
            print('Attempting json5 after stripping...')
            try:
                import json5
                days = json5.loads(arr_js)
                print(f'Parsed {len(days)} days')
                return days
            except:
                pass
        # Try json5 anyway
        import json5
        days = json5.loads(arr_js)
        print(f'Parsed {len(days)} days')
        return days
    except Exception as e:
        print(f'Parse error: {e}')
        # Debug: show the problematic area
        arr_js = re.sub(r'Object\.freeze\(', '___FREEZE___', arr_js)
        print(f'First 2000 with freeze markers: {arr_js[:2000]}')
        return []

# Test
proxies = {'http': 'http://127.0.0.1:10020', 'https': 'http://127.0.0.1:10020'}
days = fetch_calendar(proxies)
if days:
    for d in days:
        dl = d.get('dateline', 0)
        dt = datetime.fromtimestamp(dl) if dl else None
        evs = d.get('events', [])
        if evs:
            print(f'{dt.strftime("%Y-%m-%d %A") if dt else ""}: {len(evs)} events')
            for ev in evs[:2]:
                imp = ev.get('impactName','')
                if imp in ('high','medium'):
                    print(f'  {ev.get("timeLabel","")} [{imp}] {ev.get("currency","")} {ev.get("name","")}')
