"""Render a search task and its delivery receipts."""
from html import escape

from . import mailer
from .delivery_receipts import destination_id
from .task_runs import task_name


_PHASES = {"search": "检索", "report": "日报", "metrics": "期刊指标", "ai": "AI 摘要",
           "geolocation": "AI 地理定位", "topics": "主题建模", "index": "历史索引", "delivery": "投递"}
_STATES = {
    "running": "进行中", "pending": "等待中", "sending": "发送中", "completed": "完成",
    "failed": "失败", "partial": "部分完成", "interrupted": "中断", "skipped": "已跳过", "cancelled": "已停止",
    "superseded": "已由新任务替代",
    "accepted": "服务器已接受", "no_new": "没有新内容", "unknown": "结果未确认",
    "ok": "成功", "empty": "无匹配", "timeout": "超时", "limited": "触发限流",
}
_STATE_CLASS = {
    "completed": "ok", "ok": "ok", "accepted": "ok", "no_new": "ok",
    "running": "run", "sending": "run", "pending": "wait",
    "failed": "bad", "partial": "warn", "interrupted": "warn", "cancelled": "warn",
    "timeout": "bad", "limited": "warn", "unknown": "warn", "empty": "wait",
}


def render_task(task: dict, receipts: list[dict], css: str) -> str:
    run_id = task["id"]

    def state(row):
        status = row["status"]
        css_class = _STATE_CLASS.get(status, "wait")
        return f"<span class='task-state {css_class}'>{escape(_STATES.get(status, status))}</span>"

    def timestamp(value):
        return escape((value or "")[:19].replace("T", " ")) or "—"

    def table(title, headings, rows, empty):
        if not rows:
            return f"<h3>{title}</h3><p class='task-empty'>{empty}</p>"
        head = "".join(f"<th>{heading}</th>" for heading in headings)
        body = "".join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows)
        return f"<h3>{title}</h3><div class='task-table-wrap'><table class='hist task-table'><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>"

    stages = [(_PHASES[name], state(row), timestamp(row.get("updated_at")), escape(row.get("error", "")))
              for name, row in task["stages"].items() if name in _PHASES]
    sources = [(escape(name), state(row), str(row.get("fetched", "—")), str(row.get("count", "—")))
               for name, row in sorted(task["sources"].items())]
    try:
        email_cfg = mailer.load_cfg()
        addresses = {destination_id("email", row["address"]): row["address"]
                     for row in mailer.recipients(email_cfg)}
    except Exception:
        addresses = {}
    destinations = []
    for row in receipts:
        display_label = addresses.get(row["destination"], row["label"])
        action = ""
        if row["status"] == "failed" and task["status"] != "running" and task["report_ready"]:
            action = f"<button data-retry='{escape(row['destination'], quote=True)}'>重试</button>"
        destinations.append((escape(display_label), state(row), str(row["attempts"]),
                             timestamp(row["updated_at"]), escape(row["error"] or ""), action))
    link = f"<a href='/history/{run_id}/report'>打开本次日报</a>" if task["report_ready"] else ""
    action = ""
    if task.get("workflow") and task["status"] in {"running", "interrupted"}:
        command, label = ("cancel", "停止检索") if task["status"] == "running" else ("resume", "继续检索")
        action = f"<button data-task-action='{command}'>{label}</button>"
    error = f"<p role='status'>{escape(task['error'])}</p>" if task.get("error") else ""
    name = task.get("name") or task_name(task.get("profile", ""), task.get("started_at", ""))
    report_date = ((task.get("started_at") or task.get("scheduled_for") or "")[:10])
    refresh = "setTimeout(() => location.reload(), 3000)" if task["status"] == "running" else "null"
    return f"""<!doctype html><html lang='zh'><head><meta charset='utf-8'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<meta name='nd-report-date' content='{escape(report_date)}'>
<title>{escape(name)} · 日报</title>{css}<style>
.task-head{{margin:12px 0 26px;padding-bottom:20px;border-bottom:1px solid #2c2c2a}}
.task-head h1{{font-size:clamp(1.7rem,3vw,2.8rem);line-height:1.15;margin:0 0 8px}}
.task-head .task-meta{{color:#979791;font-size:.82rem;display:flex;flex-wrap:wrap;gap:8px 18px;align-items:center}}
.task-state{{display:inline-block;padding:2px 8px;border:1px solid currentColor;border-radius:1px;font-size:.7rem;letter-spacing:.04em}}
.task-state.ok{{color:#8da7a1}} .task-state.run{{color:#c8a96b}} .task-state.bad{{color:#c47a6b}} .task-state.warn{{color:#c6a46b}} .task-state.wait{{color:#77756e}}
.task-table-wrap{{overflow-x:auto;border-top:1px solid #2c2c2a}}
.task-table th{{background:transparent;color:#77756e;font-size:.68rem;letter-spacing:.06em;text-transform:uppercase}}
.task-table td{{font-size:.78rem;color:#c6c1b7;border-bottom-color:rgba(255,255,255,.08)}}
.task-empty{{border:1px dashed #2c2c2a;padding:12px;color:#77756e}}
.task-actions{{display:flex;flex-wrap:wrap;gap:12px;margin:18px 0}}
.task-actions a,.task-actions button{{font-size:.8rem}}
</style></head><body><main class='wrap'>
<p><a href='/history'>运行历史</a> · <a href='/'>日报首页</a></p>
<div class='task-head'><h1>{escape(name)}</h1><div class='task-meta'><span data-no-i18n>{escape(task.get('profile',''))}</span><span>{state(task)}</span><span>{task.get('item_count', 0)} 条结果</span></div></div>
<dl><dt>计划执行</dt><dd>{timestamp(task['scheduled_for'])}</dd>
<dt>实际开始</dt><dd>{timestamp(task['started_at'])}</dd>
<dt>记录结束</dt><dd>{timestamp(task['finished_at'])}</dd></dl>
{error}<p class='task-actions'>{link} {action}</p>
{table('处理阶段', ('阶段', '状态', '更新时间', '详情'), stages, '暂无处理阶段。')}
{table('来源进度', ('来源', '状态', '抓取', '匹配'), sources, '暂无来源进度。')}
{table('投递记录', ('渠道', '状态', '尝试次数', '更新时间', '详情', ''), destinations, '暂无投递记录。')}
<p id='retry-message' role='status'></p>
</main><script>
const t=window.ndT||String;

const reloadTimer = {refresh};
const taskAction = document.querySelector('[data-task-action]');
if (taskAction) taskAction.addEventListener('click', async () => {{
  clearTimeout(reloadTimer);
  taskAction.disabled = true;
  const message = document.getElementById('retry-message');
  const action = taskAction.dataset.taskAction;
  try {{
    const response = await fetch('/api/run/{run_id}/' + action, {{method: 'POST'}});
    if (response.ok && action === 'resume') {{ setTimeout(() => location.reload(), 500); return; }}
    if (response.ok) {{
      message.textContent = t('正在停止检索，等待当前操作结束…');
      const poll = setInterval(async () => {{
        try {{
          const r = await fetch('/api/history/{run_id}', {{cache: 'no-store'}});
          if (r.ok && (await r.json()).task?.status !== 'running') {{
            clearInterval(poll); location.reload();
          }}
        }} catch (_) {{}}
      }}, 2000);
      return;
    }}
    message.textContent = (await response.json()).error || t('任务操作失败。');
  }} catch (_) {{ message.textContent = t('无法连接服务。'); }}
  taskAction.disabled = false;
}});
document.querySelectorAll('[data-retry]').forEach(button => {{
  button.addEventListener('click', async () => {{
    const message = document.getElementById('retry-message');
    button.disabled = true;
    message.textContent = t('正在重试投递…');
    try {{
      const response = await fetch('/api/history/{run_id}/delivery/' +
        encodeURIComponent(button.dataset.retry) + '/retry', {{method: 'POST'}});
      if (response.ok) {{ location.reload(); return; }}
      const body = await response.json();
      message.textContent = body.error || t('重试失败。');
    }} catch (_) {{ message.textContent = t('无法连接服务。'); }}
    button.disabled = false;
  }});
}});
</script></body></html>"""
