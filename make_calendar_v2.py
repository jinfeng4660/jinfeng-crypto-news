import re

with open('docs/calendar.html', 'r', encoding='utf-8') as f:
    content = f.read()

# --- Extract EVENTS_DATA JSON precisely ---
data_start = content.index("var EVENTS_DATA = [") + len("var EVENTS_DATA = [")
data_end = content.index("];", data_start) + 1
events_json = content[data_start:data_end]

# --- Extract HEADER_TIME ---
ht_match = re.search(r'(var HEADER_TIME = [^;]+;)', content)
header_time = ht_match.group(1) if ht_match else 'var HEADER_TIME = "2026-07-11";'

print(f"Data length: {len(events_json)}")
print(f"Header time: {header_time}")

# --- New CSS ---
grid_css = '''
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
'''

# CSS ending with newline
grid_css = grid_css + '\n'

# --- New body HTML ---
body_html = '''<body>
<div class="header">
  <div class="header-l">
    <div class="header-logo">金</div>
    <h1>财经日历 <span class="badge">v2.0</span></h1>
    <span class="header-time" id="header-time">更新于 \u2014</span>
  </div>
  <div class="header-r">
    <a href="./" class="back-btn">\u2190 返回快讯</a>
  </div>
</div>

<div class="cal-grid-wrap" id="calendar-grid"></div>
<div class="cal-sel-section" id="cal-events"></div>
'''

