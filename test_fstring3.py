import sys
sys.stdout.reconfigure(encoding='utf-8')

# Test: are {{ }} in an f-string escaped?
s = f'''test {{}}'''
print(repr(s))

# Test: what about in a larger f-string with interpolation?
name = "world"
s2 = f'''hello {{name='{name}'}}'''
print(repr(s2))

# The actual pattern from calendar_page.py
s3 = f'''<script>
var X = ''' + '"test"' + ''';
function $(){{return 1}}
</script>'''
print(repr(s3))
