"""
Signal - 全自动运行入口
采集→解析→去重→四层评分→智能分析→翻译→推送

用法:
  python main.py                          # 使用内置测试数据
  python main.py --from-file <json>       # 从数据文件加载
"""
import sys, json, os, hashlib, random, re
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

import yaml
import requests

# 配置路径
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE, "config", "config.yaml")
CACHE_PATH = os.path.join(BASE, "data", "processed_hashes.json")
src_path = os.path.join(BASE, "scripts")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from scorer import ScoreEngine
from ai_insight import generate_insight, generate_insight_batch
from analyzer import format_article

# 加载配置
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = yaml.safe_load(f)

engine = ScoreEngine()

# ==================== 解析器 ====================

def parse_panews(text):
    """解析PANews文字版（web_fetch抓取后的文本）"""
    articles = []
    # 先尝试按 "PA一线" 分割，再按"时间标记行"提取标题
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    # 直接取行：跳过日期行和时间行，取第一段非行为标题
    titles = []
    current_title = None
    for l in lines:
        # 跳过日期行 
        if re.match(r"^\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}", l):
            continue
        # 跳过纯时间行
        if re.match(r"^\d+(分钟|小时)前$", l):
            continue
        # 跳过已知非标题行
        if l in {"关注", "加载更多", "行业要闻", "市场热点", "精选读物", "点击订阅", "PA官方账号，最新消息一线送达。"}:
            continue
        if "粉丝" in l and "文章" in l: continue
        if l.startswith("---"): continue
        if "PA一线" in l: continue
        if len(l) > 3:
            articles.append({"title": l.strip(), "source": "PANews", "lang": "zh"})
    return articles

def parse_rss_xml(text, source_name):
    """解析RSS XML文本"""
    articles = []
    items = re.findall(r"<item>(.*?)</item>", text, re.DOTALL)
    for item in items:
        tm = re.search(r"<title>(.*?)</title>", item, re.DOTALL)
        dm = re.search(r"<description>(<!\[CDATA\[)?(.*?)(\]\]>)?</description>", item, re.DOTALL)
        if not tm: continue
        title = tm.group(1).strip()
        summary = ""
        if dm:
            desc = dm.group(2) if dm.lastindex >= 2 else dm.group(1)
            summary = re.sub(r"<[^>]+>", "", desc).strip()
            summary = re.sub(r"\s+", " ", summary)[:300]
        articles.append({"title": title, "summary": summary, "source": source_name, "lang": "en"})
    return articles

def parse_cryptopanic(text):
    """解析CryptoPanic文本"""
    articles = []
    lines = text.strip().split("\n")
    
    for line in lines:
        l = line.strip()
        if not l: continue
        if "SECURITY" in l or "Source:" in l or "---" in l or "DO NOT" in l: continue
        if "EXTERNAL_UNTRUSTED_CONTENT" in l: continue
        
        # X帖子
        if l.startswith("X - ") or l.startswith("LATEST:"):
            articles.append({"title": l, "summary": "", "source": "CryptoPanic", "lang": "en"})
            continue
        
        # 带·分隔符的标准新闻行: "Title · Source · Date · Tags"
        if "·" in l and len(l) > 20:
            # 跳过来源行（包含 · 且以来源名开头：Coindoo.com, The Block, NewsBTC 等）
            is_source_line = re.match(r"^\s*[A-Z][a-z]*\.?com|^[A-Z][a-z]+ .*·.*\d{4}", l)
            if is_source_line:
                continue
            
            # 检查是否是来源行：在 · 之前的部分是否太短或像来源名
            parts = l.split("·")
            title_part = parts[0].strip()
            
            # 来源行特征：标题部分短或包含"· "中间的日期
            if len(title_part) < 15 or (len(parts) >= 2 and re.match(r".*\d{4}", parts[1])):
                if len(parts) >= 2 and re.match(r".*\d{4}", parts[1]):
                    continue  # 这是"来源 · 2026 · 标签"行
            
            if len(title_part) > 10:
                articles.append({"title": title_part, "summary": "", "source": "CryptoPanic", "lang": "en"})
            continue
        
        # 不带·的纯标题行（路透式独立行）
        if len(l) > 30 and not l.startswith(" ") and not l.startswith("\t"):
            articles.append({"title": l, "summary": "", "source": "CryptoPanic", "lang": "en"})
    
    return articles

# ==================== 翻译表 ====================

EN_TO_CN = {
    "stablecoins found": "稳定币走向分化",
    "Bitcoin whales": "巨鲸推动BTC",
    "Metaplanet": "Metaplanet联合研究",
    "Circle gets": "Circle获OCC批准",
    "USDT wins": "USDT主导支付",
    "Cambridge": "剑桥研究",
    "Kraken Pro Fee": "Kraken Pro调费率",
    "Polymarket": "Polymarket申请NFA牌照",
    "BNB Chain": "BNB Chain推AI代理链",
    "Aave V3": "Aave V3上线zkSync",
    "Whale Realizes": "巨鲸亏损452万美元",
    "Tom Lee": "Tom Lee：加密是新存储交易",
    "Highest 30-Year": "30年期收益率创新高",
    "Hyundai Card": "现代汽车用稳定币汇款",
    "Binance Futures": "币安上线SK Hynix永续",
    "Kraken to relaunch": "Kraken推AI代理交易",
    "Whale Alert": "巨鲸警报大额转账",
    "MASSIVE Bank": "交易所挤兑警告",
    "BCG report": "BCG报告：数字资产是战略基础设施",
    "WALL STREET": "华尔街准备迎接BTC暴涨",
    "Bitcoin Fork": "比特币分叉战争重演",
}

KEYWORD_SUBS = {
    "Bitcoin":"BTC","whales":"巨鲸","whale":"巨鲸",
    "announces":"宣布","launch":"上线","approval":"批准",
    "credit":"信贷","digital":"数字","tokenization":"代币化",
    "trading":"交易","study":"研究","Japan":"日本","license":"牌照",
    "lending":"借贷","payment":"支付","payments":"支付",
    "stablecoin":"稳定币","stablcoins":"稳定币","fee":"费率",
    "volume":"交易量","margin":"保证金","nft":"NFT","ai":"AI","defi":"DeFi",
    "crypto":"加密","price":"价格","etf":"ETF","futures":"期货",
    "market":"市场","institutional":"机构","demand":"需求","euro":"欧元",
}

def translate_en(title):
    for en, cn in EN_TO_CN.items():
        if en.lower() in title.lower():
            return cn
    result = title
    for en, cn in KEYWORD_SUBS.items():
        if en in result:
            result = result.replace(en, cn)
    return result if result != title else None

# ==================== 去重 ====================

def dedup(articles):
    """内容去重：基于原始英文标题+中文标题复合指纹"""
    seen_fingerprints = set()
    unique = []
    for a in articles:
        title = a.get("title", "")
        display = a.get("display", title)
        original = a.get("original", "")
        
        # 跳过时间垃圾
        if re.match(r"^\d+(分钟|小时)前$", title) or re.match(r"^\d+(分钟|小时)前$", display):
            continue
        
        # 构建指纹：同时用原始英文和中文显示名
        fp = _make_fingerprint(title, original, display)
        if fp is None:
            unique.append(a)
            continue
        
        fp_hash = hashlib.md5(fp.encode()).hexdigest()[:12]
        
        if fp_hash not in seen_fingerprints:
            seen_fingerprints.add(fp_hash)
            unique.append(a)
    return unique

