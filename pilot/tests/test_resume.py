"""Checks that an interrupted run can be resumed without corrupting the design.

Resumability is not only about saving money. Two of these tests defend the
within-subject design itself:

`test_context_draw_is_identical_across_formats` — the three scale formats of a
(model, task) pair must share one presentation, or a format comparison is also a
direction comparison.

`test_skipping_does_not_shift_later_draws` — the pilot drew from one sequential
generator walked in loop order, so a resumed run that skipped finished work would
have drawn different directions for everything after the skip. Keyed seeding is
what makes a resumed run indistinguishable from an uninterrupted one.
"""

import json

import pytest

import run_main
from pilot import config, resume
from pilot.analyze import Observation

DESIGN_REF = (
    "DESIGN.md §10 requires one solution and one presentation per (model, task), "
    "reused across all three scale formats, so that a format difference cannot be "
    "a solution or presentation difference."
)


def _observation(model="m1", task_id="t1", scale_format="p5") -> Observation:
    return Observation(
        model=model,
        task_id=task_id,
        task_set="mbpp",
        scale_format=scale_format,
        scale_direction=config.SCALE_ASCENDING,
        low_vignette_first=True,
        y_v_draws=[4, 4, 5, 4, 5],
        z_lo_draws=[2, 2, 2, 2, 2],
        z_hi_draws=[4, 4, 4, 4, 4],
        y_n_draws=[5, 5, 5, 5, 5],
        other_draws=[3, 3, 3, 3, 3],
        passes_hidden=True,
        passes_visible=True,
        executes_cleanly=True,
        code_extracted=True,
    )


def _solution(model="m1", task_id="t1") -> resume.SolutionRecord:
    return resume.SolutionRecord(
        model=model,
        task_id=task_id,
        solution="def f(x):\n    return x\n",
        failure_reason=None,
        passes_hidden=True,
        passes_visible=False,
        executes_cleanly=True,
    )


# --- Observation round-trip and keying ---------------------------------------


def test_missing_file_is_empty_not_an_error():
    """A first run has no output file; that is the normal case, not a failure."""
    missing = config.OUT_DIR / "does_not_exist_test.jsonl"
    assert resume.completed_observation_keys(missing) == set()
    assert resume.load_solutions(missing) == {}


def test_observation_round_trips(tmp_path):
    path = tmp_path / "observations.jsonl"
    import run_pilot

    original = _observation()
    run_pilot.append_observation(original, path)
    assert resume.load_observations(path) == [original]


def test_observation_key_includes_the_scale_format():
    """Same (model, task) in two formats are two separate pieces of work."""
    p5 = resume.observation_key(_observation(scale_format="p5"))
    p7 = resume.observation_key(_observation(scale_format="p7"))
    assert p5 != p7, (
        "Keying observations without the scale format would make the first "
        "completed format suppress the other two on resume."
    )


def test_completed_keys_are_what_the_runner_skips(tmp_path):
    import run_pilot

    path = tmp_path / "observations.jsonl"
    for fmt_name in ("p5", "p7"):
        run_pilot.append_observation(_observation(scale_format=fmt_name), path)

    done = resume.completed_observation_keys(path)
    assert ("m1", "t1", "p5") in done
    assert ("m1", "t1", "s100") not in done


# --- Solution persistence ---------------------------------------------------


def test_solution_round_trips_with_its_ground_truth(tmp_path):
    """Ground truth travels with the solution rather than being recomputed.

    `passes_visible=False` here is deliberately inconsistent with
    `passes_hidden=True`: it can only survive the round trip if the stored values
    are read back, not re-derived.
    """
    path = tmp_path / "solutions.jsonl"
    original = _solution()
    resume.append_solution(original, path)

    loaded = resume.load_solutions(path)
    assert loaded == {("m1", "t1"): original}
    assert loaded[("m1", "t1")].passes_hidden is True
    assert loaded[("m1", "t1")].passes_visible is False


def test_solution_key_omits_the_scale_format(tmp_path):
    """One solution serves all three formats, so its key must not mention them."""
    assert _solution().key == ("m1", "t1"), DESIGN_REF


def test_last_write_wins_on_a_duplicated_solution(tmp_path):
    path = tmp_path / "solutions.jsonl"
    resume.append_solution(_solution(), path)
    resume.append_solution(
        resume.SolutionRecord(
            model="m1",
            task_id="t1",
            solution="def f(x):\n    return x + 1\n",
            failure_reason=None,
            passes_hidden=False,
            passes_visible=False,
            executes_cleanly=True,
        ),
        path,
    )
    assert len(resume.load_solutions(path)) == 1
    assert resume.load_solutions(path)[("m1", "t1")].passes_hidden is False


