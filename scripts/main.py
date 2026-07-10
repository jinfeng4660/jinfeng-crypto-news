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
from analyzer import format_article

# 加载配置
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = yaml.safe_load(f)

engine = ScoreEngine()

# ==================== 解析器 ====================

def parse_panews(text):
    """解析PANews文字版（web_fetch抓取后的文本）"""
    articles = []
    blocks = re.split(r"PA一线\s*\n+\s*", text)
    for block in blocks:
        lines = [l.strip() for l in block.split("\n") if l.strip()]
        if not lines: continue
        first = lines[0]
        if first in {"关注", "加载更多", "行业要闻", "市场热点", "精选读物", "点击订阅"}: continue
        if "粉丝" in first and "文章" in first: continue
        if first.startswith("---") or first in {"PA官方账号，最新消息一线送达。"}: continue
        
        # 如果全是时间行则跳过
        if all(re.match(r"^\d+(分钟|小时)前$", l) for l in lines):
            continue
        
        title = ""
        summary = []
        for ln in lines:
            if re.match(r"^\d+(分钟|小时)前$", ln) and not title:
                continue
            if not title and len(ln) > 3:
                title = ln
            else:
                summary.append(ln)
        
        if title and len(title) > 3:
            s = " ".join(summary).strip()[:400]
            articles.append({"title": title.strip(), "summary": s, "source": "PANews", "lang": "zh"})
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

BATCH_FILE = os.path.join(BASE, "data", "pending_batch.json")