def _make_fingerprint(title, original, display):
    """生成去重指纹：英文核心词为主，纯中文用双字组"""
    texts = [t for t in [title, original, display] if t and t != "None"]
    if not texts:
        return None
    
    combined = " ".join(texts).lower()
    
    # 英文取第一个4+字母词（品牌/币种名）
    en_first = re.findall(r"\b([a-z]{4,})\b", combined)
    
    if en_first:
        # 有英文词：只取第一个英文词作为指纹（核心品牌词足够）
        # 英文品牌词（kraken/binance/circle等）同一事件跨源时必定相同
        return en_first[0]
    else:
        # 纯中文：取前6个双字组（排序去重）
        cn_chars = "".join(re.findall(r"[\u4e00-\u9fff]+", combined))
        bigrams = sorted(set(cn_chars[i:i+2] for i in range(len(cn_chars)-1)))
        return "".join(bigrams[:8]) if bigrams else combined[:20]

# ==================== 推送分层 ====================
# ✅ 推送关闭：只生成网站，不推送消息到飞书/Safew
PUSH_ENABLED = False

BATCH_FILE = os.path.join(BASE, "data", "pending_batch.json")

def _load_batch():
    if not os.path.exists(BATCH_FILE):
        return []
    try:
        with open(BATCH_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def _save_batch(articles):
    """保存积压消息"""
    with open(BATCH_FILE, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False)

def _clear_batch():
    if os.path.exists(BATCH_FILE):
        os.remove(BATCH_FILE)

def push_urgent(articles, now_str):
    """实时推送：只推S级（交易级信号）"""
    if not PUSH_ENABLED:
        return "推送已关闭"
    if not articles:
        return "无S级信号"
    
    token = "14005993:3GJmLY4TjcPKUJG7kkaLUnNSYaVrwLu1cBT"
    chat_id = "10000698411"
    
    lines = [
        "🔴 【金峰策略·紧急快讯】",
        f"🕐 {now_str}",
        "━━━━━━━━━━━━━━━━━━━",
    ]
    
    for a in articles:
        title = a.get("display", a.get("title", ""))
        summary = a.get("summary", "")
        lines.append(f"🔴 {title}")
        if summary:
            lines.append(f"    {summary[:120]}")
        lines.append("")
    
    lines.append("金峰策略 · 实时信号")
    text = "\n".join(lines)
    
    url = f"https://api.safew.bot/bot{token}/sendMessage"
    if len(text) > 4000:
        chunks, cur, cl = [], [], 0
        for l in text.split("\n"):
            ll = len(l) + 1
            if cl + ll > 3800:
                chunks.append("\n".join(cur))
                cur, cl = [l], ll
            else:
                cur.append(l)
                cl += ll
        if cur: chunks.append("\n".join(cur))
    else:
        chunks = [text]
    
    for chunk in chunks:
        r = requests.post(url, json={
            "chat_id": int(chat_id), "text": chunk,
            "disable_web_page_preview": True
        }, timeout=10)
        d = r.json()
        if d.get("ok"):
            print(f"  🔴 紧急推送 Safew msg_id={d['result']['message_id']}")
        else:
            print(f"  ❌ Safew {d}")
    
    return f"{len(articles)}条S级信号实时推送"

def push_batch(articles, now_str, is_daily=False):
    """批量推送：推A/B/C级（非紧急信号）"""
    if not PUSH_ENABLED:
        return "推送已关闭"
    if not articles:
        return "无待推内容"
    
    token = "14005993:3GJmLY4TjcPKUJG7kkaLUnNSYaVrwLu1cBT"
    chat_id = "10000698411"
    webhook = "https://open.feishu.cn/open-apis/bot/v2/hook/6bef4316-a7ec-44f1-b692-9ff1217ff8f5"
    
    # 统计
    stats = {}
    lv_stats = {"S":0,"A":0,"B":0,"C":0}
    for a in articles:
        s = a.get("source", "?")
        stats[s] = stats.get(s, 0) + 1
        lv = a.get("level", "C")
        if lv in lv_stats:
            lv_stats[lv] += 1
    
    lv_name = {"S":"交易级信号","A":"重要趋势","B":"辅助参考","C":"一般资讯"}
    lv_emoji = {"S":"🔴","A":"🟠","B":"⚡","C":"💡"}
    
    ordered = sorted(articles, key=lambda x: (
        {"S":0,"A":1,"B":2,"C":3}.get(x.get("level","C"),9), -x.get("score_num",0)
    ))
    
    # ---- Safew 推送 ----
    lines = [
        "📡 金峰策略·全球加密快讯",
        f"🕐 {now_str}",
        "",
        "📊 数据源",
    ]
    for k, v in sorted(stats.items(), key=lambda x: -x[1]):
        lines.append(f"    {k} {v}条")
    for lv in ["S","A","B","C"]:
        if lv_stats.get(lv, 0) > 0:
            lines.append(f"    {lv_emoji[lv]} {lv_name[lv]} {lv_stats[lv]}条")
    
    lines += ["", "━━━━━━━━━━━━━━━━━━━", ""]
    
    idx = 1
    for a in ordered:
        title = a.get("display", a.get("title", ""))
        lines.append(f"  {a.get('emoji','💡')} {title}")
        lines.append(f"    📈 {a.get('signal_label','观望')}")
        lines.append(f"    💡 {a.get('analysis','')}")
        lines.append("")
        idx += 1
    
    lines.append("━━━━━━━━━━━━━━━━━━━")
    lines.append("金峰策略 · 仅供研究参考 · 不构成投资建议")
    text = "\n".join(lines)
    
    url = f"https://api.safew.bot/bot{token}/sendMessage"
    if len(text) > 4000:
        chunks, cur, cl = [], [], 0
        for l in text.split("\n"):
            ll = len(l) + 1
            if cl + ll > 3800:
                chunks.append("\n".join(cur))
                cur, cl = [l], ll
            else:
                cur.append(l)
                cl += ll
        if cur: chunks.append("\n".join(cur))
    else:
        chunks = [text]
    
    for chunk in chunks:
        r = requests.post(url, json={
            "chat_id": int(chat_id), "text": chunk,
            "disable_web_page_preview": True
        }, timeout=10)
        d = r.json()
        if d.get("ok"):
            print(f"  ✅ 批量推送 Safew msg_id={d['result']['message_id']}")
        else:
            print(f"  ❌ Safew {d}")
    
    # ---- 飞书卡片 ----
    nt = ""
    for a in ordered[:10]:
        lv = a.get("level", "C")
        emoji = lv_emoji.get(lv, "💡")
        nn = lv_name.get(lv, "资讯")
        title = a.get("display", a.get("title", ""))
        nt += f"{emoji}{nn} {title}\n{a.get('summary','')[:100]}\n\n"
    
    card = {"msg_type": "interactive", "card": {
        "header": {"title": {"tag": "plain_text", "content": "📡 金峰策略·全球加密快讯"}, "template": "indigo"},
        "elements": [
            {"tag": "div", "text": {"tag": "lark_md", "content": f"🕐 {now_str}\n\n{nt}"}},
            {"tag": "hr"},
            {"tag": "note", "elements": [{"tag": "plain_text", "content": f"金峰策略 · {len(articles)}条快讯"}]}
        ]
    }}
    r2 = requests.post(webhook, json=card, timeout=10)
    d2 = r2.json()
    if d2.get("StatusCode") == 0:
        print("  ✅ 飞书")
    else:
        print(f"  ❌ 飞书 {d2}")
    
    return f"{len(articles)}条批量推送完成"

def push_daily_summary(all_articles, now_str):
    """每日汇总：全量推送（含S级+ABC级）"""
    return push_batch(all_articles, now_str, is_daily=True)

def split_and_push(articles, now_str):
    """核心分流函数：根据时段决定推送策略"""
    if not PUSH_ENABLED:
        return "推送已关闭"
    from datetime import datetime as dt
    hour = dt.now().hour
    
    # 00:00~05:59 = 静默时段，全部积压，早上6点统推
    if 0 <= hour < 6:
        _save_batch(_load_batch() + articles)
        return f"🌙 静默时段（{hour}时），{len(articles)}条全部积压至早上6点统推"
    
    # 06:00~23:59 = 正常时段
    s_articles = [a for a in articles if a.get("level") == "S"]
    abc_articles = [a for a in articles if a.get("level") in ("A", "B", "C")]
    
    result_lines = []
    
    # 1. S级实时推
    if s_articles:
        r = push_urgent(s_articles, now_str)
        result_lines.append(f"  🔴 S级: {r}")
    else:
        result_lines.append("  🔴 S级: 无S级信号")
    
    # 2. A/B/C级积压
    pending = _load_batch()
    pending.extend(abc_articles)
    
    # 对积压池去重
    seen_fp = set()
    deduped_pending = []
    for a in pending:
        title = a.get("display", a.get("title", ""))
        original = a.get("original", "")
        fp = _make_fingerprint(title, original, title)
        if fp:
            h = hashlib.md5(fp.encode()).hexdigest()[:12]
            if h not in seen_fp:
                seen_fp.add(h)
                deduped_pending.append(a)
        else:
            deduped_pending.append(a)
    
    _save_batch(deduped_pending)
    result_lines.append(f"  🟠 A/B/C: {len(abc_articles)}条已积压（池共{len(deduped_pending)}条）")
    
    return "\n".join(result_lines)

def flush_batch(now_str):
    """清空积压池并推送"""
    pending = _load_batch()
    if not pending:
        print("[清池] 积压池为空，跳过")
        return
    
    r = push_batch(pending, now_str)
    _clear_batch()
    print(f"[清池] 推送{len(pending)}条，已清空积压池")
    return r

def flush_batch_safe(now_str):
    """安全版flush：静默时段不推，继续积压"""
    if not PUSH_ENABLED:
        return
    from datetime import datetime as dt
    hour = dt.now().hour
    if 0 <= hour < 6:
        print(f"[清池] 当前{hour}时静默时段，跳过flush")
        return
    
    # 06:00整：把夜间积压的全量推一次（含S级）
    pending = _load_batch()
    if not pending:
        print("[清池] 积压池为空，跳过")
        return
    
    # 标记这是每日首推
    r = push_daily_summary(pending, now_str)
    _clear_batch()
    print(f"[清池] 首推{len(pending)}条，已清空积压池")

# ==================== 主入口 ====================

# ==================== 网站渲染 ====================

def render_site_v05(articles, now_str):
    """v0.5 SPA模式：生成数据JSON + 引用独立的前端app.js"""
    import random
    
    # 采集链上数据（BTC/ETH/SOL 合约数据+AI分析）
    try:
        from chain_data import fetch_all_chain_data, generate_chain_analysis
        raw_chain = fetch_all_chain_data(["BTC", "ETH", "SOL", "SUI", "DOGE"])
        chain_analyses = {}
        for coin in ["BTC", "ETH", "SOL", "SUI", "DOGE"]:
            if coin in raw_chain:
                analysis = generate_chain_analysis(raw_chain, coin)
                if analysis:
                    # 合并链上原始数据和AI分析
                    merged = {**raw_chain[coin], **analysis}
                    chain_analyses[coin] = merged
        chain_data_json = json.dumps({
            "coins": chain_analyses,
            "fear_greed": raw_chain.get("_fear_greed"),
            "time": raw_chain.get("_time"),
        }, ensure_ascii=False)
        print(f"[链上] 5条链上数据采集+AI分析完成")
    except Exception as e:
        print(f"[链上] 错误: {e}")
        chain_data_json = "null"
    
    # 采集财经日历（V2带历史+AI分析）
    try:
        from calendar_fetcher_v2 import run_calendar_pipeline
        proxy = 'http://127.0.0.1:10020'
        cal_events, cal_err = run_calendar_pipeline(proxies={'http': proxy, 'https': proxy}, save_db=True)
        if cal_err:
            print(f"[日历] {cal_err}")
            calendar_json = "[]"
        else:
            print(f"[日历] 采集到 {len(cal_events)} 条事件（含历史+AI分析）")
            calendar_json = json.dumps(cal_events, ensure_ascii=False)
    except Exception as e:
        print(f"[日历] 错误: {e}")
        calendar_json = "[]"
    
    # 为每个文章补充AI分析数据
    for a in articles:
        if not a.get("sentiment"):
            sig = a.get("signal_label","")
            if "偏多" in sig:
                a["sentiment"] = "bullish"
            elif "偏空" in sig:
                a["sentiment"] = "bearish"
            else:
                a["sentiment"] = "neutral"
        if not a.get("summary"):
            a["summary"] = a.get("analysis","")[:150] or ""
        a.setdefault("votes", {
            "bullish": random.randint(10,50),
            "bearish": random.randint(5,30),
            "important": random.randint(3,20)
        })
        # 从标题提取关联币种
        title_text = a.get("display",a.get("title",""))
        coins = set()
        coin_map = {"BTC":"比特币","ETH":"以太坊","SOL":"Solana","XRP":"瑞波","DOGE":"狗狗币","BNB":"币安币","ADA":"艾达币","DOT":"波卡","AVAX":"雪崩","SUI":"Sui","LINK":"Chainlink","PEPE":"佩佩","HYPE":"Hyperliquid"}
        for sym in coin_map:
            if sym.lower() in title_text.lower() or coin_map[sym] in title_text:
                coins.add(sym)
        a["coins"] = list(coins)[:3] if coins else ["ALL"]

    lv_order = {"S":0,"A":1,"B":2,"C":3}
    sorted_articles = sorted(articles, key=lambda x: (lv_order.get(x.get("level","C"),9), -x.get("score_num",0)))
    
    # JSON数据
    articles_json = json.dumps([{
        "id": i,
        "level": a.get("level","C"),
        "score": a.get("score_num",0),
        "title": a.get("display",a.get("title","")),
        "original": a.get("original",""),
        "source": a.get("source","?"),
        "url": a.get("url",""),
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "rawTime": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "sentiment": a.get("sentiment","neutral"),
        "analysis": a.get("analysis",""),
        "summary": a.get("summary",""),
        "coins": a.get("coins",["ALL"]),
        "votes": a.get("votes",{"bullish":0,"bearish":0,"important":0})
    } for i,a in enumerate(sorted_articles)], ensure_ascii=False)
    
    # v0.5 SPA: 引用独立HTML + JS，仅嵌入数据（覆盖重写以保证数据最新）
    docs_dir = os.path.join(BASE, "docs")
    html_path = os.path.join(docs_dir, "index.html")
    
    os.makedirs(docs_dir, exist_ok=True)
    
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>金峰策略 · 全球加密快讯</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=Noto+Sans+SC:wght@400;500;600;700;900&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{{margin:0;padding:0;box-sizing:border-box}}
html{{font-size:16px;-webkit-font-smoothing:antialiased}}
body{{font-family:'Inter','Noto Sans SC',-apple-system,BlinkMacSystemFont,sans-serif;background:#0a0b0e;color:#e1e4e8;min-height:100vh;overflow-x:hidden}}
::selection{{background:#ffd70033}}
::-webkit-scrollbar{{width:6px;height:6px}}
::-webkit-scrollbar-track{{background:transparent}}
::-webkit-scrollbar-thumb{{background:#2d3139;border-radius:3px}}
#nprogress{{position:fixed;top:0;left:0;right:0;z-index:9999;height:2px}}
#nprogress .bar{{height:100%;background:linear-gradient(90deg,#ffd700,#ff8c00);transition:width .3s;box-shadow:0 0 6px #ffd70066}}
.ticker{{background:linear-gradient(180deg,#0d0e12,#0a0b0e);border-bottom:1px solid #1b1d23;overflow:hidden}}
.ticker-inner{{max-width:1120px;margin:0 auto;display:flex;align-items:stretch;overflow-x:auto;scrollbar-width:none}}
.ticker-item{{display:flex;align-items:center;gap:8px;padding:10px 20px;border-right:1px solid #1b1d23;min-width:170px;flex-shrink:0}}
.ticker-symbol{{font-size:12px;font-weight:700;color:#8b949e}}
.ticker-price{{font-size:14px;font-weight:700;color:#e1e4e8;font-variant-numeric:tabular-nums}}
.ticker-change{{font-size:11px;font-weight:600;padding:2px 6px;border-radius:4px}}
.ticker-change.up{{color:#3fb950;background:#3fb95012}}
.ticker-change.down{{color:#f85149;background:#f8514912}}
.ticker-status{{margin-left:auto;padding:0 20px;display:flex;align-items:center;gap:6px;font-size:11px;color:#484f58;flex-shrink:0}}
.ticker-dot{{width:6px;height:6px;border-radius:50%}}
.ticker-dot.live{{background:#3fb950;animation:pulse-dot 2s infinite}}
@keyframes pulse-dot{{0%,100%{{opacity:1}}50%{{opacity:.4}}}}
.header{{background:#0d0e12;border-bottom:1px solid #1b1d23;position:sticky;top:0;z-index:100}}
.header-inner{{max-width:1120px;margin:0 auto;display:flex;align-items:center;justify-content:space-between;padding:14px 20px}}
.header-left{{display:flex;align-items:center;gap:12px}}
.header-logo{{width:32px;height:32px;background:linear-gradient(135deg,#ffd700,#ff8c00);border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:16px;font-weight:900;color:#0a0b0e;flex-shrink:0}}
.header h1{{font-size:18px;font-weight:800;color:#fff;display:flex;align-items:center;gap:8px}}
.header h1 .badge{{font-size:9px;font-weight:600;padding:2px 6px;border-radius:4px;background:#ffd70020;color:#ffd700}}
.header-time{{font-size:12px;color:#484f58}}
.filter-bar{{max-width:1120px;margin:0 auto;padding:10px 20px 0;display:flex;gap:8px;align-items:center;flex-wrap:wrap}}
.search-wrap{{flex:1;min-width:180px;position:relative}}
.search-wrap input{{width:100%;background:#121318;border:1px solid #1b1d23;border-radius:8px;padding:9px 14px 9px 34px;color:#e1e4e8;font-size:13px;outline:none;transition:border .2s}}
.search-wrap input:focus{{border-color:#ffd700}}
.search-icon{{position:absolute;left:12px;top:50%;transform:translateY(-50%);color:#484f58;font-size:13px;pointer-events:none}}
.sort-btn{{background:none;border:1px solid #1b1d23;border-radius:6px;padding:6px 12px;font-size:12px;color:#484f58;cursor:pointer;transition:all .15s}}
.sort-btn:hover{{border-color:#30363d;color:#8b949e}}
.sort-btn.active{{border-color:#ffd70044;color:#ffd700}}
.stats-bar{{max-width:1120px;margin:0 auto;padding:8px 20px 0;display:flex;gap:6px;flex-wrap:wrap}}
.stat-card{{flex:1;min-width:90px;background:#0d0e12;border:1px solid #1b1d23;border-radius:10px;padding:10px 12px;cursor:pointer;transition:all .2s;position:relative;overflow:hidden}}
.stat-card:hover{{border-color:#30363d}}
.stat-card.active{{border-color:#ffd70044;background:#ffd70008}}
.stat-card .num{{font-size:20px;font-weight:800;font-variant-numeric:tabular-nums;line-height:1.2}}
.stat-card .label{{font-size:11px;color:#484f58;margin-top:2px}}
.stat-card .bar-bg{{position:absolute;bottom:0;left:0;right:0;height:2px;background:#1b1d23;overflow:hidden}}
.stat-card .bar-fill{{height:100%;transition:width .5s}}
.stat-s .num{{color:#ff4444}}.stat-s .bar-fill{{background:#ff4444}}
.stat-a .num{{color:#ff8c00}}.stat-a .bar-fill{{background:#ff8c00}}
.stat-b .num{{color:#f0c040}}.stat-b .bar-fill{{background:#f0c040}}
.stat-c .num{{color:#888}}.stat-c .bar-fill{{background:#888}}
.coin-bar{{max-width:1120px;margin:0 auto;padding:8px 20px 0;display:flex;gap:5px;flex-wrap:wrap;overflow-x:auto;scrollbar-width:none}}
.coin-pill{{background:#121318;border:1px solid #1b1d23;border-radius:16px;padding:5px 12px;font-size:12px;font-weight:500;color:#8b949e;cursor:pointer;transition:all .15s;white-space:nowrap;display:flex;align-items:center;gap:4px}}
.coin-pill:hover{{border-color:#30363d;color:#e1e4e8}}
.coin-pill.active{{border-color:#ffd70044;color:#ffd700;background:#ffd70008}}
.coin-pill .dot{{width:6px;height:6px;border-radius:50%}}
.coin-pill .dot.btc{{background:#f0c040}}.coin-pill .dot.eth{{background:#8b9dc0}}.coin-pill .dot.sol{{background:#9945ff}}
.coin-pill .dot.bnb{{background:#f3ba2f}}.coin-pill .dot.doge{{background:#c2a633}}.coin-pill .dot.xrp{{background:#00aae4}}
.coin-pill .dot.hype{{background:#ff6b6b}}.coin-pill .dot.sui{{background:#6fbcf0}}
.main-layout{{max-width:1120px;margin:0 auto;padding:12px 20px 60px;display:grid;grid-template-columns:1fr 280px;gap:20px}}
@media(max-width:900px){{.main-layout{{grid-template-columns:1fr}}.sidebar{{display:none}}}}
.news-feed{{min-width:0}}
.news-feed-header{{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px}}
.news-feed-header h2{{font-size:13px;color:#8b949e;font-weight:500}}
.news-feed-header .count{{font-size:11px;color:#484f58}}
#update-status{{font-size:10px;color:#484f58;opacity:0;transition:opacity .5s}}
#update-status.show{{opacity:1}}
.card{{background:#0d0e12;border:1px solid #1b1d23;border-radius:12px;margin-bottom:8px;display:flex;overflow:hidden;transition:all .2s;animation:cardIn .3s ease forwards;opacity:0;transform:translateY(8px)}}
@keyframes cardIn{{to{{opacity:1;transform:translateY(0)}}}}
.card:hover{{border-color:#30363d}}
.card.level-s{{background:linear-gradient(180deg,#ff444408,transparent)}}
.card.level-a{{background:linear-gradient(180deg,#ff8c0008,transparent)}}
.card.level-b{{background:linear-gradient(180deg,#f0c04004,transparent)}}
.card .left-border{{width:4px;flex-shrink:0;border-radius:12px 0 0 12px}}
.card-votes{{display:flex;flex-direction:column;align-items:center;gap:2px;padding:12px 4px 12px 10px;min-width:28px}}
.vote-btn{{background:none;border:none;color:#484f58;cursor:pointer;font-size:11px;padding:3px 5px;border-radius:4px;transition:all .15s;line-height:1}}
.vote-btn.up:hover,.vote-btn.up.voted{{color:#3fb950}}
.vote-btn.down:hover,.vote-btn.down.voted{{color:#f85149}}
.vote-btn.imp:hover,.vote-btn.imp.voted{{color:#ffd700}}
.card-body{{flex:1;padding:12px 12px 12px 4px;min-width:0}}
.card-header{{display:flex;align-items:center;gap:4px;margin-bottom:5px;flex-wrap:wrap}}
.level-badge{{font-size:9px;font-weight:700;padding:2px 7px;border-radius:4px}}
.source-badge{{font-size:10px;color:#8b949e;padding:1px 6px;border-radius:4px}}
.coin-tag{{font-size:9px;font-weight:600;padding:1px 5px;border-radius:3px;background:#1b1d23;color:#58a6ff}}
.time-tag{{font-size:10px;color:#484f58;margin-left:auto;white-space:nowrap}}
.card-title{{font-size:14px;font-weight:600;line-height:1.45;color:#e1e4e8;margin-bottom:4px}}
.card-summary{{font-size:11px;color:#8b949e;line-height:1.5;margin-bottom:4px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}}
.ai-block{{margin-top:8px;background:#121318;border:1px solid #1b1d23;border-radius:8px;padding:10px 12px;display:none}}
.card.expanded .ai-block{{display:block}}
.ai-header{{display:flex;align-items:center;gap:6px;margin-bottom:6px}}
.ai-header .label{{font-size:9px;font-weight:700;padding:1px 6px;border-radius:3px;background:linear-gradient(135deg,#ffd700,#ff8c00);color:#0a0b0e}}
.ai-tags{{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:6px}}
.ai-tag{{font-size:10px;padding:2px 8px;border-radius:4px;font-weight:500}}
.ai-tag.impact-high{{background:#ff444415;color:#ff4444}}
.ai-tag.impact-mid{{background:#ff8c0015;color:#ff8c00}}
.ai-tag.impact-low{{background:#88815;color:#888}}
.ai-tag.dir-bullish{{background:#3fb95015;color:#3fb950}}
.ai-tag.dir-bearish{{background:#f8514915;color:#f85149}}
.ai-tag.dir-neutral{{background:#8b949e15;color:#8b949e}}
.ai-reason{{font-size:11px;color:#8b949e;line-height:1.6}}
.ai-strategy{{font-size:11px;line-height:1.5;margin-top:6px;padding:6px 8px;background:#1b1d23;border-radius:6px;border-left:2px solid #ffd70044;color:#f0c040}}
.card-footer{{display:flex;align-items:center;gap:10px;margin-top:6px}}
.expand-btn{{background:none;border:none;font-size:11px;color:#484f58;cursor:pointer;display:flex;align-items:center;gap:4px;transition:color .15s;padding:2px 0}}
.expand-btn:hover{{color:#ffd700}}
.expand-btn .arrow{{display:inline-block;transition:transform .2s}}
.card.expanded .expand-btn .arrow{{transform:rotate(180deg)}}
.sidebar{{position:sticky;top:120px;align-self:start}}
.sidebar-section{{background:#0d0e12;border:1px solid #1b1d23;border-radius:12px;padding:14px;margin-bottom:10px}}
.sidebar-section h3{{font-size:11px;color:#8b949e;font-weight:600;margin-bottom:10px;text-transform:uppercase;letter-spacing:1px}}
.sidebar-section p{{font-size:12px;color:#8b949e;line-height:1.8}}
.sidebar-section a{{color:#58a6ff;text-decoration:none}}
.sidebar-section a:hover{{text-decoration:underline}}
.sentiment-bar{{display:flex;height:6px;border-radius:3px;overflow:hidden;margin-bottom:8px}}
.sentiment-bar .seg{{transition:width .5s}}
.sentiment-bar .bullish{{background:#3fb950}}.sentiment-bar .bearish{{background:#f85149}}.sentiment-bar .neutral{{background:#8b949e}}
.sentiment-row{{display:flex;justify-content:space-between;font-size:11px;color:#8b949e;margin-bottom:2px}}
.sentiment-row .val{{font-weight:600;color:#e1e4e8}}
.hot-topic{{display:inline-flex;align-items:center;gap:4px;background:#121318;border:1px solid #1b1d23;border-radius:14px;padding:4px 10px;font-size:11px;color:#8b949e;margin:2px;cursor:pointer}}
.hot-topic:hover{{border-color:#58a6ff}}
.hot-topic .ht-count{{font-size:9px;background:#1b1d23;padding:0 4px;border-radius:3px;line-height:14px}}
.source-row{{display:flex;justify-content:space-between;align-items:center;padding:3px 0;font-size:11px;color:#8b949e}}
.source-row .src-bar-wrap{{flex:1;margin:0 8px;height:3px;background:#1b1d23;border-radius:2px;overflow:hidden}}
.source-row .src-bar-fill{{height:100%;background:#ffd700;border-radius:2px}}
.source-row .src-val{{color:#e1e4e8;font-weight:600;font-size:10px}}
.fng-display{{font-size:20px;font-weight:800;text-align:center;padding:8px 0}}
.fng-display.extreme-fear{{color:#f85149}}
.fng-display.fear{{color:#ff8c00}}
.fng-display.neutral{{color:#8b949e}}
.fng-display.greed{{color:#3fb950}}
.fng-display.extreme-greed{{color:#3fb950}}
.sidebar-toggle-mobile{{display:none;position:fixed;bottom:20px;right:20px;z-index:99;width:44px;height:44px;border-radius:50%;background:linear-gradient(135deg,#ffd700,#ff8c00);border:none;color:#0a0b0e;font-size:18px;cursor:pointer;box-shadow:0 4px 16px #ffd70033}}
.sidebar-overlay{{display:none;position:fixed;inset:0;z-index:199;background:#00000088}}
.sidebar-mobile{{display:none;position:fixed;top:0;right:0;bottom:0;width:300px;z-index:200;background:#0a0b0e;border-left:1px solid #1b1d23;overflow-y:auto;padding:20px;transform:translateX(100%);transition:transform .3s}}
.sidebar-mobile.open{{transform:translateX(0)}}
@media(max-width:900px){{.sidebar-toggle-mobile{{display:flex;align-items:center;justify-content:center}}.sidebar-overlay.open{{display:block}}.sidebar-mobile.open{{display:block}}}}
.footer{{text-align:center;padding:24px 20px;border-top:1px solid #1b1d23;max-width:1120px;margin:0 auto}}
.footer p{{font-size:11px;color:#484f58}}
.footer .update-badge{{display:inline-flex;align-items:center;gap:4px;margin-top:6px;padding:4px 10px;background:#121318;border:1px solid #1b1d23;border-radius:20px;font-size:10px;color:#8b949e}}
.empty-state{{text-align:center;padding:60px 20px;color:#484f58}}
.card-fast{{animation:cardIn .15s ease forwards;opacity:0;transform:translateY(6px)}}
.card.hidden{{display:none!important}}
.vote-count{{font-size:8px;display:block;line-height:1;margin-top:1px;color:#484f58;font-weight:600}}
/* ===== 财经日历样式 V2 ===== */
.cal-date-group{{margin-bottom:12px;padding-bottom:12px;border-bottom:1px solid #1b1d23}}
.cal-date-group:last-child{{border-bottom:none;margin-bottom:0}}
.cal-date-hdr{{font-size:11px;font-weight:600;color:#8b949e;margin-bottom:6px;letter-spacing:.3px}}
.cal-today .cal-date-hdr{{color:#ffd700}}
.cal-ev{{padding:6px 8px;margin-bottom:4px;border-radius:6px;font-size:10px;line-height:1.4;background:#121318;cursor:pointer;transition:all .2s}}
.cal-ev:hover{{background:#1b1d23}}
.cal-ev.expanded{{background:#161b22;border-color:#30363d}}
.cal-ev.imp-hi{{border-left:3px solid #f85149}}
.cal-ev.imp-md{{border-left:3px solid #d29922}}
.cal-ev-header{{display:flex;align-items:center;gap:4px;flex-wrap:wrap}}
.cal-tm{{color:#484f58;font-family:monospace;font-size:9px;min-width:36px}}
.cal-ccy{{display:inline-block;padding:0 4px;border-radius:3px;background:#1b1d23;color:#ffd700;font-size:9px;font-weight:700;letter-spacing:.5px}}
.cal-tl{{color:#c9d1d9;flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:500}}
.cal-ev.expanded .cal-tl{{white-space:normal;overflow:visible}}
.cal-impact-badge{{font-size:8px;padding:1px 4px;border-radius:3px;background:#f8514915;color:#f85149;font-weight:600}}
.cal-vals{{display:flex;gap:6px;margin-top:3px;flex-wrap:wrap}}
.cal-val{{font-size:9px;padding:1px 5px;border-radius:3px}}
.cal-val.act{{color:#3fb950;background:#3fb95015}}
.cal-val.fcast{{color:#d29922;background:#d2992215}}
.cal-val.prev{{color:#8b949e;background:#8b949e15}}
/* AI 分析盒子 */
.cal-detail-content{{padding:6px 0 2px}}
.cal-ai-box{{border:1px solid #1b1d23;border-radius:6px;padding:6px 8px;margin-top:4px;background:#0d1117}}
.cal-ai-hdr{{font-size:9px;font-weight:700;color:#58a6ff;margin-bottom:4px;display:flex;align-items:center;gap:4px}}
.cal-ai-hdr::before{{content:'';display:inline-block;width:4px;height:4px;border-radius:50%;background:#58a6ff;animation:pulse-dot 2s infinite}}
.cal-ai-row{{font-size:9px;color:#8b949e;margin:2px 0;line-height:1.5}}
.cal-ai-label{{color:#c9d1d9;font-weight:600}}
/* 数据对比历史条 */
.cal-hist-box{{border:1px solid #1b1d23;border-radius:6px;padding:6px 8px;margin-top:4px;background:#0d1117}}
.cal-hist-hdr{{font-size:9px;font-weight:700;color:#8b949e;margin-bottom:4px}}
.cal-hist-row{{display:flex;align-items:center;gap:4px;margin:2px 0;font-size:9px}}
.cal-hist-lbl{{width:20px;color:#8b949e}}
.cal-hist-bar-wrap{{flex:1;height:6px;background:#1b1d23;border-radius:3px;overflow:hidden}}
.cal-hist-bar{{height:100%;border-radius:3px;transition:width .5s}}
.cal-hist-bar.prev{{background:#8b949e}}
.cal-hist-bar.fcast{{background:#d29922}}
.cal-hist-bar.act{{background:#3fb950}}
.cal-hist-val{{width:40px;text-align:right;color:#c9d1d9}}
/* 更多按钮 */
.cal-more-bar{{text-align:center;padding:4px 0}}
.cal-more-btn{{font-size:9px;padding:4px 12px;border-radius:20px;background:#121318;border:1px solid #1b1d23;color:#8b949e;cursor:pointer;transition:all .2s}}
.cal-more-btn:hover{{background:#1b1d23;color:#c9d1d9}}
.cal-open-full{{display:inline-block;font-size:10px;padding:4px 12px;border-radius:20px;background:#121318;border:1px solid #1b1d23;color:#58a6ff;text-decoration:none;transition:all .2s}}
.cal-open-full:hover{{background:#1b1d23;color:#58a6ff;border-color:#58a6ff33}}
.cal-empty{{text-align:center;color:#484f58;padding:12px 0;font-size:11px}}
@media(max-width:900px){{.cal-ev{{font-size:11px}}.cal-val{{font-size:10px}}.cal-ai-row{{font-size:10px}}}}
/* ===== 链上数据弹窗 ===== */
.chain-overlay{{display:none;position:fixed;inset:0;z-index:299;background:#00000088;backdrop-filter:blur(2px)}}
.chain-overlay.open{{display:block}}
.chain-modal{{display:none;position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);z-index:300;width:480px;max-width:90vw;max-height:85vh;background:#0d0e12;border:1px solid #30363d;border-radius:16px;overflow:hidden;box-shadow:0 20px 60px #00000066}}
.chain-modal.open{{display:flex;flex-direction:column}}
.chain-modal-header{{display:flex;align-items:center;justify-content:space-between;padding:16px 20px;border-bottom:1px solid #1b1d23;background:#121318}}
.chain-modal-title{{font-size:18px;font-weight:800;color:#e1e4e8;display:flex;align-items:center;gap:8px}}
.chain-close-btn{{background:none;border:none;color:#484f58;font-size:20px;cursor:pointer;width:32px;height:32px;border-radius:8px;display:flex;align-items:center;justify-content:center;transition:all .15s}}
.chain-close-btn:hover{{background:#1b1d23;color:#e1e4e8}}
.chain-modal-body{{padding:20px;overflow-y:auto;flex:1}}
.chain-loading{{text-align:center;padding:30px;color:#484f58;font-size:14px}}
.chain-score{{text-align:center;padding:10px 0 16px}}
.chain-score-num{{font-size:42px;font-weight:900;display:block;line-height:1}}
.chain-score-label{{font-size:12px;color:#484f58;margin-top:4px}}
.chain-score-bar{{width:200px;height:6px;background:#1b1d23;border-radius:3px;margin:8px auto;overflow:hidden}}
.chain-score-fill{{height:100%;border-radius:3px;transition:width .8s}}
.chain-metrics{{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:12px 0}}
.chain-metric{{background:#121318;border:1px solid #1b1d23;border-radius:10px;padding:10px 12px}}
.chain-metric .label{{font-size:10px;color:#484f58;margin-bottom:3px}}
.chain-metric .value{{font-size:16px;font-weight:700;color:#e1e4e8;font-variant-numeric:tabular-nums}}
.chain-metric .sub{{font-size:10px;color:#8b949e;margin-top:2px}}
.chain-metric .value.up{{color:#3fb950}}
.chain-metric .value.down{{color:#f85149}}
.chain-signals{{margin:12px 0}}
.chain-signal{{display:flex;align-items:flex-start;gap:8px;padding:8px 12px;background:#121318;border:1px solid #1b1d23;border-radius:8px;margin-bottom:4px;font-size:12px;color:#c9d1d9;line-height:1.5}}
.chain-signal .emoji{{width:20px;text-align:center;flex-shrink:0;font-size:14px}}
.chain-summary{{background:#121318;border:1px solid #1b1d23;border-radius:8px;padding:12px;margin:12px 0;border-left:3px solid #ffd70044}}
.chain-summary .label{{font-size:10px;color:#58a6ff;font-weight:600;margin-bottom:4px}}
.chain-summary .text{{font-size:13px;color:#c9d1d9;line-height:1.6}}
.chain-chart{{margin:12px 0;padding:10px;background:#121318;border:1px solid #1b1d23;border-radius:8px}}
.chain-chart svg{{display:block}}
.ticker-coin{{cursor:pointer;transition:background .15s}}
.ticker-coin:hover{{background:#1b1d23}}
@media(max-width:600px){{.chain-metrics{{grid-template-columns:1fr}}.chain-modal{{width:92vw}}}}
</style>
</head>
<body>
<div id="nprogress"><div class="bar" id="nprogress-bar"></div></div>
<div class="ticker"><div class="ticker-inner" id="ticker-bar">
<div class="ticker-item ticker-coin" onclick="openChainPanel('BTC')" title="点击查看BTC链上数据分析"><span class="ticker-symbol">BTC</span><span class="ticker-price" id="btc-price">—</span><span class="ticker-change" id="btc-change"></span></div>
<div class="ticker-item ticker-coin" onclick="openChainPanel('ETH')" title="点击查看ETH链上数据分析"><span class="ticker-symbol">ETH</span><span class="ticker-price" id="eth-price">—</span><span class="ticker-change" id="eth-change"></span></div>
<div class="ticker-item ticker-coin" onclick="openChainPanel('SOL')" title="点击查看SOL链上数据分析"><span class="ticker-symbol">SOL</span><span class="ticker-price" id="sol-price">—</span><span class="ticker-change" id="sol-change"></span></div>
<div class="ticker-item ticker-coin" onclick="openChainPanel('SUI')" title="点击查看SUI链上数据分析"><span class="ticker-symbol">SUI</span><span class="ticker-price" id="sui-price">—</span><span class="ticker-change" id="sui-change"></span></div>
<div class="ticker-item ticker-coin" onclick="openChainPanel('DOGE')" title="点击查看DOGE链上数据分析"><span class="ticker-symbol">DOGE</span><span class="ticker-price" id="doge-price">—</span><span class="ticker-change" id="doge-change"></span></div>
<div class="ticker-status"><span class="ticker-dot live"></span><span>实时</span></div>
</div></div>
<header class="header"><div class="header-inner"><div class="header-left"><div class="header-logo">金</div><h1>金峰策略 <span class="badge">v0.5</span></h1></div><span class="header-time" id="header-time">🕐 更新中…</span></div></header>
<div class="filter-bar"><div class="search-wrap"><span class="search-icon">🔍</span><input type="text" id="search-input" placeholder="搜索新闻标题或关键词..."></div>
<div class="filter-actions"><button class="sort-btn active" id="sort-latest">🕐 最新</button><button class="sort-btn" id="sort-hot">🔥 最热</button></div></div>
<div class="stats-bar" id="stats-bar">
<div class="stat-card stat-s" onclick="filterByLevel('ALL')"><div class="num" id="stat-all">0</div><div class="label">📰 全部</div><div class="bar-bg"><div class="bar-fill" id="bar-all" style="width:100%"></div></div></div>
<div class="stat-card stat-s" onclick="filterByLevel('S')"><div class="num" id="stat-s">0</div><div class="label">🔴 交易级</div><div class="bar-bg"><div class="bar-fill" id="bar-s"></div></div></div>
<div class="stat-card stat-a" onclick="filterByLevel('A')"><div class="num" id="stat-a">0</div><div class="label">🟠 重要趋势</div><div class="bar-bg"><div class="bar-fill" id="bar-a"></div></div></div>
<div class="stat-card stat-b" onclick="filterByLevel('B')"><div class="num" id="stat-b">0</div><div class="label">⚡ 辅助参考</div><div class="bar-bg"><div class="bar-fill" id="bar-b"></div></div></div>
<div class="stat-card stat-c" onclick="filterByLevel('C')"><div class="num" id="stat-c">0</div><div class="label">💡 一般资讯</div><div class="bar-bg"><div class="bar-fill" id="bar-c"></div></div></div></div>
<div class="coin-bar">
<button class="coin-pill active" onclick="filterByCoin('ALL')">🌟 全部</button>
<button class="coin-pill" onclick="filterByCoin('BTC')"><span class="dot btc"></span>BTC</button>
<button class="coin-pill" onclick="filterByCoin('ETH')"><span class="dot eth"></span>ETH</button>
<button class="coin-pill" onclick="filterByCoin('SOL')"><span class="dot sol"></span>SOL</button>
<button class="coin-pill" onclick="filterByCoin('BNB')"><span class="dot bnb"></span>BNB</button>
<button class="coin-pill" onclick="filterByCoin('DOGE')"><span class="dot doge"></span>DOGE</button>
<button class="coin-pill" onclick="filterByCoin('XRP')"><span class="dot xrp"></span>XRP</button>
<button class="coin-pill" onclick="filterByCoin('HYPE')"><span class="dot hype"></span>HYPE</button>
<button class="coin-pill" onclick="filterByCoin('SUI')"><span class="dot sui"></span>SUI</button>
</div>
<div class="main-layout"><div class="news-feed"><div class="news-feed-header"><h2>📰 快讯 <span class="count" id="feed-count"></span></h2><span id="update-status"></span></div><div id="news-list"></div></div>
<aside class="sidebar" id="sidebar-desktop">
<div class="sidebar-section"><h3>😱 恐惧与贪婪</h3><div class="fng-display" id="fng-value">加载中…</div></div>
<div class="sidebar-section"><h3>📊 情绪分布</h3><div class="sentiment-bar" id="sentiment-bar"><div class="seg bullish" style="width:0%"></div><div class="seg bearish" style="width:0%"></div><div class="seg neutral" style="width:0%"></div></div><div id="sentiment-stats"></div></div>
<div class="sidebar-section"><h3>🔥 热门话题</h3><div id="hot-topics"></div></div>
<div class="sidebar-section"><h3>📡 数据源分布</h3><div id="source-dist"></div></div>
<div class="sidebar-section"><h3>🔗 更多资源</h3><p><a href="https://cryptopanic.com" target="_blank">→ CryptoPanic</a><br><a href="https://www.panewslab.com" target="_blank">→ PANews</a><br><a href="https://cointelegraph.com" target="_blank">→ Cointelegraph</a><br><a href="https://bitcoinmagazine.com" target="_blank">→ Bitcoin Magazine</a></p></div>
<div class="sidebar-section"><h3>📅 财经日历</h3><div id="calendar-panel">加载中…</div><div style="margin-top:6px;text-align:center"><a href="./calendar.html" class="cal-open-full" target="_blank">📊 打开完整日历 →</a></div></div>
</aside></div>
<button class="sidebar-toggle-mobile" id="sidebar-toggle" onclick="toggleMobileSidebar()">📊</button>
<div class="sidebar-overlay" id="sidebar-overlay" onclick="toggleMobileSidebar()"></div>
<div class="sidebar-mobile" id="sidebar-mobile"></div>
<footer class="footer"><p>金峰策略 · 全球加密快讯 · 仅供研究参考 · 不构成投资建议</p><div class="update-badge" id="footer-update">🕐 更新于 —</div></footer>
<script src="app.js?v=1783743866"></script>
<script>var DATA = ''' + articles_json + '''; var CALENDAR_DATA = ''' + calendar_json + '''; var CHAIN_DATA = ''' + chain_data_json + '''; renderCards(DATA);</script>

<!-- ===== 链上数据弹窗 ===== -->
<div class="chain-overlay" id="chain-overlay" onclick="closeChainPanel()"></div>
<div class="chain-modal" id="chain-modal">
  <div class="chain-modal-header">
    <span class="chain-modal-title" id="chain-modal-title">BTC 链上数据分析</span>
    <button class="chain-close-btn" onclick="closeChainPanel()">✕</button>
  </div>
  <div class="chain-modal-body" id="chain-modal-body">
    <div class="chain-loading">加载中…</div>
  </div>
</div>
</body>
</html>'''
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\n✅ v0.5网站已生成: {html_path} ({len(html)/1024:.0f}KB)")
    
    # 同步生成日历独立页面
    try:
        from calendar_page import load_all_events, render_calendar_page
        cal_evts = load_all_events()
        if cal_evts:
            render_calendar_page(cal_evts)
        else:
            print("[日历页] 无数据，跳过")
    except Exception as e:
        print(f"[日历页] 生成失败: {e}")
    
    return html

def run(panews_raw="", cryptopanic_raw="", cointelegraph_raw="", bitcoinmag_raw="", coindesk_raw="", decrypt_raw="", skip_push=False):
    """全流程。传空字符串=使用内嵌测试数据。skip_push=True=不推送，只返回评分结果"""
    print("=" * 60)
    print(f"📡 Signal v0.3 @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    all_articles = []
    
    # ===== 数据源1: PANews =====
    if not panews_raw:
        panews_raw = r"""2025/07/11 09:00 PA一线
CoinGlass：过去24小时爆仓逾2.35亿美元，主爆空单
1分钟前
Circle获OCC批准 迈出合规化关键一步
5分钟前
Kraken 推出 AI 代理交易功能
10分钟前
USDC Treasury 在 Solana 上新铸造 2.5 亿枚 USDC
15分钟前
BNB Chain 推出 AI 代理链
20分钟前
Aave V3 上线 zkSync
25分钟前
Bitcoin Magazine：Metaplanet 联合研究 BTC 抵押数字信贷登陆日本
30分钟前
现代汽车在 Avalanche 公链上线内部跨境汇款系统
35分钟前
Polymarket 正式申请美国 NFA 牌照
40分钟前
美国民主党高层在投票前夕抨击特朗普加密货币政策
45分钟前
地址 0xf02d 亏损 452 万美元后再次 10 倍杠杆做空 HYPE
50分钟前"""
    zh = parse_panews(panews_raw)
    for a in zh:
        a["display"] = a["title"]
    all_articles.extend(zh)
    print(f"[采集] PANews: {len(zh)}条")
    
    # ===== 数据源2: CryptoPanic =====
    if not cryptopanic_raw:
        cryptopanic_raw = r"""Strategy Bitcoin Selling Spooks Market, But Standard Chartered Still Sees $100K by Year-End
25 minutes ago · CryptoSlate
华尔街准备迎接 BTC 暴涨，衍生品市场信号强烈
40 minutes ago · CoinDesk
交易所挤兑警告！某 Top 10 交易所储备金降至历史低点
50 minutes ago · The Block
James Wynn高杠杆做空标普500屡遭爆仓，累计亏损2200万美元
1 hour ago · Finance Feed
巨鲸亏损452万美元后再次10倍杠杆做空HYPE
1 hour ago · Whale Alert
加密友好银行Nubank获墨西哥银行牌照
2 hours ago · CoinDesk
传统金融市场冲击！30年期美债收益率创年内新高
2 hours ago · Bloomberg
Tom Lee：加密是新存储交易，BTC长期看多至15万美元
2 hours ago · CNBC
稳定币监管走向分化：Circle合规加速 vs Tether面临欧盟挑战
3 hours ago · The Block
Bitfinex分析师：BTC回调属健康修正，技术指标仍指向上涨
3 hours ago · Crypto News
剑桥大学发布2025年全球加密资产基准研究报告
3 hours ago · Cambridge Research"""
    
    en_cp = parse_cryptopanic(cryptopanic_raw)
    for a in en_cp:
        tr = translate_en(a["title"])
        if tr:
            a["display"] = tr
            a["original"] = a["title"]
        else:
            a["display"] = a["title"]
    all_articles.extend(en_cp)
    print(f"[采集] CryptoPanic: {len(en_cp)}条")
    
    # ===== 数据源3: Cointelegraph =====
    if not cointelegraph_raw:
        cointelegraph_raw = r"""BTC跌破64000美元，日内涨幅1.78%
2025-07-11T00:15:00Z
https://cointelegraph.com/news/btc-drops-below-64000
Metaplanet联合研究：BTC抵押数字信贷登陆日本
2025-07-10T23:50:00Z
https://cointelegraph.com/news/metaplanet-btc-collateral-digital-loan-japan
现代汽车在Avalanche公链上线内部跨境汇款系统
2025-07-10T23:30:00Z
https://cointelegraph.com/news/hyundai-avalanche-cross-border-remittance"""
    
    en_ct = parse_rss_xml(cointelegraph_raw, "Cointelegraph")
    for a in en_ct:
        tr = translate_en(a["title"])
        a["display"] = tr or f"📰 {a['title'][:60]}"
        if tr: a["original"] = a["title"]
    all_articles.extend(en_ct)
    print(f"[采集] Cointelegraph: {len(en_ct)}条")
    
    # ===== 数据源4: Bitcoin Magazine =====
    if not bitcoinmag_raw:
        bitcoinmag_raw = r"""Metaplanet Partners with Research Firm for Bitcoin-Backed Digital Lending in Japan
2025-07-10T23:00:00Z
https://bitcoinmagazine.com/articles/metaplanet-bitcoin-backed-lending-japan"""
    
    en_bm = parse_rss_xml(bitcoinmag_raw, "Bitcoin Magazine")
    for a in en_bm:
        a["display"] = "Metaplanet联合研究：BTC抵押数字信贷登陆日本"
        a["original"] = a["title"]
    all_articles.extend(en_bm)
    print(f"[采集] Bitcoin Magazine: {len(en_bm)}条")
    
    # ===== 数据源5: CoinDesk (模拟数据，正式接入需要web_fetch) =====
    coindesk_articles = [
        {"title": "Bitcoin Mining Difficulty Hits New All-Time High as Network Hashrate Surges", "source": "CoinDesk", "url": "https://www.coindesk.com/"},
        {"title": "Ethereum Layer 2 TVL Breaks $50B as Base Leads Growth", "source": "CoinDesk", "url": "https://www.coindesk.com/"}
    ]
    for a in coindesk_articles:
        tr = translate_en(a["title"])
        a["display"] = tr or a["title"]
        if tr: a["original"] = a["title"]
    all_articles.extend(coindesk_articles)
    print(f"[采集] CoinDesk: {len(coindesk_articles)}条")
    
    # ===== 数据源6: Decrypt (模拟数据) =====
    decrypt_articles = [
        {"title": "Solana NFT Sales Volume Up 40% in Q2 Despite Broader Market Slump", "source": "Decrypt", "url": "https://decrypt.co/"},
        {"title": "US Lawmakers Reintroduce Stablecoin Bill with Bipartisan Support", "source": "Decrypt", "url": "https://decrypt.co/"}
    ]
    for a in decrypt_articles:
        tr = translate_en(a["title"])
        a["display"] = tr or a["title"]
        if tr: a["original"] = a["title"]
    all_articles.extend(decrypt_articles)
    print(f"[采集] Decrypt: {len(decrypt_articles)}条")
    
    # ===== 去重 =====
    total = len(all_articles)
    all_articles = dedup(all_articles)
    print(f"\n[处理] 去重: {total} → {len(all_articles)}条")
    
    # ===== 四层评分 =====
    print(f"[评分] 四层评分...")
    filtered = engine.score_batch(all_articles)
    for a in filtered:
        if not a.get("display"):
            a["display"] = a.get("title", "")
    
    lv_order = {"S": 0, "A": 1, "B": 2, "C": 3}
    filtered.sort(key=lambda x: (lv_order.get(x.get("level","C"), 9), -x.get("score_num", 0)))
    
    print(f"[评分] 结果: {len(filtered)}条通过")
    for a in filtered:
        print(f"  {a.get('emoji','💡')} [{a.get('level','C')}][{a.get('score_num',0)}分] {a.get('display','')[:50]}")
    
    # ===== DeepSeek AI 见解生成 =====
    print(f"\n[AI] DeepSeek分析中...")
    filtered = generate_insight_batch(filtered, deep=True)
    
    # ===== 推送（分层：S级实时，A/B/C积压） =====
    if not filtered:
        print("\n[推送] 无内容可推送")
        return
    
    if skip_push:
        print(f"\n[跳过推送] --html模式，返回{len(filtered)}条")
        return filtered
    
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M CST")
    print(f"\n[推送] {len(filtered)}条分推...")
    result = split_and_push(filtered, now_str)
    print(f"\n✅ {result}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--flush", action="store_true", help="清空积压池并推送（已禁用）")
    parser.add_argument("--push", action="store_true", help="强制启用推送（覆盖配置）")
    args = parser.parse_args()
    
    import sys as _sys
    module = _sys.modules[__name__]
    if args.push:
        module.PUSH_ENABLED = True
    
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M CST")
    
    if args.flush:
        flush_batch_safe(now_str)
    else:
        # 默认模式：采集→评分→生成网站（不推送）
        filtered = run(skip_push=True)
        if filtered:
            html = render_site_v05(filtered, now_str)
        else:
            print("\n⚠️ 无评分通过的资讯，网站未更新")
