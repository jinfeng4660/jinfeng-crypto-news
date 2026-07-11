import sys
sys.stdout.reconfigure(encoding='utf-8')
import json
from calendar_fetcher_v2 import run_calendar_pipeline

proxy = 'http://127.0.0.1:10020'
events, err = run_calendar_pipeline(proxies={'http': proxy, 'https': proxy}, save_db=True)
print(f'Events: {len(events)}, err: {err}')
for i, ev in enumerate(events):
    print(f'{i}: {ev.get("date","")} {ev.get("title","")}')
    print(f'  ai_analysis: {ev.get("ai_analysis","MISSING")}')
    print(f'  keys: {list(ev.keys())}')
