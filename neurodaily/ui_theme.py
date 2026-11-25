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
