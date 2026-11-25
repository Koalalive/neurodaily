"""Daily schedule tied to the desktop sidecar's lifetime."""
from __future__ import annotations

import logging
from datetime import datetime, time, timedelta

RETRY_DELAY = timedelta(minutes=5)


def scheduled_time(scheduled: dict) -> time | None:
    if not scheduled.get("enabled") or scheduled.get("paused"):
        return None
    try:
        return time(int(scheduled.get("hour", 8)), int(scheduled.get("minute", 0)))
    except (TypeError, ValueError):
        return None


def run_schedule(stop, load_config, start_search, now=datetime.now) -> None:
    """Run today's due slot, including after an app restart or system wake."""
    completed = set()
    day = None
    while not stop.is_set():
        try:
            config = load_config()
            current = now()
            schedule = scheduled_time(config.scheduled)
            if day != current.date():
                day = current.date()
                completed.clear()
            if schedule is not None:
                due = datetime.combine(day, schedule)
                slot = (config.profile, due)
                if due <= current and slot not in completed and not stop.is_set():
                    if start_search(config, due):
                        completed.add(slot)
        except Exception:
            logging.getLogger(__name__).exception("Could not check the desktop schedule")
        stop.wait(5)
