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
  var syms=['BTCUSDT','ETHUSDT','SOLUSDT','SUIUSDT','DOGEUSDT'];
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
    if(!d)return;
    if(!groups[d])groups[d]={weekday:ev.weekday||'',isToday:!!ev.isToday,events:[]};
    if(!groups[d].events)groups[d].events=[];
    groups[d].events.push(ev);
  });
  
  var dates=Object.keys(groups).sort();
  
  // Show first 2 dates by default, rest collapsed
  var showCount=2;
  var hasMore=dates.length>showCount;
  if(hasMore)dates=dates.slice(0,showCount);
  
  var html='';
  dates.forEach(function(ds){
    var g=groups[ds];
    var tc=g.isToday?' cal-today':'';
    html+='<div class="cal-date-group'+tc+'">';
    html+='<div class="cal-date-hdr">'+esc(ds)+' 周'+g.weekday+'</div>';
    g.events.forEach(function(ev){
      html+=renderCalEvent(ev);
    });
    html+='</div>';
  });
  
  if(hasMore){
    html+='<div class="cal-more-bar"><button class="cal-more-btn" onclick="expandCalendar()">📅 查看全部 '+(Object.keys(groups).length-showCount)+' 天日程</button></div>';
  }
  
  cp.innerHTML=html;
}

function renderCalEvent(ev){
  var ic=ev.impact==='high'?'hi':'md';
  var ai=ev.ai_analysis||{};
  
  var html='<div class="cal-ev imp-'+ic+'" onclick="toggleCalDetail(this)">';
  html+='<div class="cal-ev-header">';
  html+='<span class="cal-tm">'+esc(ev.time||'--:--')+'</span>';
  html+='<span class="cal-ccy">'+esc(ev.currency)+'</span>';
  html+='<span class="cal-tl">'+esc(ev.title)+'</span>';
  if(ev.impact==='high')html+='<span class="cal-impact-badge">🔴 高</span>';
  html+='</div>';
  
  // Values row
  var vals='';
  if(ev.actual)vals+='<span class="cal-val act">实: '+esc(ev.actual)+'</span>';
  if(ev.forecast)vals+='<span class="cal-val fcast">预: '+esc(ev.forecast)+'</span>';
  if(ev.previous)vals+='<span class="cal-val prev">前: '+esc(ev.previous)+'</span>';
  if(vals)html+='<div class="cal-vals">'+vals+'</div>';
  
  // Collapsible detail (AI analysis + historical comparison)
  html+='<div class="cal-detail-content" style="display:none">';
  
  // AI analysis
  if(ai.impact_assessment||ai.crypto_relevance||ai.trend_note){
    html+='<div class="cal-ai-box">';
    html+='<div class="cal-ai-hdr">🤖 AI 分析</div>';
    if(ai.trend_note)html+='<div class="cal-ai-row"><span class="cal-ai-label">趋势：</span>'+esc(ai.trend_note)+'</div>';
    if(ai.impact_assessment)html+='<div class="cal-ai-row"><span class="cal-ai-label">影响：</span>'+esc(ai.impact_assessment)+'</div>';
    if(ai.crypto_relevance)html+='<div class="cal-ai-row"><span class="cal-ai-label">加密关联：</span>'+esc(ai.crypto_relevance)+'</div>';
    var db=ai.direction_bias;
    if(db&&db!=='neutral'){
      var dirIcon=db==='bullish'?'📈':'📉';
      html+='<div class="cal-ai-row"><span class="cal-ai-label">倾向：</span>'+dirIcon+' '+(db==='bullish'?'偏多':'偏空')+'</div>';
    }
    html+='</div>';
  }
  
  // Historical comparison (if actual vs forecast)
  if(ev.actual&&ev.forecast){
    html+='<div class="cal-hist-box">';
    html+='<div class="cal-hist-hdr">📊 数据对比</div>';
    html+='<div class="cal-hist-chart">';
    html+='<div class="cal-hist-row"><span class="cal-hist-lbl">前值</span><div class="cal-hist-bar-wrap"><div class="cal-hist-bar prev" style="width:50%"></div></div><span class="cal-hist-val">'+esc(ev.previous)+'</span></div>';
    html+='<div class="cal-hist-row"><span class="cal-hist-lbl">预测</span><div class="cal-hist-bar-wrap"><div class="cal-hist-bar fcast" style="width:60%"></div></div><span class="cal-hist-val">'+esc(ev.forecast)+'</span></div>';
    html+='<div class="cal-hist-row"><span class="cal-hist-lbl">实际</span><div class="cal-hist-bar-wrap"><div class="cal-hist-bar act" style="width:80%"></div></div><span class="cal-hist-val">'+esc(ev.actual)+'</span></div>';
    html+='</div></div>';
  }
  
  html+='</div>'; // detail-content
  html+='</div>';
  return html;
}

