"""
Auto Normal/Abnormal detection for lab results.

Deliberately conservative: this is a CLINICAL system, so a wrong auto-flag
is worse than no auto-flag. If the reference range or the entered value
can't be parsed with confidence (qualitative tests like "Negative/Positive",
free-text ranges, multi-part ranges with age/gender notes, etc.), this
returns None and the lab tech makes the call manually — same as today.

This NEVER overrides a value the lab tech has already saved; it only
supplies the initial suggested state of the "Abnormal" checkbox, which
stays fully editable. The final saved value is always whatever the
checkbox shows at the moment they hit Save.
"""
import re

_RANGE_PAIR = re.compile(r'(-?\d+(?:\.\d+)?)\s*(?:-|to|–|—)\s*(-?\d+(?:\.\d+)?)', re.IGNORECASE)
_UPPER_ONLY = re.compile(r'^\s*[<≤]\s*(-?\d+(?:\.\d+)?)')
_LOWER_ONLY = re.compile(r'^\s*[>≥]\s*(-?\d+(?:\.\d+)?)')
_PLAIN_NUMBER = re.compile(r'^\s*(-?\d+(?:\.\d+)?)')


def parse_numeric_range(reference_range: str):
    """
    Returns (low, high) as floats, where either can be None for an
    open-ended bound, or None entirely if the range text isn't a
    confidently-parseable numeric range (e.g. "Negative", "See notes").
    """
    if not reference_range:
        return None
    text = reference_range.strip()

    pair = _RANGE_PAIR.search(text)
    if pair:
        low, high = float(pair.group(1)), float(pair.group(2))
        if low > high:
            low, high = high, low
        return (low, high)

    upper = _UPPER_ONLY.match(text)
    if upper:
        return (None, float(upper.group(1)))

    lower = _LOWER_ONLY.match(text)
    if lower:
        return (float(lower.group(1)), None)

    return None


def parse_numeric_value(result_value: str):
    """Extract a leading numeric value from a result string (e.g. '110 mg/dL' -> 110.0)."""
    if not result_value:
        return None
    match = _PLAIN_NUMBER.match(result_value.strip())
    if not match:
        return None
    return float(match.group(1))


def auto_flag_abnormal(result_value: str, reference_range: str):
    """
    Returns True/False if it can confidently determine Normal vs Abnormal,
    or None if either side of the comparison couldn't be parsed (in which
    case the caller must leave the decision to a human).
    """
    value = parse_numeric_value(result_value)
    if value is None:
        return None
    bounds = parse_numeric_range(reference_range)
    if bounds is None:
        return None
    low, high = bounds
    if low is not None and value < low:
        return True
    if high is not None and value > high:
        return True
    return False
