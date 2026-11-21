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
input,select,textarea{background:var(--panel2);border:1px solid var(--line);color:var(--text);border-radius:8px;padding:7px 9px;font-size:.85rem;width:100%}
input[type=checkbox]{width:auto;vertical-align:middle}
input:focus{outline:none;border-color:var(--accent)}
.row{display:flex;gap:8px;align-items:center;margin:6px 0;flex-wrap:wrap}
.row.grid{display:grid;grid-template-columns:1.1fr 1fr 1fr 1fr 1.2fr auto auto;gap:6px}
.row.src{display:grid;grid-template-columns:1.2fr auto 90px 100px;gap:8px}
.row.j{display:grid;grid-template-columns:1fr 1.4fr 1.4fr .8fr .7fr .6fr .7fr auto;gap:6px}
.row.j .j-aliases{grid-column:1 / 5}
.row.j .j-issns{grid-column:5 / -1}
.row.feed{display:flex}
.inline{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.inline input[type=number]{width:80px}
button{background:var(--panel2);color:var(--accent);border:1px solid var(--line);border-radius:8px;padding:7px 12px;font-size:.82rem;cursor:pointer}
button:hover{border-color:var(--accent)}
button[aria-pressed=true]{border-color:var(--accent);background:#172334}
button:disabled{opacity:.6;cursor:default}
button.del{color:#f87171;border-color:#3a1a1a;padding:6px 9px}
button.primary{background:linear-gradient(90deg,var(--accent),var(--accent2));color:#04121c;border:none;font-weight:700;padding:9px 22px}
button.warn{border-color:#7a2b2b;color:#fca5a5}
.mini{color:var(--muted);font-size:.78rem}
.hint{color:var(--muted);font-size:.75rem;margin-top:6px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media(max-width:820px){
  .row.grid,.row.j,.row.src,.grid2{grid-template-columns:1fr}
  .row.j .j-aliases,.row.j .j-issns{grid-column:auto}
}
.search-controls{display:grid;gap:12px}
.search-controls label{color:var(--text)}
.search-controls :is(input,select,button,summary,textarea):focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.search-controls textarea{display:block;resize:vertical;font-family:ui-monospace,monospace;line-height:1.5}
.search-tools{min-width:0;border:1px solid var(--line);border-radius:8px;padding:8px 12px}
.search-tools>summary,.search-preview summary{cursor:pointer;overflow-wrap:anywhere}
.search-tools[open]>summary{margin-bottom:8px}
.search-group{min-width:0;margin:8px 0;padding:8px 10px;border:1px solid var(--line);border-radius:8px}
.search-group legend{font-size:.8rem;color:var(--muted)}
.search-tools .inline select{width:auto;max-width:100%}
.search-term,.search-set{display:grid;align-items:center;gap:6px;margin:6px 0}
.search-term{grid-template-columns:minmax(130px,1fr) minmax(107px,.8fr) minmax(100px,2fr) auto}
.search-set{grid-template-columns:auto minmax(0,1fr) auto auto}
.search-set input{font-family:ui-monospace,monospace}
.search-preview{display:grid;gap:8px;min-width:0;overflow-wrap:anywhere}
.search-preview:empty{display:none}
.search-preview p,.search-preview ul{margin:6px 0}
.search-preview pre{margin:6px 0;white-space:pre-wrap;overflow-wrap:anywhere;color:var(--muted)}
.search-preview .source-details{border-top:1px solid var(--line);padding-top:8px}
#search_preview_status[data-state="error"]{color:#f87171}
@media(max-width:620px){
  .search-term{grid-template-columns:minmax(0,1fr) minmax(0,1fr)}
  .search-set{grid-template-columns:auto minmax(0,1fr) auto}
  .search-set .set-expression{grid-row:1;grid-column:2/-1}
}
footer{position:sticky;bottom:0;background:#000;border-top:1px solid var(--line);padding:12px 24px;display:flex;gap:12px;align-items:center}
[hidden]{display:none!important}
#msg{font-size:.84rem}
#msg.ok{color:#34d399}#msg.bad{color:#f87171}
.pill{background:var(--panel2);border:1px solid var(--line);border-radius:999px;padding:3px 10px;font-size:.75rem;color:var(--muted)}
.pill.on{color:#34d399;border-color:#164e3a}
</style></head>
<body>
<header><h1>⚙ NeuroDaily Settings</h1><a href="/">← Back to dashboard</a><span class="mini" id="cfgpath"></span></header>
<main>
  <section>
    <h2>配置文件</h2>
    <div class="inline">
      <a href="/api/config/export" download>导出已保存的配置</a>
      <button type="button" onclick="document.getElementById('profile_file').click()">导入配置文件</button>
      <input id="profile_file" type="file" accept=".json,application/json" hidden onchange="previewProfileFile(this)">
      <button id="apply_profile" type="button" hidden onclick="applyProfileFile()">确认导入</button>
    </div>
    <p class="desc">分享学科、检索规则、期刊和数据源设置。邮件、Webhook 和本机路径由各自设备管理。</p>
    <p id="profile_import_status" role="status" aria-live="polite"></p>
  </section>
  <section>
    <h2>Research presets</h2>
    <div id="research_presets" class="inline" role="group" aria-label="Research presets"></div>
    <p class="hint" id="preset_status" role="status">A preset fills the research fields. Review them before saving.</p>
  </section>
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

  <section aria-labelledby="advanced_search_title">
    <h2 id="advanced_search_title">Advanced literature search</h2>
    <p class="desc">Build a query for this research profile and preview how each source applies it.</p>
    <div class="search-controls">
      <details class="search-tools" id="search_builder">
        <summary>Build with conditions</summary>
        <div class="inline">
          <label for="search_group_operator">Include groups</label>
          <select id="search_group_operator">
            <option value="AND">Match all groups</option>
            <option value="OR">Match any group</option>
          </select>
        </div>
        <div id="search_groups"></div>
        <div class="inline">
          <button type="button" id="search_add_group">+ Add group</button>
          <button type="button" id="search_apply_conditions">Add to expression</button>
          <button type="button" id="search_save_conditions">Create search set</button>
        </div>
        <p class="hint">Added conditions are joined to the current expression with AND.</p>
        <p class="hint" id="search_builder_status" role="status"></p>
      </details>

      <div>
        <label for="search_query">Search expression</label>
        <textarea id="search_query" rows="3" spellcheck="false" aria-describedby="search_query_help"
          placeholder='TI="working memory" AND (TIAB=EEG OR TIAB=electroencephalography)'></textarea>
        <p class="hint" id="search_query_help">Use <code>AND</code>, <code>OR</code>, <code>NOT</code>, parentheses, <code>TI="working memory"</code>, <code>TIAB=EEG NEAR/5 TIAB=memory</code>, or <code>PY=2024-2026</code>. For a keyword search, clear the expression and keep all journals.</p>
      </div>

      <details class="search-tools" id="search_sets_panel">
        <summary>Numbered search sets</summary>
        <div id="search_sets"></div>
        <button type="button" id="search_add_set">+ Add search set</button>
        <p class="hint">Reuse sets in the expression, for example <code>(#1 AND #2) NOT #3</code>.</p>
      </details>

      <div class="grid2">
        <div>
          <label for="search_journal_mode">Journal scope</label>
          <select id="search_journal_mode">
            <option value="any">All journals</option>
            <option value="only">Only listed journals</option>
            <option value="prefer">Prioritize listed journals</option>
          </select>
        </div>
        <div>
          <label for="search_sort">Sort results</label>
          <select id="search_sort">
            <option value="default">Default</option>
            <option value="relevance">Relevance</option>
            <option value="latest">Newest first</option>
            <option value="journal">Priority journals first</option>
          </select>
        </div>
      </div>
      <div id="search_journals_row" hidden>
        <label for="search_journals">Journal names or ISSNs</label>
        <input id="search_journals" aria-describedby="search_journals_help" placeholder="NeuroImage, Journal of Neuroscience">
        <p class="hint" id="search_journals_help">Separate journals with commas. Put names containing commas in double quotes.</p>
      </div>
      <div class="inline">
        <button type="button" id="search_preview_button" disabled>Preview search</button>
        <span id="search_preview_status" role="status"></span>
      </div>
      <div class="search-preview" id="search_preview_results" aria-label="Search preview by source"></div>
    </div>
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
      <label><input type="checkbox" id="otd_enabled"> Include "On This Day" (neuroscience history)</label>
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
      <span id="launchd_controls" hidden>
        <button onclick="launchd('install')">Install / update schedule</button>
        <button class="warn" onclick="launchd('uninstall')">Uninstall schedule</button>
      </span>
    </div>
    <p class="hint" id="schedule_hint"></p>
  </section>

  <section>
    <h2>Policy / news RSS</h2>
    <div id="policy_feeds"></div>
    <button onclick="addFeed()">+ Add RSS</button>
  </section>

  <section>
    <h2>Top journals watch-list</h2>
    <p class="desc">Journals with RSS are fetched for the papers section. Add aliases and ISSNs to recognize the same journal across sources.</p>
    <div id="journals"></div>
    <button onclick="addJournal()">+ Add journal</button>
  </section>

  <section>
    <h2>Push settings (email / webhook)</h2>
    <p class="desc">Save these settings before starting a search. Delivery is optional.</p>
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
  <button class="primary" id="saveRun" onclick="saveAndContinue()" disabled>Save & continue to search</button>
  <button onclick="save()">Save only</button>
  <button onclick="load()">Reload</button>
  <span id="msg" role="status"></span>
</footer>
<script>
var BASE=null;
var PUSH_BASELINE=null;
var SEARCH_PREVIEW=null;
var NEXT_SEARCH_SET=1;
var SEARCH_FIELDS=[
  ['TIAB','Title or abstract'],['TI','Title'],['AB','Abstract'],['TS','Topic'],
  ['SO','Journal'],['ISSN','ISSN'],['AU','Author'],['AK','Author keywords'],
  ['MH','MeSH'],['DT','Publication type'],['PY','Publication year'],
  ['PD','Publication date'],['CAT','Source category']
];
function el(id){return document.getElementById(id);}
function esc(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
function csv(a){
  return (a||[]).map(function(x){
    return /[",]/.test(x) ? '"' + x.replace(/"/g,'""') + '"' : x;
  }).join(', ');
}
function split(s){
  var values=[], match, fields=/(?:^|,)\s*(?:"((?:[^"]|"")*)"|([^,]*))/g;
  while((match=fields.exec(s||''))!==null){
    var value=match[1]===undefined ? match[2].trim() : match[1].replace(/""/g,'"');
    if(value) values.push(value);
    if(fields.lastIndex===match.index) fields.lastIndex++;
  }
  return values;
}

function addSearchTerm(container, focus){
  var row=document.createElement('div');
  row.className='search-term';
  row.innerHTML='<select class="term-field" aria-label="Search field">'+SEARCH_FIELDS.map(function(field){
    return '<option value="'+field[0]+'">'+field[1]+' ('+field[0]+')</option>';
  }).join('')+'</select>'+
    '<select class="term-mode" aria-label="Match type"><option value="phrase">Match phrase</option>'+
    '<option value="AND">All words</option><option value="OR">Any word</option></select>'+
    '<input class="term-value" aria-label="Search terms" placeholder="Enter words or a phrase" spellcheck="false">'+
    '<button type="button" class="del" aria-label="Remove condition">✕</button>';
  row.querySelector('button').onclick=function(){
    var next=(row.nextElementSibling||row.previousElementSibling);
    var target=next?next.querySelector('.term-field'):container.parentElement.querySelector('.add-term');
    row.remove();
    target.focus();
  };
  container.appendChild(row);
  if(focus) row.querySelector('.term-field').focus();
}

function addSearchGroup(focus){
  var group=document.createElement('fieldset');
  group.className='search-group';
  group.innerHTML='<legend>Condition group</legend><div class="inline">'+
    '<select class="term-operator" aria-label="Combine conditions"><option value="AND">Match all conditions</option>'+
    '<option value="OR">Match any condition</option></select>'+
    '<label><input type="checkbox" class="exclude-group"> Exclude matches</label>'+
    '<button type="button" class="del remove-group">Remove group</button></div>'+
    '<div class="search-terms"></div><button type="button" class="add-term">+ Add condition</button>';
  var terms=group.querySelector('.search-terms');
  group.querySelector('.add-term').onclick=function(){addSearchTerm(terms,true);};
  group.querySelector('.remove-group').onclick=function(){
    group.remove();
    el('search_add_group').focus();
  };
  el('search_groups').appendChild(group);
  addSearchTerm(terms,focus);
}

function groupExpression(parts,operator){
  return parts.length>1?'('+parts.join(' '+operator+' ')+')':parts[0]||'';
}

function conditionExpression(){
  var included=[],excluded=[];
  el('search_groups').querySelectorAll('.search-group').forEach(function(group){
    var clauses=[];
    group.querySelectorAll('.search-term').forEach(function(row){
      var value=row.querySelector('.term-value').value.trim();
      if(!value) return;
      var field=row.querySelector('.term-field').value;
      var mode=row.querySelector('.term-mode').value;
      var words=mode==='phrase'?[value]:value.split(/\s+/);
      clauses.push(groupExpression(words.map(function(word){
        return field+'='+JSON.stringify(word);
      }),mode));
    });
    var expr=groupExpression(clauses,group.querySelector('.term-operator').value);
    if(!expr) return;
    if(group.querySelector('.exclude-group').checked) excluded.push('NOT ('+expr+')');
    else included.push(expr);
  });
  var expr=groupExpression(included,el('search_group_operator').value);
  return (expr?[expr]:[]).concat(excluded).join(' AND ');
}

function appendSearchExpression(expression){
  var field=el('search_query');
  var current=field.value.trim();
  field.value=current?'('+current+') AND ('+expression+')':expression;
  field.focus();
  field.dispatchEvent(new Event('input',{bubbles:true}));
}

function addSearchSet(number,expression,focus){
  var row=document.createElement('div');
  row.className='search-set';
  row.dataset.number=number;
  row.innerHTML='<label for="search_set_'+esc(number)+'">#'+esc(number)+'</label>'+
    '<input class="set-expression" id="search_set_'+esc(number)+'" placeholder=\'TI="working memory"\' spellcheck="false">'+
    '<button type="button" class="insert-set">Use #'+esc(number)+'</button>'+
    '<button type="button" class="del remove-set" aria-label="Remove search set #'+esc(number)+'">✕</button>';
  var field=row.querySelector('input');
  field.value=expression||'';
  row.querySelector('.insert-set').onclick=function(){
    if(field.value.trim()) appendSearchExpression('#'+number);
    else field.focus();
  };
  row.querySelector('.remove-set').onclick=function(){
    row.remove();
    markPreviewStale();
    el('search_add_set').focus();
  };
  el('search_sets').appendChild(row);
  if(focus){
    el('search_sets_panel').open=true;
    field.focus();
  }
}

function resetSearchBuilder(){
  el('search_groups').replaceChildren();
  el('search_group_operator').value='AND';
  addSearchGroup(false);
}

function applySearchConditions(asSet){
  var expression=conditionExpression();
  if(!expression){
    el('search_builder_status').textContent='Enter a term in a condition to continue.';
    var first=el('search_groups').querySelector('.term-value');
    if(first) first.focus();
    return;
  }
  resetSearchBuilder();
  if(asSet){
    var number=NEXT_SEARCH_SET++;
    addSearchSet(number,expression,true);
    el('search_builder_status').textContent='Search set #'+number+' created.';
    markPreviewStale();
  }else{
    appendSearchExpression(expression);
    el('search_builder_status').textContent='Conditions added to the expression.';
  }
}

function showJournalScope(){
  el('search_journals_row').hidden=el('search_journal_mode').value==='any';
}

function renderSearch(search){
  if(SEARCH_PREVIEW){
    SEARCH_PREVIEW.abort();
    SEARCH_PREVIEW=null;
  }
  el('search_preview_results').replaceChildren();
  el('search_preview_results').removeAttribute('aria-busy');
  el('search_preview_status').textContent='';
  el('search_preview_status').dataset.state='';
  el('search_preview_button').disabled=false;
  resetSearchBuilder();
  el('search_builder_status').textContent='';
  search=search||{};
  el('search_query').value=search.query||'';
  el('search_journal_mode').value=search.journal_mode||'any';
  el('search_journals').value=csv(search.journals);
  el('search_sort').value=search.sort||'default';
  showJournalScope();
  el('search_sets').replaceChildren();
  NEXT_SEARCH_SET=1;
  var rawSets=search.sets||{},sets={};
  Object.keys(rawSets).forEach(function(key){sets[key.replace(/^#+/,'')]=rawSets[key];});
  Object.keys(sets).sort(function(a,b){return Number(a)-Number(b);}).forEach(function(number){
    addSearchSet(number,sets[number],false);
    NEXT_SEARCH_SET=Math.max(NEXT_SEARCH_SET,Number(number)+1);
  });
}

function collectSearch(previous){
  var query=el('search_query').value.trim();
  var journal_mode=el('search_journal_mode').value;
  var journals=split(el('search_journals').value);
  var sort=el('search_sort').value;
  var sets={};
  el('search_sets').querySelectorAll('.search-set').forEach(function(row){
    var expression=row.querySelector('input').value.trim();
    if(expression) sets[row.dataset.number]=expression;
  });
  if(!previous&&!query&&journal_mode==='any'&&!journals.length&&sort==='default'&&!Object.keys(sets).length) return;
  return Object.assign({},previous,{query:query,sets:sets,journal_mode:journal_mode,journals:journals,sort:sort});
}

function searchText(parent,tag,value){
  var node=document.createElement(tag);
  node.textContent=value;
  parent.appendChild(node);
  return node;
}

function previewExample(list,example){
  var item=document.createElement('li');
  list.appendChild(item);
  var title=example.title||'Untitled record';
  var url;
  try{url=new URL(example.url);}catch(e){}
  if(url&&(url.protocol==='https:'||url.protocol==='http:')){
    var link=searchText(item,'a',title);
    link.href=url.href; link.target='_blank'; link.rel='noopener noreferrer';
  }else{
    searchText(item,'b',title);
  }
  if(example.search_match==='unknown'){
    searchText(item,'p','Needs more metadata to confirm a match.').className='mini';
  }
  if(example.matched_rules&&example.matched_rules.length){
    searchText(item,'p','Matched · '+example.matched_rules.join(' · ')).className='mini';
  }
  if(example.missing_fields&&example.missing_fields.length){
    searchText(item,'p','Fields unavailable · '+example.missing_fields.join(', ')).className='mini';
  }
}

function showSearchPreview(sources){
  var results=el('search_preview_results');
  var labels={ok:'Available',empty:'No matches',partial:'Partial coverage',timeout:'Timed out',
    limited:'Limited',failed:'Failed',unsupported:'Unsupported'};
  var coverageLabels={full:'Complete for this request',sampled:'Sampled coverage',partial:'Partial coverage'};
  results.replaceChildren();
  sources.forEach(function(source){
    var details=document.createElement('details');
    details.className='source-details';
    details.open=Boolean(source.examples&&source.examples.length);
    var unavailable=['timeout','failed','limited'].includes(source.status);
    var matched=!unavailable&&source.status!=='empty'&&Number.isFinite(source.count)
      ?' · '+source.count+(source.status==='partial'?' confirmed matches':' matches'):'';
    var candidates=(!unavailable||source.candidates>0)&&Number.isFinite(source.candidates)
      ?' · '+source.candidates+' candidates':'';
    var unknown=source.unknown?' · '+source.unknown+' unconfirmed':'';
    var coverage=coverageLabels[source.coverage]||'';
    var status=source.status==='empty'&&source.coverage==='sampled'?'No sample matches':
      labels[source.status]||source.status||'Unknown';
    var summary=[source.source,status+matched+candidates+unknown];
    if(coverage&&coverage!==status) summary.push(coverage);
    if(source.truncated) summary.push('Candidate cap reached');
    searchText(details,'summary',summary.join(' · '));
    if(!coverage&&typeof source.coverage==='string'&&source.coverage){
      searchText(details,'p',source.coverage).className='mini';
    }
    if(source.date_range&&source.date_range.length===2){
      searchText(details,'p','Publication dates · '+source.date_range.join(' to ')).className='mini';
    }else if(source.lookback_days){
      searchText(details,'p','Source lookback · '+source.lookback_days+' days').className='mini';
    }
    if(Number.isFinite(source.fetched)) searchText(details,'p','Retrieved · '+source.fetched).className='mini';
    var errors=[source.error].concat(source.request_errors||[]).filter(Boolean);
    if(errors.length) searchText(details,'p',Array.from(new Set(errors)).join(' · '));
    var queries=source.queries&&source.queries.length?source.queries:[source.query].filter(Boolean);
    if(queries.length){
      searchText(details,'p',queries.length===1?'Source query':'Source queries').className='mini';
      searchText(details,'pre',queries.join('\n'));
    }
    if(source.examples&&source.examples.length){
      var examples=document.createElement('ul');
      source.examples.forEach(function(example){previewExample(examples,example);});
      details.appendChild(examples);
    }
    results.appendChild(details);
  });
}

function searchError(output){
  return Array.isArray(output.errors)&&output.errors.length?output.errors.join(' · '):output.error||'Invalid settings.';
}

function markPreviewStale(){
  if(!el('search_preview_results').childElementCount) return;
  el('search_preview_results').replaceChildren();
  el('search_preview_status').dataset.state='';
  el('search_preview_status').textContent='Settings changed. Preview again to see updated results.';
}

async function previewSearch(){
  if(!BASE||SEARCH_PREVIEW) return;
  var snapshot=JSON.stringify(collect());
  var controller=new AbortController();
  SEARCH_PREVIEW=controller;
  var button=el('search_preview_button'),status=el('search_preview_status'),results=el('search_preview_results');
  button.disabled=true;
  status.dataset.state='';
  status.textContent='Checking enabled sources…';
  results.replaceChildren();
  results.setAttribute('aria-busy','true');
  try{
    var response=await fetch('/api/search/preview',{method:'POST',headers:{'Content-Type':'application/json'},
      body:snapshot,signal:controller.signal});
    var output=await response.json();
    if(SEARCH_PREVIEW!==controller) return;
    if(snapshot!==JSON.stringify(collect())){
      status.textContent='Settings changed during the preview. Preview again.';
      return;
    }
    if(!response.ok||output.error) throw new Error(searchError(output));
    var sources=output.sources||[];
    showSearchPreview(sources);
    var counts=output.unique_candidates;
    status.textContent=!sources.length?'No sources available for this preview.':
      counts?counts.match+' unique matches · '+counts.unknown+' with missing metadata':
      'Preview for '+(output.profile||'this profile')+'.';
  }catch(error){
    if(SEARCH_PREVIEW!==controller) return;
    status.dataset.state='error';
    status.textContent='Preview failed. '+error.message;
  }finally{
    if(SEARCH_PREVIEW===controller){
      SEARCH_PREVIEW=null;
      button.disabled=false;
      results.removeAttribute('aria-busy');
    }
  }
}

function disciplineRow(x){
  x=x||{}; var d=document.createElement('div'); d.className='row grid';
  d.innerHTML='<input class="d-name" placeholder="Discipline name" value="'+esc(x.name)+'">'+
    '<input class="d-arxiv" placeholder="arXiv categories" value="'+esc(csv(x.arxiv_cats))+'">'+
    '<input class="d-mesh" placeholder="PubMed MeSH" value="'+esc(csv(x.mesh_terms))+'">'+
    '<input class="d-bio" placeholder="bioRxiv categories" value="'+esc(csv(x.bio_cats))+'">'+
    '<input class="d-kw" placeholder="Keywords" value="'+esc(csv(x.keywords))+'">'+
    '<label><input type="checkbox" class="d-en" '+(x.enabled!==false?'checked':'')+'> On</label>'+
    '<button class="del" onclick="this.closest(\'.row\').remove();markPreviewStale();">✕</button>';
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
  d.dataset.metricYear=x.metric_year==null?'':x.metric_year;
  d.innerHTML='<input class="j-name" placeholder="Journal name" value="'+esc(x.name)+'">'+
    '<input class="j-url" placeholder="Website URL" value="'+esc(x.url)+'">'+
    '<input class="j-rss" placeholder="RSS (optional)" value="'+esc(x.rss)+'">'+
    '<input class="j-cat" placeholder="Category" value="'+esc(x.category)+'">'+
    '<input class="j-if" type="number" step="0.01" placeholder="IF" value="'+(x.impact_factor!=null?x.impact_factor:'')+'">'+
    '<input class="j-jcr" placeholder="JCR" value="'+esc(x.jcr)+'">'+
    '<input class="j-cas" placeholder="中科院" value="'+esc(x.cas)+'">'+
    '<button class="del" onclick="this.closest(\'.row\').remove();markPreviewStale();">✕</button>'+
    '<label class="j-aliases">Journal aliases<input class="j-alias" value="'+esc(csv(x.aliases))+'"></label>'+
    '<label class="j-issns">ISSNs<input class="j-issn" value="'+esc(csv(x.issns))+'"></label>';
  return d;
}
function addJournal(){el('journals').appendChild(journalRow({category:'neuroscience'}));}

function render(){
  el('profile').value=BASE.profile||'';
  var dbox=el('disciplines'); dbox.innerHTML='';
  (BASE.disciplines||[]).forEach(function(x){dbox.appendChild(disciplineRow(x));});
  el('global_keywords').value=csv(BASE.global_keywords);
  renderSearch(BASE.search);
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

async function loadPresets(){
  var box=el('research_presets');
  try{
    var r=await fetch('/api/config/presets');
    if(!r.ok) throw new Error();
    var presets=await r.json();
    box.replaceChildren();
    presets.forEach(function(preset){
      var button=document.createElement('button');
      button.type='button';
      button.textContent=preset.label;
      button.setAttribute('aria-pressed',String(BASE.profile===preset.config.profile));
      button.onclick=function(){
        var current=collect();
        var clearSearch=current.profile!==preset.config.profile&&
          !Object.prototype.hasOwnProperty.call(preset.config,'search');
        var reset=clearSearch&&current.search&&
          (current.search.query||Object.keys(current.search.sets||{}).length||current.search.journal_mode!=='any');
        BASE=Object.assign(current,preset.config);
        if(clearSearch) delete BASE.search;
        render();
        box.querySelectorAll('button').forEach(function(option){
          option.setAttribute('aria-pressed',String(option===button));
        });
        el('preset_status').textContent=preset.label+' applied. '+
          (reset?'Review the reset search conditions and save.':'Review and save to use it.');
      };
      box.appendChild(button);
    });
  }catch(e){el('preset_status').textContent='Could not load research presets.';}
}

async function load(){
  el('saveRun').disabled=true;
  el('search_preview_button').disabled=true;
  try{
    var r=await fetch('/api/config');
    if(!r.ok) throw new Error('Could not load settings');
    BASE=await r.json(); render();
    el('cfgpath').textContent='config: ~/neurodaily/config/config.json';
    el('msg').textContent=''; el('msg').className='';
    loadPresets();
    await loadPush();
    el('saveRun').disabled=false;
  }catch(e){el('msg').textContent='Load failed: '+e; el('msg').className='bad';}
  loadLaunchdStatus();
  try{
    if(new URLSearchParams(location.search).get('next')==='run'){
      el('saveRun').scrollIntoView({block:'center'});
      el('saveRun').style.boxShadow='0 0 0 3px rgba(56,189,248,.5)';
    }
  }catch(e){}
}

var importedProfile = null;
var profilePreviewSequence = 0;

async function sendProfileFile(text, apply){
  var response = await fetch('/api/config/import' + (apply ? '?apply=true' : ''), {
    method: 'POST', headers: {'Content-Type': 'application/json'}, body: text
  });
  var result = await response.json();
  if (!response.ok) throw new Error(result.error || '无法读取配置文件');
  return result.summary;
}

async function previewProfileFile(input){
  var status = el('profile_import_status'), apply = el('apply_profile');
  var file = input.files[0];
  var sequence = ++profilePreviewSequence;
  input.value = '';
  importedProfile = null;
  apply.hidden = true;
  if (!file) return;
  status.textContent = '正在校验配置…';
  try {
    if (file.size > 256 * 1024) throw new Error('配置文件不能超过 256 KB');
    var text = await file.text();
    var summary = await sendProfileFile(text, false);
    if (sequence !== profilePreviewSequence) return;
    status.textContent = file.name + ' · ' + summary.profile + ' · ' +
      summary.disciplines + ' 个学科 · ' + summary.sources + ' 个数据源 · ' +
      summary.journals + ' 本期刊' + (summary.has_query ? ' · 含高级检索规则' : '') +
      (summary.removed_private_fields ? ' · 本机专用字段将跳过' : '');
    importedProfile = text;
    apply.hidden = false;
  } catch (error) {
    if (sequence === profilePreviewSequence) status.textContent = '校验失败 · ' + error.message;
  }
}

async function applyProfileFile(){
  if (!importedProfile) return;
  var status = el('profile_import_status'), apply = el('apply_profile');
  apply.disabled = true;
  try {
    var summary = await sendProfileFile(importedProfile, true);
    importedProfile = null;
    apply.hidden = true;
    await load();
    status.textContent = '已导入 ' + summary.profile;
  } catch (error) {
    status.textContent = '导入失败 · ' + error.message;
  } finally {
    apply.disabled = false;
  }
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
  var search=collectSearch(data.search);
  if(search) data.search=search;
  data.sources={};
  [].slice.call(el('sources').querySelectorAll('.row')).forEach(function(r){
    var key=r.dataset.key;
    var prev=(BASE.sources&&BASE.sources[key])||{};
    data.sources[key]=Object.assign({},prev,{
      enabled:r.querySelector('.s-en').checked,
      max_results:parseInt(r.querySelector('.s-max').value||'0',10),
      lookback_days:parseInt(r.querySelector('.s-look').value||'1',10)});
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
  data.policy_feeds=[].slice.call(el('policy_feeds').querySelectorAll('input.feed')).map(function(i){return i.value.trim();}).filter(Boolean);
  data.journals=[].slice.call(el('journals').querySelectorAll('.row')).map(function(r){
    var iv=r.querySelector('.j-if').value.trim();
    return {name:r.querySelector('.j-name').value.trim(),
      url:r.querySelector('.j-url').value.trim(),
      rss:r.querySelector('.j-rss').value.trim(),
      category:r.querySelector('.j-cat').value.trim(),
      impact_factor: iv?parseFloat(iv):null,
      jcr:r.querySelector('.j-jcr').value.trim(),
      cas:r.querySelector('.j-cas').value.trim(),
      aliases:split(r.querySelector('.j-alias').value),
      issns:split(r.querySelector('.j-issn').value),
      metric_year:r.dataset.metricYear?Number(r.dataset.metricYear):null};
  }).filter(function(x){return x.name;});
  return data;
}

async function save(){
  var data=collect();
  el('msg').textContent='Saving…'; el('msg').className='';
  try{
    var r=await fetch('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
    var out=await r.json();
    if(out.ok){
      el('msg').textContent='✅ Saved → '+out.path; el('msg').className='ok';
      loadLaunchdStatus();
      return true;
    }
    el('msg').textContent='Save failed. '+searchError(out); el('msg').className='bad'; return false;
  }catch(e){el('msg').textContent='❌ '+e; el('msg').className='bad'; return false;}
}

async function resetDefaults(){
  if(!confirm('Reset to defaults? This overwrites current settings.')) return;
  var r=await fetch('/api/config/reset',{method:'POST'});
  var out=await r.json();
  if(out.ok){await load(); el('msg').textContent='✅ Reset to defaults'; el('msg').className='ok';}
  else{el('msg').textContent='❌ Reset failed'; el('msg').className='bad';}
}

var desktopScheduler=false;
async function loadLaunchdStatus(){
  try{
    var r=await fetch('/api/launchd/status'); var s=await r.json();
    var desktop=s.backend==='desktop';
    desktopScheduler=desktop;
    el('launchd_controls').hidden=desktop;
    el('schedule_hint').textContent=desktop
      ? 'Save to apply. The app catches up on today’s missed time when it starts or wakes. Minimize the window to keep it running. Quitting stops the scheduled service.'
      : 'After changing the time, click Install / update schedule to apply.';
    var t=desktop
      ? (s.loaded?'Desktop schedule: daily at '+s.schedule+' (local time)':'Desktop schedule: off')
      : 'Scheduler: '+(s.loaded?'loaded':'not loaded')+(s.installed?' / installed':' / not installed')+'（'+s.schedule+'）';
    if(desktop&&s.loaded){
      if(s.state==='running') t+=' · Searching now';
      else if(s.state==='waiting') t+=' · Waiting to start';
      else if(s.state==='retrying') t+=' · Last attempt failed. Retry '+new Date(s.next_run).toLocaleString();
      else if(s.next_run) t+=' · Next '+new Date(s.next_run).toLocaleString();
    }
    if(desktop&&s.last_run){
      t+=' · Last '+new Date(s.last_run.finished_at).toLocaleString()+' ('+s.last_run.status+')';
      if(s.last_run.error) t+=' · '+s.last_run.error;
    }
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
  PUSH_BASELINE=null;
  try{
    var r=await fetch('/api/push');
    if(!r.ok) return;
    var d=await r.json();
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
    PUSH_BASELINE=pushPayload();
  }catch(e){}
}
async function savePush(){
  var current=pushPayload(), changes={};
  Object.keys(current).forEach(function(key){
    if(JSON.stringify(current[key])!==JSON.stringify(PUSH_BASELINE[key])) changes[key]=current[key];
  });
  if(Object.keys(changes).length){
    var r=await fetch('/api/push',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(changes)});
    var out=await r.json();
    if(!out.ok) throw new Error(out.error||'Failed to save push settings');
    PUSH_BASELINE=current;
  }
  var pw=el('push_password').value;
  if(pw){
    var r2=await fetch('/api/push/password',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:pw})});
    var o2=await r2.json();
    if(!o2.ok) throw new Error(o2.error||'Failed to save password');
    el('push_password').value=''; el('push_pw_state').textContent='(set)';
  }
}
async function saveAndContinue(){
  el('saveRun').disabled=true;
  try{
    if(!await save()) return;
    if(PUSH_BASELINE) await savePush();
    location.href='/run';
  }catch(e){ el('msg').className='bad'; el('msg').textContent='❌ '+e; }
  finally{el('saveRun').disabled=false;}
}

el('search_add_group').onclick=function(){addSearchGroup(true);};
el('search_apply_conditions').onclick=function(){applySearchConditions(false);};
el('search_save_conditions').onclick=function(){applySearchConditions(true);};
el('search_add_set').onclick=function(){addSearchSet(NEXT_SEARCH_SET++,'',true);};
el('search_journal_mode').onchange=showJournalScope;
el('search_preview_button').onclick=previewSearch;
document.querySelector('main').addEventListener('input',function(event){
  if(!event.target.closest('#search_builder')) markPreviewStale();
});
document.querySelector('main').addEventListener('change',function(event){
  if(!event.target.closest('#search_builder')) markPreviewStale();
});
load();
setInterval(function(){if(desktopScheduler&&!document.hidden) loadLaunchdStatus();},10000);
</script>
</body></html>
"""
