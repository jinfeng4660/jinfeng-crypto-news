"""
在 render_site_v05 中加入历史文章系统
在函数开头加载 ARTICLES_HISTORY_JSON，合并当前文章，
输出到 index.html 时包含全部历史
"""
import os, json

BASE = r'C:\Users\Administrator\.openclaw\workspace\skills\automated-news-push'
HISTORY_PATH = os.path.join(BASE, 'data', 'articles_history.json')

# 读取 main.py
with open(os.path.join(BASE, 'scripts', 'main.py'), 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 在 render_site_v05 开头加入历史文章加载
# 在 "def render_site_v05" 内部第一个语句之后
insert_point = """    # 采集链上数据（BTC/ETH/SOL 合约数据+AI分析）"""
new_hist_load = """    # ===== 加载历史文章 =====
    history_path = os.path.join(BASE, "data", "articles_history.json")
    try:
        if os.path.exists(history_path):
            with open(history_path, "r", encoding="utf-8") as f:
                hist_articles = json.load(f)
            print(f"[历史] 加载 {len(hist_articles)} 条历史文章")
            # 合并：当前articles + 历史（去重，优先用新的）
            existing_hashes = set()
            merged = []
            for a in articles:
                h = a.get("title","") + a.get("source","")
                existing_hashes.add(h)
                merged.append(a)
            for a in hist_articles:
                h = a.get("title","") + a.get("source","")
                if h not in existing_hashes:
                    merged.append(a)
                    existing_hashes.add(h)
            # 保存最新版本（当前新文章追加到历史）
            for a in articles:
                h = a.get("title","") + a.get("source","")
                found = False
                for ha in hist_articles:
                    hh = ha.get("title","") + ha.get("source","")
                    if hh == h:
                        ha.update(a)  # 更新为新版本
                        found = True
                        break
                if not found:
                    hist_articles.append(a)
            with open(history_path, "w", encoding="utf-8") as f:
                json.dump(hist_articles, f, ensure_ascii=False)
            print(f"[历史] 保存后共 {len(hist_articles)} 条")
            articles = merged
            print(f"[渲染] 共 {len(articles)} 条文章（当前{len(articles)} + 历史{len(merged)-len(articles)}）")
        else:
            # 首次运行，保存当前文章作为历史基线
            with open(history_path, "w", encoding="utf-8") as f:
                json.dump(articles, f, ensure_ascii=False)
            print(f"[历史] 首次创建，保存 {len(articles)} 条")
    except Exception as e:
        print(f"[历史] 错误: {e}")
    
    """

if insert_point in content and 'history_path' not in content:
    content = content.replace(insert_point, new_hist_load + '\n' + insert_point, 1)
    print("[历史] 文章历史系统已注入到 render_site_v05")
else:
    print("[历史] 注入点不存在或已存在，跳过")
    if 'history_path' in content:
        print("[历史] 已存在")

# 写入
with open(os.path.join(BASE, 'scripts', 'main.py'), 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✅ 完成")
