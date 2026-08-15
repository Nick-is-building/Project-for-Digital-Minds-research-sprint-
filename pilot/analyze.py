"""Go/no-go analysis (DESIGN.md §9).

Reduces a list of `Observation` records to the four assumption checks P1–P4,
their thresholds, the §2 validity screen, and the diagnostics DESIGN.md §9 asks
for. Renders a report: numbers side by side per model, PASS/FAIL per criterion,
no interpretation.

Deliberately absent, per DESIGN.md §9 and §10: AUROC, correlations, variance
ratios, significance tests. Nothing in this module computes one.

Four things here are load-bearing and easy to get silently wrong:

**Scale format.** Format is an experimental variable (DESIGN.md §3), so every
bound, threshold and tolerance is read off the observation's own `scale_format`
at the point of use. Previously `_MIN_POINT`/`_MAX_POINT` were module-level and
computed at *import* time from a single global scale — which is exactly what went
stale when the 0-100 control run was analysed against 1-5 bounds. `analyze()`
refuses a mixed-format list rather than pooling formats, because pooling means
averaging numbers that are not on the same scale.

**Orientation.** Scale direction is randomised per context (DESIGN.md §3), so
`_orient` exists to make the treatment of direction explicit and testable. It is
deliberately the identity — see its docstring.

**Range.** A strictly-parsed integer can still be off-scale (a model replying
"7" on a 1-5 scale). Off-scale draws are excluded from means and counted
separately, alongside parse failures, rather than being averaged in.

**Vacuity.** Constant anchors make rescaling a monotone recoding of `y`, so every
rank-based statistic is invariant by construction (DESIGN.md §2). Each (model,
format) cell is screened for that and reported Valid or Invalid. The screen is
reported, never applied as a silent filter: an Invalid cell's observations stay
in the tables, and the cell cannot produce a GO.

No P1–P4 threshold is a function of `C`, so the two `tie_rule` runs cannot
disagree on a verdict; the report states that as a structural fact and shows the
`C` distributions, which do differ, next to `ambiguous_C_rate`.
"""

from dataclasses import dataclass, field
from pathlib import Path
from statistics import stdev

from pilot import config
from pilot.rescale import compute_C, reset_tolerance_counts, tolerance_counts

RATING_FIELDS = ("y_v_draws", "z_lo_draws", "z_hi_draws", "y_n_draws", "other_draws")

# `C` has five categories in every scale format: two anchors partition the line
# into exactly five regions (DESIGN.md §5). This is not the input scale.
C_POINTS = (1, 2, 3, 4, 5)


@dataclass(frozen=True)
class Observation:
    """One (model, task, scale format) unit: both conditions, P4, ground truth.

    Draws are the raw parsed integers as returned by `elicit`, in the
    orientation they were presented in; `scale_direction` says which that was.
    Ground truth fields come from execution only (DESIGN.md §8) and are shared
    across the three formats of a (model, task) pair, which all replay the same
    solution — see DESIGN.md §10.
    """

    model: str
    task_id: str
    task_set: str  # "mbpp" or "lbpp" — see tasks.py.
    scale_format: str  # key into config.SCALE_FORMATS
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
    # Why extraction failed, when it did (pilot.extract). Distinguishes "our
    # output ceiling cut the reply off" from "the model emitted junk".
    codegen_failure_reason: str | None = None

    @property
    def scale(self) -> config.ScaleFormat:
        return config.SCALE_FORMATS[self.scale_format]


@dataclass(frozen=True)
class Criterion:
    criterion_id: str
    statement: str
    threshold: str
    verdict: bool
    per_model: dict[str, dict[str, object]] = field(default_factory=dict)
    overall: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class Validity:
    """One (model, format) cell's §2 validity screen result."""

    model: str
    scale_format: str
    valid: bool
    reason: str
    n_usable: int
    z_lo_range: tuple[float, float] | None
    z_hi_range: tuple[float, float] | None


@dataclass(frozen=True)
class Report:
    scale_format: str
    tie_rule: str
    criteria: list[Criterion]
    diagnostics: dict[str, dict[str, object]]
    c_distribution: dict[str, dict[str, object]]
    tolerance_firing: dict[str, object]
    validity: list[Validity]

    @property
    def all_cells_valid(self) -> bool:
        return bool(self.validity) and all(v.valid for v in self.validity)

    @property
    def go(self) -> bool:
        """GO requires P1, P2, P3 and every cell Valid. P4 does not block."""
        criteria_ok = all(c.verdict for c in self.criteria if c.criterion_id != "P4")
        return criteria_ok and self.all_cells_valid

    def verdicts(self) -> dict[str, bool]:
        return {c.criterion_id: c.verdict for c in self.criteria}


