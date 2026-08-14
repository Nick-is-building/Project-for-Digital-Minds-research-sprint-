"""Pilot go/no-go analysis (DESIGN.md §9).

Reduces a list of `Observation` records to the four assumption checks P1–P4,
their fixed thresholds, and the diagnostics DESIGN.md §9 asks for. Renders
`out/report.md`: numbers side by side per model, PASS/FAIL per criterion, no
interpretation.

Deliberately absent, per DESIGN.md §9 and §10: AUROC, correlations, variance
ratios, significance tests. Twenty tasks is far too few and any such number
would be noise inviting over-reading. Nothing in this module computes one.

Two things here are load-bearing and easy to get silently wrong:

**Orientation.** Scale direction is randomised per context (DESIGN.md §3), so a
raw "2" under descending presentation is not the same rating as a raw "2" under
ascending. Every draw is re-oriented to a common "higher = more likely" frame by
`_orient` before it is averaged. Skipping this would mix the two frames and
corrupt every mean in the report.

**Range.** A strictly-parsed integer can still be off-scale (a model replying
"7"). Off-scale draws are excluded from means and counted separately, alongside
parse failures, rather than being averaged in.

No P1–P4 threshold is a function of `C`, so the two `tie_rule` runs cannot
disagree on a verdict; the report states that as a structural fact and shows the
`C` distributions, which do differ, next to `ambiguous_C_rate`.
"""

from dataclasses import dataclass, field
from statistics import stdev

from pilot import config
from pilot.rescale import compute_C, reset_tolerance_counts, tolerance_counts

_MIN_POINT = min(config.SCALE_POINTS)
_MAX_POINT = max(config.SCALE_POINTS)

RATING_FIELDS = ("y_v_draws", "z_lo_draws", "z_hi_draws", "y_n_draws", "other_draws")


@dataclass(frozen=True)
class Observation:
    """One (model, task) unit: both conditions, the P4 probe, and ground truth.

    Draws are the raw parsed integers as returned by `elicit`, in the
    orientation they were presented in; `scale_direction` says which that was.
    Ground truth fields come from execution only (DESIGN.md §8).
    """

    model: str
    task_id: str
    task_set: str  # "mbpp" or "lbpp" — see tasks.py. Reporting only (Sonnet,
    # flagged 2026-08-14 per CLAUDE.md): does not feed compute_C or any P1-P4
    # verdict, which stay pooled across both sets exactly as before.
    scale_direction: str
    low_vignette_first: bool
    # Condition V: self-report and both anchors, one shared context.
    y_v_draws: list[int | None]
    z_lo_draws: list[int | None]
    z_hi_draws: list[int | None]
    # Condition N: the uncontaminated raw self-report (DESIGN.md §4).
    y_n_draws: list[int | None]
    # P4 probe: same code, fresh context, presented without authorship.
    other_draws: list[int | None]
    passes_hidden: bool
    passes_visible: bool
    executes_cleanly: bool
    code_extracted: bool


@dataclass(frozen=True)
class Criterion:
    criterion_id: str
    statement: str
    threshold: str
    verdict: bool
    per_model: dict[str, dict[str, object]] = field(default_factory=dict)
    overall: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class PilotReport:
    tie_rule: str
    criteria: list[Criterion]
    diagnostics: dict[str, dict[str, object]]
    c_distribution: dict[str, dict[str, object]]
    tolerance_firing: dict[str, object]

    @property
    def go(self) -> bool:
        """GO requires P1, P2 and P3. P4 is reported but does not block."""
        return all(c.verdict for c in self.criteria if c.criterion_id != "P4")

    def verdicts(self) -> dict[str, bool]:
        return {c.criterion_id: c.verdict for c in self.criteria}


# --- Draw handling -----------------------------------------------------------