def test_a_failed_solution_is_recorded_so_it_is_not_retried(tmp_path):
    path = tmp_path / "solutions.jsonl"
    record = resume.SolutionRecord(
        model="m1",
        task_id="t1",
        solution=None,
        failure_reason="unclosed_code_fence",
        passes_hidden=False,
        passes_visible=False,
        executes_cleanly=False,
    )
    resume.append_solution(record, path)
    assert resume.load_solutions(path)[("m1", "t1")].solution is None


# --- Truncated final line ---------------------------------------------------


def test_truncated_final_line_is_forgiven(tmp_path):
    """A process killed mid-write leaves a partial last line; redo that work."""
    path = tmp_path / "solutions.jsonl"
    resume.append_solution(_solution(task_id="t1"), path)
    with open(path, "a") as f:
        f.write('{"model": "m1", "task_id": "t2", "solu')

    loaded = resume.load_solutions(path)
    assert set(loaded) == {("m1", "t1")}


def test_corruption_earlier_in_the_file_raises(tmp_path):
    """Silently dropping a mid-file line would hide real data loss."""
    path = tmp_path / "solutions.jsonl"
    resume.append_solution(_solution(task_id="t1"), path)
    with open(path, "a") as f:
        f.write("{not json}\n")
    resume.append_solution(_solution(task_id="t3"), path)

    with pytest.raises(json.JSONDecodeError):
        resume.load_solutions(path)


def test_blank_lines_are_ignored(tmp_path):
    path = tmp_path / "solutions.jsonl"
    resume.append_solution(_solution(), path)
    with open(path, "a") as f:
        f.write("\n\n")
    assert len(resume.load_solutions(path)) == 1


# --- Keyed randomisation (run_main.py) --------------------------------------


def test_context_draw_is_deterministic():
    assert run_main.context_for("m1", "t1") == run_main.context_for("m1", "t1")


def test_context_draw_is_identical_across_formats():
    """There is nothing format-dependent in the draw — that is the guarantee.

    Stated as a test because the alternative (drawing inside the format loop) is
    the obvious way to write the runner and silently breaks the pairing.
    """
    draws = {
        fmt.name: run_main.context_for("m1", "t1") for fmt in config.MAIN_SCALE_FORMATS
    }
    assert len(set(draws.values())) == 1, DESIGN_REF


def test_skipping_does_not_shift_later_draws():
    """A resumed run draws exactly what an uninterrupted one would have drawn.

    Simulates the interruption directly: walk every cell, then walk only the
    cells a resumed run would still have to do, and require the draws to agree.
    """
    cells = [(m, f"t{i}") for m in ("m1", "m2") for i in range(10)]
    full = {cell: run_main.context_for(*cell) for cell in cells}

    resumed = {cell: run_main.context_for(*cell) for cell in cells[7:]}
    for cell, drawn in resumed.items():
        assert drawn == full[cell], (
            "The draw for a cell changed depending on how much work preceded it. "
            "A resumed run would then use a different presentation than the "
            "interrupted one, and the two halves of the data would not be "
            "comparable."
        )


def test_context_draw_varies_across_cells():
    """Keyed seeding must still randomise, not return one constant."""
    draws = {run_main.context_for("m1", f"t{i}") for i in range(40)}
    assert len(draws) > 1, (
        "Every cell drew the same presentation, so scale direction and vignette "
        "order are no longer randomised (DESIGN.md §3, §4)."
    )


def test_both_directions_and_both_orders_occur():
    draws = [run_main.context_for("m1", f"t{i}") for i in range(60)]
    assert set(d[0] for d in draws) == set(config.SCALE_DIRECTIONS)
    assert set(d[1] for d in draws) == {True, False}


# --- Remaining-work accounting ----------------------------------------------


def test_remaining_calls_is_the_full_budget_when_nothing_is_done():
    task_list = [_FakeTask("t1"), _FakeTask("t2")]
    assert run_main.remaining_calls(task_list, set(), {}) == run_main.planned_calls(
        len(task_list)
    )


def test_a_finished_format_removes_exactly_its_own_calls():
    task_list = [_FakeTask("t1")]
    model = config.MAIN_MODELS[0]
    done = {(model, "t1", config.MAIN_SCALE_FORMATS[0].name)}
    solutions = {(model, "t1"): _solution(model=model)}

    full = run_main.remaining_calls(task_list, set(), {})
    after = run_main.remaining_calls(task_list, done, solutions)
    # One rating block skipped, plus the code-generation call already spent.
    assert full - after == run_main.calls_per_format() + 1


def test_a_fully_finished_task_costs_nothing_to_resume():
    task_list = [_FakeTask("t1")]
    done = {
        (model, "t1", fmt.name)
        for model in config.MAIN_MODELS
        for fmt in config.MAIN_SCALE_FORMATS
    }
    assert run_main.remaining_calls(task_list, done, {}) == 0


class _FakeTask:
    """Just the `task_id` the accounting reads; loading real tasks hits the network."""

    def __init__(self, task_id: str):
        self.task_id = task_id
