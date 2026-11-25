(() => {
  const host = document.getElementById('nd-report-feedback');
  if (!host || !/^[1-9][0-9]{0,17}$/.test(host.dataset.runId) || location.protocol === 'file:') return;
  const label = {
    zh: ['相关', '不相关', '保存反馈失败，请重试。'],
    en: ['Relevant', 'Not relevant', 'Could not save feedback. Try again.'],
    ru: ['Релевантно', 'Не релевантно', 'Не удалось сохранить отзыв. Повторите попытку.']
  }[document.documentElement.lang] || ['Relevant', 'Not relevant', 'Could not save feedback. Try again.'];
  const route = '/api/history/' + host.dataset.runId + '/feedback';
  const cards = Array.from(document.querySelectorAll('[data-report-record]'))
    .filter(card => /^[0-9a-f]{64}$/.test(card.dataset.reportRecord));

  fetch(route, {credentials: 'same-origin', cache: 'no-store'})
    .then(response => response.ok ? response.json() : Promise.reject())
    .then(data => {
      for (const card of cards) {
        const key = card.dataset.reportRecord;
        const state = document.createElement('span');
        const buttons = label.slice(0, 2).map((text, index) => {
          const button = document.createElement('button');
          button.type = 'button';
          button.className = 'minibtn';
          button.textContent = text;
          button.addEventListener('click', async () => {
            buttons.forEach(item => {item.disabled = true;});
            state.textContent = '';
            try {
              const relevant = index === 0;
              const response = await fetch(route, {
                method: 'POST', credentials: 'same-origin',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({record_key: key, relevant})
              });
              if (!response.ok) throw new Error('Feedback rejected');
              select(relevant);
            } catch {
              state.textContent = label[2];
            } finally {
              buttons.forEach(item => {item.disabled = false;});
            }
          });
          return button;
        });
        function select(choice) {
          buttons.forEach((button, index) => button.setAttribute('aria-pressed', String(choice === (index === 0))));
        }
        state.setAttribute('role', 'status');
        state.className = 'byline';
        select(data.feedback?.[key]);
        card.replaceChildren(...buttons, state);
        card.hidden = false;
      }
    })
    .catch(() => {});
})();
