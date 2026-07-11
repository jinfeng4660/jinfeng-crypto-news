import sys, json, requests, re

sys.stdout.reconfigure(encoding='utf-8')
proxies = {'http': 'http://127.0.0.1:10020', 'https': 'http://127.0.0.1:10020'}
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
}

# Forex Factory uses ?day parameter for specific date
# Let's try to get next week's data starting from Monday Jul 13
url = 'https://www.forexfactory.com/calendar?day=2026-07-13'
resp = requests.get(url, headers=headers, proxies=proxies, timeout=15)
text = resp.text
print(f'Status: {resp.status_code}, len={len(text)}')

# Find calendarComponentStates
import json5
parts = re.findall(r'calendarComponentStates\[\d+\]\s*=\s*({.*?});\s*$', text, re.MULTILINE | re.DOTALL)
print(f'Found {len(parts)} state objects')

if parts:
    for pi, part in enumerate(parts):
        try:
            obj = json5.loads(part)
            days = obj.get('days', [])
            print(f'  Part {pi}: {len(days)} days')
            for d in days:
                dl = d.get('dateline', 0)
                ev = len(d.get('events', []))
                import datetime
                dt = datetime.datetime.fromtimestamp(dl) if dl else None
                ds = dt.strftime('%Y-%m-%d %A') if dt else 'N/A'
                print(f'    {ds} events={ev}')
        except:
            print(f'  Part {pi}: parse error')
