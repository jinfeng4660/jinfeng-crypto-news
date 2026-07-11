"""
chain_data.py — 链上数据采集模块
Binance API (免费、无需认证) + Alternative.me (恐惧贪婪指数)
采集 BTC/ETH/SOL 三大主流币的链上+合约数据
"""
import urllib.request, json, logging
from datetime import datetime

logger = logging.getLogger(__name__)

# ===== 配置 =====
SYMBOLS = {
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT",
    "SOL": "SOLUSDT",
    "SUI": "SUIUSDT",
    "DOGE": "DOGEUSDT",
}

PROXY = "http://127.0.0.1:10020"


def _fetch(url, timeout=10):
    """带代理统一请求"""
    proxy_handler = urllib.request.ProxyHandler({"http": PROXY, "https": PROXY})
    opener = urllib.request.build_opener(proxy_handler)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    resp = opener.open(req, timeout=timeout)
    return json.loads(resp.read().decode())


def fetch_oi(symbol):
    """未平仓合约"""
    url = f"https://fapi.binance.com/fapi/v1/openInterest?symbol={symbol}"
    d = _fetch(url)
    return {
        "oi": float(d["openInterest"]),
        "oi_usdt": float(d["openInterest"]) * 0,  # will be multiplied by price later
    }


def fetch_funding(symbol):
    """资金费率 + 标记价格 + 指数价格"""
    url = f"https://fapi.binance.com/fapi/v1/premiumIndex?symbol={symbol}"
    d = _fetch(url)
    return {
        "funding_rate": float(d["lastFundingRate"]) * 100,  # 转为百分比
        "mark_price": float(d["markPrice"]),
        "index_price": float(d["indexPrice"]),
        "next_funding_time": d["nextFundingTime"],
    }


def fetch_24hr(symbol):
    """24小时行情"""
    url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"
    d = _fetch(url)
    return {
        "last_price": float(d["lastPrice"]),
        "price_change_pct": float(d["priceChangePercent"]),
        "high_24h": float(d["highPrice"]),
        "low_24h": float(d["lowPrice"]),
        "volume_24h": float(d["volume"]),
        "quote_volume_24h": float(d["quoteVolume"]),
        "weighted_avg_price": float(d["weightedAvgPrice"]),
    }


def fetch_long_short_ratio(symbol):
    """多空持仓人数比（全网账户）"""
    url = f"https://fapi.binance.com/futures/data/globalLongShortAccountRatio?symbol={symbol}&period=1h&limit=1"
    d = _fetch(url)
    if d and len(d) > 0:
        return {
            "long_account_pct": float(d[0]["longAccount"]) * 100,
            "short_account_pct": float(d[0]["shortAccount"]) * 100,
            "long_short_ratio": float(d[0]["longShortRatio"]),
        }
    return None


def fetch_top_trader_ratio(symbol):
    """大户多空仓位比"""
    url = f"https://fapi.binance.com/futures/data/topLongShortPositionRatio?symbol={symbol}&period=1h&limit=1"
    d = _fetch(url)
    if d and len(d) > 0:
        return {
            "top_long_pct": float(d[0]["longAccount"]) * 100,
            "top_short_pct": float(d[0]["shortAccount"]) * 100,
            "top_long_short_ratio": float(d[0]["longShortRatio"]),
        }
    return None


def fetch_taker_ratio(symbol):
    """主动买/卖成交量比"""
    url = f"https://fapi.binance.com/futures/data/takerlongshortRatio?symbol={symbol}&period=1h&limit=1"
    d = _fetch(url)
    if d and len(d) > 0:
        return {
            "buy_vol": float(d[0]["buyVol"]),
            "sell_vol": float(d[0]["sellVol"]),
            "buy_sell_ratio": float(d[0]["buySellRatio"]),
        }
    return None


def fetch_klines(symbol, interval="15m", limit=96):
    """K线数据，用于走势图（默认96根15min = 24h）"""
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        d = _fetch(url)
        candles = []
        for c in d:
            candles.append({
                "t": c[0],       # open time
                "o": float(c[1]), # open
                "h": float(c[2]), # high
                "l": float(c[3]), # low
                "c": float(c[4]), # close
                "v": float(c[5]), # volume
            })
        return candles
    except Exception as e:
        logger.warning(f"[{symbol}] K线采集失败: {e}")
    return None


def fetch_fear_greed():
    """恐惧与贪婪指数"""
    try:
        url = "https://api.alternative.me/fng/?limit=1"
        d = _fetch(url)
        if d and d.get("data") and len(d["data"]) > 0:
            item = d["data"][0]
            return {
                "value": int(item["value"]),
                "classification": item["value_classification"],
            }
    except Exception as e:
        logger.warning(f"恐惧指数采集失败: {e}")
    return None


