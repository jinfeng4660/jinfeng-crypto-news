import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('scripts/main.py','r',encoding='utf-8') as f:
    content = f.read()

# Find the renderCards call
import re
# Replace the entire script block
old_block = """<script>var DATA = ''' + articles_json + '''; window.__r=setInterval(function(){if(typeof renderCards===chr(34)+chr(102)+chr(117)+chr(110)+chr(99)+chr(116)+chr(105)+chr(111)+chr(110)+chr(34)){clearInterval(window.__r);renderCards(DATA)}},10);</script>"""
new_block = """<script>var DATA = """
new_block += "'" + "'" + "' + articles_json + '" + "'" + "'"
new_block += """; window.addEventListener('load',function(){renderCards(DATA)});</script>"""

content = content.replace(old_block, new_block)
with open('scripts/main.py','w',encoding='utf-8') as f:
    f.write(content)
print('replaced successfully')
