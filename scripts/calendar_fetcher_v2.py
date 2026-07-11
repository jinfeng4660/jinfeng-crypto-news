"""
Forex Factory 财经日历采集器 V2
功能：
1. 从Forex Factory抓取每周经济日历数据（完整7天）
2. SQLite持久化历史数据（含已发布事件的历史记录）
3. AI分析：对每个事件生成市场影响分析
4. 支持多数据源聚合（FF主源 + Investing备用）
"""

import sys, json, re, requests, sqlite3, os, hashlib
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "calendar_history.db")

# SQLite schema
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS calendar_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ev_key TEXT UNIQUE NOT NULL,       -- hash: date+title+currency
    date TEXT NOT NULL,
    weekday TEXT,
    time TEXT,
    impact TEXT,                        -- high / medium
    currency TEXT,
    title TEXT,
    actual TEXT DEFAULT '',
    previous TEXT DEFAULT '',
    forecast TEXT DEFAULT '',
    ai_analysis TEXT DEFAULT '',        -- AI分析JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_cal_date ON calendar_events(date);
CREATE INDEX IF NOT EXISTS idx_cal_impact ON calendar_events(impact);
"""


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    return conn


def ev_key(ev):
    """生成唯一事件key"""
    raw = f'{ev.get("date","")}|{ev.get("title","")}|{ev.get("currency","")}'
    return hashlib.md5(raw.encode()).hexdigest()


def save_to_db(conn, events):
    """追加/更新事件到SQLite"""
    cur = conn.cursor()
    added = 0
    updated = 0
    for ev in events:
        key = ev_key(ev)
        cur.execute("SELECT id FROM calendar_events WHERE ev_key=?", (key,))
        row = cur.fetchone()
        if row:
            # 更新实际值/预测值（已发布事件可能有新数据）
            cur.execute("""
                UPDATE calendar_events SET
                    actual=?, previous=?, forecast=?, updated_at=CURRENT_TIMESTAMP
                WHERE ev_key=?
            """, (ev.get('actual',''), ev.get('previous',''), ev.get('forecast',''), key))
            updated += 1
        else:
            cur.execute("""
                INSERT INTO calendar_events (ev_key, date, weekday, time, impact, currency, title, actual, previous, forecast)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (
                key,
                ev.get('date',''),
                ev.get('weekday',''),
                ev.get('time',''),
                ev.get('impact',''),
                ev.get('currency',''),
                ev.get('title',''),
                ev.get('actual',''),
                ev.get('previous',''),
                ev.get('forecast',''),
            ))
            added += 1
    conn.commit()
    return added, updated


def load_historical_events(conn, days_back=30):
    """从DB加载近期历史事件"""
    cur = conn.cursor()
    cur.execute("""
        SELECT date, weekday, time, impact, currency, title, actual, previous, forecast, ai_analysis
        FROM calendar_events
        WHERE date >= date('now', ?)
        ORDER BY date, time
    """, (f'-{days_back} days',))
    rows = cur.fetchall()
    cols = ['date','weekday','time','impact','currency','title','actual','previous','forecast','ai_analysis']
    return [dict(zip(cols, r)) for r in rows]


#####################
# 数据源1: Forex Factory (主源)
#####################

