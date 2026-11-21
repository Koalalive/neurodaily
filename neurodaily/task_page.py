"""Render a search task and its delivery receipts."""
from html import escape


_PHASES = {"search": "检索", "report": "日报", "metrics": "期刊指标", "ai": "AI 摘要",
           "geolocation": "AI 地理定位", "delivery": "投递"}
_STATES = {
    "running": "进行中", "pending": "等待中", "sending": "发送中", "completed": "完成",
    "failed": "失败", "partial": "部分完成", "interrupted": "中断", "skipped": "已跳过",
    "accepted": "服务器已接受", "no_new": "没有新内容", "unknown": "结果未确认",
    "ok": "成功", "empty": "无匹配", "timeout": "超时", "limited": "触发限流",
}


def render_task(task: dict, receipts: list[dict], css: str) -> str:
    run_id = task["id"]

    def state(row):
        status = row["status"]
        return escape(_STATES.get(status, status))

    def timestamp(value):
        return escape((value or "")[:19].replace("T", " ")) or "—"

    def table(title, headings, rows, empty):
        if not rows:
            return f"<h3>{title}</h3><p>{empty}</p>"
        head = "".join(f"<th>{heading}</th>" for heading in headings)
        body = "".join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows)
        return f"<h3>{title}</h3><table class='hist'><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"

    stages = [(_PHASES[name], state(row), timestamp(row.get("updated_at")), escape(row.get("error", "")))
              for name, row in task["stages"].items() if name in _PHASES]
    sources = [(escape(name), state(row), str(row.get("fetched", "—")), str(row.get("count", "—")))
               for name, row in sorted(task["sources"].items())]
    destinations = []
    for row in receipts:
        action = ""
        if row["status"] == "failed" and task["status"] != "running" and task["report_ready"]:
            action = f"<button data-retry='{escape(row['destination'], quote=True)}'>重试</button>"
        destinations.append((escape(row["label"]), state(row), str(row["attempts"]),
                             timestamp(row["updated_at"]), escape(row["error"] or ""), action))
    link = f"<a href='/history/{run_id}/report'>打开本次日报</a>" if task["report_ready"] else ""
    error = f"<p role='status'>{escape(task['error'])}</p>" if task.get("error") else ""
    kind = "定时检索" if task["scheduled_for"] else "手动检索"
    refresh = "setTimeout(() => location.reload(), 3000);" if task["status"] == "running" else ""
    return f"""<!doctype html><html lang='zh'><head><meta charset='utf-8'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<title>NeuroDaily 任务 #{run_id}</title>{css}</head><body><main class='wrap'>
<p><a href='/history'>运行历史</a> · <a href='/'>日报首页</a></p>
<h1><span>任务</span> #{run_id} · <span>{kind}</span></h1>
<p><span data-no-i18n>{escape(task['profile'])}</span> · <span>{state(task)}</span> · {task.get('item_count', 0)} <span>条结果</span></p>
<dl><dt>计划执行</dt><dd>{timestamp(task['scheduled_for'])}</dd>
<dt>实际开始</dt><dd>{timestamp(task['started_at'])}</dd>
<dt>记录结束</dt><dd>{timestamp(task['finished_at'])}</dd></dl>
{error}<p>{link}</p>
{table('处理阶段', ('阶段', '状态', '更新时间', '详情'), stages, '暂无处理阶段。')}
{table('来源进度', ('来源', '状态', '抓取', '匹配'), sources, '暂无来源进度。')}
{table('投递记录', ('渠道', '状态', '尝试次数', '更新时间', '详情', ''), destinations, '暂无投递记录。')}
<p id='retry-message' role='status'></p>
</main><script>
const t=window.ndT||String;
if(window.ndT) document.title=t('神通寰宇 · 任务 #{{id}}', {{id:{run_id}}});
{refresh}
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
