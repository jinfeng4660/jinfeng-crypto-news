"""
种子脚本来填充文章历史数据库
生成多天不同时间的历史文章数据
"""
import json, os, random

HISTORY_PATH = r'C:\Users\Administrator\.openclaw\workspace\skills\automated-news-push\data\articles_history.json'

# 不同日期的文章（60+条）
all_articles = [
    # ===== 7月9日 =====
    {"title": "BTC突破65000美元关口，24小时涨幅3.2%", "display": "BTC突破65000美元关口，24小时涨幅3.2%", "level": "S", "score_num": 8, "source": "PANews", "sentiment": "bullish", "analysis": "BTC强势突破关键阻力位65000美元，放量上涨确认趋势延续性。", "coins": ["BTC"]},
    {"title": "美联储7月维持利率不变概率升至92%", "display": "美联储7月维持利率不变概率升至92%", "level": "S", "score_num": 7, "source": "CryptoPanic", "sentiment": "neutral", "analysis": "CME FedWatch工具显示市场几乎完全定价美联储7月按兵不动。", "coins": ["BTC", "ETH"]},
    {"title": "ETH链上活跃地址数创3个月新高", "display": "ETH链上活跃地址数创3个月新高", "level": "A", "score_num": 6, "source": "CoinDesk", "sentiment": "bullish", "analysis": "ETH链上活跃度持续攀升，Layer2交易量同步增长。", "coins": ["ETH"]},
    {"title": "Solana生态TVL突破80亿美元", "display": "Solana生态TVL突破80亿美元", "level": "A", "score_num": 6, "source": "Decrypt", "sentiment": "bullish", "analysis": "Solana生态增长势头强劲，DeFi协议锁仓量创年度新高。", "coins": ["SOL"]},
    {"title": "美国参议院通过稳定币监管框架法案", "display": "美国参议院通过稳定币监管框架法案", "level": "S", "score_num": 9, "source": "CryptoPanic", "sentiment": "bullish", "analysis": "立法里程碑！稳定币发行将纳入联邦监管体系，合规化加速利好行业。", "coins": ["ALL"]},
    {"title": "MicroStrategy再次增持5000枚BTC", "display": "MicroStrategy再次增持5000枚BTC", "level": "S", "score_num": 8, "source": "Bitcoin Magazine", "sentiment": "bullish", "analysis": "Michael Saylor继续执行BTC战略储备计划，机构配置趋势不改。", "coins": ["BTC"]},
    {"title": "DOGE日活跃地址突破100万", "display": "DOGE日活跃地址突破100万", "level": "B", "score_num": 4, "source": "PANews", "sentiment": "bullish", "analysis": "DOGE生态应用增长带动链上活跃度攀升。", "coins": ["DOGE"]},
    
    # ===== 7月10日 =====
    {"title": "以太坊ETF单日净流入2.8亿美元", "display": "以太坊ETF单日净流入2.8亿美元", "level": "S", "score_num": 8, "source": "PANews", "sentiment": "bullish", "analysis": "机构资金持续涌入ETH现货ETF，市场情绪显著改善。", "coins": ["ETH"]},
    {"title": "德国政府BTC持仓完全清空", "display": "德国政府BTC持仓完全清空", "level": "S", "score_num": 9, "source": "CryptoPanic", "sentiment": "bullish", "analysis": "德国抛压完全解除，市场最后一波重大利空落地。", "coins": ["BTC"]},
    {"title": "SUI链上交易量突破历史记录", "display": "SUI链上交易量突破历史记录", "level": "A", "score_num": 6, "source": "CoinDesk", "sentiment": "bullish", "analysis": "SUI生态持续爆发，DeFi+NFT双轮驱动交易量创新高。", "coins": ["SUI"]},
    {"title": "BNB Chain宣布Q3生态激励计划", "display": "BNB Chain宣布Q3生态激励计划", "level": "B", "score_num": 5, "source": "PANews", "sentiment": "bullish", "analysis": "BNB Chain推出新一轮开发者激励计划，总奖金池1亿美元。", "coins": ["BNB"]},
    {"title": "印度将加密资产纳入税法明确框架", "display": "印度将加密资产纳入税法明确框架", "level": "A", "score_num": 5, "source": "CryptoPanic", "sentiment": "neutral", "analysis": "印度监管清晰化有利于推动合规交易所重返市场。", "coins": ["ALL"]},
    {"title": "Avalanche与Visa达成支付合作协议", "display": "Avalanche与Visa达成支付合作协议", "level": "A", "score_num": 6, "source": "Decrypt", "sentiment": "bullish", "analysis": "传统支付巨头Visa与Avalanche合作探索跨境支付解决方案。", "coins": ["AVAX"]},
    {"title": "Bitcoin算力创历史新高780EH/s", "display": "Bitcoin算力创历史新高780EH/s", "level": "B", "score_num": 4, "source": "Bitcoin Magazine", "sentiment": "bullish", "analysis": "矿工信心持续增强，算力稳步攀升显示网络安全性加强。", "coins": ["BTC"]},
    
    # ===== 7月11日（今天） =====
    {"title": "CoinGlass：过去24小时爆仓逾2.35亿美元，主爆空单", "display": "CoinGlass：过去24小时爆仓逾2.35亿美元，主爆空单", "level": "S", "score_num": 9, "source": "PANews", "sentiment": "bullish", "analysis": "空头遭到清算，短期市场情绪偏多。主爆空单说明市场在上涨过程中空头被迫平仓。", "coins": ["ALL"]},
    {"title": "James Wynn高杠杆做空标普500屡遭爆仓，累计亏损2200万美元", "display": "James Wynn高杠杆做空标普500屡遭爆仓，累计亏损2200万美元", "level": "S", "score_num": 8, "source": "CryptoPanic", "sentiment": "bearish", "analysis": "宏观做空者持续爆仓说明当前趋势方向与做空方向相反。", "coins": ["ALL"]},
    {"title": "Circle获OCC批准 迈出合规化关键一步", "display": "Circle获OCC批准 迈出合规化关键一步", "level": "A", "score_num": 6, "source": "PANews", "sentiment": "bullish", "analysis": "Circle成为首个获得OCC全国性信托银行牌照的加密公司，合规化重大里程碑。", "coins": ["ETH"]},
    {"title": "稳定币监管走向分化：Circle合规加速 vs Tether面临欧盟挑战", "display": "稳定币监管走向分化：Circle合规加速 vs Tether面临欧盟挑战", "level": "A", "score_num": 6, "source": "CryptoPanic", "sentiment": "neutral", "analysis": "USDC与USDT的监管路径出现分化，Circle在美国合规领先，Tether面临MiCA挑战。", "coins": ["ETH"]},
    {"title": "Kraken 推出 AI 代理交易功能", "display": "Kraken 推出 AI 代理交易功能", "level": "A", "score_num": 5, "source": "PANews", "sentiment": "bullish", "analysis": "Kraken推出AI驱动的自动化交易代理，支持策略回测和智能执行。", "coins": ["ALL"]},
    {"title": "USDC Treasury 在 Solana 上新铸造 2.5 亿枚 USDC", "display": "USDC Treasury 在 Solana 上新铸造 2.5 亿枚 USDC", "level": "A", "score_num": 5, "source": "PANews", "sentiment": "bullish", "analysis": "Solana链上USDC供应量增加，流动性增强有利于DeFi生态发展。", "coins": ["SOL"]},
    {"title": "Polymarket 正式申请美国 NFA 牌照", "display": "Polymarket 正式申请美国 NFA 牌照", "level": "A", "score_num": 4, "source": "PANews", "sentiment": "bullish", "analysis": "预测市场巨头Polymarket向合规化迈出重要一步。", "coins": ["ALL"]},
    {"title": "美国民主党高层在投票前夕抨击特朗普加密货币政策", "display": "美国民主党高层在投票前夕抨击特朗普加密货币政策", "level": "A", "score_num": 4, "source": "PANews", "sentiment": "neutral", "analysis": "美国两党对加密监管立场分歧加大，选举年政策不确定性增加。", "coins": ["ALL"]},
    {"title": "US Lawmakers Reintroduce Stablecoin Bill with Bipartisan Support", "display": "US Lawmakers Reintroduce Stablecoin Bill with Bipartisan Support", "level": "A", "score_num": 5, "source": "Decrypt", "sentiment": "bullish", "analysis": "两党议员重新提出稳定币法案，监管框架有望年内落地。", "coins": ["ALL"]},
    {"title": "BNB Chain 推出 AI 代理链", "display": "BNB Chain 推出 AI 代理链", "level": "B", "score_num": 4, "source": "PANews", "sentiment": "bullish", "analysis": "BNB Chain推出专用AI代理链，支持智能合约AI agent部署。", "coins": ["BNB"]},
    {"title": "Metaplanet 联合研究 BTC 抵押数字信贷登陆日本", "display": "Metaplanet 联合研究 BTC 抵押数字信贷登陆日本", "level": "B", "score_num": 4, "source": "Bitcoin Magazine", "sentiment": "bullish", "analysis": "日本上市公司推进BTC抵押贷款业务，亚洲机构采纳加速。", "coins": ["BTC"]},
    {"title": "Ethereum Layer 2 TVL Breaks $50B as Base Leads Growth", "display": "Ethereum Layer 2 TVL Breaks $50B as Base Leads Growth", "level": "B", "score_num": 4, "source": "CoinDesk", "sentiment": "bullish", "analysis": "ETH Layer2锁仓量突破500亿美元，Base链贡献主要增量。", "coins": ["ETH"]},
    {"title": "Aave V3 上线 zkSync", "display": "Aave V3 上线 zkSync", "level": "B", "score_num": 3, "source": "PANews", "sentiment": "bullish", "analysis": "Aave扩展至zkSync生态，进一步巩固DeFi借贷龙头地位。", "coins": ["ETH"]},
    {"title": "现代汽车在 Avalanche 公链上线内部跨境汇款系统", "display": "现代汽车在 Avalanche 公链上线内部跨境汇款系统", "level": "B", "score_num": 3, "source": "PANews", "sentiment": "bullish", "analysis": "传统企业采用区块链技术解决跨境支付痛点，企业级采用里程碑。", "coins": ["AVAX"]},
    {"title": "Bitfinex分析师：BTC回调属健康修正，技术指标仍指向上涨", "display": "Bitfinex分析师：BTC回调属健康修正，技术指标仍指向上涨", "level": "B", "score_num": 3, "source": "CryptoPanic", "sentiment": "bullish", "analysis": "比特币短期回调被视为健康的牛市调整，长期看涨结构未破坏。", "coins": ["BTC"]},
    {"title": "Solana NFT Sales Volume Up 40% in Q2 Despite Broader Market Slump", "display": "Solana NFT Sales Volume Up 40% in Q2 Despite Broader Market Slump", "level": "B", "score_num": 3, "source": "Decrypt", "sentiment": "bullish", "analysis": "Solana NFT交易量逆市增长，生态活力持续增强。", "coins": ["SOL"]},
    {"title": "地址 0xf02d 亏损 452 万美元后再次 10 倍杠杆做空 HYPE", "display": "地址 0xf02d 亏损 452 万美元后再次 10 倍杠杆做空 HYPE", "level": "B", "score_num": 2, "source": "PANews", "sentiment": "bearish", "analysis": "巨鲸持续做空HYPE，高杠杆操作风险极高。", "coins": ["HYPE"]},
]

# 添加随机投票数据
for a in all_articles:
    a.setdefault('votes', {
        'bullish': random.randint(15, 55),
        'bearish': random.randint(5, 35),
        'important': random.randint(5, 25)
    })
    a.setdefault('url', '')

# 保存
with open(HISTORY_PATH, 'w', encoding='utf-8') as f:
    json.dump(all_articles, f, ensure_ascii=False)

print(f'写入 {len(all_articles)} 条历史文章到 {HISTORY_PATH}')
print(f'级别分布: S={sum(1 for a in all_articles if a["level"]=="S")}, A={sum(1 for a in all_articles if a["level"]=="A")}, B={sum(1 for a in all_articles if a["level"]=="B")}')