// Expand/collapse event detail
function toggleCalDetail(el){
  var detail=el.querySelector('.cal-detail-content');
  if(!detail)return;
  var expanded=detail.style.display!=='none';
  detail.style.display=expanded?'none':'block';
  el.classList.toggle('expanded',!expanded);
}

var calendarFullData=[];
function expandCalendar(){
  var cd=typeof CALENDAR_DATA!=='undefined'?CALENDAR_DATA:[];
  if(!cd||!cd.length)return;
  
  // Group all by date
  var groups={};
  cd.forEach(function(ev){
    var d=ev.date;
    if(!d)return;
    if(!groups[d])groups[d]={weekday:ev.weekday||'',isToday:!!ev.isToday,events:[]};
    groups[d].events.push(ev);
  });
  
  var dates=Object.keys(groups).sort();
  var cp=$('calendar-panel');
  var html='';
  dates.forEach(function(ds){
    var g=groups[ds];
    var tc=g.isToday?' cal-today':'';
    html+='<div class="cal-date-group'+tc+'">';
    html+='<div class="cal-date-hdr">'+esc(ds)+' 周'+g.weekday+'</div>';
    g.events.forEach(function(ev){
      html+=renderCalEvent(ev);
    });
    html+='</div>';
  });
  cp.innerHTML=html;
}

// ===== Chain Data Panel (链上数据弹窗) =====
function openChainPanel(coin){
  var ov=$('chain-overlay'),md=$('chain-modal'),mb=$('chain-modal-body'),mt=$('chain-modal-title');
  if(!ov||!md||!mb)return;
  
  // Close if already open with same coin
  if(md.classList.contains('open')&&mt.dataset.coin===coin){closeChainPanel();return}
  
  ov.classList.add('open');
  md.classList.add('open');
  mt.textContent=coin+' 链上数据分析';
  mt.dataset.coin=coin;
  mb.innerHTML='<div class="chain-loading">加载中…</div>';
  
  var cd=typeof CHAIN_DATA!=='undefined'&&CHAIN_DATA?CHAIN_DATA:null;
  if(!cd||!cd.coins||!cd.coins[coin]){
    mb.innerHTML='<div class="chain-loading" style="padding:30px">⚠️ 链上数据暂不可用，请稍后刷新页面</div>';
    return;
  }
  
  renderChainPanel(mb,cd,coin);
}

function closeChainPanel(){
  var ov=$('chain-overlay'),md=$('chain-modal');
  if(ov)ov.classList.remove('open');
  if(md)md.classList.remove('open');
}

// ESC key to close
document.addEventListener('keydown',function(e){
  if(e.key==='Escape')closeChainPanel();
});

