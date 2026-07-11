"""
将月历网格注入到现有calendar.html的HTML结构中
- 在 .left-panel 顶部加入月历网格区域（在 panel-header 下方，event-list 上方）
- 添加月历网格的CSS样式（内联到原有style中）
- 添加月历交互JS（内联到原有script前）
"""
import re, os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAL_PATH = os.path.join(BASE, "docs", "calendar.html")

with open(CAL_PATH, "r", encoding="utf-8") as f:
    html = f.read()

# ===== 1. 注入 CSS（在 </style> 前） =====
grid_css = """
/* ===== 月历网格 ===== */
.cal-grid-wrap{padding:12px 14px 4px;border-bottom:1px solid #1b1d23}
.cal-grid-nav{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px}
.cal-grid-nav .nav-btn{background:#121318;border:1px solid #1b1d23;border-radius:6px;color:#8b949e;cursor:pointer;padding:4px 10px;font-size:14px;transition:all .2s}
.cal-grid-nav .nav-btn:hover{background:#1b1d23;color:#c9d1d9}
.cal-grid-nav .nav-title{font-size:13px;font-weight:700;color:#e1e4e8}
.cal-grid-dows{display:grid;grid-template-columns:repeat(7,1fr);gap:2px;margin-bottom:4px}
.cal-grid-dows .dow{text-align:center;font-size:10px;color:#484f58;padding:3px 0;font-weight:600}
.cal-grid-body{display:grid;grid-template-columns:repeat(7,1fr);gap:2px}
.cal-gcell{aspect-ratio:1;display:flex;flex-direction:column;align-items:center;justify-content:center;border-radius:6px;font-size:12px;color:#8b949e;cursor:pointer;transition:all .15s;position:relative;min-height:28px}
.cal-gcell:hover{background:#1b1d23;color:#c9d1d9}
.cal-gcell .day-num{font-weight:500}
.cal-gcell .day-dots{display:flex;gap:2px;position:absolute;bottom:2px}
.cal-gcell .day-dot{width:3px;height:3px;border-radius:50%}
.cal-gcell .day-dot.hi{background:#f85149}
.cal-gcell .day-dot.md{background:#d29922}
.cal-hempty{aspect-ratio:1;min-height:28px}
.cal-hempty:hover{background:transparent;cursor:default}
.cal-gtoday{border:1px solid #3fb950;background:#3fb95008}
.cal-gtoday .day-num{color:#3fb950;font-weight:700}
.cal-gselected{background:#1b1d23;border:1px solid #30363d}
.cal-gselected .day-num{color:#e1e4e8;font-weight:700}
.cal-gouter-month .day-num{color:#30363d}
"""

if grid_css not in html:
    html = html.replace("</style>", grid_css + "\n</style>")
    print("[CSS] 月历网格样式已注入")
else:
    print("[CSS] 月历网格样式已存在，跳过")

# ===== 2. 注入 HTML 月历区域 =====
# 在 <div id="event-list"></div> 前加入月历网格
grid_html = """  <div class="cal-grid-wrap" id="cal-grid-wrap">
    <div class="cal-grid-nav">
      <button class="nav-btn" onclick="prevMonth()">◀</button>
      <span class="nav-title" id="cal-nav-title"></span>
      <button class="nav-btn" onclick="nextMonth()">▶</button>
    </div>
    <div class="cal-grid-dows" id="cal-grid-dows">
      <span class="dow">日</span><span class="dow">一</span><span class="dow">二</span><span class="dow">三</span>
      <span class="dow">四</span><span class="dow">五</span><span class="dow">六</span>
    </div>
    <div class="cal-grid-body" id="cal-grid-body"></div>
  </div>
"""

target = '<div id="event-list"></div>'
if '<div class="cal-grid-wrap"' not in html:
    html = html.replace(target, grid_html + '\n    ' + target)
    print("[HTML] 月历网格 DOM 已注入")
else:
    print("[HTML] 月历网格 DOM 已存在，跳过")

