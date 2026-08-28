"""Regression test for the vignettes' ground truth (DESIGN.md §7).

Protects the verification recorded as comments above VIGNETTE_LOW_CODE and
VIGNETTE_HIGH_CODE in pilot/tasks.py: LOW must fail VIGNETTE_HIDDEN_ASSERTS
(5 of 7 pass, 2 fail) and HIGH must pass (7 of 7). Previously checked only by
a one-off sandbox run; a future edit to either constant could otherwise
silently invert which vignette is "low" and which is "high".
"""

from pilot import sandbox, tasks


def test_vignette_low_fails_hidden_asserts():
    assert (
        sandbox.run_solution(tasks.VIGNETTE_LOW_CODE, list(tasks.VIGNETTE_HIDDEN_ASSERTS))
        is False
    )


def test_vignette_high_passes_hidden_asserts():
    assert (
        sandbox.run_solution(tasks.VIGNETTE_HIGH_CODE, list(tasks.VIGNETTE_HIDDEN_ASSERTS))
        is True
    )
