"""Control experiment: does scale coarseness explain the ceiling saturation?

The two real pilot runs (DEVLOG 2026-08-14 22:40 / 23:10) found the
condition-V self-rating `y` and the high anchor `z_hi` both pinned near 5.0 on
the locked 5-point scale (DESIGN.md §3), leaving almost no room for `C` to
vary. The obvious objection: a 5-point scale is too coarse to show gradation
near the ceiling. This script changes exactly one thing — the response scale
becomes 0-100 — to rule that objection in or out.

AUTHORISED DEVIATION from CLAUDE.md's locked "exactly 5 scale points, fixed
wording" decision, for this one diagnostic control only (see DEVLOG entry for
this session). DESIGN.md §3 and the 5-point pilot are untouched: this script
does not edit config.py, run_pilot.py or analyze.py, and does not import or
call any P1-P4 threshold logic — those thresholds are calibrated to a width-4
scale and are meaningless here.

Everything except the scale is identical to run_pilot.py: same 20 tasks (10
MBPP + 10 LBPP), same two models, same three questions (pronoun-only
difference), same two vignettes, same 5 samples at temperature 1.0, same
condition V / condition N / P4-probe turn structure, same random seed. This
is achieved by monkeypatching a handful of `pilot.config` attributes at
process start and then calling run_pilot.py's own (unmodified) functions —
`_run_observation`, `_dry_run`, `_planned_calls`, `_print_cost_summary` — so
the turn-sequencing logic that DEVLOG already validated cannot drift between
the two scripts.

Two deviations from the literal 5-point config, both confirmed with the user
before running (see DEVLOG):

- ANSWER_INSTRUCTION's original text says "a single digit", which would cap
  every reply at 0-9 and defeat the point of a 0-100 scale. Reworded to keep
  the same strict, no-prose intent while permitting the actual range.
- MAX_OUTPUT_TOKENS_RATING=8 was sized for a one-digit reply; raised to 16 as
  headroom for a up-to-three-digit reply. parse_rating is untouched and stays
  strict — this is not a parser relaxation.

Writes to separate files; the 5-point run's data is never opened for writing:
    pilot/out/raw_scale100.jsonl
    pilot/out/observations_scale100.jsonl
    pilot/out/report_scale100.md

Usage:
    python run_control_scale100.py --dry-run
    python run_control_scale100.py
"""

import argparse
import dataclasses
import json
import random
import statistics
import sys

import run_pilot as pilot_run
from pilot import config, elicit
from pilot.analyze import Observation

# --- Wide-scale overrides (see module docstring for the reasoning) ----------

SCALE_POINTS_WIDE = {0: "Very unlikely", 100: "Very likely"}

ANSWER_INSTRUCTION_WIDE = (
    "Reply with a single integer from 0 to 100 and nothing else — no words, "
    "no punctuation, no explanation."
)

MAX_OUTPUT_TOKENS_RATING_WIDE = 16

# TOLERANCE=0.01 (DESIGN.md §5) is calibrated to a width-4 scale (1-5). The
# proportional equivalent on a width-100 scale is 0.01 * 100/4 = 0.25.
TOLERANCE_WIDE = 0.25

RAW_JSONL_PATH_WIDE = config.OUT_DIR / "raw_scale100.jsonl"
OBSERVATIONS_PATH_WIDE = config.OUT_DIR / "observations_scale100.jsonl"
REPORT_PATH_WIDE = config.OUT_DIR / "report_scale100.md"

_MIN_POINT_WIDE = 0
_MAX_POINT_WIDE = 100


def _apply_overrides() -> None:
    """Patches `pilot.config` attributes in place.

    Every consumer (run_pilot.py, elicit.py) reads these off the `config`
    module object at call time, not at import time, so patching after import
    and before any call is sufficient — see module docstring.
    """
    config.SCALE_POINTS = SCALE_POINTS_WIDE
    config.ANSWER_INSTRUCTION = ANSWER_INSTRUCTION_WIDE
    config.MAX_OUTPUT_TOKENS_RATING = MAX_OUTPUT_TOKENS_RATING_WIDE
    config.RAW_JSONL_PATH = RAW_JSONL_PATH_WIDE


# --- Persistence (separate files; run_pilot._append_observation is NOT reused
# because it hardcodes "observations.jsonl") -------------------------------


def _append_observation(obs: Observation) -> None:
    config.OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OBSERVATIONS_PATH_WIDE, "a") as f:
        f.write(json.dumps(dataclasses.asdict(obs)) + "\n")


# --- Report: exactly what was asked for, nothing interpreted ---------------


def _valid_draws_wide(draws: list[int | None]) -> list[int]:
    return [d for d in draws if d is not None and _MIN_POINT_WIDE <= d <= _MAX_POINT_WIDE]


def _mean_wide(draws: list[int | None]) -> float | None:
    valid = _valid_draws_wide(draws)
    return sum(valid) / len(valid) if valid else None


def _sd(values: list[float]) -> float | None:
    return statistics.stdev(values) if len(values) >= 2 else None


def _group(observations: list[Observation]) -> dict[tuple[str, str], list[Observation]]:
    grouped: dict[tuple[str, str], list[Observation]] = {}
    for obs in observations:
        grouped.setdefault((obs.model, obs.task_set), []).append(obs)
    return grouped


