import re

with open('docs/index.html','r',encoding='utf-8') as f:
    c=f.read()

# Version app.js
c = re.sub(r'src="(\./)?app\.js(\?[^"]*)?', 'src="./app.js?v=2.0', c)

# Version index.html itself - add meta to prevent caching
if 'meta http-equiv="cache-control"' not in c:
    c = c.replace('<head>', '<head>\n<meta http-equiv="cache-control" content="no-cache, no-store, must-revalidate">\n<meta http-equiv="pragma" content="no-cache">\n<meta http-equiv="expires" content="0">')

with open('docs/index.html','w',encoding='utf-8') as f:
    f.write(c)
print('Done')

# Also check calendar.html
with open('docs/calendar.html','r',encoding='utf-8') as f:
    c=f.read()

if 'meta http-equiv="cache-control"' not in c:
    c = c.replace('<head>', '<head>\n<meta http-equiv="cache-control" content="no-cache, no-store, must-revalidate">\n<meta http-equiv="pragma" content="no-cache">\n<meta http-equiv="expires" content="0">')
    with open('docs/calendar.html','w',encoding='utf-8') as f:
        f.write(c)
print('calendar.html also updated')
