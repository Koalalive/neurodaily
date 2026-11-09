"""Settings GUI page for NeuroDaily (dependency-free vanilla JS)."""

DASHBOARD_SETTINGS_LINK = (
    '<a href="/settings" style="position:fixed;top:12px;right:16px;z-index:9999;'
    'background:#171f2f;border:1px solid #38bdf8;color:#38bdf8;padding:6px 12px;'
    'border-radius:8px;text-decoration:none;font:600 13px -apple-system,Segoe UI,sans-serif;">'
    "⚙ Settings</a>"
)

SETTINGS_HTML = r"""<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>NeuroDaily — Settings</title>
<style>
:root{--bg:#000;--panel:#0f0f0f;--panel2:#161616;--line:#262626;--accent:#38bdf8;--accent2:#818cf8;--text:#e8e8e8;--muted:#8a8a8a}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif}
header{position:sticky;top:0;background:#000;border-bottom:1px solid var(--line);padding:16px 24px;display:flex;align-items:center;gap:16px;z-index:10}
h1{margin:0;font-size:1.2rem;color:var(--accent)}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
main{max-width:1100px;margin:0 auto;padding:24px}
section{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px 18px;margin-bottom:18px}
h2{margin:0 0 4px;font-size:1rem;color:var(--text)}
.desc{color:var(--muted);font-size:.8rem;margin:0 0 12px}
label{font-size:.82rem;color:var(--muted)}
input,select{background:var(--panel2);border:1px solid var(--line);color:var(--text);border-radius:8px;padding:7px 9px;font-size:.85rem;width:100%}
input[type=checkbox]{width:auto;vertical-align:middle}
input:focus{outline:none;border-color:var(--accent)}
.row{display:flex;gap:8px;align-items:center;margin:6px 0;flex-wrap:wrap}
.row.grid{display:grid;grid-template-columns:1.1fr 1fr 1fr 1fr 1.2fr auto auto;gap:6px}
.row.src{display:grid;grid-template-columns:1.2fr auto 90px 100px;gap:8px}
.row.j{display:grid;grid-template-columns:1fr 1.4fr 1.4fr .8fr auto;gap:6px}
.row.feed{display:flex}
.inline{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.inline input[type=number]{width:80px}
button{background:var(--panel2);color:var(--accent);border:1px solid var(--line);border-radius:8px;padding:7px 12px;font-size:.82rem;cursor:pointer}
button:hover{border-color:var(--accent)}
button.del{color:#f87171;border-color:#3a1a1a;padding:6px 9px}
button.primary{background:linear-gradient(90deg,var(--accent),var(--accent2));color:#04121c;border:none;font-weight:700;padding:9px 22px}
button.warn{border-color:#7a2b2b;color:#fca5a5}
.mini{color:var(--muted);font-size:.78rem}
.hint{color:var(--muted);font-size:.75rem;margin-top:6px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media(max-width:820px){.row.grid,.row.j,.row.src{grid-template-columns:1fr}.grid2{grid-template-columns:1fr}}
footer{position:sticky;bottom:0;background:#000;border-top:1px solid var(--line);padding:12px 24px;display:flex;gap:12px;align-items:center}
#msg{font-size:.84rem}
#msg.ok{color:#34d399}#msg.bad{color:#f87171}
.pill{background:var(--panel2);border:1px solid var(--line);border-radius:999px;padding:3px 10px;font-size:.75rem;color:var(--muted)}
.pill.on{color:#34d399;border-color:#164e3a}
</style></head>
<body>
<header><h1>⚙ NeuroDaily 设置</h1><a href="/">← 返回仪表盘</a><span class="mini" id="cfgpath"></span></header>
<main>
  <section>
    <h2>基本</h2>
    <div class="row"><input id="profile" placeholder="profile (如 neuro)"></div>
  </section>

  <section>
    <h2>学科（关注方向）</h2>
    <p class="desc">每行一个学科；分类/关键词用英文逗号分隔。</p>
    <div id="disciplines"></div>
    <button onclick="addDiscipline()">+ 添加学科</button>
  </section>

  <section>
    <h2>全局关键词</h2>
    <input id="global_keywords" placeholder="brain, neuro, EEG, fMRI ...">
  </section>

  <section>
    <h2>数据源</h2>
    <p class="desc">启用开关、每次抓取上限、回看天数。</p>
    <div id="sources"></div>
  </section>

  <section>
    <h2>输出</h2>
    <div class="grid2">
      <div><label>报告目录</label><input id="out_dir"></div>
      <div><label>文件名格式</label><input id="out_fmt"></div>
    </div>
    <div class="inline" style="margin-top:10px"><label><input type="checkbox" id="out_open"> 跑完自动打开报告</label></div>
  </section>

  <section>
    <h2>每日定时任务</h2>
    <div class="inline">
      <label><input type="checkbox" id="sch_enabled"> 启用定时</label>
      <span class="mini">时间</span>
      <input type="number" id="sch_hour" min="0" max="23"> :
      <input type="number" id="sch_minute" min="0" max="59">
    </div>
    <div class="inline" style="margin-top:10px">
      <label><input type="checkbox" id="otd_enabled"> 报告含「历史上的今天」</label>
      <label><input type="checkbox" id="otd_notify"> 每天弹桌面通知</label>
    </div>
    <div class="inline" style="margin-top:12px">
      <span class="pill" id="ldstat">定时状态：…</span>
      <button onclick="launchd('install')">安装/更新定时任务</button>
      <button class="warn" onclick="launchd('uninstall')">卸载定时任务</button>
    </div>
    <p class="hint">改动时间后需点「安装/更新定时任务」才生效。</p>
  </section>

  <section>
    <h2>政策 / 新闻 RSS</h2>
    <div id="policy_feeds"></div>
    <button onclick="addFeed()">+ 添加 RSS</button>
  </section>

  <section>
    <h2>顶级期刊观察列表</h2>
    <p class="desc">有 RSS 的期刊会被抓取并置顶到论文区。</p>
    <div id="journals"></div>
    <button onclick="addJournal()">+ 添加期刊</button>
  </section>

  <section>
    <h2>恢复默认</h2>
    <p class="desc">把配置重置为内置默认值（会覆盖当前设置）。</p>
    <button class="warn" onclick="resetDefaults()">重置为默认配置</button>
  </section>
</main>
<footer>
  <button class="primary" onclick="save()">保存</button>
  <button onclick="load()">重新载入</button>
  <span id="msg"></span>
</footer>
<script>
var BASE=null;
function el(id){return document.getElementById(id);}
function esc(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
function csv(a){return (a||[]).join(', ');}
function split(s){return (s||'').split(',').map(function(x){return x.trim();}).filter(Boolean);}

function disciplineRow(x){
  x=x||{}; var d=document.createElement('div'); d.className='row grid';
  d.innerHTML='<input class="d-name" placeholder="学科名" value="'+esc(x.name)+'">'+
    '<input class="d-arxiv" placeholder="arXiv 分类" value="'+esc(csv(x.arxiv_cats))+'">'+
    '<input class="d-mesh" placeholder="PubMed MeSH" value="'+esc(csv(x.mesh_terms))+'">'+
    '<input class="d-bio" placeholder="bioRxiv 分类" value="'+esc(csv(x.bio_cats))+'">'+
    '<input class="d-kw" placeholder="关键词" value="'+esc(csv(x.keywords))+'">'+
    '<label><input type="checkbox" class="d-en" '+(x.enabled!==false?'checked':'')+'> 启用</label>'+
    '<button class="del" onclick="this.closest(\'.row\').remove()">✕</button>';
  return d;
}
function addDiscipline(){el('disciplines').appendChild(disciplineRow({}));}

function sourceRow(k,o){
  o=o||{}; var d=document.createElement('div'); d.className='row src'; d.dataset.key=k;
  d.innerHTML='<b>'+esc(k)+'</b>'+
    '<label><input type="checkbox" class="s-en" '+(o.enabled!==false?'checked':'')+'> 启用</label>'+
    '<input type="number" class="s-max" title="max_results" value="'+(o.max_results!=null?o.max_results:20)+'">'+
    '<input type="number" class="s-look" title="lookback_days" value="'+(o.lookback_days!=null?o.lookback_days:1)+'">';
  return d;
}
function feedRow(u){
  var d=document.createElement('div'); d.className='row feed';
  d.innerHTML='<input class="feed" value="'+esc(u)+'">'+
    '<button class="del" onclick="this.closest(\'.row\').remove()">✕</button>';
  return d;
}
function addFeed(){el('policy_feeds').appendChild(feedRow(''));}

function journalRow(x){
  x=x||{}; var d=document.createElement('div'); d.className='row j';
  d.innerHTML='<input class="j-name" placeholder="期刊名" value="'+esc(x.name)+'">'+
    '<input class="j-url" placeholder="官网 URL" value="'+esc(x.url)+'">'+
    '<input class="j-rss" placeholder="RSS (可空)" value="'+esc(x.rss)+'">'+
    '<input class="j-cat" placeholder="分类" value="'+esc(x.category)+'">'+
    '<button class="del" onclick="this.closest(\'.row\').remove()">✕</button>';
  return d;
}
function addJournal(){el('journals').appendChild(journalRow({category:'neuroscience'}));}

function render(){
  el('profile').value=BASE.profile||'';
  var dbox=el('disciplines'); dbox.innerHTML='';
  (BASE.disciplines||[]).forEach(function(x){dbox.appendChild(disciplineRow(x));});
  el('global_keywords').value=csv(BASE.global_keywords);
  var sbox=el('sources'); sbox.innerHTML='';
  Object.keys(BASE.sources||{}).forEach(function(k){sbox.appendChild(sourceRow(k,BASE.sources[k]));});
  var o=BASE.output||{};
  el('out_dir').value=o.dir||''; el('out_fmt').value=o.filename_format||''; el('out_open').checked=!!o.open_on_finish;
  var sc=BASE.scheduled||{}; var otd=sc.on_this_day||{};
  el('sch_enabled').checked=!!sc.enabled;
  el('sch_hour').value=(sc.hour!=null?sc.hour:8); el('sch_minute').value=(sc.minute!=null?sc.minute:0);
  el('otd_enabled').checked=(otd.enabled!==false); el('otd_notify').checked=(otd.notify!==false);
  var pbox=el('policy_feeds'); pbox.innerHTML='';
  (BASE.policy_feeds||[]).forEach(function(u){pbox.appendChild(feedRow(u));});
  var jbox=el('journals'); jbox.innerHTML='';
  (BASE.journals||[]).forEach(function(x){jbox.appendChild(journalRow(x));});
}

async function load(){
  try{
    var r=await fetch('/api/config'); BASE=await r.json(); render();
    el('cfgpath').textContent='config: ~/neurodaily/config/config.json';
    el('msg').textContent=''; el('msg').className='';
  }catch(e){el('msg').textContent='加载失败: '+e; el('msg').className='bad';}
  loadLaunchdStatus();
}

function collect(){
  var data=JSON.parse(JSON.stringify(BASE||{}));
  data.profile=el('profile').value.trim();
  data.disciplines=[].slice.call(el('disciplines').querySelectorAll('.row')).map(function(r){
    return {name:r.querySelector('.d-name').value.trim(),
      arxiv_cats:split(r.querySelector('.d-arxiv').value),
      mesh_terms:split(r.querySelector('.d-mesh').value),
      bio_cats:split(r.querySelector('.d-bio').value),
      keywords:split(r.querySelector('.d-kw').value),
      enabled:r.querySelector('.d-en').checked};
  }).filter(function(x){return x.name;});
  data.global_keywords=split(el('global_keywords').value);
  data.sources={};
  [].slice.call(el('sources').querySelectorAll('.row')).forEach(function(r){
    data.sources[r.dataset.key]={enabled:r.querySelector('.s-en').checked,
      max_results:parseInt(r.querySelector('.s-max').value||'0',10),
      lookback_days:parseInt(r.querySelector('.s-look').value||'1',10)};
  });
  data.output=Object.assign({},data.output||{});
  data.output.dir=el('out_dir').value.trim();
  data.output.filename_format=el('out_fmt').value.trim();
  data.output.open_on_finish=el('out_open').checked;
  data.scheduled=Object.assign({},data.scheduled||{});
  data.scheduled.enabled=el('sch_enabled').checked;
  data.scheduled.hour=parseInt(el('sch_hour').value||'8',10);
  data.scheduled.minute=parseInt(el('sch_minute').value||'0',10);
  data.scheduled.on_this_day={enabled:el('otd_enabled').checked,notify:el('otd_notify').checked};
  data.policy_feeds=[].slice.call(el('policy_feeds').querySelectorAll('.feed')).map(function(i){return i.value.trim();}).filter(Boolean);
  data.journals=[].slice.call(el('journals').querySelectorAll('.row')).map(function(r){
    return {name:r.querySelector('.j-name').value.trim(),
      url:r.querySelector('.j-url').value.trim(),
      rss:r.querySelector('.j-rss').value.trim(),
      category:r.querySelector('.j-cat').value.trim()};
  }).filter(function(x){return x.name;});
  return data;
}

async function save(){
  var data=collect();
  el('msg').textContent='保存中…'; el('msg').className='';
  try{
    var r=await fetch('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
    var out=await r.json();
    if(out.ok){el('msg').textContent='✅ 已保存 → '+out.path; el('msg').className='ok';}
    else{el('msg').textContent='❌ 保存失败: '+(out.error||'unknown'); el('msg').className='bad';}
  }catch(e){el('msg').textContent='❌ '+e; el('msg').className='bad';}
}

async function resetDefaults(){
  if(!confirm('确定重置为默认配置？（会覆盖当前设置）')) return;
  var r=await fetch('/api/config/reset',{method:'POST'});
  var out=await r.json();
  if(out.ok){await load(); el('msg').textContent='✅ 已重置为默认'; el('msg').className='ok';}
  else{el('msg').textContent='❌ 重置失败'; el('msg').className='bad';}
}

async function loadLaunchdStatus(){
  try{
    var r=await fetch('/api/launchd/status'); var s=await r.json();
    var t='定时状态：'+(s.loaded?'已装载':'未装载')+(s.installed?' / 已安装':' / 未安装')+'（'+s.schedule+'）';
    el('ldstat').textContent=t;
    el('ldstat').className='pill'+(s.loaded?' on':'');
  }catch(e){el('ldstat').textContent='定时状态：读取失败';}
}

async function launchd(action){
  if(action==='uninstall' && !confirm('卸载定时任务？')) return;
  el('msg').textContent='处理中…'; el('msg').className='';
  var r=await fetch('/api/launchd/'+action,{method:'POST'});
  var out=await r.json();
  el('msg').textContent = out.ok ? ('✅ '+(action==='install'?'已安装/更新':'已卸载')) : '❌ 操作失败';
  el('msg').className = out.ok?'ok':'bad';
  loadLaunchdStatus();
}

load();
</script>
</body></html>
"""
