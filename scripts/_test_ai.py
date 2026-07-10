import json, sys
sys.stdout.reconfigure(encoding='utf-8')
sys.stdin.reconfigure(encoding='utf-8')

# 直接调ai_insight测试
from ai_insight import generate_insight

test_cases = [
    ("CoinGlass：过去24小时爆仓逾2.35亿美元，主爆空单", "PANews"),
    ("Circle获OCC批准，USDC合规化进程加速", "PANews"),
    ("BTC跌破64000美元，日内跌幅扩大", "Cointelegraph"),
]

for title, src in test_cases:
    r = generate_insight(title, src, deep=True)
    print(f"\n=== {title[:30]}... ===")
    print(f"  摘要: {r['zh_summary']}")
    print(f"  情绪: {r['sentiment']} | 理由: {r['reason']}")
    print(f"  影响币种: {r['coins_affected']}")
    print(f"  影响程度: {r['impact_level']}")
    print(f"  分析: {r['analysis'][:80]}...")
