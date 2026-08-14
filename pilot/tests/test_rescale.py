"""Checks on the King & Wand rescaling (DESIGN.md §5).

`test_invariance` is the reason this file exists. It encodes, as an executable
assertion, the mathematics that killed the project's first design: with vignette
ratings held constant across observations, `compute_C` is a monotone recoding of
the self-report and every rank-based statistic is invariant by construction, so
the pipeline is guaranteed to report exactly zero effect. See CLAUDE.md,
"THE ONE RULE THAT PROTECTS THE PROJECT". Never weaken, skip, or temporarily
disable it.
"""

import numpy as np
import pytest
from scipy.stats import spearmanr

from pilot import config
from pilot.rescale import compute_C, reset_tolerance_counts, tolerance_counts

RULE_REF = (
    "See CLAUDE.md, 'THE ONE RULE THAT PROTECTS THE PROJECT', and DESIGN.md §2. "
    "Vignette ratings MUST be elicited fresh in every task context; if they are "
    "constant, C is a monotone recoding of y and the result is a guaranteed null."
)

N_OBS = 500
SEED = 20260814

# y is a mean over config.N_SAMPLES draws, so the attainable values are the
# multiples of 1/N_SAMPLES between 1 and 5. Both the invariance support and the
# per-observation anchors below are drawn from that grid, never from arbitrary
# floats, so the test operates on values the pipeline can actually produce.
MEAN_GRID = np.round(np.arange(1.0, 5.0 + 1e-9, 1.0 / config.N_SAMPLES), 10)

# Five attainable y values and constant anchors sitting on two of them. This
# support is deliberately restricted: C has five categories, so a constant-anchor
# recoding is injective — and therefore exactly rank-preserving — only if y takes
# at most five distinct values. With a richer support, constant anchors coarsen y
# and move Spearman through pure information loss, which is a different (and
# weaker) statement than the invariance being asserted here. The support-free
# version of the same claim is test_constant_anchors_add_no_information.
Y_SUPPORT = (1.4, 2.2, 3.0, 3.8, 4.6)
Z_LO_CONST, Z_HI_CONST = 2.2, 3.8


