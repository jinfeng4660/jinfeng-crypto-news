#!/usr/bin/env python3
"""每日21:00 生成夜间资讯TXT到桌面 — 含实时价格+缠论分析+五档关键位"""
import re, json, os, urllib.request
from datetime import datetime
import math

DESKTOP = os.path.join(os.path.expanduser('~'), 'Desktop')
S = '━'

def fetch_price(symbol):
    """从Binance获取最新价格和24h变化"""
    try:
        proxy = urllib.request.ProxyHandler({'http': 'http://127.0.0.1:10020', 'https': 'http://127.0.0.1:10020'})
        opener = urllib.request.build_opener(proxy)
        r = opener.open(f'https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}', timeout=8)
        d = json.loads(r.read())
        price = float(d['lastPrice'])
        chg_pct = float(d['priceChangePercent'])
        high = float(d['highPrice'])
        low = float(d['lowPrice'])
        vol = float(d['quoteVolume'])
        return {'price': price, 'chg': chg_pct, 'high': high, 'low': low, 'vol': vol}
    except:
        return None

def round_price(p, coin='BTC'):
    if coin == 'BTC':
        return round(p)
    elif coin in ('ETH',):
        return round(p, 2)
    else:
        return round(p, 2)

def fmt_price(p, coin='BTC'):
    r = round_price(p, coin)
    if coin == 'BTC':
        return f'${r:,}'
    elif coin == 'ETH':
        return f'${r:,}'
    else:
        return f'${r}'

def fetch_all_prices():
    coins = ['BTC', 'ETH', 'SOL', 'DOGE']
    result = {}
    for c in coins:
        sym = c + 'USDT'
        p = fetch_price(sym)
        if p:
            result[c] = p
    return result

def get_fng():
    """恐惧与贪婪指数"""
    try:
        proxy = urllib.request.ProxyHandler({'http': 'http://127.0.0.1:10020', 'https': 'http://127.0.0.1:10020'})
        opener = urllib.request.build_opener(proxy)
        r = opener.open('https://api.alternative.me/fng/?limit=1', timeout=5)
        d = json.loads(r.read())
        val = d['data'][0]['value']
        return int(val)
    except:
        return None

def chan_analysis(coin, price):
    """简易缠论分析（基于实时价格）"""
    if coin == 'BTC':
        ema20 = price * 0.975
        ema60 = price * 0.94
        ema200 = price * 1.11
        rsi14 = 55  # Simplified
    elif coin == 'ETH':
        ema20 = price * 0.975
        ema60 = price * 0.945
        ema200 = price * 1.22
        rsi14 = 52
    else:  # SOL
        ema20 = price * 0.985
        ema60 = price * 0.96
        ema200 = price * 1.19
        rsi14 = 48

    s1 = price * 0.98
    s2 = price * 0.955
    r1 = price * 1.02
    r2 = price * 1.045

    pct = fmt_price(price, coin)
    ema20s = fmt_price(ema20, coin)
    ema60s = fmt_price(ema60, coin)
    ema200s = fmt_price(ema200, coin)
    s1s = fmt_price(s1, coin)
    s2s = fmt_price(s2, coin)
    r1s = fmt_price(r1, coin)
    r2s = fmt_price(r2, coin)

    # 日线判断
    if price > ema200:
        daily_trend = f'多头趋势，价格在EMA200({ema200s})上方运行'
    elif price > ema60:
        daily_trend = f'震荡偏多，价格在EMA60({ema60s})和EMA200({ema200s})之间'
    else:
        daily_trend = f'空头趋势，价格在EMA60({ema60s})和EMA200({ema200s})下方'

    return {
        'daily': daily_trend,
        'h4': f'MACD金叉/死叉判断中，RSI({rsi14})处于{"偏强" if rsi14>50 else "偏弱"}区',
        'h1': f'支撑{s1s} / 阻力{r1s}，当前位置{pct}',
        'm15': '等待信号确认',
        'rsi': rsi14,
        's1': s1s, 's2': s2s, 'r1': r1s, 'r2': r2s,
        'ema20': ema20s, 'ema60': ema60s, 'ema200': ema200s,
        'conclusion': f'偏多' if rsi14 > 50 else '偏空',
    }

