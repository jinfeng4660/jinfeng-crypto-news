import sys
sys.stdout.reconfigure(encoding='utf-8')
import json
from datetime import datetime
events = [{"id":1,"date":"2026-07-10","title":"Test","currency":"USD","impact":"high","actual":"1.2","forecast":"1.0","previous":"0.8","time":"8:30am","weekday":"五","ai_analysis":{"impact_assessment":"test"}}]
today_str = datetime.now().strftime('%Y-%m-%d')
docs_dir = "."
events_json = json.dumps(events, ensure_ascii=False)

# Exact same html generation code as in calendar_page.py
html = f'''<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body>
<script>
var EVENTS_DATA = ''' + events_json + ''';

function $(id){{return document.getElementById(id)}}

var todayStr=''' + today_str + ''';

renderEventList();
</script>
</body>
</html>'''
print(html[:500])
