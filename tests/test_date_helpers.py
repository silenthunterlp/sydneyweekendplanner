from datetime import date

from sydney_planner.utils.date_helpers import get_upcoming_weekend


def test_returns_saturday_and_sunday():
    saturday_str, sunday_str = get_upcoming_weekend()
    saturday = date.fromisoformat(saturday_str)
    sunday = date.fromisoformat(sunday_str)
    assert saturday.weekday() == 5  # Saturday
    assert sunday.weekday() == 6    # Sunday
    assert (sunday - saturday).days == 1


def test_saturday_is_in_the_future_or_today():
    saturday_str, _ = get_upcoming_weekend()
    saturday = date.fromisoformat(saturday_str)
    assert saturday >= date.today()