# ===== 3. 注入 JS 月历逻辑（在第一个 <script> 内容中，var EVENTS_DATA 之后） =====
grid_js = """
// ===== 月历网格 =====
var calViewDate = new Date();
var calSelectedDate = '';
var calEventMap = {};

function buildCalEventMap(){
  calEventMap = {};
  EVENTS_DATA.forEach(function(e){
    var d = e.date;
    if(!calEventMap[d]) calEventMap[d] = {hi:0, md:0, events:[]};
    if(e.impact === 'high' || e.impact === 'red') calEventMap[d].hi++;
    else if(e.impact === 'medium' || e.impact === 'orange') calEventMap[d].md++;
    else calEventMap[d].md++; // low impact as md dot
    calEventMap[d].events.push(e);
  });
}

function renderCalendarGrid(){
  var year = calViewDate.getFullYear();
  var month = calViewDate.getMonth();
  
  // 标题
  var months = ['一月','二月','三月','四月','五月','六月','七月','八月','九月','十月','十一月','十二月'];
  document.getElementById('cal-nav-title').textContent = months[month] + ' ' + year;
  
  // 当月天数
  var firstDay = new Date(year, month, 1).getDay(); // 0=周日
  var daysInMonth = new Date(year, month + 1, 0).getDate();
  
  // 今天
  var today = new Date();
  var todayStr = today.getFullYear() + '-' + String(today.getMonth()+1).padStart(2,'0') + '-' + String(today.getDate()).padStart(2,'0');
  
  var body = document.getElementById('cal-grid-body');
  body.innerHTML = '';
  
  // 上月补齐（空白格）
  for(var i=0; i<firstDay; i++){
    var empty = document.createElement('div');
    empty.className = 'cal-gcell cal-hempty';
    body.appendChild(empty);
  }
  
  // 当月日子
  for(var d=1; d<=daysInMonth; d++){
    var dateStr = year + '-' + String(month+1).padStart(2,'0') + '-' + String(d).padStart(2,'0');
    var cell = document.createElement('div');
    cell.className = 'cal-gcell';
    cell.dataset.date = dateStr;
    
    // 今天高亮
    if(dateStr === todayStr) cell.classList.add('cal-gtoday');
    // 选中
    if(dateStr === calSelectedDate) cell.classList.add('cal-gselected');
    
    // 日子数字
    var numSpan = document.createElement('span');
    numSpan.className = 'day-num';
    numSpan.textContent = d;
    cell.appendChild(numSpan);
    
    // 事件点
    var info = calEventMap[dateStr];
    if(info && (info.hi > 0 || info.md > 0)){
      var dots = document.createElement('div');
      dots.className = 'day-dots';
      for(var h=0; h<Math.min(info.hi,3); h++){
        var dot = document.createElement('span');
        dot.className = 'day-dot hi';
        dots.appendChild(dot);
      }
      for(var m=0; m<Math.min(info.md,3); m++){
        var dot2 = document.createElement('span');
        dot2.className = 'day-dot md';
        dots.appendChild(dot2);
      }
      cell.appendChild(dots);
    }
    
    cell.onclick = function(){
      selectCalDate(this.dataset.date);
    };
    
    body.appendChild(cell);
  }
}

function prevMonth(){
  calViewDate.setMonth(calViewDate.getMonth() - 1);
  renderCalendarGrid();
}

function nextMonth(){
  calViewDate.setMonth(calViewDate.getMonth() + 1);
  renderCalendarGrid();
}

function selectCalDate(dateStr){
  calSelectedDate = dateStr;
  renderCalendarGrid();
  
  // 筛选左侧事件列表
  applyDateFilter(dateStr);
}

function applyDateFilter(dateStr){
  var groups = document.querySelectorAll('.cal-date-group');
  groups.forEach(function(g){
    var dateHdr = g.querySelector('.cal-date-hdr');
    if(!dateHdr) return;
    var gDate = g.dataset.date || '';
    if(gDate === dateStr){
      g.style.display = '';
      // 把该组滚到可视区域
      setTimeout(function(){ g.scrollIntoView({behavior:'smooth', block:'start'}) }, 100);
    } else {
      g.style.display = 'none';
    }
  });
}

function clearDateFilter(){
  calSelectedDate = '';
  document.querySelectorAll('.cal-date-group').forEach(function(g){ g.style.display = '' });
  renderCalendarGrid();
}

// 初始化月历时加载事件映射
buildCalEventMap();
renderCalendarGrid();
"""

# 找到 EVENTS_DATA 定义之后、第一个函数之前
# 在 calendar.html 的JS中，EVENTS_DATA 是 var EVENTS_DATA = [...] 
# 在它后面插入月历JS
insert_target = 'var calViewDate = new Date();'
if insert_target not in html or True:  # 重新注入
    # 找 EVENTS_DATA 声明位置
    ev_idx = html.find('var EVENTS_DATA =')
    if ev_idx >= 0:
        # 找 EVENTS_DATA 数组结束位置 -> 后面的分号
        # 直接在 EVENTS_DATA 后面、TITLE_CN 之前插入
        tc_idx = html.find('var TITLE_CN =', ev_idx)
        if tc_idx >= 0:
            # 在 TITLE_CN 之前插入月历JS
            before = html[:tc_idx]
            after = html[tc_idx:]
            # 检查是否已插过
            if 'calViewDate' in before:
                print("[JS] 月历JS已存在，跳过")
            else:
                html = before + '\n' + grid_js + '\n' + after
                print("[JS] 月历JS已注入（在 TITLE_CN 前）")
        else:
            # 找后面的注释或函数
            fn_idx = html.find('function t(', ev_idx)
            if fn_idx >= 0:
                before = html[:fn_idx]
                after = html[fn_idx:]
                if 'calViewDate' not in before:
                    html = before + '\n' + grid_js + '\n' + after
                    print("[JS] 月历JS已注入（在 t() 前）")
                else:
                    print("[JS] 月历JS已存在，跳过")
    else:
        print("[JS] 找不到 EVENTS_DATA!")
else:
    print("[JS] 月历JS已存在，跳过")

# 写入
with open(CAL_PATH, "w", encoding="utf-8") as f:
    f.write(html)

print(f"\n✅ 月历网格已注入 {CAL_PATH}")
print(f"   文件大小: {len(html.encode('utf-8'))} bytes")
