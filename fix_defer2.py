import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('scripts/main.py','r',encoding='utf-8') as f:
    t = f.read()
old = 'window.addEventListener(' + chr(39) + 'load' + chr(39) + ',function(){renderCards(DATA)})'
new = 'renderCards(DATA)'
t = t.replace(old, new)
with open('scripts/main.py','w',encoding='utf-8') as f:
    f.write(t)
print('reverted renderCards to direct call')
