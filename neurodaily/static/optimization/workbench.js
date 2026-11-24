import {t} from './workbench-copy.js';
import {categories, element, renderEvidence, renderReview} from './workbench-render.js';

const api = '/api/optimization';
const workbench = document.getElementById('optimization-workbench');

if (workbench) setupWorkbench(workbench);

function labelsByIdentifier(groups = []) {
  return Object.fromEntries(groups.flatMap(({ids, relevant}) => ids.map(id => [id, relevant])));
}

function setupWorkbench(root) {
  const get = (id) => root.querySelector('#optimization-' + id);
  const historyRuns = get('history-runs');
  const [enabled, conversation, messages, text, send, status, error, retry, cancel, resume,
    rollback, review, findings, profile, newChat] =
    ['enabled', 'conversations', 'chat', 'text', 'send', 'status', 'error', 'retry', 'cancel', 'resume',
      'rollback', 'review', 'findings', 'profile', 'new'].map(get);
  let state = null;
  let selected = '';
  let selectedHistory = '';
  let category = 'all';
  let timer;
  let loading = false;
  let action = false;
  let snapshotSequence = 0;
  let pendingPreference;
  let pendingConfigSync = '';
  let componentReady = false;
  let lastTranscript = '';
  let lastEvidence = '';
  let lastReview = '';
  let lastConversations = '';
  let lastHistory = '';

  for (const node of root.querySelectorAll('[data-opt-text]')) node.textContent = t(node.dataset.optText);
  text.placeholder = t('prompt');
  conversation.setAttribute('aria-label', t('conversation'));
  historyRuns.setAttribute('aria-label', t('evidenceSelection'));
  get('categories').setAttribute('aria-label', t('categories'));

  for (const name of categories) {
    const button = element('button', t(name));
    button.type = 'button';
    button.setAttribute('aria-pressed', String(name === category));
    button.addEventListener('click', () => {
      category = name;
      for (const other of get('categories').children) other.setAttribute('aria-pressed', String(other === button));
      paintEvidence();
    });
    get('categories').append(button);
  }

  import('./deep-chat.js').then(() => {
    componentReady = true;
    paintTranscript();
  }).catch(() => {
    // Preserve the transcript with native elements if the optional renderer cannot load.
  });
  paintTranscript();

  function paintTranscript() {
    const rows = (state?.messages || []).map(row => ({
      role: row.role === 'user' ? 'user' : 'ai', text: String(row.text ?? row.content ?? ''),
    }));
    if (!rows.length) rows.push({role: 'ai', text: t('noConversation')});
    const key = JSON.stringify([componentReady, selected, rows]);
    if (key === lastTranscript) return;
    lastTranscript = key;
    if (componentReady) {
      const chat = element('deep-chat');
      // An explicit font stack prevents the component's default font download.
      chat.chatStyle = {backgroundColor: 'var(--panel)', color: 'var(--text)', border: 'none', fontFamily: 'inherit'};
      chat.textInput = {disabled: true};
      chat.inputAreaStyle = {display: 'none'};
      chat.auxiliaryStyle = '.nd-chat-text{white-space:pre-wrap;overflow-wrap:anywhere}';
      chat.messageStyles = {default: {
        shared: {bubble: {fontSize: '.85rem', color: 'var(--text)'}},
        user: {bubble: {backgroundColor: '#173145'}},
        ai: {bubble: {backgroundColor: 'var(--panel2)'}},
      }};
      chat.history = rows.map(row => ({
        role: row.role,
        // Using a text node keeps the model response and user input in plain text.
        html: element('span', row.text, 'nd-chat-text').outerHTML,
      }));
      messages.replaceChildren(chat);
    } else {
      const list = element('ol', null, 'optimization-transcript');
      for (const row of rows) {
        const item = element('li');
        item.append(element('strong', t(row.role === 'user' ? 'user' : 'assistant')), element('div', row.text));
        list.append(item);
      }
      messages.replaceChildren(list);
      list.scrollTop = list.scrollHeight;
    }
  }

  function paintEvidence() {
    const evidence = state?.evidence ?? state?.run?.evidence ?? [];
    const attributions = state?.attributions ?? state?.run?.attributions ?? [];
    const sources = Array.isArray(evidence) ? evidence : (evidence.sources || []);
    const labels = labelsByIdentifier(state?.labels);
    const checks = selectedHistory ? [] : state?.run?.checks || [];
    const key = JSON.stringify([category, sources, attributions, checks, labels]);
    if (key === lastEvidence) return;
    lastEvidence = key;
    const fromTrial = sources.some(source => source.publication);
    get('evidence-window').textContent = fromTrial ? t('evidenceWindow', {days: evidence.days || 30})
      : sources.length ? t('historicalEvidence') : '';
    const open = new Set(Array.from(findings.querySelectorAll('details[open] > summary'), summary => summary.textContent));
    findings.replaceChildren(renderEvidence(sources, attributions, checks, category, mark, labels));
    for (const disclosure of findings.querySelectorAll('details')) {
      if (open.has(disclosure.firstElementChild.textContent)) disclosure.open = true;
    }
  }

  function paintConversations() {
    const entries = state?.conversations || [];
    const key = JSON.stringify(entries);
    if (key !== lastConversations) {
      lastConversations = key;
      conversation.replaceChildren(...entries.map(row => {
        const option = element('option', row.title || row.created_at || t('conversation'));
        option.value = row.id;
        return option;
      }));
    }
    conversation.hidden = entries.length < 2;
    conversation.value = selected;
  }

  function paint() {
    const run = state?.run;
    const busy = ['queued', 'running', 'cancelling', 'applying', 'rolling_back'].includes(run?.status);
    enabled.checked = pendingPreference ?? (state?.enabled !== false);
    enabled.disabled = !state || action;
    get('disabled').hidden = enabled.checked;
    newChat.disabled = !state || action || Boolean(pendingConfigSync);
    conversation.disabled = !state || action || Boolean(pendingConfigSync);
    const cannotSend = !state || !enabled.checked || action || busy;
    text.disabled = cannotSend;
    send.disabled = cannotSend;
    cancel.hidden = !['queued', 'running'].includes(run?.status);
    resume.hidden = !['interrupted', 'cancelled'].includes(run?.status);
    get('reject').hidden = run?.status !== 'review';
    get('reject').disabled = action;
    rollback.hidden = run?.status !== 'applied';
    const nextStatus = run ? [t(run.status, {round: run.round || 1}), run.stage && run.stage !== run.status ? t(run.stage) : '']
      .filter(Boolean).join(' · ') : t(state ? 'noRuns' : 'loading');
    if (status.textContent !== nextStatus) status.textContent = nextStatus;
    const conclusion = get('conclusion');
    conclusion.textContent = run?.error || [run?.conclusion, ...(run?.blockers || []).map(reason => t(reason))]
      .filter(Boolean).join(' ');
    conclusion.hidden = !conclusion.textContent;
    profile.textContent = state?.profile ? t('profile', {profile: state.profile}) : '';
    paintConversations();
    const batches = state?.history_runs || [];
    const historyKey = JSON.stringify(batches);
    if (historyKey !== lastHistory) {
      lastHistory = historyKey;
      const latest = element('option', t('latestEvidence'));
      latest.value = '';
      historyRuns.replaceChildren(latest, ...batches.map(batch => {
        const option = element('option', String(batch.date).slice(0, 16).replace('T', ' ') + ' · ' + batch.item_count);
        option.value = batch.id;
        return option;
      }));
    }
    historyRuns.hidden = !batches.length;
    historyRuns.value = selectedHistory;
    paintTranscript();
    paintEvidence();
    const reviewKey = JSON.stringify([run?.id, run?.status, run?.candidates, run?.baseline_metrics, state?.labels]);
    if (lastReview !== reviewKey) {
      lastReview = reviewKey;
      review.replaceChildren(renderReview(run, accept, mark, labelsByIdentifier(state?.labels)));
    }
    for (const button of [cancel, resume, rollback, ...review.querySelectorAll('button')]) {
      button.disabled = action || (!enabled.checked && (button === resume || button.dataset.action === 'accept'));
    }
  }

  async function request(path, payload) {
    const options = payload === undefined ? {cache: 'no-store'} : {
      method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload),
    };
    const response = await fetch(api + path, options);
    let result;
    try { result = await response.json(); } catch { throw new Error(t('requestError')); }
    if (!response.ok) {
      const detail = result?.error || result?.detail;
      throw Object.assign(new Error(typeof detail === 'string' ? detail : t('requestError')), {status: response.status});
    }
    return result;
  }

  function showError(message = '') {
    error.textContent = message;
    error.hidden = !message;
  }

  async function refresh() {
    const sequence = ++snapshotSequence;
    const parameters = new URLSearchParams();
    if (selected) parameters.set('conversation_id', selected);
    if (selectedHistory) parameters.set('history_run_id', selectedHistory);
    const query = parameters.size ? '?' + parameters.toString() : '';
    let snapshot;
    try {
      snapshot = await request(query);
    } catch (err) {
      if (snapshotSequence !== sequence) return;
      if (!query || err.status !== 404) throw err;
      selectedHistory = '';
      snapshot = await request('');
    }
    if (snapshotSequence !== sequence) return;
    state = snapshot;
    selected = state.conversation_id || selected;
    retry.hidden = true;
    if (pendingConfigSync === state.run?.id && !['applying', 'rolling_back'].includes(state.run.status)) {
      pendingConfigSync = '';
      if (['applied', 'rolled_back'].includes(state.run.status)) await syncSettings();
    }
    paint();
  }

  function schedule() {
    clearTimeout(timer);
    const active = ['queued', 'running', 'cancelling', 'applying', 'rolling_back'].includes(state?.run?.status);
    timer = setTimeout(poll, active ? 1500 : 10000);
  }

  async function poll(force = false) {
    if (action || (loading && force !== true) || (document.hidden && state)) {
      schedule();
      return;
    }
    loading = true;
    try {
      await refresh();
    } catch (err) {
      showError(err.message);
      retry.hidden = false;
    } finally {
      loading = false;
      schedule();
    }
  }

  async function mutate(path, payload, onSuccess) {
    if (action) return false;
    action = true;
    clearTimeout(timer);
    ++snapshotSequence;
    showError();
    paint();
    try {
      const result = await request(path, payload);
      if (result.conversation_id) selected = result.conversation_id;
      if (onSuccess) await onSuccess(result);
      await refresh();
      return true;
    } catch (err) {
      showError(err.message);
      return false;
    } finally {
      action = false;
      paint();
      schedule();
    }
  }

  const runPath = (name) => '/runs/' + encodeURIComponent(state.run.id) + '/' + name;
  const mayApply = () => {
    if (!window.ndCanUpdateSearch || window.ndCanUpdateSearch()) return true;
    showError(t('needSave'));
    return false;
  };
  const syncSettings = async () => {
    if (window.ndRefreshSearchSettings && !await window.ndRefreshSearchSettings()) {
      showError(t('refreshNeeded'));
    }
  };
  const accept = (candidate_id) => {
    if (mayApply()) mutate(runPath('accept'), {candidate_id}, () => { pendingConfigSync = state.run.id; });
  };
  const mark = (ids, relevant, date) => mutate('/labels', {ids, relevant, date});
  enabled.addEventListener('change', async () => {
    pendingPreference = enabled.checked;
    try {
      await mutate('/preferences', {enabled: pendingPreference});
    } finally {
      pendingPreference = undefined;
      paint();
    }
  });
  newChat.addEventListener('click', () => mutate('/conversations', {}));
  conversation.addEventListener('change', () => {
    selected = conversation.value;
    poll(true);
  });
  historyRuns.addEventListener('change', () => {
    selectedHistory = historyRuns.value;
    poll(true);
  });
  retry.addEventListener('click', poll);
  cancel.addEventListener('click', () => mutate(runPath('cancel'), {}));
  resume.addEventListener('click', () => mutate(runPath('resume'), {}));
  get('reject').addEventListener('click', () => mutate(runPath('reject'), {}));
  rollback.addEventListener('click', () => {
    if (mayApply() && confirm(t('rollbackConfirm'))) {
      mutate(runPath('rollback'), {}, () => { pendingConfigSync = state.run.id; });
    }
  });
  get('form').addEventListener('submit', event => {
    event.preventDefault();
    const message = text.value.trim();
    if (!message || !mayApply()) return;
    mutate('/messages', {
      text: message, conversation_id: selected || undefined, rounds: get('rounds').valueAsNumber,
      max_sources: get('max-sources').valueAsNumber, allow_tradeoffs: get('tradeoffs').checked,
    }, () => { text.value = ''; });
  });
  document.addEventListener('visibilitychange', () => { if (!document.hidden) poll(); });
  document.addEventListener('nd:search-profile-changed', () => {
    selected = '';
    selectedHistory = '';
    poll(true);
  });
  paint();
  poll();
}