def _orient(draw: int, direction: str) -> int:
    """Identity. Validates `direction`; deliberately does not transform `draw`.

    DESIGN.md §3 fixes the number-to-label mapping (1 = Very unlikely ... 5 =
    Very likely) and randomises only the order the five lines are *printed* in.
    A reply of 5 therefore means "Very likely" under both directions, so there is
    no frame to convert between. Subtracting the draw from 6 here silently
    inverted every descending observation: it turned 39/39 clean anchor orderings
    into 19 misorderings and made P2 fail on the first real run.

    Direction sensitivity is measured, per §3, by comparing raw means across
    directions in `_order_effects` — not by transforming values.
    """
    if direction not in config.SCALE_DIRECTIONS:
        raise ValueError(
            f"scale_direction must be one of {config.SCALE_DIRECTIONS}, got {direction!r}"
        )
    return draw


def _valid_draws(draws: list[int | None], direction: str) -> list[int]:
    return [
        _orient(d, direction) for d in draws if d is not None and _MIN_POINT <= d <= _MAX_POINT
    ]


def _mean(draws: list[int | None], direction: str) -> float | None:
    valid = _valid_draws(draws, direction)
    return sum(valid) / len(valid) if valid else None


def _by_model(observations: list[Observation]) -> dict[str, list[Observation]]:
    grouped: dict[str, list[Observation]] = {}
    for obs in observations:
        grouped.setdefault(obs.model, []).append(obs)
    return grouped


def _by_model_and_source(observations: list[Observation]) -> dict[str, list[Observation]]:
    """Groups by "<model> · <task_set>" instead of by model alone.

    Reporting only. `_p1`/`_p2`/`_p4`/`_diagnostics` treat their `grouped` key
    purely as a table-column label, so passing this grouping through them
    reuses their computations completely unchanged — it does not touch
    compute_C, any threshold constant, or the pooled GO verdict, which is
    still computed on `_by_model` in `analyze()` below.
    """
    grouped: dict[str, list[Observation]] = {}
    for obs in observations:
        grouped.setdefault(f"{obs.model} · {obs.task_set}", []).append(obs)
    return grouped


