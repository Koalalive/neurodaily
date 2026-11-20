"""Settings GUI page for NeuroDaily (dependency-free vanilla JS)."""

DASHBOARD_SETTINGS_LINK = (
    '<a href="/settings" style="position:fixed;top:12px;right:16px;z-index:9999;'
    'background:#171f2f;border:1px solid #38bdf8;color:#38bdf8;padding:6px 12px;'
    'border-radius:8px;text-decoration:none;font:600 13px -apple-system,Segoe UI,sans-serif;">'
    "⚙ Settings</a>"
)

SETTINGS_HTML = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
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
<header><h1>⚙ NeuroDaily Settings</h1><a href="/">← Back to dashboard</a><span class="mini" id="cfgpath"></span></header>
<main>
  <section>
    <h2>General</h2>
    <div class="row"><input id="profile" placeholder="profile (e.g. neuro)"></div>
  </section>

  <section>
    <h2>Disciplines (focus areas)</h2>
    <p class="desc">One discipline per row; separate categories and keywords with commas.</p>
    <div id="disciplines"></div>
    <button onclick="addDiscipline()">+ Add discipline</button>
  </section>

  <section>
    <h2>Global keywords</h2>
    <input id="global_keywords" placeholder="brain, neuro, EEG, fMRI ...">
  </section>

  <section>
    <h2>Sources</h2>
    <p class="desc">Enable, max results per fetch, lookback days.</p>
    <div id="sources"></div>
  </section>

  <section>
    <h2>Output</h2>
    <div class="grid2">
      <div><label>Report directory</label><input id="out_dir"></div>
      <div><label>Filename format</label><input id="out_fmt"></div>
    </div>
    <div class="inline" style="margin-top:10px"><label><input type="checkbox" id="out_open"> Open report when finished</label></div>
  </section>

  <section>
    <h2>Retrieval windows</h2>
    <p class="desc">Only items inside each window are shown; daily and manual runs can differ (hours).</p>
    <div class="grid2">
      <div><label>Daily: paper hours</label><input type="number" id="win_daily" min="1" max="720"></div>
      <div><label>Manual: paper hours</label><input type="number" id="win_manual" min="1" max="8760"></div>
      <div><label>Trials: hours</label><input type="number" id="win_trials" min="1" max="8760"></div>
      <div><label>Funding: hours</label><input type="number" id="win_funding" min="1" max="8760"></div>
      <div><label>News / policy: hours</label><input type="number" id="win_news" min="1" max="8760"></div>
    </div>
  </section>

  <section>
    <h2>Schedule</h2>
    <div class="inline">
      <label><input type="checkbox" id="sch_enabled"> Enable schedule</label>
      <span class="mini">Time</span>
      <input type="number" id="sch_hour" min="0" max="23"> :
      <input type="number" id="sch_minute" min="0" max="59">
    </div>
    <div class="inline" style="margin-top:10px">
      <label><input type="checkbox" id="otd_enabled"> Include "On This Day"</label>
      <label><input type="checkbox" id="otd_notify"> Desktop notification daily</label>
    </div>
    <div class="inline" style="margin-top:10px">
      <label>"On This Day" language</label>
      <select id="otd_lang" style="width:160px">
        <option value="zh">Chinese</option>
        <option value="en">English</option>
        <option value="ru">Русский</option>
      </select>
    </div>
    <div class="inline" style="margin-top:12px">
      <span class="pill" id="ldstat">Scheduler: …</span>
      <button onclick="launchd('install')">Install / update schedule</button>
      <button class="warn" onclick="launchd('uninstall')">Uninstall schedule</button>
    </div>
    <p class="hint">After changing the time, click Install / update schedule to apply.</p>
  </section>

  <section>
    <h2>Policy / news RSS</h2>
    <div id="policy_feeds"></div>
    <button onclick="addFeed()">+ Add RSS</button>
  </section>

  <section>
    <h2>Top journals watch-list</h2>
    <p class="desc">Journals with RSS are fetched and pinned to the papers section.</p>
    <div id="journals"></div>
    <button onclick="addJournal()">+ Add journal</button>
  </section>

  <section>
    <h2>Push settings (email / webhook)</h2>
    <p class="desc">After saving, click "Save & run now" at the bottom to fetch and push.</p>
    <div class="inline"><label><input type="checkbox" id="push_email_enabled"> Enable email</label>
      <label><input type="checkbox" id="push_attach" checked> Attach full HTML</label></div>
    <div style="margin-top:8px"><label>Recipients (comma or newline separated)</label>
      <textarea id="push_to" rows="3" style="width:100%;background:#161616;border:1px solid #262626;color:#e8e8e8;border-radius:8px;padding:8px"></textarea></div>
    <div class="grid2" style="margin-top:8px">
      <div><label>SMTP host</label><input id="push_host"></div>
      <div><label>Port</label><input type="number" id="push_port"></div>
      <div><label>Username</label><input id="push_user"></div>
      <div><label>From</label><input id="push_from"></div>
    </div>
    <div class="inline" style="margin-top:8px"><label>Subject template</label><input id="push_subject" style="flex:1"></div>
    <div class="inline" style="margin-top:8px"><label>SMTP app password</label>
      <input type="password" id="push_password" placeholder="Leave blank to keep" style="flex:1">
      <span class="mini" id="push_pw_state"></span></div>
    <div class="grid2" style="margin-top:8px">
      <div><label>Feishu webhook</label><input id="push_feishu"></div>
      <div><label>WeCom webhook</label><input id="push_wecom"></div>
    </div>
  </section>

  <section>
    <h2>Reset</h2>
    <p class="desc">Reset config to built-in defaults (overwrites current settings).</p>
    <button class="warn" onclick="resetDefaults()">Reset to defaults</button>
  </section>
