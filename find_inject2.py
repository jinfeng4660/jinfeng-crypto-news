import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('scripts/main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the line with "file write" pattern
target = 'with open(html_path, "w", encoding="utf-8") as f:'
insert_after = '    return articles'

target_idx = None
insert_idx = None
for i, line in enumerate(lines):
    if target in line:
        target_idx = i
    if insert_after in line and i > 500:
        insert_idx = i
        break

print(f'File write line: {target_idx}, return line: {insert_idx}')
print(f'Lines around return:')
for j in range(max(0, insert_idx-5), min(len(lines), insert_idx+3)):
    print(f'  {j}: {lines[j].rstrip()[:120]}')
