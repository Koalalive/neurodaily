"""Settings GUI page for NeuroDaily (dependency-free vanilla JS)."""

from .optimization_ui import OPTIMIZATION_HEAD, OPTIMIZATION_WORKBENCH

DASHBOARD_SETTINGS_LINK = (
    '<a href="/settings" style="position:fixed;top:12px;right:16px;z-index:9999;'
    'background:#0e1013;border:1px solid #c8a96b;color:#c8a96b;padding:6px 12px;'
    'border-radius:2px;text-decoration:none;font:600 13px Georgia,serif;">'
    "◈ Settings</a>"
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
.row.j{display:grid;grid-template-columns:repeat(3,minmax(0,1fr)) minmax(0,.7fr) auto;gap:6px;margin:0 0 14px}
.row.j .j-aliases{grid-column:1 / 3}
.row.j .j-issns{grid-column:3 / -1}
.j-metrics{grid-column:1 / -1;border-bottom:1px solid var(--line);padding:4px 0 8px}
.j-metrics summary{cursor:pointer;color:var(--accent);font-size:.82rem}
.j-metrics-fields{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin-top:8px}
.j-metrics-fields label{min-width:0}
.j-metrics-fields .j-tags-label{grid-column:1 / -1}
.row.feed{display:grid;grid-template-columns:minmax(10ch,1fr) auto auto}
.row.recipient{display:grid;grid-template-columns:minmax(180px,1.5fr) 110px 120px auto;gap:6px;margin-bottom:6px}
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
@media(max-width:580px){.j-metrics-fields{grid-template-columns:repeat(2,minmax(0,1fr))}}
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

html { color-scheme: dark; scrollbar-color: #3a4352 #0b0b0c; scrollbar-width: thin; }
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: #0b0b0c; }
::-webkit-scrollbar-thumb { background: #3a4352; border: 2px solid #0b0b0c; border-radius: 999px; }
::-webkit-scrollbar-thumb:hover { background: #58647a; }
</style>
<!-- OPTIMIZATION_HEAD -->
</head>
<body>
<header><h1>NeuroDaily Settings</h1><a href="/">← Back to dashboard</a><span class="mini" id="cfgpath"></span></header>
<main>
  <section>
    <label for="ui_language">界面语言</label>
    <select id="ui_language" style="width:auto" disabled>
      <option value="zh" lang="zh">简体中文</option>
      <option value="en" lang="en">English</option>
      <option value="ru" lang="ru">Русский</option>
    </select>
    <p id="ui_language_status" role="status"></p>
  </section>
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
    <div class="inline" style="margin-top:10px">
      <a href="/api/app-settings/export" download>导出应用设置</a>
      <button type="button" onclick="document.getElementById('app_settings_file').click()">导入应用设置</button>
      <input id="app_settings_file" type="file" accept=".json,application/json" hidden onchange="importAppSettings(this)">
    </div>
    <p class="desc">应用设置只包含输出、计划、邮件、Webhook、AI 连接和界面语言；不包含检索 profile。密钥默认不导出。</p>
    <p id="app_settings_status" role="status" aria-live="polite"></p>
    <details id="profile_revisions" style="margin-top:10px">
      <summary>Profile revision history</summary>
      <p class="hint">Restoring creates a new research revision and preserves app settings.</p>
      <div class="inline">
        <select id="profile_revision_select" aria-label="Profile revision history"></select>
        <button id="profile_revision_more" type="button" hidden>Load older revisions</button>
        <button id="profile_revision_restore" type="button" disabled>Restore research revision</button>
      </div>
      <p id="profile_revision_status" class="hint" role="status"></p>
      <pre id="profile_revision_diff" hidden style="white-space:pre-wrap;overflow-wrap:anywhere"></pre>
    </details>
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

      <div class="inline" style="margin-top:8px">
        <label for="search_authors">Scholar tracking</label>
        <input id="search_authors" placeholder="Nolan Williams, Jane Doe" style="flex:1">
        <select id="search_author_mode" style="width:auto">
          <option value="intersect">Track within this topic</option>
          <option value="track">Track all new works</option>
        </select>
      </div>
      <p class="hint">Names are matched against PubMed author fields and local author metadata. Use ORCID/affiliation to disambiguate common names.</p>

      <div>
        <label for="search_query">Search expression</label>
        <textarea id="search_query" rows="3" spellcheck="false" aria-describedby="search_query_help"
          placeholder='TI="working memory" AND (TIAB=EEG OR TIAB=electroencephalography)'></textarea>
        <p class="hint" id="search_query_help"><span>Use</span> <code>AND</code>, <code>OR</code>, <code>NOT</code>, <span>parentheses</span>, <code>TI="working memory"</code>, <code>TIAB=EEG NEAR/5 TIAB=memory</code>, <code>PY=2024-2026</code>. <span>For a keyword search, clear the expression and keep all journals.</span></p>
      </div>

      <details class="search-tools" id="search_sets_panel">
        <summary>Numbered search sets</summary>
        <div id="search_sets"></div>
        <button type="button" id="search_add_set">+ Add search set</button>
        <p class="hint"><span>Reuse sets in the expression, for example</span> <code>(#1 AND #2) NOT #3</code>.</p>
      </details>

      <details class="search-tools">
        <summary>新闻、政策与试验检索规则</summary>
        <p class="hint">各类型独立匹配，可以使用同一组编号集合。留空时使用来源默认检索。</p>
        <label for="rule_news">新闻检索式</label><input id="rule_news" placeholder='TS="brain-computer interface"'>
        <label for="rule_policy">政策检索式</label><input id="rule_policy" placeholder='TS="neurotechnology"'>
        <label for="rule_trial">试验检索式</label><input id="rule_trial" placeholder='TS="deep brain stimulation"'>
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
        <button type="button" id="search_lint_button">Check draft locally</button>
        <button type="button" id="search_preview_button" disabled>Preview search</button>
        <span id="search_preview_status" role="status"></span>
      </div>
      <details id="search_lint_results" hidden>
        <summary>Local search check</summary>
        <div id="search_lint_details" role="status"></div>
      </details>
      <div class="search-preview" id="search_preview_results" aria-label="Search preview by source"></div>
    </div>
    <!-- OPTIMIZATION_WORKBENCH -->
  </section>

  <section>
    <h2>Sources</h2>
    <p class="desc">Enable, max results per fetch (0 = no item cap), lookback days.</p>
    <div id="sources"></div>
  </section>

  <section>
    <h2>Output</h2>
    <div class="grid2">
      <div><label>Report directory</label><input id="out_dir"></div>
      <div><label>Filename format</label><input id="out_fmt"></div>
    </div>
    <div class="inline" style="margin-top:10px"><label><input type="checkbox" id="out_open"> Open report when finished</label>
      <label><input type="checkbox" id="out_seen_dedup"> Hide items already shown on a previous day</label></div>
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
    <h2>Report content</h2>
    <div class="inline">
      <label><input type="checkbox" id="otd_enabled"> Include "On This Day" (neuroscience history)</label>
      <label><input type="checkbox" id="otd_notify"> Desktop notification daily</label>
      <label><input type="checkbox" id="topic_map_enabled"> Include LDA + t-SNE topic map</label>
      <label><input type="checkbox" id="topic_ai_labels"> 用大模型标注主题</label>
    </div>
    <div class="inline" style="margin-top:10px">
      <label>主题标签并发数 <input id="topic_concurrency" type="number" min="1" max="4" value="4" style="width:70px"></label>
    </div>
    <div class="inline" style="margin-top:10px">
      <label>"On This Day" language</label>
      <select id="otd_lang" style="width:160px">
        <option value="zh">Chinese</option>
        <option value="en">English</option>
        <option value="ru">Русский</option>
      </select>
    </div>
    <p class="desc">This switch affects both scheduled and manual reports. Disabling it removes the section from the report and email.</p>
  </section>

  <section>
    <h2>Schedule</h2>
    <div class="inline">
      <label><input type="checkbox" id="sch_enabled"> Enable schedule</label>
      <span class="mini">Time</span>
      <input type="number" id="sch_hour" min="0" max="23"> :
      <input type="number" id="sch_minute" min="0" max="59">
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
    <p class="desc">Enter publication metrics, indexing and custom tags to show them beside matching papers.</p>
    <div id="journals"></div>
    <button onclick="addJournal()">+ Add journal</button>
  </section>

  <section>
    <h2>Push settings (email / webhook)</h2>
    <p class="desc">Save these settings before starting a search. Delivery is optional.</p>
    <div class="inline"><label><input type="checkbox" id="push_email_enabled"> Enable email</label>
      <label><input type="checkbox" id="push_attach" checked> Attach full HTML</label></div>
    <div style="margin-top:8px"><label>Recipients</label>
      <div id="push_recipients"></div>
      <button type="button" onclick="addRecipient()">+ Add recipient</button>
      <p class="hint">Push time is local time (HH:MM); leave blank to send immediately. Language controls the email body labels.</p></div>
    <div class="grid2" style="margin-top:8px">
      <div><label>SMTP host</label><input id="push_host"></div>
      <div><label>Port</label><input type="number" id="push_port"></div>
      <div><label for="push_security">SMTP 加密方式</label><select id="push_security">
        <option value="starttls">STARTTLS（常用 587）</option>
        <option value="ssl">SSL/TLS（常用 465）</option>
      </select></div>
      <div><label>Username</label><input id="push_user"></div>
      <div><label>From</label><input id="push_from"></div>
    </div>
    <div class="inline" style="margin-top:8px"><label>Subject template</label><input id="push_subject" style="flex:1"></div>
    <div style="margin-top:8px"><label>Public report URL (optional)</label><input id="push_public_url" type="url" placeholder="https://your-server.example/report/latest" style="width:100%"></div>
    <div class="inline" style="margin-top:8px"><label>SMTP app password</label>
      <input type="password" id="push_password" placeholder="Leave blank to keep" style="flex:1">
      <span class="mini" id="push_pw_state"></span></div>
    <div class="inline" style="margin-top:8px">
      <button id="push_test" type="button" onclick="testMail()">测试邮件连通性</button>
      <span id="push_test_status" role="status"></span>
    </div>
    <div class="grid2" style="margin-top:8px">
      <div>
        <label for="push_feishu">飞书 Webhook</label>
        <input type="password" id="push_feishu" autocomplete="new-password" placeholder="留空保留已有地址">
        <span class="mini" id="push_feishu_state"></span>
        <label><input type="checkbox" id="push_feishu_remove" disabled> 移除已保存地址</label>
      </div>
      <div>
        <label for="push_wecom">企业微信 Webhook</label>
        <input type="password" id="push_wecom" autocomplete="new-password" placeholder="留空保留已有地址">
        <span class="mini" id="push_wecom_state"></span>
        <label><input type="checkbox" id="push_wecom_remove" disabled> 移除已保存地址</label>
      </div>
    </div>
  </section>

  <section>
    <h2>AI 摘要</h2>
    <label><input type="checkbox" id="ai_enabled"> 启用 AI 摘要</label>
    <div class="grid2" style="margin-top:8px">
      <div><label for="ai_base">API 基础地址</label><input type="url" id="ai_base" placeholder="https://api.example.com/v1"></div>
      <div><label for="ai_model">模型 ID</label><input id="ai_model" placeholder="服务商提供的模型 ID"></div>
    </div>
    <div class="inline" style="margin-top:8px">
      <label for="ai_key">API 密钥</label>
      <input type="password" id="ai_key" autocomplete="new-password" placeholder="留空保留已有密钥" style="flex:1">
      <span id="ai_key_state" class="mini"></span>
    </div>
    <div class="inline" style="margin-top:8px">
      <button id="ai_test" type="button" onclick="testAi()">测试模型 API</button>
      <span id="ai_test_status" role="status"></span>
    </div>
    <p class="desc">使用兼容 Chat Completions 的接口。测试使用当前输入，仅发送一条简短请求，可在保存前验证。</p>
    <p><a href="/billing">API 账单与地图设置</a></p>
  </section>

  <section>
    <h2>Reset</h2>
    <p class="desc">Reset config to built-in defaults (overwrites current settings).</p>
    <button class="warn" onclick="resetDefaults()">Reset to defaults</button>
  </section>
</main>
<footer>
  <button class="primary" id="saveRun" onclick="saveAndContinue()" disabled>Save & continue to search</button>
  <button id="saveOnly" onclick="saveSettings(false)">Save only</button>
  <button onclick="load()">Reload</button>
  <span id="msg" role="status"></span>
</footer>
<script>
var BASE=null;
var savedConfigFingerprint=null;
var savedConfigVersion=null;
var displayedSearchProfile=null;
var PUSH_BASELINE=null;
var AI_BASELINE=null;
var SEARCH_PREVIEW=null;
var NEXT_SEARCH_SET=1;
var SEARCH_FIELDS=[
  ['TIAB','Title or abstract'],['TI','Title'],['AB','Abstract'],['TS','Topic'],
  ['SO','Journal'],['ISSN','ISSN'],['AU','Author'],['AK','Author keywords'],
  ['MH','MeSH'],['DT','Publication type'],['PY','Publication year'],
  ['PD','Publication date'],['CAT','Source category']
];
function el(id){return document.getElementById(id);}
var t=window.ndT||function(message,values){
  return message.replace(/\{(\w+)\}/g,function(match,key){return values&&key in values?values[key]:match;});
};
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
    return '<option value="'+field[0]+'">'+esc(t(field[1]))+' ('+field[0]+')</option>';
  }).join('')+'</select>'+
    '<select class="term-mode" aria-label="Match type"><option value="phrase">Match phrase</option>'+
    '<option value="AND">All words</option><option value="OR">Any word</option></select>'+
    '<input class="term-value" aria-label="Search terms" placeholder="Enter words or a phrase" spellcheck="false">'+
    '<button type="button" class="del" aria-label="Remove condition">×</button>';
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
    '<button type="button" class="insert-set">'+esc(t('Use #{number}',{number:number}))+'</button>'+
    '<button type="button" class="del remove-set" aria-label="'+esc(t('Remove search set #{number}',{number:number}))+'">×</button>';
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
    el('search_builder_status').textContent=t('Search set #{number} created.',{number:number});
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
  for(var kind of ['news','policy','trial']) el('rule_'+kind).value=(search.rules||{})[kind]||'';
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
  var rules={};
  for(var kind of ['news','policy','trial']){
    var expression=el('rule_'+kind).value.trim();
    if(expression) rules[kind]=expression;
  }
  var sets={};
  el('search_sets').querySelectorAll('.search-set').forEach(function(row){
    var expression=row.querySelector('input').value.trim();
    if(expression) sets[row.dataset.number]=expression;
  });
  if(!previous&&!query&&journal_mode==='any'&&!journals.length&&sort==='default'&&!Object.keys(sets).length&&!Object.keys(rules).length) return;
  var result=Object.assign({},previous,{query:query,sets:sets,journal_mode:journal_mode,journals:journals,sort:sort});
  if(Object.keys(rules).length) result.rules=rules;
  else delete result.rules;
  return result;
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
  var title=example.title||t('Untitled record');
  var url;
  try{url=new URL(example.url);}catch(e){}
  if(url&&(url.protocol==='https:'||url.protocol==='http:')){
    var link=searchText(item,'a',title);
    link.href=url.href; link.target='_blank'; link.rel='noopener noreferrer';
    link.dataset.noI18n='';
  }else{
    searchText(item,'b',title).dataset.noI18n='';
  }
  if(example.search_match==='unknown'){
    searchText(item,'p','Needs more metadata to confirm a match.').className='mini';
  }
  if(example.search_match==='miss') searchText(item,'p','未满足本类型的检索规则。').className='mini';
  if(example.matched_rules&&example.matched_rules.length){
    searchText(item,'p',t('Matched · {rules}',{rules:example.matched_rules.join(' · ')})).className='mini';
  }
  if(example.missing_fields&&example.missing_fields.length){
    searchText(item,'p',t('Fields unavailable · {fields}',{fields:example.missing_fields.join(', ')})).className='mini';
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
      ?' · '+t(source.status==='partial'?'{count} confirmed matches':'{count} matches',{count:source.count}):'';
    var candidates=(!unavailable||source.candidates>0)&&Number.isFinite(source.candidates)
      ?' · '+t('{count} candidates',{count:source.candidates}):'';
    var unknown=source.unknown?' · '+t('{count} unconfirmed',{count:source.unknown}):'';
    var excluded=source.excluded?' · '+t('{count} 条已排除',{count:source.excluded}):'';
    var coverage=t(coverageLabels[source.coverage]||'');
    var status=t(source.status==='empty'&&source.coverage==='sampled'?'No sample matches':
      labels[source.status]||source.status||'Unknown');
    var summary=[source.source,status+matched+candidates+unknown+excluded];
    if(coverage&&coverage!==status) summary.push(coverage);
    if(source.truncated) summary.push(t('Candidate cap reached'));
    searchText(details,'summary',summary.join(' · '));
    if(!coverage&&typeof source.coverage==='string'&&source.coverage){
      searchText(details,'p',source.coverage).className='mini';
    }
    if(source.date_range&&source.date_range.length===2){
      searchText(details,'p',t('Publication dates · {start} to {end}',{start:source.date_range[0],end:source.date_range[1]})).className='mini';
    }else if(source.lookback_days){
      searchText(details,'p',t('Source lookback · {count} days',{count:source.lookback_days})).className='mini';
    }
    if(Number.isFinite(source.fetched)) searchText(details,'p',t('Retrieved · {count}',{count:source.fetched})).className='mini';
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
  return Array.isArray(output.errors)&&output.errors.length?output.errors.map(function(error){return t(error);}).join(' · '):t(output.error||'Invalid settings.');
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
      counts?t('{matches} unique matches · {unknown} with missing metadata',{matches:counts.match,unknown:counts.unknown}):
      t('Preview for {profile}.',{profile:output.profile||t('this profile')});
  }catch(error){
    if(SEARCH_PREVIEW!==controller) return;
    status.dataset.state='error';
    status.textContent=t('Preview failed. {error}',{error:error.message});
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
    '<button class="del" onclick="this.closest(\'.row\').remove();markPreviewStale();">×</button>';
  return d;
}
function addDiscipline(){el('disciplines').appendChild(disciplineRow({}));}

function sourceRow(k,o){
  o=o||{}; var d=document.createElement('div'); d.className='row src'; d.dataset.key=k;
  d.innerHTML='<b data-no-i18n>'+esc(k)+'</b>'+
    '<label><input type="checkbox" class="s-en" '+(o.enabled!==false?'checked':'')+'> On</label>'+
    '<input type="number" class="s-max" title="max_results" value="'+(o.max_results!=null?o.max_results:20)+'">'+
    '<input type="number" class="s-look" title="lookback_days" value="'+(o.lookback_days!=null?o.lookback_days:1)+'">';
  if(['trials','europe_pmc','openalex','gdelt','nih_brain','google_news_zh'].includes(k)){
    var query=document.createElement('input');
    query.className='s-query';
    query.style.gridColumn='1 / -1';
    query.value=o.query||'';
    query.placeholder='来源专用查询（可选）';
    d.append(query);
  }
  return d;
}
function feedRow(u, kind){
  var d=document.createElement('div'); d.className='row feed';
  d.innerHTML='<input class="feed" value="'+esc(u)+'">'+
    '<select class="feed-kind" aria-label="订阅源内容类型"><option value="">自动识别</option><option value="paper">论文</option><option value="news">新闻</option><option value="policy">政策</option><option value="funding">资助</option><option value="conference">会议</option></select>'+
    '<button class="del" onclick="this.closest(\'.row\').remove()">×</button>';
  d.querySelector('.feed-kind').value=kind||'';
  return d;
}
function addFeed(){el('policy_feeds').appendChild(feedRow(''));}

function journalRow(x){
  x=x||{}; var d=document.createElement('div'); d.className='row j';
  function yearField(css,label,value){
    return '<label>'+label+'<input class="'+css+'" type="number" inputmode="numeric" min="1900" max="9999" step="1" value="'+esc(value)+'"></label>';
  }
  function indexing(css,label,value){
    return '<label>'+label+'<select class="'+css+'">'+
      '<option value="">Not set</option><option value="yes" '+(value===true?'selected':'')+'>Indexed</option>'+
      '<option value="no" '+(value===false?'selected':'')+'>Not indexed</option></select></label>';
  }
  d.innerHTML='<input class="j-name" placeholder="Journal name" value="'+esc(x.name)+'">'+
    '<input class="j-url" placeholder="Website URL" value="'+esc(x.url)+'">'+
    '<input class="j-rss" placeholder="RSS (optional)" value="'+esc(x.rss)+'">'+
    '<input class="j-cat" placeholder="Category" value="'+esc(x.category)+'">'+
    '<button class="del" onclick="this.closest(\'.row\').remove();markPreviewStale();">×</button>'+
    '<label class="j-aliases">Journal aliases<input class="j-alias" value="'+esc(csv(x.aliases))+'"></label>'+
    '<label class="j-issns">ISSNs<input class="j-issn" value="'+esc(csv(x.issns))+'"></label>'+
    '<details class="j-metrics"><summary>Journal metrics and tags</summary><div class="j-metrics-fields">'+
    '<label>IF<input class="j-if" type="number" min="0" step="any" value="'+esc(x.impact_factor)+'"></label>'+
    '<label>JCR<input class="j-jcr" placeholder="Q1" value="'+esc(x.jcr)+'"></label>'+
    '<label>中科院<input class="j-cas" value="'+esc(x.cas)+'"></label>'+
    yearField('j-if-year','IF year',x.impact_factor_year)+
    yearField('j-jcr-year','JCR year',x.jcr_year)+
    yearField('j-cas-year','CAS year',x.cas_year)+
    yearField('j-metric-year','Shared metric year',x.metric_year)+
    indexing('j-sci','SCI',x.sci)+indexing('j-ssci','SSCI',x.ssci)+
    '<label><input class="j-cas-top" type="checkbox" '+(x.cas_top===true?'checked':'')+'> CAS Top</label>'+
    '<label class="j-tags-label">Custom journal tags<input class="j-tags" placeholder="Separate tags with commas" value="'+
    esc(csv(x.tags))+'"></label></div></details>';
  return d;
}
function addJournal(){el('journals').appendChild(journalRow({category:'neuroscience'}));}

function render(){
  el('profile').value=BASE.profile||'';
  var dbox=el('disciplines'); dbox.innerHTML='';
  (BASE.disciplines||[]).forEach(function(x){dbox.appendChild(disciplineRow(x));});
  el('global_keywords').value=csv(BASE.global_keywords);
  renderSearch(BASE.search);
  el('search_authors').value=csv((BASE.search||{}).authors);
  el('search_author_mode').value=(BASE.search||{}).author_mode||'intersect';
  var sbox=el('sources'); sbox.innerHTML='';
  Object.keys(BASE.sources||{}).forEach(function(k){sbox.appendChild(sourceRow(k,BASE.sources[k]));});
  var o=BASE.output||{};
  el('out_dir').value=o.dir||''; el('out_fmt').value=o.filename_format||''; el('out_open').checked=!!o.open_on_finish;
  el('out_seen_dedup').checked=!!o.seen_dedup;
  var sc=BASE.scheduled||{}; var otd=sc.on_this_day||{};
  el('sch_enabled').checked=!!sc.enabled;
  el('sch_hour').value=(sc.hour!=null?sc.hour:8); el('sch_minute').value=(sc.minute!=null?sc.minute:0);
  el('otd_enabled').checked=(otd.enabled!==false); el('otd_notify').checked=(otd.notify!==false);
  el('topic_map_enabled').checked=(o.topic_map!==false);
  el('topic_ai_labels').checked=(o.topic_ai_labels!==false);
  el('topic_concurrency').value=o.topic_concurrency||4;
  el('otd_lang').value = otd.lang || 'zh';
  var w = BASE.windows || {};
  el('win_daily').value = (w.daily_paper_hours != null ? w.daily_paper_hours : 36);
  el('win_manual').value = (w.manual_paper_hours != null ? w.manual_paper_hours : 240);
  el('win_trials').value = (w.trials_hours != null ? w.trials_hours : 168);
  el('win_funding').value = (w.funding_hours != null ? w.funding_hours : 36);
  el('win_news').value = (w.news_hours != null ? w.news_hours : 36);
  var pbox=el('policy_feeds'); pbox.innerHTML='';
  var feedKinds=((BASE.sources||{}).policy||{}).feed_kinds||{};
  (BASE.policy_feeds||[]).forEach(function(u){pbox.appendChild(feedRow(u,feedKinds[u]));});
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
        el('preset_status').textContent=t('{preset} applied. {hint}',{
          preset:t(preset.label),hint:t(reset?'Review the reset search conditions and save.':'Review and save to use it.')});
      };
      box.appendChild(button);
    });
  }catch(e){el('preset_status').textContent='Could not load research presets.';}
}