# --- Draw handling -----------------------------------------------------------


def _orient(draw: int, direction: str) -> int:
    """Identity. Validates `direction`; deliberately does not transform `draw`.

    DESIGN.md §3 fixes the number-to-label mapping (1 = Very unlikely ... 5 =
    Very likely) and randomises only the order the lines are *printed* in. A
    reply of 5 therefore means "Very likely" under both directions, so there is
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


def _valid_draws(obs: Observation, name: str) -> list[int]:
    """In-range, parseable draws of one field, oriented to a common frame.

    Takes the Observation rather than a bare list so the range bounds always
    come from that observation's own scale format; a caller cannot forget to
    pass it.
    """
    scale = obs.scale
    return [
        _orient(d, obs.scale_direction)
        for d in getattr(obs, name)
        if d is not None and scale.in_range(d)
    ]


def _mean(obs: Observation, name: str) -> float | None:
    valid = _valid_draws(obs, name)
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
    compute_C, any threshold, or the pooled GO verdict.
    """
    grouped: dict[str, list[Observation]] = {}
    for obs in observations:
        grouped.setdefault(f"{obs.model} · {obs.task_set}", []).append(obs)
    return grouped


def _by_format(observations: list[Observation]) -> dict[str, list[Observation]]:
    grouped: dict[str, list[Observation]] = {}
    for obs in observations:
        grouped.setdefault(obs.scale_format, []).append(obs)
    return grouped


def _single_format(observations: list[Observation]) -> config.ScaleFormat:
    names = {o.scale_format for o in observations}
    if len(names) != 1:
        raise ValueError(
            "analyze() takes one scale format at a time; got "
            f"{sorted(names)}. Pooling formats would average values that are "
            "not on the same scale — split with _by_format first."
        )
    return config.SCALE_FORMATS[names.pop()]