# --- New JS (NO f-strings, use string concat with .format for safety) ---
js_template = '''
var EVENTS_DATA = [{data}];

var TITLE_CN = {{
  'Federal Funds Rate':'联邦基金利率', 'Official Bank Rate':'官方银行利率',
  'Official Cash Rate':'官方现金利率', 'Cash Rate':'现金利率',
  'Overnight Rate':'隔夜利率', 'Main Refinancing Rate':'主要再融资利率',
  'SNB Policy Rate':'瑞士央行政策利率', 'BOJ Policy Rate':'日本央行政策利率',
  'MPC Official Bank Rate Votes':'MPC利率投票比',
  'FOMC Statement':'FOMC声明', 'FOMC Meeting Minutes':'FOMC会议纪要',
  'FOMC Economic Projections':'FOMC经济预测', 'FOMC Press Conference':'FOMC新闻发布会',
  'Monetary Policy Statement':'货币政策声明', 'Monetary Policy Summary':'货币政策摘要',
  'Monetary Policy Meeting Minutes':'货币政策会议纪要', 'Monetary Policy Report Hearings':'货币政策报告听证会',
  'BOC Rate Statement':'加拿大央行利率声明', 'BOC Monetary Policy Report':'加拿大央行货币政策报告',
  'BOC Press Conference':'加拿大央行新闻发布会',
  'RBA Rate Statement':'澳洲联储利率声明', 'RBA Monetary Policy Statement':'澳洲联储货币政策声明',
  'RBA Press Conference':'澳洲联储新闻发布会',
  'RBNZ Rate Statement':'新西兰联储利率声明', 'RBNZ Monetary Policy Statement':'新西兰联储货币政策声明',
  'RBNZ Press Conference':'新西兰联储新闻发布会',
  'SNB Monetary Policy Assessment':'瑞士央行货币政策评估', 'SNB Press Conference':'瑞士央行新闻发布会',
  'ECB Press Conference':'欧央行新闻发布会', 'ECB Financial Stability Review':'欧央行金融稳定评估报告',
  'BOE Monetary Policy Report':'英央行货币政策报告', 'BOJ Outlook Report':'日本央行经济展望报告',
  'BOJ Press Conference':'日本央行新闻发布会',
  'Jackson Hole Symposium':'杰克逊霍尔全球央行年会',
  'OPEC Meetings':'OPEC会议', 'OPEC-JMMC Meetings':'OPEC联合部长级监督委员会会议',
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
  'Employment Change':'就业人数变化', 'Employment Change q/q':'就业人数变化季率',
  'Unemployment Rate':'失业率', 'Unemployment Claims':'初请失业金人数',
  'Claimant Count Change':'申领失业金人数变化',
  'Average Earnings Index 3m/y':'平均薪资指数3月/年',
  'Average Hourly Earnings m/m':'平均时薪月率',
  'Employment Cost Index q/q':'就业成本指数季率',
  'JOLTS Job Openings':'JOLTS职位空缺',
  'Prelim Benchmark Payrolls Revision':'基准薪资修正初值',
  'Advance GDP q/q':'GDP初值季率', 'Advance GDP Price Index q/q':'GDP初值物价指数季率',
  'Prelim GDP q/q':'GDP修正值季率', 'Prelim GDP Price Index q/q':'GDP修正值物价指数季率',
  'Final GDP q/q':'GDP终值季率', 'Final GDP Price Index q/q':'GDP终值物价指数季率',
  'GDP m/m':'GDP月率','GDP q/q':'GDP季率',
  'German Prelim GDP q/q':'德国GDP初值季率',
  'Flash Manufacturing PMI':'制造业PMI初值','Flash Services PMI':'服务业PMI初值',
  'French Flash Manufacturing PMI':'法国制造业PMI初值',
  'French Flash Services PMI':'法国服务业PMI初值',
  'German Flash Manufacturing PMI':'德国制造业PMI初值',
  'German Flash Services PMI':'德国服务业PMI初值',
  'ISM Manufacturing PMI':'ISM制造业PMI', 'ISM Manufacturing Prices':'ISM制造业物价指数',
  'ISM Services PMI':'ISM服务业PMI',
  'Philly Fed Manufacturing Index':'费城联储制造业指数',
  'Retail Sales m/m':'零售销售月率',
  'CB Consumer Confidence':'谘商会消费者信心指数',
  'Prelim UoM Consumer Sentiment':'密歇根大学消费者信心初值',
  'Revised UoM Consumer Sentiment':'密歇根大学消费者信心终值',
  'New Home Sales':'新屋销售', 'Pending Home Sales m/m':'成屋签约销售月率',
  'Annual Budget Release':'年度预算发布', 'Ivey PMI':'Ivey采购经理人指数',
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
  'Jackson Hole Symposium':'杰克逊霍尔全球央行年会',
}};

function t(en){{
  if(TITLE_CN[en]) return TITLE_CN[en];
  return en;
}}

function esc(s){{
  if(!s)return'';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}}

var _calYear = null, _calMonth = null, _calSelected = null;

function renderCalendar(){{
  var cd = EVENTS_DATA.filter(function(ev){{ return ev.date && ev.time; }});
  var groups = {{}};
  cd.forEach(function(ev){{
    var d = ev.date;
    if(!groups[d]) groups[d] = {{events:[]}};
    groups[d].events.push(ev);
  }});

  var todayStr = new Date().toISOString().slice(0,10);
  var sortedDates = Object.keys(groups).sort();
  var focus = sortedDates.indexOf(todayStr) >= 0 ? todayStr : sortedDates[0];
  if(!focus) {{ document.getElementById('calendar-grid').innerHTML = '<div class=\"empty-state\">暂无数据</div>'; return; }}
  var parts = focus.split('-');
  if(_calYear === null) {{ _calYear = parseInt(parts[0]); _calMonth = parseInt(parts[1]); }}
  if(!_calSelected) _calSelected = todayStr;

  var curYear = _calYear, curMonth = _calMonth;
  var monthNames = ['一月','二月','三月','四月','五月','六月','七月','八月','九月','十月','十一月','十二月'];
  var firstDay = new Date(curYear, curMonth-1, 1);
  var lastDay = new Date(curYear, curMonth, 0);
  var totalDays = lastDay.getDate();
  var startWeekday = firstDay.getDay();
  var dowNames = ['日','一','二','三','四','五','六'];

  var html = '<div class=\"cal-grid-nav\">' +
    '<button class=\"cal-nav-btn\" onclick=\"prevMonth()\">&#9664;</button>' +
    '<span class=\"cal-nav-title\">'+monthNames[curMonth-1]+' '+curYear+'</span>' +
    '<button class=\"cal-nav-btn\" onclick=\"nextMonth()\">&#9654;</button></div>';

  html += '<div class=\"cal-grid-dows\">';
  for(var wi=0;wi<7;wi++) html += '<span class=\"cal-gdow\">'+dowNames[wi]+'</span>';
  html += '</div><div class=\"cal-grid-body\">';

  for(var ei=0;ei<startWeekday;ei++) html += '<div class=\"cal-gcell cal-gempty\"></div>';

  for(var di=1;di<=totalDays;di++){{
    var dateStr = curYear+'-'+(curMonth<10?'0':'')+curMonth+'-'+(di<10?'0':'')+di;
    var g = groups[dateStr];
    var evCount = g ? g.events.length : 0;
    var hiCount = g ? g.events.filter(function(e){{return e.impact==='high'}}).length : 0;
    var cls = dateStr === todayStr ? ' cal-gtoday' : '';
    if(evCount > 0) cls += ' cal-ghasevent';
    if(dateStr === _calSelected) cls += ' cal-gselected';
    html += '<div class=\"cal-gcell'+cls+'\" onclick=\"selectDate(&quot;'+dateStr+'&quot;)\">';
    html += '<span class=\"cal-gdaynum\">'+di+'</span>';
    if(evCount > 0){{
      html += '<span class=\"cal-gdot\">';
      for(var h=0;h<hiCount&&h<3;h++) html += '<span class=\"cal-gdot-hi\"></span>';
      for(var m=0;m<evCount-hiCount&&m<3;m++) html += '<span class=\"cal-gdot-md\"></span>';
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
  if(!g && !groups){{
    var cd = EVENTS_DATA.filter(function(ev){{return ev.date&&ev.time;}});
    var tmp = {{}};
    cd.forEach(function(ev){{if(!tmp[ev.date])tmp[ev.date]={{events:[]}};tmp[ev.date].events.push(ev);}});
    g = tmp[dateStr];
  }}
  if(!g||!g.events.length){{
    el.innerHTML = '<div class=\"cal-sel-header\">'+esc(dateStr)+'<span class=\"cal-sel-count\">0条事件</span></div><div class=\"cal-sel-empty\">所选日期暂无事件</div>';
    return;
  }}
  var count = g.events.length;
  var hiCount = g.events.filter(function(e){{return e.impact==='high'}}).length;
  var html = '<div class=\"cal-sel-header\">'+esc(dateStr)+'<span class=\"cal-sel-count\">'+count+'条事件（高影响'+hiCount+'条）</span></div>';
  g.events.forEach(function(ev){{ html += renderCalEvent(ev); }});
  el.innerHTML = html;
}}

function renderCalEvent(ev){{
  var ai = ev.ai_analysis || {{}};
  var ic = ev.impact === 'high' ? 'hi' : 'md';
  var html = '<div class=\"cal-ev imp-'+ic+'\" onclick=\"toggleDetail(this)\">';
  html += '<div class=\"cal-ev-header\">';
  html += '<span class=\"cal-tm\">'+esc(ev.time||'--:--')+'</span>';
  html += '<span class=\"cal-ccy\">'+esc(ev.currency)+'</span>';
  html += '<span class=\"cal-tl\">'+esc(t(ev.title))+'</span>';
  if(ev.impact==='high') html += '<span class=\"cal-impact-badge\" style=\"background:#f8514915;color:#f85149\">&#128308; 高</span>';
  html += '</div>';
  var vals = '';
  if(ev.actual) vals += '<span class=\"cal-val act\">实: '+esc(ev.actual)+'</span>';
  if(ev.forecast) vals += '<span class=\"cal-val fcast\">预: '+esc(ev.forecast)+'</span>';
  if(ev.previous) vals += '<span class=\"cal-val prev\">前: '+esc(ev.previous)+'</span>';
  if(vals) html += '<div class=\"cal-vals\">'+vals+'</div>';
  html += '<div class=\"cal-ev-detail\">';
  if(ai.impact_assessment||ai.crypto_relevance||ai.trend_note){{
    html += '<div class=\"ai-card\"><h3>&#129302; AI 分析</h3><div class=\"ai-grid\">';
    if(ai.trend_note) html += '<div class=\"ai-row\"><span class=\"ai-lbl\">趋势：</span><span class=\"ai-val\">'+esc(ai.trend_note)+'</span></div>';
    if(ai.impact_assessment) html += '<div class=\"ai-row\"><span class=\"ai-lbl\">影响：</span><span class=\"ai-val\">'+esc(ai.impact_assessment)+'</span></div>';
    if(ai.crypto_relevance) html += '<div class=\"ai-row\"><span class=\"ai-lbl\">加密关联：</span><span class=\"ai-val\">'+esc(ai.crypto_relevance)+'</span></div>';
    if(ai.direction_bias&&ai.direction_bias!=='neutral') html += '<div class=\"ai-row\"><span class=\"ai-lbl\">倾向：</span><span class=\"ai-val\">'+(ai.direction_bias==='bullish'?'&#128200; 偏多':'&#128201; 偏空')+'</span></div>';
    html += '</div></div>';
  }}
  if(ev.actual&&ev.forecast){{
    html += '<div class=\"ai-card\"><h3>&#128202; 数据对比</h3><div class=\"hist-chart\">';
    var maxV = 0;
    [ev.previous,ev.forecast,ev.actual].forEach(function(v){{
      var n = parseFloat(String(v||'0').replace(/[^0-9.]/g,''));
      if(n>maxV)maxV=n;
    }});
    if(maxV===0)maxV=1;
    ['previous','forecast','actual'].forEach(function(k){{
      var lbl = {{previous:'前',forecast:'预',actual:'实'}}[k];
      var val = ev[k];
      var n = parseFloat(String(val||'0').replace(/[^0-9.]/g,''));
      var w = Math.max(8, Math.round(n/maxV*100));
      var barCls = k==='actual'?'act':(k==='forecast'?'fcast':'prev');
      html += '<div class=\"hist-row\"><span class=\"hist-lbl\">'+lbl+'</span><div class=\"hist-bar-wrap\"><div class=\"hist-bar '+barCls+'\" style=\"width:'+w+'%\"></div></div><span class=\"hist-val\">'+esc(val||'-')+'</span></div>';
    }});
    html += '</div></div>';
  }}
  html += '</div></div>';
  return html;
}}

function toggleDetail(el){{
  var detail = el.querySelector('.cal-ev-detail');
  if(!detail) return;
  detail.style.display = detail.style.display === 'none' ? 'block' : 'none';
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

document.addEventListener('DOMContentLoaded', function(){{
  var h = document.getElementById('header-time');
  if(h && window.HEADER_TIME) h.textContent = window.HEADER_TIME;
  renderCalendar();
}});
'''

js_code = js_template.replace('{data}', events_json)

# --- Build full HTML ---
# Find CSS end in original, insert grid CSS
css_end = content.index('</style>') + 8
head = content[:css_end]

result = head + grid_css + body_html + '<script>\n' + js_code + '\n' + header_time + '\n</script>\n</body>\n</html>\n'

with open('docs/calendar.html', 'w', encoding='utf-8') as f:
    f.write(result)

print(f"Done! {len(result)} bytes")
print(f"TITLE_CN occurrences: {js_code.count('TITLE_CN')}")
print(f"function renderCalendar: {'renderCalendar' in js_code}")
print(f"function renderCalEvent: {'renderCalEvent' in js_code}")
print(f"function t: {js_code.count('function t(')}")
