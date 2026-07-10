"""
Signal 分析引擎 - AI级智能见解生成
根据标题和内容自动匹配看多/看空/观望判断 + 一句话分析
"""
import re

def analyze(text, source=""):
    """生成见解：方向判断 + 一句话分析"""
    t = text.lower()
    direction = "观望"
    confidence = "中等"
    
    # ===== 偏空信号（优先级高于偏多——风控优先原则） =====
    bearish_signals = [
        (r"出售.*btc|sale.*bitcoin|sale.*btc|strategy.*sale|strategy.*sell|微策略.*卖|灰度.*卖|机构.*卖", "机构减持", "机构抛售BTC，短期卖压加大", "偏空"),
        (r"爆仓.*多|多单.*爆仓|多头.*清|多头爆|liquid.*long|多头清算", "多头出清", "多头被大量清算，短期抛压仍在", "偏空"),
        (r"etf.*流出|etf.*outflow|etf.*净卖出|灰度.*sell|etf.*负", "机构流出", "机构减持信号，中期偏空", "偏空"),
        (r"跌破|跌超|新低|破位|崩盘|暴跌|crash|flash.*crash|跌破.*关键", "破位下行", "关键支撑被击穿，下方空间打开", "偏空"),
        (r"出售|dumping|抛售|卖出.*btc|减持|减仓|sell.*btc", "主动抛售", "市场卖压增大，短期偏空", "偏空"),
        (r"加息|rate.*hike|紧缩|hawkish|缩表", "加息预期", "紧缩政策利空风险资产", "偏空"),
        (r"制裁|sanction|禁止|ban|关停|shut.*down|禁止交易|冻结|seize|扣押", "监管打击", "政策利空冲击市场", "偏空"),
        (r"黑客|hack|被盗|exploit|漏洞|攻击.*协议|钓鱼|phish|rug|跑路|scam", "安全事件", "安全事件冲击短期信心", "偏空"),
        (r"通胀|inflation|cpi.*高|cpi.*超|物价.*涨", "通胀风险", "高通胀压制风险偏好", "偏空"),
        (r"战争|war|冲突|conflict|袭击|strike|军事|militar|动武", "地缘风险", "地缘紧张推升避险情绪，加密承压", "偏空"),
        (r"亏损|lost|亏|loss.*万|亏损.*万|巨额亏损|巨亏", "资金亏损", "市场亏损增加，情绪偏弱", "偏空"),
        (r"做空|short.*position|空头.*加|空头.*增", "空头加仓", "空头力量增强，市场承压", "偏空"),
        (r"暂停.*提|停止.*提|提现困难|无法提现|挤兑|bank.*run", "交易所危机", "信任危机，市场恐慌卖出", "偏空"),
    ]
    
    # ===== 偏多信号 =====
    bullish_signals = [
        (r"爆仓.*空|空单.*爆仓|空头.*清|liquid.*short|空头清算|轧空", "轧空信号", "空头过度拥挤，短期有轧空风险", "偏多"),
        (r"etf.*流入|etf.*inflow|etf.*净买入|etf.*净流入|etf.*approv|etf.*批准|etf.*通过", "ETF流入", "机构资金持续流入，中期偏多", "偏多"),
        (r"突破.*关键|突破.*阻力|涨超|创.*新高|冲破|ath|新高", "突破信号", "价格突破关键位，动能向上", "偏多"),
        (r"买入|buying|buy.*btc|增持|增仓|加仓|accumulat|收集筹码", "主动买入", "市场买盘力量增强，短期偏多", "偏多"),
        (r"降息|rate.*cut|宽松|dovish|降准|降息预期", "降息预期", "流动性宽松预期利好风险资产", "偏多"),
        (r"巨鲸.*存|whale.*deposit|whale.*进|whale.*buy|巨鲸.*进|巨鲸.*买", "巨鲸买入", "大资金进场信号，中期偏多", "偏多"),
        (r"减半|halving|供应.*减少|supply.*drop|稀缺|scarcit", "供应冲击", "供应减少是长期利好", "偏多"),
        (r"合规|牌照|license|批准.*银行|approv.*bank|银行牌照", "监管利好", "合规化推进利好整个行业", "偏多"),
        (r"目标.*10万|target.*price|预测.*涨.*[0-9]万|目标价.*[0-9]", "看多目标", "机构目标价支撑市场信心", "偏多"),
        (r"铸造|mint.*usdc|usdc.*mint|usdt.*mint|增发.*稳定币|新铸", "流动性注入", "稳定币增发=资金入场潜力增加", "偏多"),
    ]
    
    # ===== 中性/关键事件 =====
    neutral_signals = [
        (r"cpi|通胀|pce|物价|consumer.*price", "通胀数据待评估", "关键数据公布前市场观望，等待方向确认", "观望"),
        (r"选|election|投票|poll|民调", "政策不确定性", "选举事件扰动市场，方向不确定", "观望"),
        (r"上线|launch|上币|perpetual|永续", "产品上线", "新产品上线对行情影响中性偏正面", "观望"),
        (r"ai|人工智能|agent|代理", "AI技术进展", "技术面积极进展但不直接影响币价", "观望"),
        (r"融资|funding|raise|投资|invest", "融资进展", "长期利好但不影响短期走势", "观望"),
        (r"合作|partner|integration|inregrat", "生态合作", "合作推进生态发展，影响温和正面", "观望"),
        (r"报告|report|research|研究", "研报发布", "信息参考，不直接反映交易信号", "观望"),
    ]
    
    # 匹配
    scores = {"偏多": 0, "偏空": 0, "观望": 0}
    best_analysis = ""
    best_reason = ""
    
    for pattern, reason, analysis, dir_ in bullish_signals:
        if re.search(pattern, text, re.IGNORECASE):
            scores["偏多"] += 2
            best_analysis = analysis
            best_reason = reason
    
    for pattern, reason, analysis, dir_ in bearish_signals:
        if re.search(pattern, text, re.IGNORECASE):
            scores["偏空"] += 2
            best_analysis = analysis
            best_reason = reason
    
    for pattern, reason, analysis, dir_ in neutral_signals:
        if re.search(pattern, text, re.IGNORECASE):
            scores["观望"] += 2
            best_analysis = analysis
            best_reason = reason
    
    # 判断方向
    max_dir = max(scores, key=scores.get)
    if scores["偏多"] > 0 and scores["偏空"] == 0:
        direction = "偏多"
    elif scores["偏空"] > 0 and scores["偏多"] == 0:
        direction = "偏空"
    elif scores["偏多"] >= scores["偏空"]:
        direction = "偏多"
        if not best_analysis:
            best_analysis = "多空因素交织，略偏正面"
    else:
        direction = "偏空"
        if not best_analysis:
            best_analysis = "多空因素交织，略偏负面"
    
    if scores["观望"] > scores["偏多"] and scores["观望"] > scores["偏空"]:
        direction = "观望"
        if not best_analysis:
            best_analysis = "关键事件前市场等待确认"
    
    # 置信度
    total = sum(scores.values())
    if total >= 4:
        confidence = "高"
    elif total >= 2:
        confidence = "中等"
    else:
        confidence = "低"
    
    # 保底分析
    if not best_analysis:
        if "涨" in text or "升" in text or "突破" in text or "涨超" in text:
            best_analysis = "价格上行，动能偏多，关注能否站稳"
            direction = "偏多" if direction == "观望" else direction
        elif "跌" in text or "跌破" in text or "跌超" in text or "降" in text:
            best_analysis = "价格下行，动能偏空，关注支撑位"
            direction = "偏空" if direction == "观望" else direction
        elif "爆仓" in text:
            best_analysis = "极端行情导致爆仓连锁反应"
        elif "whale" in text or "巨鲸" in text:
            best_analysis = "大额资金异动，建议关注链上确认"
        elif "监管" in text or "sec" in text or "cftc" in text or "法规" in text:
            best_analysis = "监管动态影响市场预期，波动可能加大"
        elif "usdc" in text or "usdt" in text or "稳定币" in text:
            best_analysis = "稳定币供应量变化反映市场资金流向"
        elif "ai" in text or "人工智能" in text:
            best_analysis = "技术面积极进展，长期基本面利好"
        else:
            best_analysis = "关注事件后续发展，等待明确交易信号"
    
    return direction, confidence, best_analysis, best_reason