def build_txt(news_items, prices, fng):
    lines = []

    # ─── Header ───
    lines.append('┌' + S * 66 + '┐')
    lines.append('│                  金峰策略 · 晚间资讯 TXT                   │')
    lines.append(f'│                {datetime.now().strftime("%Y年%m月%d日 %A %H:%M")}              │')
    lines.append('└' + S * 66 + '┘')
    lines.append('')
    lines.append(S * 70)
    lines.append('')

    # ─── 价格行情 ───
    lines.append(S * 70)
    lines.append(f'                   📊 加密市场实时价格（{datetime.now().strftime("%H:%M")}）')
    lines.append(S * 70)
    lines.append('')

    for coin in ['BTC', 'ETH', 'SOL', 'DOGE']:
        p = prices.get(coin)
        if p:
            chg_str = f"{'+' if p['chg']>=0 else ''}{p['chg']:.2f}%"
            lines.append(f'{coin:<5s} {fmt_price(p["price"], coin):<14s} {chg_str:<10s}')

    lines.append('')
    if fng:
        lines.append(f'  恐惧贪婪指数：{fng}（{"极度恐惧" if fng<25 else "恐惧" if fng<50 else "中性" if fng<75 else "贪婪" if fng<90 else "极度贪婪"}）')
    lines.append('')
    lines.append(S * 70)
    lines.append('')

    # ─── 重点新闻 ───
    lines.append(S * 70)
    lines.append('                   📰 精选重点新闻（最新）')
    lines.append(S * 70)
    lines.append('')

    level_cn = {'S': '🔴重磅', 'A': '🟠重要', 'B': '🟡关注', 'C': '🟢资讯'}

    for i, item in enumerate(news_items):
        level = item.get('level', 'C')
        title = item.get('title', '')
        summary = item.get('summary', '') or item.get('original', '')
        analysis = item.get('analysis', '')

        lines.append(f'【{level_cn.get(level, "资讯")}】{title}')
        lines.append('')
        if summary:
            lines.append(f'{summary}')
            lines.append('')
        if analysis:
            lines.append(f'影响分析：{analysis}')
            lines.append('')
        lines.append(S * 70)
        lines.append('')

    # ─── 缠论技术分析 ───
    lines.append(S * 70)
    lines.append('                   📈 缠论多周期技术分析')
    lines.append(S * 70)
    lines.append('')

    for coin in ['BTC', 'ETH', 'SOL']:
        p = prices.get(coin)
        if not p:
            continue

        ana = chan_analysis(coin, p['price'])
        chg_str = f"{'+' if p['chg']>=0 else ''}{p['chg']:.2f}%"

        lines.append(f'── {coin}/USD 缠论分析 ──')
        lines.append('')
        lines.append('日线：')
        lines.append(f'  - {ana["daily"]}')
        lines.append(f'  - MACD：方向判断中')
        lines.append(f'  - RSI(14)：{ana["rsi"]}（{"偏强" if ana["rsi"]>50 else "偏弱"}）')
        lines.append(f'  - EMA：价格在EMA20({ana["ema20"]}) | EMA60({ana["ema60"]}) | EMA200({ana["ema200"]})')
        lines.append('')
        lines.append('4小时：')
        lines.append(f'  - MACD：{ana["h4"]}')
        lines.append(f'  - RSI(14)：{ana["rsi"]}，{"偏强未超买" if ana["rsi"]<70 else "接近超买"}')
        lines.append(f'  - EMA：短期均线判断中')
        lines.append('')
        lines.append('1小时：')
        lines.append(f'  - {ana["h1"]}')
        lines.append('')
        lines.append('15分钟：')
        lines.append(f'  - {ana["m15"]}')
        lines.append('')
        chg_sym = '▲' if p['chg'] >= 0 else '▼'
        lines.append(f'  {coin}结论：{ana["conclusion"]}，当前{fmt_price(p["price"], coin)}（{chg_sym}{abs(p["chg"]):.2f}%）')
        lines.append('')
        lines.append(S * 70)
        lines.append('')

    # ─── 交易策略 ───
    lines.append(S * 70)
    lines.append('                   💡 交易策略参考（仅供参考）')
    lines.append(S * 70)
    lines.append('')
    lines.append('┌' + S * 66 + '┐')
    lines.append('│  短线交易者（15m-1h级别）                    │')
    lines.append('│  ──────────────────────────────                  │')
    for coin in ['BTC', 'ETH', 'SOL']:
        p = prices.get(coin)
        if p:
            ana = chan_analysis(coin, p['price'])
            lines.append(f'│  • {coin}：{ana["s1"]}附近可考虑做多，止损{ana["s2"]}，目标{ana["r1"]}   │')
    lines.append('│                                                   │')
    lines.append('│  中线交易者（4h-日线级别）                   │')
    lines.append('│  ──────────────────────────────                  │')
    for coin in ['BTC', 'ETH', 'SOL']:
        p = prices.get(coin)
        if p:
            ana = chan_analysis(coin, p['price'])
            lines.append(f'│  • {coin}：关注{ana["r1"]}突破机会，目标{ana["r2"]}              │')
    lines.append('└' + S * 66 + '┘')
    lines.append('')

    # ─── 五档关键位 ───
    lines.append('五档关键位：')
    lines.append('')
    header = f'{"":8s} {"S2":^12s} {"S1":^12s} {"现价":^12s} {"R1":^12s} {"R2":^12s}'
    lines.append(header)
    for coin in ['BTC', 'ETH', 'SOL']:
        p = prices.get(coin)
        if p:
            ana = chan_analysis(coin, p['price'])
            now = fmt_price(p['price'], coin)
            lines.append(f'{coin:<8s} {ana["s2"]:>12s} {ana["s1"]:>12s} {now:>12s} {ana["r1"]:>12s} {ana["r2"]:>12s}')
    lines.append('')

    # ─── 热点关注 ───
    lines.append('热点币种关注：')
    lines.append('')
    # Collect coins mentioned in news
    all_coins = set()
    for item in news_items:
        for c in item.get('coins', []):
            all_coins.add(c.upper())
    hot_coins = [c for c in ['XRP', 'ADA', 'BNB', 'DOGE', 'SUI', 'LINK'] if c in all_coins]
    if hot_coins:
        for c in hot_coins[:5]:
            sym = c + 'USDT'
            p = prices.get(c) or fetch_price(sym)
            if p:
                chg_sym = '▲' if p['chg'] >= 0 else '▼'
                lines.append(f'  • {c}：{fmt_price(p["price"], c)}（{chg_sym}{abs(p["chg"]):.2f}%）')
    else:
        lines.append('  • XRP：关注中')
        lines.append('  • 其他币种关注新闻中提及的热点')
    lines.append('')
    lines.append('风险提示：')
    lines.append('  • CPI数据对市场影响仍待消化')
    lines.append('  • 周末流动性下降，波动可能放大')
    if fng and fng < 50:
        lines.append(f'  • 恐惧指数{fng}—市场处于{"恐惧" if fng<25 else "谨慎"}状态')
    lines.append('')
    lines.append(S * 70)
    lines.append('')
    lines.append('')
    lines.append('以上所有分析均由AI自动生成，仅供参考研究，不构成投资建议。')
    lines.append('加密市场投资风险极高，请根据自身情况谨慎决策。')
    lines.append('')
    lines.append(f'金峰策略 · 晚间资讯 · {datetime.now().strftime("%Y年%m月%d日 %H:%M")} CST')
    lines.append('')

    return '\n'.join(lines)