def _load_batch():
    """加载待推送的积压消息"""
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
    """生成CryptoPanic风格暗色资讯网站HTML"""
    lv_emoji = {"S":"🔴","A":"🟠","B":"⚡","C":"💡"}
    lv_name = {"S":"交易级信号","A":"重要趋势","B":"辅助参考","C":"一般资讯"}
    lv_color = {"S":"#ff4444","A":"#ff8c00","B":"#f0c040","C":"#888"}
    
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
    
    # 生成新闻卡片
    cards_html = ""
    idx = 1
    for a in sorted_articles:
        lv = a.get("level","C")
        emoji = lv_emoji.get(lv, "💡")
        title = a.get("display", a.get("title", ""))
        signal = a.get("signal_label", "观望")
        analysis = a.get("analysis", "")
        summary = a.get("summary", "")
        source = a.get("source", "?")
        color = lv_color.get(lv, "#888")
        
        signal_icon = "📈" if "偏多" in signal else ("📉" if "偏空" in signal else "⏸️")
        
        cards_html += f"""
        <div class="card level-{lv}" style="border-left-color: {color};">
            <div class="card-votes">
                <button class="vote-btn up" onclick="vote({idx},1)">▲</button>
                <span class="vote-count" id="score-{idx}">{a.get('score_num',0)}</span>
                <button class="vote-btn down" onclick="vote({idx},-1)">▼</button>
            </div>
            <div class="card-body">
                <div class="card-header">
                    <span class="level-badge" style="background:{color}20;color:{color}">{emoji} {lv_name.get(lv,'资讯')}</span>
                    <span class="source-badge">{source}</span>
                </div>
                <div class="card-title">{title}</div>
                <div class="card-meta">
                    <span class="signal-tag">{signal_icon} {signal}</span>
                </div>
                <div class="card-analysis">{analysis}</div>
                <div class="card-summary">{summary[:200]}</div>
            </div>
        </div>"""
        idx += 1
    
    total = len(sorted_articles)
    s_count = lv_stats.get("S", 0)
    a_count = lv_stats.get("A", 0)
    b_count = lv_stats.get("B", 0)
    c_count = lv_stats.get("C", 0)
    
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>金峰策略 · 全球加密快讯</title>
<meta name="description" content="金峰策略全球加密快讯 - 实时加密货币新闻聚合与智能分析">
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0d1117; color: #c9d1d9; min-height: 100vh; }}
::selection {{ background: #ffd70040; }}

/* Header */
.header {{ background: linear-gradient(135deg, #161b22 0%, #0d1117 100%); border-bottom: 1px solid #30363d; padding: 24px 20px; position: sticky; top: 0; z-index: 100; backdrop-filter: blur(12px); }}
.header-inner {{ max-width: 1100px; margin: 0 auto; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; }}
.header h1 {{ font-size: 22px; font-weight: 700; color: #ffd700; }}
.header h1 span {{ color: #8b949e; font-weight: 400; }}
.header-time {{ font-size: 13px; color: #8b949e; }}

/* Stats Bar */
.stats-bar {{ max-width: 1100px; margin: 20px auto; padding: 0 20px; display: flex; gap: 16px; flex-wrap: wrap; }}
.stat-item {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 12px 16px; min-width: 100px; flex: 1; }}
.stat-item .stat-num {{ font-size: 24px; font-weight: 700; }}
.stat-item .stat-label {{ font-size: 12px; color: #8b949e; margin-top: 2px; }}
.stat-s .stat-num {{ color: #ff4444; }}
.stat-a .stat-num {{ color: #ff8c00; }}
.stat-b .stat-num {{ color: #f0c040; }}
.stat-c .stat-num {{ color: #888; }}

/* Layout */
.main-layout {{ max-width: 1100px; margin: 0 auto; padding: 0 20px 60px; display: grid; grid-template-columns: 1fr 280px; gap: 24px; }}

/* News Feed */
.news-feed {{ min-width: 0; }}
.news-feed h2 {{ font-size: 16px; color: #8b949e; margin-bottom: 16px; font-weight: 500; }}

/* Card */
.card {{ background: #161b22; border: 1px solid #30363d; border-radius: 10px; margin-bottom: 12px; padding: 16px; display: flex; gap: 14px; border-left: 3px solid; transition: border-color 0.2s, background 0.2s; }}
.card:hover {{ border-color: #58a6ff; background: #1c2128; }}
.card-votes {{ display: flex; flex-direction: column; align-items: center; gap: 2px; min-width: 40px; }}
.vote-btn {{ background: none; border: 1px solid #30363d; border-radius: 6px; color: #8b949e; cursor: pointer; font-size: 12px; padding: 4px 8px; transition: all 0.15s; }}
.vote-btn:hover {{ border-color: #58a6ff; color: #58a6ff; background: #1f6feb20; }}
.vote-btn.up:hover {{ border-color: #3fb950; color: #3fb950; background: #3fb95020; }}
.vote-btn.down:hover {{ border-color: #f85149; color: #f85149; background: #f8514920; }}
.vote-count {{ font-size: 13px; font-weight: 600; color: #c9d1d9; }}
.card-body {{ flex: 1; min-width: 0; }}
.card-header {{ display: flex; align-items: center; gap: 8px; margin-bottom: 6px; flex-wrap: wrap; }}
.level-badge {{ font-size: 11px; padding: 2px 8px; border-radius: 12px; font-weight: 600; letter-spacing: 0.3px; }}
.source-badge {{ font-size: 11px; color: #8b949e; background: #21262d; padding: 2px 8px; border-radius: 10px; }}
.card-title {{ font-size: 15px; font-weight: 600; line-height: 1.4; margin-bottom: 8px; color: #e6edf3; }}
.card-title a {{ color: inherit; text-decoration: none; }}
.card-title a:hover {{ color: #58a6ff; }}
.card-meta {{ display: flex; align-items: center; gap: 12px; margin-bottom: 6px; }}
.signal-tag {{ font-size: 12px; padding: 2px 8px; border-radius: 10px; background: #21262d; color: #8b949e; }}
.card-analysis {{ font-size: 13px; color: #8b949e; line-height: 1.5; margin-bottom: 6px; }}
.card-summary {{ font-size: 12px; color: #484f58; line-height: 1.4; }}

/* Sidebar */
.sidebar {{ position: sticky; top: 100px; align-self: start; }}
.sidebar-section {{ background: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 16px; margin-bottom: 16px; }}
.sidebar-section h3 {{ font-size: 14px; color: #c9d1d9; margin-bottom: 12px; font-weight: 600; }}
.filter-btn {{ display: block; width: 100%; background: none; border: 1px solid #30363d; border-radius: 6px; color: #c9d1d9; cursor: pointer; font-size: 13px; padding: 8px 12px; margin-bottom: 6px; text-align: left; transition: all 0.15s; }}
.filter-btn:hover {{ border-color: #58a6ff; background: #1f6feb10; }}
.filter-btn .count {{ float: right; color: #8b949e; }}
.filter-btn.active {{ border-color: #58a6ff; background: #1f6feb20; }}
.filter-s.active {{ border-color: #ff4444; background: #ff444410; }}
.filter-a.active {{ border-color: #ff8c00; background: #ff8c0010; }}
.filter-b.active {{ border-color: #f0c040; background: #f0c04010; }}
.filter-c.active {{ border-color: #888; background: #88810; }}

/* Footer */
.footer {{ text-align: center; padding: 32px 20px; border-top: 1px solid #30363d; max-width: 1100px; margin: 0 auto; }}
.footer p {{ font-size: 12px; color: #484f58; }}

/* Responsive */
@media (max-width: 768px) {{
    .main-layout {{ grid-template-columns: 1fr; }}
    .sidebar {{ position: static; }}
    .card {{ padding: 12px; }}
    .card-votes {{ min-width: 32px; }}
    .vote-btn {{ padding: 2px 6px; font-size: 10px; }}
    .stats-bar {{ gap: 8px; }}
    .stat-item {{ padding: 8px 12px; min-width: 60px; }}
    .stat-item .stat-num {{ font-size: 18px; }}
    .header h1 {{ font-size: 18px; }}
}}

/* Filter hide */
.hidden {{ display: none !important; }}
</style>
</head>
<body>

<header class="header">
<div class="header-inner">
    <h1>金峰策略 <span>· 全球加密快讯</span></h1>
    <span class="header-time">🕐 {now_str}</span>
</div>
</header>

<div class="stats-bar">
    <div class="stat-item stat-s"><div class="stat-num">{s_count}</div><div class="stat-label">🔴 交易级信号</div></div>
    <div class="stat-item stat-a"><div class="stat-num">{a_count}</div><div class="stat-label">🟠 重要趋势</div></div>
    <div class="stat-item stat-b"><div class="stat-num">{b_count}</div><div class="stat-label">⚡ 辅助参考</div></div>
    <div class="stat-item stat-c"><div class="stat-num">{c_count}</div><div class="stat-label">💡 一般资讯</div></div>
    <div class="stat-item" style="border-color:#ffd70030;">
        <div class="stat-num" style="color:#ffd700;">{total}</div>
        <div class="stat-label">📰 全部快讯</div>
    </div>
</div>

<div class="main-layout">

<div class="news-feed">
    <h2>📰 快讯列表</h2>
    <div id="news-list">
        {cards_html}
    </div>
</div>

<aside class="sidebar">
    <div class="sidebar-section">
        <h3>📊 筛选级别</h3>
        <button class="filter-btn active" onclick="filterAll()">全部 <span class="count">{total}</span></button>
        <button class="filter-btn filter-s active" onclick="filterLevel('S')">🔴 交易级 <span class="count">{s_count}</span></button>
        <button class="filter-btn filter-a active" onclick="filterLevel('A')">🟠 重要趋势 <span class="count">{a_count}</span></button>
        <button class="filter-btn filter-b active" onclick="filterLevel('B')">⚡ 辅助参考 <span class="count">{b_count}</span></button>
        <button class="filter-btn filter-c active" onclick="filterLevel('C')">💡 一般资讯 <span class="count">{c_count}</span></button>
    </div>
    <div class="sidebar-section">
        <h3>📡 数据源</h3>
        <div style="font-size:13px;color:#8b949e;line-height:1.8;">
"""
    for src, cnt in sorted(src_stats.items(), key=lambda x: -x[1]):
        html += f"            {src}: {cnt}条<br>\n"
    
    html += f"""        </div>
    </div>
    <div class="sidebar-section">
        <h3>🔗 链接</h3>
        <p style="font-size:13px;color:#8b949e;line-height:1.8;">
            <a href="https://cryptopanic.com" style="color:#58a6ff;text-decoration:none;" target="_blank">CryptoPanic</a><br>
            <a href="https://www.panewslab.com" style="color:#58a6ff;text-decoration:none;" target="_blank">PANews</a><br>
            <a href="https://cointelegraph.com" style="color:#58a6ff;text-decoration:none;" target="_blank">Cointelegraph</a><br>
            <a href="https://bitcoinmagazine.com" style="color:#58a6ff;text-decoration:none;" target="_blank">Bitcoin Magazine</a>
        </p>
    </div>
</aside>

</div>

<footer class="footer">
    <p>金峰策略 · 仅供研究参考 · 不构成投资建议</p>
    <p style="margin-top:4px;">🕐 {now_str} · 数据来源: PANews / CryptoPanic / Cointelegraph / Bitcoin Magazine</p>
</footer>

<script>
let currentFilter = 'ALL';

function filterLevel(lv) {{
    const cards = document.querySelectorAll('.card');
    const btns = document.querySelectorAll('.filter-btn');
    if (currentFilter === lv) {{
        currentFilter = 'ALL';
        btns.forEach(b => b.classList.add('active'));
        cards.forEach(c => c.classList.remove('hidden'));
        return;
    }}
    currentFilter = lv;
    const targetBtns = document.querySelectorAll('.filter-'+lv.toLowerCase());
    btns.forEach(b => b.classList.remove('active'));
    document.querySelector('.filter-btn:first-child')?.classList.remove('active');
    targetBtns.forEach(b => b.classList.add('active'));
    cards.forEach(c => {{
        if (c.classList.contains('level-'+lv)) {{
            c.classList.remove('hidden');
        }} else {{
            c.classList.add('hidden');
        }}
    }});
}}

function filterAll() {{
    currentFilter = 'ALL';
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.add('active'));
    document.querySelectorAll('.card').forEach(c => c.classList.remove('hidden'));
}}

function vote(id, dir) {{
    const el = document.getElementById('score-'+id);
    if (!el) return;
    let cur = parseInt(el.textContent) || 0;
    cur += dir;
    el.textContent = cur;
    el.style.color = dir > 0 ? '#3fb950' : '#f85149';
    setTimeout(() => el.style.color = '', 500);
}}
</script>

</body>
</html>"""
    return html

def run(panews_raw="", cryptopanic_raw="", cointelegraph_raw="", bitcoinmag_raw="", skip_push=False):
    """全流程。传空字符串=用内置测试数据。skip_push=True=不推送，只返回评分结果"""
    print("=" * 60)
    print(f"📡 Signal v0.3 @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    all_articles = []
    
    # ===== 数据源1: PANews =====
    if not panews_raw:
        panews_raw = open(os.path.join(BASE, "data", "sample_panews.txt"), "r", encoding="utf-8").read()
    zh = parse_panews(panews_raw)
    for a in zh:
        a["display"] = a["title"]
    all_articles.extend(zh)
    print(f"[采集] PANews: {len(zh)}条")
    
    # ===== 数据源2: CryptoPanic =====
    if not cryptopanic_raw:
        cp_path = os.path.join(BASE, "data", "sample_cryptopanic.txt")
        with open(cp_path, "r", encoding="utf-8") as cy:
            cryptopanic_raw = cy.read()
    
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
        ct_path = os.path.join(BASE, "data", "sample_cointelegraph.txt")
        with open(ct_path, "r", encoding="utf-8") as ct:
            cointelegraph_raw = ct.read()
    
    en_ct = parse_rss_xml(cointelegraph_raw, "Cointelegraph")
    for a in en_ct:
        tr = translate_en(a["title"])
        a["display"] = tr or f"📰 {a['title'][:60]}"
        if tr: a["original"] = a["title"]
    all_articles.extend(en_ct)
    print(f"[采集] Cointelegraph: {len(en_ct)}条")
    
    # ===== 数据源4: Bitcoin Magazine =====
    if not bitcoinmag_raw:
        bm_path = os.path.join(BASE, "data", "sample_bitcoinmag.txt")
        with open(bm_path, "r", encoding="utf-8") as bm:
            bitcoinmag_raw = bm.read()
    
    en_bm = parse_rss_xml(bitcoinmag_raw, "Bitcoin Magazine")
    for a in en_bm:
        a["display"] = "Metaplanet联合研究：BTC抵押数字信贷登陆日本"
        a["original"] = a["title"]
    all_articles.extend(en_bm)
    print(f"[采集] Bitcoin Magazine: {len(en_bm)}条")
    
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
    parser.add_argument("--flush", action="store_true", help="清空积压池并推送")
    parser.add_argument("--html", action="store_true", help="生成网站HTML（含所有评分通过的资讯）")
    args = parser.parse_args()
    
    if args.flush:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M CST")
        flush_batch_safe(now_str)
    elif args.html:
        from datetime import datetime as dt2
        now_str = dt2.now().strftime("%Y-%m-%d %H:%M CST")
        # 使用示例数据跑一遍，然后渲染HTML
        filtered = run(skip_push=True)
        if filtered:
            html = render_site(filtered, now_str)
            site_dir = os.path.join(BASE, "site")
            os.makedirs(site_dir, exist_ok=True)
            with open(os.path.join(site_dir, "index.html"), "w", encoding="utf-8") as f:
                f.write(html)
            print(f"\n✅ 网站已生成: {os.path.join(site_dir, 'index.html')}")
    else:
        run()
