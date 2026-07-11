import sys, re
sys.stdout.reconfigure(encoding='utf-8')
with open('docs/calendar.html','r',encoding='utf-8') as f:
    content = f.read()

# Check for double braces in the document
if '{{' in content:
    idx = content.index('{{')
    line = content[:idx].count('\n') + 1
    print(f'Double braces at line {line}:')
    print(f'  ...{content[max(0,idx-40):idx+40]}...')
else:
    print('No double braces in document')

# Check script section
m = re.search(r'<script>(.*?)</script>', content, re.DOTALL)
if m:
    js = m.group(1)
    # Check unclosed braces or bad syntax
    lines = js.split('\n')
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped and stripped[0] == '{':
            print(f'Line {i+1} starts with {{: {stripped[:40]}')
