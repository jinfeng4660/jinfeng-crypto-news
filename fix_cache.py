import sys
import time
sys.stdout.reconfigure(encoding='utf-8')
with open('scripts/main.py','r',encoding='utf-8') as f:
    t = f.read()
old = '<script src="app.js"'
ts = int(time.time())
new = '<script src="app.js?v=' + str(ts) + '"'
t = t.replace(old, new)
with open('scripts/main.py','w',encoding='utf-8') as f:
    f.write(t)
print('cache buster added:', ts)
