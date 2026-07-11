import urllib.request, time, sys

proxy = "http://127.0.0.1:10020"
proxy_handler = urllib.request.ProxyHandler({"http": proxy, "https": proxy})
opener = urllib.request.build_opener(proxy_handler)
time.sleep(5)
req = urllib.request.Request("https://jinfeng4660.github.io/jinfeng-crypto-news/?v=2", headers={"User-Agent": "Mozilla/5.0"})
resp = opener.open(req, timeout=15)
html = resp.read().decode()

checks = {
    "openChainPanel": "JS function",
    "SUI": "SUI in page",
    "chain-chart": "chart CSS",
    "ticker-coin": "clickable coins",
    "chain-modal": "modal HTML",
    "klines": "Kline data",
}
for c, label in checks.items():
    ok = c in html
    print(f"{'OK' if ok else 'MISSING'}: {label} ({c})")

# Verify no LINK with onclick
for line in html.split("\n"):
    if "LINK" in line and "ticker" in line.lower():
        if "onclick" in line:
            print("ERROR: LINK still has onclick handler!")
        else:
            print("OK: LINK removed, no click handler")
print(f"Page size: {len(html)} bytes ({len(html)/1024:.0f}KB)")
