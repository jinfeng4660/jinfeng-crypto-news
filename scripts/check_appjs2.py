import urllib.request, time
proxy = "http://127.0.0.1:10020"
h = urllib.request.ProxyHandler({"http": proxy, "https": proxy})
o = urllib.request.build_opener(h)
time.sleep(5)
r = o.open(urllib.request.Request("https://jinfeng4660.github.io/jinfeng-crypto-news/app.js?v=" + str(int(time.time()*1000)), headers={"User-Agent": "Mozilla/5.0", "Cache-Control": "no-cache"}), timeout=15)
d = r.read().decode()
print("Size:", len(d))
print("Has '最高' on left side (no right label):", '最高' in d)
print("Has dominant-baseline:", 'dominant-baseline' in d)
print("Has 'text-anchor=\"end\"':", 'text-anchor="end"' in d)
print("Last 200 chars:", d[-200:])
