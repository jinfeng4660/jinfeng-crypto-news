// ===== Utility =====
function $(id){return document.getElementById(id)}
function esc(s){var d=document.createElement('div');d.textContent=s;return d.innerHTML}
function fmt(n){return typeof n==='number'?n.toLocaleString('en-US'):n}
function qs(s,ctx){return (ctx||document).querySelector(s)}
function qsa(s,ctx){return (ctx||document).querySelectorAll(s)}

// ===== NProgress =====
var npTimer=null;
function startProgress(){var b=$('nprogress-bar');var w=15;b.style.width=w+'%';clearInterval(npTimer);npTimer=setInterval(function(){w+=(100-w)*0.06;if(w>=95)w=95;b.style.width=w+'%'},300)}
function doneProgress(){clearInterval(npTimer);$('nprogress-bar').style.width='100%';setTimeout(function(){$('nprogress-bar').style.width='0%'},400)}

// ===== State =====
var currentLevel='ALL',currentCoin='ALL',searchQuery='',currentSort='latest',ARTICLES_DATA=[];
var voted={};

// ===== Prices (Binance API — 无CORS) =====
async function fetchPrices(){
  var syms=['BTCUSDT','ETHUSDT','SOLUSDT','LINKUSDT','DOGEUSDT'];
  try{
    var r=await fetch('https://api.binance.com/api/v3/ticker/24hr?symbols='+JSON.stringify(syms));
    var d=await r.json();
    d.forEach(function(t){
      var sym=t.symbol.replace('USDT','').toLowerCase();
      var pel=$(sym+'-price'),cel=$(sym+'-change');
      if(pel)pel.textContent='$'+fmt(parseFloat(t.lastPrice));
      if(cel){
        var ch=parseFloat(t.priceChangePercent);
        cel.textContent=(ch>0?'+':'')+ch.toFixed(2)+'%';
        cel.className='ticker-change '+(ch>0?'up':'down');
      }
    });
  }catch(e){console.warn('Binance price fetch failed',e)}
  fetchFearGreed();
}
fetchPrices();setInterval(fetchPrices,60000);

// ===== Fear & Greed =====
async function fetchFearGreed(){
  try{
    var r=await fetch('https://api.alternative.me/fng/?limit=1');
    var d=await r.json();
    if(d&&d.data&&d.data[0]){
      var v=parseInt(d.data[0].value);
      var cls=v<=25?'extreme-fear':v<=45?'fear':v<=55?'neutral':v<=75?'greed':'extreme-greed';
      var label=d.data[0].value_classification;
      var fg=$('fng-value');
      if(fg){
        fg.textContent=v+' — '+label;
        fg.className='fng '+cls;
      }
    }
  }catch(e){$('fng-value')&&($('fng-value').textContent='—')}
}

// ===== Relative Time =====
function relTime(t){
  if(!t)return '';
  var now=Date.now();
  var ts;
  if(typeof t==='number'){ts=t}
  else if(typeof t==='string'){
    // Strip timezone suffix like " CST" for parsing
    var clean=t.replace(/\s+(CST|UTC|GMT)[+-]?\d*$/,'');
    if(clean.includes('T')||clean.includes(' ')){
      // Try ISO first, then space-separated
      ts=new Date(clean.replace(' ','T')).getTime();
      if(isNaN(ts)){
        ts=new Date(clean.replace(/(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}).*/,'$1T$2:00')).getTime();
      }
    }else if(t.match(/^\d{4}-\d{2}-\d{2}/)){
      ts=new Date(clean.slice(0,10)+'T'+clean.slice(11,16)+':00').getTime();
    }else{return t}
  }else{return''}
  if(isNaN(ts))return t;
  var m=Math.floor((now-ts)/60000);
  if(m<1)return'刚刚';
  if(m<60){return m+'分钟前'}
  var h=Math.floor(m/60);
  if(h<24){return h+'小时前'}
  return Math.floor(h/24)+'天前';
}

