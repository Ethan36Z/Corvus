import re
from datetime import datetime, timedelta, timezone

from dateparser.search import search_dates


YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")


def year_bounds(year: int):
    """Return the canonical half-open interval for a calendar year."""
    return (
        datetime(year, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        datetime(year + 1, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
    )


def month_bounds(year: int, month: int):
    """Return the canonical half-open interval for a calendar month."""
    if not 1 <= month <= 12:
        raise ValueError("month must be in 1..12")

    start = datetime(year, month, 1, 0, 0, 0, tzinfo=timezone.utc)

    if month == 12:
        end = datetime(year + 1, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    else:
        end = datetime(year, month + 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    return start, end


def day_bounds(year: int, month: int, day: int):
    """Return the canonical half-open interval for a calendar day."""
    start = datetime(year, month, day, 0, 0, 0, tzinfo=timezone.utc)
    return start, start + timedelta(days=1)


def instant_bounds(value: datetime):
    """
    Return the canonical point encoding for an instant.

    Equal endpoints here represent a temporal POINT sentinel, not a
    half-open duration interval. Callers must use granularity=INSTANT
    to distinguish point semantics from interval semantics.
    """
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)

    return value, value


def parse_temporal_expression(text: str, reference: datetime):
    results = search_dates(
        text,
        languages=["en"],
        settings={
            "RELATIVE_BASE": reference,
            "RETURN_AS_TIMEZONE_AWARE": False,
        },
    )

    if not results:
        return None

    source_text, parsed_dt = results[0]
    source_lower = source_text.lower().strip()

    year_match = YEAR_RE.search(source_text)

    if year_match:
        year = int(year_match.group(0))
        interval_start, interval_end = year_bounds(year)

        return {
            "source_text": source_text,
            "normalized_value": str(year),
            "granularity": "YEAR",
            "interval_start": interval_start.isoformat(),
            "interval_end": interval_end.isoformat(),
            "provenance": "USER_EXPLICIT",
            "derivation": "DIRECT_NORMALIZATION",
        }

    if source_lower == "now":
        interval_start, interval_end = instant_bounds(parsed_dt)

        return {
            "source_text": source_text,
            "normalized_value": parsed_dt.isoformat(timespec="minutes"),
            "granularity": "INSTANT",
            "interval_start": interval_start.isoformat(),
            "interval_end": interval_end.isoformat(),
            "provenance": "USER_EXPLICIT",
            "derivation": "DERIVED_DETERMINISTIC",
        }

    if source_lower == "last year":
        year = parsed_dt.year
        interval_start, interval_end = year_bounds(year)

        return {
            "source_text": source_text,
            "normalized_value": str(year),
            "granularity": "YEAR",
            "interval_start": interval_start.isoformat(),
            "interval_end": interval_end.isoformat(),
            "provenance": "USER_EXPLICIT",
            "derivation": "DERIVED_DETERMINISTIC",
        }

    return {
        "source_text": source_text,
        "normalized_value": None,
        "granularity": "UNKNOWN",
        "interval_start": None,
        "interval_end": None,
        "provenance": "USER_EXPLICIT",
        "derivation": "UNRESOLVED",
    }


if __name__ == "__main__":
    reference = datetime(2026, 8, 31, 10, 39)

    samples = [
        "I lived in Beijing in 2020.",
        "I live in Los Angeles now.",
        "I moved here last year.",
    ]

    for sample in samples:
        print("TEXT:", sample)
        print(parse_temporal_expression(sample, reference))
        print("-" * 60)