def _sample_dataset(rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    """Self-reports plus a binary ground truth that genuinely tracks them."""
    y = rng.choice(Y_SUPPORT, size=N_OBS)
    p_correct = 0.1 + 0.8 * (y - min(Y_SUPPORT)) / (max(Y_SUPPORT) - min(Y_SUPPORT))
    truth = (rng.random(N_OBS) < p_correct).astype(int)
    return y, truth


# --- 1. The properly ordered ladder (DESIGN.md §5) ---------------------------


@pytest.mark.parametrize(
    ("y", "expected"),
    [(1.0, 1.0), (2.0, 2.0), (3.0, 3.0), (4.0, 4.0), (5.0, 5.0)],
)
@pytest.mark.parametrize("tie_rule", ["lower", "upper"])
def test_ordered_ladder(y: float, expected: float, tie_rule: str):
    assert compute_C(y, 2.0, 4.0, tie_rule) == expected


def test_tolerance_decides_the_equality_categories():
    """Just inside the tolerance is category 2; just outside it is category 3."""
    inside = 2.0 + config.TOLERANCE / 2
    outside = 2.0 + config.TOLERANCE * 2
    assert compute_C(inside, 2.0, 4.0, "lower") == 2.0
    assert compute_C(outside, 2.0, 4.0, "lower") == 3.0


# --- 2. Misordering is survivable -------------------------------------------


def test_misordering_does_not_raise():
    assert compute_C(3.0, 4.0, 2.0, "lower") is not None


def test_misordered_pair_straddling_y_is_uninformative():
    assert compute_C(3.0, 4.0, 2.0, "lower") == 1.0
    assert compute_C(3.0, 4.0, 2.0, "upper") == 5.0


def test_misordered_pair_below_y_is_still_point_identified():
    """An ordering violation does not always destroy identification."""
    assert compute_C(5.0, 4.0, 2.0, "lower") == compute_C(5.0, 4.0, 2.0, "upper")
    assert compute_C(5.0, 4.0, 2.0, "lower") == 5.0


# --- 3. Tied anchors are interval-identified --------------------------------


def test_tie_bounds_differ():
    lower = compute_C(3.0, 3.0, 3.0, "lower")
    upper = compute_C(3.0, 3.0, 3.0, "upper")
    assert lower != upper, (
        "Tied anchors leave C interval-identified; the two bounds must differ, "
        "otherwise the DESIGN.md §5 robustness check across bound choices is "
        "vacuous."
    )
    assert (lower, upper) == (2.0, 4.0)


# --- 4. THE INVARIANCE TEST -------------------------------------------------


def test_invariance():
    """Constant anchors change no rank statistic; per-context anchors do.

    First assertion: the invariance is real, so no implementation of compute_C
    can rescue a pipeline that reuses vignette ratings. Second assertion:
    eliciting the anchors per observation genuinely changes the statistic, so
    the pipeline's per-context elicitation is doing real work.
    """
    rng = np.random.default_rng(SEED)
    y, truth = _sample_dataset(rng)

    c_constant = [compute_C(v, Z_LO_CONST, Z_HI_CONST, "lower") for v in y]
    c_per_context = [
        compute_C(v, rng.choice(MEAN_GRID), rng.choice(MEAN_GRID), "lower") for v in y
    ]

    rho_raw = spearmanr(y, truth).statistic
    rho_constant = spearmanr(c_constant, truth).statistic
    rho_per_context = spearmanr(c_per_context, truth).statistic

    assert rho_constant == pytest.approx(rho_raw, abs=1e-6), (
        f"Spearman moved under constant vignette ratings: raw {rho_raw:.6f} vs "
        f"rescaled {rho_constant:.6f}. Either compute_C is no longer a monotone "
        f"recoding of y, or this test's assumptions drifted. {RULE_REF}"
    )
    assert abs(rho_per_context - rho_constant) > 0.01, (
        f"Per-observation vignette ratings changed nothing: constant "
        f"{rho_constant:.6f} vs per-context {rho_per_context:.6f}. The anchors "
        f"are not entering the computation, so the correction is inert. "
        f"{RULE_REF}"
    )


def test_constant_anchors_add_no_information():
    """The support-free form of the invariance: C is then a function of y alone.

    Holds for any y, unlike test_invariance's exact rank equality, which needs a
    support small enough for the five-category recoding to stay injective.
    """
    rng = np.random.default_rng(SEED)
    y = rng.choice(MEAN_GRID, size=N_OBS)

    by_y: dict[float, set[float | None]] = {}
    for value in y:
        by_y.setdefault(float(value), set()).add(
            compute_C(value, Z_LO_CONST, Z_HI_CONST, "lower")
        )

    collisions = {k: v for k, v in by_y.items() if len(v) > 1}
    assert not collisions, (
        f"C varied for identical y under constant anchors: {collisions}. That is "
        f"impossible if C depends only on (y, z_lo, z_hi). {RULE_REF}"
    )
    assert len(by_y) > len({next(iter(v)) for v in by_y.values()}), (
        "Constant anchors did not coarsen a continuous y, so this test is no "
        "longer exercising the mechanism it was written for."
    )


# --- Diagnostics and input contract ----------------------------------------


def test_tolerance_firing_is_counted():
    reset_tolerance_counts()
    compute_C(2.0, 2.0, 4.0, "lower")  # y ties z_lo
    compute_C(4.0, 2.0, 4.0, "lower")  # y ties z_hi
    compute_C(3.0, 3.0, 3.0, "lower")  # anchors tied, y ties both
    compute_C(1.0, 2.0, 4.0, "lower")  # nothing ties

    counts = tolerance_counts()
    assert (counts.calls, counts.y_vs_z_lo, counts.y_vs_z_hi, counts.z_lo_vs_z_hi) == (
        4,
        2,
        2,
        1,
    )


@pytest.mark.parametrize(
    ("y", "z_lo", "z_hi"),
    [(None, 2.0, 4.0), (3.0, None, 4.0), (3.0, 2.0, None)],
)
def test_parse_failure_propagates_as_none(y, z_lo, z_hi):
    assert compute_C(y, z_lo, z_hi, "lower") is None


def test_unknown_tie_rule_raises():
    with pytest.raises(ValueError):
        compute_C(3.0, 2.0, 4.0, "midpoint")
