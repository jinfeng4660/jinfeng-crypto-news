// ===== Utility =====
function $(id){return document.getElementById(id)}
function esc(s){var d=document.createElement('div');d.textContent=s;return d.innerHTML}
function fmt(n){return typeof n==='number'?n.toLocaleString('en-US'):n}

// ===== Progress Bar =====
var npTimer=null;
function startProgress(){var b=$('nprogress-bar');var w=10;b.style.width=w+'%';clearInterval(npTimer);npTimer=setInterval(function(){w+=(100-w)*0.08;if(w>=98)w=98;b.style.width=w+'%'},300)}
function doneProgress(){clearInterval(npTimer);$('nprogress-bar').style.width='100%';setTimeout(function(){$('nprogress-bar').style.width='0%'},500)}

// ===== State =====
var currentLevel='ALL',currentCoin='ALL',searchQuery='',currentSort='latest',ARTICLES_DATA=[];

// ===== Prices =====
async function fetchPrices(){try{var r=await fetch('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana&vs_currencies=usd&include_24hr_change=true');var d=await r.json();function u(id,pel,cel){var p=d[id]?.usd,c=d[id]?.usd_24h_change;if(p)$(pel).textContent='$'+fmt(p);if(c!==undefined){$(cel).textContent=(c>0?'+':'')+c.toFixed(2)+'%';$(cel).className='ticker-change '+(c>0?'up':'down')}};u('bitcoin','btc-price','btc-change');u('ethereum','eth-price','eth-change');u('solana','sol-price','sol-change')}catch(e){}}
fetchPrices();setInterval(fetchPrices,60000);

// ===== AI Analysis Generator =====
function genAI(a){
  var t=(a.title||'')+' '+(a.summary||'');
  var imp=3,dir='neutral',reason='市场关注度一般',strat='';
  var hl=t.match(/(爆仓|暴跌|暴涨|批准|牌照|4\.9亿|2200万|抛售|出售|起诉|诉讼|创新高|巨鲸|强平)/);
  var ml=t.match(/(上线|投资|收购|合作|推出|突破|铸造|获批|银行|通过|牌照|融资|开源)/);
  if(hl){imp=7+Math.random()*3|0;reason='重大市场事件，对行情有直接冲击'}else if(ml){imp=4+Math.random()*3|0;reason='行业发展信号，中短期影响值得关注'}else{imp=1+Math.random()*4|0;reason='市场常规动态，持续观察即可'}
  var bullW=(t.match(/(暴涨|看涨|买入|批准|突破|支持|利好|增持|正向|积极|上线|银行|牌照|机构|流入|铸造|融资)/g)||[]);
  var bearW=(t.match(/(暴跌|抛售|看跌|卖出|做空|亏损|爆仓|下跌|利空|抛压|挤兑|起诉|诉讼|流失|调查|监管|打压|出售|罚款)/g)||[]);
  if(bullW.length>bearW.length+1){dir='bullish';reason=bullW.slice(0,2).join('、')+'等利多因素'}else if(bearW.length>bullW.length+1){dir='bearish';reason=bearW.slice(0,2).join('、')+'等利空因素'}
  if(imp>=7){strat='该事件影响级别较高，建议结合技术面确认后决策'}else if(imp>=4){strat='趋势性事件，纳入中短期分析参考'}else{strat='常规信息，保持关注即可'}
  return{impact:imp,direction:dir,reason:reason,strategy:strat}
}

// ===== Render =====
function renderCards(data){
  ARTICLES_DATA=data;
  buildCards();
  var now=new Date();
  $('header-time').textContent='🕐 '+now.toLocaleDateString('zh-CN')+' '+now.toLocaleTimeString('zh-CN',{hour12:false,hour:'2-digit',minute:'2-digit'});
  $('footer-update').textContent='🕐 更新于 '+now.toLocaleTimeString('zh-CN',{hour12:false,hour:'2-digit',minute:'2-digit'});
  doneProgress();
}

