"""Minimal "Run now" page: one range for this run, no config writes."""

RUN_HTML = r"""<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>NeuroDaily — Run now</title>
<style>
:root{--bg:#0b0b0c;--panel:#121214;--line:#2a2a2e;--text:#e9e9ee;--muted:#9a9aa3;--accent:#38bdf8}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.6 -apple-system,Segoe UI,Roboto,sans-serif}
main{max-width:560px;margin:12vh auto;padding:24px;background:var(--panel);border:1px solid var(--line);border-radius:16px}
h1{margin:0 0 6px;font-size:1.25rem;color:var(--accent)}
p{color:var(--muted);margin:0 0 18px;font-size:.9rem}
label{display:block;font-size:.85rem;color:var(--muted);margin-bottom:6px}
input{width:100%;background:#18181b;border:1px solid var(--line);color:var(--text);border-radius:10px;padding:10px 12px;font-size:1rem}
.row{display:flex;gap:10px;margin-top:16px}
button{flex:1;border:0;border-radius:10px;padding:11px 14px;font-weight:700;cursor:pointer}
#go{background:linear-gradient(90deg,#38bdf8,#818cf8);color:#04121c}
#go:disabled{opacity:.55;cursor:wait}
#cancel{background:#18181b;color:var(--muted);border:1px solid var(--line)}
#msg{margin-top:14px;font-size:.88rem;color:var(--muted)}
#msg.ok{color:#34d399}#msg.bad{color:#f87171}
small{display:block;color:var(--muted);font-size:.78rem;margin-top:8px}
</style></head><body>
<main>
  <h1>本次检索范围</h1>
  <p>日报生成后自动打开。AI 摘要和投递会继续处理。</p>
  <label for="hours">临时覆盖时间范围（小时，可选）</label>
  <input id="hours" type="number" min="1" max="8760" value="240" placeholder="默认 240；留空使用已保存设置">
  <small>默认 240 小时（10 天）；可改为 36（最近 36 小时）等。</small>
  <div class="row">
    <button id="cancel" type="button">返回设置</button>
    <button id="go" type="button">开始检索</button>
  </div>
  <div id="msg" role="status"></div>
  <a id="task" hidden>查看任务进度</a>
</main>
<script>
(function(){
  var msg=document.getElementById('msg');
  var go=document.getElementById('go');
  var task=document.getElementById('task');
  var t=window.ndT||function(message,values){
    return message.replace(/\{(\w+)\}/g,function(match,key){return values&&key in values?values[key]:match;});
  };
  var submitting=false, sharedBusy=false, checking=false, announcedReport=null;
  function set(t,ok){msg.textContent=t;msg.className=ok===true?'ok':(ok===false?'bad':'');}
  function updateButton(){
    go.disabled=submitting||sharedBusy;
    go.textContent=t(go.disabled?'正在检索…':'开始检索');
  }
  function failed(message){submitting=false;updateButton();set(message,false);}
  async function currentSearch(){
    var response=await fetch('/api/search/status',{cache:'no-store'});
    if(!response.ok) throw new Error();
    return (await response.json()).search;
  }
  function progress(run){
    task.hidden=!run.id;
    if(run.id) task.href='/history/'+run.id;
    var sources=Object.values(run.sources||{});
    var done=sources.filter(function(source){return !['pending','running'].includes(source.status);}).length;
    var phases={metrics:'正在更新期刊指标…',ai:'正在生成 AI 摘要…',geolocation:'正在定位地图条目…',topics:'正在生成主题景观…',report:'正在保存日报…',index:'正在更新历史索引…',delivery:'日报已生成，正在投递…'};
    var status=t(phases[run.phase]||(run.scheduled_for?'定时检索正在运行':'检索正在运行'));
    set(status+(run.phase==='search'&&sources.length?' · '+t('已处理 {done}/{total} 个来源',{done:done,total:sources.length}):''));
  }
  async function refresh(){
    if(submitting||checking||document.hidden) return;
    checking=true;
    try{
      var run=await currentSearch();
      if(submitting) return;
      var next=!!run&&run.status==='running';
      if(next) progress(run);
      else if(run&&run.workflow&&run.status==='interrupted'){
        task.hidden=false;
        task.href='/history/'+run.id;
        set(t('上次检索中断。打开任务详情继续。'));
      }
      else if(sharedBusy) set('');
      sharedBusy=next;
      updateButton();
    }catch(e){}
    finally{checking=false;}
  }
  async function poll(id,tries){
    try{
      var run=await currentSearch();
      if(!run||run.id!==id){
        var response=await fetch('/api/history/'+id);
        if(response.ok) run=(await response.json()).task;
      }
      if(run && run.id===id){
        if(run.report_ready && announcedReport!==id){
          announcedReport=id;
          if(window.parent===window){
            set(t('已生成日报（{count} 条），正在打开…',{count:run.item_count}),true);
            location.href='/history/'+id+'/report';
            return;
          }
          window.parent.postMessage({type:'nd-report',taskId:id,status:run.status,revision:run.report_revision},location.origin);
        }
        if(run.status!=='running'){
          submitting=false;
          sharedBusy=false;
          updateButton();
          if(run.report_ready){
            set(t('已生成日报（{count} 条）。',{count:run.item_count}),true);
          }else{
            failed(t(run.error||'本次检索未生成报告'));
          }
          return;
        }
        progress(run);
      }
    }catch(e){}
    if(tries>=1800){failed(t('等待超时，请在运行历史中查看结果'));return;}
    setTimeout(function(){poll(id,tries+1);},2000);
  }
  document.getElementById('cancel').onclick=function(){location.href='/settings';};
  go.onclick=async function(){
    var value=document.getElementById('hours').value;
    var h=Number(value);
    if(value&&(!Number.isInteger(h)||h<1||h>8760)){failed(t('请输入 1–8760 的整数小时'));return;}
    submitting=true;
    updateButton();
    set(t('已启动，正在检索…'));
    try{
      var r=await fetch('/api/run?force=1'+(value?'&hours='+h:''),{method:'POST'});
      var d=await r.json();
      if(r.status===409){
        submitting=false;
        sharedBusy=true;
        updateButton();
        set(t('已有检索正在运行。'));
        await refresh();
        return;
      }
      if(!r.ok){throw new Error(t(d.detail||d.error||'启动失败'));}
      poll(d.task_id,0);
    }catch(e){failed('❌ '+e.message);}
  };
  go.disabled=true;
  refresh();
  setInterval(refresh,2000);
  document.addEventListener('visibilitychange',refresh);
})();
</script>
</body></html>
"""