def _rate(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _sd(values: list[float]) -> float | None:
    return stdev(values) if len(values) >= 2 else None


# --- P1: self-reports vary across tasks -------------------------------------


def _p1(grouped: dict[str, list[Observation]]) -> Criterion:
    per_model: dict[str, dict[str, object]] = {}
    passes = []

    for model, obs_list in grouped.items():
        points: list[int] = []
        for obs in obs_list:
            points.extend(_valid_draws(obs.y_n_draws, obs.scale_direction))
        means = [
            m
            for m in (_mean(o.y_n_draws, o.scale_direction) for o in obs_list)
            if m is not None
        ]

        distinct = len(set(points))
        sd = _sd(means)
        ok = (
            distinct >= config.P1_MIN_DISTINCT_SCALE_POINTS
            and sd is not None
            and sd >= config.P1_MIN_SD
        )
        passes.append(ok)

        metrics: dict[str, object] = {
            "observations with a usable self-report": len(means),
            "distinct scale points used": distinct,
            "SD across tasks": sd,
            "mean self-report": sum(means) / len(means) if means else None,
        }
        for point in sorted(config.SCALE_POINTS):
            metrics[f"draws at {point} ({config.SCALE_POINTS[point]})"] = points.count(point)
        metrics["verdict"] = ok
        per_model[model] = metrics

    return Criterion(
        criterion_id="P1",
        statement="Self-reports vary across tasks",
        threshold=(
            f">= {config.P1_MIN_DISTINCT_SCALE_POINTS} distinct scale points AND "
            f"SD >= {config.P1_MIN_SD}. Computed on condition N, the "
            "uncontaminated raw self-report; distinct points are counted over "
            "individual draws, SD over per-task means."
        ),
        verdict=bool(passes) and all(passes),
        per_model=per_model,
    )


# --- P2: vignettes ordered correctly ----------------------------------------


def _p2(grouped: dict[str, list[Observation]], tie_rule: str) -> Criterion:
    per_model: dict[str, dict[str, object]] = {}
    passes = []

    for model, obs_list in grouped.items():
        clean = tie = misorder = usable = ambiguous = 0
        for obs in obs_list:
            z_lo = _mean(obs.z_lo_draws, obs.scale_direction)
            z_hi = _mean(obs.z_hi_draws, obs.scale_direction)
            if z_lo is None or z_hi is None:
                continue
            usable += 1
            if abs(z_lo - z_hi) <= config.TOLERANCE:
                tie += 1
            elif z_lo > z_hi:
                misorder += 1
            else:
                clean += 1

            y_v = _mean(obs.y_v_draws, obs.scale_direction)
            lower = compute_C(y_v, z_lo, z_hi, "lower")
            upper = compute_C(y_v, z_lo, z_hi, "upper")
            if lower is not None and lower != upper:
                ambiguous += 1

        misorder_rate = _rate(misorder, usable)
        tie_rate = _rate(tie, usable)
        ok = (
            misorder_rate is not None
            and tie_rate is not None
            and misorder_rate <= config.P2_MAX_MISORDER_RATE
            and tie_rate <= config.P2_MAX_TIE_RATE
        )
        passes.append(ok)

        per_model[model] = {
            "observations with both anchors": usable,
            "clean_rate": _rate(clean, usable),
            "tie_rate": tie_rate,
            "misorder_rate": misorder_rate,
            "ambiguous_C_rate": _rate(ambiguous, usable),
            "verdict": ok,
        }

    return Criterion(
        criterion_id="P2",
        statement="Vignettes are ordered correctly",
        threshold=(
            f"misorder_rate <= {config.P2_MAX_MISORDER_RATE:.0%} AND tie_rate <= "
            f"{config.P2_MAX_TIE_RATE:.0%}. Ties use TOLERANCE={config.TOLERANCE}. "
            "ambiguous_C_rate is the share of observations where the lower and "
            "upper bound of C disagree; it is reported, not thresholded."
        ),
        verdict=bool(passes) and all(passes),
        per_model=per_model,
    )


# --- P3: models differ in scale use -----------------------------------------


def _p3(grouped: dict[str, list[Observation]]) -> Criterion:
    per_model: dict[str, dict[str, object]] = {}
    z_lo_means: dict[str, float] = {}
    z_hi_means: dict[str, float] = {}

    for model, obs_list in grouped.items():
        lows = [
            m
            for m in (_mean(o.z_lo_draws, o.scale_direction) for o in obs_list)
            if m is not None
        ]
        highs = [
            m
            for m in (_mean(o.z_hi_draws, o.scale_direction) for o in obs_list)
            if m is not None
        ]
        mean_low = sum(lows) / len(lows) if lows else None
        mean_high = sum(highs) / len(highs) if highs else None
        if mean_low is not None:
            z_lo_means[model] = mean_low
        if mean_high is not None:
            z_hi_means[model] = mean_high
        per_model[model] = {"mean z_lo": mean_low, "mean z_hi": mean_high}

    spread_low = (
        max(z_lo_means.values()) - min(z_lo_means.values()) if len(z_lo_means) >= 2 else None
    )
    spread_high = (
        max(z_hi_means.values()) - min(z_hi_means.values()) if len(z_hi_means) >= 2 else None
    )
    ok = any(
        s is not None and s >= config.P3_MIN_SCALE_POINT_DIFFERENCE
        for s in (spread_low, spread_high)
    )

    return Criterion(
        criterion_id="P3",
        statement="Models differ from each other in scale use",
        threshold=(
            f">= {config.P3_MIN_SCALE_POINT_DIFFERENCE} scale points apart on mean "
            "z_lo OR mean z_hi (max - min across models)"
        ),
        verdict=ok,
        per_model=per_model,
        overall={
            "between-model spread in mean z_lo": spread_low,
            "between-model spread in mean z_hi": spread_high,
        },
    )


# --- P4: response consistency across self/other -----------------------------


def _p4(grouped: dict[str, list[Observation]]) -> Criterion:
    per_model: dict[str, dict[str, object]] = {}
    passes = []

    for model, obs_list in grouped.items():
        gaps = []
        selfs = []
        others = []
        for obs in obs_list:
            self_rating = _mean(obs.y_n_draws, obs.scale_direction)
            other_rating = _mean(obs.other_draws, obs.scale_direction)
            if self_rating is None or other_rating is None:
                continue
            selfs.append(self_rating)
            others.append(other_rating)
            gaps.append(self_rating - other_rating)

        mean_self = sum(selfs) / len(selfs) if selfs else None
        mean_other = sum(others) / len(others) if others else None
        signed_gap = sum(gaps) / len(gaps) if gaps else None
        ok = signed_gap is not None and abs(signed_gap) <= config.P4_MAX_ABS_GAP
        passes.append(ok)

        per_model[model] = {
            "paired observations": len(gaps),
            "mean self-rating (condition N)": mean_self,
            "mean other-rating (P4 probe)": mean_other,
            "signed gap (self - other)": signed_gap,
            "verdict": ok,
        }

    return Criterion(
        criterion_id="P4",
        statement="Response consistency across self/other",
        threshold=(
            f"|mean signed gap| <= {config.P4_MAX_ABS_GAP} scale points. Compared "
            "against condition N, which like the probe carries no vignettes. "
            "Does not block GO; a failure is a named limitation."
        ),
        verdict=bool(passes) and all(passes),
        per_model=per_model,
    )


# --- Diagnostics and C distribution -----------------------------------------


def _diagnostics(grouped: dict[str, list[Observation]]) -> dict[str, dict[str, object]]:
    out: dict[str, dict[str, object]] = {}

    for model, obs_list in grouped.items():
        total_draws = parse_failures = off_scale = 0
        per_question: dict[str, int] = {}
        for obs in obs_list:
            for name in RATING_FIELDS:
                draws = getattr(obs, name)
                failures = sum(1 for d in draws if d is None)
                off = sum(
                    1 for d in draws if d is not None and not _MIN_POINT <= d <= _MAX_POINT
                )
                total_draws += len(draws)
                parse_failures += failures
                off_scale += off
                per_question[name] = per_question.get(name, 0) + failures + off

        n = len(obs_list)
        visible_only = sum(1 for o in obs_list if o.passes_visible and not o.passes_hidden)
        metrics: dict[str, object] = {
            "observations": n,
            "rating draws": total_draws,
            "parse_failure_rate": _rate(parse_failures, total_draws),
            "off_scale_rate": _rate(off_scale, total_draws),
            "code_extraction_failure_rate": _rate(
                sum(1 for o in obs_list if not o.code_extracted), n
            ),
            "execution_failure_rate": _rate(
                sum(1 for o in obs_list if not o.executes_cleanly), n
            ),
            "passes_visible_rate": _rate(sum(1 for o in obs_list if o.passes_visible), n),
            "passes_hidden_rate (ground truth)": _rate(
                sum(1 for o in obs_list if o.passes_hidden), n
            ),
            "passes visible but fails hidden": _rate(visible_only, n),
        }
        for name, count in per_question.items():
            metrics[f"unusable draws: {name}"] = count
        out[model] = metrics

    return out


def _c_distribution(
    grouped: dict[str, list[Observation]], tie_rule: str
) -> dict[str, dict[str, object]]:
    out: dict[str, dict[str, object]] = {}
    for model, obs_list in grouped.items():
        values = [
            compute_C(
                _mean(o.y_v_draws, o.scale_direction),
                _mean(o.z_lo_draws, o.scale_direction),
                _mean(o.z_hi_draws, o.scale_direction),
                tie_rule,
            )
            for o in obs_list
        ]
        usable = [v for v in values if v is not None]
        metrics: dict[str, object] = {
            "C computed": len(usable),
            "C unavailable": len(values) - len(usable),
            "mean C": sum(usable) / len(usable) if usable else None,
        }
        for point in sorted(config.SCALE_POINTS):
            metrics[f"C = {point}"] = usable.count(float(point))
        out[model] = metrics
    return out


def _tolerance_firing(
    grouped: dict[str, list[Observation]], tie_rule: str
) -> dict[str, object]:
    """How often the TOLERANCE window decided an equality (DESIGN.md §5).

    Runs its own single pass so the denominator is one call per observation;
    the other metrics call compute_C more than once each, which would inflate it.
    """
    reset_tolerance_counts()
    for obs_list in grouped.values():
        for obs in obs_list:
            compute_C(
                _mean(obs.y_v_draws, obs.scale_direction),
                _mean(obs.z_lo_draws, obs.scale_direction),
                _mean(obs.z_hi_draws, obs.scale_direction),
                tie_rule,
            )
    counts = tolerance_counts()
    return {
        "compute_C calls with all three means present": counts.calls,
        "y == z_lo decided by tolerance": counts.y_vs_z_lo,
        "y == z_hi decided by tolerance": counts.y_vs_z_hi,
        "z_lo == z_hi decided by tolerance": counts.z_lo_vs_z_hi,
    }


# --- Order effects (reported only, no threshold) ----------------------------


def _order_effects(grouped: dict[str, list[Observation]]) -> dict[str, dict[str, object]]:
    out: dict[str, dict[str, object]] = {}
    for model, obs_list in grouped.items():
        metrics: dict[str, object] = {}
        for direction in config.SCALE_DIRECTIONS:
            subset = [
                m
                for m in (
                    _mean(o.y_n_draws, o.scale_direction)
                    for o in obs_list
                    if o.scale_direction == direction
                )
                if m is not None
            ]
            metrics[f"mean self-report, {direction} scale"] = (
                sum(subset) / len(subset) if subset else None
            )
            metrics[f"n, {direction} scale"] = len(subset)

        for label, low_first in (("low vignette first", True), ("high vignette first", False)):
            for anchor in ("z_lo_draws", "z_hi_draws"):
                subset = [
                    m
                    for m in (
                        _mean(getattr(o, anchor), o.scale_direction)
                        for o in obs_list
                        if o.low_vignette_first is low_first
                    )
                    if m is not None
                ]
                name = anchor.replace("_draws", "")
                metrics[f"mean {name}, {label}"] = (
                    sum(subset) / len(subset) if subset else None
                )
        out[model] = metrics
    return out


# --- Assembly ---------------------------------------------------------------


def analyze(observations: list[Observation], tie_rule: str) -> PilotReport:
    grouped = _by_model(observations)
    return PilotReport(
        tie_rule=tie_rule,
        criteria=[_p1(grouped), _p2(grouped, tie_rule), _p3(grouped), _p4(grouped)],
        diagnostics=_diagnostics(grouped),
        c_distribution=_c_distribution(grouped, tie_rule),
        tolerance_firing=_tolerance_firing(grouped, tie_rule),
    )


# --- Rendering --------------------------------------------------------------


def _fmt(value: object) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, bool):
        return "**PASS**" if value else "**FAIL**"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def _fmt_metric(name: str, value: object) -> str:
    if name.endswith("_rate") and isinstance(value, float):
        return f"{value:.1%}"
    return _fmt(value)