</main>
<footer>
  <button class="primary" id="saveRun" onclick="saveAndRun()">Save & run now</button>
  <button onclick="save()">Save only</button>
  <button onclick="load()">Reload</button>
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
  d.innerHTML='<input class="d-name" placeholder="Discipline name" value="'+esc(x.name)+'">'+
    '<input class="d-arxiv" placeholder="arXiv categories" value="'+esc(csv(x.arxiv_cats))+'">'+
    '<input class="d-mesh" placeholder="PubMed MeSH" value="'+esc(csv(x.mesh_terms))+'">'+
    '<input class="d-bio" placeholder="bioRxiv categories" value="'+esc(csv(x.bio_cats))+'">'+
    '<input class="d-kw" placeholder="Keywords" value="'+esc(csv(x.keywords))+'">'+
    '<label><input type="checkbox" class="d-en" '+(x.enabled!==false?'checked':'')+'> On</label>'+
    '<button class="del" onclick="this.closest(\'.row\').remove()">✕</button>';
  return d;
}
function addDiscipline(){el('disciplines').appendChild(disciplineRow({}));}

function sourceRow(k,o){
  o=o||{}; var d=document.createElement('div'); d.className='row src'; d.dataset.key=k;
  d.innerHTML='<b>'+esc(k)+'</b>'+
    '<label><input type="checkbox" class="s-en" '+(o.enabled!==false?'checked':'')+'> On</label>'+
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
  d.innerHTML='<input class="j-name" placeholder="Journal name" value="'+esc(x.name)+'">'+
    '<input class="j-url" placeholder="Website URL" value="'+esc(x.url)+'">'+
    '<input class="j-rss" placeholder="RSS (optional)" value="'+esc(x.rss)+'">'+
    '<input class="j-cat" placeholder="Category" value="'+esc(x.category)+'">'+
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
  el('otd_lang').value = otd.lang || 'zh';
  var w = BASE.windows || {};
  el('win_daily').value = (w.daily_paper_hours != null ? w.daily_paper_hours : 36);
  el('win_manual').value = (w.manual_paper_hours != null ? w.manual_paper_hours : 168);
  el('win_trials').value = (w.trials_hours != null ? w.trials_hours : 36);
  el('win_funding').value = (w.funding_hours != null ? w.funding_hours : 36);
  el('win_news').value = (w.news_hours != null ? w.news_hours : 36);
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
  }catch(e){el('msg').textContent='Load failed: '+e; el('msg').className='bad';}
  loadPush();
  loadLaunchdStatus();
  try{
    if(new URLSearchParams(location.search).get('next')==='run'){
      el('saveRun').scrollIntoView({block:'center'});
      el('saveRun').style.boxShadow='0 0 0 3px rgba(56,189,248,.5)';
    }
  }catch(e){}
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
  data.scheduled.on_this_day={enabled:el('otd_enabled').checked,notify:el('otd_notify').checked,
    lang:el('otd_lang').value};
  data.windows=Object.assign({},data.windows||{});
  data.windows.daily_paper_hours=parseInt(el('win_daily').value||'36',10);
  data.windows.manual_paper_hours=parseInt(el('win_manual').value||'168',10);
  data.windows.trials_hours=parseInt(el('win_trials').value||'36',10);
  data.windows.funding_hours=parseInt(el('win_funding').value||'36',10);
  data.windows.news_hours=parseInt(el('win_news').value||'36',10);
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
  el('msg').textContent='Saving…'; el('msg').className='';
  try{
    var r=await fetch('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
    var out=await r.json();
    if(out.ok){el('msg').textContent='✅ Saved → '+out.path; el('msg').className='ok'; return true;}
    el('msg').textContent='❌ Save failed: '+(out.error||'unknown'); el('msg').className='bad'; return false;
  }catch(e){el('msg').textContent='❌ '+e; el('msg').className='bad'; return false;}
}

