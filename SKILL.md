---
name: automated-news-push
description: 全球加密快讯自动化采集→评分→分析→分层推送系统。使用 web_fetch 抓取4个免费数据源（PANews、CryptoPanic、Cointelegraph RSS、Bitcoin Magazine RSS），执行脚本后按级别实时/批量推送到 Safew Bot + 飞书群。
---

# 金峰策略 · Signal 全球加密快讯系统

定型版 v0.4 · 2026-07-11

## 系统概览

五层架构：**采集 → 解析 → 去重 → 四层评分 + 智能分析 → 分层推送**

每日自动运行时段 06:00~23:00（静默时段 00:00~05:59 全部积压）

## 架构细节

### 第一层：数据采集（4个免费源）

| 数据源 | URL | 语言 | 采集方式 |
|--------|-----|------|---------|
| PANews | `https://www.panewslab.com/` | 中文 | web_fetch |
| CryptoPanic | `https://cryptopanic.com/news` | 英文 | web_fetch |
| Cointelegraph | `https://cointelegraph.com/rss` | 英文(RSS) | web_fetch |
| Bitcoin Magazine | `https://bitcoinmagazine.com/.rss/full/` | 英文(RSS) | web_fetch |

⚠️ Windows 上 Python requests 外网超时，**必须用 web_fetch 工具采集**，存为缓存文件后喂给 main.py。

### 第二层：解析与去重

**解析器（scripts/main.py）：**
- `parse_panews()` — 正则切"PA一线"块，过滤时间行
- `parse_cryptopanic()` — 三路解析（X帖子 / 带·分隔行 / 独立长标题行），过滤来源名
- `parse_rss_xml()` — 正则提取 `<item>` 块

**去重（`_make_fingerprint()`）：**
- 英文新闻：取合并文本中**第一个4+字母英文词**（品牌/币种名）作为主指纹
- 中文新闻：取2-gram双字组集合排序拼接
- 验证效果：30条→27条，成功消除Kraken/Circle/Binance/现代汽车等跨源重复

**翻译（`translate_en()`）：**
- 30条精确标题映射 + 50+个币圈术语关键词替换
- 硬编码翻译表，无需外部API

### 第三层：四层评分引擎（scripts/scorer.py）

| 等级 | 名称 | 触发场景 | 推送 |
|:----:|:----:|:---------|:----:|
| 🔴 S | 交易级信号 | 链上资金/爆仓/宏观突变/地缘/监管/价格极端动作 | **实时** |
| 🟠 A | 重要趋势 | ETF/合规/机构/造币/巨头动态 | 积压1小时统推 |
| ⚡ B | 辅助参考 | 项目进展/生态/区域动态/技术更新 | 积压1小时统推 |
| 💡 C | 一般资讯 | 研究报告/常态新闻/行业观点 | 积压1小时统推 |

关键词体系（共50+条正则规则）：
- S级：清算/爆仓/鲸鱼/资金费率/融资/强平/OI变化/ETF净流/MSTR/微策略/贝莱德/美联储/降息/CPI/利率/地缘/制裁/中东/交易所挤兑/暂停提币/安全事故/链上大额转账（>5000BTC）/价格剧烈波动等
- A级：ETF/合规/牌照/造币/销毁/OTC/OTC/DERIVATIVES/机构等
- B级：上线/迁移/升级/生态/GAS/手续费调整/DAO/质押等
- C级：其它通过筛选的资讯

### 第四层：智能分析引擎（scripts/analyzer.py）

50+条正则自动判断每条新闻的多空方向：

**判断输出格式：**
```json
{
  "signal": "偏多" | "偏空" | "观望",
  "confidence": "高" | "中" | "低",
  "analysis": "一句话分析原因"
}
```

**信号优先级：偏空 > 偏多**（风控优先原则）