def _parse_failure_rate(obs_list: list[Observation]) -> dict[str, object]:
    total = failures = off_scale = 0
    for obs in obs_list:
        for name in ("y_v_draws", "z_lo_draws", "z_hi_draws", "y_n_draws", "other_draws"):
            draws = getattr(obs, name)
            total += len(draws)
            failures += sum(1 for d in draws if d is None)
            off_scale += sum(
                1 for d in draws if d is not None and not _MIN_POINT_WIDE <= d <= _MAX_POINT_WIDE
            )
    return {
        "rating draws": total,
        "parse_failure_rate": failures / total if total else None,
        "off_scale_rate": off_scale / total if total else None,
    }


def render_report(observations: list[Observation]) -> str:
    lines = [
        "# Control experiment: 0-100 response scale",
        "",
        "Authorised diagnostic deviation from CLAUDE.md's locked 5-point scale "
        "(see DEVLOG). Not the main experiment; not a replacement for the "
        "5-point pilot. P1-P4 thresholds are NOT applied — they are calibrated "
        "to a width-4 scale and are meaningless here.",
        "",
        f"Scale: two labelled endpoints, {SCALE_POINTS_WIDE}. "
        f"ANSWER_INSTRUCTION: {ANSWER_INSTRUCTION_WIDE!r}. "
        f"MAX_OUTPUT_TOKENS_RATING: {MAX_OUTPUT_TOKENS_RATING_WIDE}. "
        f"Equality/near-ceiling tolerance: {TOLERANCE_WIDE} "
        "(proportional equivalent of the 5-point run's TOLERANCE=0.01 on a "
        "width-100 scale, i.e. 0.01 * 100/4).",
        "",
        f"{len(observations)} observations.",
        "",
    ]

    grouped = _group(observations)
    for (model, task_set), obs_list in sorted(grouped.items()):
        y_means = [m for m in (_mean_wide(o.y_v_draws) for o in obs_list) if m is not None]
        zlo_means = [m for m in (_mean_wide(o.z_lo_draws) for o in obs_list) if m is not None]
        zhi_means = [m for m in (_mean_wide(o.z_hi_draws) for o in obs_list) if m is not None]
        paired = [
            (yv, zh)
            for yv, zh in (
                (_mean_wide(o.y_v_draws), _mean_wide(o.z_hi_draws)) for o in obs_list
            )
            if yv is not None and zh is not None
        ]
        near_ceiling = sum(1 for yv, zh in paired if abs(yv - zh) <= TOLERANCE_WIDE)
        diag = _parse_failure_rate(obs_list)

        lines += [
            f"## {model} · {task_set}",
            "",
            f"n observations: {len(obs_list)}",
            f"n with usable y / z_lo / z_hi: {len(y_means)} / {len(zlo_means)} / {len(zhi_means)}",
            "",
            f"y distribution (per-observation mean of {config.N_SAMPLES} draws, sorted): "
            f"{sorted(y_means)}",
            f"z_lo distribution (sorted): {sorted(zlo_means)}",
            f"z_hi distribution (sorted): {sorted(zhi_means)}",
            "",
            f"distinct y values: {len(set(y_means))}",
            f"distinct z_lo values: {len(set(zlo_means))}",
            f"distinct z_hi values: {len(set(zhi_means))}",
            "",
        ]
        if y_means:
            lines.append(
                f"y: min={min(y_means):.3f} max={max(y_means):.3f} "
                f"mean={statistics.mean(y_means):.3f} "
                f"sd={_sd(y_means) if _sd(y_means) is not None else float('nan'):.3f}"
            )
        else:
            lines.append("y: no usable observations")
        lines.append(
            f"share |y - z_hi| <= {TOLERANCE_WIDE} (n={len(paired)}): "
            f"{near_ceiling / len(paired) if paired else float('nan'):.3f}"
        )
        lines += [
            "",
            f"rating draws: {diag['rating draws']}  "
            f"parse_failure_rate: {diag['parse_failure_rate']}  "
            f"off_scale_rate: {diag['off_scale_rate']}",
            "",
        ]

    return "\n".join(lines) + "\n"


def write_report(observations: list[Observation]) -> str:
    markdown = render_report(observations)
    config.OUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH_WIDE.write_text(markdown)
    return markdown


# --- Entry point -------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    _apply_overrides()

    task_list = pilot_run.tasks.load_tasks()

    if args.dry_run:
        pilot_run._dry_run(task_list)
        return 0

    planned = pilot_run._planned_calls(len(task_list))
    if planned > config.MAX_CALLS:
        print(
            f"Refusing to start: {planned} planned calls exceeds "
            f"config.MAX_CALLS ({config.MAX_CALLS}).",
            file=sys.stderr,
        )
        return 1

    print(
        f"Starting 0-100 scale control: {planned} planned calls, "
        f"MAX_CALLS={config.MAX_CALLS}. Writing to {RAW_JSONL_PATH_WIDE.name}, "
        f"{OBSERVATIONS_PATH_WIDE.name}, {REPORT_PATH_WIDE.name}."
    )
    rng = random.Random(config.PILOT_RANDOM_SEED)
    observations: list[Observation] = []

    try:
        for model in config.PILOT_MODELS:
            for task in task_list:
                obs = pilot_run._run_observation(model, task, rng)
                observations.append(obs)
                _append_observation(obs)
                print(f"  {model} task {task.task_id}: done")
    except elicit.CallBudgetExceeded as exc:
        print(f"\nAborted: {exc}", file=sys.stderr)
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)

    if observations:
        write_report(observations)
        print(f"\nWrote {REPORT_PATH_WIDE}")

    elicit.print_usage_summary()
    pilot_run._print_cost_summary()
    return 0


if __name__ == "__main__":
    sys.exit(main())
