import re

with open('docs/calendar.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Find EVENTS_DATA in the script
data_start = content.index("var EVENTS_DATA = [") + len("var EVENTS_DATA = [")
data_end = content.index("];", data_start) + 1
events_json = content[data_start:data_end]

print(f"DATA: {data_start} to {data_end}, len={data_end-data_start}")

# Verify by checking for TITLE_CN (should NOT contain it)
if "TITLE_CN" in events_json:
    print("ERROR: TITLE_CN found inside DATA!")
    idx = events_json.index("TITLE_CN")
    print(f"  At char {idx}: ...{events_json[max(0,idx-50):idx+50]}...")
else:
    print("DATA clean, no TITLE_CN inside")

# Find HEADER_TIME
ht_match = re.search(r'(var HEADER_TIME = [^;]+;)', content)
header_time = ht_match.group(1) if ht_match else 'var HEADER_TIME = "2026-07-11";'
print(f"HEADER_TIME: {header_time}")
