"""
ai_insight.py — DeepSeek AI 新闻见解生成模块
每条新闻入库后触发AI深度分析，生成看涨/看跌判断+一句话摘要+市场影响分析
"""
import requests, json, os, re, time
from datetime import datetime

API_KEY = "sk-913be28d084c4f588552e4335d5b8afd"
API_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"

# 简版提示词（每条约 200-300 token，成本极低）
SHORT_PROMPT = """分析以下加密货币新闻，返回JSON格式：
{{
  "en_summary": "10字以内英文摘要（关键信息核心词）",
  "zh_summary": "一句话中文摘要（20字以内）",
  "sentiment": "bullish|bearish|neutral",
  "reason": "一句简短理由（15字以内）",
  "coins_affected": ["BTC","ETH","SOL"] （最多3个币种，如无关联则空数组）
}}

标题：{title}
来源：{source}
内容摘要：{content}
"""

# 深度版提示词（更详细的分析，用于日报/晚报）
DEEP_PROMPT = """你是一位专业的加密货币分析师。请分析以下新闻，提供深度见解。

返回严格JSON格式（不要markdown）：
{{
  "en_summary": "英文关键摘要（15字内）",
  "zh_summary": "中文一句话摘要（25字内）",
  "sentiment": "bullish|bearish|neutral",
  "impact_level": "high|medium|low",
  "reason": "简短判断理由（20字内）",
  "price_impact_btc": "对BTC的潜在影响（15字内）",
  "price_impact_eth": "对ETH的潜在影响（15字内）",
  "coins_affected": ["币种符号，最多3个"],
  "analysis": "一段深度分析（50-100字，中文，包含背景和逻辑链）"
}}

新闻标题：{title}
来源：{source}
内容：{content}
"""

def generate_insight(title, source="?", content="", deep=False):
    """调用DeepSeek生成AI见解，返回结构化dict"""
    if not title:
        return _default_insight()
    
    prompt = DEEP_PROMPT if deep else SHORT_PROMPT
    content_trunc = (content or title)[:300] if not deep else (content or title)[:500]
    prompt = prompt.format(title=title, source=source, content=content_trunc)
    
    try:
        resp = requests.post(API_URL, json={
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,  # 低温度保证一致性
            "max_tokens": 500 if deep else 250,
        }, headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }, timeout=15)
        
        if resp.status_code == 200:
            text = resp.json()["choices"][0]["message"]["content"]
            # 清理可能的markdown代码块标记
            text = text.strip().strip("`").strip()
            if text.startswith("json"):
                text = text[4:].strip()
            result = json.loads(text)
            return _validate(result)
        else:
            print(f"[AI] API错误 {resp.status_code}: {resp.text[:100]}")
            return _default_insight()
            
    except json.JSONDecodeError as e:
        print(f"[AI] JSON解析失败: {e}")
        return _default_insight()
    except Exception as e:
        print(f"[AI] 调用失败: {e}")
        return _default_insight()

def generate_insight_batch(articles, deep=False):
    """批量生成AI见解，传入文章列表，返回带见解的文章列表"""
    results = []
    for i, a in enumerate(articles):
        title = a.get("display", a.get("title", ""))
        source = a.get("source", "?")
        content = a.get("summary", a.get("analysis", ""))
        
        insight = generate_insight(title, source, content, deep)
        a["ai_insight"] = insight
        a["sentiment"] = insight.get("sentiment", "neutral")
        a["zh_summary"] = insight.get("zh_summary", "")
        if insight.get("coins_affected"):
            a["coins"] = insight["coins_affected"]
        
        results.append(a)
        if (i+1) % 5 == 0:
            print(f"  [AI] 已分析 {i+1}/{len(articles)} 条")
    
    print(f"[AI] 批量分析完成: {len(results)} 条")
    return results

def _validate(result):
    """确保返回结果包含所有必要字段"""
    defaults = _default_insight()
    for k, v in defaults.items():
        if k not in result:
            result[k] = v
    if result["sentiment"] not in ("bullish", "bearish", "neutral"):
        result["sentiment"] = "neutral"
    if not isinstance(result.get("coins_affected"), list):
        result["coins_affected"] = []
    return result

def _default_insight():
    return {
        "en_summary": "",
        "zh_summary": "",
        "sentiment": "neutral",
        "impact_level": "medium",
        "reason": "",
        "price_impact_btc": "",
        "price_impact_eth": "",
        "coins_affected": [],
        "analysis": ""
    }

# 测试入口
if __name__ == "__main__":
    test_title = "CoinGlass：过去24小时爆仓逾2.35亿美元，主爆空单"
    r = generate_insight(test_title, "PANews", deep=True)
    print(json.dumps(r, ensure_ascii=False, indent=2))
