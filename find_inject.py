import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('scripts/main.py', 'r', encoding='utf-8') as f:
    t = f.read()

# Find the script tag with renderCards
idx = t.find('renderCards(DATA)')
print('Context around renderCards(DATA):')
print(repr(t[max(0,idx-100):idx+50]))
print()
print('===')
# Find where articles_json is generated
idx2 = t.find('articles_json = json.dumps')
print('articles_json assignment:')
print('  ...', repr(t[idx2-10:idx2+100]))
print()
# Find end of articles_json
idx3 = t.find('''; renderCards(DATA)''')
print('Before the final script block:', repr(t[idx3-20:idx3+40]))
