# NeuroDaily Handoff

Updated: 2026-11-23 (Asia/Shanghai)

This document is for the next supervising agent. It describes the live system, release state, daily automation, and the checks that must be run before changing anything.

## Live surfaces

- Public repository: https://github.com/Koalalive/neurodaily
- Public website: https://koalalive.github.io/neurodaily/
- Chinese demo: https://koalalive.github.io/neurodaily/demo/latest-report.zh.html
- English demo: https://koalalive.github.io/neurodaily/demo/latest-report.en.html
- Russian demo: https://koalalive.github.io/neurodaily/demo/latest-report.ru.html
- CLI/Homebrew release: https://github.com/Koalalive/neurodaily/releases/tag/cli-v1.0.8

The website is served from `docs/` through GitHub Pages. Recent website copy changes: `AI Agent Skills助力检索配置构建`, Chinese `检索配置`, macOS inline command styling, and an Agent installation guide link. A push to `main` triggers `pages-build-deployment`; the daily demo workflow pushes generated snapshots to `main`, which triggers Pages separately.

## Daily homepage update

Workflow: `.github/workflows/daily-demo.yml`

- Cron: `0 0 * * *` UTC = **08:00 Asia/Shanghai**.
- Manual fallback: GitHub Actions -> `daily-demo` -> `Run workflow`.
- It builds a **168-hour** public demo from `config/demo.json`, then commits:
  - `docs/demo/latest-report.zh.html`
  - `docs/demo/latest-report.en.html`
  - `docs/demo/latest-report.ru.html`
- It verifies the demo config before building:
  - `windows.trials_hours >= 168`
  - `sources.trials.lookback_days >= 7`
- It verifies generated pages contain `trials`, `conferences`, and translatable navigation before committing.
- `concurrency: daily-demo` prevents overlapping runs.

Supervisor checks after 08:00 Asia/Shanghai:

```bash
gh run list --workflow daily-demo.yml --limit 3
curl -fsSL https://koalalive.github.io/neurodaily/demo/latest-report.zh.html | \
  sed -n '/<section id="trials"/,/<\/h2>/p' | head -5
```

Expected: a successful `daily-demo` run and a non-zero trial count when ClinicalTrials.gov has fresh registry updates. A genuinely empty result is allowed, but verify the source health and the 168h config first.

The `daily-demo` workflow receives `NEURODAILY_LLM_API_KEY`; AI summaries and
the research-activity map run on the GitHub runner, and the workflow fails loudly
if either section disappears from the generated public demo. The public snapshot
removes the private focus-prompt section.

Important: GitHub disables scheduled workflows after 60 days without repository activity. If the 08:00 run stops, trigger `daily-demo` manually and make a normal commit; then verify the schedule is re-enabled in Actions.

## Release state

Current versions in source:

- `pyproject.toml`: `1.0.8`
- `desktop/tauri/src-tauri/tauri.conf.json`: `1.0.8`
- `neurodaily/__init__.py`: `1.0.8`

Baseline for upgrade verification: **v1.0.7**. Do not delete `v1.0.7` until the release workflow baseline is changed and verified.

Historical releases older than `v1.0.7` were intentionally removed. `cli-v1.0.8` remains published.

**v1.0.8 is published** from run **45067766511** (commit `c24a47c`), tag `v1.0.8`.
The release is non-draft and contains the Windows NSIS/MSI, Linux DEB/AppImage,
their signatures, and the Python wheel.

Release history:
- Upgrade smoke now reads `/history/{id}/report` instead of the `/history/{id}` summary page.
- Linux native-UI smoke now sets `NEURODAILY_ALLOW_PRIVATE_SOURCES=1` for its loopback fixture feed.
- Baseline is `v1.0.7`; do not delete it.
- Main is ahead of the release tag after the latest report/demo changes. If a new
  desktop build is required, bump to the next patch version and run
  `release-tauri.yml` again; do not overwrite a published release.

Release workflow: `.github/workflows/release-tauri.yml`