function buildCards(){
  var list=$('news-list');list.innerHTML='';
  if(!ARTICLES_DATA.length){list.innerHTML='<div class="empty-state"><div class="icon">📭</div><h3>暂无快讯</h3><p>数据采集中，请稍后刷新</p></div>';return}
  
  // Stats
  var stats={S:0,A:0,B:0,C:0};
  ARTICLES_DATA.forEach(function(a){stats[a.level]=(stats[a.level]||0)+1});
  $('stat-all').textContent=ARTICLES_DATA.length;
  $('stat-s').textContent=stats.S||0;$('stat-a').textContent=stats.A||0;$('stat-b').textContent=stats.B||0;$('stat-c').textContent=stats.C||0;
  var max=Math.max(stats.S||1,stats.A||1,stats.B||1,stats.C||1);
  ['S','A','B','C'].forEach(function(l){var el=$('bar-'+l.toLowerCase());if(el)el.style.width=((stats[l]||0)/max*100)+'%'});
  
  // Sidebar: sentiment
  var bullish=0,bearish=0,neutral=0;
  var srcMap={};
  ARTICLES_DATA.forEach(function(a){
    var ai=genAI(a);
    if(ai.direction==='bullish')bullish++;else if(ai.direction==='bearish')bearish++;else neutral++;
    srcMap[a.source]=(srcMap[a.source]||0)+1;
  });
  var total=ARTICLES_DATA.length;
  var bp=Math.round(bullish/total*100),bp2=Math.round(bearish/total*100),np=100-bp-bp2;
  $('sentiment-bar').innerHTML='<div class="seg bullish" style="width:'+bp+'%"></div><div class="seg bearish" style="width:'+bp2+'%"></div><div class="seg neutral" style="width:'+np+'%"></div>';
  $('sentiment-stats').innerHTML=
    '<div class="sentiment-row"><span>📈 看涨</span><span class="val">'+bullish+' ('+bp+'%)</span></div>'+
    '<div class="sentiment-row"><span>📉 看跌</span><span class="val">'+bearish+' ('+bp2+'%)</span></div>'+
    '<div class="sentiment-row"><span>➡️ 中性</span><span class="val">'+neutral+' ('+np+'%)</span></div>';
  
  // Sidebar: sources
  var srcSorted=Object.keys(srcMap).sort(function(a,b){return srcMap[b]-srcMap[a]});
  var srcMax=Math.max.apply(null,Object.values(srcMap));
  var srcHtml='';srcSorted.forEach(function(s){var p=Math.round(srcMap[s]/srcMax*100);srcHtml+='<div class="source-row"><span class="src-name">'+esc(s)+'</span><div class="src-bar-wrap"><div class="src-bar-fill" style="width:'+p+'%"></div></div><span class="src-val">'+srcMap[s]+'</span></div>'});
  $('source-dist').innerHTML=srcHtml;
  
  // Sidebar: hot topics
  var topics={};
  ARTICLES_DATA.forEach(function(a){if(a.coins){a.coins.forEach(function(c){if(c!=='ALL'){topics[c]=(topics[c]||0)+1}})}});
  var topicSorted=Object.keys(topics).sort(function(a,b){return topics[b]-topics[a]}).slice(0,8);
  var topicHtml='';topicSorted.forEach(function(t){topicHtml+='<span class="hot-topic"><span class="dot '+t.toLowerCase()+'"></span>'+esc(t)+'<span class="ht-count">'+topics[t]+'</span></span>'});
  if(!topicHtml)topicHtml='<span class="hot-topic">无活跃话题</span>';
  $('hot-topics').innerHTML=topicHtml;
  
  // Cards
  var sorted=[].concat(ARTICLES_DATA);
  if(currentSort==='hot')sorted.sort(function(a,b){return(b.votes?.bullish||0)+(b.votes?.bearish||0)+(b.votes?.important||0)-((a.votes?.bullish||0)+(a.votes?.bearish||0)+(a.votes?.important||0))});
  
  sorted.forEach(function(a,i){
    var lv=a.level||'C';
    var leftColor=lv==='S'?'#ff4444':lv==='A'?'#ff8c00':lv==='B'?'#f0c040':'#888';
    var lvLabel=lv==='S'?'🔴 交易级':lv==='A'?'🟠 重要趋势':lv==='B'?'⚡ 辅助参考':'💡 一般资讯';
    var lvColor=lv==='S'?'#ff4444':lv==='A'?'#ff8c00':lv==='B'?'#f0c040':'#888';
    var ai=genAI(a);
    var impLabel=ai.impact>=7?'🔴 高影响':ai.impact>=4?'🟡 中影响':'⚪ 低影响';
    var impCls=ai.impact>=7?'impact-high':ai.impact>=4?'impact-mid':'impact-low';
    var dirLabel=ai.direction==='bullish'?'📈 看涨':ai.direction==='bearish'?'📉 看跌':'➡️ 中性';
    var dirCls='dir-'+ai.direction;
    var dirColor=ai.direction==='bullish'?'#3fb950':ai.direction==='bearish'?'#f85149':'#8b949e';
    var coins=a.coins&&a.coins.length?a.coins.filter(function(c){return c!=='ALL'}):[];
    var coinHtml=coins.map(function(c){return '<span class="coin-tag">'+esc(c)+'</span>'}).join('');
    var timeStr=a.time||'';
    var v=a.votes||{bullish:0,bearish:0,important:0};
    var title=esc(a.title||'');
    var summary=esc(a.summary||'');
    
    var card=document.createElement('div');
    card.className='card level-'+lv.toLowerCase();
    card.style.animationDelay=(i*30)+'ms';
    card.dataset.i=i;
    card.dataset.level=lv;
    card.dataset.coins=JSON.stringify(a.coins||['ALL']);
    card.dataset.title=(a.title||'').toLowerCase();
    
    card.innerHTML=
      '<div class="left-border" style="background:'+leftColor+'"></div>'+
      '<div class="card-votes">'+
        '<button class="vote-btn up" onclick="vote(\''+i+'\',\'bullish\')">▲</button>'+
        '<button class="vote-btn imp" onclick="vote(\''+i+'\',\'important\')">⚡</button>'+
        '<button class="vote-btn down" onclick="vote(\''+i+'\',\'bearish\')">▼</button>'+
      '</div>'+
      '<div class="card-body">'+
        '<div class="card-header">'+
          '<span class="level-badge" style="background:'+lvColor+'15;color:'+lvColor+'">'+lvLabel+'</span>'+
          '<span class="source-badge">'+esc(a.source||'')+'</span>'+
          coinHtml+
          (timeStr?'<span class="time-tag">'+esc(timeStr)+'</span>':'')+
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
          '<button class="expand-btn" onclick="toggleExpand('+i+')"><span class="arrow">▾</span> AI分析</button>'+
        '</div>'+
      '</div>';
    
    // Animation delay queue
    setTimeout(function(){list.appendChild(card)},i*20);
  });
  
  // Still need the final count update after all cards appended
  setTimeout(updateCount,ARTICLES_DATA.length*20+100);
  updateSidebarMobile();
}

