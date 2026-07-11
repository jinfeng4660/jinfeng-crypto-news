"""尝试按周遍历Forex Factory历史日历"""
import requests, re, json5, sys
from datetime import datetime, timedelta
sys.stdout.reconfigure(encoding='utf-8')
proxies = {'http': 'http://127.0.0.1:10020', 'https': 'http://127.0.0.1:10020'}

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

# Try different URL patterns
patterns = [
    'https://www.forexfactory.com/calendar',
    'https://www.forexfactory.com/calendar?date=2026-07-06',
    'https://www.forexfactory.com/calendar?month=jul.2026',
]

for url in patterns:
    try:
        resp = requests.get(url, headers=headers, proxies=proxies, timeout=20)
        days_count = resp.text.count('days: [')
        size = len(resp.text)
        print(f'{url}: {resp.status_code}, {size} bytes, {days_count} "days:" occurrences')
        if days_count > 0:
            # show first componentStates context
            for m in re.finditer(r'calendarComponentStates\[(\d+)\]', resp.text):
                pos = m.start()
                ctx = resp.text[pos:pos+150]
                print(f'  State[{m.group(1)}]: {ctx[:80]}...')
    except Exception as e:
        print(f'{url}: ERROR {e}')

# Also try to check cookie/redirect behavior
resp = requests.get('https://www.forexfactory.com/calendar', headers=headers, proxies=proxies, timeout=20, allow_redirects=True)
print(f'\nMain page status: {resp.status_code}, history: {[r.url for r in resp.history]}')
print(f'Cookies: {dict(resp.cookies)}')
print(f'Page title match: {"calendar" in resp.text[:2000].lower()}')
print(f'Contains "days:": {"days:" in resp.text}')
