"""
财经日历独立页面渲染器
生成独立的 calendar.html 页面，展示完整财经日历
功能：
- 左侧事件列表（近30天，按日期分组）
- 右侧事件详情（点击左侧事件展开）
- 每个事件的历史发布记录趋势
- AI分析
"""

import sys, json, os, sqlite3, hashlib
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE, "data", "calendar_history.db")


def load_all_events(days_back=60):
    """从SQLite加载所有事件"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT id, date, weekday, time, impact, currency, title,
               actual, previous, forecast, ai_analysis
        FROM calendar_events
        WHERE date >= date('now', ?)
        ORDER BY date DESC, time
    """, (f'-{days_back} days',))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def group_by_event_key(events):
    """按(currency, title)分组，得到每个事件的历史发布记录"""
    groups = {}
    for ev in events:
        key = f'{ev["currency"]}|{ev["title"]}'
        if key not in groups:
            groups[key] = {
                'currency': ev['currency'],
                'title': ev['title'],
                'impact': ev['impact'],
                'history': []
            }
        groups[key]['history'].append({
            'id': ev['id'],
            'date': ev['date'],
            'time': ev.get('time', ''),
            'actual': ev.get('actual', ''),
            'previous': ev.get('previous', ''),
            'forecast': ev.get('forecast', ''),
        })
    return groups


def build_event_groups(events):
    """按日期分组全部事件"""
    groups = {}
    for ev in events:
        d = ev.get('date', '')
        if not d:
            continue
        if d not in groups:
            groups[d] = {'events': []}
        groups[d]['events'].append(ev)
    return groups


