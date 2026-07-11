import urllib.request, re

url='https://jinfeng4660.github.io/jinfeng-crypto-news/index.html'
req=urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0','Cache-Control':'no-cache'})
t=urllib.request.urlopen(req,timeout=15).read().decode('utf-8','ignore')

print('Page length:', len(t))

m=re.search(r'src="(\./)?app\.js(\?[^"]*)?', t)
print('app.js src:', m.group(0) if m else 'NOT FOUND')

# Check sidebar
if '打开完整日历' in t:
    print('完整日历链接: YES')
else:
    print('完整日历链接: NO - old sidebar')
    # What's in the sidebar section?
    cal_idx = t.find('财经日历')
    if cal_idx > 0:
        print(f'Sidebar context: ...{t[cal_idx:cal_idx+300]}...')

# Chain data
print('CHAIN_DATA in page:', 'YES' if 'CHAIN_DATA' in t else 'NO')
print('openChainPanel in page:', 'YES' if 'openChainPanel' in t else 'NO')
print('renderCalendar in page:', 'YES' if 'renderCalendar' in t else 'NO')
print('NO-CACHE header:', 'YES' if 'no-cache' in t else 'NO')

# Check cache headers
print('\n--- Response headers ---')
for k,v in req.headers.items():
    print(f'{k}: {v}')
