"""Small, explicit decision helpers for incremental-effect probes.

The Phase 5 classical-control line originally treated a confidence interval
that included zero as evidence that an added signal was redundant.  Failure
to reject a zero effect is not an equivalence test.  This module keeps the
project's decision margin explicit and distinguishes:

* evidence for a positive, practically material increment;
* evidence that the increment is smaller than the declared margin; and
* an inconclusive interval.

The helper does not decide whether the interval itself is valid.  Callers
must still use the correct resampling unit (normally composition/object, not
individual correlated queries) and name the evaluation universe.
"""

from __future__ import annotations


def practical_increment_verdict(
        delta: float,
        ci95: tuple[float, float] | list[float],
        margin: float,
        *,
        positive_label: str = "MATERIAL_INCREMENT_DETECTED",
        below_margin_label: str = "INCREMENT_BELOW_DECLARED_MARGIN",
        inconclusive_label: str = "INCONCLUSIVE",
) -> str:
    """Classify an incremental effect against a declared useful margin.

    A two-sided 95% interval with an upper endpoint below ``margin`` supports
    the bounded statement that effects at least as large as the margin are
    not supported in this setup.  A material-positive verdict requires both
    a positive lower endpoint and a point estimate at least as large as the
    margin.  All overlapping cases remain inconclusive.
    """
    if margin <= 0:
        raise ValueError("margin must be positive")
    if len(ci95) != 2:
        raise ValueError("ci95 must contain exactly two endpoints")
    lo, hi = float(ci95[0]), float(ci95[1])
    if lo > hi:
        raise ValueError("ci95 endpoints are reversed")
    if hi < margin:
        return below_margin_label
    if lo > 0.0 and delta >= margin:
        return positive_label
    return inconclusive_label
