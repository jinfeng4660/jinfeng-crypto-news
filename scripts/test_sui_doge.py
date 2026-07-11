"""Test SUI and DOGE API availability"""
import urllib.request, json

PROXY = "http://127.0.0.1:10020"
proxy_handler = urllib.request.ProxyHandler({"http": PROXY, "https": PROXY})
opener = urllib.request.build_opener(proxy_handler)
hdr = {"User-Agent": "Mozilla/5.0"}

for sym in ["SUIUSDT", "DOGEUSDT"]:
    print(f"\n=== {sym} ===")
    # OI
    try:
        url = f"https://fapi.binance.com/fapi/v1/openInterest?symbol={sym}"
        d = json.loads(opener.open(urllib.request.Request(url, headers=hdr), timeout=10).read())
        print(f"OI: {float(d['openInterest']):.0f}")
    except Exception as e:
        print(f"OI Error: {e}")
    # LS ratio
    try:
        url = f"https://fapi.binance.com/futures/data/globalLongShortAccountRatio?symbol={sym}&period=1h&limit=1"
        d = json.loads(opener.open(urllib.request.Request(url, headers=hdr), timeout=10).read())
        print(f"L/S ratio: {d[0]['longShortRatio']}")
    except Exception as e:
        print(f"L/S Error: {e}")
    # Top trader
    try:
        url = f"https://fapi.binance.com/futures/data/topLongShortPositionRatio?symbol={sym}&period=1h&limit=1"
        d = json.loads(opener.open(urllib.request.Request(url, headers=hdr), timeout=10).read())
        print(f"Top L/S: {d[0]['longShortRatio']}")
    except Exception as e:
        print(f"Top L/S Error: {e}")
    # Taker
    try:
        url = f"https://fapi.binance.com/futures/data/takerlongshortRatio?symbol={sym}&period=1h&limit=1"
        d = json.loads(opener.open(urllib.request.Request(url, headers=hdr), timeout=10).read())
        print(f"Taker B/S: {d[0]['buySellRatio']}")
    except Exception as e:
        print(f"Taker Error: {e}")
    # 24hr ticker
    try:
        url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={sym}"
        d = json.loads(opener.open(urllib.request.Request(url, headers=hdr), timeout=10).read())
        print(f"Price: {d['lastPrice']}, Change: {d['priceChangePercent']}%")
    except Exception as e:
        print(f"24hr Error: {e}")
    # Klines for chart
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={sym}&interval=15m&limit=96"
        d = json.loads(opener.open(urllib.request.Request(url, headers=hdr), timeout=10).read())
        print(f"Klines: {len(d)} candles (24h)")
        # Show first and last
        print(f"  First: O={d[0][1]}, C={d[0][4]}")
        print(f"  Last:  O={d[-1][1]}, C={d[-1][4]}")
    except Exception as e:
        print(f"Klines Error: {e}")
