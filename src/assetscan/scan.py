"""The scan: Fame, Uniqueness, a 0-100 Distinctiveness Score and a grid quadrant for each asset.

Method (Romaniuk / Ehrenberg-Bass distinctive asset grid):
  Fame        = share of respondents who link the unbranded asset to YOUR brand.
  Uniqueness  = of all brand attributions the asset received, the share that went to YOUR brand.
  Score       = 100 x Fame^w x Uniqueness^(1-w)   (weighted geometric mean, w = 0.5 by default)
See docs/RESEARCH.md for why each choice was made and which parts are convention, not law.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from .stats import geometric_blend, percentile, posterior_draws, wilson

QUADRANTS = {
    "use": ("Use or lose", "Famous and yours. Protect it and put it in every high-reach touchpoint."),
    "invest": ("Invest", "Yours alone, but not famous yet. It needs reach and repetition to build fame."),
    "avoid": ("Avoid solo use", "Famous, but shared with rivals. On its own it advertises the category, not you."),
    "test": ("Test or ignore", "Neither famous nor unique. Rework it or put the effort into another asset."),
}
# The execution checklist from the monthly IDC audit (Sharp / Ehrenberg-Bass + Orlando Wood's System 1 items).
CHECKS = {
    "sound": "Recognisable without sound",
    "name": "Recognisable without the name",
    "context": "Recognisable out of context, cold, at scroll speed",
    "consistent": "Held constant across the last releases or campaigns",
    "instant": "Read instantly and by feel (System 1), not explained in copy",
}
BANDS = [(70, "Ownable"), (45, "Building"), (20, "Weak"), (0, "Not an asset")]


@dataclass
class Asset:
    name: str
    n: int                       # respondents shown the unbranded asset
    brand: int                   # linked it to your brand
    rivals: dict = field(default_factory=dict)   # rival name -> count (or {"rivals": total})
    prompted: bool = False       # was the brand list shown? (inflates fame)
    segment: str = ""            # e.g. "buyers", "non-buyers"; blank = everyone
    checks: dict = field(default_factory=dict)   # CHECKS key -> True / False / None (unverified)
    used: int = 0                # touchpoints where the asset appeared ...
    total: int = 0               # ... out of this many audited

    @property
    def rivals_total(self) -> int:
        return sum(self.rivals.values())


def validate(a: Asset) -> None:
    if not a.name.strip():
        raise ValueError("every asset needs a name")
    if a.n <= 0:
        raise ValueError(f"'{a.name}': respondents must be at least 1")
    counts = [a.brand, *a.rivals.values()]
    if any(c < 0 for c in counts):
        raise ValueError(f"'{a.name}': counts can't be negative")
    if a.brand + a.rivals_total > a.n:
        raise ValueError(f"'{a.name}': attributions ({a.brand + a.rivals_total}) exceed respondents ({a.n})")


def checklist(a: Asset) -> dict | None:
    """Execution audit: how well the asset is *deployed*, separate from how well it is *known*.
    Unverified items are left out of the score rather than counted as failures."""
    if not a.checks and not a.total:
        return None
    items = [{"key": k, "label": v, "result": a.checks.get(k)} for k, v in CHECKS.items()]
    passed = sum(1 for i in items if i["result"] is True)
    failed = sum(1 for i in items if i["result"] is False)
    checked = passed + failed
    coverage = a.used / a.total if a.total else None
    parts = ([passed / checked] if checked else []) + ([coverage] if coverage is not None else [])
    return {
        "items": items, "passed": passed, "failed": failed, "unverified": len(items) - checked,
        "coverage": coverage, "used": a.used, "total": a.total,
        "score": 100 * sum(parts) / len(parts) if parts else None,
    }


def band(score: float) -> str:
    return next(label for floor, label in BANDS if score >= floor)


def analyze_asset(a: Asset, fame_cut: float = 0.3, uniq_cut: float = 0.5, w_fame: float = 0.5) -> dict:
    validate(a)
    r = a.rivals_total
    attributed = a.brand + r
    unknown = a.n - attributed
    fame = a.brand / a.n
    uniq = a.brand / attributed if attributed else 0.0
    f_lo, f_hi = wilson(a.brand, a.n)
    u_lo, u_hi = wilson(a.brand, attributed) if attributed else (0.0, 1.0)
    score = 100 * geometric_blend(fame, uniq, w_fame)

    draws = posterior_draws(a.brand, r, unknown)
    scores = sorted(100 * geometric_blend(f, u, w_fame) for f, u in draws)
    probs = {"use": 0, "invest": 0, "avoid": 0, "test": 0}
    for f, u in draws:
        key = ("use" if u >= uniq_cut else "avoid") if f >= fame_cut else ("invest" if u >= uniq_cut else "test")
        probs[key] += 1
    probs = {k: v / len(draws) for k, v in probs.items()}

    quad = ("use" if uniq >= uniq_cut else "avoid") if fame >= fame_cut else ("invest" if uniq >= uniq_cut else "test")

    # Who else gets the credit? Shares over everyone who linked the asset to any brand.
    shares = {"You": a.brand / attributed if attributed else 0.0}
    for k, v in sorted(a.rivals.items(), key=lambda kv: -kv[1]):
        shares[k] = v / attributed if attributed else 0.0
    rival_names = [k for k in a.rivals if a.rivals[k] > 0]
    top_rival = max(rival_names, key=lambda k: a.rivals[k]) if rival_names else None
    hhi = sum(s * s for s in shares.values())
    entropy = -sum(s * math.log(s) for s in shares.values() if s > 0)
    max_ent = math.log(len(shares)) if len(shares) > 1 else 1.0

    half = (f_hi - f_lo) / 2
    confidence = "solid" if half <= 0.05 else "fair" if half <= 0.08 else "thin"
    notes = []
    if a.n < 100:
        notes.append(f"Only {a.n} respondents. Fame is an estimate with a wide interval (±{half * 100:.0f} points).")
    if attributed < 30:
        notes.append(f"Only {attributed} people linked this asset to any brand, so uniqueness rests on a small base.")
    if a.prompted:
        notes.append("Prompted test: showing a brand list inflates fame, by up to about 20 points in Romaniuk's work. Treat fame as a ceiling.")
    if attributed == 0:
        notes.append("Nobody linked this asset to any brand. Fame is zero and uniqueness can't be measured.")
    if top_rival and a.rivals[top_rival] > a.brand:
        notes.append(f"{top_rival} gets more credit for this asset than you do.")
    if quad == "avoid" and top_rival:
        notes.append(f"The leak is mostly {top_rival} ({a.rivals[top_rival] / attributed * 100:.0f}% of attributions).")

    ck = checklist(a)
    if ck and ck["score"] is not None:
        if score >= 45 and ck["score"] < 50:
            notes.append("Well known but poorly deployed. Audit shows it isn't being used consistently, so recognition may fade.")
        if score < 45 and ck["score"] >= 70:
            notes.append("Deployed well but not yet known. The execution is fine, so the gap is reach and repetition.")
    if a.total and a.used > a.total:
        raise ValueError(f"'{a.name}': touchpoints used ({a.used}) exceed audited ({a.total})")

    return {
        "name": a.name, "n": a.n, "segment": a.segment, "checklist": ck, "brand": a.brand, "rivals": r, "unknown": unknown,
        "fame": fame, "fame_ci": [f_lo, f_hi],
        "uniqueness": uniq, "uniqueness_ci": [u_lo, u_hi],
        "score": score, "score_ci": [percentile(scores, 0.025), percentile(scores, 0.975)],
        "band": band(score),
        "quadrant": quad, "quadrant_label": QUADRANTS[quad][0], "action": QUADRANTS[quad][1],
        "quadrant_probs": probs,
        "shares": shares, "top_rival": top_rival,
        "concentration": hhi, "ownership": (1 - entropy / max_ent) if max_ent else 0.0,
        "confidence": confidence, "prompted": a.prompted, "notes": notes,
    }


def pool(rows: list[Asset]) -> Asset:
    """Combine segment rows into one asset by summing counts (respondents are independent across segments)."""
    if len(rows) == 1:
        return rows[0]
    rivals: dict = {}
    for r in rows:
        for k, v in r.rivals.items():
            rivals[k] = rivals.get(k, 0) + v
    checks = {}
    for r in rows:
        for k, v in r.checks.items():
            if checks.get(k) is None:
                checks[k] = v
    first = next((r for r in rows if r.total), rows[0])
    return Asset(rows[0].name, sum(r.n for r in rows), sum(r.brand for r in rows), rivals,
                 any(r.prompted for r in rows), "", checks, first.used, first.total)


def _seg_view(r: dict) -> dict:
    keys = ("segment", "n", "fame", "fame_ci", "uniqueness", "uniqueness_ci", "score", "score_ci", "quadrant", "quadrant_label")
    return {k: r[k] for k in keys}


def analyze(assets: list[Asset], fame_cut: float = 0.3, uniq_cut: float = 0.5, w_fame: float = 0.5) -> dict:
    if not assets:
        raise ValueError("add at least one asset")
    if not (0 < fame_cut < 1 and 0 < uniq_cut < 1):
        raise ValueError("thresholds must be between 0 and 100%")
    if not (0 < w_fame < 1):
        raise ValueError("fame weight must be between 0 and 1")
    groups: dict[str, list[Asset]] = {}
    for a in assets:
        groups.setdefault(a.name.strip().lower(), []).append(a)
    pooled = []
    for rows_ in groups.values():
        segs = [r.segment.strip().lower() for r in rows_]
        if len(rows_) > 1 and (len(set(segs)) != len(segs) or "" in segs):
            raise ValueError(f"'{rows_[0].name}' appears twice. Give each row a different segment, or merge them")
        pooled.append((pool(rows_), rows_ if len(rows_) > 1 else []))
    rows = []
    for asset, parts in pooled:
        r = analyze_asset(asset, fame_cut, uniq_cut, w_fame)
        r["segments"] = [_seg_view(analyze_asset(p, fame_cut, uniq_cut, w_fame)) for p in parts]
        rows.append(r)
    rows.sort(key=lambda r: -r["score"])
    # Portfolio view: how much of the brand's recognition is concentrated in its best asset.
    top = rows[0]
    summary = {
        "assets": len(rows), "best": top["name"], "best_score": top["score"],
        "portfolio_score": sum(r["score"] for r in rows) / len(rows),
        "ownable": sum(1 for r in rows if r["score"] >= 70),
        "segments": sorted({sg["segment"] for r in rows for sg in r["segments"]}),
    }
    return {"settings": {"fame_cut": fame_cut, "uniq_cut": uniq_cut, "w_fame": w_fame},
            "summary": summary, "assets": rows}
