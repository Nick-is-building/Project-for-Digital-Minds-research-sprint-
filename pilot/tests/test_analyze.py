"""Regression tests for `_orient`, the function that produced a false NO-GO.

`_orient` once returned `config.SCALE_POINTS_MAX + 1 - draw` for descending
observations, on the assumption that a randomised scale direction meant the
model was answering in a flipped frame. It does not: DESIGN.md §3 randomises the
order the scale lines are *printed* in and leaves the number-to-label mapping
fixed, so a reply of 5 means "Very likely" either way. Inverting half the data
turned 39/39 clean anchor orderings into 19 misorderings and failed P2 on the
first real run.

That function had no test at all. These are it. The load-bearing assertion is
`test_descending_is_not_inverted`: it fails for any implementation that
transforms the draw, which is the entire class of bug.
"""

import pytest

from pilot import config
from pilot.analyze import Observation, _mean, _orient, _valid_draws

INVERSION_REF = (
    "_orient must be the identity. DESIGN.md §3 randomises the printed order of "
    "the scale lines, not the number-to-label mapping, so there is no frame to "
    "convert between. Inverting descending draws produced a false NO-GO on P2 "
    "(DEVLOG 2026-08-14)."
)


def _observation(draws: list[int | None], direction: str, fmt=config.SCALE_P5):
    return Observation(
        model="test-model",
        task_id="t1",
        task_set="mbpp",
        scale_format=fmt.name,
        scale_direction=direction,
        low_vignette_first=True,
        y_v_draws=list(draws),
        z_lo_draws=[],
        z_hi_draws=[],
        y_n_draws=[],
        other_draws=[],
        passes_hidden=True,
        passes_visible=True,
        executes_cleanly=True,
        code_extracted=True,
    )


# --- The regression itself ---------------------------------------------------


@pytest.mark.parametrize("fmt", list(config.MAIN_SCALE_FORMATS))
def test_descending_is_not_inverted(fmt: config.ScaleFormat):
    """The draw is returned unchanged under descending, in every scale format."""
    for draw in (fmt.min_point, fmt.min_point + 1, fmt.max_point):
        assert _orient(draw, config.SCALE_DESCENDING) == draw, INVERSION_REF


@pytest.mark.parametrize("direction", list(config.SCALE_DIRECTIONS))
@pytest.mark.parametrize("draw", [1, 2, 3, 4, 5])
def test_orient_is_direction_independent(draw: int, direction: str):
    assert _orient(draw, direction) == _orient(draw, config.SCALE_ASCENDING)


def test_direction_does_not_change_the_mean():
    """The published symptom: identical draws must give an identical mean.

    The inversion bug was invisible at the level of a single draw and only showed
    up as anchor misordering, so the assertion is made on the aggregate that the
    P1-P4 criteria actually consume.
    """
    draws = [1, 2, 4, 5, 5]
    ascending = _mean(_observation(draws, config.SCALE_ASCENDING), "y_v_draws")
    descending = _mean(_observation(draws, config.SCALE_DESCENDING), "y_v_draws")
    assert ascending == descending == 3.4, INVERSION_REF


def test_anchor_ordering_survives_descending():
    """A cleanly ordered anchor pair stays ordered when the direction flips.

    This is the exact quantity the inversion broke: z_lo < z_hi became
    z_lo > z_hi for every descending observation, which is what P2 counts.
    """
    for direction in config.SCALE_DIRECTIONS:
        z_lo = _mean(_observation([2, 2, 2, 2, 2], direction), "y_v_draws")
        z_hi = _mean(_observation([4, 4, 4, 4, 4], direction), "y_v_draws")
        assert z_lo < z_hi, f"anchors misordered under {direction}. {INVERSION_REF}"


# --- Input contract ----------------------------------------------------------


def test_unknown_direction_raises():
    """An unrecognised direction is a bug upstream, not something to default."""
    with pytest.raises(ValueError):
        _orient(3, "randomised")


def test_out_of_range_draws_are_dropped_per_format():
    """Range bounds come from the observation's own format, not a global constant.

    6 is off-scale on p5 and on-scale on p7. Reading the bounds from a
    module-level constant is how the 0-100 control run came to be analysed
    against 5-point bounds.
    """
    on_p5 = _valid_draws(_observation([3, 6], config.SCALE_ASCENDING, config.SCALE_P5), "y_v_draws")
    on_p7 = _valid_draws(_observation([3, 6], config.SCALE_ASCENDING, config.SCALE_P7), "y_v_draws")
    assert on_p5 == [3]
    assert on_p7 == [3, 6]


def test_parse_failures_are_dropped_not_imputed():
    obs = _observation([None, 4, None], config.SCALE_ASCENDING)
    assert _valid_draws(obs, "y_v_draws") == [4]
    assert _mean(obs, "y_v_draws") == 4.0


def test_all_draws_unusable_gives_none_not_zero():
    obs = _observation([None, None], config.SCALE_ASCENDING)
    assert _mean(obs, "y_v_draws") is None
