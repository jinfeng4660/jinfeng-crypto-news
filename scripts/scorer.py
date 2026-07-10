"""
Signal - 智能评分引擎 (V2 四层评分体系)
老板指定架构：分层关键词 → 打分 → 标签
"""

import re

# ==================== 四层关键词体系 ====================
# S级 - 交易级信号（直接影响操作决策，必须推送）
# A级 - 重要趋势（中期策略参考，必须推送）
# B级 - 辅助参考（有价值但不紧迫）
# C级 - 一般资讯（分情况推送）

KEYWORD_LEVELS = {
    "S": {
        "name": "交易级信号",
        "emoji": "🔴",
        "desc": "直接影响开平仓决策的信息",
        "weight": 10,
        "keywords": [
            # 链上巨鲸/大额
            r"whale|巨鲸|大额转账|large.*transfer|chain.*liquid",
            r"address.*(transfer|transferred|moved|转|存入|转出|归集)",
            r"wallet.*(move|transfer|collect)",
            # 爆仓/清算
            r"爆仓|liquidation|liquidat|清仓|清算|强制平仓",
            r"累計清算|累计清算|total.*liquid|open.*interest.*drop",
            # 持仓/资金费率
            r"funding rate|资金费率|funding",
            r"open interest|oi.*(rise|drop|surge|plunge)|持仓量",
            # 地缘政治冲突
            r"伊朗|iran|中东|middle.?east|美伊|以色列|israel|战争|war",
            r"sanction|制裁|核.*(谈|试|协议)|nuclear",
            r"军事|military|冲突|conflict|袭击|strike",
            # 宏观超级事件
            r"加息|降息|rate.*(hike|cut)|利率决议",
            r"cpi|通胀|inflation|pce|核心通胀|core cpi",
            r"非农|nonfarm|就业|失业率|unemployment|jobless",
            r"国债收益率|treasury.*yield|国债.*倒挂|yield.*curve",
            # 监管突发
            r"sec.*sue|sec.*指控|sec.*起诉|起诉|罚款|fine",
            r"禁止交易|ban|禁止|shut.?down|关停",
            r"cftc.*(sue|charge|fine|起诉|罚款)",
            # 交易所信任危机
            r"usdt.*depeg|usdc.*depeg|脱钩|脱锚",
            r"bank.run|挤兑|run.on|暂停.*提|停止.*提",
            r"frozen|冻结|扣押|seize|查封",
            # 价格极端
            r"闪崩|flash.?crash|暴跌|崩盘|crash|暴跌|黑天鹅|black.?swan",
            r"暴涨|暴拉|pump.*dump|割韭菜|rug|跑路|scam|诈骗",
            # ETF资金流
            r"etf.*(inflow|outflow|flow|净流入|净流出|净买入|净卖出)",
            r"spot.*etf.*(data|flow|volume)",
            r"btc.*etf|eth.*etf",
            # 机构大动作
            r"strategy.*(sale|sell|出售|卖|买入|buy|buying)",
            r"microstrategy.*(sale|sell|出售|buy)",
            r"blackrock.*(sell|卖|buy|买入|etf)",
            # 宏观经济数据发布
            r"cpi.*数据|pce.*数据|非农数据|gdp.*数据",
            r"失业金|初请|续请|jobless.*claims",
        ]
    },
    "A": {
        "name": "重要趋势",
        "emoji": "🟠",
        "desc": "影响中期策略判断",
        "weight": 7,
        "keywords": [
            # 政治/政府
            r"trump|特朗普|biden|拜登|election|选举|民调|poll",
            r"政府|government|政变|coup|内阁|白宫|white.?house",
            # 大国
            r"中国|china|香港|hong.?kong|台湾|taiwan|人民币|rmb|cny",
            r"俄罗斯|russia|乌克兰|ukraine|欧洲|europe|eu|欧盟",
            # 主流机构
            r"blackrock|贝莱德|fidelity|富达|jpmorgan|摩根|goldman|高盛",
            r"circle|usdc|usdt|tether|paxos",
            r"strategy|微策略|microstrategy|metaplanet|saylor",
            # 交易所重大公告
            r"coinbase|binance|okx|bybit|kraken|bitget",
            r"上币|listing|delist|退市|暂停交易|下线",
            # 监管动向
            r"sec|cftc|occ|finra|finma|fca|nydf|oak",
            r"牌照|license|批准|approv|法案|bill|crypto.?bill",
            # 链上数据趋势
            r"tvl|total.?value.?locked|锁仓|defi.*(volume|数据)",
            r"stablecoin.*(supply|供应|发行|mint|铸造|burn|销毁)",
            r"etf.*(approv|批准|deny|拒绝|delay|延迟)",
            # 矿工
            r"矿工|miner|挖矿|hashrate|算力|难度|difficulty",
            r"减半|halving|矿机|mining.*(pool|rig|farm)",
            # 价格突破关键位
            r"突破|跌破|涨超|跌超|创.*新高|创.*新低|ath|新高|新低",
            r"btc.*(6[0-9]|7[0-9]|8[0-9])|btc.*(万|k|000)",
            r"eth.*(2[0-9]00|3[0-9]00|4[0-9]00|5[0-9]00)",
            r"sol.*([0-9]{2,3})",
            # 交易所余额
            r"exchange.*(reserve|balance|储备|余额|supply)",
            # 安全漏洞
            r"漏洞|vuln|bug|0day|exploit|攻击|attack|hack|黑客|被盗|钓鱼|phish",
            # AI向加密
            r"ai.*(agent|代理|crypto|加密)|agentic.*(trad|交易)",
        ]
    },
    "B": {
        "name": "辅助参考",
        "emoji": "⚡",
        "desc": "有价值但不紧急",
        "weight": 4,
        "keywords": [
            # 项目进展/上线
            r"上线|launch|上币|listing|上线.*合约|perpetual",
            r"融资|raise|funding|fundraise|融资.*(万|亿)|million|billion",
            r"投资|invest|收购|acquisit|合并|merger",
            # 基础设施
            r"代币化|tokeniz|rwa|real.?world.?asset|实物资产",
            r"solidity|evm|zk|rollup|l2|layer.?2",
            # 区域
            r"日本|japan|韩国|korea|新加坡|singapore|dubai|阿联酋|uae",
            r"中国香港|hong.?kong.*(web3|crypto|加密|虚拟)",
            # L1/L2链
            r"solana|sol|ethereum|eth|bitcoin|btc|bnb|avax|avalanche",
            r"polygon|matic|arb|arbitrum|op|optimism|base",
            r"hyperliquid|hype|sui|aptos|near|celestia|tia",
            # 板块热点
            r"defi|lending|借贷|dex|swap|稳定币|stablecoin",
            r"memecoin|meme|nft|gamefi|rwa|depin|lsd|lst|ai|crypto",
            # KOL
            r"tom.?lee|planb|woo.?bull|checkmate|glassnode",
            r"分析|analys|预测|predict|outlook|展望",
            # 合作
            r"partner|合作|integration|集成|integrat|新.*(合作|伙伴)",
        ]
    },
    "C": {
        "name": "一般资讯",
        "emoji": "💡",
        "desc": "信息参考",
        "weight": 1,
        "keywords": [
            r"报告|report|research|研究|观点|opinion|调查|survey",
            r"推文|tweet|post|x.*(post|tweet)",
            r"日涨幅|日内|24h|24小时|daily",
            r"订阅|subscribe|关注|follow",
        ]
    }
}


