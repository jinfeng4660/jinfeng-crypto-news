import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('scripts/calendar_page.py','r',encoding='utf-8') as f:
    text = f.read()

# Find the string segments in the html assignment
idx = text.find("html = f'''")
print(f'html assignment starts at {idx} ({text[:idx].count(chr(10))+1})')

# Find the end - the final '''
end_idx = text.rfind("\"\"\"")
print(f'Possible end at {end_idx}')
# Actually find the closing ''' of html
after = text[idx+9:]  # after "html = f'''"
closing = after.find("'''")
print(f'First closing: {idx+9+closing}')
# But there might be inner ''' from string concatenation
# Let's find all ''' after the start
import re
matches = list(re.finditer(r"'''", text[idx:]))
for m in matches:
    pos = idx + m.start()
    line_no = text[:pos].count('\n') + 1
    context_before = text[max(0,pos-30):pos]
    print(f'Line {line_no}: pos={pos} ctx={repr(context_before[-20:])}')