var _rtInt=null;
function startRelTime(){
  if(_rtInt)clearInterval(_rtInt);
  _rtInt=setInterval(function(){
    qsa('.reltime').forEach(function(el){
      var ts=el.dataset.ts;
      if(ts)el.textContent=relTime(ts);
    });
    // Also update minutes display in vote buttons area
  },15000);
}

// ===== AI Analysis =====
function genAI(a){
  var t=(a.title||'')+' '+(a.summary||'');
  var imp=3,dir='neutral',reason='市场关注度一般',strat='';
  var hl=t.match(/(爆仓|暴跌|暴涨|批准|牌照|4\.9亿|2200万|抛售|出售|起诉|诉讼|创新高|巨鲸|强平|崩盘|熔断|清算|回收)/);
  var ml=t.match(/(上线|投资|收购|合作|推出|突破|铸造|获批|银行|通过|牌照|融资|开源|ETF|合规|TVL)/);
  if(hl){imp=7+Math.random()*3|0;reason='重大市场事件，对行情有直接冲击'}else if(ml){imp=4+Math.random()*3|0;reason='行业发展信号，中短期影响值得关注'}else{imp=1+Math.random()*4|0;reason='市场常规动态，持续观察即可'}
  var bullW=(t.match(/(暴涨|看涨|买入|批准|突破|支持|利好|增持|正向|积极|上线|银行|牌照|机构|流入|铸造|融资|增长|流入)/g)||[]);
  var bearW=(t.match(/(暴跌|抛售|看跌|卖出|做空|亏损|爆仓|下跌|利空|抛压|挤兑|起诉|诉讼|流失|调查|监管|打压|出售|罚款|spook|sell|loss|清算)/g)||[]);
  if(bullW.length>bearW.length+1){dir='bullish';reason=bullW.slice(0,2).join('、')+'等利多因素'}else if(bearW.length>bullW.length+1){dir='bearish';reason=bearW.slice(0,2).join('、')+'等利空因素'}
  if(imp>=7){strat='该事件影响级别较高，建议结合技术面确认后决策'}else if(imp>=4){strat='趋势性事件，纳入中短期分析参考'}else{strat='常规信息，保持关注即可'}
  return{impact:imp,direction:dir,reason:reason,strategy:strat}
}

// ===== Render =====
function renderCards(data){
  ARTICLES_DATA=data;
  buildCards();
  startRelTime();
  updateHeaderTime();
}

function updateHeaderTime(){
  var now=new Date();
  if($('header-time'))$('header-time').textContent='🕐 '+now.toLocaleDateString('zh-CN')+' '+now.toLocaleTimeString('zh-CN',{hour12:false,hour:'2-digit',minute:'2-digit'});
  if($('footer-update'))$('footer-update').textContent='🕐 更新于 '+now.toLocaleTimeString('zh-CN',{hour12:false,hour:'2-digit',minute:'2-digit'});
}

// ===== Build Cards (DocumentFragment) =====
function buildCards(){
  var list=$('news-list');
  var fragment=document.createDocumentFragment();
  list.innerHTML='';
  
  if(!ARTICLES_DATA.length){
    list.innerHTML='<div class="empty-state"><div class="icon">📭</div><h3>暂无快讯</h3><p>数据采集中，请稍后刷新</p></div>';
    updateCount();updateSidebar();return
  }
  
  updateStats();
  updateSidebar();
  
  var sorted=getSortedData();
  sorted.forEach(function(a,i){
    fragment.appendChild(createCard(a,i));
  });
  
  list.appendChild(fragment);
  updateCount();
  applyFilterDOM();
  doneProgress();
}

function getSortedData(){
  var sorted=[].concat(ARTICLES_DATA);
  if(currentSort==='hot')sorted.sort(function(a,b){return(b.votes?.bullish||0)+(b.votes?.bearish||0)+(b.votes?.important||0)-((a.votes?.bullish||0)+(a.votes?.bearish||0)+(a.votes?.important||0))});
  return sorted;
}

