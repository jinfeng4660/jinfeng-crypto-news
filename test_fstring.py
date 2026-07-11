import sys
sys.stdout.reconfigure(encoding='utf-8')
text = f'test {{}} test {{hello}}'
print(repr(text))
print(text)

code = 'function $(id){{return document.getElementById(id)}}'
print(code)
# In f-string:
html = f'''{code}'''
print(repr(html))