async function load(){
  el('saveRun').disabled=true;
  el('search_preview_button').disabled=true;
  try{
    var r=await fetch('/api/config',{cache:'no-store'});
    if(!r.ok) throw new Error(t('Could not load settings'));
    BASE=await r.json(); render();
    rememberSavedConfig(collect(),r.headers.get('ETag'));
    el('cfgpath').textContent=t('Config: {path}',{path:'~/neurodaily/config/config.json'});
    el('msg').textContent=''; el('msg').className='';
    loadPresets();
    await Promise.all([loadPush(),loadAi()]);
    el('saveRun').disabled=false;
  }catch(e){el('msg').textContent=t('Load failed: {error}',{error:e.message}); el('msg').className='bad';}
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

var profileRevisionRows=[];
var reviewedRevision=null;
var revisionOrigins={existing:'Observed configuration',save:'Saved configuration',settings:'Settings saved',
  'import':'Imported configuration',cli_patch:'CLI patch',restore:'Restored revision',reset:'Reset defaults',
  optimization:'Applied optimization',optimization_rollback:'Reverted optimization'};

async function loadProfileRevisions(older){
  var select=el('profile_revision_select'), status=el('profile_revision_status'), more=el('profile_revision_more');
  var before=older&&profileRevisionRows.length?'?before='+profileRevisionRows.at(-1).id:'';
  try{
    var response=await fetch('/api/config/revisions'+before,{cache:'no-store'});
    if(!response.ok) throw new Error();
    var result=await response.json(), selected=select.value;
    profileRevisionRows=(older?profileRevisionRows:[]).concat(result.revisions);
    select.replaceChildren(...profileRevisionRows.map(function(row){
      var label=new Date(row.created_at).toLocaleString(document.documentElement.lang)+' · '+row.profile+' · '+row.revision.slice(0,12);
      return new Option(label,row.id);
    }));
    if(older&&selected) select.value=selected;
    more.hidden=result.revisions.length<50;
    await loadProfileRevisionDiff();
  }catch(_){status.textContent=t('Could not load profile revisions.');}
}

async function loadProfileRevisionDiff(){
  var id=el('profile_revision_select').value, diff=el('profile_revision_diff'), status=el('profile_revision_status');
  var restore=el('profile_revision_restore');
  reviewedRevision=null;
  restore.disabled=true;
  diff.hidden=true;
  if(!id) return;
  try{
    var response=await fetch('/api/config/revisions/'+id,{cache:'no-store'});
    if(!response.ok) throw new Error();
    var result=await response.json();
    if(el('profile_revision_select').value!==id) return;
    reviewedRevision={id:id,version:response.headers.get('ETag')};
    diff.textContent=result.diff||t('No portable fields differ.');
    diff.hidden=false;
    var details=[result.revision, t(revisionOrigins[result.origin]||result.origin)];
    if(result.provenance?.optimization_run_id) details.push(t('Optimization run')+' '+result.provenance.optimization_run_id);
    if(result.provenance?.snapshot_id) details.push(t('Evidence snapshot')+' '+result.provenance.snapshot_id);
    if(result.provenance?.restored_revision) details.push(t('Restored revision {number}',{number:result.provenance.restored_revision}));
    status.textContent=details.join(' · ');
    restore.disabled=!reviewedRevision.version||result.revision===result.current_revision;
  }catch(_){status.textContent=t('Could not load profile revisions.');}
}

async function restoreProfileRevision(){
  var selected=reviewedRevision, status=el('profile_revision_status'), button=el('profile_revision_restore');
  if(!selected) return;
  if(!window.ndCanUpdateSearch()){
    status.textContent=t('Save or discard your settings form edits before restoring a revision.');
    return;
  }
  button.disabled=true;
  try{
    var response=await fetch('/api/config/revisions/'+selected.id+'/restore',{method:'POST',headers:configHeaders(selected.version)});
    if(!response.ok){
      var result=await response.json();
      status.textContent=t(result.error||'Could not restore the profile revision.');
      return;
    }
    await load();
    await loadProfileRevisions();
    status.textContent=t('Research revision restored.');
  }catch(_){status.textContent=t('Could not restore the profile revision.');}
}

el('profile_revisions').addEventListener('toggle',function(){if(this.open) loadProfileRevisions();});
el('profile_revision_select').addEventListener('change',loadProfileRevisionDiff);
el('profile_revision_more').addEventListener('click',function(){loadProfileRevisions(true);});
el('profile_revision_restore').addEventListener('click',restoreProfileRevision);

async function checkSearchDraft(data, show){
  var details=el('search_lint_details'), box=el('search_lint_results');
  try{
    var response=await fetch('/api/config/lint',{method:'POST',headers:configHeaders(),body:JSON.stringify(data)});
    var result=await response.json();
    var nodes=[];
    var add=function(text){var line=document.createElement('p');line.textContent=text;nodes.push(line);};
    (result.errors||[]).forEach(add);
    (result.sources||[]).forEach(function(row){
      if(row.metadata_gaps.length) add(t('{source} may lack metadata for {fields}.',{source:row.source,fields:row.metadata_gaps.join(', ')}));
      if(!row.remote_filter&&row.fields.length) add(t('{source} applies this rule locally.',{source:row.source}));
      if(show&&row.query_preview) add(t('{source} candidate hint · {query}',{source:row.source,query:row.query_preview}));
    });
    if(result.known_records){
      var records=result.known_records;
      if(records.matched||records.missed||records.unknown){
        add(t('Historical sample includes {matched} matches, {missed} exclusions and {unknown} with missing metadata.',records));
        records.examples.forEach(function(row){
          add(row.title+' · '+(row.missing_fields.length?row.missing_fields.join(', '):t('Excluded by the draft')));
        });
      }
    }
    var warnings=nodes.length>0;
    if(!warnings) add(t('No issues found in the local check.'));
    details.replaceChildren(...nodes);
    box.hidden=false;
    box.open=Boolean(show||warnings);
    return response.ok;
  }catch(_){
    details.textContent=t('The local search check is unavailable.');
    box.hidden=false;
    box.open=true;
    return true;
  }
}

el('search_lint_button').addEventListener('click',function(){if(BASE) checkSearchDraft(collect(),true);});

function configHeaders(version){
  var headers={'Content-Type':'application/json'};
  if(version) headers['If-Match']=version;
  return headers;
}

async function sendProfileFile(text, apply, version){
  var response = await fetch('/api/config/import' + (apply ? '?apply=true' : ''), {
    method: 'POST', headers: configHeaders(version), body: text
  });
  var result = await response.json();
  if (!response.ok) {
    var stale=result.code==='configuration_changed';
    var error=new Error(t(stale?'Configuration changed since the preview. Select the file to preview it again.':
      (result.error||'无法读取配置文件')));
    error.stale=stale;
    throw error;
  }
  return {summary:result.summary,version:response.headers.get('ETag')};
}

async function importAppSettings(input){
  var file=input.files[0], status=el('app_settings_status');
  input.value='';
  if(!file) return;
  status.textContent='正在导入…';
  try{
    var text=await file.text();
    var response=await fetch('/api/app-settings/import',{method:'POST',headers:configHeaders(savedConfigVersion),body:text});
    var result=await response.json();
    if(!response.ok||!result.ok) throw new Error(t(result.error||'导入失败'));
    status.textContent='✓ 已导入应用设置';
    await load();
  }catch(e){status.textContent='× '+e.message;}
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
    if (file.size > 256 * 1024) throw new Error(t('配置文件不能超过 256 KB'));
    var text = await file.text();
    var preview = await sendProfileFile(text, false);
    if (sequence !== profilePreviewSequence) return;
    var summary = preview.summary;
    status.textContent = [file.name,summary.profile,t('{disciplines} 个学科 · {sources} 个数据源 · {journals} 本期刊',summary),
      summary.has_query?t('含高级检索规则'):'',summary.removed_private_fields?t('本机专用字段将跳过'):''].filter(Boolean).join(' · ');
    importedProfile = {text:text,version:preview.version};
    apply.hidden = false;
  } catch (error) {
    if (sequence === profilePreviewSequence) status.textContent = t('校验失败 · {error}',{error:error.message});
  }
}

