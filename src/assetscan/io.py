"""CSV input. Columns: asset, respondents, brand, then one column per rival (header = rival name).
Optional columns: `prompted` (yes/no); `segment` (one row per asset per segment); the audit:
`check_sound`, `check_name`, `check_context`, `check_consistent`, `check_instant` (yes/no/blank = unverified),
`touchpoints_used`, `touchpoints_total`. Respondents who linked the asset to nobody are inferred."""
from __future__ import annotations

import csv
import io

from .scan import CHECKS, Asset

NAME = {"asset", "name"}
N = {"respondents", "n", "shown", "sample"}
BRAND = {"brand", "you", "yours", "linked_to_you", "linked_to_brand"}
PROMPTED = {"prompted"}
SEGMENT = {"segment"}
USED = {"touchpoints_used"}
TOTAL = {"touchpoints_total"}


def tri(v: str):
    v = str(v).strip().lower()
    return True if v in {"yes", "y", "true", "1", "pass"} else False if v in {"no", "n", "false", "0", "fail"} else None


def _int(v: str, what: str) -> int:
    try:
        f = float(str(v).strip() or 0)
    except ValueError:
        raise ValueError(f"{what} must be a whole number, got '{v}'") from None
    if f != int(f):
        raise ValueError(f"{what} must be a whole number, got '{v}'")
    return int(f)


def read_csv_text(text: str) -> list[Asset]:
    rows = list(csv.reader(io.StringIO(text.strip())))
    if len(rows) < 2:
        raise ValueError("the csv needs a header row and at least one asset")
    head = [h.strip() for h in rows[0]]
    low = [h.lower() for h in head]

    def find(options):
        for i, h in enumerate(low):
            if h in options:
                return i
        return None

    i_name, i_n, i_brand, i_pr = find(NAME), find(N), find(BRAND), find(PROMPTED)
    i_seg, i_used, i_total = find(SEGMENT), find(USED), find(TOTAL)
    check_cols = {k: low.index(f"check_{k}") for k in CHECKS if f"check_{k}" in low}
    if None in (i_name, i_n, i_brand):
        raise ValueError("the header needs asset, respondents and brand columns, then one column per rival")
    used = {i_name, i_n, i_brand, i_pr, i_seg, i_used, i_total, *check_cols.values()}
    rival_cols = [(i, head[i]) for i in range(len(head)) if i not in used and head[i]]
    out = []
    for line in rows[1:]:
        if not any(c.strip() for c in line):
            continue
        line = line + [""] * (len(head) - len(line))
        name = line[i_name].strip()
        out.append(Asset(
            name=name, n=_int(line[i_n], f"'{name}' respondents"), brand=_int(line[i_brand], f"'{name}' brand"),
            rivals={r: _int(line[i], f"'{name}' {r}") for i, r in rival_cols if _int(line[i], f"'{name}' {r}") > 0},
            prompted=(i_pr is not None and line[i_pr].strip().lower() in {"yes", "y", "true", "1"}),
            segment=line[i_seg].strip() if i_seg is not None else "",
            checks={k: tri(line[i]) for k, i in check_cols.items()},
            used=_int(line[i_used], f"'{name}' touchpoints used") if i_used is not None else 0,
            total=_int(line[i_total], f"'{name}' touchpoints total") if i_total is not None else 0,
        ))
    return out


def read_csv(path: str) -> list[Asset]:
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return read_csv_text(fh.read())
