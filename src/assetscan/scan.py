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
BANDS = [(70, "Ownable"), (45, "Building"), (20, "Weak"), (0, "Not an asset")]


@dataclass
class Asset:
    name: str
    n: int                       # respondents shown the unbranded asset
    brand: int                   # linked it to your brand
    rivals: dict = field(default_factory=dict)   # rival name -> count (or {"rivals": total})
    prompted: bool = False       # was the brand list shown? (inflates fame)

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

    return {
        "name": a.name, "n": a.n, "brand": a.brand, "rivals": r, "unknown": unknown,
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


def analyze(assets: list[Asset], fame_cut: float = 0.3, uniq_cut: float = 0.5, w_fame: float = 0.5) -> dict:
    if not assets:
        raise ValueError("add at least one asset")
    if not (0 < fame_cut < 1 and 0 < uniq_cut < 1):
        raise ValueError("thresholds must be between 0 and 100%")
    if not (0 < w_fame < 1):
        raise ValueError("fame weight must be between 0 and 1")
    names = [a.name.strip().lower() for a in assets]
    if len(set(names)) != len(names):
        raise ValueError("asset names must be unique")
    rows = [analyze_asset(a, fame_cut, uniq_cut, w_fame) for a in assets]
    rows.sort(key=lambda r: -r["score"])
    # Portfolio view: how much of the brand's recognition is concentrated in its best asset.
    top = rows[0]
    summary = {
        "assets": len(rows), "best": top["name"], "best_score": top["score"],
        "portfolio_score": sum(r["score"] for r in rows) / len(rows),
        "ownable": sum(1 for r in rows if r["score"] >= 70),
    }
    return {"settings": {"fame_cut": fame_cut, "uniq_cut": uniq_cut, "w_fame": w_fame},
            "summary": summary, "assets": rows}