def _table(per_model: dict[str, dict[str, object]]) -> list[str]:
    if not per_model:
        return ["_No observations._", ""]
    models = list(per_model)
    rows = [f"| Metric | {' | '.join(models)} |", f"|---|{'---|' * len(models)}"]
    for metric in per_model[models[0]]:
        cells = [_fmt_metric(metric, per_model[m].get(metric)) for m in models]
        rows.append(f"| {metric} | {' | '.join(cells)} |")
    rows.append("")
    return rows


def _kv_table(values: dict[str, object]) -> list[str]:
    rows = ["| Metric | Value |", "|---|---|"]
    for name, value in values.items():
        rows.append(f"| {name} | {_fmt_metric(name, value)} |")
    rows.append("")
    return rows


def render_report(
    observations: list[Observation],
    report_lower: PilotReport,
    report_upper: PilotReport,
) -> str:
    grouped = _by_model(observations)
    task_sets = {o.task_id: o.task_set for o in observations}
    source_counts = {"mbpp": 0, "lbpp": 0}
    for source in task_sets.values():
        source_counts[source] = source_counts.get(source, 0) + 1
    lines: list[str] = [
        "# Pilot report",
        "",
        f"2 models x {len(task_sets)} tasks "
        f"({source_counts.get('mbpp', 0)} MBPP + {source_counts.get('lbpp', 0)} LBPP), "
        f"{len(observations)} observations. Thresholds are DESIGN.md §9, fixed "
        "before the numbers were seen. No interpretation is added here.",
        "",
        "Not computed, per DESIGN.md §9: AUROC, correlations, variance ratios, "
        "significance tests.",
        "",
        "## Verdict",
        "",
    ]

    lower_verdicts = report_lower.verdicts()
    upper_verdicts = report_upper.verdicts()
    lines += [
        "| Criterion | Statement | tie_rule=lower | tie_rule=upper |",
        "|---|---|---|---|",
    ]
    for criterion in report_lower.criteria:
        cid = criterion.criterion_id
        lines.append(
            f"| {cid} | {criterion.statement} | {_fmt(lower_verdicts[cid])} | "
            f"{_fmt(upper_verdicts[cid])} |"
        )
    lines += [
        f"| **GO** | Requires P1, P2 and P3 | {_fmt(report_lower.go)} | "
        f"{_fmt(report_upper.go)} |",
        "",
        f"Verdicts change between bound choices: "
        f"**{'YES' if lower_verdicts != upper_verdicts or report_lower.go != report_upper.go else 'NO'}**. "
        "No P1–P4 threshold is a function of C, so the two runs cannot disagree "
        "on a verdict; the bound choice affects the C distribution below and "
        "ambiguous_C_rate, which is where DESIGN.md §5's robustness check lives.",
        "",
    ]
    if not report_lower.criteria[3].verdict:
        lines += [
            "P4 FAILED. It does not block GO, and is recorded here as a named "
            "limitation that changes how the result must be framed.",
            "",
        ]

    for criterion in report_lower.criteria:
        lines += [
            f"## {criterion.criterion_id} — {criterion.statement}",
            "",
            f"Threshold: {criterion.threshold}",
            "",
            f"Verdict: {_fmt(criterion.verdict)}",
            "",
        ]
        lines += _table(criterion.per_model)
        if criterion.overall:
            lines += _kv_table(criterion.overall)

    lines += ["## Diagnostics", ""] + _table(report_lower.diagnostics)
    lines += [
        "## Tolerance firing (DESIGN.md §5)",
        "",
        f"Counted over all models, one compute_C call per observation, "
        f"TOLERANCE={config.TOLERANCE}.",
        "",
    ] + _kv_table(report_lower.tolerance_firing)
    lines += ["## Order effects (reported, not thresholded)", ""] + _table(
        _order_effects(grouped)
    )
    lines += [
        "## Rescaled C distribution",
        "",
        f"### tie_rule = lower",
        "",
    ] + _table(report_lower.c_distribution)
    lines += [f"### tie_rule = upper", ""] + _table(report_upper.c_distribution)

    grouped_ms = _by_model_and_source(observations)
    lines += [
        "## Task-set comparison (MBPP vs LBPP)",
        "",
        "Diagnostic only, added 2026-08-14 alongside the LBPP task set. Reuses "
        "the same P1/P2/P4/diagnostics computations as above, applied per "
        "(model, task set) instead of pooled per model, so the two halves can "
        "be compared directly. Does not feed the GO verdict, which stays "
        "computed on the pooled full set above.",
        "",
        "### P1 — self-reports vary, by task set",
        "",
    ] + _table(_p1(grouped_ms).per_model)
    lines += [
        "### P2 — vignette ordering, by task set",
        "",
    ] + _table(_p2(grouped_ms, report_lower.tie_rule).per_model)
    lines += [
        "### P4 — response consistency, by task set",
        "",
    ] + _table(_p4(grouped_ms).per_model)
    lines += ["### Diagnostics, by task set", ""] + _table(_diagnostics(grouped_ms))

    return "\n".join(lines) + "\n"


def write_report(observations: list[Observation]) -> str:
    """Runs the analysis under both bound choices and writes out/report.md."""
    lower = analyze(observations, "lower")
    upper = analyze(observations, "upper")
    markdown = render_report(observations, lower, upper)
    config.OUT_DIR.mkdir(parents=True, exist_ok=True)
    (config.OUT_DIR / "report.md").write_text(markdown)
    return markdown
