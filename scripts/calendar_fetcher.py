"""
Forex Factory 财经日历采集器
从Forex Factory日历页面提取经济事件数据
"""
import sys, json, re, requests
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

def fetch_forex_factory_calendar(proxies=None, days_lookahead=14):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }
    url = 'https://www.forexfactory.com/calendar'

    try:
        resp = requests.get(url, headers=headers, proxies=proxies, timeout=15)
        if resp.status_code != 200:
            return [], f'FF返回{resp.status_code}'
    except Exception as e:
        return [], f'请求失败: {e}'

    text = resp.text

    # Extract the days array from calendarComponentStates[1]  
    idx = text.find('days: [')
    if idx < 0:
        return [], '未找到日历数据'

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
        return [], f'json5解析失败: {e}'

    if not days:
        return [], '无数据'

    now = datetime.now()
    today_ts = int(datetime(now.year, now.month, now.day).timestamp())
    cutoff_ts = today_ts + days_lookahead * 86400

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

    return events, None  # (events, error_or_none)


def build_calendar_html(events):
    if not events:
        return '<div class="cal-empty">本周暂无重要经济数据</div>'

    date_groups = {}
    for ev in events:
        d = ev['date']
        if d not in date_groups:
            date_groups[d] = {'weekday': ev['weekday'], 'isToday': ev['isToday'], 'events': []}
        date_groups[d]['events'].append(ev)

    html = ''
    sorted_dates = sorted(date_groups.keys())

    for date_str in sorted_dates:
        g = date_groups[date_str]
        today_cls = ' cal-today' if g['isToday'] else ''
        html += f'<div class="cal-date-group{today_cls}">'
        html += f'<div class="cal-date-hdr">{date_str} 周{g["weekday"]}</div>'
        for ev in g['events']:
            imp_cls = 'hi' if ev['impact'] == 'high' else 'md'
            html += f'<div class="cal-ev imp-{imp_cls}">'
            html += f'<span class="cal-tm">{ev["time"]}</span>'
            html += f'<span class="cal-ccy">{ev["currency"]}</span>'
            html += f'<span class="cal-tl">{ev["title"]}</span>'
            det = []
            if ev['actual']: det.append(f'实: {ev["actual"]}')
            if ev['previous']: det.append(f'前: {ev["previous"]}')
            if ev['forecast']: det.append(f'预: {ev["forecast"]}')
            if det:
                html += f'<div class="cal-det">{" | ".join(det)}</div>'
            html += '</div>'
        html += '</div>'

    return html


if __name__ == '__main__':
    proxies = {'http': 'http://127.0.0.1:10020', 'https': 'http://127.0.0.1:10020'}
    evts, err = fetch_forex_factory_calendar(proxies)
    if err:
        print(f'Error: {err}')
    else:
        print(f'共{len(evts)}条事件:')
        for ev in evts:
            m = '🔴' if ev['impact'] == 'high' else '🟡'
            print(f'  {ev["date"]} {ev["time"]} {m} {ev["currency"]} {ev["title"]}')
            det = '/'.join(x for x in [ev['actual'], ev['previous'], ev['forecast']] if x)
            if det:
                print(f'    {det}')
