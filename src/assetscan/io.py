"""CSV input. Columns: asset, respondents, brand, then one column per rival (header = rival name).
Optional `prompted` column (yes/no). Respondents who linked the asset to nobody are inferred."""
from __future__ import annotations

import csv
import io

from .scan import Asset

NAME = {"asset", "name"}
N = {"respondents", "n", "shown", "sample"}
BRAND = {"brand", "you", "yours", "linked_to_you", "linked_to_brand"}
PROMPTED = {"prompted"}


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
    if None in (i_name, i_n, i_brand):
        raise ValueError("the header needs asset, respondents and brand columns, then one column per rival")
    used = {i_name, i_n, i_brand, i_pr}
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
        ))
    return out


def read_csv(path: str) -> list[Asset]:
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return read_csv_text(fh.read())
