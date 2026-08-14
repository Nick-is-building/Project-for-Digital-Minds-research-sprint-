"""Nonparametric King & Wand (2007) rescaling (DESIGN.md §5).

Maps a self-report `y` onto a 5-point common scale using the two vignette
ratings `z_lo` and `z_hi` elicited in the same context.

## How the bounds are derived

DESIGN.md §5 fixes the properly-ordered ladder (`z_lo < z_hi`):

    y < z_lo         -> 1        y == z_hi        -> 4
    y == z_lo        -> 2        y > z_hi         -> 5
    z_lo < y < z_hi  -> 3

That ladder is undefined when the anchors are tied or misordered, where the
true `C` is an interval. Rather than special-casing three branches, this module
uses one construction that covers all of them: compare `y` to each anchor
*separately*, and read off what each comparison alone implies about `C`.

    y <  z_lo -> {1}        y >  z_hi -> {5}
    y == z_lo -> {2}        y == z_hi -> {4}
    y >  z_lo -> {3,4,5}    y <  z_hi -> {1,2,3}

Two properties make this the right generalisation:

1. When the intersection of the two constraints is non-empty it is always a
   singleton, and on ordered anchors it reproduces the DESIGN.md ladder above
   exactly, equality cases included. Nothing about the ordered case changes.
2. The intersection is empty **iff** `z_hi <= y <= z_lo` — precisely the tied
   and misordered cases. The degeneracy is detected by the arithmetic instead
   of being tested for separately.

When the intersection is empty the two anchors place `y` in contradictory
positions, so `C` is only interval-identified; the interval is the hull of the
two constraints and `tie_rule` selects a bound. Written in terms of
`lo = min(z_lo, z_hi)` and `hi = max(z_lo, z_hi)` as DESIGN.md §5 puts it, the
crossed region `lo <= y <= hi` yields

    lower bound = 2 if y == hi else 1
    upper bound = 4 if y == lo else 5

so tied anchors with `y` equal to them give [2, 4], and a misordered pair
straddling `y` gives the uninformative [1, 5]. Note that a misordered pair does
*not* always destroy identification: with `z_lo=4, z_hi=2, y=5`, `y` is above
both anchors and `C = 5` regardless of the ordering violation. Those cases come
back with both bounds equal, which is a degenerate interval, not a contradiction
of DESIGN.md.

Running the whole analysis once per `tie_rule` and checking agreement is the
robustness check (DESIGN.md §5, after He et al. 2017).

## Tolerance

Inputs are means over `config.N_SAMPLES` draws, so they are continuous and exact
equality is rare. Equality uses `config.TOLERANCE`. How often that tolerance
fires is a reported diagnostic, not an internal detail: see `tolerance_counts`.

## What this module must never become

`C` is a function of `y` *and the two anchors*. If the anchors are constant
across observations it collapses to a function of `y` alone and every rank-based
statistic is invariant by construction — a guaranteed null result. That is a
property of this mathematics, not a bug to be patched here. See CLAUDE.md,
"THE ONE RULE THAT PROTECTS THE PROJECT", and tests/test_rescale.py.
"""

from dataclasses import dataclass

from pilot import config

TIE_RULES = ("lower", "upper")


@dataclass(frozen=True)
class ToleranceCounts:
    """How often tolerance-based equality fired, since the last reset."""

    calls: int
    y_vs_z_lo: int
    y_vs_z_hi: int
    z_lo_vs_z_hi: int


_counts = {"calls": 0, "y_vs_z_lo": 0, "y_vs_z_hi": 0, "z_lo_vs_z_hi": 0}


def tolerance_counts() -> ToleranceCounts:
    """Tolerance-firing counts accumulated over `compute_C` calls.

    Process-global: reset before a run whose diagnostics you intend to report.
    `calls` counts only calls that computed a value, not `None` returns.
    """
    return ToleranceCounts(**_counts)


def reset_tolerance_counts() -> None:
    for key in _counts:
        _counts[key] = 0


def _equal(a: float, b: float) -> bool:
    return abs(a - b) <= config.TOLERANCE


def compute_C(
    y: float | None,
    z_lo: float | None,
    z_hi: float | None,
    tie_rule: str,
) -> float | None:
    """Rescales `y` against the anchors `z_lo`/`z_hi` onto the 5-point scale.

    `tie_rule` selects which bound to return where `C` is only
    interval-identified (tied or misordered anchors); it has no effect
    otherwise. Returns None iff any input is None — a parse failure upstream
    (DESIGN.md §4) is not something to guess a rating for.
    """
    if tie_rule not in TIE_RULES:
        raise ValueError(f"tie_rule must be one of {TIE_RULES}, got {tie_rule!r}")
    if y is None or z_lo is None or z_hi is None:
        return None

    _counts["calls"] += 1
    if _equal(z_lo, z_hi):
        _counts["z_lo_vs_z_hi"] += 1

    if _equal(y, z_lo):
        _counts["y_vs_z_lo"] += 1
        from_lo = (2, 2)
    elif y < z_lo:
        from_lo = (1, 1)
    else:
        from_lo = (3, 5)

    if _equal(y, z_hi):
        _counts["y_vs_z_hi"] += 1
        from_hi = (4, 4)
    elif y > z_hi:
        from_hi = (5, 5)
    else:
        from_hi = (1, 3)

    both_lower = max(from_lo[0], from_hi[0])
    both_upper = min(from_lo[1], from_hi[1])
    if both_lower > both_upper:
        # Contradictory placements: tied or misordered anchors. Take the hull.
        both_lower = min(from_lo[0], from_hi[0])
        both_upper = max(from_lo[1], from_hi[1])

    return float(both_lower if tie_rule == "lower" else both_upper)