def fetch_ff_calendar(proxies=None):
    """从Forex Factory抓取当周日历"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }
    url = 'https://www.forexfactory.com/calendar'

    try:
        resp = requests.get(url, headers=headers, proxies=proxies, timeout=20)
        if resp.status_code != 200:
            return [], f'FF返回{resp.status_code}'
    except Exception as e:
        return [], f'FF请求失败: {e}'

    text = resp.text

    # Extract days array from calendarComponentStates[1]
    idx = text.find('days: [')
    if idx < 0:
        return [], '未找到FF日历数据'

    start = idx + 6
    depth = 0
    in_str = False
    esc = False
    end = start
    for i in range(start, len(text)):
        c = text[i]
        if esc: esc = False; continue
        if c == '\\' and in_str: esc = True; continue
        if c == '"' and not esc: in_str = not in_str; continue
        if not in_str:
            if c == '[': depth += 1
            elif c == ']': depth -= 1
            if depth == 0: end = i + 1; break

    arr_js = text[start:end].replace('\\/', '/')

    try:
        import json5
        days = json5.loads(arr_js)
    except Exception as e:
        return [], f'FF解析失败: {e}'

    if not days:
        return [], 'FF无数据'

    # Also try to get next week data from other states
    next_week_events = []
    for state_idx in range(2, 4):
        pattern = f'days: ['
        idx2 = text.find(f'calendarComponentStates[{state_idx}]')
        if idx2 < 0:
            continue
        idx_days = text.find('days: [', idx2)
        if idx_days < 0:
            continue
        start2 = idx_days + 6
        depth = 0
        in_str = False
        esc = False
        end2 = start2
        for i in range(start2, len(text)):
            c = text[i]
            if esc: esc = False; continue
            if c == '\\' and in_str: esc = True; continue
            if c == '"' and not esc: in_str = not in_str; continue
            if not in_str:
                if c == '[': depth += 1
                elif c == ']': depth -= 1
                if depth == 0: end2 = i + 1; break
        arr_js2 = text[start2:end2]
        try:
            days2 = json5.loads(arr_js2)
            for day in days2:
                for ev in day.get('events', []):
                    next_week_events.append(ev)
        except:
            pass

    now = datetime.now()
    today_ts = int(datetime(now.year, now.month, now.day).timestamp())
    cutoff_ts = today_ts + 14 * 86400

    events = []
    for day in days:
        dl = day.get('dateline', 0)
        if not dl or dl < today_ts - 86400 or dl > cutoff_ts:
            continue

        dt = datetime.fromtimestamp(dl)
        date_str = dt.strftime('%Y-%m-%d')
        weekday_cn = ['一','二','三','四','五','六','日'][dt.weekday()]
        is_today = (dl == today_ts)

        for ev in day.get('events', []):
            impact = ev.get('impactName', 'low')
            if impact not in ('high', 'medium'):
                continue

            tstr = ev.get('timeLabel', '') or ev.get('time', '') or ''

            event = {
                'source': 'forexfactory',
                'date': date_str,
                'weekday': weekday_cn,
                'isToday': is_today,
                'time': tstr,
                'impact': impact,
                'currency': ev.get('currency', ''),
                'title': ev.get('name', ''),
                'actual': ev.get('actual', '') or '',
                'previous': ev.get('previous', '') or '',
                'forecast': ev.get('forecast', '') or '',
            }
            events.append(event)

    return events, None


#####################
# 数据源2: Investing.com (备用，更多事件)
#####################

def fetch_investing_calendar(proxies=None):
    """从Investing.com抓取经济日历（备用数据源）"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'X-Requested-With': 'XMLHttpRequest',
    }
    # Investing经济日历API
    url = 'https://www.investing.com/economic-calendar/Service/getCalendarFilterData'
    payload = {
        'dateFrom': datetime.now().strftime('%Y-%m-%d'),
        'dateTo': datetime.now().strftime('%Y-%m-%d'),
        'currentTab': 'thisWeek',
        'limitCountries': '',
    }
    try:
        resp = requests.post(url, headers=headers, data=payload, proxies=proxies, timeout=15)
        if resp.status_code != 200:
            return [], f'Investing返回{resp.status_code}'
        data = resp.json()
        events = []
        for item in data.get('data', data if isinstance(data, list) else []):
            if isinstance(item, dict):
                events.append({
                    'source': 'investing',
                    'date': item.get('date', ''),
                    'time': item.get('time', ''),
                    'impact': 'high' if 'red' in str(item.get('importance', '')).lower() else 'medium',
                    'currency': item.get('currency', ''),
                    'title': item.get('event', item.get('name', '')),
                    'actual': item.get('actual', '') or '',
                    'previous': item.get('previous', '') or '',
                    'forecast': item.get('forecast', '') or '',
                })
        return events, None
    except Exception as e:
        return [], f'Investing失败: {e}'


#####################
# AI分析引擎
#####################

