"""Markup for the profile-scoped workbench embedded in Advanced Search."""

OPTIMIZATION_HEAD = """<link rel="stylesheet" href="/static/optimization/workbench.css">
<script type="module" src="/static/optimization/workbench.js"></script>"""

OPTIMIZATION_WORKBENCH = """
<div id="optimization-workbench" data-no-i18n aria-labelledby="optimization-title">
  <div class="optimization-heading">
    <div>
      <h3 id="optimization-title" data-opt-text="title"></h3>
      <p class="optimization-muted" id="optimization-profile"></p>
    </div>
    <label class="optimization-switch">
      <input id="optimization-enabled" type="checkbox" role="switch" checked disabled>
      <span data-opt-text="enabled"></span>
    </label>
  </div>
  <p class="optimization-muted" id="optimization-disabled" data-opt-text="disabledHelp" hidden></p>
  <div class="optimization-columns">
    <div class="optimization-chat-column">
      <div class="optimization-actions">
        <select id="optimization-conversations" hidden></select>
        <button id="optimization-new" type="button" data-opt-text="newChat" disabled></button>
      </div>
      <div id="optimization-chat" aria-labelledby="optimization-title"></div>
      <form id="optimization-form">
        <label for="optimization-text" data-opt-text="message"></label>
        <textarea id="optimization-text" rows="3" maxlength="4000" required disabled></textarea>
        <div class="optimization-actions">
          <button type="submit" id="optimization-send" data-opt-text="send" disabled></button>
          <details id="optimization-budget">
            <summary data-opt-text="trialOptions"></summary>
            <label><span data-opt-text="rounds"></span>
              <input id="optimization-rounds" type="number" min="1" max="6" value="4" required>
            </label>
            <label><span data-opt-text="maxSources"></span>
              <input id="optimization-max-sources" type="number" min="1" max="14" value="10" required>
            </label>
            <label><span data-opt-text="onlineRequestLimit"></span>
              <input id="optimization-online-requests" type="number" min="1" max="600" value="120" required>
            </label>
            <label><span data-opt-text="onlineTimeLimit"></span>
              <input id="optimization-online-seconds" type="number" min="1" max="900" value="120" required>
            </label>
            <label><input id="optimization-tradeoffs" type="checkbox">
              <span data-opt-text="tradeoffs"></span>
            </label>
          </details>
        </div>
      </form>
    </div>
    <div class="optimization-evidence-column" aria-labelledby="optimization-evidence-title">
      <h4 id="optimization-evidence-title" data-opt-text="evidence"></h4>
      <select id="optimization-history-runs" hidden></select>
      <p id="optimization-evidence-window" class="optimization-muted"></p>
      <div class="optimization-actions" id="optimization-categories" role="group"></div>
      <div id="optimization-findings"></div>
    </div>
  </div>
  <div class="optimization-progress">
    <p id="optimization-status" role="status" aria-live="polite" data-opt-text="loading"></p>
    <p id="optimization-budget-usage" class="optimization-muted" hidden></p>
    <p id="optimization-conclusion" class="optimization-muted" hidden></p>
    <p id="optimization-error" role="alert" hidden></p>
    <div id="optimization-controls" class="optimization-actions">
      <button id="optimization-retry" type="button" data-opt-text="retry" hidden></button>
      <button id="optimization-cancel" type="button" data-opt-text="cancel" hidden></button>
      <button id="optimization-resume" type="button" data-opt-text="resume" hidden></button>
      <button id="optimization-reject" type="button" data-opt-text="reject" hidden></button>
      <button id="optimization-rollback" type="button" data-opt-text="rollback" hidden></button>
    </div>
  </div>
  <div id="optimization-review"></div>
</div>
"""
