import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('docs/app.js','r',encoding='utf-8') as f:
    lines = f.readlines()

new_block = [
    '  var topics={};\n',
    '  ARTICLES_DATA.forEach(function(a){\n',
    '    if(a.coins){\n',
    '      a.coins.forEach(function(c){\n',
    '        if(c!="ALL"){topics[c]=(topics[c]||0)+1}\n',
    '      })\n',
    '    }\n',
    '  });\n',
]

with open('docs/app.js','w',encoding='utf-8') as f:
    i = 0
    while i < len(lines):
        if 'updateTopics' in lines[i]:
            # Replace line 294 (topics var), 295 (forEach), 296 (sorted)
            f.write(lines[i])
            i += 1
            f.writelines(new_block)
            # skip old lines 295-296
            i += 2
        else:
            f.write(lines[i])
            i += 1
print('replacement done')
