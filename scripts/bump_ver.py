import hashlib, os

# Read app.js, compute hash of first 100 chars as version
with open('docs/app.js', 'r', encoding='utf-8') as f:
    app_js = f.read()

# Compute short hash from content
h = hashlib.md5(app_js.encode()).hexdigest()[:8]
ver = 'v' + h

print(f'app.js version: {ver}')

# Update index.html
with open('docs/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

import re
old_ver_match = re.search(r'app\.js\?v=([\w.]+)', html)
if old_ver_match:
    old_ver = old_ver_match.group(1)
    print(f'Old version: {old_ver}')
    html = html.replace(f'app.js?v={old_ver}', f'app.js?v={ver}')
    with open('docs/index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'Updated to {ver}')
else:
    print('No version found')