class ScoreEngine:
    """四层关键词评分引擎"""
    
    def __init__(self):
        self.levels = KEYWORD_LEVELS
    
    def score_article(self, article):
        """对单篇文章评分，返回等级和分数"""
        text = article.get("display", article.get("title", ""))
        summary = article.get("summary", "")
        source = article.get("source", "")
        
        full_text = f"{text} {summary}"
        text_lower = full_text.lower()
        
        level_scores = {}
        
        for level, config in self.levels.items():
            total_score = 0
            match_count = 0
            for kw in config["keywords"]:
                matches = re.findall(kw, text_lower)
                if matches:
                    cnt = len(matches)
                    total_score += cnt * 2
                    match_count += cnt
            if match_count > 0:
                level_scores[level] = {
                    "score": total_score,
                    "matches": match_count
                }
        
        # 确定最高等级
        best_level = "C"
        best_score = 0
        
        for level in ["S", "A", "B", "C"]:
            if level in level_scores:
                sc = level_scores[level]["score"]
                if sc > best_score:
                    best_score = sc
                    best_level = level
        
        # C级至少有基础分
        if best_score == 0:
            # 中文PANews新闻默认过线
            if source == "PANews" and len(text) > 5:
                best_score = 1
                best_level = "C"
            else:
                # 无匹配英文降权
                return {
                    "level": "N", "emoji": "⚪", "score": 0,
                    "decision": "skip", "detail": "无关键词匹配"
                }
        
        # 决策
        skip_levels = {"S": 0.1, "A": 0.3, "B": 0.8, "C": 0.6}
        rand_cutoff = {k: 1.0 - v for k, v in skip_levels.items()}
        
        conf = self.levels.get(best_level, {})
        
        return {
            "level": best_level,
            "emoji": conf.get("emoji", "💡"),
            "score": best_score,
            "decision": "push",
            "detail": f"{conf.get('name','?')}({best_score}分,{level_scores.get(best_level,{}).get('matches',0)}个匹配)"
        }
    
    def score_batch(self, articles):
        """批量评分 + 排序"""
        scored = []
        for art in articles:
            result = self.score_article(art)
            art["scoring"] = result
            art["level"] = result["level"]
            art["emoji"] = result["emoji"]
            art["score_num"] = result["score"]
            
            scored.append((result["score"], {
                "S": 0, "A": 1, "B": 2, "C": 3, "N": 4
            }.get(result["level"], 9), art))
        
        # 排序：等级优先，分数次之
        scored.sort(key=lambda x: (x[1], -x[0]))
        
        # 过滤N级
        filtered = [art for _, _, art in scored if art.get("level") != "N"]
        
        return filtered


