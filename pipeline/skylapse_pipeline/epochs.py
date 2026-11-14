"""SPHEREx time clusters: split at gaps > 30 days; optionally split long clusters into bins of <= max_bin_days."""
from __future__ import annotations

import math

from .config import GAP_DAYS


def cluster_times(mjds: list[float], gap: float = GAP_DAYS, max_bin_days: float | None = None) -> list[tuple[float, float]]:
    """Return sorted (start, end) MJD intervals; every mjd falls in exactly one interval."""
    if not mjds:
        return []
    ts = sorted(mjds)
    clusters = [[ts[0], ts[0]]]
    for t in ts[1:]:
        if t - clusters[-1][1] > gap:
            clusters.append([t, t])
        else:
            clusters[-1][1] = t
    if not max_bin_days:
        return [tuple(c) for c in clusters]
    out = []
    for a, b in clusters:
        n = max(1, math.ceil((b - a) / max_bin_days))
        width = (b - a) / n if n > 1 else 0
        for i in range(n):
            lo = a + i * width
            hi = b if i == n - 1 else a + (i + 1) * width
            members = [t for t in ts if (lo <= t < hi) or (i == n - 1 and lo <= t <= hi)]
            if members:
                out.append((min(members), max(members)))
    return out


def assign(mjd: float, intervals: list[tuple[float, float]]) -> int:
    for i, (a, b) in enumerate(intervals):
        if a - 1e-6 <= mjd <= b + 1e-6:
            return i
    return -1