function createCard(a,i){
  var lv=a.level||'C';
  var leftColor=lv==='S'?'#ff4444':lv==='A'?'#ff8c00':lv==='B'?'#f0c040':'#888';
  var lvLabel=lv==='S'?'🔴 交易级':lv==='A'?'🟠 重要趋势':lv==='B'?'⚡ 辅助参考':'💡 一般资讯';
  var lvColor=lv==='S'?'#ff4444':lv==='A'?'#ff8c00':lv==='B'?'#f0c040':'#888';
  
  var ai=genAI(a);
  var impLabel=ai.impact>=7?'🔴 高影响':ai.impact>=4?'🟡 中影响':'⚪ 低影响';
  var impCls=ai.impact>=7?'impact-high':ai.impact>=4?'impact-mid':'impact-low';
  var dirLabel=ai.direction==='bullish'?'📈 看涨':ai.direction==='bearish'?'📉 看跌':'➡️ 中性';
  var dirCls='dir-'+ai.direction;
  
  var v=a.votes||{bullish:0,bearish:0,important:0};
  var bullishV=v.bullish||0,bearishV=v.bearish||0,impV=v.important||0;
  
  var coins=a.coins&&a.coins.length?a.coins.filter(function(c){return c!=='ALL'}):[];
  var coinHtml=coins.map(function(c){return '<span class="coin-tag">'+esc(c)+'</span>'}).join('');
  
  var linkUrl=a.url||'';
  var linkHtml=linkUrl?' <a href="'+esc(linkUrl)+'" target="_blank" class="source-link" onclick="event.stopPropagation()">🔗</a>':'';
  
  var title=esc(a.title||'');
  var summary=esc(a.summary||'');
  var rawTime=a.rawTime||a.time||'';
  var displayTime=relTime(rawTime);

  var card=document.createElement('div');
  card.className='card level-'+lv.toLowerCase()+(i<3?' card-fast':'');
  card.dataset.i=i;
  card.dataset.level=lv;
  card.dataset.coins=JSON.stringify(a.coins||['ALL']);
  card.dataset.title=(a.title||'').toLowerCase();
  
  card.innerHTML=
    '<div class="left-border" style="background:'+leftColor+'"></div>'+
    '<div class="card-votes">'+
      '<button class="vote-btn up'+(voted[i+'-bullish']?' voted':'')+'" onclick="vote('+i+',\'bullish\',event)">▲<span class="vote-count">'+bullishV+'</span></button>'+
      '<button class="vote-btn imp'+(voted[i+'-important']?' voted':'')+'" onclick="vote('+i+',\'important\',event)">⚡<span class="vote-count">'+impV+'</span></button>'+
      '<button class="vote-btn down'+(voted[i+'-bearish']?' voted':'')+'" onclick="vote('+i+',\'bearish\',event)">▼<span class="vote-count">'+bearishV+'</span></button>'+
    '</div>'+
    '<div class="card-body">'+
      '<div class="card-header">'+
        '<span class="level-badge" style="background:'+lvColor+'15;color:'+lvColor+'">'+lvLabel+'</span>'+
        '<span class="source-badge">'+esc(a.source||'')+linkHtml+'</span>'+
        coinHtml+
        '<span class="time-tag reltime" data-ts="'+esc(rawTime)+'">'+displayTime+'</span>'+
      '</div>'+
      '<div class="card-title">'+title+'</div>'+
      (summary?'<div class="card-summary">'+summary+'</div>':'')+
      '<div class="ai-block">'+
        '<div class="ai-header"><span class="label">AI</span><span style="font-size:10px;color:#484f58">金峰策略智能分析</span></div>'+
        '<div class="ai-tags">'+
          '<span class="ai-tag '+impCls+'">'+impLabel+'</span>'+
          '<span class="ai-tag '+dirCls+'">'+dirLabel+'</span>'+
        '</div>'+
        '<div class="ai-reason">原因：'+esc(ai.reason)+'</div>'+
        '<div class="ai-strategy">'+esc(ai.strategy)+'</div>'+
      '</div>'+
      '<div class="card-footer">'+
        '<button class="expand-btn" onclick="toggleExpand('+i+',event)"><span class="arrow">▾</span> AI分析</button>'+
      '</div>'+
    '</div>';
  
  return card;
}

