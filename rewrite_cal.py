import re

with open('docs/calendar.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Extract DATA JSON array
data_match = re.search(r'var EVENTS_DATA = (\[.+\]);', content, re.DOTALL)
events_json = data_match.group(1)

# Find TITLE_CN and t() section
ts = content.index('var TITLE_CN =')
te2 = content.index('function setFilter', ts)
title_cn_section = content[ts:te2]

print(f"DATA length: {len(events_json)}")
print(f"TITLE_CN section: {len(title_cn_section)} chars")

# New calendar grid CSS
cal_grid_css = """
/* Calendar Grid */
.cal-grid-wrap{background:#0d0e12;border-radius:8px;padding:12px 16px;margin:16px 24px 0;border:1px solid #1b1d23}
.cal-grid-nav{display:flex;justify-content:space-between;align-items:center;padding:4px 0 8px;border-bottom:1px solid #1b1d23;margin-bottom:8px}
.cal-nav-btn{background:#121318;border:1px solid #30363d;color:#8b949e;border-radius:4px;padding:4px 12px;cursor:pointer;font-size:12px;transition:all .2s}
.cal-nav-btn:hover{background:#1b1d23;color:#e6edf3}
.cal-nav-title{font-size:14px;font-weight:700;color:#e6edf3}
.cal-grid-dows{display:grid;grid-template-columns:repeat(7,1fr);text-align:center;font-size:11px;color:#484f58;margin-bottom:4px}
.cal-gdow{padding:3px 0}
.cal-grid-body{display:grid;grid-template-columns:repeat(7,1fr);gap:2px}
.cal-gcell{background:#121318;border-radius:4px;text-align:center;padding:5px 0;cursor:pointer;position:relative;min-height:36px;transition:all .15s}
.cal-gcell:hover{background:#1b1d23}
.cal-gtoday{background:#1f3a3f!important;border:1px solid #3fb950}
.cal-gselected{background:#2a2d33!important;border:1px solid #58a6ff}
.cal-ghasevent{background:#161b22}
.cal-gdaynum{display:block;font-size:13px;color:#8b949e;font-weight:500}
.cal-gtoday .cal-gdaynum{color:#3fb950;font-weight:700}
.cal-gempty{background:transparent!important;cursor:default;min-height:36px}
.cal-gdot{display:flex;justify-content:center;gap:2px;margin-top:2px}
.cal-gdot-hi{width:5px;height:5px;border-radius:50%;background:#f85149;display:inline-block}
.cal-gdot-md{width:5px;height:5px;border-radius:50%;background:#d29922;display:inline-block}
.cal-sel-section{margin:12px 24px 24px}
.cal-sel-header{font-size:13px;font-weight:600;color:#e1e4e8;padding:8px 0;border-bottom:1px solid #1b1d23;margin-bottom:8px;display:flex;justify-content:space-between;align-items:center}
.cal-sel-count{font-size:11px;color:#484f58;font-weight:400}
.cal-sel-empty{text-align:center;color:#484f58;padding:20px 0;font-size:12px}
.cal-ev-detail{display:none;padding:8px;margin:4px 0;background:#0d0e12;border-radius:6px}
.cal-ev.expanded .cal-ev-detail{display:block}
@media(max-width:768px){
.cal-grid-wrap{margin:12px 12px 0;padding:8px 10px}
.cal-sel-section{margin:12px}
.cal-gcell{min-height:30px;padding:3px 0}
.cal-gdaynum{font-size:11px}
}
"""

# New body HTML (delete left/right layout, replace with single column)
new_body = """
<body>
<div class="header">
  <div class="header-l">
    <div class="header-logo">金</div>
    <h1>财经日历 <span class="badge">v2.0</span></h1>
    <span class="header-time" id="header-time">更新于 —</span>
  </div>
  <div class="header-r">
    <a href="./" class="back-btn">← 返回快讯</a>
  </div>
</div>

<div class="cal-grid-wrap" id="calendar-grid"></div>
<div class="cal-sel-section" id="cal-events"></div>

"""

# New JS (replaces existing render + event logic)
new_js = f"""
var EVENTS_DATA = {events_json};

{title_cn_section}

function t(en){{
  if(TITLE_CN[en])return TITLE_CN[en];
  return en;
}}

function esc(s){{
  if(!s)return'';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}}

// Render month calendar
var _calYear, _calMonth, _calSelected;
function renderCalendar(){{
  // Filter active events (today or past with actual data, future events)
  var cd = EVENTS_DATA.filter(function(ev){{ return ev.date && ev.time; }});

  // Group by date
  var groups = {{}};
  cd.forEach(function(ev){{
    var d = ev.date;
    if(!groups[d]) groups[d] = {{events:[]}};
    groups[d].events.push(ev);
  }});

  // Determine focus month from today or earliest
  var todayStr = new Date().toISOString().slice(0,10);
  var sortedDates = Object.keys(groups).sort();
  var focus = sortedDates.indexOf(todayStr) >= 0 ? todayStr : sortedDates[0];
  if(!focus) {{ document.getElementById('calendar-grid').innerHTML = '<div class="empty-state">暂无数据</div>'; return; }}
  var parts = focus.split('-');
  if(!_calYear) {{ _calYear = parseInt(parts[0]); _calMonth = parseInt(parts[1]); }}
  if(!_calSelected) _calSelected = todayStr;

  var curYear = _calYear, curMonth = _calMonth;

  // Calendar grid
  var monthNames = ['一月','二月','三月','四月','五月','六月','七月','八月','九月','十月','十一月','十二月'];
  var firstDay = new Date(curYear, curMonth-1, 1);
  var lastDay = new Date(curYear, curMonth, 0);
  var totalDays = lastDay.getDate();
  var startWeekday = firstDay.getDay();

  var html = '<div class="cal-grid-nav">' +
    '<button class="cal-nav-btn" onclick="prevMonth()">◀</button>' +
    '<span class="cal-nav-title">'+monthNames[curMonth-1]+' '+curYear+'</span>' +
    '<button class="cal-nav-btn" onclick="nextMonth()">▶</button>' +
    '</div>';

  var dowNames = ['日','一','二','三','四','五','六'];
  html += '<div class="cal-grid-dows">';
  for(var wi=0;wi<7;wi++) html += '<span class="cal-gdow">'+dowNames[wi]+'</span>';
  html += '</div>';

  html += '<div class="cal-grid-body">';
  for(var ei=0;ei<startWeekday;ei++) html += '<div class="cal-gcell cal-gempty"></div>';

  for(var di=1;di<=totalDays;di++){{
    var dateStr = curYear+'-'+(curMonth<10?'0':'')+curMonth+'-'+(di<10?'0':'')+di;
    var g = groups[dateStr];
    var evCount = g ? g.events.length : 0;
    var hiCount = g ? g.events.filter(function(e){{return e.impact==='high'}}).length : 0;
    var isToday = dateStr === todayStr ? ' cal-gtoday' : '';
    var hasEv = evCount > 0 ? ' cal-ghasevent' : '';
    var sel = dateStr === _calSelected ? ' cal-gselected' : '';
    html += '<div class="cal-gcell'+isToday+hasEv+sel+'" onclick="selectDate(\''+dateStr+'\')">';
    html += '<span class="cal-gdaynum">'+di+'</span>';
    if(evCount > 0){{
      html += '<span class="cal-gdot">';
      for(var h=0;h<hiCount && h<3;h++) html += '<span class="cal-gdot-hi"></span>';
      for(var m=0;m<evCount-hiCount && m<3;m++) html += '<span class="cal-gdot-md"></span>';
      html += '</span>';
    }}
    html += '</div>';
  }}
  html += '</div>';

  document.getElementById('calendar-grid').innerHTML = html;
  renderEventsForDate(_calSelected, groups);
}}

function renderEventsForDate(dateStr, groups){{
  var el = document.getElementById('cal-events');
  var g = groups ? groups[dateStr] : null;
  if(!groups){{
    // rebuild groups
    var cd = EVENTS_DATA.filter(function(ev){{return ev.date && ev.time;}});
    var gtmp = {{}};
    cd.forEach(function(ev){{if(!gtmp[ev.date])gtmp[ev.date]={{events:[]}};gtmp[ev.date].events.push(ev);}});
    g = gtmp[dateStr];
  }}
  if(!g || !g.events.length){{
    el.innerHTML = '<div class="cal-sel-header">'+esc(dateStr)+'<span class="cal-sel-count">0条事件</span></div><div class="cal-sel-empty">所选日期暂无事件</div>';
    return;
  }}
  var count = g.events.length;
  var hiCount = g.events.filter(function(e){{return e.impact==='high'}}).length;
  var html = '<div class="cal-sel-header">'+esc(dateStr)+'<span class="cal-sel-count">'+count+'条事件（高影响'+hiCount+'条）</span></div>';
  g.events.forEach(function(ev){{
    html += renderCalEvent(ev);
  }});
  el.innerHTML = html;
}}

function renderCalEvent(ev){{
  var ic = ev.impact === 'high' ? 'hi' : 'md';
  var ai = ev.ai_analysis || {{}};
  var html = '<div class="cal-ev imp-'+ic+'" onclick="toggleDetail(this,\''+escapeKey(ev.ev_key)+'\')">';
  html += '<div class="cal-ev-header">';
  html += '<span class="cal-tm">'+esc(ev.time||'--:--')+'</span>';
  html += '<span class="cal-ccy">'+esc(ev.currency)+'</span>';
  html += '<span class="cal-tl">'+esc(t(ev.title))+'</span>';
  if(ev.impact==='high') html += '<span class="cal-impact-badge" style="background:#f8514915;color:#f85149">🔴 高</span>';
  html += '</div>';
  var vals = '';
  if(ev.actual) vals += '<span class="cal-val act">实: '+esc(ev.actual)+'</span>';
  if(ev.forecast) vals += '<span class="cal-val fcast">预: '+esc(ev.forecast)+'</span>';
  if(ev.previous) vals += '<span class="cal-val prev">前: '+esc(ev.previous)+'</span>';
  if(vals) html += '<div class="cal-vals">'+vals+'</div>';
  html += '<div class="cal-ev-detail">';
  // AI analysis
  if(ai.impact_assessment || ai.crypto_relevance || ai.trend_note){{
    html += '<div class="ai-card"><h3>🤖 AI 分析</h3><div class="ai-grid">';
    if(ai.trend_note) html += '<div class="ai-row"><span class="ai-lbl">趋势：</span><span class="ai-val">'+esc(ai.trend_note)+'</span></div>';
    if(ai.impact_assessment) html += '<div class="ai-row"><span class="ai-lbl">影响：</span><span class="ai-val">'+esc(ai.impact_assessment)+'</span></div>';
    if(ai.crypto_relevance) html += '<div class="ai-row"><span class="ai-lbl">加密关联：</span><span class="ai-val">'+esc(ai.crypto_relevance)+'</span></div>';
    var db = ai.direction_bias;
    if(db && db!=='neutral'){{
      html += '<div class="ai-row"><span class="ai-lbl">倾向：</span><span class="ai-val">'+(db==='bullish'?'📈 偏多':'📉 偏空')+'</span></div>';
    }}
    html += '</div></div>';
  }}
  // Historical comparison
  if(ev.actual && ev.forecast){{
    var prevW = ev.previous ? Math.min(100, Math.abs(parseFloat(ev.previous))/Math.abs(parseFloat(ev.forecast))*50+25) : 25;
    var fcastW = 50;
    var actW = Math.min(100, Math.abs(parseFloat(ev.actual))/Math.abs(parseFloat(ev.forecast))*50+25);
    html += '<div class="ai-card"><h3>📊 数据对比</h3><div class="hist-chart">';
    html += '<div class="hist-row"><span class="hist-lbl">前</span><div class="hist-bar-wrap"><div class="hist-bar prev" style="width:'+prevW+'%"></div></div><span class="hist-val">'+esc(ev.previous||'-')+'</span></div>';
    html += '<div class="hist-row"><span class="hist-lbl">预</span><div class="hist-bar-wrap"><div class="hist-bar fcast" style="width:50%"></div></div><span class="hist-val">'+esc(ev.forecast)+'</span></div>';
    html += '<div class="hist-row"><span class="hist-lbl">实</span><div class="hist-bar-wrap"><div class="hist-bar act" style="width:'+actW+'%"></div></div><span class="hist-val">'+esc(ev.actual)+'</span></div>';
    html += '</div></div>';
  }}
  html += '</div></div>';
  return html;
}}

function escapeKey(k){{
  return String(k).replace(/'/g,"\\\\'");
}}

function toggleDetail(el, key){{
  var detail = el.querySelector('.cal-ev-detail');
  if(!detail) return;
  var expanded = detail.style.display !== 'none';
  detail.style.display = expanded ? 'none' : 'block';
  el.classList.toggle('expanded', !expanded);
}}

function selectDate(dateStr){{
  _calSelected = dateStr;
  renderCalendar();
}}

function prevMonth(){{
  if(_calMonth===1){{_calYear--;_calMonth=12;}}
  else _calMonth--;
  renderCalendar();
}}

function nextMonth(){{
  if(_calMonth===12){{_calYear++;_calMonth=1;}}
  else _calMonth++;
  renderCalendar();
}}

// Initialize
document.addEventListener('DOMContentLoaded', function(){{
  var h = document.getElementById('header-time');
  if(h && window.HEADER_TIME) h.textContent = HEADER_TIME;
  renderCalendar();
}});

function setFilter(level){{}}
"""

# Now reconstruct the file
# Part 1: up to </style>
style_end = content.index('</style>') + 8
part1 = content[:style_end]

# Insert calendar grid CSS before </style>
part1_with_grid = part1.replace('</style>', cal_grid_css + '\n</style>')

# Part 2: body HTML
# From <body> to <script> (replace the middle portion)
part2 = new_body

# Part 3: the script
part3 = '<script>\n' + new_js + '\n</script>\n'

# Part 4: </body></html>
part4 = '</body>\n</html>\n'

new_content = part1_with_grid + part2 + part3 + part4

with open('docs/calendar.html', 'w', encoding='utf-8') as f:
    f.write(new_content)

print(f"Original size: {len(content)} bytes")
print(f"New size: {len(new_content)} bytes")
print("Done!")