function renderChainPanel(mb,cd,coin){
  var d=cd.coins[coin]||{};
  var fg=cd.fear_greed||{};
  var price=d.price||0;
  var change=d.change_pct||0;
  var score=d.score||50;
  var risk=d.risk_level||'中';
  var signals=d.signals||[];
  var detail=d.detail||'';
  var marketTrend=d.market_trend||'中性';
  var leverageSent=d.leverage_sentiment||'中性';
  var capitalFlow=d.capital_flow||'中性';
  
  // Score color
  var sc=score>=65?'#3fb950':score>=45?'#d29922':'#f85149';
  
  var html='';
  
  // Score circle
  html+='<div class="chain-score">';
  html+='  <span class="chain-score-num" style="color:'+sc+'">'+score+'</span>';
  html+='  <span class="chain-score-label">综合评分 · 风险等级 '+risk+'</span>';
  html+='  <div class="chain-score-bar">';
  html+='    <div class="chain-score-fill" style="width:'+score+'%;background:'+sc+'"></div>';
  html+='  </div>';
  html+='</div>';
  
  // Summary
  html+='<div class="chain-summary">';
  html+='  <div class="label">🤖 金峰策略AI分析</div>';
  html+='  <div class="text">'+esc(detail)+'</div>';
  html+='</div>';
  
  // 3 status tags
  var trendEmoji=marketTrend.includes('上涨')||marketTrend.includes('强势')?'📈':marketTrend.includes('下跌')?'📉':'➡️';
  html+='<div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px">';
  html+='  <span style="font-size:11px;padding:3px 8px;border-radius:6px;background:#121318;border:1px solid #1b1d23;color:#c9d1d9">'+trendEmoji+' '+esc(marketTrend)+'</span>';
  var levEmoji=leverageSent.includes('过热')?'🔥':leverageSent.includes('偏')||leverageSent.includes('略')?'💸':'⚖️';
  html+='  <span style="font-size:11px;padding:3px 8px;border-radius:6px;background:#121318;border:1px solid #1b1d23;color:#c9d1d9">'+levEmoji+' '+esc(leverageSent)+'</span>';
  var capEmoji=capitalFlow.includes('极度偏多')?'⚠️':capitalFlow.includes('偏多')?'👥':capitalFlow.includes('偏空')?'🟢':'⚖️';
  html+='  <span style="font-size:11px;padding:3px 8px;border-radius:6px;background:#121318;border:1px solid #1b1d23;color:#c9d1d9">'+capEmoji+' '+esc(capitalFlow)+'</span>';
  html+='</div>';
  
  // Key metrics grid
  var pc=change>=0?'up':'down';
  var pcLabel=(change>=0?'+':'')+change.toFixed(2)+'%';
  
  html+='<div class="chain-metrics">';
  html+='  <div class="chain-metric"><div class="label">价格</div><div class="value" style="color:#e1e4e8;font-size:18px">$'+fmt(price)+'</div><div class="value '+pc+'" style="font-size:13px;font-weight:500">'+pcLabel+'</div></div>';
  html+='  <div class="chain-metric"><div class="label">24h成交量</div><div class="value" style="color:#e1e4e8">$'+(d.volume_24h?fmt(Math.round(d.volume_24h)):'—')+'</div></div>';
  
  if(d.oi_usdt){
    var oiB=coin==='BTC'?(d.oi/1e5).toFixed(2):coin==='ETH'?(d.oi/1e6).toFixed(2):(d.oi/1e6).toFixed(2);
    html+='  <div class="chain-metric"><div class="label">未平仓合约 (OI)</div><div class="value" style="color:#e1e4e8;font-size:15px">$'+fmt(Math.round(d.oi_usdt))+'</div><div class="sub">'+oiB+' 万张</div></div>';
  }else{
    html+='  <div class="chain-metric"><div class="label">未平仓合约</div><div class="value" style="color:#888">—</div></div>';
  }
  
  if(d.funding_rate!==undefined){
    var frLabel=(d.funding_rate>=0?'+':'')+d.funding_rate.toFixed(4)+'%';
    var frColor=d.funding_rate>0.01?'#f85149':d.funding_rate>0.005?'#d29922':'#8b949e';
    html+='  <div class="chain-metric"><div class="label">资金费率</div><div class="value" style="color:'+frColor+'">'+frLabel+'</div></div>';
  }else{
    html+='  <div class="chain-metric"><div class="label">资金费率</div><div class="value" style="color:#888">—</div></div>';
  }
  
  if(d.long_short_ratio){
    var lsr=d.long_short_ratio;
    var lsColor=lsr>1.5?'#f85149':lsr>1.2?'#d29922':'#8b949e';
    var shortPct=(100-d.long_account_pct).toFixed(1);
    html+='  <div class="chain-metric"><div class="label">多/空比</div><div class="value" style="color:'+lsColor+';font-size:15px">'+lsr.toFixed(2)+'</div><div class="sub">多'+(d.long_account_pct||'').toFixed(1)+'% / 空'+shortPct+'%</div></div>';
  }else{
    html+='  <div class="chain-metric"><div class="label">多/空比</div><div class="value" style="color:#888">—</div></div>';
  }
  
  if(d.taker_bs_ratio){
    var tbr=d.taker_bs_ratio;
    var tbColor=tbr>1.1?'#3fb950':tbr<0.9?'#f85149':'#8b949e';
    html+='  <div class="chain-metric"><div class="label">主动买/卖比</div><div class="value" style="color:'+tbColor+'">'+tbr.toFixed(2)+'</div></div>';
  }else{
    html+='  <div class="chain-metric"><div class="label">主动买/卖比</div><div class="value" style="color:#888">—</div></div>';
  }
  
  if(d.top_ls_ratio){
    html+='  <div class="chain-metric"><div class="label">大户多/空比</div><div class="value" style="color:#c9d1d9;font-size:15px">'+d.top_ls_ratio.toFixed(2)+'</div><div class="sub">多'+(d.top_long_pct||'').toFixed(1)+'% / 空'+(100-d.top_long_pct).toFixed(1)+'%</div></div>';
  }else{
    html+='  <div class="chain-metric"><div class="label">大户多/空比</div><div class="value" style="color:#888">—</div></div>';
  }
  
  html+='</div>';
  
  // Signals
  if(signals.length>0){
    html+='<div class="chain-signals">';
    signals.forEach(function(s){
      var e='';
      if(s.includes('📈'))e='📈';else if(s.includes('📉'))e='📉';else if(s.includes('🔥'))e='🔥';else if(s.includes('⚠️'))e='⚠️';else if(s.includes('🟢'))e='🟢';else if(s.includes('🔴'))e='🔴';else if(s.includes('💸'))e='💸';else if(s.includes('💰'))e='💰';else if(s.includes('👥'))e='👥';else if(s.includes('📊'))e='📊';else if(s.includes('⚪'))e='⚪';else if(s.includes('⚖️'))e='⚖️';else if(s.includes('➡️'))e='➡️';else if(s.includes('💤'))e='💤';else if(s.includes('😱')||s.includes('😰')||s.includes('🤑')||s.includes('😊'))e='😱';else e='📌';
      html+='<div class="chain-signal"><span class="emoji">'+e+'</span><span>'+esc(s.replace(/^[📈📉🔥⚠️🟢🔴💸💰👥📊⚪⚖️➡️💤😱😰🤑😊📌]\s*/,''))+'</span></div>';
    });
    html+='</div>';
  }
  
  // Fear & Greed
  if(fg.value){
    var fgColor=fg.value<=25?'#f85149':fg.value<=45?'#ff8c00':fg.value>=75?'#3fb950':'#8b949e';
    html+='<div style="display:flex;align-items:center;gap:8px;padding:8px 12px;background:#121318;border:1px solid #1b1d23;border-radius:8px;margin:8px 0">';
    html+='  <span style="font-size:14px">😱</span>';
    html+='  <span style="flex:1;font-size:12px;color:#8b949e">恐惧与贪婪指数</span>';
    html+='  <span style="font-size:16px;font-weight:700;color:'+fgColor+'">'+fg.value+' — '+fg.classification+'</span>';
    html+='</div>';
  }
  
  // Mini price chart (SVG line chart from klines)
  if(d.klines && d.klines.length>10){
    var prices=d.klines.map(function(c){return c.c});
    var highs=d.klines.map(function(c){return c.h});
    var lows=d.klines.map(function(c){return c.l});
    var minP=Math.min.apply(null,prices);
    var maxP=Math.max.apply(null,prices);
    var range=maxP-minP||1;
    var startP=prices[0];
    var endP=prices[prices.length-1];
    var isUp=endP>=startP;
    var lineColor=isUp?'#3fb950':'#f85149';
    var areaColor=isUp?'rgba(63,185,80,0.12)':'rgba(248,81,73,0.12)';
    var changePct=((endP-startP)/startP*100).toFixed(2);
    // Expand range to include actual high/low in case start/end exceed close range
    var chartMinP=Math.min(minP,startP,endP);
    var chartMaxP=Math.max(maxP,startP,endP);
    var chartRange=chartMaxP-chartMinP||1;
    // Also expand by 5% margin for visual breathing room
    var margin=(chartMaxP-chartMinP)*0.05;
    chartMinP-=margin;
    chartMaxP+=margin;
    chartRange=chartMaxP-chartMinP||1;
    
    var leftPad=52,topPad=16,btmPad=16;  // px padding for labels
    var chW=d.klines.length,chH=120;
    var plotW=chW;
    var plotH=chH-topPad-btmPad;
    // Helper: price to y (using expanded range)
    function py(p){return topPad+plotH-((p-chartMinP)/chartRange*plotH)};
    // Format price
    var f2=function(p){return '$'+p.toFixed(2)};
    var f4=function(p){return p<1?'$'+p.toFixed(4):'$'+p.toFixed(2)};
    var fp=function(p){return p<0.01?p.toFixed(6):p<1?p.toFixed(4):p.toFixed(2)};
    // Key price points: always show high / open / current / low (deduplicated)
    var keyPrices=[chartMaxP, startP, endP, chartMinP];
    keyPrices.sort(function(a,b){return b-a});
    var deduped=[];
    keyPrices.forEach(function(p){
      var r=Math.round(p*10000)/10000;
      if(deduped.length===0 || Math.abs(deduped[deduped.length-1]-r)>0.0001) deduped.push(p);
    });
    keyPrices=deduped;
    
    html+='<div class="chain-chart">';
    html+='<div class="label" style="margin-bottom:6px;display:flex;justify-content:space-between;align-items:center">';
    html+='  <span>📈 24h走势图（15分钟线）</span>';
    html+='  <span style="font-size:12px;font-weight:600;color:'+lineColor+'">高:'+f4(maxP)+' 开:'+f4(startP)+' 现:'+f4(endP)+' <span style="font-weight:700;color:'+lineColor+'">'+(isUp?'+':'')+changePct+'%</span></span>';
    html+='</div>';
    
    html+='<svg width="100%" height="'+chH+'" viewBox="0 0 '+chW+' '+chH+'" preserveAspectRatio="none" style="overflow:visible;display:block">';
    
    // ===== Horizontal lines + price labels for key points =====
    var gColor='rgba(255,255,255,0.06)';
    var tColor='#8b949e';
    keyPrices.forEach(function(p){
      var y=py(p);
      var label='';
      if(p===chartMaxP) label='最高';
      else if(p===chartMinP) label='最低';
      else if(p===startP) label='开盘';
      else if(p===endP) label='现价';
      html+='<line x1="0" y1="'+y+'" x2="'+chW+'" y2="'+y+'" stroke="'+gColor+'" stroke-width="1"/>';
      // Left price
      html+='<text x="0" y="'+(y+3)+'" fill="'+tColor+'" font-size="9" font-family="monospace">'+f4(p)+'</text>';
      // Right label
      html+='<text x="'+(chW-1)+'" y="'+(y-4)+'" fill="'+(label==='现价'?lineColor:tColor)+'" font-size="'+(label==='现价'?'9':'8')+'" text-anchor="end" font-weight="'+(label==='现价'?'bold':'normal')+'">'+label+'</text>';
    });
    
    // ===== Area fill =====
    var areaPts=[];
    prices.forEach(function(p,i){
      var y=py(p);
      areaPts.push(i+','+y);
    });
    var areaStr='0,'+chH+' '+areaPts.join(' ')+' '+(chW-1)+','+chH;
    html+='<polygon points="'+areaStr+'" fill="'+areaColor+'" stroke="none"/>';
    
    // ===== Price line =====
    var pts=[];
    prices.forEach(function(p,i){
      pts.push(i+','+py(p));
    });
    html+='<polyline points="'+pts.join(' ')+'" fill="none" stroke="'+lineColor+'" stroke-width="1.5" stroke-linejoin="round"/>';
    
    // ===== Start/End dots =====
    var startY=py(prices[0]);
    var endY=py(prices[prices.length-1]);
    // Start dot (small)
    html+='<circle cx="0" cy="'+startY+'" r="2.5" fill="'+lineColor+'" opacity="0.6"/>';
    // End dot (big)
    html+='<circle cx="'+(chW-1)+'" cy="'+endY+'" r="4" fill="'+lineColor+'" stroke="#0d0e12" stroke-width="2"/>';
    
    // ===== Volume bars (thin, bottom 25%) =====
    var vols=d.klines.map(function(c){return c.v});
    var maxVol=Math.max.apply(null,vols);
    var volH=plotH*0.18; // 18% of plot height at bottom
    var volY=chH-1;      // bottom of chart
    vols.forEach(function(v,i){
      var barH=(v/maxVol)*volH;
      html+='<rect x="'+i+'" y="'+(volY-barH)+'" width="1" height="'+barH+'" fill="'+lineColor+'" opacity="0.15"/>';
    });
    
    html+='</svg></div>';
  }
  
  // Update timestamp
  if(cd.time){
    html+='<div style="font-size:10px;color:#484f58;text-align:center;padding:6px 0">数据来源: Binance API · 更新时间: '+esc(cd.time.slice(0,19))+'</div>';
  }
  
  mb.innerHTML=html;
}

// Add click handler to coin pills to open chain panel
function setupChainPills(){
  setTimeout(function(){
    document.querySelectorAll('.coin-pill').forEach(function(pill){
      var txt=pill.textContent.trim();
      if(['BTC','ETH','SOL','SUI','DOGE'].indexOf(txt)>=0){
        pill.style.cursor='pointer';
        pill.title='点击查看'+txt+'链上数据';
        pill.addEventListener('click',function(e){
          openChainPanel(txt);
        });
      }
    });
  },500);
}
setupChainPills();