// ===== Silent Fetch (新快讯静默追加到顶部) =====
async function silentRefresh(){
  var el=$('update-status');
  if(el){el.textContent='正在检查新快讯…';el.classList.add('show')}
  try{
    var r=await fetch('https://api.github.com/repos/jinfeng4660/jinfeng-crypto-news/contents/docs/index.html');
    var d=await r.json();
    var content=atob(d.content);
    var dataMatch=content.match(/var DATA = (\[.+?\]);/);
    if(dataMatch){
      var newData=JSON.parse(dataMatch[1]);
      if(newData.length>ARTICLES_DATA.length){
        // New news arrived - we need the time from the raw
        if(el){el.textContent='📬 发现 '+(newData.length-ARTICLES_DATA.length)+' 条新快讯，刷新页面';el.classList.add('show')}
        setTimeout(function(){location.reload()},3000);
      }else{
        if(el)el.textContent='✅ 已是最新';el.classList.add('show')
        setTimeout(function(){if(el)el.classList.remove('show')},2000);
      }
    }
  }catch(e){if(el)el.textContent='检查失败';setTimeout(function(){if(el)el.classList.remove('show')},2000)}
}

// ===== Toggle Expand =====
function toggleExpand(i,e){
  if(e){e.stopPropagation()}
  var cards=qsa('.card');
  var card=cards[i];
  if(card)card.classList.toggle('expanded');
}

// ===== Stats =====
function updateStats(){
  var stats={S:0,A:0,B:0,C:0};
  ARTICLES_DATA.forEach(function(a){stats[a.level]=(stats[a.level]||0)+1});
  $('stat-all').textContent=ARTICLES_DATA.length;
  $('stat-s').textContent=stats.S||0;$('stat-a').textContent=stats.A||0;$('stat-b').textContent=stats.B||0;$('stat-c').textContent=stats.C||0;
  var max=Math.max(stats.S||1,stats.A||1,stats.B||1,stats.C||1);
  ['S','A','B','C'].forEach(function(l){var el=$('bar-'+l.toLowerCase());if(el)el.style.width=((stats[l]||0)/max*100)+'%'});
}

function updateCount(){
  var visible=qsa('.card:not(.hidden)').length;
  $('feed-count').textContent=visible+' / '+ARTICLES_DATA.length+' 条';
}

// ===== Sidebar =====
function updateSidebar(){
  updateSentiment();
  updateTopics();
  renderCalendar();
  var topics={};
  ARTICLES_DATA.forEach(function(a){
    if(a.coins){
      a.coins.forEach(function(c){
        if(c!="ALL"){topics[c]=(topics[c]||0)+1}
      })
    }
  });
  var m=$('sidebar-mobile');
  if(m)m.innerHTML=$('sidebar-desktop').innerHTML;
}

function updateSentiment(){
  var bullish=0,bearish=0,neutral=0;
  ARTICLES_DATA.forEach(function(a){
    var ai=genAI(a);
    if(ai.direction==='bullish')bullish++;else if(ai.direction==='bearish')bearish++;else neutral++;
  });
  var total=ARTICLES_DATA.length||1;
  var bp=Math.round(bullish/total*100),bp2=Math.round(bearish/total*100),np=100-bp-bp2;
  var sb=$('sentiment-bar');
  if(sb)sb.innerHTML='<div class="seg bullish" style="width:'+bp+'%"></div><div class="seg bearish" style="width:'+bp2+'%"></div><div class="seg neutral" style="width:'+np+'%"></div>';
  var ss=$('sentiment-stats');
  if(ss)ss.innerHTML=
    '<div class="sentiment-row"><span>📈 看涨</span><span class="val">'+bullish+' ('+bp+'%)</span></div>'+
    '<div class="sentiment-row"><span>📉 看跌</span><span class="val">'+bearish+' ('+bp2+'%)</span></div>'+
    '<div class="sentiment-row"><span>➡️ 中性</span><span class="val">'+neutral+' ('+np+'%)</span></div>';
}