def get_chain_data_for_symbol(coin):
    """采集单个币种的全部链上数据"""
    symbol = SYMBOLS.get(coin.upper() if len(coin) <= 6 else coin.upper() + "USDT")
    if not symbol:
        # 直接处理 BTCUSDT 格式
        if "USDT" in coin.upper():
            symbol = coin.upper()
            coin = symbol.replace("USDT", "")
        else:
            return None

    result = {"coin": coin, "symbol": symbol, "time": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")}

    try:
        ticker = fetch_24hr(symbol)
        result["price"] = ticker["last_price"]
        result["change_pct"] = ticker["price_change_pct"]
        result["high_24h"] = ticker["high_24h"]
        result["low_24h"] = ticker["low_24h"]
        result["volume_24h"] = ticker["quote_volume_24h"]  # USDT value
    except Exception as e:
        logger.warning(f"[{coin}] 24h行情采集失败: {e}")

    try:
        oi = fetch_oi(symbol)
        result["oi"] = oi["oi"]  # 币本位
        if result.get("price"):
            result["oi_usdt"] = oi["oi"] * result["price"]
    except Exception as e:
        logger.warning(f"[{coin}] OI采集失败: {e}")

    try:
        funding = fetch_funding(symbol)
        result["funding_rate"] = funding["funding_rate"]
        result["mark_price"] = funding["mark_price"]
        result["index_price"] = funding["index_price"]
    except Exception as e:
        logger.warning(f"[{coin}] 资金费率采集失败: {e}")

    try:
        ls = fetch_long_short_ratio(symbol)
        if ls:
            result["long_account_pct"] = ls["long_account_pct"]
            result["short_account_pct"] = ls["short_account_pct"]
            result["long_short_ratio"] = ls["long_short_ratio"]
    except Exception as e:
        logger.warning(f"[{coin}] 多空比采集失败: {e}")

    try:
        taker = fetch_taker_ratio(symbol)
        if taker:
            result["taker_buy_vol"] = taker["buy_vol"]
            result["taker_sell_vol"] = taker["sell_vol"]
            result["taker_bs_ratio"] = taker["buy_sell_ratio"]
    except Exception as e:
        logger.warning(f"[{coin}] 主动买卖比采集失败: {e}")

    try:
        top = fetch_top_trader_ratio(symbol)
        if top:
            result["top_long_pct"] = top["top_long_pct"]
            result["top_short_pct"] = top["top_short_pct"]
            result["top_ls_ratio"] = top["top_long_short_ratio"]
    except Exception as e:
        logger.warning(f"[{coin}] 大户多空采集失败: {e}")

    # K线数据（走势图用）
    try:
        klines = fetch_klines(symbol, interval="15m", limit=96)
        if klines:
            result["klines"] = klines
            closes = [c["c"] for c in klines]
            result["kline_high"] = max(closes)
            result["kline_low"] = min(closes)
    except Exception as e:
        logger.warning(f"[{coin}] K线采集失败: {e}")

    return result


def fetch_all_chain_data(coins=None):
    """采集所有币种的链上数据 + 恐惧指数"""
    if coins is None:
        coins = ["BTC", "ETH", "SOL"]

    chain_data = {}
    for coin in coins:
        data = get_chain_data_for_symbol(coin)
        if data:
            chain_data[coin] = data
            logger.info(f"[链上] {coin}: 价格={data.get('price')}, OI={data.get('oi')}, 资金费率={data.get('funding_rate')}")

    chain_data["_fear_greed"] = fetch_fear_greed()
    chain_data["_time"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    return chain_data


def generate_chain_analysis(chain_data, coin):
    """基于链上数据生成AI分析"""
    if coin not in chain_data:
        return None

    d = chain_data[coin]

    analysis = {
        "coin": coin,
        "market_trend": "中性",
        "leverage_sentiment": "中性",
        "capital_flow": "中性",
        "risk_level": "中",
        "score": 50,
        "signals": [],
        "detail": "",
    }

    signals = []
    score = 50  # 基准50分

    # 1. 价格趋势
    pct = d.get("change_pct", 0)
    if pct > 2:
        analysis["market_trend"] = "强势上涨"
        score += 10
        signals.append("📈 24h涨幅>2%，短期强势")
    elif pct > 0.5:
        analysis["market_trend"] = "偏多震荡"
        score += 5
        signals.append("📈 24h小幅上涨，多头占优")
    elif pct < -2:
        analysis["market_trend"] = "强势下跌"
        score -= 10
        signals.append("📉 24h跌幅>2%，短期承压")
    elif pct < -0.5:
        analysis["market_trend"] = "偏空震荡"
        score -= 5
        signals.append("📉 24h小幅下跌，空头占优")
    else:
        analysis["market_trend"] = "横盘整理"
        signals.append("➡️ 24h价格窄幅波动")

    # 2. OI变化判断资金流入/流出
    oi = d.get("oi", 0)
    oi_signal = ""
    if oi > 0:
        # OI绝对值判断市场热度
        if coin == "BTC":
            if oi > 150000:
                oi_signal = "OI极高，资金大量涌入"
                score += 8
                signals.append(f"🔥 未平仓合约{oi:.0f}张，市场高度活跃")
            elif oi < 80000:
                oi_signal = "OI偏低，资金观望"
                score -= 5
                signals.append(f"💤 OI仅{oi:.0f}张，市场参与度下降")
            else:
                oi_signal = "OI中等，市场正常"
                signals.append(f"📊 OI {oi:.0f}张，市场正常活跃")
        elif coin == "ETH":
            if oi > 3000000:
                signals.append(f"🔥 OI {oi:.0f}张，资金活跃")
            elif oi < 1500000:
                signals.append(f"💤 OI {oi:.0f}张，资金参与度偏低")
            else:
                signals.append(f"📊 OI {oi:.0f}张，正常水平")
        elif coin == "SUI":
            if oi > 2e8:
                signals.append(f"🔥 OI {oi:.1e}张，资金活跃")
            elif oi < 5e7:
                signals.append(f"💤 OI {oi:.1e}张，资金参与度偏低")
            else:
                signals.append(f"📊 OI {oi:.1e}张，正常水平")
        elif coin == "DOGE":
            if oi > 5e9:
                signals.append(f"🔥 OI {oi:.1e}张，资金活跃")
            elif oi < 1e9:
                signals.append(f"💤 OI {oi:.1e}张，资金参与度偏低")
            else:
                signals.append(f"📊 OI {oi:.1e}张，正常水平")

    # 3. 资金费率判断多空情绪
    fr = d.get("funding_rate", 0)
    if fr > 0.01:
        analysis["leverage_sentiment"] = "多头过热"
        score -= 5
        signals.append(f"⚠️ 资金费率{fr:.4f}%，多头仓位成本偏高，有踩踏风险")
    elif fr > 0.005:
        analysis["leverage_sentiment"] = "略偏多"
        score += 3
        signals.append(f"💰 资金费率{fr:.4f}%，多头情绪温和")
    elif fr < -0.01:
        analysis["leverage_sentiment"] = "空头过热"
        score += 8  # 空头过热 → 潜在轧空
        signals.append(f"🔥 资金费率{fr:.4f}%，空头仓位成本高，轧空风险上升")
    elif fr < -0.005:
        analysis["leverage_sentiment"] = "略偏空"
        score -= 3
        signals.append(f"💸 资金费率{fr:.4f}%，空头略占优")
    else:
        analysis["leverage_sentiment"] = "均衡"
        signals.append(f"⚖️ 资金费率{fr:.4f}%，多空平衡")

    # 4. 多空比
    lsr = d.get("long_short_ratio", 1)
    if lsr > 2:
        analysis["capital_flow"] = "散户极度偏多"
        score -= 5  # 散户一致看多 → 潜在反转
        signals.append(f"⚠️ 全网多空比{lsr:.2f}，散户一致看多，警惕反向行情")
    elif lsr > 1.5:
        analysis["capital_flow"] = "散户偏多"
        score -= 2
        signals.append(f"👥 全网多空比{lsr:.2f}，散户偏多")
    elif lsr < 0.7:
        analysis["capital_flow"] = "散户偏空"
        score += 5  # 散户一致看空 → 潜在反弹
        signals.append(f"👥 全网多空比{lsr:.2f}，散户偏空，潜在支撑")
    elif lsr < 0.5:
        analysis["capital_flow"] = "散户极度偏空"
        score += 8
        signals.append(f"🔥 全网多空比{lsr:.2f}，散户极度看空，反弹概率大")
    else:
        analysis["capital_flow"] = "多空均衡"
        signals.append(f"👥 全网多空比{lsr:.2f}，多空均衡")

    # 5. 主动买卖比
    taker_r = d.get("taker_bs_ratio", 1)
    if taker_r > 1.2:
        score += 5
        signals.append(f"🟢 主动买/卖比{taker_r:.2f}，买方力量占优")
    elif taker_r < 0.8:
        score -= 5
        signals.append(f"🔴 主动买/卖比{taker_r:.2f}，卖方力量占优")
    else:
        signals.append(f"⚪ 主动买/卖比{taker_r:.2f}，买卖均衡")

    # 6. 大户多空比（机构/聪明钱方向）
    top_ls = d.get("top_ls_ratio", 1)
    if top_ls > 1.3 and lsr > 1.5:
        # 大户和散户都偏多 → 趋势健康
        signals.append(f"📊 大户和散户均偏多，趋势一致性良好")
        score += 5
    elif top_ls < 0.8 and lsr > 1.5:
        # 大户偏空 + 散户偏多 → 背离警告
        signals.append(f"⚠️ 大户偏空(比{top_ls:.2f})但散户偏多(比{lsr:.2f})，资金背离")
        score -= 10
    elif top_ls > 1.3 and lsr < 0.7:
        # 大户偏多 + 散户偏空 → 聪明钱抄底
        signals.append(f"🟢 大户偏多(比{top_ls:.2f})散户偏空(比{lsr:.2f})，聪明钱在买入")
        score += 10

    # 7. 恐惧贪婪
    fg = chain_data.get("_fear_greed", {})
    if fg:
        fg_val = fg.get("value", 50)
        fg_cls = fg.get("classification", "")
        if fg_val <= 25:
            signals.append(f"😱 恐惧贪婪指数{fg_val}（极度恐惧），历史底部区间，潜在反弹机会")
            score += 10
        elif fg_val <= 45:
            signals.append(f"😰 恐惧贪婪指数{fg_val}（恐惧），市场情绪偏悲观")
            score += 5
        elif fg_val >= 75:
            signals.append(f"🤑 恐惧贪婪指数{fg_val}（贪婪），市场过热风险")
            score -= 10
        elif fg_val >= 55:
            signals.append(f"😊 恐惧贪婪指数{fg_val}（贪婪偏乐观），市场情绪较好")
            score -= 5

    # 8. 24h成交量评估
    vol = d.get("volume_24h", 0)
    if vol > 0:
        if coin == "BTC" and vol > 50_000_000_000:
            signals.append(f"💰 24h成交量${vol/1e9:.1f}B，市场交投活跃")
            score += 5
        elif coin == "BTC" and vol < 15_000_000_000:
            signals.append(f"💤 24h成交量${vol/1e9:.1f}B，交投清淡")
            score -= 3

    # 综合评分和风险等级
    score = max(0, min(100, score))
    analysis["score"] = score

    if score >= 75:
        analysis["risk_level"] = "低"
        analysis["detail"] = "链上数据全面偏多，资金流向健康"
    elif score >= 60:
        analysis["risk_level"] = "低中"
        analysis["detail"] = "链上数据偏多，部分指标需关注"
    elif score >= 45:
        analysis["risk_level"] = "中"
        analysis["detail"] = "多空指标交织，无明显倾向"
    elif score >= 30:
        analysis["risk_level"] = "中高"
        analysis["detail"] = "链上数据偏空，需警惕下行风险"
    else:
        analysis["risk_level"] = "高"
        analysis["detail"] = "链上数据全面偏空，注意风险控制"

    analysis["signals"] = signals[:6]  # 最多6条信号

    return analysis


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    # 测试采集
    data = fetch_all_chain_data(["BTC", "ETH", "SOL", "SUI", "DOGE"])
    print("=" * 60)
    print("链上数据采集完成")
    print("=" * 60)

    for coin in ["BTC", "ETH", "SOL", "SUI", "DOGE"]:
        cd = data.get(coin, {})
        print(f"\n{'=' * 40}")
        print(f"  {coin}")
        print(f"{'=' * 40}")
        for k, v in cd.items():
            if k != "coin" and k != "symbol" and k != "time":
                print(f"  {k}: {v}")
        analysis = generate_chain_analysis(data, coin)
        if analysis:
            print(f"\n  AI分析:")
            print(f"  综合评分: {analysis['score']}/100")
            print(f"  市场趋势: {analysis['market_trend']}")
            print(f"  杠杆情绪: {analysis['leverage_sentiment']}")
            print(f"  资金流向: {analysis['capital_flow']}")
            print(f"  风险等级: {analysis['risk_level']}")
            print(f"  概述: {analysis['detail']}")
            print(f"  信号:")
            for s in analysis["signals"]:
                print(f"    {s}")

    fg = data.get("_fear_greed", {})
    if fg:
        print(f"\n  📊 恐惧与贪婪指数: {fg['value']} — {fg['classification']}")