async function applyProfileFile(){
  if (!importedProfile) return;
  var status = el('profile_import_status'), apply = el('apply_profile');
  apply.disabled = true;
  try {
    var applied = await sendProfileFile(importedProfile.text, true, importedProfile.version);
    importedProfile = null;
    apply.hidden = true;
    await load();
    status.textContent = t('已导入 {profile}',{profile:applied.summary.profile});
  } catch (error) {
    if(error.stale){importedProfile=null;apply.hidden=true;}
    status.textContent = t('导入失败 · {error}',{error:error.message});
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
  data.search=Object.assign({},data.search||{});
  data.search.authors=split(el('search_authors').value);
  data.search.author_mode=el('search_author_mode').value;
  data.sources={};
  [].slice.call(el('sources').querySelectorAll('.row')).forEach(function(r){
    var key=r.dataset.key;
    var prev=(BASE.sources&&BASE.sources[key])||{};
    data.sources[key]=Object.assign({},prev,{
      enabled:r.querySelector('.s-en').checked,
      max_results:parseInt(r.querySelector('.s-max').value||'0',10),
      lookback_days:parseInt(r.querySelector('.s-look').value||'1',10)});
    var query=r.querySelector('.s-query');
    if(query) data.sources[key].query=query.value.trim();
  });
  data.output=Object.assign({},data.output||{});
  data.output.dir=el('out_dir').value.trim();
  data.output.filename_format=el('out_fmt').value.trim();
  data.output.open_on_finish=el('out_open').checked;
  data.output.seen_dedup=el('out_seen_dedup').checked;
  data.output.topic_map=el('topic_map_enabled').checked;
  data.output.topic_ai_labels=el('topic_ai_labels').checked;
  data.output.topic_concurrency=Number(el('topic_concurrency').value||4);
  data.scheduled=Object.assign({},data.scheduled||{});
  data.scheduled.enabled=el('sch_enabled').checked;
  data.scheduled.hour=parseInt(el('sch_hour').value||'8',10);
  data.scheduled.minute=parseInt(el('sch_minute').value||'0',10);
  data.scheduled.on_this_day={enabled:el('otd_enabled').checked,notify:el('otd_notify').checked,
    lang:el('otd_lang').value};
  data.windows=Object.assign({},data.windows||{});
  data.windows.daily_paper_hours=parseInt(el('win_daily').value||'36',10);
  data.windows.manual_paper_hours=parseInt(el('win_manual').value||'240',10);
  data.windows.trials_hours=parseInt(el('win_trials').value||'168',10);
  data.windows.funding_hours=parseInt(el('win_funding').value||'36',10);
  data.windows.news_hours=parseInt(el('win_news').value||'36',10);
  var feedKinds={};
  data.policy_feeds=Array.from(el('policy_feeds').querySelectorAll('input.feed')).map(function(input){
    var url=input.value.trim();
    var kind=input.closest('.row').querySelector('.feed-kind').value;
    if(url&&kind) feedKinds[url]=kind;
    return url;
  }).filter(Boolean);
  if(Object.keys(feedKinds).length) (data.sources.policy||={}).feed_kinds=feedKinds;
  else if(data.sources.policy) delete data.sources.policy.feed_kinds;
  data.journals=[].slice.call(el('journals').querySelectorAll('.row')).map(function(r){
    var iv=r.querySelector('.j-if').value.trim();
    function year(selector){var v=r.querySelector(selector).value; return v?Number(v):null;}
    function indexState(selector){
      var v=r.querySelector(selector).value;
      return v ? v==='yes' : null;
    }
    return {name:r.querySelector('.j-name').value.trim(),
      url:r.querySelector('.j-url').value.trim(),
      rss:r.querySelector('.j-rss').value.trim(),
      category:r.querySelector('.j-cat').value.trim(),
      impact_factor: iv?parseFloat(iv):null,
      jcr:r.querySelector('.j-jcr').value.trim(),
      cas:r.querySelector('.j-cas').value.trim(),
      impact_factor_year:year('.j-if-year'),
      jcr_year:year('.j-jcr-year'),
      cas_year:year('.j-cas-year'),
      metric_year:year('.j-metric-year'),
      cas_top:r.querySelector('.j-cas-top').checked,
      sci:indexState('.j-sci'),
      ssci:indexState('.j-ssci'),
      tags:split(r.querySelector('.j-tags').value),
      aliases:split(r.querySelector('.j-alias').value),
      issns:split(r.querySelector('.j-issn').value)};
  }).filter(function(x){return x.name;});
  return data;
}

function rememberSavedConfig(data, version){
  savedConfigFingerprint=JSON.stringify(data);
  savedConfigVersion=version;
  if(displayedSearchProfile!==null&&displayedSearchProfile!==data.profile){
    document.dispatchEvent(new Event('nd:search-profile-changed'));
  }
  displayedSearchProfile=data.profile;
}

window.ndCanUpdateSearch=function(){
  return BASE!==null&&savedConfigFingerprint===JSON.stringify(collect());
};

window.ndRefreshSearchSettings=async function(){
  var response=await fetch('/api/config',{cache:'no-store'});
  if(!response.ok) return false;
  var updated=await response.json();
  if(!window.ndCanUpdateSearch()) return false;
  BASE=updated;
  render();
  rememberSavedConfig(collect(),response.headers.get('ETag'));
  return true;
};

async function save(){
  var data=collect();
  el('msg').textContent='Saving…'; el('msg').className='';
  try{
    if(!await checkSearchDraft(data,false)){
      el('msg').textContent=t('Review the local search check before saving.');
      el('msg').className='bad';
      return false;
    }
    var r=await fetch('/api/config',{method:'POST',headers:configHeaders(savedConfigVersion),body:JSON.stringify(data)});
    var out=await r.json();
    if(out.ok){
      BASE=data;
      rememberSavedConfig(data,r.headers.get('ETag'));
      el('msg').textContent=t('✓ Saved → {path}',{path:out.path}); el('msg').className='ok';
      loadLaunchdStatus();
      return true;
    }
    el('msg').textContent=t('Save failed. {error}',{error:t(searchError(out))}); el('msg').className='bad'; return false;
  }catch(e){el('msg').textContent='× '+e; el('msg').className='bad'; return false;}
}

async function resetDefaults(){
  if(!confirm(t('Reset to defaults? This overwrites current settings.'))) return;
  var r=await fetch('/api/config/reset',{method:'POST',headers:configHeaders(savedConfigVersion)});
  var out=await r.json();
  if(out.ok){await load(); el('msg').textContent='✓ Reset to defaults'; el('msg').className='ok';}
  else{el('msg').textContent='× '+t(out.error||'Reset failed'); el('msg').className='bad';}
}

var desktopScheduler=false;
async function loadLaunchdStatus(){
  try{
    var r=await fetch('/api/launchd/status'); var s=await r.json();
    var desktop=s.backend==='desktop';
    desktopScheduler=desktop;
    el('launchd_controls').hidden=desktop;
    el('schedule_hint').textContent=t(desktop
      ? 'Save to apply. The app catches up on today’s missed time when it starts or wakes. Minimize the window to keep it running. Quitting stops the scheduled service.'
      : 'After changing the time, click Install / update schedule to apply.');
    var scheduleText=desktop
      ? t(s.loaded?'Desktop schedule: daily at {time} (local time)':'Desktop schedule: off',{time:s.schedule})
      : t('Scheduler: {loaded} / {installed} ({time})',{
          loaded:t(s.loaded?'loaded':'not loaded'),installed:t(s.installed?'installed':'not installed'),time:s.schedule});
    var time=function(value){return new Date(value).toLocaleString(document.documentElement.lang);};
    if(desktop&&s.loaded){
      if(s.state==='running') scheduleText+=' · '+t('Searching now');
      else if(s.state==='waiting') scheduleText+=' · '+t('Waiting to start');
      else if(s.state==='retrying') scheduleText+=' · '+t('Last attempt failed. Retry {time}',{time:time(s.next_run)});
      else if(s.next_run) scheduleText+=' · '+t('Next {time}',{time:time(s.next_run)});
    }
    if(desktop&&s.last_run){
      var states={completed:'Completed',failed:'Failed',skipped:'Skipped',interrupted:'Interrupted',cancelled:'已停止'};
      scheduleText+=' · '+t('Last {time} ({state})',{
        time:time(s.last_run.finished_at),state:t(states[s.last_run.status]||s.last_run.status)});
      if(s.last_run.error) scheduleText+=' · '+t(s.last_run.error);
    }
    el('ldstat').textContent=scheduleText;
    el('ldstat').className='pill'+(s.loaded?' on':'');
  }catch(e){el('ldstat').textContent='Scheduler: read failed';}
}

async function launchd(action){
  if(action==='uninstall' && !confirm(t('Uninstall schedule？'))) return;
  el('msg').textContent='Working…'; el('msg').className='';
  var r=await fetch('/api/launchd/'+action,{method:'POST'});
  var out=await r.json();
  el('msg').textContent = out.ok ? ('✓ '+t(action==='install'?'installed/updated':'Uninstalled')) : t('× Action failed');
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

function recipientRow(x){
  x=x||{}; var d=document.createElement('div'); d.className='row recipient';
  d.innerHTML='<input class="r-address" type="email" placeholder="name@example.com" value="'+esc(x.address)+'">'+
    '<input class="r-time" type="time" value="'+esc(x.time)+'" title="本地推送时间">'+
    '<select class="r-lang"><option value="zh">中文</option><option value="en">English</option><option value="ru">Русский</option></select>'+
    '<button type="button" class="del" onclick="this.closest(\'.row\').remove()">×</button>';
  d.querySelector('.r-lang').value=x.language||'zh';
  return d;
}
function addRecipient(){el('push_recipients').appendChild(recipientRow({language:'zh'}));}

var webhookProviders=['feishu','wecom'];
function showWebhookSettings(settings){
  webhookProviders.forEach(function(provider){
    var id='push_'+provider, configured=Boolean(settings[provider+'_configured']);
    el(id).value='';
    el(id).disabled=false;
    el(id+'_state').textContent=t(configured?'已保存地址':'尚未保存地址');
    el(id+'_remove').checked=false;
    el(id+'_remove').disabled=!configured;
  });
}
webhookProviders.forEach(function(provider){
  var id='push_'+provider;
  el(id+'_remove').addEventListener('change',function(){el(id).disabled=this.checked;});
});
function pushPayload(){
  var recipients=Array.from(el('push_recipients').querySelectorAll('.row.recipient')).map(function(row){
    return {address:row.querySelector('.r-address').value.trim(),
            time:row.querySelector('.r-time').value,
            language:row.querySelector('.r-lang').value};
  }).filter(function(x){return x.address;});
  var webhooks={};
  webhookProviders.forEach(function(provider){
    var id='push_'+provider, value=el(id).value.trim();
    if(el(id+'_remove').checked) webhooks[provider]='';
    else if(value) webhooks[provider]=value;
  });
  return {email:{enabled:el('push_email_enabled').checked,
      recipients:recipients,
      to:recipients.map(function(x){return x.address;}),
      smtp_host:el('push_host').value.trim(),
      smtp_port:parseInt(el('push_port').value||'587',10),
      use_ssl:el('push_security').value==='ssl',
      username:el('push_user').value.trim(),
      from:el('push_from').value.trim(),
      subject_template:el('push_subject').value.trim(),
      public_url:el('push_public_url').value.trim(),
      attach_report:el('push_attach').checked},
    webhooks:webhooks};
}
async function loadPush(){
  PUSH_BASELINE=null;
  try{
    var r=await fetch('/api/push');
    if(!r.ok) return;
    var d=await r.json();
    var e=d.email||{};
    el('push_email_enabled').checked=e.enabled!==false;
    var pbox=el('push_recipients'); pbox.innerHTML='';
    var recips=e.recipients||[];
    if(!recips.length) recips=(e.to||[]).map(function(a){return {address:a,time:'',language:e.language||'zh'};});
    recips.forEach(function(r){pbox.appendChild(recipientRow(r));});
    el('push_host').value=e.smtp_host||'';
    el('push_port').value=e.smtp_port||587;
    el('push_security').value=e.use_ssl?'ssl':'starttls';
    el('push_user').value=e.username||'';
    el('push_from').value=e.from||'';
    el('push_subject').value=e.subject_template||'';
    el('push_public_url').value=e.public_url||'';
    el('push_attach').checked=e.attach_report!==false;
    el('push_pw_state').textContent=d.password_set?'(set)':'(not set)';
    showWebhookSettings(d.webhooks||{});
    PUSH_BASELINE=pushPayload();
  }catch(e){}
}
async function savePush(){
  var current=pushPayload(), changes={};
  Object.keys(current).forEach(function(key){
    if(JSON.stringify(current[key])!==JSON.stringify(PUSH_BASELINE[key])) changes[key]=current[key];
  });
  var pw=el('push_password').value.trim();
  if(pw) changes.smtp_password=pw;
  if(Object.keys(changes).length){
    var r=await fetch('/api/push',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(changes)});
    var out=await r.json();
    if(!out.ok) throw new Error(t(out.error||'Failed to save push settings'));
    showWebhookSettings(out.webhooks||{});
    PUSH_BASELINE=pushPayload();
  }
  if(pw){
    el('push_password').value=''; el('push_pw_state').textContent='(set)';
  }
}

async function testService(path,draft,buttonId,statusId){
  var button=el(buttonId),status=el(statusId);
  button.disabled=true;
  status.textContent='正在测试…';
  try{
    var response=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(draft)});
    var result=await response.json();
    status.textContent=t(result.message||'测试失败，请稍后重试。');
  }catch(e){status.textContent='测试失败，请检查 NeuroDaily 服务是否仍在运行。';}
  finally{button.disabled=false;}
}

