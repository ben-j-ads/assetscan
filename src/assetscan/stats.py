"""Statistical primitives. Standard library only."""
from __future__ import annotations

import math
import random
from statistics import NormalDist

_N = NormalDist()


def wilson(successes: int, n: int, conf: float = 0.95) -> tuple[float, float]:
    """Wilson score interval for a proportion. Behaves at 0, 1 and small n, unlike the Wald interval."""
    if n <= 0:
        return (0.0, 1.0)
    z = _N.inv_cdf(0.5 + conf / 2)
    p = successes / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, centre - half), min(1.0, centre + half))


def n_for_margin(margin: float, p: float = 0.5, conf: float = 0.95) -> int:
    """Respondents needed so a proportion near p has a +/- margin interval (normal approximation)."""
    z = _N.inv_cdf(0.5 + conf / 2)
    return math.ceil(z * z * p * (1 - p) / (margin * margin))


def geometric_blend(fame: float, uniqueness: float, w_fame: float = 0.5) -> float:
    """Weighted geometric mean of two 0..1 quantities. Zero if either is zero: an asset needs both."""
    if fame <= 0 or uniqueness <= 0:
        return 0.0
    return fame ** w_fame * uniqueness ** (1 - w_fame)


def posterior_draws(brand: int, rivals: int, unknown: int, draws: int = 4000, seed: int = 7):
    """Joint posterior draws of (fame, uniqueness) from a Dirichlet(1,1,1) prior over
    (linked to you, linked to a rival, no link). Fame = p_brand. Uniqueness = p_brand / (p_brand + p_rival).
    Seeded, so the same data always gives the same answer."""
    rng = random.Random(seed)
    out = []
    for _ in range(draws):
        a = rng.gammavariate(brand + 1, 1)
        b = rng.gammavariate(rivals + 1, 1)
        c = rng.gammavariate(unknown + 1, 1)
        out.append((a / (a + b + c), a / (a + b)))
    return out


def percentile(sorted_vals: list[float], q: float) -> float:
    if not sorted_vals:
        return 0.0
    i = min(len(sorted_vals) - 1, max(0, int(round(q * (len(sorted_vals) - 1)))))
    return sorted_vals[i]