def format_article(article, idx=1):
    """格式化单条新闻"""
    title = article.get("display", article.get("title", ""))
    level = article.get("level", "C")
    summary = article.get("summary", "")[:200]
    
    lv_emoji = {"S": "🔴", "A": "🟠", "B": "⚡", "C": "💡"}
    lv_name = {"S": "交易级", "A": "重要趋势", "B": "辅助分析", "C": "一般资讯"}
    emoji = lv_emoji.get(level, "💡")
    name = lv_name.get(level, "资讯")
    
    # 分析
    direction, conf, analysis, reason = analyze(f"{title} {summary}")
    
    dir_emoji = {"偏多": "📈", "偏空": "📉", "观望": "⏸️"}
    dir_emoji2 = dir_emoji.get(direction, "⏸️")
    
    text = f"{emoji}[{name}] {title}"
    if direction != "观望" or conf == "高":
        text += f"\n   {dir_emoji2} 判断: {direction}（{conf}置信）"
    text += f"\n   💡 {analysis}"
    
    return text


if __name__ == "__main__":
    tests = [
        "CoinGlass：过去24小时爆仓逾2.35亿美元，主爆空单",
        "BTC跌破64000美元，日内涨幅1.78%",
        "Circle获OCC批准设立国家信托银行",
        "美国民主党高层在投票前夕抨击特朗普加密货币政策",
        "Kraken推出AI代理交易",
        "USDC Treasury在Solana上新铸造2.5亿枚USDC",
        "James Wynn高杠杆做空标普500屡遭爆仓，累计亏损2200万美元",
        "Strategy比特币出售扰动市场，渣打仍坚持年末10万美元目标",
        "现代汽车在Avalanche公链上线内部跨境汇款系统",
        "Metaplanet联合研究：BTC抵押数字信贷登陆日本",
        "加密友好银行Nubank获墨西哥银行牌照",
        "Bitcoin whales sent BTC price to $64K",
    ]
    
    print("=" * 50)
    print("Signal 智能分析测试")
    print("=" * 50)
    
    for t in tests:
        direction, conf, analysis, reason = analyze(t)
        de = {"偏多": "📈", "偏空": "📉", "观望": "⏸️"}.get(direction, "⏸️")
        print(f"\n{t}")
        print(f"  {de} {direction}（{conf}）")
        print(f"  💡 {analysis[:60]}")