async function resetDefaults(){
  if(!confirm('Reset to defaults? This overwrites current settings.')) return;
  var r=await fetch('/api/config/reset',{method:'POST'});
  var out=await r.json();
  if(out.ok){await load(); el('msg').textContent='✅ Reset to defaults'; el('msg').className='ok';}
  else{el('msg').textContent='❌ Reset failed'; el('msg').className='bad';}
}

async function loadLaunchdStatus(){
  try{
    var r=await fetch('/api/launchd/status'); var s=await r.json();
    var t='Scheduler: '+(s.loaded?'loaded':'not loaded')+(s.installed?' / installed':' / not installed')+'（'+s.schedule+'）';
    el('ldstat').textContent=t;
    el('ldstat').className='pill'+(s.loaded?' on':'');
  }catch(e){el('ldstat').textContent='Scheduler: read failed';}
}

async function launchd(action){
  if(action==='uninstall' && !confirm('Uninstall schedule？')) return;
  el('msg').textContent='Working…'; el('msg').className='';
  var r=await fetch('/api/launchd/'+action,{method:'POST'});
  var out=await r.json();
  el('msg').textContent = out.ok ? ('✅ '+(action==='install'?'installed/updated':'Uninstalled')) : '❌ Action failed';
  el('msg').className = out.ok?'ok':'bad';
  loadPush();
  loadLaunchdStatus();
  try{
    if(new URLSearchParams(location.search).get('next')==='run'){
      el('saveRun').scrollIntoView({block:'center'});
      el('saveRun').style.boxShadow='0 0 0 3px rgba(56,189,248,.5)';
    }
  }catch(e){}
}

function pushPayload(){
  return {email:{enabled:el('push_email_enabled').checked,
      to:el('push_to').value,
      smtp_host:el('push_host').value.trim(),
      smtp_port:parseInt(el('push_port').value||'587',10),
      username:el('push_user').value.trim(),
      from:el('push_from').value.trim(),
      subject_template:el('push_subject').value.trim(),
      attach_report:el('push_attach').checked},
    webhooks:{feishu:el('push_feishu').value.trim(),
      wecom:el('push_wecom').value.trim()}};
}
async function loadPush(){
  try{
    var d=await (await fetch('/api/push')).json();
    var e=d.email||{};
    el('push_email_enabled').checked=e.enabled!==false;
    el('push_to').value=(e.to||[]).join('\n');
    el('push_host').value=e.smtp_host||'';
    el('push_port').value=e.smtp_port||587;
    el('push_user').value=e.username||'';
    el('push_from').value=e.from||'';
    el('push_subject').value=e.subject_template||'';
    el('push_attach').checked=e.attach_report!==false;
    el('push_pw_state').textContent=d.password_set?'(set)':'(not set)';
    var w=d.webhooks||{};
    el('push_feishu').value=w.feishu||'';
    el('push_wecom').value=w.wecom||'';
  }catch(e){}
}
async function savePush(){
  var r=await fetch('/api/push',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(pushPayload())});
  var out=await r.json();
  if(!out.ok) throw new Error(out.error||'Failed to save push settings');
  var pw=el('push_password').value;
  if(pw){
    var r2=await fetch('/api/push/password',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:pw})});
    var o2=await r2.json();
    if(!o2.ok) throw new Error(o2.error||'Failed to save password');
    el('push_password').value=''; el('push_pw_state').textContent='(set)';
  }
}
async function saveAndRun(){
  el('msg').textContent='Saving and starting…'; el('msg').className='';
  try{
    var okc=await save(); if(okc===false) throw new Error('Failed to save config');
    await savePush();
    var r=await fetch('/api/run?force=1',{method:'POST'});
    var d=await r.json(); var started=d.started_at;
    el('msg').textContent='Fetching… (about 2–4 minutes)';
    var timer=setInterval(async function(){
      try{
        var s=await (await fetch('/api/status')).json();
        if(s.last_run && s.last_run>=started){
          clearInterval(timer);
          el('msg').className='ok';
          el('msg').innerHTML='✅ Done ('+s.item_count+' items) · report opened locally · <a href="/report/latest" target="_blank">Open again</a>';
        }
      }catch(e){}
    },2000);
  }catch(e){ el('msg').className='bad'; el('msg').textContent='❌ '+e; }
}

load();
</script>
</body></html>
"""
