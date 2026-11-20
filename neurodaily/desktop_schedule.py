"""Daily schedule tied to the desktop sidecar's lifetime."""
from __future__ import annotations

import logging
from datetime import datetime, time


def scheduled_time(scheduled: dict) -> time | None:
    if not scheduled.get("enabled"):
        return None
    try:
        return time(int(scheduled.get("hour", 8)), int(scheduled.get("minute", 0)))
    except (TypeError, ValueError):
        return None


def run_schedule(stop, load_config, start_search, now=datetime.now) -> None:
    """Start one scheduled attempt per day and wait for any active search."""
    previous_time = None
    active_since = now()
    last_started = None
    while not stop.is_set():
        try:
            config = load_config()
            current = now()
            schedule = scheduled_time(config.scheduled)
            if schedule != previous_time:
                previous_time = schedule
                active_since = current
            today = current.date()
            if schedule is not None and last_started != today:
                due = datetime.combine(today, schedule)
                if active_since <= due <= current and not stop.is_set():
                    if start_search(config, today):
                        last_started = today
        except Exception:
            logging.getLogger(__name__).exception("Could not check the desktop schedule")
        stop.wait(5)
