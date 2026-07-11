import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('scripts/main.py', 'r', encoding='utf-8-sig') as f:
    compile(f.read(), 'main.py', 'exec')
print('main.py: OK')
