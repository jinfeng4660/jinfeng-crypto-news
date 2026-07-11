import re
html=open('docs/index.html','r',encoding='utf-8').read()
js=open('docs/app.js','r',encoding='utf-8').read()

html=re.sub(r'<script src="./app\.js[^"]*"></script>', '', html)
html=html.replace('</body>', '<script>\n'+js+'\n</script>\n</body>')

with open('docs/index.html','w',encoding='utf-8') as f:
    f.write(html)
print(f'Inlined. Size: {len(html)} bytes')
