import sys, re, subprocess
sys.stdout.reconfigure(encoding='utf-8')
with open('docs/calendar.html','r',encoding='utf-8') as f:
    content = f.read()
m = re.search(r'<script>(.*?)</script>', content, re.DOTALL)
if m:
    js = m.group(1)
    with open('/tmp/cal_js_test.js','w',encoding='utf-8') as f:
        f.write('try {\n')
        f.write(js)
        f.write('\nconsole.log("OK");\n} catch(e) { console.log(e.message + " at line " + e.lineNumber); }\n')
    r = subprocess.run(['node', 'c:/temp/cal_js_test.js'], capture_output=True, text=True, timeout=5)
    print('stdout:', r.stdout[:500])
    print('stderr:', r.stderr[:500])