def analyze_events(events):
    """对每个事件生成AI分析"""
    analyzed = []
    for ev in events:
        analysis = {
            'impact_assessment': '',
            'trend_note': '',
            'crypto_relevance': '',
            'direction_bias': 'neutral',
            'confidence': 'low',
        }
        
        title = ev.get('title', '')
        currency = ev.get('currency', '')
        impact = ev.get('impact', '')
        actual = ev.get('actual', '')
        previous = ev.get('previous', '')
        forecast = ev.get('forecast', '')
        
        # 如果已发布，分析实际 vs 预测偏差
        if actual and forecast:
            try:
                a = float(actual.replace('%', '').replace('K', '').replace('M', '').replace('B', '').strip())
                f = float(forecast.replace('%', '').replace('K', '').replace('M', '').replace('B', '').strip())
                deviation_pct = ((a - f) / abs(f) * 100) if f != 0 else 0
                
                if abs(deviation_pct) > 10:
                    analysis['impact_assessment'] = f'实际偏差{deviation_pct:.0f}%，远超预期，市场可能已较大波动'
                    analysis['confidence'] = 'high'
                elif abs(deviation_pct) > 3:
                    analysis['impact_assessment'] = f'实际偏差{deviation_pct:.0f}%，与预期偏离较大，注意行情异动'
                    analysis['confidence'] = 'medium'
                else:
                    analysis['impact_assessment'] = '实际值与预期基本一致，市场反应有限'
                    analysis['confidence'] = 'medium'
                
                # 判断方向
                if '就业' in title or 'GDP' in title or 'CPI' in title or '通胀' in title:
                    if a > f:
                        analysis['direction_bias'] = 'bearish' if '就业' in title or 'GDP' in title else 'bullish'
                    elif a < f:
                        analysis['direction_bias'] = 'bullish' if '就业' in title or 'GDP' in title else 'bearish'
            except ValueError:
                analysis['impact_assessment'] = f'实际: {actual} (前值: {previous})'
        else:
            # 未发布事件
            if impact == 'high':
                analysis['impact_assessment'] = f'高影响事件，{title}，市场高度关注'
                analysis['confidence'] = 'medium'
            else:
                analysis['impact_assessment'] = f'{currency} {title}，中等影响，需关注'
                analysis['confidence'] = 'low'
        
        # 加密货币相关性分析
        crypto_keywords = ['CPI', '通胀', 'GDP', '就业', '利率', '失业', '非农', 'NFP', 'FOMC',
                          'PMI', '零售', '美联储', 'fed', 'FED', '消费', '信心']
        rel_score = 0
        for kw in crypto_keywords:
            if kw.lower() in title.lower():
                rel_score += 1
        
        usd_ccy = currency in ('USD', 'US')
        if rel_score >= 2 and usd_ccy:
            analysis['crypto_relevance'] = '★★★★★ 核心数据，直接影响BTC/DXY联动'
            analysis['direction_bias'] = 'bullish' if analysis.get('direction_bias') == 'neutral' else analysis['direction_bias']
        elif rel_score >= 1:
            analysis['crypto_relevance'] = '★★★☆☆ 间接相关，可能影响风险偏好'
        else:
            analysis['crypto_relevance'] = '★☆☆☆☆ 对加密市场影响较小'
        
        # 趋势笔记
        if previous and forecast:
            analysis['trend_note'] = f'前值{previous} → 预测{forecast}'
        elif previous:
            analysis['trend_note'] = f'前值: {previous}'
        
        ev['ai_analysis'] = analysis
    
    return events


#####################
# 主入口：全量采集+存储+分析
#####################

def run_calendar_pipeline(proxies=None, save_db=True):
    """
    采集+存储+分析完整流程
    返回: (events_by_date, error)
    """
    # Step 1: 从FF采集
    events, err = fetch_ff_calendar(proxies)
    
    # Step 2: 如果FF没数据，尝试Investing备用
    if not events:
        events2, err2 = fetch_investing_calendar(proxies)
        if events2:
            events = events2
            print(f'[日历] 备用源Investing: {len(events2)}条')
    
    if not events:
        return [], err or '无数据'
    
    # Step 3: AI分析
    events = analyze_events(events)
    
    # Step 4: 存入SQLite
    if save_db:
        try:
            conn = init_db()
            added, updated = save_to_db(conn, events)
            print(f'[日历-SQLite] 新增{added} 更新{updated} 条')
            # 也加载近期历史数据
            hist = load_historical_events(conn)
            if hist:
                events.extend(hist)
            conn.close()
        except Exception as e:
            print(f'[日历-SQLite] 存储失败: {e}')
    
    # 去重（历史+当前可能有重复）
    seen = set()
    deduped = []
    for ev in events:
        key = ev_key(ev)
        if key not in seen:
            seen.add(key)
            deduped.append(ev)
    
    print(f'[日历] 总计 {len(deduped)} 条事件 (含历史)')
    return deduped, None


def get_events_by_date(events):
    """按日期分组排序"""
    groups = {}
    for ev in events:
        d = ev.get('date', '')
        if not d:
            continue
        if d not in groups:
            groups[d] = {'weekday': ev.get('weekday',''), 'isToday': ev.get('isToday',False), 'events': []}
        groups[d]['events'].append(ev)
    return groups


if __name__ == '__main__':
    proxies = {'http': 'http://127.0.0.1:10020', 'https': 'http://127.0.0.1:10020'}
    events, err = run_calendar_pipeline(proxies)
    if err:
        print(f'Error: {err}')
    else:
        groups = get_events_by_date(events)
        dates = sorted(groups.keys())
        print(f'\n共 {len(events)} 条事件, {len(dates)} 天')
        for ds in dates:
            g = groups[ds]
            m = ' 📌今天' if g['isToday'] else ''
            print(f'\n📅 {ds} 周{g["weekday"]}{m}')
            for ev in g['events']:
                icon = '🔴' if ev['impact'] == 'high' else '🟡'
                print(f'  {ev.get("time","")} {icon} {ev.get("currency","")} {ev.get("title","")}')
                ai = ev.get('ai_analysis', {})
                if ai.get('crypto_relevance'):
                    print(f'    → {ai["crypto_relevance"]}')
                if ai.get('impact_assessment'):
                    print(f'    → {ai["impact_assessment"]}')