function updateTopics(){
  var topics={};
  ARTICLES_DATA.forEach(function(a){
    if(a.coins){
      a.coins.forEach(function(c){
        if(c!="ALL"){topics[c]=(topics[c]||0)+1}
      })
    }
  });
  var topicSorted=Object.keys(topics).sort(function(a,b){return topics[b]-topics[a]}).slice(0,8);
  var html='';topicSorted.forEach(function(t){html+='<span class="hot-topic" onclick="filterByCoin(\''+t+'\')"><span class="dot '+t.toLowerCase()+'"></span>'+esc(t)+'<span class="ht-count">'+topics[t]+'</span></span>'});
  if(!html)html='<span class="hot-topic">无活跃话题</span>';
  var ht=$('hot-topics');
  if(ht)ht.innerHTML=html;
}

function updateSources(){
  var srcMap={};
  ARTICLES_DATA.forEach(function(a){srcMap[a.source]=(srcMap[a.source]||0)+1});
  var srcSorted=Object.keys(srcMap).sort(function(a,b){return srcMap[b]-srcMap[a]});
  var srcMax=Math.max.apply(null,Object.values(srcMap))||1;
  var html='';srcSorted.forEach(function(s){var p=Math.round(srcMap[s]/srcMax*100);html+='<div class="source-row"><span class="src-name">'+esc(s)+'</span><div class="src-bar-wrap"><div class="src-bar-fill" style="width:'+p+'%"></div></div><span class="src-val">'+srcMap[s]+'</span></div>'});
  var sd=$('source-dist');
  if(sd)sd.innerHTML=html;
}

// ===== Filters =====
function applyFilterDOM(){
  var cards=qsa('.card');
  cards.forEach(function(c){
    var idx=parseInt(c.dataset.i);
    var a=ARTICLES_DATA[idx];
    if(!a){c.classList.add('hidden');return}
    var show=true;
    if(currentLevel!=='ALL'&&a.level!==currentLevel)show=false;
    if(currentCoin!=='ALL'){
      var tags=a.coins||[];
      if(!tags.includes(currentCoin))show=false;
    }
    if(searchQuery&&!(a.title||'').toLowerCase().includes(searchQuery))show=false;
    c.classList.toggle('hidden',!show);
  });
  updateCount();
}

function filterByLevel(lv){
  qsa('.stat-item').forEach(function(b){b.classList.remove('active')});
  if(lv!=='ALL')qsa('.stat-item').forEach(function(b){if(b.classList.contains('stat-'+lv))b.classList.add('active')});
  else qsa('.stat-item')[0].classList.add('active');
  currentLevel=lv;
  applyFilterDOM();
}

function filterByCoin(coin){
  qsa('.coin-pill').forEach(function(b){b.classList.remove('active')});
  qsa('.coin-pill').forEach(function(b){if(b.textContent.trim()===coin)b.classList.add('active')});
  currentCoin=coin;
  applyFilterDOM();
  qsa('.hot-topic').forEach(function(b){b.classList.toggle('inactive',coin!=='ALL'&&b.textContent.trim()!==coin)});
}

function doSearch(q){
  searchQuery=q.toLowerCase();
  applyFilterDOM();
}

function setSort(mode){
  currentSort=mode;
  qsa('.sort-btn').forEach(function(b){b.classList.remove('active')});
  $('sort-'+mode).classList.add('active');
  buildCards();
}