if __name__ == "__main__":
    engine = ScoreEngine()
    
    tests = [
        {"title": "BTC跌破64000美元，日内涨幅1.78%", "source": "PANews"},
        {"title": "CoinGlass：过去24小时爆仓逾2.35亿美元，主爆空单", "source": "PANews"},
        {"title": "Whale Alert: 10000 BTC transferred from unknown wallet to Binance", "source": "CryptoPanic"},
        {"title": "币安上线SK Hynix美股永续合约", "source": "PANews"},
        {"title": "美国CPI数据公布，核心CPI同比3.2%低于预期", "source": "PANews"},
        {"title": "Kraken推出AI代理交易功能", "source": "PANews"},
        {"title": "现代汽车在Avalanche公链上线内部跨境汇款系统", "source": "PANews"},
        {"title": "加密友好银行Nubank获墨西哥银行牌照", "source": "PANews"},
        {"title": "What is SpaceX? Is it really worth $2 Trillion?", "source": "CryptoPanic"},
        {"title": "Tom Lee Says Crypto Is The New Memory Trade", "source": "CryptoPanic"},
    ]
    
    print("=" * 60)
    print("信号评分测试")
    print("=" * 60)
    
    for t in tests:
        result = engine.score_article(t)
        emoji = result["emoji"]
        level = result["level"]
        score = result["score"]
        if result["decision"] == "skip":
            print(f"  ⚪ [{level}][0分] {t['title'][:40]} → 跳过")
        else:
            print(f"  {emoji} [{level}][{score}分] {t['title'][:45]}")
    
    print(f"\n批量排序:")
    filtered = engine.score_batch(tests)
    for a in filtered:
        emoji = a.get("emoji", "?")
        level = a.get("level", "?")
        score = a.get("score_num", 0)
        title = a.get("title", "")[:45]
        print(f"  {emoji} [{level}][{score}分] {title}")
