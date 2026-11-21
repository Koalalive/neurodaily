"""Tab container for the desktop WebView and local browser workspace."""
from __future__ import annotations

import json


_COPY = {
    "zh": {"settings": "设置", "dashboard": "最新日报", "history": "运行历史", "run": "开始检索",
           "report": "日报", "task": "任务", "close": "关闭", "tabs": "工作区标签页"},
    "en": {"settings": "Settings", "dashboard": "Latest report", "history": "Run history", "run": "Run search",
           "report": "Report", "task": "Task", "close": "Close", "tabs": "Workspace tabs"},
    "ru": {"settings": "Настройки", "dashboard": "Последний отчёт", "history": "История запусков", "run": "Поиск",
           "report": "Отчёт", "task": "Задача", "close": "Закрыть", "tabs": "Вкладки"},
}


def render_workspace(language: str, after: int) -> str:
    return (_PAGE.replace("__LANG__", language)
            .replace("__COPY__", json.dumps(_COPY, ensure_ascii=False))
            .replace("__AFTER__", str(after)))


_PAGE = r"""<!doctype html><html lang="__LANG__"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>NeuroDaily · 神通寰宇</title>
<style>
*{box-sizing:border-box}body{margin:0;height:100dvh;display:flex;flex-direction:column;background:#0b0b0c;color:#ededf2;font:14px -apple-system,Segoe UI,sans-serif}
.toolbar{display:flex;align-items:center;gap:8px;padding:8px 12px;background:#17171a;border-bottom:1px solid #333338;overflow-x:auto}
.brand{font-weight:700;white-space:nowrap;margin-right:8px;color:#a5e6fc}button{font:inherit;white-space:nowrap;color:inherit;border:1px solid #3a3a40;background:#202024;border-radius:6px;padding:6px 9px;cursor:pointer}
button:hover{background:#33333a}button:focus-visible{outline:2px solid #67dafa;outline-offset:2px}
#tabs{display:flex;overflow-x:auto;flex-shrink:0;min-height:41px;padding:5px 8px 0;gap:3px;border-bottom:1px solid #333338;background:#111114}
.tab{display:flex;align-items:center;gap:2px;border-bottom:2px solid transparent}.tab:has([aria-selected=true]){border-color:#67dafa;background:#23232a}
.tab button{background:transparent;border:0;padding:5px 8px}.tab button:hover{background:#34343c}.tab .close{font-size:16px;color:#adadb9}
#panes{flex:1;min-height:0}iframe{border:0;width:100%;height:100%;background:#0b0b0c}iframe[hidden]{display:none}
</style></head><body>
<header class="toolbar"><span class="brand">NeuroDaily</span>
<button data-open="/settings" data-label="settings"></button><button data-open="/" data-label="dashboard"></button>
<button data-open="/history" data-label="history"></button><button data-open="/run" data-label="run"></button>
</header>
<div id="tabs" role="tablist"></div><main id="panes"></main>
<script>
(() => {
  const translations = __COPY__;
  let language = document.documentElement.lang;
  let scanAfter = __AFTER__;
  let busy = false;
  let selected;
  let serial = 0;
  const tabs = [];
  const announced = new Set();
  const unfinished = new Set();
  const tablist = document.getElementById('tabs');
  const panes = document.getElementById('panes');
  const toolbar = document.querySelector('.toolbar');
  const word = key => translations[language][key];
  const localUrl = path => new URL(path, location.origin);
  const route = url => url.origin === location.origin &&
    /^(\/|\/settings|\/run|\/history(?:\/compare|\/\d+(?:\/report)?)?|\/report\/latest|\/reports\/[^/]+)$/.test(url.pathname);

  function title(path) {
    const pathname = localUrl(path).pathname;
    if (pathname === '/settings') return word('settings');
    if (pathname === '/run') return word('run');
    if (pathname === '/history' || pathname === '/history/compare') return word('history');
    const run = pathname.match(/^\/history\/(\d+)(\/report)?$/);
    if (run) return `${word(run[2] ? 'report' : 'task')} #${run[1]}`;
    return word('dashboard');
  }

  function labels() {
    tablist.setAttribute('aria-label', word('tabs'));
    toolbar.querySelectorAll('[data-label]').forEach(button => {
      button.textContent = word(button.dataset.label);
    });
    tabs.forEach(tab => {
      tab.button.textContent = title(tab.path);
      tab.iframe.title = tab.button.textContent;
      tab.close.setAttribute('aria-label', `${word('close')} ${tab.button.textContent}`);
    });
  }

  function activate(tab) {
    selected = tab;
    tabs.forEach(item => {
      const current = item === tab;
      item.iframe.hidden = !current;
      item.button.setAttribute('aria-selected', String(current));
      item.button.tabIndex = current ? 0 : -1;
    });
  }

  function refresh(tab) {
    const url = localUrl(tab.path);
    url.searchParams.set('ui', '1');
    tab.iframe.src = url.href;
  }

  function openTab(path) {
    const id = ++serial;
    const group = document.createElement('div');
    group.className = 'tab';
    group.setAttribute('role', 'presentation');
    const button = document.createElement('button');
    button.type = 'button';
    button.id = `tab-${id}`;
    button.setAttribute('role', 'tab');
    button.setAttribute('aria-controls', `pane-${id}`);
    const close = document.createElement('button');
    close.type = 'button';
    close.className = 'close';
    close.textContent = '×';
    const iframe = document.createElement('iframe');
    iframe.id = `pane-${id}`;
    iframe.setAttribute('aria-labelledby', button.id);
    const tab = {path, group, iframe, button, close};
    button.addEventListener('click', () => activate(tab));
    close.addEventListener('click', () => {
      const index = tabs.indexOf(tab);
      tabs.splice(index, 1);
      group.remove();
      iframe.remove();
      if (selected !== tab) return;
      if (tabs.length) activate(tabs[Math.min(index, tabs.length - 1)]);
      else openTab('/settings');
    });
    iframe.addEventListener('load', () => connect(iframe));
    group.append(button, close);
    tabs.push(tab);
    tablist.append(group);
    refresh(tab);
    panes.append(iframe);
    labels();
    activate(tab);
    group.scrollIntoView({block: 'nearest', inline: 'nearest'});
    return tab;
  }

  function connect(iframe) {
    const doc = iframe.contentDocument;
    if (!doc) return;
    doc.defaultView.addEventListener('click', event => {
      if (event.defaultPrevented || event.button !== 0) return;
      const control = event.target.closest?.('#runNow, #cancel, a[href]');
      if (!control) return;
      if (control.tagName === 'BUTTON') {
        if (control.disabled) return;
        event.preventDefault();
        event.stopImmediatePropagation();
        openTab(control.id === 'runNow' ? '/run' : '/settings');
        return;
      }
      if (control.getAttribute('href').startsWith('#')) return;
      const target = new URL(control.href);
      if (!['http:', 'https:'].includes(target.protocol)) return;
      if (control.hasAttribute('download')) {
        if (target.origin !== location.origin) return;
        event.preventDefault();
        event.stopImmediatePropagation();
        const download = document.createElement('a');
        if (target.pathname === '/api/config/export') target.searchParams.set('language', language);
        download.href = target.href;
        download.download = control.download;
        document.body.append(download);
        download.click();
        download.remove();
        return;
      }
      if (route(target) || target.origin !== location.origin) {
        event.preventDefault();
        event.stopImmediatePropagation();
        if (route(target)) {
          target.searchParams.delete('ui');
          openTab(`${target.pathname}${target.search}${target.hash}`);
        } else if (window.__TAURI_INTERNALS__ || window.__TAURI__) {
          window.location.assign(target.href);
        } else {
          window.open(target.href, '_blank', 'noopener,noreferrer');
        }
      }
    }, true);
    doc.addEventListener('submit', event => {
      const form = event.target;
      const target = new URL(form.action);
      if (target.origin !== location.origin || target.pathname !== '/history/compare') return;
      event.preventDefault();
      openTab(`${target.pathname}?${new URLSearchParams(new FormData(form))}`);
    }, true);
  }

  function showReport(id) {
    if (announced.has(id)) return;
    announced.add(id);
    openTab(`/history/${id}/report`);
  }

  function updateReport(task) {
    if (!task?.report_ready) return;
    showReport(task.id);
    if (task.status === 'running') {
      unfinished.add(task.id);
    } else if (unfinished.delete(task.id)) {
      tabs.filter(tab => tab.path === `/history/${task.id}/report`).forEach(refresh);
    }
  }

  async function checkTasks() {
    if (busy) return;
    busy = true;
    try {
      const response = await fetch(`/api/ui/reports?after=${scanAfter}`, {cache: 'no-store'});
      if (response.ok) {
        for (const task of (await response.json()).reports) {
          updateReport(task);
          scanAfter = task.id;
        }
      }
      for (const id of unfinished) {
        const state = await fetch(`/api/history/${id}`, {cache: 'no-store'});
        if (state.ok) updateReport((await state.json()).task);
        else if (state.status === 404) unfinished.delete(id);
      }
    } catch (_) { /* Keep the current tabs through a temporary sidecar error. */ }
    finally { busy = false; }
  }

  toolbar.addEventListener('click', event => {
    const path = event.target.dataset.open;
    if (path) openTab(path);
  });
  tablist.addEventListener('keydown', event => {
    const direction = {ArrowLeft: -1, ArrowRight: 1}[event.key];
    if (!direction) return;
    const index = (tabs.indexOf(selected) + direction + tabs.length) % tabs.length;
    event.preventDefault();
    activate(tabs[index]);
    tabs[index].button.focus();
  });
  window.addEventListener('message', event => {
    if (event.origin !== location.origin || !tabs.some(tab => tab.iframe.contentWindow === event.source)) return;
    const data = event.data;
    if (data?.type === 'nd-language' && Object.hasOwn(translations, data.language)) {
      language = data.language;
      document.documentElement.lang = language;
      labels();
      tabs.forEach(refresh);
    }
    if (data?.type === 'nd-report' && Number.isSafeInteger(data.taskId) && data.taskId > 0) {
      showReport(data.taskId);
      unfinished.add(data.taskId);
    }
    if (data?.type === 'nd-navigate' && data.path === '/run') openTab('/run');
  });
  openTab('/settings');
  checkTasks();
  setInterval(checkTasks, 2000);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) checkTasks(); });
})();
</script></body></html>"""
