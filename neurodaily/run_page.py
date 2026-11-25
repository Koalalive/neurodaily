"""Run-now page with an editorial live progress view."""

RUN_HTML = r"""<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>NeuroDaily — Run now</title>
<style>
:root{--bg:#090a0c;--panel:#0e1013;--line:rgba(255,255,255,.10);--text:#ece9e2;--muted:#979791;--accent:#c8a96b}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:15px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC",sans-serif}
header.run-head{padding:30px 24px 24px;border-bottom:1px solid var(--line);background:radial-gradient(60% 120% at 10% 0%,#17171a 0%,transparent 70%),var(--bg)}
.run-wrap{max-width:900px;margin:0 auto;padding:38px 24px 70px}
.run-kicker{color:var(--accent);font-size:11px;letter-spacing:.17em;font-weight:600}
h1{margin:10px 0 5px;font-size:clamp(2rem,4vw,3.2rem);line-height:1.08;letter-spacing:-.03em}
.sub{color:var(--muted);margin:0;font-size:.9rem}
#setup,.run-live{background:transparent;border:0;border-top:1px solid var(--line);padding:26px 0 0;margin:0 0 24px}
label{display:block;font-size:.8rem;color:var(--muted);margin-bottom:7px}
input{width:100%;background:var(--panel);border:1px solid var(--line);color:var(--text);border-radius:2px;padding:10px 12px;font-size:.95rem}
small{display:block;color:var(--muted);font-size:.76rem;margin-top:7px}
.actions{display:flex;flex-wrap:wrap;gap:10px;margin-top:20px;align-items:center}
button{font:inherit;font-size:.8rem;border:1px solid var(--line);border-radius:2px;padding:8px 14px;cursor:pointer;background:transparent;color:var(--muted)}
button:hover{border-color:var(--accent);color:var(--accent)}
#go{background:var(--accent);border-color:var(--accent);color:#171207;font-weight:700;padding:9px 18px}
#go:hover{background:#ddc183;border-color:#ddc183;color:#171207}
#go:disabled{background:#2a261e;border-color:#5d5547;color:#bdb5a5;cursor:wait}
#cancel{background:transparent}
.live-top{display:flex;align-items:flex-start;justify-content:space-between;gap:18px;margin-bottom:20px}
.live-kicker{color:var(--accent);font-size:10px;letter-spacing:.15em}
.live-title{font-family:"Source Serif 4","Iowan Old Style","Noto Serif CJK SC","Songti SC",Georgia,serif;font-size:clamp(1.5rem,3vw,2.2rem);margin:6px 0 0;font-weight:600;letter-spacing:-.02em}
#elapsed{color:var(--muted);font-size:.78rem;font-variant-numeric:tabular-nums;white-space:nowrap;padding-top:7px}
.progress-meta{display:flex;justify-content:space-between;gap:12px;color:var(--muted);font-size:.76rem;margin:10px 0 7px}
.progress-track{height:3px;background:#22221f;overflow:hidden}
#progress-fill{width:0;height:100%;background:var(--accent);transition:width .35s ease}
.stage-list{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:0;list-style:none;margin:18px 0 0;padding:0;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}
.stage{padding:12px 12px 11px 0;min-width:0;color:#77756e;border-right:1px solid var(--line);font-size:.74rem}
.stage:last-child{border-right:0}
.stage.done{color:var(--accent2)}
.stage.running{color:var(--text)}
.stage.failed{color:#c47a6b}
.stage.partial{color:#c6a46b}
.stage b{display:block;font-size:.68rem;letter-spacing:.06em;font-weight:500;color:inherit}
.stage span{display:block;margin-top:3px;color:#77756e;font-size:.66rem}
.section-head{display:flex;justify-content:space-between;align-items:baseline;gap:12px;margin:28px 0 10px}
.section-head h2{font-family:"Source Serif 4","Iowan Old Style","Noto Serif CJK SC","Songti SC",Georgia,serif;font-size:1.25rem;margin:0;font-weight:600}
#source-summary{color:var(--muted);font-size:.75rem}
.source-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0;border-top:1px solid var(--line)}
.source{border-bottom:1px solid var(--line);padding:12px 14px 11px 0;min-width:0}
.source:nth-child(even){padding-left:14px;border-left:1px solid var(--line)}
.source-line{display:flex;align-items:center;justify-content:space-between;gap:8px}
.source-name{font-family:"Source Serif 4","Iowan Old Style","Noto Serif CJK SC",Georgia,serif;font-size:.85rem;color:var(--text)}
.source-state{font-size:.65rem;letter-spacing:.04em;color:var(--muted)}
.source-state.ok{color:var(--accent2)}.source-state.bad{color:#c47a6b}
.source-detail{color:#77756e;font-size:.68rem;margin-top:3px}
.live-actions{margin-top:22px;display:flex;flex-wrap:wrap;gap:12px;align-items:center}
#msg{margin-top:18px;color:var(--muted);font-size:.82rem;min-height:1.4em}
#msg.ok{color:var(--accent2)}#msg.bad{color:#c47a6b}
#task,#open-report{color:var(--accent);font-size:.8rem;text-decoration:none;border-bottom:1px solid var(--accent);padding-bottom:2px}
#task:hover,#open-report:hover{color:#e3cfa0;border-color:#e3cfa0}
[hidden]{display:none!important}
@media(max-width:640px){
  header.run-head{padding:24px 18px 20px}.run-wrap{padding:28px 18px 56px}
  .stage-list{grid-template-columns:repeat(2,minmax(0,1fr))}.stage:nth-child(2){border-right:0}.stage:nth-child(-n+2){border-bottom:1px solid var(--line)}
  .source-grid{grid-template-columns:1fr}.source:nth-child(even){padding-left:0;border-left:0}
  .live-top{display:block}#elapsed{margin-top:8px}
}
</style></head><body>
<header class="run-head"><div class="run-kicker">NEURODAILY / RUN</div><h1>本次检索范围</h1><p class="sub">日报生成后会自动打开；AI 摘要、地图和主题标注会继续在后台完成。</p></header>
<main class="run-wrap">
  <section id="setup">
    <label for="hours">临时覆盖时间范围（小时，可选）</label>
    <input id="hours" type="number" min="1" max="8760" value="240" placeholder="默认 240；留空使用已保存设置">
    <small>默认 240 小时（10 天）；可改为 36（最近 36 小时）等。</small>
    <div class="actions"><button id="cancel" type="button">返回设置</button><button id="go" type="button">▸ 开始检索</button></div>
  </section>
  <section id="live" class="run-live" hidden>
    <div class="live-top"><div><div class="live-kicker">RUN #<span id="run-id"></span></div><h2 class="live-title" id="run-title">检索进行中</h2></div><div id="elapsed">00:00</div></div>
    <div class="progress-meta"><span id="progress-label">准备中</span><span id="progress-percent">0%</span></div>
    <div class="progress-track" role="progressbar" aria-label="检索进度" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0"><div id="progress-fill"></div></div>
    <ol class="stage-list" id="stages"></ol>
    <div class="section-head"><h2>来源进度</h2><span id="source-summary"></span></div>
    <div class="source-grid" id="sources"></div>
    <div class="live-actions"><button id="cancel-run" type="button">取消检索</button><a id="task" href="#">查看任务详情 ↗</a><a id="open-report" href="#" hidden>打开已生成日报 ↗</a></div>
  </section>
  <div id="msg" role="status"></div>
</main>
<script>
(function(){
  var setup=document.getElementById('setup'),live=document.getElementById('live');
  var msg=document.getElementById('msg'),go=document.getElementById('go'),task=document.getElementById('task'),openReport=document.getElementById('open-report'),cancelRun=document.getElementById('cancel-run');
  var t=window.ndT||function(message,values){return message.replace(/\{(\w+)\}/g,function(match,key){return values&&key in values?values[key]:match;});};
  var submitting=false,sharedBusy=false,checking=false,runId=null,elapsedTimer=null;
  var order=['search','metrics','ai','geolocation','topics','report','index','delivery'];
  var stageLabels={search:'来源抓取',metrics:'期刊指标',ai:'AI 摘要',geolocation:'研究地图',topics:'主题景观',report:'保存日报',index:'历史索引',delivery:'投递'};
  var phaseLabels={search:'正在抓取来源…',metrics:'正在更新期刊指标…',ai:'正在生成 AI 摘要…',geolocation:'正在定位地图条目…',topics:'正在生成主题景观…',report:'正在保存日报…',index:'正在更新历史索引…',delivery:'日报已生成，正在投递…'};
  function set(text,ok){msg.textContent=text;msg.className=ok===true?'ok':(ok===false?'bad':'');}
  function updateButton(){go.disabled=submitting||sharedBusy;go.textContent=t(go.disabled?'正在检索…':'▸ 开始检索');}
  function fmtElapsed(run){if(!run||!run.started_at)return '00:00';var start=new Date(run.started_at);var end=run.finished_at?new Date(run.finished_at):new Date();var seconds=Math.max(0,Math.floor((end-start)/1000));return String(Math.floor(seconds/60)).padStart(2,'0')+':'+String(seconds%60).padStart(2,'0');}
  function stateOf(name,run){var row=(run.stages||{})[name];if(row&&row.status){return ({completed:'done',cancelled:'failed',skipped:'done'})[row.status]||row.status;}var index=order.indexOf(name),current=order.indexOf(run.phase);if(current>=0&&index<current)return 'done';if(name===run.phase)return 'running';return 'pending';}
  function renderStages(run){var el=document.getElementById('stages');el.replaceChildren();order.forEach(function(name){var state=stateOf(name,run);var li=document.createElement('li');li.className='stage '+state;var b=document.createElement('b');b.textContent=stageLabels[name];var s=document.createElement('span');s.textContent=state==='done'?'已完成':state==='running'?'进行中':state==='failed'?'失败':state==='partial'?'部分完成':'等待';li.append(b,s);el.append(li);});}
  function renderSources(run){var el=document.getElementById('sources');el.replaceChildren();var rows=Object.keys(run.sources||{}).sort();var done=0;rows.forEach(function(name){var row=run.sources[name]||{};var state=row.status||'pending';if(!['pending','running'].includes(state))done++;var card=document.createElement('div');card.className='source';var line=document.createElement('div');line.className='source-line';var title=document.createElement('span');title.className='source-name';title.textContent=name;var status=document.createElement('span');status.className='source-state '+((state==='ok'||state==='empty')?'ok':(state==='failed'?'bad':''));status.textContent=state==='ok'?'完成':state==='empty'?'无命中':state==='running'?'抓取中':state==='pending'?'等待':state==='failed'?'失败':state;line.append(title,status);var detail=document.createElement('div');detail.className='source-detail';detail.textContent=(row.fetched==null?'—':row.fetched)+' 抓取 · '+(row.count==null?'—':row.count)+' 命中'+(row.ms?' · '+(row.ms/1000).toFixed(1)+'s':'');card.append(line,detail);el.append(card);});document.getElementById('source-summary').textContent=done+'/'+rows.length+' 完成';}
  function render(run){if(!run){setup.hidden=false;live.hidden=true;return;}setup.hidden=true;live.hidden=false;runId=run.id;document.getElementById('run-id').textContent=run.id;document.getElementById('run-title').textContent=run.status==='completed'?'检索完成':run.status==='failed'?'检索失败':'检索进行中';var label=phaseLabels[run.phase]||'检索进行中';var done=order.filter(function(n){return stateOf(n,run)==='done'}).length;var current=order.indexOf(run.phase);var percent=Math.min(100,Math.round(((done+(current>=0?0.5:0))/order.length)*100));if(run.report_ready&&run.status==='running'){label='日报已生成，AI/地图继续处理…';percent=Math.max(percent,90);}if(run.status==='completed')percent=100;document.getElementById('progress-label').textContent=label;document.getElementById('progress-percent').textContent=percent+'%';document.getElementById('progress-fill').style.width=percent+'%';document.querySelector('.progress-track').setAttribute('aria-valuenow',String(percent));document.getElementById('elapsed').textContent=fmtElapsed(run);renderStages(run);renderSources(run);task.href='/history/'+run.id;if(run.report_file||run.report_ready){openReport.hidden=false;openReport.href='/history/'+run.id+'/report';}else{openReport.hidden=true;}cancelRun.hidden=run.status!=='running';if(run.status==='completed'){set('检索完成 · '+run.item_count+' 条结果',true);}else if(run.status==='failed'){set(run.error||'检索失败',false);}else if(run.report_ready){set('日报已生成，后台仍在完善摘要、地图和主题。',true);}else{set(label);}if(elapsedTimer){clearInterval(elapsedTimer);}if(run.status==='running'){elapsedTimer=setInterval(function(){document.getElementById('elapsed').textContent=fmtElapsed(run);},1000);}}
  async function currentSearch(){var response=await fetch('/api/search/status',{cache:'no-store'});if(!response.ok)throw new Error();return (await response.json()).search;}
  async function refresh(){if(checking||document.hidden)return;checking=true;try{var run=await currentSearch();var running=!!run&&run.status==='running';if(running){sharedBusy=true;render(run);}else{sharedBusy=false;setup.hidden=false;live.hidden=true;if(run&&run.status==='interrupted'){set('上次检索中断，可在运行历史中继续。');}else{set('');}}updateButton();}catch(e){}finally{checking=false;}}
  async function poll(id,tries){try{var run=await currentSearch();if(!run||run.id!==id){var response=await fetch('/api/history/'+id);if(response.ok)run=(await response.json()).task;}if(run&&run.id===id){render(run);if(run.status!=='running'){submitting=false;sharedBusy=false;updateButton();if(window.parent!==window)window.parent.postMessage({type:'nd-report',taskId:id,status:run.status,revision:run.report_revision},location.origin);return;}}}catch(e){}if(tries>=1800){failed('等待超时，请在运行历史中查看结果');return;}setTimeout(function(){poll(id,tries+1);},2000);}
  function failed(text){submitting=false;updateButton();set(text,false);}
  cancelRun.onclick=async function(){if(!runId)return;cancelRun.disabled=true;try{var r=await fetch('/api/run/'+runId+'/cancel',{method:'POST'});if(!r.ok)throw new Error();set('正在取消…');}catch(e){set('取消失败，请查看任务详情。',false);}finally{setTimeout(function(){cancelRun.disabled=false;},1500);}};
  document.getElementById('cancel').onclick=function(){location.href='/settings';};
  go.onclick=async function(){var value=document.getElementById('hours').value;var h=Number(value);if(value&&(!Number.isInteger(h)||h<1||h>8760)){failed('请输入 1–8760 的整数小时');return;}submitting=true;updateButton();set('已启动，正在检索…');try{var r=await fetch('/api/run?force=1'+(value?'&hours='+h:''),{method:'POST'});var d=await r.json();if(r.status===409){submitting=false;sharedBusy=true;updateButton();set('已有检索正在运行。');await refresh();return;}if(!r.ok)throw new Error(t(d.detail||d.error||'启动失败'));runId=d.task_id;poll(d.task_id,0);}catch(e){failed('× '+e.message);}};
  go.disabled=true;refresh();setInterval(refresh,2000);document.addEventListener('visibilitychange',refresh);
})();
</script>
</body></html>
"""
