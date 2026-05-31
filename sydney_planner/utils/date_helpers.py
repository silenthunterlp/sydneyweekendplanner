from datetime import date, timedelta


def get_upcoming_weekend() -> tuple[str, str]:
    """Return (saturday_iso, sunday_iso) for the next upcoming weekend."""
    today = date.today()
    # weekday(): Monday=0 ... Saturday=5, Sunday=6
    days_until_saturday = (5 - today.weekday()) % 7
    if days_until_saturday == 0 and today.weekday() == 5:
        # Today is Saturday
        saturday = today
    elif today.weekday() == 6:
        # Today is Sunday — show next weekend
        saturday = today + timedelta(days=6)
    else:
        saturday = today + timedelta(days=days_until_saturday)
    sunday = saturday + timedelta(days=1)
    return (saturday.isoformat(), sunday.isoformat())
