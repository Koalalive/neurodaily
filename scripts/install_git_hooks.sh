#!/bin/sh
# Install a local pre-commit hook that blocks personal addresses and API keys.
# Generic rules only (no real addresses embedded): blocks any @qq.com, any
# @sjtu.edu.cn except you@/example@, and sk- tokens.
set -e
ROOT=$(git rev-parse --show-toplevel)
HOOK="$ROOT/.git/hooks/pre-commit"

cat > "$HOOK" <<'HOOKEOF'
#!/bin/sh
PY="$PWD/.venv/bin/python"
[ -x "$PY" ] || PY=python3
"$PY" - <<'PYEOF'
import re, subprocess, sys
diff = subprocess.run(["git", "diff", "--cached", "-U0"], capture_output=True, text=True).stdout
added = "\n".join(l[1:] for l in diff.splitlines() if l.startswith("+") and not l.startswith("+++"))
bad = []
for m in re.finditer(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+)", added):
    addr, dom = m.group(0), m.group(1).lower()
    if dom == "qq.com":
        bad.append(addr)
    elif dom == "sjtu.edu.cn" and addr.lower() not in ("you@sjtu.edu.cn", "example@sjtu.edu.cn"):
        bad.append(addr)
if re.search(r"sk-[A-Za-z0-9_-]{16,}", added):
    bad.append("<api-key>")
if bad:
    print("\u2716 pre-commit blocked: " + ", ".join(sorted(set(bad))), file=sys.stderr)
    print("Use placeholders (you@example.com) or move secrets to gitignored files.", file=sys.stderr)
    sys.exit(1)
PYEOF
HOOKEOF

chmod +x "$HOOK"
echo "installed $HOOK"