// ===== Voting =====
function vote(idx,type,e){
  if(e){e.stopPropagation()}
  var key=idx+'-'+type;
  var cards=qsa('.card');
  var card=cards[parseInt(idx)];
  if(!card)return;
  var btns=card.querySelectorAll('.vote-btn');
  
  if(voted[key]){voted[key]=false;btns.forEach(function(b){b.classList.remove('voted')});return}
  
  ['bullish','bearish','important'].forEach(function(t){voted[idx+'-'+t]=false});
  btns.forEach(function(b){b.classList.remove('voted')});
  
  voted[key]=true;
  var btnMap={bullish:'up',bearish:'down',important:'imp'};
  var cls=btnMap[type]||'';
  btns.forEach(function(b){if(b.classList.contains(cls))b.classList.add('voted')});
}

// ===== Mobile =====
function toggleMobileSidebar(){
  $('sidebar-overlay').classList.toggle('open');
  $('sidebar-mobile').classList.toggle('open');
}

// ===== Auto: silent refresh every 90 seconds =====
setInterval(function(){
  silentRefresh();
  updateHeaderTime();
},90000);

setInterval(function(){
  // 30min full page refresh as fallback
  location.reload();
},1800000);

// ===== Keyboard =====
document.addEventListener('DOMContentLoaded',function(){
  var si=$('search-input');
  if(si)si.addEventListener('input',function(){doSearch(this.value)});
  qsa('.stat-item')[0]&&qsa('.stat-item')[0].classList.add('active');
  startRelTime();
});
// If app.js loaded after DOM, initialize immediately
if(document.readyState!=='loading'){
  var si=$('search-input');
  if(si)si.addEventListener('input',function(){doSearch(this.value)});
  qsa('.stat-item')[0]&&qsa('.stat-item')[0].classList.add('active');
  if(typeof ARTICLES_DATA!=='undefined')renderCards(ARTICLES_DATA);
}
// window.load fallback for renderCards
if(typeof window!=='undefined'){
  if(document.readyState==='complete'){
    if(typeof ARTICLES_DATA!=='undefined'&&typeof renderCards==='function')renderCards(ARTICLES_DATA);
  }else{
    window.addEventListener('load',function(){
      if(typeof ARTICLES_DATA!=='undefined'&&typeof renderCards==='function')renderCards(ARTICLES_DATA);
    });
  }
}

// ===== Calendar =====
function renderCalendar(){
  var cp=$('calendar-panel');
  if(!cp)return;
  var cd=typeof CALENDAR_DATA!=='undefined'?CALENDAR_DATA:[];
  if(!cd||!cd.length){cp.innerHTML='<div class="cal-empty">暂无财经日历数据</div>';return}
  
  // Group by date
  var groups={};
  cd.forEach(function(ev){
    var d=ev.date;
    if(!groups[d])groups[d]={weekday:ev.weekday,isToday:!!ev.isToday,events:[]};
    groups[d].events.push(ev);
  });
  
  var dates=Object.keys(groups).sort();
  var html='';
  dates.forEach(function(ds){
    var g=groups[ds];
    var tc=g.isToday?' cal-today':'';
    html+='<div class="cal-date-group'+tc+'">';
    html+='<div class="cal-date-hdr">'+esc(ds)+' 周'+g.weekday+'</div>';
    g.events.forEach(function(ev){
      var ic=ev.impact==='high'?'hi':'md';
      html+='<div class="cal-ev imp-'+ic+'">';
      html+='<span class="cal-tm">'+esc(ev.time||'--:--')+'</span>';
      html+='<span class="cal-ccy">'+esc(ev.currency)+'</span>';
      html+='<span class="cal-tl">'+esc(ev.title)+'</span>';
      var det=[];
      if(ev.actual)det.push('实: '+ev.actual);
      if(ev.previous)det.push('前: '+ev.previous);
      if(ev.forecast)det.push('预: '+ev.forecast);
      if(det.length)html+='<div class="cal-det">'+det.join(' | ')+'</div>';
      html+='</div>';
    });
    html+='</div>';
  });
  cp.innerHTML=html;
}