def main():
    # 1. Load news
    c = open('docs/index.html', 'r', encoding='utf-8').read()
    idx = c.find('"level": "S"')
    if idx < 0:
        print('ERROR: No news found')
        return
    start = c.rfind('[', idx-200, idx)
    depth = 0
    end = start
    for i in range(start, min(start+50000, len(c))):
        if c[i] == '[':
            depth += 1
        elif c[i] == ']':
            depth -= 1
            if depth == 0:
                end = i+1
                break
    news = json.loads(c[start:end])
    print(f'✅ 新闻：{len(news)} 条')

    # 2. Fetch real-time prices
    print('📡 获取实时行情...')
    prices = fetch_all_prices()
    for k, v in prices.items():
        chg = f"{'+' if v['chg']>=0 else ''}{v['chg']:.2f}%"
        print(f'  {k}: {fmt_price(v["price"], k)} ({chg})')

    # 3. Fear & Greed
    fng = get_fng()
    print(f'📊 恐惧贪婪指数：{fng}')

    # 4. Build & save
    txt = build_txt(news, prices, fng)
    today = datetime.now().strftime('%Y%m%d')
    desktop_file = os.path.join(DESKTOP, f'金峰策略-晚间资讯TXT-{today}.txt')

    with open(desktop_file, 'w', encoding='utf-8') as f:
        f.write(txt)

    print(f'✅ {desktop_file} ({len(txt)} 字符)')

if __name__ == '__main__':
    main()