def _rate(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _sd(values: list[float]) -> float | None:
    return stdev(values) if len(values) >= 2 else None


def _spread(values: list[float]) -> float | None:
    return max(values) - min(values) if len(values) >= 2 else None


# --- §2 validity screen ------------------------------------------------------


def _validity(
    grouped: dict[str, list[Observation]], scale: config.ScaleFormat
) -> list[Validity]:
    """Marks each (model, format) cell Valid or Invalid (DESIGN.md §2).

    Invalid iff *both* anchors are constant across the cell, to within the
    format's equality tolerance — that is the exact condition under which `C`
    reduces to a monotone recoding of `y`. One constant anchor still leaves a
    varying threshold, so it is not vacuous and is not flagged here (it is
    visible in P2/P3 instead).
    """
    out: list[Validity] = []
    for model, obs_list in grouped.items():
        lows = [m for m in (_mean(o, "z_lo_draws") for o in obs_list) if m is not None]
        highs = [m for m in (_mean(o, "z_hi_draws") for o in obs_list) if m is not None]
        n_usable = min(len(lows), len(highs))

        lo_spread = _spread(lows)
        hi_spread = _spread(highs)

        if n_usable < 2:
            valid, reason = False, (
                f"undetermined: only {n_usable} observation(s) with both anchors "
                "usable, so constancy cannot be assessed"
            )
        else:
            lo_constant = lo_spread is not None and lo_spread <= scale.tolerance
            hi_constant = hi_spread is not None and hi_spread <= scale.tolerance
            if lo_constant and hi_constant:
                valid = False
                reason = (
                    f"INVALID: both anchors constant to within tolerance "
                    f"{scale.tolerance:g} (z_lo ≡ {lows[0]:g}, z_hi ≡ {highs[0]:g}). "
                    "C is a monotone recoding of y here, so every rank-based "
                    "statistic is invariant by construction (DESIGN.md §2) and "
                    "any apparent effect is an artefact of the recoding."
                )
            else:
                valid = True
                reason = (
                    f"valid: anchors vary across observations (z_lo spread "
                    f"{lo_spread:g}, z_hi spread {hi_spread:g}, tolerance "
                    f"{scale.tolerance:g})"
                )

        out.append(
            Validity(
                model=model,
                scale_format=scale.name,
                valid=valid,
                reason=reason,
                n_usable=n_usable,
                z_lo_range=(min(lows), max(lows)) if lows else None,
                z_hi_range=(min(highs), max(highs)) if highs else None,
            )
        )
    return out


# --- P1: self-reports vary across tasks -------------------------------------


def _p1(grouped: dict[str, list[Observation]], scale: config.ScaleFormat) -> Criterion:
    per_model: dict[str, dict[str, object]] = {}
    passes = []

    for model, obs_list in grouped.items():
        points: list[int] = []
        for obs in obs_list:
            points.extend(_valid_draws(obs, "y_n_draws"))
        means = [m for m in (_mean(o, "y_n_draws") for o in obs_list) if m is not None]

        distinct = len(set(points))
        sd = _sd(means)
        ok = (
            distinct >= config.P1_MIN_DISTINCT_SCALE_POINTS
            and sd is not None
            and sd >= scale.p1_min_sd
        )
        passes.append(ok)

        metrics: dict[str, object] = {
            "observations with a usable self-report": len(means),
            "distinct scale points used": distinct,
            "SD across tasks": sd,
            "mean self-report": sum(means) / len(means) if means else None,
        }
        if scale.fully_labelled:
            for point in sorted(scale.labels):
                metrics[f"draws at {point} ({scale.labels[point]})"] = points.count(point)
        else:
            metrics["draw range (min-max)"] = (
                f"{min(points)}-{max(points)}" if points else None
            )
            metrics["distinct per-task means"] = len(set(means))
        metrics["verdict"] = ok
        per_model[model] = metrics

    return Criterion(
        criterion_id="P1",
        statement="Self-reports vary across tasks",
        threshold=(
            f">= {config.P1_MIN_DISTINCT_SCALE_POINTS} distinct scale points AND "
            f"SD >= {scale.p1_min_sd:g} "
            f"({config.P1_MIN_SD_FRACTION_OF_WIDTH:g} x width {scale.width}). "
            "Computed on condition N, the uncontaminated raw self-report; "
            "distinct points are counted over individual draws, SD over "
            "per-task means. The distinct-point count is absolute across "
            "formats and is therefore easier to clear on a finer scale — see "
            "DESIGN.md §9."
        ),
        verdict=bool(passes) and all(passes),
        per_model=per_model,
    )


# --- P2: vignettes ordered correctly ----------------------------------------


def _p2(
    grouped: dict[str, list[Observation]], tie_rule: str, scale: config.ScaleFormat
) -> Criterion:
    per_model: dict[str, dict[str, object]] = {}
    passes = []

    for model, obs_list in grouped.items():
        clean = tie = misorder = usable = ambiguous = 0
        for obs in obs_list:
            z_lo = _mean(obs, "z_lo_draws")
            z_hi = _mean(obs, "z_hi_draws")
            if z_lo is None or z_hi is None:
                continue
            usable += 1
            if abs(z_lo - z_hi) <= scale.tolerance:
                tie += 1
            elif z_lo > z_hi:
                misorder += 1
            else:
                clean += 1

            y_v = _mean(obs, "y_v_draws")
            lower = compute_C(y_v, z_lo, z_hi, "lower", scale.tolerance)
            upper = compute_C(y_v, z_lo, z_hi, "upper", scale.tolerance)
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
            f"{config.P2_MAX_TIE_RATE:.0%}. Ties use tolerance "
            f"{scale.tolerance:g} "
            f"({config.TOLERANCE_FRACTION_OF_WIDTH:g} x width {scale.width}). "
            "ambiguous_C_rate is the share of observations where the lower and "
            "upper bound of C disagree; it is reported, not thresholded."
        ),
        verdict=bool(passes) and all(passes),
        per_model=per_model,
    )


# --- P3: models differ in scale use -----------------------------------------


