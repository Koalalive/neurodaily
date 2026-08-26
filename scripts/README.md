# scripts/

The `com.neurodaily.daily.plist` in this directory is **machine-generated** by
`neurodaily launchd install` and contains local absolute paths
(e.g. `/Users/<you>/neurodaily/.venv/bin/python`), so it is not committed.

To set up the daily 08:00 schedule on your machine:

```bash
cd ~/neurodaily
.venv/bin/python -m neurodaily launchd install   # writes scripts/com.neurodaily.daily.plist + loads it
.venv/bin/python -m neurodaily launchd show      # preview the plist
.venv/bin/python -m neurodaily launchd uninstall # remove it
```