function testMail(){
  var email=pushPayload().email;
  return testService('/api/push/test',{
    smtp_host:email.smtp_host, smtp_port:email.smtp_port, use_ssl:email.use_ssl,
    username:email.username, password:el('push_password').value
  },'push_test','push_test_status');
}

function aiPayload(){
  return {enabled:el('ai_enabled').checked,base_url:el('ai_base').value.trim(),model:el('ai_model').value.trim()};
}

function showAiSettings(data){
  el('ai_enabled').checked=data.enabled===true;
  el('ai_base').value=data.base_url||'';
  el('ai_model').value=data.model||'';
  el('ai_key').value='';
  var sources={settings:'已保存',environment:'来自环境变量',file:'来自本机密钥文件'};
  el('ai_key_state').textContent=sources[data.key_source]||'待填写';
  AI_BASELINE=aiPayload();
}

async function loadAi(){
  AI_BASELINE=null;
  try{
    var response=await fetch('/api/ai/settings');
    if(!response.ok) throw new Error();
    showAiSettings(await response.json());
  }catch(e){el('ai_key_state').textContent='暂时无法读取 AI 设置';}
}

async function saveAi(){
  var draft=aiPayload(),key=el('ai_key').value;
  if(!key&&JSON.stringify(draft)===JSON.stringify(AI_BASELINE)) return;
  var response=await fetch('/api/ai/settings',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify(Object.assign(draft,{api_key:key}))});
  var result=await response.json();
  if(!result.ok) throw new Error(t(result.message||'无法保存 AI 设置'));
  showAiSettings(result);
}