def render_calendar_page(events):
    """生成独立日历HTML页面"""
    today_str = datetime.now().strftime('%Y-%m-%d')
    docs_dir = os.path.join(BASE, "docs")
    events_json = json.dumps(events, ensure_ascii=False)

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>金峰策略 · 财经日历</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=Noto+Sans+SC:wght@400;500;600;700;900&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{{margin:0;padding:0;box-sizing:border-box}}
html{{font-size:15px;-webkit-font-smoothing:antialiased;background:#0a0b0e;color:#c9d1d9;font-family:'Inter','Noto Sans SC',sans-serif}}
body{{min-height:100vh;display:flex;flex-direction:column}}
a{{color:#58a6ff;text-decoration:none}}

/* Header */
.header{{background:#0d0e12;border-bottom:1px solid #1b1d23;padding:14px 24px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100}}
.header-l{{display:flex;align-items:center;gap:10px}}
.header-logo{{width:32px;height:32px;border-radius:8px;background:linear-gradient(135deg,#ffd700,#ff8c00);display:flex;align-items:center;justify-content:center;font-weight:900;font-size:18px;color:#0a0b0e}}
.header h1{{font-size:16px;font-weight:700;color:#e1e4e8}}
.header .badge{{font-size:10px;padding:2px 6px;border-radius:4px;background:#1b1d23;color:#8b949e;margin-left:6px}}
.header-time{{font-size:11px;color:#484f58}}
.header-r{{display:flex;align-items:center;gap:12px}}
.back-btn{{padding:6px 14px;border-radius:6px;background:#121318;border:1px solid #1b1d23;color:#8b949e;font-size:12px;cursor:pointer;transition:all .2s}}
.back-btn:hover{{background:#1b1d23;color:#c9d1d9}}

/* Layout */
.layout{{display:flex;flex:1;height:calc(100vh - 57px);overflow:hidden}}

/* Left panel - events list */
.left-panel{{width:380px;min-width:380px;border-right:1px solid #1b1d23;overflow-y:auto;background:#0d0e12}}
.left-panel::-webkit-scrollbar{{width:4px}}
.left-panel::-webkit-scrollbar-thumb{{background:#1b1d23;border-radius:2px}}
.left-panel::-webkit-scrollbar-track{{background:transparent}}

.panel-header{{padding:10px 14px;border-bottom:1px solid #1b1d23;font-size:13px;font-weight:600;color:#e1e4e8;position:sticky;top:0;background:#0d0e12;z-index:10}}
.panel-header span{{font-size:10px;font-weight:400;color:#484f58;margin-left:6px}}
.panel-header .filter-row{{margin-top:6px;display:flex;gap:4px;flex-wrap:wrap}}
.filter-btn{{font-size:9px;padding:2px 8px;border-radius:12px;background:#121318;border:1px solid #1b1d23;color:#484f58;cursor:pointer;transition:all .2s}}
.filter-btn.active{{background:#1b1d23;border-color:#30363d;color:#c9d1d9}}
.filter-btn.high{{border-color:#f8514933}}
.filter-btn.high.active{{border-color:#f85149;color:#f85149}}
.filter-btn.med{{border-color:#d2992233}}
.filter-btn.med.active{{border-color:#d29922;color:#d29922}}

.cal-date-group{{padding:8px 14px}}
.cal-date-group+.cal-date-group{{border-top:1px solid #1b1d23}}
.cal-date-hdr{{font-size:11px;font-weight:600;color:#8b949e;margin-bottom:6px;letter-spacing:.3px}}
.cal-today .cal-date-hdr{{color:#ffd700}}

.cal-ev{{padding:8px 10px;margin-bottom:4px;border-radius:6px;font-size:12px;line-height:1.4;background:#121318;cursor:pointer;transition:all .2s;border-left:3px solid transparent}}
.cal-ev:hover{{background:#1b1d23}}
.cal-ev.selected{{background:#161b22;border-color:#30363d}}
.cal-ev.imp-hi{{border-left-color:#f85149}}
.cal-ev.imp-md{{border-left-color:#d29922}}
.cal-ev-header{{display:flex;align-items:center;gap:6px;flex-wrap:wrap}}
.cal-tm{{color:#484f58;font-family:monospace;font-size:10px;min-width:40px}}
.cal-ccy{{display:inline-block;padding:1px 5px;border-radius:3px;background:#1b1d23;color:#ffd700;font-size:10px;font-weight:700}}
.cal-tl{{color:#c9d1d9;flex:1;font-weight:500;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.cal-impact-badge{{font-size:9px;padding:1px 5px;border-radius:3px;font-weight:600}}
.cal-impact-badge.hi{{background:#f8514915;color:#f85149}}
.cal-impact-badge.md{{background:#d2992215;color:#d29922}}
.cal-vals{{display:flex;gap:6px;margin-top:4px;flex-wrap:wrap}}
.cal-val{{font-size:10px;padding:1px 6px;border-radius:3px}}
.cal-val.act{{color:#3fb950;background:#3fb95015}}
.cal-val.fcast{{color:#d29922;background:#d2992215}}
.cal-val.prev{{color:#8b949e;background:#8b949e15}}
.cal-date-badge{{font-size:9px;color:#484f58;margin-top:2px}}

/* Right panel - detail */
.right-panel{{flex:1;overflow-y:auto;padding:24px 32px;background:#0a0b0e}}
.right-panel::-webkit-scrollbar{{width:6px}}
.right-panel::-webkit-scrollbar-thumb{{background:#1b1d23;border-radius:3px}}
.right-panel::-webkit-scrollbar-track{{background:transparent}}
.no-selection{{display:flex;align-items:center;justify-content:center;height:100%;color:#484f58;font-size:14px;text-align:center;padding:40px}}
.no-selection p{{max-width:360px;line-height:1.8}}

/* Event Detail */
.detail-section{{margin-bottom:24px}}
.detail-hdr{{display:flex;align-items:center;gap:8px;margin-bottom:16px}}
.detail-hdr .big-ccy{{padding:2px 8px;border-radius:4px;background:#1b1d23;color:#ffd700;font-size:16px;font-weight:700}}
.detail-hdr h2{{font-size:20px;font-weight:700;color:#e1e4e8}}
.detail-impact{{font-size:11px;padding:2px 8px;border-radius:4px;font-weight:600}}
.detail-impact.hi{{background:#f8514915;color:#f85149}}
.detail-impact.md{{background:#d2992215;color:#d29922}}
.detail-date{{font-size:12px;color:#484f58;margin-top:4px}}

/* Data card */
.data-card{{background:#0d0e12;border:1px solid #1b1d23;border-radius:8px;padding:16px;margin-bottom:16px}}
.data-card h3{{font-size:13px;font-weight:600;color:#e1e4e8;margin-bottom:12px;display:flex;align-items:center;gap:6px}}
.data-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}}
.data-item{{text-align:center;padding:8px;border-radius:6px;background:#121318}}
.data-item .lbl{{font-size:10px;color:#484f58;margin-bottom:4px}}
.data-item .val{{font-size:22px;font-weight:700}}
.data-item .val.act{{color:#3fb950}}
.data-item .val.fcast{{color:#d29922}}
.data-item .val.prev{{color:#8b949e}}

/* Historical bar chart */
.hist-chart{{margin:16px 0 4px}}
.hist-row{{display:flex;align-items:center;gap:8px;margin:6px 0}}
.hist-lbl{{width:28px;font-size:10px;color:#8b949e;text-align:right}}
.hist-bar-wrap{{flex:1;height:10px;background:#1b1d23;border-radius:5px;overflow:hidden}}
.hist-bar{{height:100%;border-radius:5px;transition:width .6s ease}}
.hist-bar.prev{{background:#8b949e}}
.hist-bar.fcast{{background:#d29922}}
.hist-bar.act{{background:#3fb950}}
.hist-val{{width:60px;text-align:right;font-size:11px;font-weight:600;color:#c9d1d9;font-family:monospace}}

/* History timeline */
.history-table{{width:100%;border-collapse:collapse;font-size:12px}}
.history-table th{{text-align:left;padding:8px 10px;border-bottom:1px solid #1b1d23;color:#484f58;font-weight:600;font-size:10px;text-transform:uppercase;letter-spacing:.5px}}
.history-table td{{padding:8px 10px;border-bottom:1px solid #121318;color:#8b949e}}
.history-table tr:hover td{{background:#121318}}
.history-table .val{{font-weight:600}}
.history-table .val.up{{color:#3fb950}}
.history-table .val.down{{color:#f85149}}

/* AI Analysis */
.ai-card{{border:1px solid #1b1d23;border-radius:8px;padding:16px;margin-bottom:16px}}
.ai-card h3{{font-size:13px;font-weight:600;color:#58a6ff;margin-bottom:10px;display:flex;align-items:center;gap:6px}}
.ai-grid{{display:grid;gap:8px}}
.ai-row{{padding:6px 0;border-bottom:1px solid #121318;display:flex;gap:8px;font-size:12px;line-height:1.6}}
.ai-row:last-child{{border-bottom:none}}
.ai-lbl{{color:#8b949e;min-width:70px;font-weight:500}}
.ai-val{{color:#c9d1d9;flex:1}}

/* Empty state */
.empty-state{{text-align:center;padding:40px 20px;color:#484f58;font-size:13px}}

/* Mobile */
@media(max-width:768px){{
.layout{{flex-direction:column;height:auto}}
.left-panel{{width:100%;min-width:100%;max-height:50vh;border-right:none;border-bottom:1px solid #1b1d23}}
.right-panel{{padding:16px}}
.detail-hdr h2{{font-size:17px}}
.data-grid{{grid-template-columns:repeat(3,1fr);gap:8px}}
.hist-lbl{{width:24px}}
.hist-val{{width:50px}}
}}

/* Loading */
.loading-dots::after{{content:'';animation:dots 1.5s infinite}}
@keyframes dots{{0%{{content:'.'}}33%{{content:'..'}}66%{{content:'...'}}}}
</style>
</head>
<body>
<div class="header">
  <div class="header-l">
    <div class="header-logo">金</div>
    <h1>财经日历 <span class="badge">v1.0</span></h1>
    <span class="header-time" id="header-time">更新于 —</span>
  </div>
  <div class="header-r">
    <a href="./" class="back-btn">← 返回快讯</a>
  </div>
</div>

<div class="layout">
  <!-- Left: Event List -->
  <div class="left-panel" id="left-panel">
    <div class="panel-header">
      全部事件 <span id="ev-count"></span>
      <div class="filter-row">
        <button class="filter-btn active" onclick="setFilter('ALL')">全部</button>
        <button class="filter-btn high" onclick="setFilter('high')">🔴 高影响</button>
        <button class="filter-btn med" onclick="setFilter('medium')">🟡 中影响</button>
      </div>
    </div>
    <div id="event-list"></div>
  </div>

  <!-- Right: Detail -->
  <div class="right-panel" id="right-panel">
    <div class="no-selection">
      <p>📅 从左侧选择一条经济事件<br>查看详细数据、AI分析及历史趋势</p>
    </div>
  </div>
</div>

<script>
var EVENTS_DATA = ''' + events_json + ''';

// 经济事件中英文翻译
var TITLE_CN = {
  'Federal Funds Rate':'联邦基金利率',
  'Official Bank Rate':'官方银行利率',
  'Official Cash Rate':'官方现金利率',
  'Cash Rate':'现金利率',
  'Overnight Rate':'隔夜利率',
  'Main Refinancing Rate':'主要再融资利率',
  'SNB Policy Rate':'瑞士央行政策利率',
  'BOJ Policy Rate':'日本央行政策利率',
  'MPC Official Bank Rate Votes':'MPC利率投票比',
  'FOMC Statement':'FOMC声明',
  'FOMC Meeting Minutes':'FOMC会议纪要',
  'FOMC Economic Projections':'FOMC经济预测',
  'FOMC Press Conference':'FOMC新闻发布会',
  'Monetary Policy Statement':'货币政策声明',
  'Monetary Policy Summary':'货币政策摘要',
  'Monetary Policy Meeting Minutes':'货币政策会议纪要',
  'Monetary Policy Report Hearings':'货币政策报告听证会',
  'BOC Rate Statement':'加拿大央行利率声明',
  'BOC Monetary Policy Report':'加拿大央行货币政策报告',
  'BOC Press Conference':'加拿大央行新闻发布会',
  'RBA Rate Statement':'澳洲联储利率声明',
  'RBA Monetary Policy Statement':'澳洲联储货币政策声明',
  'RBA Press Conference':'澳洲联储新闻发布会',
  'RBNZ Rate Statement':'新西兰联储利率声明',
  'RBNZ Monetary Policy Statement':'新西兰联储货币政策声明',
  'RBNZ Press Conference':'新西兰联储新闻发布会',
  'SNB Monetary Policy Assessment':'瑞士央行货币政策评估',
  'SNB Press Conference':'瑞士央行新闻发布会',
  'ECB Press Conference':'欧央行新闻发布会',
  'ECB Financial Stability Review':'欧央行金融稳定评估报告',
  'BOE Monetary Policy Report':'英央行货币政策报告',
  'BOJ Outlook Report':'日本央行经济展望报告',
  'BOJ Press Conference':'日本央行新闻发布会',
  'Jackson Hole Symposium':'杰克逊霍尔全球央行年会',
  'OPEC Meetings':'OPEC会议',
  'OPEC-JMMC Meetings':'OPEC联合部长级监督委员会会议',
  'Fed Chair Nomination Vote':'美联储主席提名投票',
  'CPI m/m':'CPI月率','CPI y/y':'CPI年率','CPI q/q':'CPI季率',
  'CPI Flash Estimate y/y':'CPI初值年率',
  'Core CPI m/m':'核心CPI月率','Core CPI y/y':'核心CPI年率',
  'Core CPI Flash Estimate y/y':'核心CPI初值年率',
  'Core PCE Price Index m/m':'核心PCE物价指数月率',
  'Core PPI m/m':'核心PPI月率','Core Retail Sales m/m':'核心零售销售月率',
  'PPI m/m':'PPI月率','PPI y/y':'PPI年率',
  'Common CPI y/y':'普通CPI年率','Median CPI y/y':'中值CPI年率',
  'Trimmed CPI y/y':'截尾CPI年率','Trimmed Mean CPI m/m':'截尾均值CPI月率',
  'Tokyo Core CPI y/y':'东京核心CPI年率',
  'Prelim UoM Inflation Expectations':'密歇根大学通胀预期初值',
  'Revised UoM Inflation Expectations':'密歇根大学通胀预期终值',
  'Inflation Expectations q/q':'通胀预期季率',
  'German Prelim CPI m/m':'德国CPI初值月率',
  'Non-Farm Employment Change':'非农就业人数变化',
  'ADP Non-Farm Employment Change':'ADP非农就业人数变化',
  'Employment Change':'就业人数变化',
  'Employment Change q/q':'就业人数变化季率',
  'Unemployment Rate':'失业率',
  'Unemployment Claims':'初请失业金人数',
  'Claimant Count Change':'申领失业金人数变化',
  'Average Earnings Index 3m/y':'平均薪资指数3月/年',
  'Average Hourly Earnings m/m':'平均时薪月率',
  'Employment Cost Index q/q':'就业成本指数季率',
  'JOLTS Job Openings':'JOLTS职位空缺',
  'Prelim Benchmark Payrolls Revision':'基准薪资修正初值',
  'Advance GDP q/q':'GDP初值季率',
  'Advance GDP Price Index q/q':'GDP初值物价指数季率',
  'Prelim GDP q/q':'GDP修正值季率',
  'Prelim GDP Price Index q/q':'GDP修正值物价指数季率',
  'Final GDP q/q':'GDP终值季率',
  'Final GDP Price Index q/q':'GDP终值物价指数季率',
  'GDP m/m':'GDP月率','GDP q/q':'GDP季率',
  'German Prelim GDP q/q':'德国GDP初值季率',
  'Flash Manufacturing PMI':'制造业PMI初值','Flash Services PMI':'服务业PMI初值',
  'French Flash Manufacturing PMI':'法国制造业PMI初值',
  'French Flash Services PMI':'法国服务业PMI初值',
  'German Flash Manufacturing PMI':'德国制造业PMI初值',
  'German Flash Services PMI':'德国服务业PMI初值',
  'ISM Manufacturing PMI':'ISM制造业PMI',
  'ISM Manufacturing Prices':'ISM制造业物价指数',
  'ISM Services PMI':'ISM服务业PMI',
  'Philly Fed Manufacturing Index':'费城联储制造业指数',
  'Retail Sales m/m':'零售销售月率',
  'CB Consumer Confidence':'谘商会消费者信心指数',
  'Prelim UoM Consumer Sentiment':'密歇根大学消费者信心初值',
  'Revised UoM Consumer Sentiment':'密歇根大学消费者信心终值',
  'New Home Sales':'新屋销售',
  'Pending Home Sales m/m':'成屋签约销售月率',
  'Annual Budget Release':'年度预算发布',
  'Ivey PMI':'Ivey采购经理人指数',
  'Wage Price Index q/q':'薪资价格指数季率',
  'FOMC Member Powell Speaks':'FOMC成员鲍威尔讲话',
  'Fed Chairman Warsh Speaks':'美联储主席沃什讲话',
  'Fed Chairman Warsh Testifies':'美联储主席沃什证词',
  'President Trump Speaks':'特朗普总统讲话',
  'BOC Gov Macklem Speaks':'加拿大央行行长麦克勒姆讲话',
  'BOE Gov Bailey Speaks':'英央行行长贝利讲话',
  'BOJ Gov Ueda Speaks':'日本央行行长植田和男讲话',
  'ECB President Lagarde Speaks':'欧央行行长拉加德讲话',
  'RBA Gov Bullock Speaks':'澳洲联储主席布洛克讲话',
  'RBNZ Gov Breman Speaks':'新西兰联储主席布雷曼讲话',
  'SNB Chairman Schlegel Speaks':'瑞士央行主席施莱格尔讲话',
  'Treasury Sec Bessent Speaks':'财政部长贝森特讲话',
  'Fed Chair Nomination Vote':'美联储主席提名投票',
  'Annual Budget Release':'年度预算发布',
  'Jackson Hole Symposium':'杰克逊霍尔全球央行年会',
};

function t(en){ return TITLE_CN[en] || en; }

var currentFilter = 'ALL';
var currentFilter = 'ALL';
var selectedEvKey = null;

// ==== Filter ====
function setFilter(f){
  currentFilter=f;
  document.querySelectorAll('.filter-btn').forEach(function(b){
    b.classList.toggle('active',b.textContent.includes(f==='high'?'高':f==='medium'?'中':'全部'));
  });
  renderEventList();
}

// ==== Render Event List ====
function renderEventList(){
  var el=$('event-list');
  var filtered=EVENTS_DATA.filter(function(ev){
    if(currentFilter==='ALL')return true;
    return ev.impact===currentFilter;
  });
  
  // Group by date
  var groups={};
  filtered.forEach(function(ev){
    var d=ev.date;
    if(!groups[d])groups[d]={events:[]};
    groups[d].events.push(ev);
  });
  
  var dates=Object.keys(groups).sort().reverse();
  var html='';
  dates.forEach(function(ds){
    var tc=ds===todayStr?' cal-today':'';
    html+='<div class="cal-date-group'+tc+'">';
    html+='<div class="cal-date-hdr">'+esc(ds)+'</div>';
    groups[ds].events.forEach(function(ev){
      var key=ev.currency+'|'+ev.title;
      var sel=key===selectedEvKey?' selected':'';
      var ic=ev.impact==='high'?'hi':'md';
      html+='<div class="cal-ev imp-'+ic+sel+'" data-key="'+esc(key)+'" onclick="selectEvent(this,this.dataset.key)">';
      html+='<div class="cal-ev-header">';
      html+='<span class="cal-tm">'+esc(ev.time||'--:--')+'</span>';
      html+='<span class="cal-ccy">'+esc(ev.currency)+'</span>';
      html+='<span class="cal-tl">'+t(ev.title)+'</span>';
      html+='<span class="cal-impact-badge '+ic+'">'+(ev.impact==='high'?'🔴 高':'🟡 中')+'</span>';
      html+='</div>';
      var vals='';
      if(ev.actual)vals+='<span class="cal-val act">实: '+esc(ev.actual)+'</span>';
      if(ev.forecast)vals+='<span class="cal-val fcast">预: '+esc(ev.forecast)+'</span>';
      if(ev.previous)vals+='<span class="cal-val prev">前: '+esc(ev.previous)+'</span>';
      if(vals)html+='<div class="cal-vals">'+vals+'</div>';
      html+='</div>';
    });
    html+='</div>';
  });
  
  if(!html)html='<div class="empty-state">暂无匹配事件</div>';
  el.innerHTML=html;
  $('ev-count').textContent='('+filtered.length+'条)';
}

// ==== Select Event & Show Detail ====
function selectEvent(el, key){
  document.querySelectorAll('.cal-ev.selected').forEach(function(b){b.classList.remove('selected')});
  el.classList.add('selected');
  selectedEvKey=key;
  showDetail(key);
}

function showDetail(key){
  var rp=$('right-panel');
  // Get all events with this key
  var ccy=key.split('|')[0];
  var title=key.split('|')[1];
  // Also get events with same title (possibly different currency for comparison)
  var related=EVENTS_DATA.filter(function(ev){
    return ev.title===title;
  });
  // Group history by currency
  var histByCcy={};
  related.forEach(function(ev){
    var c=ev.currency;
    if(!histByCcy[c])histByCcy[c]=[];
    histByCcy[c].push(ev);
  });
  
  // Latest event (the one that was clicked or first)
  var latest = related.filter(function(ev){return ev.currency===ccy})[0] || related[0];
  if(!latest){rp.innerHTML='<div class="empty-state">无数据</div>';return}
  
  var imp=latest.impact==='high'?'hi':'md';
  var ai=latest.ai_analysis||{};
  var ic=latest.impact==='high'?'🔴 高':'🟡 中';
  
  var html='';
  // Header
  html+='<div class="detail-section">';
  html+='<div class="detail-hdr">';
  html+='<span class="big-ccy">'+esc(latest.currency)+'</span>';
  html+='<h2>'+t(latest.title)+'</h2>';
  html+='<span class="detail-impact '+imp+'">'+ic+'</span>';
  html+='</div>';
  html+='<div class="detail-date">最新数据: '+esc(latest.date)+' '+esc(latest.time||'')+'</div>';
  html+='</div>';
  
  // Data Card
  html+='<div class="data-card"><h3>📊 当期数据</h3><div class="data-grid">';
  html+='<div class="data-item"><div class="lbl">实际值</div><div class="val act">'+(latest.actual||'—')+'</div></div>';
  html+='<div class="data-item"><div class="lbl">预测值</div><div class="val fcast">'+(latest.forecast||'—')+'</div></div>';
  html+='<div class="data-item"><div class="lbl">前值</div><div class="val prev">'+(latest.previous||'—')+'</div></div>';
  html+='</div>';
  
  // Historical bars
  if(latest.actual&&latest.forecast){
    try{
      var maxVal=0;
      ['actual','forecast','previous'].forEach(function(k){
        var v=parseFloat(String(latest[k]||'0').replace(/[^0-9.]/g,''));
        if(v>maxVal)maxVal=v;
      });
      if(maxVal>0){
        html+='<div class="hist-chart">';
        ['previous','forecast','actual'].forEach(function(k){
          var lbl={previous:'前',forecast:'预',actual:'实'}[k];
          var v=parseFloat(String(latest[k]||'0').replace(/[^0-9.]/g,''));
          var pct=(v/maxVal*80+5);
          html+='<div class="hist-row"><span class="hist-lbl">'+lbl+'</span><div class="hist-bar-wrap"><div class="hist-bar '+k+'" style="width:'+pct+'%"></div></div><span class="hist-val">'+(latest[k]||'—')+'</span></div>';
        });
        html+='</div>';
      }
    }catch(e){}
  }
  html+='</div>';
  
  // AI Analysis
  if(ai.impact_assessment||ai.crypto_relevance||ai.trend_note){
    html+='<div class="ai-card"><h3>🤖 AI 分析</h3><div class="ai-grid">';
    if(ai.trend_note)html+='<div class="ai-row"><span class="ai-lbl">趋势</span><span class="ai-val">'+esc(ai.trend_note)+'</span></div>';
    if(ai.impact_assessment)html+='<div class="ai-row"><span class="ai-lbl">影响评估</span><span class="ai-val">'+esc(ai.impact_assessment)+'</span></div>';
    if(ai.crypto_relevance)html+='<div class="ai-row"><span class="ai-lbl">加密关联</span><span class="ai-val">'+esc(ai.crypto_relevance)+'</span></div>';
    html+='</div></div>';
  }
  
  // Historical timeline: same title across all dates
  var sortedHist = related.slice().sort(function(a,b){return a.date.localeCompare(b.date)||a.time.localeCompare(b.time)});
  if(sortedHist.length>1){
    html+='<div class="data-card"><h3>📈 历史发布记录 ('+sortedHist.length+'次)</h3>';
    html+='<table class="history-table"><thead><tr><th>日期</th><th>币种</th><th>实际</th><th>预测</th><th>前值</th><th>偏差</th></tr></thead><tbody>';
    sortedHist.forEach(function(ev){
      var actualVal=ev.actual||'—';
      var forecastVal=ev.forecast||'—';
      var prevVal=ev.previous||'—';
      var devHtml='<span class="val" style="color:#484f58">—</span>';
      if(ev.actual&&ev.forecast){
        try{
          var a=parseFloat(String(ev.actual).replace(/[^0-9.-]/g,''));
          var f=parseFloat(String(ev.forecast).replace(/[^0-9.-]/g,''));
          if(f!==0){
            var d=((a-f)/Math.abs(f)*100).toFixed(1);
            devHtml='<span class="val '+(d>0?'up':'down')+'">'+(d>0?'+':'')+d+'%</span>';
          }
        }catch(e){}
      }
      html+='<tr><td>'+esc(ev.date)+'</td><td>'+esc(ev.currency)+'</td>';
      html+='<td class="val">'+actualVal+'</td><td>'+forecastVal+'</td><td>'+prevVal+'</td>';
      html+='<td>'+devHtml+'</td></tr>';
    });
    html+='</tbody></table></div>';
  }
  
  rp.innerHTML=html;
}

// ==== Utility ====
function $(id){return document.getElementById(id)}
function esc(s){var d=document.createElement('div');d.textContent=s;return d.innerHTML}

var todayStr=__TODAY_Q__2026-07-11__TODAY_Q__;

// Init
renderEventList();
$('header-time').textContent='🕐 更新于 ' + new Date().toLocaleString('zh-CN',{hour:'2-digit',minute:'2-digit'});
</script>
</body>
</html>'''

    html = html.replace("__TODAY__", today_str)
    html = html.replace("__TODAY_Q__", "'")
    path = os.path.join(docs_dir, "calendar.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f'✅ 日历独立页面已生成: {path} ({len(html)//1024}KB)')
    return html


if __name__ == '__main__':
    from calendar_fetcher_v2 import run_calendar_pipeline
    proxy = 'http://127.0.0.1:10020'
    events, err = run_calendar_pipeline(proxies={'http': proxy, 'https': proxy}, save_db=True)
    if err:
        print(f'采集错误: {err}')
    else:
        print(f'采集到 {len(events)} 条事件')
    
    # Combine with all DB data for the page
    all_events = load_all_events()
    print(f'DB中共 {len(all_events)} 条记录')
    
    render_calendar_page(all_events)
