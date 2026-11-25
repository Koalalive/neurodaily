"""Shared Editorial visual language for the workspace pages.

The report template owns its richer article layout; this module makes the
surrounding app (settings, history, tasks, billing, archive and desktop tabs)
share the same paper-like palette and type system.
"""

UI_CSS = r"""
:root {
  --bg: #090a0c !important;
  --panel: #0e1013 !important;
  --panel2: #121419 !important;
  --line: rgba(255,255,255,.10) !important;
  --accent: #c8a96b !important;
  --accent2: #8da7a1 !important;
  --text: #ece9e2 !important;
  --muted: #979791 !important;
  --serif: "Source Serif 4", "Iowan Old Style", "Noto Serif CJK SC", "Songti SC", Georgia, serif;
  --sans: var(--serif);
  color-scheme: dark;
}
html { background: var(--bg); color-scheme: dark; scrollbar-color: #3b3a37 #0b0c0e; }
body, button, input, select, textarea, h1, h2, h3, h4, h5, h6,
label, p, a, th, td, summary, small, .mini, .hint, .desc, .pill {
  font-family: var(--serif) !important;
}
body { background: var(--bg) !important; color: var(--text) !important; letter-spacing: .001em; }
h1, h2, h3, h4 { color: var(--text) !important; font-weight: 600 !important; letter-spacing: -.015em; }
h1 { color: var(--accent) !important; }
a { color: var(--accent) !important; text-underline-offset: .18em; }
a:hover { color: #e3cfa0 !important; }
header, footer { background: var(--bg) !important; border-color: var(--line) !important; }
section { background: var(--panel) !important; border-color: var(--line) !important; border-radius: 2px !important; }
input, select, textarea { background: var(--panel2) !important; border-color: var(--line) !important; color: var(--text) !important; border-radius: 2px !important; }
input:focus, select:focus, textarea:focus { border-color: var(--accent) !important; outline: 1px solid var(--accent) !important; }
button { background: transparent !important; border-color: var(--line) !important; border-radius: 2px !important; color: var(--muted) !important; }
button:hover { border-color: var(--accent) !important; color: var(--accent) !important; }
button[aria-pressed=true], button.primary { background: var(--accent) !important; border-color: var(--accent) !important; color: #171207 !important; }
button.primary { background: var(--accent) !important; }
button.del, button.warn { color: #c47a6b !important; border-color: #4a2e2a !important; }
button:disabled { opacity: .45 !important; }
.pill { background: transparent !important; border-color: var(--line) !important; color: var(--muted) !important; }
.pill.on { color: var(--accent2) !important; border-color: #3e5751 !important; }
.mini, .hint, .desc, small { color: var(--muted) !important; }
table, th, td { border-color: var(--line) !important; }
th { background: transparent !important; color: var(--muted) !important; }
td { color: var(--text) !important; }
#optimization-workbench, .optimization-columns, .optimization-chat-column,
.optimization-evidence-column, .optimization-card, #optimization-chat,
#optimization-findings details, .optimization-card details {
  border-color: var(--line) !important;
}
.optimization-chat-column, .optimization-evidence-column, .optimization-card,
#optimization-chat { background: var(--panel) !important; border-radius: 2px !important; }
.optimization-heading h3 { color: var(--text) !important; }
.optimization-switch input { accent-color: var(--accent) !important; }
#optimization-error { color: #c47a6b !important; }
.optimization-metrics { color: var(--muted) !important; }
.optimization-records button { color: var(--muted) !important; }
"""


def inject_ui_theme(html: str) -> str:
    """Append the shared theme after page-local CSS so it wins the cascade."""
    if not html:
        return html
    style = "<style id=\"nd-editorial-theme\">" + UI_CSS + "</style>"
    if "</head>" in html:
        return html.replace("</head>", style + "</head>", 1)
    if "<body" in html:
        return html.replace("<body", style + "<body", 1)
    return style + html

# Visible app-shell pass: the token-only theme above is not enough for the
# dense settings page. These rules turn the surrounding app into the same
# editorial surface as the report.
UI_CSS += r"""
body > header {
  min-height: 112px !important; padding: 30px 30px 24px !important;
  border-bottom: 1px solid var(--line) !important;
  background: radial-gradient(70% 120% at 12% 0%, #17171a 0%, transparent 72%), var(--bg) !important;
}
body > header h1 {
  color: var(--text) !important; font-size: clamp(1.8rem, 3.2vw, 2.8rem) !important;
  line-height: 1.05 !important; letter-spacing: -.03em !important;
}
body > header h1::before {
  content: "NEURODAILY / SETTINGS"; display: block; margin-bottom: 10px;
  color: var(--accent) !important; font: 500 .56em/1.2 var(--serif);
  letter-spacing: .16em;
}
body > header a { color: var(--muted) !important; font-size: .76rem !important; }
body > header .mini { color: #77756e !important; }
main { max-width: 1120px !important; padding: 34px 30px 76px !important; }
section {
  background: transparent !important; border: 0 !important;
  border-top: 1px solid var(--line) !important; border-radius: 0 !important;
  padding: 26px 0 24px !important; margin: 0 0 10px !important;
}
section h2 { font-size: clamp(1.35rem, 2vw, 1.75rem) !important; margin-bottom: 6px !important; }
section .desc { color: var(--muted) !important; max-width: 76ch; margin-bottom: 16px !important; }
section > .inline:first-of-type { gap: 18px !important; }
input, select, textarea { min-height: 34px; }
input, select, textarea, button { font-size: .82rem !important; }
button.primary {
  background: var(--accent) !important; color: #171207 !important;
  border: 1px solid var(--accent) !important; border-radius: 1px !important;
  padding: 8px 18px !important;
}
button { padding: 6px 10px !important; }
.j-metrics { border-bottom-color: var(--line) !important; }
.j-metrics summary { color: var(--accent) !important; }
footer {
  border-top: 1px solid var(--line) !important; padding: 18px 30px !important;
  background: var(--bg) !important;
}
.optimization-chat-column, .optimization-evidence-column, .optimization-card,
#optimization-chat { background: transparent !important; border: 1px solid var(--line) !important; }
.optimization-columns { gap: 28px !important; }
#optimization-workbench { border-top-color: var(--line) !important; margin-top: 28px !important; }
#optimization-workbench h3 { font-size: 1.35rem !important; }
#optimization-chat { min-height: 9rem; }
.optimization-heading { padding-bottom: 10px; border-bottom: 1px solid var(--line); }
@media (max-width: 640px) {
  body > header { min-height: 0 !important; padding: 24px 18px 18px !important; }
  main { padding: 24px 18px 64px !important; }
  section { padding: 22px 0 20px !important; }
}
"""

# Primary action buttons live inside pages with their own IDs, so the generic
# button reset above must be followed by an explicit primary treatment.
UI_CSS += r"""
#go, button.primary, .button-primary {
  background: var(--accent) !important;
  border: 1px solid var(--accent) !important;
  border-radius: 1px !important;
  color: #171207 !important;
  font-weight: 700 !important;
  padding: 9px 18px !important;
  opacity: 1;
}
#go:hover, button.primary:hover, .button-primary:hover {
  background: #ddc183 !important;
  border-color: #ddc183 !important;
  color: #171207 !important;
}
#go:disabled {
  background: #2a261e !important;
  border-color: #5d5547 !important;
  color: #bdb5a5 !important;
  opacity: 1;
}
"""