def _p3(grouped: dict[str, list[Observation]], scale: config.ScaleFormat) -> Criterion:
    per_model: dict[str, dict[str, object]] = {}
    z_lo_means: dict[str, float] = {}
    z_hi_means: dict[str, float] = {}

    for model, obs_list in grouped.items():
        lows = [m for m in (_mean(o, "z_lo_draws") for o in obs_list) if m is not None]
        highs = [m for m in (_mean(o, "z_hi_draws") for o in obs_list) if m is not None]
        mean_low = sum(lows) / len(lows) if lows else None
        mean_high = sum(highs) / len(highs) if highs else None
        if mean_low is not None:
            z_lo_means[model] = mean_low
        if mean_high is not None:
            z_hi_means[model] = mean_high
        per_model[model] = {"mean z_lo": mean_low, "mean z_hi": mean_high}

    spread_low = _spread(list(z_lo_means.values()))
    spread_high = _spread(list(z_hi_means.values()))
    ok = any(
        s is not None and s >= scale.p3_min_difference for s in (spread_low, spread_high)
    )

    return Criterion(
        criterion_id="P3",
        statement="Models differ from each other in scale use",
        threshold=(
            f">= {scale.p3_min_difference:g} scale points "
            f"({config.P3_MIN_DIFFERENCE_FRACTION_OF_WIDTH:g} x width "
            f"{scale.width}) apart on mean z_lo OR mean z_hi (max - min across "
            "models, within this format)"
        ),
        verdict=ok,
        per_model=per_model,
        overall={
            "between-model spread in mean z_lo": spread_low,
            "between-model spread in mean z_hi": spread_high,
        },
    )


# --- P4: response consistency across self/other -----------------------------


def _p4(grouped: dict[str, list[Observation]], scale: config.ScaleFormat) -> Criterion:
    per_model: dict[str, dict[str, object]] = {}
    passes = []

    for model, obs_list in grouped.items():
        gaps = []
        selfs = []
        others = []
        for obs in obs_list:
            self_rating = _mean(obs, "y_n_draws")
            other_rating = _mean(obs, "other_draws")
            if self_rating is None or other_rating is None:
                continue
            selfs.append(self_rating)
            others.append(other_rating)
            gaps.append(self_rating - other_rating)

        mean_self = sum(selfs) / len(selfs) if selfs else None
        mean_other = sum(others) / len(others) if others else None
        signed_gap = sum(gaps) / len(gaps) if gaps else None
        ok = signed_gap is not None and abs(signed_gap) <= scale.p4_max_abs_gap
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
            f"|mean signed gap| <= {scale.p4_max_abs_gap:g} scale points "
            f"({config.P4_MAX_ABS_GAP_FRACTION_OF_WIDTH:g} x width "
            f"{scale.width}). Compared against condition N, which like the probe "
            "carries no vignettes. Does not block GO; a failure is a named "
            "limitation."
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
        reasons: dict[str, int] = {}
        for obs in obs_list:
            scale = obs.scale
            for name in RATING_FIELDS:
                draws = getattr(obs, name)
                failures = sum(1 for d in draws if d is None)
                off = sum(1 for d in draws if d is not None and not scale.in_range(d))
                total_draws += len(draws)
                parse_failures += failures
                off_scale += off
                per_question[name] = per_question.get(name, 0) + failures + off
            if obs.codegen_failure_reason:
                reasons[obs.codegen_failure_reason] = (
                    reasons.get(obs.codegen_failure_reason, 0) + 1
                )

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
        for reason, count in sorted(reasons.items()):
            metrics[f"codegen rejected: {reason}"] = count
        out[model] = metrics

    return out


def _c_distribution(
    grouped: dict[str, list[Observation]], tie_rule: str, scale: config.ScaleFormat
) -> dict[str, dict[str, object]]:
    out: dict[str, dict[str, object]] = {}
    for model, obs_list in grouped.items():
        values = [
            compute_C(
                _mean(o, "y_v_draws"),
                _mean(o, "z_lo_draws"),
                _mean(o, "z_hi_draws"),
                tie_rule,
                scale.tolerance,
            )
            for o in obs_list
        ]
        usable = [v for v in values if v is not None]
        metrics: dict[str, object] = {
            "C computed": len(usable),
            "C unavailable": len(values) - len(usable),
            "mean C": sum(usable) / len(usable) if usable else None,
        }
        for point in C_POINTS:
            metrics[f"C = {point}"] = usable.count(float(point))
        out[model] = metrics
    return out


