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
#cancel{background:#18181b;color:var(--muted);border:1px solid var(--line)}
#msg{margin-top:14px;font-size:.88rem;color:var(--muted)}
#msg.ok{color:#34d399}#msg.bad{color:#f87171}
small{display:block;color:var(--muted);font-size:.78rem;margin-top:8px}
</style></head><body>
<main>
  <h1>本次检索范围</h1>
  <p>只影响这一次运行，不会修改每日/定时设置。</p>
  <label for="hours">时间范围（小时）</label>
  <input id="hours" type="number" min="1" max="8760" value="36" autofocus>
  <small>例如 36 = 最近 36 小时；168 = 最近 7 天。论文、临床试验、Funding、新闻都按此范围。</small>
  <div class="row">
    <button id="cancel" type="button">取消</button>
    <button id="go" type="button">开始检索并推送</button>
  </div>
  <div id="msg"></div>
</main>
<script>
(function(){
  var msg=document.getElementById('msg');
  function set(t,ok){msg.textContent=t;msg.className=ok===true?'ok':(ok===false?'bad':'');}
  document.getElementById('cancel').onclick=function(){location.href='/';};
  document.getElementById('go').onclick=async function(){
    var h=parseInt(document.getElementById('hours').value||'36',10);
    if(!h||h<1||h>8760){set('请输入 1–8760 小时',false);return;}
    set('已启动，正在检索…');
    try{
      var r=await fetch('/api/run?force=1&hours='+h,{method:'POST'});
      var d=await r.json();
      if(!r.ok){throw new Error(d.detail||d.error||'启动失败');}
      var start=d.started_at, tries=0;
      var t=setInterval(async function(){
        tries++;
        try{
          var s=await (await fetch('/api/status',{cache:'no-store'})).json();
          if(s.last_run&&start&&s.last_run>=start){
            clearInterval(t);set('✅ 完成（'+s.item_count+' 条），正在打开报告…',true);
            setTimeout(function(){location.href='/report/latest';},500);
          }else if(tries>240){clearInterval(t);set('超时，请到 History 查看',false);}
        }catch(e){}
      },3000);
    }catch(e){set('❌ '+e.message,false);}
  };
})();
</script>
</body></html>
"""
