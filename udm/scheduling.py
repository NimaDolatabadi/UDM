"""Download schedule eligibility and concurrency policy."""

from datetime import datetime, time, timedelta


def schedule_is_open(schedule, now=None):
    """Return whether an enabled schedule permits transfers at ``now``."""
    now = now or datetime.now()
    if not schedule.get("active", False):
        return False
    try:
        start_date = datetime.strptime(schedule["start_date"], "%Y-%m-%d").date()
        end_date = datetime.strptime(schedule["end_date"], "%Y-%m-%d").date()
        start_time = time.fromisoformat(schedule["start_time"])
        end_time = time.fromisoformat(schedule["end_time"])
    except (KeyError, TypeError, ValueError):
        return False
    current = now.time().replace(second=0, microsecond=0)
    overnight = start_time > end_time
    anchor_date = (
        now.date() - timedelta(days=1)
        if overnight and current <= end_time
        else now.date()
    )
    if not start_date <= anchor_date <= end_date:
        return False
    recurrence = schedule.get("recurrence", "Every Day")
    if recurrence == "Even Days" and anchor_date.day % 2:
        return False
    if recurrence == "Odd Days" and not anchor_date.day % 2:
        return False
    if not overnight:
        return start_time <= current <= end_time
    # An overnight window spans midnight within each eligible calendar date.
    return current >= start_time or current <= end_time


def schedule_limit(schedule):
    """Return a schedule's validated positive concurrency limit."""
    try:
        return max(1, int(schedule.get("max_dl", 1)))
    except (TypeError, ValueError):
        return 1
