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
print('---')

# Look for data patterns
# Forex Factory embeds data as JSON in script tags or as HTML attributes
# Check for data-calendar or __NEXT_DATA__ or __INITIAL_STATE__
for keyword in ['__NEXT_DATA__', '__INITIAL_STATE__', 'window.__INITIAL', '__NUXT__', '"events"', '"calendar"', 'calendar__row']:
    idx = text.find(keyword)
    if idx > -1:
        print(f'Found "{keyword}" at offset {idx}')
        print(text[idx:idx+300])
        print('---')
    else:
        print(f'Not found: {keyword}')

# Check script tags
import re
scripts = re.findall(r'<script[^>]*>([\s\S]*?)</script>', text)
print(f'Total script tags: {len(scripts)}')
for i, s in enumerate(scripts):
    if len(s) > 1000:
        print(f'  Script {i}: {len(s)} chars, starts: {s[:100]}')