- Triggered by `v*` tags and `workflow_dispatch`.
- Builds Windows NSIS/MSI, Linux AppImage/DEB, macOS Homebrew CLI, and the Python wheel.
- Upgrade smoke tests use `BASELINE_TAG=v1.0.7`.
- The publish job creates a draft release, verifies assets/signatures, publishes the Docker image, then undrafts the GitHub release.

To publish after the fixes are committed and tested:

```bash
git tag -f -a v1.0.8 -m "NeuroDaily v1.0.8" HEAD
git push origin v1.0.8 --force
gh run list --workflow release-tauri.yml --limit 2
```

Do not force-republish once a release exists unless the owner explicitly asks. Check `gh release view v1.0.8` first.

Known fixed release-test issue: Linux and Windows upgrade checks were requesting `/history/{id}` (history summary) instead of `/history/{id}/report` (saved report). Both smoke scripts now use the report route. Baseline v1.0.7 uses the same report route.

## Verification commands

Local tests:

```bash
.venv/bin/python -m unittest discover -s tests
```

Expected: 241 tests pass.

Demo build:

```bash
.venv/bin/python scripts/build_demo_snapshot.py
```

Then check:

```bash
sed -n '/<section id="trials"/,/<\/h2>/p' docs/demo/latest-report.zh.html | head -5
sed -n '/<section id="conferences"/,/<\/h2>/p' docs/demo/latest-report.zh.html | head -5
```

Live browser checks should use a real DOM, not only `curl`, because report navigation is localized by `nd-localizer` JavaScript:

- Chinese navigation: `🗓️ 学术会议`, `🧭 主题景观`
- English navigation: `🗓️ Academic conferences`, `🧭 Topic landscape`
- Russian navigation: `🗓️ Академические конференции`, `🧭 Тематический ландшафт`

The website language switch is in `docs/site.js`; current expected document links:

- 中文: `英文文档` / `俄语文档`
- English: `English documentation` / `Russian documentation`
- Русский: `Документация на английском` / `Документация на русском`

## Important constraints

- Do not copy code from `Jieli12/neurodaily`: it has no license.
- `config/config.json` and `config/profiles/` are intentionally gitignored and local-only.
- `config/demo.json` is tracked and drives the public demo.
- Public repositories are Apache-2.0.
- Do not commit generated secrets, email addresses, or local profile data.
- Keep `NEURODAILY_LLM_API_KEY`, `DOCKERHUB_TOKEN`, and signing secrets in GitHub Secrets; never echo them.
- The site may be cached by GitHub Pages for up to 10 minutes. Asset URLs in `docs/index.html` use a version query; hard refresh when verifying a fresh deploy.

## File map

- `neurodaily/digest.py`: retrieval windows and section assembly.
- `neurodaily/config.py`: defaults, including 168h trials and 7-day trial lookback.
- `neurodaily/ui_translations.py`: report navigation and UI localization catalog.
- `neurodaily/templates/report.html.j2`: report navigation, counts, sections.
- `neurodaily/settings_page.py`: settings UI defaults.
- `scripts/build_demo_snapshot.py`: 168h trilingual public demo.
- `docs/site.js` / `docs/index.html`: homepage language switch and demo iframe.
- `desktop/sidecar/linux_installer_smoke.py`: Linux DEB/AppImage and native UI checks.
- `desktop/sidecar/installer_smoke.py`: Windows installer/upgrade checks.
- `.github/workflows/daily-demo.yml`: 08:00 homepage updater.
- `.github/workflows/release-tauri.yml`: cross-platform release and publish.
- `docs/AGENT_INSTALL.md`: detailed agent-facing macOS/CLI/Docker/Actions installation guide.
- `HANDOFF.md`: this supervisor handoff.

## Supervisor checklist

1. `git status --short` is clean and `git log -1` matches the expected release commit.
2. `gh run list --limit 5` shows CI and Pages success.
3. `daily-demo` is enabled and the latest scheduled run succeeded; check the live trial count.
4. `v1.0.8` release exists, is not a draft, and contains Windows/Linux/macOS CLI/wheel assets.
5. Run a fresh browser check for the homepage language labels and both report navigation labels.
6. Record any failure with run URL, job name, exact failing step, and whether it is a test-only compatibility issue or a product regression.
