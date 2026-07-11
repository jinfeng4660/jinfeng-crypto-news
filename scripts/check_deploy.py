import urllib.request, re, time
proxy = "http://127.0.0.1:10020"
h = urllib.request.ProxyHandler({"http": proxy, "https": proxy})
o = urllib.request.build_opener(h)
time.sleep(5)
r = o.open(urllib.request.Request("https://jinfeng4660.github.io/jinfeng-crypto-news/?v=555", headers={"User-Agent": "Mozilla/5.0"}), timeout=15)
d = r.read().decode()
# Check app.js src
m = re.search(r'src="(app\.js[^"]*)"', d)
if m:
    print("Script src:", m.group(1))
# Check if new JS features exist in page
if "topPad" in d:
    print("NEW CHART CODE DETECTED (topPad found)")
elif "function py(" in d:
    print("NEW CHART CODE DETECTED (py() found)")
elif "volH" in d:
    print("NEW CHART CODE DETECTED (volH found)")
elif "volume bars" in d:
    print("NEW CHART CODE DETECTED (volume bars found)")
else:
    print("OLD CHART CODE (none of new features found)")
    # Check for old code patterns
    if "preserveAspectRatio" in d:
        print("Has preserveAspectRatio (SVG chart)")
    if "polyline" in d:
        print("Has polyline (SVG line)")
    if "chain-chart" in d:
        print("Has chain-chart CSS")
print("Page size:", len(d), "bytes")
