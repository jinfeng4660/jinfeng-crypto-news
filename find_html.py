import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('scripts/main.py', 'r', encoding='utf-8') as f:
    t = f.read()
idx = t.find("html = f'''")
print('html start at', idx)
idx2 = t.find("'''", idx + 10)
print('html end at', idx2)
lines = t[:idx].count('\n') + 1
print('html f-string starts at line', lines)