**匹配规则覆盖维度：**
- 链上资金：爆仓 → 偏空（高），巨鲸增持 → 偏多（中）
- ETF：大额净流入 → 偏多（高），大额净流出 → 偏空（高）
- 宏观：降息 → 偏多（高），加息/CPI超预期 → 偏空（高）
- 地缘：冲突/制裁 → 偏空（高）
- 交易所：挤兑/暂停提币 → 偏空（高）
- 技术：安全事故 → 偏空（高），主网上线 → 偏多（中）

### 第五层：分层推送（scripts/main.py）

**推送渠道双线：**
- Safew Bot（Telegram生态）：完整消息文本，自动分段（≤4000字符）
- 飞书群：交互式卡片，展示前10条

**按时段分流（核心创新）：**
```
🌙 00:00~05:59  静默时段 → 全部积压到 pending_batch.json
☀️ 06:00        每日首推 → 夜间积压全量推送（含S级）
☀️ 06:30        第一次采集 → S级实时 / A/B/C积压
☀️ 07:00~23:00  每30分钟采集 + 每小时整点flush
🌙 23:00~05:59  静默
```

**积压池：** `data/pending_batch.json` — JSON数组，跨session持久化，自带去重

## 文件结构

```
skills/automated-news-push/          ← 正式技能目录
├── SKILL.md                         本文件
├── config/
│   └── config.yaml                  系统配置（v0.4.0）
├── scripts/
│   ├── main.py                      主入口（全链路 + 推送分层）
│   ├── scorer.py                    四层评分引擎
│   └── analyzer.py                  智能多空分析引擎
├── data/
│   ├── sample_panews.txt            PANews 示例数据
│   ├── sample_cryptopanic.txt       CryptoPanic 示例数据
│   ├── sample_cointelegraph.txt     Cointelegraph 示例数据
│   ├── sample_bitcoinmag.txt        Bitcoin Magazine 示例数据
│   ├── pending_batch.json           积压池（A/B/C级暂存）
│   └── cache/                       缓存目录（cron自动采集落盘）
├── requirements.txt                 Python依赖
└── DEPRECATED.md                    说明

skills/signal/                        ← 旧目录，已废弃
```

## 使用方式

### 手动运行（测试用）
```bash
cd skills/automated-news-push
python scripts/main.py              # 使用内置示例数据
python scripts/main.py --flush      # 清空积压池并推送
```

### web_fetch 真实采集 + 推送
```python
from scripts.main import run
run(
    panews_raw="<web_fetch返回文本>",
    cryptopanic_raw="<web_fetch返回文本>",
    cointelegraph_raw="<web_fetch返回文本>",
    bitcoinmag_raw="<web_fetch返回文本>"
)
```

### 定时自动运行（cron任务）
两个cron任务已注册：
1. `signal-fetch-30min` — 每30分钟采集+评分+分层推送（06:30~23:30）
2. `signal-flush-hourly` — 每小时整点flush积压池（06:00~23:00）

每个cron任务启动一个isolated subagent，自动执行 web_fetch → 落缓存 → exec python main.py

## 迭代记录（关键决策）

| 时间 | 问题 | 方案 |
|:----:|:----|:----|
| 00:41 | PANews时间行误标为标题 | 正则 `[分钟小时]` → `(分钟\|小时)` |
| 00:41 | CryptoPanic只解析2条 | 三路解析（X帖/分隔行/独立标题）→ 20条 |
| 00:48 | 推送格式太机器化 | 弃用分数，改用自然语言3行格式 |
| 01:00 | 老板抱怨重复推送 | 内容指纹去重（英文品牌词）→ 30→27条 |
| 01:05 | CryptoPanic来源名当标题 | 检测标题长度+日期特征过滤 |
| 01:10 | 需要分层推送 | S级实时 / A/B/C积压1小时统推 |
| 01:18 | 静默时段需求 | 00~05全部积压，06:00首推 |

## 配置调优

- 关键词规则：编辑 `scripts/scorer.py` 中的 keyword 列表
- 分析逻辑：编辑 `scripts/analyzer.py` 中的信号匹配正则
- 推送配置：编辑 `config/config.yaml`
- 定时任务：通过 cron 命令更新
