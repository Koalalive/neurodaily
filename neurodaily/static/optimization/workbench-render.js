import {t} from './workbench-copy.js';

export const categories = ['all', 'paper', 'trial', 'news', 'industry', 'conference'];
const categoryMap = {
  paper: 'paper', literature: 'paper', trial: 'trial', clinical_trial: 'trial',
  news: 'news', policy: 'news', news_policy: 'news', funding: 'industry', industry: 'industry',
  drug: 'industry', device: 'industry', conference: 'conference',
};
const metrics = [
  ['recall', 'recall'], ['information_gain', 'novel'], ['false_positives', 'falsePositives'],
  ['cost', 'cost'], ['request_count', 'requests'], ['tokens', 'tokens'], ['elapsed_seconds', 'elapsed'],
];

export function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text != null) node.textContent = String(text);
  if (className) node.className = className;
  return node;
}

function textLink(text, href) {
  try {
    if (typeof href !== 'string' || !/^https?:\/\//i.test(href)) return element('span', text);
    const url = new URL(href);
    if (url.username || url.password) return element('span', text);
    const anchor = element('a', text);
    anchor.href = url.href;
    anchor.target = '_blank';
    anchor.rel = 'noopener noreferrer';
    return anchor;
  } catch {
    return element('span', text);
  }
}

function detail(label, open = false) {
  const node = element('details');
  node.open = open;
  node.append(element('summary', label));
  return node;
}

function recordList(rows, mark, labels) {
  const list = element('ul', null, 'optimization-records');
  for (const row of rows) {
    const item = element('li');
    item.append(textLink(row.title || row.ids?.[0] || t('record'), row.url));
    const status = [row.date, row.status ? t(row.status) : '', ...(row.missing_fields || [])].filter(Boolean);
    if (status.length) item.append(element('div', status.join(' · '), 'optimization-muted'));
    if (mark && Array.isArray(row.ids) && row.ids.length) {
      const controls = element('div', null, 'optimization-actions');
      for (const relevant of [true, false]) {
        const button = element('button', t(relevant ? 'relevant' : 'irrelevant'));
        button.type = 'button';
        const label = row.ids.map(id => labels?.[id]).find(value => typeof value === 'boolean');
        button.setAttribute('aria-pressed', String(label === relevant));
        button.addEventListener('click', async () => {
          for (const control of controls.children) control.disabled = true;
          try {
            const date = (row.available_on || row.date || '').slice(0, 10);
            const saved = await mark(row.ids, relevant, /^\d{4}-\d{2}-\d{2}$/.test(date) ? date : undefined);
            if (saved) {
              controls.children[0].setAttribute('aria-pressed', String(relevant));
              controls.children[1].setAttribute('aria-pressed', String(!relevant));
            }
          } finally {
            for (const control of controls.children) control.disabled = false;
          }
        });
        controls.append(button);
      }
      item.append(controls);
    }
    list.append(item);
  }
  return list;
}

function sourceCategories(source) {
  if (categoryMap[source.category || source.kind]) return [categoryMap[source.category || source.kind]];
  const byExample = (source.examples || []).map(row => categoryMap[row.kind]).filter(Boolean);
  if (byExample.length) return byExample;
  const name = source.source || '';
  if (/trial/i.test(name)) return ['trial'];
  if (/conference|meeting/i.test(name)) return ['conference'];
  if (/fda|device|fund|fierce|industry/i.test(name)) return ['industry'];
  if (/rss|news|policy|gdelt|nih_brain/i.test(name)) return ['news'];
  if (/med|rxiv|journal|crossref|openalex|arxiv/i.test(name)) return ['paper'];
  return [];
}

function matchesCategory(category, values) {
  return category === 'all' || values.includes(category);
}

function pluralCount(count, key) {
  return count == null ? '' : t(key, {count});
}

export function renderEvidence(evidence, attributions, checks, category, mark, labels) {
  const fragment = document.createDocumentFragment();
  for (const source of evidence) {
    if (!matchesCategory(category, sourceCategories(source))) continue;
    const name = source.source || source.title || t('source');
    const node = detail([name, t(source.status || 'unknown')].join(' · '));
    const citation = source.citation;
    const link = citation?.url || (typeof citation === 'string' ? citation : source.url);
    if (link) {
      const reference = element('p');
      reference.append(textLink(citation?.title || name, link));
      node.append(reference);
    }
    for (const [label, probe] of [[t('publicationProbe'), source.publication], [t('configuredProbe'), source.configured]]) {
      if (!probe) continue;
      const counts = [probe.status ? t(probe.status) : '', pluralCount(probe.captured, 'recordsCount'),
        pluralCount(probe.fetched, 'recordsFetched'), pluralCount(probe.matches ?? probe.count, 'matches'),
        pluralCount(probe.excluded, 'recordsExcluded'), pluralCount(probe.unknown, 'recordsUncertain'),
        probe.coverage ? t(probe.coverage) : ''].filter(Boolean);
      node.append(element('p', [label, ...counts].join(' · '), 'optimization-health'));
      if (probe.reason) node.append(element('p', probe.reason, 'optimization-muted'));
      if (probe.dated_records) {
        const dated = Object.entries(probe.dated_records).filter(([, dates]) => Array.isArray(dates) && dates.length);
        if (dated.length) {
          const days = detail(dated.map(([key, dates]) => t(key + 'Count', {count: dates.length})).join(' · '));
          for (const [key, dates] of dated) {
            days.append(element('p', `${t(key + 'Count', {count: dates.length})} · ${dates.join(', ')}`, 'optimization-muted'));
          }
          node.append(days);
        }
      }
    }
    for (const [phase, probes] of Object.entries(source.windows || {})) {
      const counts = [probes.configured?.status && t(probes.configured.status),
        pluralCount(probes.publication?.captured, 'recordsCount'), pluralCount(probes.configured?.matches, 'matches')];
      node.append(element('p', [t(phase), ...counts].filter(Boolean).join(' · '), 'optimization-muted'));
    }
    const examples = (source.examples || []).filter(row => matchesCategory(category, [categoryMap[row.kind]]));
    if (examples.length) node.append(recordList(examples, mark, labels));
    fragment.append(node);
  }

  const records = checks.filter(row =>
    matchesCategory(category, [/(^|:)nct/i.test(row.id) ? 'trial' : 'paper'])
  ).map(row => ({title: row.id, url: row.citation, status: row.status}));
  if (records.length) {
    const node = detail(t('knownIdentifiers'));
    node.append(recordList(records));
    fragment.append(node);
  }

  for (const attribution of attributions) {
    const rows = attribution.items || attribution.examples || [];
    const tagged = categoryMap[attribution.category || attribution.kind];
    if (!matchesCategory(category, [tagged, ...rows.map(row => categoryMap[row.kind])])) continue;
    const node = detail([attribution.rule || attribution.source || t('query'),
      pluralCount(attribution.count, 'matches')].filter(Boolean).join(' · '));
    if (attribution.status) node.append(element('p', t(attribution.status), 'optimization-muted'));
    const examples = rows.filter(row => matchesCategory(category, [categoryMap[row.kind] || tagged]));
    if (examples.length) node.append(recordList(examples, mark, labels));
    fragment.append(node);
  }
  if (!fragment.childNodes.length) fragment.append(element('p', t('noEvidence'), 'optimization-muted'));
  return fragment;
}

export function renderTrialDiagnostics(trials, category, mark, labels, readPage, pages) {
  const fragment = document.createDocumentFragment();
  for (const trial of trials) {
    const node = detail([t(trial.phase), trial.title].filter(Boolean).join(' · '));
    if (trial.reasons?.length) node.append(element('p', trial.reasons.map(reason => t(reason)).join(' '), 'optimization-muted'));
    for (const [direction, label] of [['added', 'added'], ['lost', 'removed']]) {
      const total = trial[direction + '_count'];
      if (!total) continue;
      const key = [trial.phase, trial.id, direction].join(':');
      const rows = pages.get(key) || [];
      const records = element('div');
      const button = element('button');
      button.type = 'button';
      function renderRows() {
        records.replaceChildren(recordList(rows.filter(row => matchesCategory(category, [categoryMap[row.kind]])), mark, labels));
        button.textContent = t(rows.length ? 'moreRecords' : 'showRecords');
        button.hidden = rows.length >= total;
      }
      button.addEventListener('click', async () => {
        button.disabled = true;
        try {
          const result = await readPage(trial, direction, rows.length);
          if (result) {
            rows.push(...result.records);
            pages.set(key, rows);
            renderRows();
          }
        } finally {
          button.disabled = false;
        }
      });
      renderRows();
      node.append(element('p', `${t(label)} · ${total}`), records, button);
    }
    fragment.append(node);
  }
  return fragment;
}

function formatMetric(value, key, delta = false) {
  if (value == null || value === '') return '—';
  if (typeof value !== 'number' || !Number.isFinite(value)) return String(value);
  const formatter = new Intl.NumberFormat(document.documentElement.lang, {
    style: key === 'recall' && !delta ? 'percent' : 'decimal',
    maximumFractionDigits: 2,
    signDisplay: delta ? 'exceptZero' : 'auto',
  });
  if (key === 'recall' && delta) return formatter.format(value * 100) + ' pp';
  return formatter.format(value);
}

function candidateSources(rows) {
  const group = detail(t('sourceBreakdown'));
  for (const row of rows) {
    const block = detail(row.source || t('source'));
    const reference = row.citation?.url || row.citation;
    if (reference) block.append(textLink(row.citation?.title || row.source || t('source'), reference));
    for (const side of ['baseline', 'candidate']) {
      const report = row[side];
      if (!report) continue;
      const counts = [pluralCount(report.matched, 'matches'), pluralCount(report.filtered, 'recordsExcluded'),
        pluralCount(report.unknown, 'recordsUncertain'), pluralCount(report.undated, 'recordsUndated'),
        pluralCount(report.request_count, 'actualRequests')].filter(Boolean);
      block.append(element('p', [t(side), report.status && t(report.status), report.coverage && t(report.coverage),
        ...counts].filter(Boolean).join(' · '), 'optimization-muted'));
    }
    group.append(block);
  }
  return group;
}

export function renderReview(run, onAccept, mark, labels) {
  const fragment = document.createDocumentFragment();
  if (run?.id && /^[0-9a-f]{32}$/.test(run.id)) {
    const billing = element('a', t('runBilling'));
    billing.href = '/billing?optimization_run_id=' + encodeURIComponent(run.id);
    billing.target = '_blank';
    billing.rel = 'noopener noreferrer';
    fragment.append(billing);
  }
  const candidates = (run?.candidates || []).filter(candidate => candidate.eligible !== false);
  if (run?.status === 'completed' && !candidates.length && !run.conclusion) {
    fragment.append(element('p', t('noQualified'), 'optimization-muted'));
    return fragment;
  }
  if (!candidates.length || !['review', 'applying', 'applied', 'rolling_back', 'rolled_back'].includes(run?.status)) {
    return fragment;
  }
  fragment.append(element('h4', t('reviewTitle')));
  if (run.status === 'review' && (run.labels_changed || run.evidence_outdated)) {
    fragment.append(element('p', t(run.evidence_outdated ? 'evidenceOutdated' : 'labelsChanged'), 'optimization-muted'));
  }
  for (const candidate of candidates) {
    const card = element('article', null, 'optimization-card');
    card.append(element('h5', candidate.title || t('candidate')));
    if (candidate.description) card.append(element('p', candidate.description));
    const baseline = candidate.baseline_metrics || candidate.comparison?.baseline_metrics || run.baseline_metrics || {};
    const data = candidate.metrics || {};
    const delta = candidate.delta || {};
    const available = metrics.filter(([key]) => key in data);
    if (available.length) {
      const totals = element('dl', null, 'optimization-metrics');
      totals.append(element('dt', t('metric')), element('dd', t('candidate')), element('dd', t('delta')));
      for (const [key, label] of available) {
        const original = baseline[key];
        const difference = delta[key] ?? (Number.isFinite(original) && Number.isFinite(data[key]) ? data[key] - original : null);
        const name = element('dt', t(label));
        name.title = t('baseline') + ' ' + formatMetric(original, key);
        totals.append(name, element('dd', formatMetric(data[key], key)), element('dd', formatMetric(difference, key, true)));
      }
      card.append(totals);
      if (candidate.details?.cost_basis) card.append(element('p', t('estimatedCost'), 'optimization-muted'));
    }
    if (candidate.diff) {
      const changes = detail(t('diff'), true);
      const text = typeof candidate.diff === 'string' ? candidate.diff : JSON.stringify(candidate.diff, null, 2);
      changes.append(element('pre', text));
      card.append(changes);
    }
    if (candidate.details?.sources?.length) card.append(candidateSources(candidate.details.sources));
    for (const [key, rows] of [['added', candidate.comparison?.added || candidate.added],
      ['removed', candidate.comparison?.lost || candidate.comparison?.removed || candidate.lost]]) {
      if (!rows?.length) continue;
      const total = candidate.details?.[key === 'added' ? 'added_count' : 'lost_count'] ?? rows.length;
      const changes = detail(t(key) + ' · ' + (total > rows.length ? `${rows.length}/${total}` : total));
      changes.append(recordList(rows, mark, labels));
      card.append(changes);
    }
    if (run.status === 'review' && candidate.id && !run.labels_changed && !run.evidence_outdated) {
      const accept = element('button', t('accept'));
      accept.type = 'button';
      accept.dataset.action = 'accept';
      accept.addEventListener('click', () => onAccept(candidate.id));
      card.append(accept);
    }
    fragment.append(card);
  }
  return fragment;
}
