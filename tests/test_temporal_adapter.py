from datetime import datetime, timedelta, timezone
from memory.temporal_adapter import day_bounds, instant_bounds, month_bounds, year_bounds

assert year_bounds(2026) == (
    datetime(2026, 1, 1, tzinfo=timezone.utc),
    datetime(2027, 1, 1, tzinfo=timezone.utc),
)

assert month_bounds(2026, 12) == (
    datetime(2026, 12, 1, tzinfo=timezone.utc),
    datetime(2027, 1, 1, tzinfo=timezone.utc),
)

assert day_bounds(2026, 9, 1) == (
    datetime(2026, 9, 1, tzinfo=timezone.utc),
    datetime(2026, 9, 2, tzinfo=timezone.utc),
)

start, end = instant_bounds(
    datetime(2026, 9, 1, 12, 30, tzinfo=timezone(timedelta(hours=-7)))
)

expected = datetime(2026, 9, 1, 19, 30, tzinfo=timezone.utc)

assert start == expected
assert end == expected

print("TEMPORAL ADAPTER CONTRACT OK")
