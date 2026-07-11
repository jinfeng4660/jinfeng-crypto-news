import re

with open('docs/calendar.html', 'r', encoding='utf-8') as f:
    content = f.read()

script_start = content.index('<script>') + 8
script_end = content.index('</script>')
js = content[script_start:script_end]

print(f"JS length: {len(js)}")
print(f"var TITLE_CN count: {js.count('var TITLE_CN =')}")
print(f"function t count: {js.count('function t(')}")
print(f"Has renderCalendar: {'function renderCalendar' in js}")
print(f"Has renderCalEvent: {'function renderCalEvent' in js}")

# Check {{ pattern
import re
curly_pairs = re.findall(r'\{\{.*?\}\}', js)
if curly_pairs:
    print(f"Found {{ }} pairs: {len(curly_pairs)}")
    for cp in curly_pairs[:3]:
        print(f"  {cp[:80]}")
else:
    print("No {{ }} patterns")

# Find the problem - last 500 chars
print(f"\nLast 500 chars:\n{js[-500:]}")
