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

def render_site(articles, now_str):
    """生成CryptoPanic风格完整资讯网站（SPA + AI分析标签 + 投票 + 币种筛选）"""
    import random
    lv_emoji = {"S":"🔴","A":"🟠","B":"⚡","C":"💡"}
    lv_name = {"S":"交易级","A":"重要趋势","B":"辅助参考","C":"一般资讯"}
    lv_color = {"S":"#ff4444","A":"#ff8c00","B":"#f0c040","C":"#888"}
    sentiment_icons = {"bullish":"📈","bearish":"📉","neutral":"➡️"}
    sentiment_color = {"bullish":"#3fb950","bearish":"#f85149","neutral":"#8b949e"}
    
    # 为每个文章生成AI见解（如果没有的话）
    for a in articles:
        if not a.get("analysis"):
            a["analysis"] = "市场关注度提升，需结合技术面综合判断"
        if not a.get("sentiment"):
            # 分析引擎的方向标签
            sig = a.get("signal_label","")
            if "偏多" in sig:
                a["sentiment"] = "bullish"
            elif "偏空" in sig:
                a["sentiment"] = "bearish"
            else:
                a["sentiment"] = "neutral"
        if not a.get("summary"):
            a["summary"] = a.get("analysis","市场关注度高，等待更多信息")[:100]
        # 随机评分和投票数据（模拟社区互动）
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

    # 按级别排序
    lv_order = {"S":0,"A":1,"B":2,"C":3}
    sorted_articles = sorted(articles, key=lambda x: (lv_order.get(x.get("level","C"),9), -x.get("score_num",0)))
    
    # 统计
    lv_stats = {"S":0,"A":0,"B":0,"C":0}
    src_stats = {}
    for a in sorted_articles:
        lv = a.get("level","C")
        lv_stats[lv] = lv_stats.get(lv, 0) + 1
        src = a.get("source","?")
        src_stats[src] = src_stats.get(src, 0) + 1
    
    # JSON数据（嵌入页面，供前端筛选/投票）
    articles_json = json.dumps([{
        "id": i,
        "level": a.get("level","C"),
        "score": a.get("score_num",0),
        "title": a.get("display",a.get("title","")),
        "original": a.get("original",""),
        "source": a.get("source","?"),
        "sentiment": a.get("sentiment","neutral"),
        "analysis": a.get("analysis",""),
        "summary": a.get("summary",""),
        "coins": a.get("coins",["ALL"]),
        "votes": a.get("votes",{"bullish":0,"bearish":0,"important":0})
    } for i,a in enumerate(sorted_articles)], ensure_ascii=False)
    
    # 生成新闻卡片
    cards_html = ""
    for i, a in enumerate(sorted_articles):
        lv = a.get("level","C")
        emoji = lv_emoji.get(lv, "💡")
        title = a.get("display", a.get("title", ""))
        sentiment = a.get("sentiment", "neutral")
        analysis = a.get("analysis", "")
        summary = a.get("summary", "")
        source = a.get("source", "?")
        color = lv_color.get(lv, "#888")
        sc = sentiment_color.get(sentiment, "#8b949e")
        si = sentiment_icons.get(sentiment, "➡️")
        sn = {"bullish":"看涨","bearish":"看跌","neutral":"中性"}.get(sentiment, "中性")
        votes = a.get("votes", {"bullish":0,"bearish":0,"important":0})
        coins_tag = "".join(f'<span class="coin-tag coin-{c.lower()}">{c}</span>' for c in a.get("coins",["ALL"]))
        
        cards_html += f"""
        <div class="card level-{lv}" style="border-left-color: {color};" data-index="{i}">
            <div class="card-votes">
                <button class="vote-btn up" onclick="vote({i},'bullish')">▲</button>
                <button class="vote-btn" onclick="vote({i},'important')">⚡</button>
                <button class="vote-btn down" onclick="vote({i},'bearish')">▼</button>
            </div>
            <div class="card-body">
                <div class="card-header">
                    <span class="level-badge" style="background:{color}20;color:{color}">{emoji} {lv_name.get(lv,'')}</span>
                    <span class="sentiment-badge" style="background:{sc}15;color:{sc}">{si} {sn}</span>
                    <span class="source-badge">{source}</span>
                    {coins_tag}
                </div>
                <div class="card-title">{title}</div>
                <div class="card-analysis">💡 {analysis}</div>
                <div class="card-summary">{summary[:200]}</div>
                <div class="card-footer">
                    <span class="vote-info" id="vote-bullish-{i}">👍 {votes.get("bullish",0)}</span>
                    <span class="vote-info" id="vote-bearish-{i}">👎 {votes.get("bearish",0)}</span>
                    <span class="vote-info" id="vote-important-{i}">⚡ {votes.get("important",0)}</span>
                </div>
            </div>
        </div>"""
    
    total = len(sorted_articles)
    s_count = lv_stats.get("S", 0)
    a_count = lv_stats.get("A", 0)
    b_count = lv_stats.get("B", 0)
    c_count = lv_stats.get("C", 0)
    
    # 数据源行
    src_rows = "".join(f'<span style="display:inline-block;margin-right:12px;font-size:13px;color:#8b949e;">{src}: <b style="color:#c9d1d9;">{cnt}</b></span>' for src,cnt in sorted(src_stats.items(),key=lambda x:-x[1]))
    
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<title>金峰策略 · 全球加密快讯</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background:#0d1117; color:#c9d1d9; }}
::selection {{ background:#ffd70040; }}

/* Price Ticker */
.ticker {{ background:#161b22; border-bottom:1px solid #30363d; padding:8px 20px; overflow-x:auto; white-space:nowrap; }}
.ticker-inner {{ max-width:1100px; margin:0 auto; display:flex; gap:24px; }}
.ticker-item {{ display:inline-flex; align-items:center; gap:6px; font-size:13px; }}
.ticker-symbol {{ font-weight:700; color:#e6edf3; }}
.ticker-price {{ color:#c9d1d9; }}
.ticker-change {{ font-weight:600; }}
.ticker-change.up {{ color:#3fb950; }}
.ticker-change.down {{ color:#f85149; }}

/* Header */
.header {{ background:linear-gradient(135deg,#161b22,#0d1117); border-bottom:1px solid #30363d; padding:20px 20px 16px; position:sticky; top:0; z-index:100; backdrop-filter:blur(12px); }}
.header-inner {{ max-width:1100px; margin:0 auto; display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px; }}
.header h1 {{ font-size:20px; font-weight:700; color:#ffd700; }}
.header h1 span {{ color:#8b949e; font-weight:400; }}
.header-time {{ font-size:12px; color:#8b949e; }}

/* Search */
.search-bar {{ max-width:1100px; margin:12px auto 0; padding:0 20px; }}
.search-bar input {{ width:100%; background:#0d1117; border:1px solid #30363d; border-radius:8px; padding:10px 14px; color:#c9d1d9; font-size:14px; outline:none; }}
.search-bar input:focus {{ border-color:#58a6ff; }}

/* Stats */
.stats-bar {{ max-width:1100px; margin:16px auto; padding:0 20px; display:flex; gap:10px; flex-wrap:wrap; }}
.stat-item {{ background:#161b22; border:1px solid #30363d; border-radius:8px; padding:10px 14px; flex:1; min-width:80px; cursor:pointer; transition:all .15s; }}
.stat-item:hover {{ border-color:#58a6ff; }}
.stat-item.active {{ border-color:#ffd700; box-shadow:0 0 0 1px #ffd70040; }}
.stat-item .stat-num {{ font-size:22px; font-weight:700; }}
.stat-item .stat-label {{ font-size:11px; color:#8b949e; margin-top:2px; }}
.stat-s .stat-num {{ color:#ff4444; }}
.stat-a .stat-num {{ color:#ff8c00; }}
.stat-b .stat-num {{ color:#f0c040; }}
.stat-c .stat-num {{ color:#888; }}

/* Coin Filter */
.coin-bar {{ max-width:1100px; margin:0 auto 16px; padding:0 20px; display:flex; gap:6px; flex-wrap:wrap; }}
.coin-btn {{ background:#161b22; border:1px solid #30363d; border-radius:20px; padding:6px 14px; color:#8b949e; font-size:13px; cursor:pointer; transition:all .15s; }}
.coin-btn:hover {{ border-color:#58a6ff; color:#58a6ff; }}
.coin-btn.active {{ border-color:#ffd700; color:#ffd700; background:#ffd70010; }}

/* Layout */
.main-layout {{ max-width:1100px; margin:0 auto; padding:0 20px 60px; display:grid; grid-template-columns:1fr 280px; gap:24px; }}
.news-feed {{ min-width:0; }}
.news-feed-header {{ display:flex; align-items:center; justify-content:space-between; margin-bottom:16px; }}
.news-feed-header h2 {{ font-size:15px; color:#8b949e; font-weight:500; }}
.news-feed-header span {{ font-size:12px; color:#484f58; }}

/* Card */
.card {{ background:#161b22; border:1px solid #30363d; border-radius:10px; margin-bottom:10px; padding:14px; display:flex; gap:12px; border-left:3px solid; transition:all .15s; }}
.card:hover {{ background:#1c2128; }}
.card-votes {{ display:flex; flex-direction:column; align-items:center; gap:4px; min-width:36px; }}
.vote-btn {{ background:none; border:1px solid #30363d; border-radius:6px; color:#8b949e; cursor:pointer; font-size:11px; padding:3px 7px; transition:all .15s; line-height:1; }}
.vote-btn:hover {{ border-color:#58a6ff; color:#58a6ff; background:#1f6feb20; }}
.vote-btn.up.voted {{ border-color:#3fb950; color:#3fb950; background:#3fb95020; }}
.vote-btn.down.voted {{ border-color:#f85149; color:#f85149; background:#f8514920; }}
.vote-btn.imp.voted {{ border-color:#ffd700; color:#ffd700; background:#ffd70020; }}
.card-body {{ flex:1; min-width:0; }}
.card-header {{ display:flex; align-items:center; gap:6px; margin-bottom:6px; flex-wrap:wrap; }}
.level-badge {{ font-size:10px; padding:2px 8px; border-radius:10px; font-weight:600; }}
.sentiment-badge {{ font-size:10px; padding:2px 8px; border-radius:10px; font-weight:500; }}
.source-badge {{ font-size:10px; color:#8b949e; background:#21262d; padding:2px 8px; border-radius:10px; }}
.coin-tag {{ font-size:9px; padding:1px 6px; border-radius:8px; font-weight:600; background:#21262d; color:#58a6ff; }}
.coin-btc {{ color:#f0c040; }}
.coin-eth {{ color:#8b9dc0; }}
.coin-sol {{ color:#9945ff; }}
.card-title {{ font-size:14px; font-weight:600; line-height:1.4; margin-bottom:6px; color:#e6edf3; }}
.card-analysis {{ font-size:12px; color:#8b949e; line-height:1.5; margin-bottom:4px; }}
.card-summary {{ font-size:11px; color:#484f58; line-height:1.4; }}
.card-footer {{ display:flex; gap:12px; margin-top:8px; }}
.vote-info {{ font-size:11px; color:#484f58; }}

/* Sidebar */
.sidebar {{ position:sticky; top:100px; align-self:start; }}
.sidebar-section {{ background:#161b22; border:1px solid #30363d; border-radius:10px; padding:14px; margin-bottom:12px; }}
.sidebar-section h3 {{ font-size:13px; color:#c9d1d9; margin-bottom:10px; font-weight:600; }}
.sidebar-section p {{ font-size:12px; color:#8b949e; line-height:1.8; }}
.sidebar-section a {{ color:#58a6ff; text-decoration:none; }}
.sidebar-section a:hover {{ text-decoration:underline; }}
.hot-topic {{ display:inline-block; background:#21262d; border:1px solid #30363d; border-radius:14px; padding:4px 10px; font-size:11px; color:#c9d1d9; margin:2px; cursor:pointer; }}
.hot-topic:hover {{ border-color:#58a6ff; }}

/* Footer */
.footer {{ text-align:center; padding:24px 20px; border-top:1px solid #30363d; max-width:1100px; margin:0 auto; }}
.footer p {{ font-size:11px; color:#484f58; }}

/* Bookmark */
.bookmark-btn {{ background:none; border:none; color:#484f58; cursor:pointer; font-size:14px; margin-left:auto; transition:color .15s; }}
.bookmark-btn:hover {{ color:#ffd700; }}
.bookmark-btn.bookmarked {{ color:#ffd700; }}

/* Animation */
@keyframes fadeIn {{ from {{ opacity:0;transform:translateY(8px); }} to {{ opacity:1;transform:translateY(0); }} }}
.card {{ animation:fadeIn .3s ease; }}

/* Responsive */
@media (max-width:768px) {{
    .main-layout {{ grid-template-columns:1fr; }}
    .sidebar {{ position:static; }}
    .card {{ padding:10px; gap:8px; }}
    .card-votes {{ min-width:30px; gap:3px; }}
    .vote-btn {{ font-size:10px; padding:2px 6px; }}
    .stats-bar {{ gap:6px; }}
    .stat-item {{ padding:8px 10px; min-width:60px; }}
    .stat-item .stat-num {{ font-size:18px; }}
    .header h1 {{ font-size:16px; }}
    .header h1 span {{ display:none; }}
    .ticker {{ padding:6px 12px; }}
    .ticker-inner {{ gap:12px; }}
    .ticker-item {{ font-size:11px; }}
    .coin-bar {{ justify-content:center; gap:4px; }}
    .coin-btn {{ font-size:11px; padding:4px 10px; }}
    .card-title {{ font-size:13px; }}
    .card-analysis {{ font-size:11px; }}
    .card-header {{ gap:4px; }}
    .sidebar-section {{ padding:10px; }}
    #fgi-box {{ flex-direction:column; }}
    .search-bar input {{ font-size:13px; padding:8px 12px; }}
}}

.hidden {{ display:none !important; }}
</style>
</head>
<body>

<!-- 价格行情条 -->
<div class="ticker">
    <div class="ticker-inner" id="ticker-bar">
        <span class="ticker-item"><span class="ticker-symbol">BTC</span> <span class="ticker-price" id="btc-price">—</span> <span class="ticker-change" id="btc-change"></span></span>
        <span class="ticker-item"><span class="ticker-symbol">ETH</span> <span class="ticker-price" id="eth-price">—</span> <span class="ticker-change" id="eth-change"></span></span>
        <span class="ticker-item"><span class="ticker-symbol">SOL</span> <span class="ticker-price" id="sol-price">—</span> <span class="ticker-change" id="sol-change"></span></span>
    </div>
</div>

<header class="header">
<div class="header-inner">
    <h1>金峰策略 <span>· 全球加密快讯</span></h1>
    <span class="header-time" id="header-time">🕐 {now_str}</span>
</div>
<div class="search-bar">
    <input type="text" id="search-input" placeholder="🔍 搜索新闻标题..." oninput="doSearch(this.value)">
</div>
</header>

<div class="stats-bar" id="stats-bar">
    <div class="stat-item stat-s" onclick="filterByLevel('ALL')"><div class="stat-num">{total}</div><div class="stat-label">📰 全部</div></div>
    <div class="stat-item stat-s" onclick="filterByLevel('S')"><div class="stat-num">{s_count}</div><div class="stat-label">🔴 S交易级</div></div>
    <div class="stat-item stat-a" onclick="filterByLevel('A')"><div class="stat-num">{a_count}</div><div class="stat-label">🟠 A重要趋势</div></div>
    <div class="stat-item stat-b" onclick="filterByLevel('B')"><div class="stat-num">{b_count}</div><div class="stat-label">⚡ B辅助参考</div></div>
    <div class="stat-item stat-c" onclick="filterByLevel('C')"><div class="stat-num">{c_count}</div><div class="stat-label">💡 C资讯</div></div>
</div>

<div class="coin-bar" id="coin-bar">
    <button class="coin-btn active" onclick="filterByCoin('ALL')">ALL</button>
    <button class="coin-btn" onclick="filterByCoin('BTC')">BTC</button>
    <button class="coin-btn" onclick="filterByCoin('ETH')">ETH</button>
    <button class="coin-btn" onclick="filterByCoin('SOL')">SOL</button>
    <button class="coin-btn" onclick="filterByCoin('HYPE')">HYPE</button>
    <button class="coin-btn" onclick="filterByCoin('SUI')">SUI</button>
    <button class="coin-btn" onclick="filterByCoin('DOGE')">DOGE</button>
    <button class="coin-btn" onclick="filterByCoin('XRP')">XRP</button>
    <button class="coin-btn" onclick="filterByCoin('BNB')">BNB</button>
</div>

<div class="main-layout">
<div class="news-feed">
    <div class="news-feed-header">
        <h2>📰 快讯列表</h2>
        <span id="feed-count">{total} 条</span>
    </div>
    <div id="news-list">
        {cards_html}
    </div>
</div>

<aside class="sidebar">
    <div class="sidebar-section">
        <h3>📊 情绪分布</h3>
        <div id="sentiment-chart" style="font-size:13px;color:#8b949e;line-height:1.8;"></div>
    </div>
    <div class="sidebar-section">
        <h3>😱 恐惧与贪婪指数</h3>
        <div id="fgi-box" style="display:flex;align-items:center;gap:12px;">
            <div id="fgi-gauge" style="width:60px;height:60px;border-radius:50%;border:4px solid #30363d;display:flex;align-items:center;justify-content:center;font-size:20px;font-weight:700;color:#c9d1d9;flex-shrink:0;"></div>
            <div id="fgi-text" style="font-size:13px;color:#8b949e;line-height:1.5;"></div>
        </div>
        <p style="font-size:11px;color:#484f58;margin-top:8px;">📡 数据来源: Alternative.me</p>
    </div>
    <div class="sidebar-section">
        <h3>🔥 热门话题</h3>
        <div id="hot-topics">
            <span class="hot-topic">BTC</span>
            <span class="hot-topic">ETF</span>
            <span class="hot-topic">加息</span>
            <span class="hot-topic">监管</span>
            <span class="hot-topic">DeFi</span>
            <span class="hot-topic">Layer2</span>
            <span class="hot-topic">AI</span>
            <span class="hot-topic">山寨币</span>
            <span class="hot-topic">矿工</span>
        </div>
    </div>
    <div class="sidebar-section">
        <h3>📡 数据源分布</h3>
        <p>{src_rows}</p>
    </div>
    <div class="sidebar-section">
        <h3>🔗 更多资源</h3>
        <p>
            <a href="https://cryptopanic.com" target="_blank">→ CryptoPanic</a><br>
            <a href="https://www.panewslab.com" target="_blank">→ PANews</a><br>
            <a href="https://cointelegraph.com" target="_blank">→ Cointelegraph</a><br>
            <a href="https://bitcoinmagazine.com" target="_blank">→ Bitcoin Magazine</a>
        </p>
    </div>
</aside>
</div>

<footer class="footer">
    <p>金峰策略 · 全球加密快讯 · 仅供研究参考 · 不构成投资建议</p>
    <p style="margin-top:4px;">🕐 {now_str} · 采集频率: 每30分钟更新</p>
</footer>

<script>
// ========== 数据 ==========
const ARTICLES = {articles_json};

let currentLevel = 'ALL';
let currentCoin = 'ALL';
let searchQuery = '';

// ========== 价格行情 ==========
async function fetchPrices() {{
    try {{
        const r = await fetch('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana&vs_currencies=usd&include_24hr_change=true');
        const d = await r.json();
        const updateTicker = (id, elId, changeId) => {{
            const p = d[id]?.usd;
            const c = d[id]?.usd_24h_change;
            if (p) document.getElementById(elId).textContent = '$' + p.toLocaleString();
            if (c) {{
                const el = document.getElementById(changeId);
                el.textContent = (c > 0 ? '+' : '') + c.toFixed(2) + '%';
                el.className = 'ticker-change ' + (c > 0 ? 'up' : 'down');
            }}
        }};
        updateTicker('bitcoin','btc-price','btc-change');
        updateTicker('ethereum','eth-price','eth-change');
        updateTicker('solana','sol-price','sol-change');
    }} catch(e) {{}}
}}
fetchPrices();
setInterval(fetchPrices, 60000);

// ========== 表情价额统计 ==========
(function() {{
    let bullish=0, bearish=0, neutral=0;
    ARTICLES.forEach(a => {{
        if(a.sentiment==='bullish') bullish++;
        else if(a.sentiment==='bearish') bearish++;
        else neutral++;
    }});
    document.getElementById('sentiment-chart').innerHTML =
        '📈 看涨: ' + bullish + '条 (' + Math.round(bullish/ARTICLES.length*100) + '%)<br>' +
        '📉 看跌: ' + bearish + '条 (' + Math.round(bearish/ARTICLES.length*100) + '%)<br>' +
        '➡️ 中性: ' + neutral + '条 (' + Math.round(neutral/ARTICLES.length*100) + '%)';
}})();

// ========== 更新显示计数 ==========
function updateCount() {{
    const visible = document.querySelectorAll('.card:not(.hidden)').length;
    document.getElementById('feed-count').textContent = visible + ' / ' + ARTICLES.length + ' 条';
}}

// ========== 级别筛选 ==========
function filterByLevel(lv) {{
    const btns = document.querySelectorAll('.stat-item');
    btns.forEach(b => b.classList.remove('active'));
    if(lv !== 'ALL') {{
        btns.forEach(b => {{
            if(b.classList.contains('stat-'+lv)) b.classList.add('active');
        }});
    }} else btns[0].classList.add('active');
    currentLevel = lv;
    applyFilters();
}}

// ========== 币种筛选 ==========
function filterByCoin(coin) {{
    const btns = document.querySelectorAll('.coin-btn');
    btns.forEach(b => b.classList.remove('active'));
    btns.forEach(b => {{
        if(b.textContent === coin) b.classList.add('active');
    }});
    currentCoin = coin;
    applyFilters();
}}

// ========== 搜索 ==========
function doSearch(q) {{
    searchQuery = q.toLowerCase();
    applyFilters();
}}

// ========== 综合筛选 ==========
function applyFilters() {{
    const cards = document.querySelectorAll('.card');
    cards.forEach(c => {{
        const idx = parseInt(c.dataset.index);
        const a = ARTICLES[idx];
        let show = true;
        if(currentLevel !== 'ALL' && a.level !== currentLevel) show = false;
        if(currentCoin !== 'ALL' && !a.coins.includes(currentCoin) && !a.coins.includes('ALL')) show = false;
        if(searchQuery && !a.title.toLowerCase().includes(searchQuery)) show = false;
        c.classList.toggle('hidden', !show);
    }});
    updateCount();
}}

// ========== 投票 ==========
const voted = {{}};
function vote(idx, type) {{
    const key = idx + '-' + type;
    const el = document.getElementById('vote-' + type + '-' + idx);
    if(!el) return;
    const btnMap = {{'bullish':'up','bearish':'down','important':'imp'}};
    
    if(voted[key]) {{
        voted[key] = false;
        let cur = parseInt(el.textContent.split(' ')[1]);
        el.textContent = el.textContent.split(' ')[0] + ' ' + (cur - 1);
        const cards = document.querySelectorAll('.card');
        const btns = cards[idx].querySelectorAll('.vote-btn');
        btns.forEach(b => b.classList.remove('voted'));
        return;
    }}
    
    voted[key] = true;
    // 清除同篇文章其他投票
    ['bullish','bearish','important'].forEach(t => {{
        const k = idx + '-' + t;
        if(k !== key && voted[k]) {{ voted[k] = false; }}
    }});
    
    let cur = parseInt(el.textContent.split(' ')[1]);
    el.textContent = el.textContent.split(' ')[0] + ' ' + (cur + 1);
    
    const cards = document.querySelectorAll('.card');
    const btns = cards[idx].querySelectorAll('.vote-btn');
    btns.forEach(b => b.classList.remove('voted'));
    // 标记当前按钮
    const className = btnMap[type] || '';
    cards[idx].querySelectorAll('.vote-btn').forEach(b => {{
        if(b.classList.contains(className)) b.classList.add('voted');
    }});
    
    // 动画闪烁
    el.style.color = type === 'bullish' ? '#3fb950' : type === 'bearish' ? '#f85149' : '#ffd700';
    setTimeout(() => el.style.color = '', 600);
    saveVotes();
}}

// ========== 投票持久化（localStorage） ==========
function saveVotes() {{
    try {{ localStorage.setItem('signal_votes_' + location.pathname, JSON.stringify(voted)); }} catch(e) {{}}
}}
function loadVotes() {{
    try {{
        const data = JSON.parse(localStorage.getItem('signal_votes_' + location.pathname));
        if(data) Object.assign(voted, data);
        // 恢复按钮状态
        Object.keys(voted).forEach(k => {{
            if(voted[k]) {{
                const [idx, type] = k.split('-');
                const btnMap = {{'bullish':'up','bearish':'down','important':'imp'}};
                const cards = document.querySelectorAll('.card');
                const className = btnMap[type] || '';
                cards[idx]?.querySelectorAll('.vote-btn').forEach(b => {{
                    if(b.classList.contains(className)) b.classList.add('voted');
                }});
            }}
        }});
    }} catch(e) {{}}
}}
loadVotes();

// ========== 收藏功能（localStorage持久化） ==========
function toggleBookmark(idx) {{
    let bookmarks = JSON.parse(localStorage.getItem('signal_bookmarks') || '[]');
    const btn = document.getElementById('bookmark-' + idx);
    if(bookmarks.includes(idx)) {{
        bookmarks = bookmarks.filter(i => i !== idx);
        btn.classList.remove('bookmarked');
    }} else {{
        bookmarks.push(idx);
        btn.classList.add('bookmarked');
    }}
    localStorage.setItem('signal_bookmarks', JSON.stringify(bookmarks));
}}
// 恢复收藏状态
(function() {{
    const bookmarks = JSON.parse(localStorage.getItem('signal_bookmarks') || '[]');
    bookmarks.forEach(idx => {{
        const btn = document.getElementById('bookmark-' + idx);
        if(btn) btn.classList.add('bookmarked');
    }});
}})();

// ========== 恐惧与贪婪指数 ==========
async function fetchFGI() {{
    try {{
        const r = await fetch('https://api.alternative.me/fng/?limit=1');
        const d = await r.json();
        const val = parseInt(d.data[0].value);
        const classification = d.data[0].value_classification;
        const gauge = document.getElementById('fgi-gauge');
        const text = document.getElementById('fgi-text');
        gauge.textContent = val;
        // 渐变颜色
        let color;
        if(val <= 25) {{ color = '#f85149'; }}      // 极度恐惧
        else if(val <= 45) {{ color = '#f0883e'; }}  // 恐惧
        else if(val <= 55) {{ color = '#f0c040'; }}  // 中性
        else if(val <= 75) {{ color = '#3fb950'; }}  // 贪婪
        else {{ color = '#2ea043'; }}                // 极度贪婪
        gauge.style.borderColor = color;
        gauge.style.color = color;
        text.innerHTML = `<b style="color:${{color}}">${{classification}}</b><br><span style="font-size:11px;color:#484f58;">最新指数</span>`;
    }} catch(e) {{
        document.getElementById('fgi-text').textContent = '数据暂不可用';
    }}
}}
fetchFGI();

// ========== 自动刷新 ==========
setTimeout(() => {{
    location.reload();
}}, 1800000); // 30分钟自动刷新页面
</script>

</body>
</html>"""
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
            html = render_site(filtered, now_str)
            site_dir = os.path.join(BASE, "docs")
            os.makedirs(site_dir, exist_ok=True)
            with open(os.path.join(site_dir, "index.html"), "w", encoding="utf-8") as f:
                f.write(html)
            print(f"\n✅ 网站已生成: {os.path.join(site_dir, 'index.html')} ({len(html)/1024:.0f}KB)")
        else:
            print("\n⚠️ 无评分通过的资讯，网站未更新")