function toggleExpand(i){
  var cards=document.getElementById('news-list').querySelectorAll('.card');
  var card=cards[i];
  if(card)card.classList.toggle('expanded');
}

// ===== Filters =====
function updateCount(){
  var visible=document.getElementById('news-list').querySelectorAll('.card:not(.hidden)').length;
  $('feed-count').textContent=visible+' / '+ARTICLES_DATA.length+' 条';
}

function filterByLevel(lv){
  document.querySelectorAll('.stat-item').forEach(function(b){b.classList.remove('active')});
  if(lv!=='ALL')document.querySelectorAll('.stat-item').forEach(function(b){if(b.classList.contains('stat-'+lv))b.classList.add('active')});
  else document.querySelectorAll('.stat-item')[0].classList.add('active');
  currentLevel=lv;
  applyFilters();
}

function filterByCoin(coin){
  document.querySelectorAll('.coin-pill').forEach(function(b){b.classList.remove('active')});
  document.querySelectorAll('.coin-pill').forEach(function(b){if(b.textContent.trim()===coin)b.classList.add('active')});
  currentCoin=coin;
  applyFilters();
}

function doSearch(q){
  searchQuery=q.toLowerCase();
  applyFilters();
}

function setSort(mode){
  currentSort=mode;
  document.querySelectorAll('.sort-btn').forEach(function(b){b.classList.remove('active')});
  document.getElementById('sort-'+mode).classList.add('active');
  buildCards();
}

function applyFilters(){
  // Just filter existing cards, don't rebuild
  var cards=document.querySelectorAll('.card');
  cards.forEach(function(c){
    var idx=parseInt(c.dataset.i);
    var a=ARTICLES_DATA[idx];
    if(!a){c.classList.add('hidden');return}
    var show=true;
    if(currentLevel!=='ALL'&&a.level!==currentLevel)show=false;
    if(currentCoin!=='ALL'&&!(a.coins||[]).includes(currentCoin)&&!(a.coins||[]).includes('ALL'))show=false;
    if(searchQuery&&!(a.title||'').toLowerCase().includes(searchQuery))show=false;
    c.classList.toggle('hidden',!show);
  });
  updateCount();
}

// ===== Voting =====
var voted={};
function vote(idx,type){
  var key=idx+'-'+type;
  var el=$('vote-'+type+'-'+idx);
  if(!el)return;
  // We don't have per-vote display in v0.5, using the data object
  // For now toggle visual state only
  var cards=document.querySelectorAll('.card');
  var btns=cards[parseInt(idx)].querySelectorAll('.vote-btn');
  btns.forEach(function(b){b.classList.remove('voted')});
  
  if(voted[key]){voted[key]=false;return}
  voted[key]=true;
  // Clear previous votes for this card
  ['bullish','bearish','important'].forEach(function(t){
    var k=idx+'-'+t;
    if(k!==key&&voted[k])voted[k]=false
  });
  
  var btnMap={bullish:'up',bearish:'down',important:'imp'};
  var cls=btnMap[type]||'';
  cards[parseInt(idx)].querySelectorAll('.vote-btn').forEach(function(b){
    if(b.classList.contains(cls))b.classList.add('voted')
  });
  
  // Flash effect
  var colors={bullish:'#3fb950',bearish:'#f85149',important:'#ffd700'};
  btns.forEach(function(b){if(b.classList.contains(cls)){b.style.color=colors[type];setTimeout(function(){b.style.color=''},600)}});
}

// ===== Mobile Sidebar =====
function toggleMobileSidebar(){
  $('sidebar-overlay').classList.toggle('open');
  $('sidebar-mobile').classList.toggle('open');
}

function updateSidebarMobile(){
  var m=$('sidebar-mobile');
  m.innerHTML=$('sidebar-desktop').innerHTML;
}

// ===== Auto Refresh =====
setTimeout(function(){location.reload()},1800000);

// ===== Status =====
function showStatus(msg){
  var el=$('update-status');
  el.textContent=msg;
  el.classList.add('show');
  clearTimeout(el._hide);
  el._hide=setTimeout(function(){el.classList.remove('show')},3000);
}
