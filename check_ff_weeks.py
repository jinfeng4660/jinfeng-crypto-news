import requests, sys, re
sys.stdout.reconfigure(encoding='utf-8')
proxies = {'http': 'http://127.0.0.1:10020', 'https': 'http://127.0.0.1:10020'}
resp = requests.get('https://www.forexfactory.com/calendar', headers={'User-Agent': 'Mozilla/5.0'}, proxies=proxies, timeout=20)
text = resp.text

# Count 'days:' occurrences with context
idxs = [m.start() for m in re.finditer(r'days:\s*\[', text)]
print(f"Found {len(idxs)} 'days:' in page")

for i, idx in enumerate(idxs[:10]):
    # show context around this occurrence
    ctx_before = text[max(0,idx-80):idx]
    ctx_after = text[idx:idx+100]
    # Get componentStates index
    cs_match = re.search(r'calendarComponentStates\[(\d+)\]', ctx_before)
    if cs_match:
        print(f"  [{i}] calendarComponentStates[{cs_match.group(1)}]: {ctx_after[:80]}...")
    else:
        print(f"  [{i}] (unknown): ...{ctx_after[:60]}...")

# Check if there's a date filter or navigation parameter
print("\n--- Checking URL params ---")
# Try with different date
for date_param in ['2026-06-01', '2026-06-15', '2026-07-06']:
    url2 = f'https://www.forexfactory.com/calendar?date={date_param}'
    r2 = requests.get(url2, headers={'User-Agent': 'Mozilla/5.0'}, proxies=proxies, timeout=20)
    count = len(re.findall(r'days:\s*\[', r2.text))
    print(f"  {url2}: {count} days: arrays, page size {len(r2.text)} bytes")
