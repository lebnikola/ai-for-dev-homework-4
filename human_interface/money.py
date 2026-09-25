from __future__ import annotations

import re

MAX_KOPECKS = 10**9

_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)*")


class AmountParseError(ValueError):
    pass


def to_kopecks(raw: str) -> int:
    cleaned = raw.replace("\u00a0", "").replace(" ", "")
    if not _NUMBER_RE.fullmatch(cleaned):
        raise AmountParseError(f"cannot parse amount: {raw!r}")

    parts = re.split(r"([.,])", cleaned)
    integer_part = parts[0]
    groups = parts[2::2]

    if not groups:
        kopecks = int(integer_part) * 100
    elif len(groups[-1]) <= 2:
        for group in groups[:-1]:
            if len(group) != 3:
                raise AmountParseError(f"cannot parse amount: {raw!r}")
        whole = integer_part + "".join(groups[:-1])
        fraction = groups[-1].ljust(2, "0")
        kopecks = int(whole) * 100 + int(fraction)
    elif len(groups[-1]) == 3:
        for group in groups:
            if len(group) != 3:
                raise AmountParseError(f"cannot parse amount: {raw!r}")
        kopecks = int(integer_part + "".join(groups)) * 100
    else:
        raise AmountParseError(f"cannot parse amount: {raw!r}")

    if kopecks <= 0:
        raise AmountParseError(f"amount must be positive: {raw!r}")
    if kopecks > MAX_KOPECKS:
        raise AmountParseError(f"amount too large: {raw!r}")
    return kopecks