def _tolerance_firing(
    grouped: dict[str, list[Observation]], tie_rule: str, scale: config.ScaleFormat
) -> dict[str, object]:
    """How often the tolerance window decided an equality (DESIGN.md §5).

    Runs its own single pass so the denominator is one call per observation;
    the other metrics call compute_C more than once each, which would inflate it.
    """
    reset_tolerance_counts()
    for obs_list in grouped.values():
        for obs in obs_list:
            compute_C(
                _mean(obs, "y_v_draws"),
                _mean(obs, "z_lo_draws"),
                _mean(obs, "z_hi_draws"),
                tie_rule,
                scale.tolerance,
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
                    _mean(o, "y_n_draws")
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
                        _mean(o, anchor)
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


def analyze(observations: list[Observation], tie_rule: str) -> Report:
    """Analyses one scale format. Raises on a mixed-format list."""
    scale = _single_format(observations)
    grouped = _by_model(observations)
    return Report(
        scale_format=scale.name,
        tie_rule=tie_rule,
        criteria=[
            _p1(grouped, scale),
            _p2(grouped, tie_rule, scale),
            _p3(grouped, scale),
            _p4(grouped, scale),
        ],
        diagnostics=_diagnostics(grouped),
        c_distribution=_c_distribution(grouped, tie_rule, scale),
        tolerance_firing=_tolerance_firing(grouped, tie_rule, scale),
        validity=_validity(grouped, scale),
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
    columns = list(dict.fromkeys(k for m in models for k in per_model[m]))
    rows = [f"| Metric | {' | '.join(models)} |", f"|---|{'---|' * len(models)}"]
    for metric in columns:
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


def _validity_table(validity: list[Validity]) -> list[str]:
    if not validity:
        return ["_No cells._", ""]
    rows = [
        "| Model | Valid | n with both anchors | z_lo range | z_hi range | Note |",
        "|---|---|---|---|---|---|",
    ]
    for v in validity:
        lo = f"{v.z_lo_range[0]:g}–{v.z_lo_range[1]:g}" if v.z_lo_range else "n/a"
        hi = f"{v.z_hi_range[0]:g}–{v.z_hi_range[1]:g}" if v.z_hi_range else "n/a"
        rows.append(
            f"| {v.model} | {'**VALID**' if v.valid else '**INVALID**'} | "
            f"{v.n_usable} | {lo} | {hi} | {v.reason} |"
        )
    rows.append("")
    return rows


def _format_section(
    observations: list[Observation], lower: Report, upper: Report
) -> list[str]:
    scale = _single_format(observations)
    grouped = _by_model(observations)
    lower_verdicts = lower.verdicts()
    upper_verdicts = upper.verdicts()

    lines = [
        f"# Format `{scale.name}`",
        "",
        f"Scale {scale.min_point}–{scale.max_point} (width {scale.width}), "
        f"{'fully labelled' if scale.fully_labelled else 'endpoints labelled only'}: "
        f"{dict(scale.labels)}. "
        f"Answer instruction: {scale.answer_instruction!r}. "
        f"Rating token cap: {scale.max_output_tokens_rating}.",
        "",
        f"Width-relative thresholds (DESIGN.md §9): P1 SD >= {scale.p1_min_sd:g}, "
        f"P3 >= {scale.p3_min_difference:g}, P4 <= {scale.p4_max_abs_gap:g}, "
        f"equality tolerance {scale.tolerance:g}.",
        "",
        f"{len(grouped)} models x {len({o.task_id for o in observations})} tasks, "
        f"{len(observations)} observations.",
        "",
        "## Validity screen (DESIGN.md §2)",
        "",
        "A cell is Invalid iff BOTH anchors are constant across its "
        "observations, in which case C is a monotone recoding of y and every "
        "rank-based statistic is invariant by construction. Invalid cells are "
        "reported, not filtered: their observations remain in every table "
        "below, and an Invalid cell cannot produce a GO.",
        "",
    ]
    lines += _validity_table(lower.validity)

    lines += ["## Verdict", ""]
    lines += [
        "| Criterion | Statement | tie_rule=lower | tie_rule=upper |",
        "|---|---|---|---|",
    ]
    for criterion in lower.criteria:
        cid = criterion.criterion_id
        lines.append(
            f"| {cid} | {criterion.statement} | {_fmt(lower_verdicts[cid])} | "
            f"{_fmt(upper_verdicts[cid])} |"
        )
    lines += [
        f"| Validity | Every cell Valid (§2) | {_fmt(lower.all_cells_valid)} | "
        f"{_fmt(upper.all_cells_valid)} |",
        f"| **GO** | Requires P1, P2, P3 and all cells Valid | "
        f"{_fmt(lower.go)} | {_fmt(upper.go)} |",
        "",
        "Verdicts change between bound choices: "
        f"**{'YES' if lower_verdicts != upper_verdicts or lower.go != upper.go else 'NO'}**. "
        "No P1–P4 threshold is a function of C, so the two runs cannot disagree "
        "on a verdict; the bound choice affects the C distribution below and "
        "ambiguous_C_rate, which is where DESIGN.md §5's robustness check lives.",
        "",
    ]
    if not lower.criteria[3].verdict:
        lines += [
            "P4 FAILED. It does not block GO, and is recorded here as a named "
            "limitation that changes how the result must be framed.",
            "",
        ]

    for criterion in lower.criteria:
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

    lines += ["## Diagnostics", ""] + _table(lower.diagnostics)
    lines += [
        "## Tolerance firing (DESIGN.md §5)",
        "",
        f"All models, one compute_C call per observation, tolerance "
        f"{scale.tolerance:g}.",
        "",
    ] + _kv_table(lower.tolerance_firing)
    lines += ["## Order effects (reported, not thresholded)", ""] + _table(
        _order_effects(grouped)
    )
    lines += [
        "## Rescaled C distribution",
        "",
        "C has five categories in every format: two anchors partition the line "
        "into five regions (DESIGN.md §5). This is not the input scale.",
        "",
        "### tie_rule = lower",
        "",
    ] + _table(lower.c_distribution)
    lines += ["### tie_rule = upper", ""] + _table(upper.c_distribution)

    grouped_ms = _by_model_and_source(observations)
    lines += [
        "## Task-set comparison (MBPP vs LBPP)",
        "",
        "Diagnostic only. Reuses the same P1/P2/P4/diagnostics computations as "
        "above, applied per (model, task set) instead of pooled per model. Does "
        "not feed the GO verdict.",
        "",
        "### P1 — self-reports vary, by task set",
        "",
    ] + _table(_p1(grouped_ms, scale).per_model)
    lines += ["### P2 — vignette ordering, by task set", ""] + _table(
        _p2(grouped_ms, lower.tie_rule, scale).per_model
    )
    lines += ["### P4 — response consistency, by task set", ""] + _table(
        _p4(grouped_ms, scale).per_model
    )
    lines += ["### Diagnostics, by task set", ""] + _table(_diagnostics(grouped_ms))

    return lines


def render_report(observations: list[Observation]) -> str:
    """One document: a cross-format summary, then one section per format."""
    by_format = _by_format(observations)
    ordered = [f.name for f in config.MAIN_SCALE_FORMATS if f.name in by_format]
    ordered += [name for name in by_format if name not in ordered]

    reports = {
        name: (analyze(by_format[name], "lower"), analyze(by_format[name], "upper"))
        for name in ordered
    }

    task_sets = {o.task_id: o.task_set for o in observations}
    source_counts: dict[str, int] = {}
    for source in task_sets.values():
        source_counts[source] = source_counts.get(source, 0) + 1

    lines = [
        "# Report",
        "",
        f"{len({o.model for o in observations})} models x {len(task_sets)} tasks "
        f"({source_counts.get('mbpp', 0)} MBPP + {source_counts.get('lbpp', 0)} LBPP) "
        f"x {len(ordered)} scale formats, {len(observations)} observations. "
        "Thresholds are DESIGN.md §9, fixed before the numbers were seen, and "
        "expressed as fractions of each format's width so they mean the same "
        "thing in all three. No interpretation is added here.",
        "",
        "Not computed, per DESIGN.md §9: AUROC, correlations, variance ratios, "
        "significance tests.",
        "",
        "## Cross-format summary",
        "",
        "| Format | Width | P1 | P2 | P3 | P4 | All cells Valid | GO |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for name in ordered:
        lower, _ = reports[name]
        v = lower.verdicts()
        scale = config.SCALE_FORMATS[name]
        lines.append(
            f"| `{name}` | {scale.width} | {_fmt(v['P1'])} | {_fmt(v['P2'])} | "
            f"{_fmt(v['P3'])} | {_fmt(v['P4'])} | "
            f"{_fmt(lower.all_cells_valid)} | {_fmt(lower.go)} |"
        )
    lines += [
        "",
        "Verdicts above are for tie_rule=lower; the per-format sections show "
        "both bounds. A format disagreeing with another is a result about the "
        "scale, not an error to be resolved — see DESIGN.md §3.",
        "",
    ]

    for name in ordered:
        lower, upper = reports[name]
        lines += ["---", ""]
        lines += _format_section(by_format[name], lower, upper)

    return "\n".join(lines) + "\n"


def write_report(observations: list[Observation], path: Path | None = None) -> str:
    """Renders every format under both bound choices and writes the report."""
    markdown = render_report(observations)
    target = path or (config.OUT_DIR / "report.md")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(markdown)
    return markdown