function testAi(){
  return testService('/api/ai/test',Object.assign(aiPayload(),{api_key:el('ai_key').value}),
    'ai_test','ai_test_status');
}

async function saveSettings(continueToSearch){
  el('saveRun').disabled=true;
  el('saveOnly').disabled=true;
  el('msg').textContent='Saving…'; el('msg').className='';
  try{
    if(PUSH_BASELINE) await savePush();
    if(AI_BASELINE) await saveAi();
    if(!await save()) return;
    if(continueToSearch){
      if(window.parent!==window){
        window.parent.postMessage({type:'nd-navigate',path:'/run'},location.origin);
      }else{
        location.href='/run';
      }
    }
  }catch(e){ el('msg').className='bad'; el('msg').textContent='× '+e; }
  finally{el('saveRun').disabled=false;el('saveOnly').disabled=false;}
}

function saveAndContinue(){return saveSettings(true);}

async function loadUiLanguage(){
  var field=el('ui_language'),status=el('ui_language_status');
  try{
    var response=await fetch('/api/ui/preferences',{cache:'no-store'});
    if(!response.ok) throw new Error();
    field.value=(await response.json()).language;
    field.disabled=false;
  }catch(e){status.textContent=t('无法读取界面语言。');}
}

el('ui_language').addEventListener('change',async function(){
  var field=el('ui_language'),status=el('ui_language_status');
  field.disabled=true;
  status.textContent='';
  try{
    var response=await fetch('/api/ui/preferences',{
      method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({language:field.value})
    });
    if(!response.ok) throw new Error();
    var language=(await response.json()).language;
    if(window.parent!==window){
      window.parent.postMessage({type:'nd-language',language:language},location.origin);
    }else{
      location.reload();
    }
  }catch(e){
    status.textContent=t('无法保存界面语言。');
    field.value=document.documentElement.lang;
    field.disabled=false;
  }
});

el('search_add_group').onclick=function(){addSearchGroup(true);};
el('search_apply_conditions').onclick=function(){applySearchConditions(false);};
el('search_save_conditions').onclick=function(){applySearchConditions(true);};
el('search_add_set').onclick=function(){addSearchSet(NEXT_SEARCH_SET++,'',true);};
el('search_journal_mode').onchange=showJournalScope;
el('search_preview_button').onclick=previewSearch;
document.querySelector('main').addEventListener('input',function(event){
  if(!event.target.closest('#search_builder, #optimization-workbench')) markPreviewStale();
});
document.querySelector('main').addEventListener('change',function(event){
  if(!event.target.closest('#search_builder, #optimization-workbench')) markPreviewStale();
});
load();
loadUiLanguage();
setInterval(function(){if(desktopScheduler&&!document.hidden) loadLaunchdStatus();},10000);
</script>
</body></html>
"""

SETTINGS_HTML = SETTINGS_HTML.replace("<!-- OPTIMIZATION_HEAD -->", OPTIMIZATION_HEAD).replace(
    "<!-- OPTIMIZATION_WORKBENCH -->", OPTIMIZATION_WORKBENCH
)
