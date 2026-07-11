import sys, json, re, requests
from datetime import datetime
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
brace = text.find('{', idx)
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

js = text[brace:end].replace('\\/', '/')
print(f'JS extracted: {len(js)} chars')
print(f'First 300: {js[:300]}')
print()
print(f'Last 200: {js[-200:]}')

# Find the rogue character - search for 'O' outside strings
# The error says column 22 of line 8 - let's check
lines = js.split('\n')
for i, line in enumerate(lines):
    if i >= 12: break
    print(f'Line {i+1} ({len(line)}): {line[:100]}')
