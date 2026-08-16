"""Condition R vs condition V report, p5 only (post-hoc, 2026-08-16). NO API CALLS.

*** CONDITION R IS A DEVIATION FROM THE PREREGISTERED DESIGN. IT WAS NOT IN ***
*** DESIGN.md. THIS REPORT DESCRIBES IT; IT DOES NOT REPLACE THE MAIN      ***
*** RESULT AND MUST NOT BE READ AS ONE.                                   ***

Condition V (main run, DESIGN.md §4) asks the two vignettes, then the
self-question, in one shared context. Condition R (`run_condition_r.py`)
reverses that order: self-question first, then both vignettes. Same wording,
same p5 scale, same 5 models, same 60 tasks, same reused solutions, same
randomised presentation per (model, task) — turn order is the only thing that
differs. `pilot/rescale.py::compute_C` is unmodified throughout; this script
only reads existing fields (`y_v_draws`/`z_lo_draws`/`z_hi_draws` from the
main run, `y_r_draws`/`z_lo_r_draws`/`z_hi_r_draws` from condition R) and
renames columns before calling it, exactly as authorised for
`cross_condition_report.py` — see that script and the DEVLOG entry
authorising both.

Reads `pilot/out/main_observations.jsonl` and
`pilot/out/condition_r_observations.jsonl` (both read-only). Writes
`pilot/out/condition_r_report.md`. Never touches `main_report.md` or
`main_observations.jsonl`.

Usage:
    python3 condition_r_report.py
"""

import dataclasses

from scipy import stats

from pilot import analyze, config, resume
from pilot.rescale import compute_C

OUT_PATH = config.CONDITION_R_REPORT_PATH
FMT = config.SCALE_P5
TIE_RULE = "lower"  # cross_condition_report.py found lower == upper throughout
                     # condition V's p5 data (0 ties, 0 misorderings); unaffected here.


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _rate(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _c_distribution(values: list[float | None]) -> tuple[dict[int, int], int]:
    dist = {p: 0 for p in analyze.C_POINTS}
    none_count = 0
    for v in values:
        if v is None:
            none_count += 1
        else:
            dist[int(v)] += 1
    return dist, none_count


class ModelCell:
    """One model's condition-R-vs-V numbers, p5 only."""

    def __init__(
        self,
        model: str,
        main_obs: list[analyze.Observation],
        r_obs: list[analyze.Observation],
    ):
        self.model = model
        self.main_obs = main_obs
        self.r_obs = r_obs

        self.y_v_values: list[float] = []
        self.y_n_values: list[float] = []
        self.c_v: list[float | None] = []
        for obs in main_obs:
            y_v = analyze._mean(obs, "y_v_draws")
            y_n = analyze._mean(obs, "y_n_draws")
            z_lo = analyze._mean(obs, "z_lo_draws")
            z_hi = analyze._mean(obs, "z_hi_draws")
            if y_v is not None:
                self.y_v_values.append(y_v)
            if y_n is not None:
                self.y_n_values.append(y_n)
            self.c_v.append(compute_C(y_v, z_lo, z_hi, TIE_RULE, FMT.tolerance))

        self.y_r_values: list[float] = []
        self.c_r: list[float | None] = []
        for obs in r_obs:
            y_r = analyze._mean(obs, "y_r_draws")
            z_lo_r = analyze._mean(obs, "z_lo_r_draws")
            z_hi_r = analyze._mean(obs, "z_hi_r_draws")
            if y_r is not None:
                self.y_r_values.append(y_r)
            self.c_r.append(compute_C(y_r, z_lo_r, z_hi_r, TIE_RULE, FMT.tolerance))

        # Ground truth is a property of the shared, reused solution (DESIGN.md
        # §10) — read off the main run's p5 cell, not recomputed here.
        self.n_total = len(main_obs)
        self.n_pass_as_is = sum(1 for o in main_obs if o.passes_hidden)
        extracted = [o for o in main_obs if o.code_extracted]
        self.n_extracted = len(extracted)
        self.n_pass_extracted = sum(1 for o in extracted if o.passes_hidden)

    def c_dist(self, which: str) -> tuple[dict[int, int], int]:
        return _c_distribution(self.c_v if which == "v" else self.c_r)

    def share_c4(self, which: str) -> float | None:
        values = self.c_v if which == "v" else self.c_r
        computed = [c for c in values if c is not None]
        return _rate(sum(1 for c in computed if int(c) == 4), len(computed))

    def mean_c(self, which: str) -> float | None:
        values = self.c_v if which == "v" else self.c_r
        return _mean([c for c in values if c is not None])

    @property
    def mean_y_v(self) -> float | None:
        return _mean(self.y_v_values)

    @property
    def mean_y_n(self) -> float | None:
        return _mean(self.y_n_values)

    @property
    def mean_y_r(self) -> float | None:
        return _mean(self.y_r_values)

    @property
    def true_rate_as_is(self) -> float | None:
        return _rate(self.n_pass_as_is, self.n_total)

    @property
    def true_rate_excl_extraction_failures(self) -> float | None:
        return _rate(self.n_pass_extracted, self.n_extracted)


def build_cells(
    main_p5_obs: list[analyze.Observation],
    r_obs: list[analyze.Observation],
    models: tuple[str, ...],
) -> dict[str, ModelCell]:
    main_by_model = analyze._by_model(main_p5_obs)
    r_by_model = analyze._by_model(r_obs)
    return {
        model: ModelCell(model, main_by_model.get(model, []), r_by_model.get(model, []))
        for model in models
    }


def _relabelled_for_validity(r_obs: list[analyze.Observation]) -> list[analyze.Observation]:
    """R's observations with the shared `_validity` field names, for reuse.

    `analyze._validity` is unmodified and reads `z_lo_draws`/`z_hi_draws` by
    name; condition R's anchors live in `z_lo_r_draws`/`z_hi_r_draws`. This
    relabels via `dataclasses.replace` — no field is recomputed, only renamed
    — same technique `cross_condition_report.py` uses to feed `compute_C`
    unmodified with a different condition's columns.
    """
    return [
        dataclasses.replace(o, z_lo_draws=o.z_lo_r_draws, z_hi_draws=o.z_hi_r_draws)
        for o in r_obs
    ]


def _correlate(xs: list[float], ys: list[float]) -> tuple[float | None, float | None]:
    if len(xs) < 3 or len(set(xs)) < 2 or len(set(ys)) < 2:
        return None, None
    pearson = stats.pearsonr(xs, ys).statistic
    spearman = stats.spearmanr(xs, ys).statistic
    return pearson, spearman


def _fmt(value: float | None, digits: int = 3) -> str:
    return "n/a" if value is None else f"{value:.{digits}f}"


def render(
    cells: dict[str, ModelCell],
    r_obs: list[analyze.Observation],
    models: tuple[str, ...],
) -> str:
    lines: list[str] = []
    lines.append("# Condition R vs condition V, p5 only (post-hoc, 2026-08-16)")
    lines.append("")
    lines.append(
        "**CONDITION R IS NOT PREREGISTERED (not in DESIGN.md).** It reverses "
        "condition V's turn order — self-question FIRST, then both vignettes — "
        "everything else held identical: wording, p5 scale, 5 models, 60 tasks, "
        "reused solutions, randomised presentation per (model, task). "
        "`pilot/rescale.py::compute_C` is unmodified; see the DEVLOG entry "
        "authorising this script and `run_condition_r.py`."
    )
    lines.append("")

    present = [m for m in models if m in cells]

    lines.append("## C distribution per model — condition R vs condition V")
    lines.append("")
    lines.append(
        "| model | condition | n | C=1 | C=2 | C=3 | C=4 | C=5 | None | share C=4 |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for model in present:
        cell = cells[model]
        for label, which in (("V (main run)", "v"), ("R (post-hoc)", "r")):
            dist, none_count = cell.c_dist(which)
            n = len(cell.main_obs) if which == "v" else len(cell.r_obs)
            lines.append(
                f"| {model} | {label} | {n} | {dist[1]} | {dist[2]} | {dist[3]} | "
                f"{dist[4]} | {dist[5]} | {none_count} | {_fmt(cell.share_c4(which), 3)} |"
            )
    lines.append("")

    lines.append("## Mean self-report `y`, by condition")
    lines.append("")
    lines.append("| model | mean y (cond. V, contaminated) | mean y (cond. N) | mean y (cond. R, post-hoc) |")
    lines.append("|---|---|---|---|")
    for model in present:
        cell = cells[model]
        lines.append(
            f"| {model} | {_fmt(cell.mean_y_v)} | {_fmt(cell.mean_y_n)} | {_fmt(cell.mean_y_r)} |"
        )
    lines.append("")

    lines.append("## Mean C and true `passes_hidden` rate")
    lines.append("")
    lines.append(
        "| model | mean C (V) | mean C (R) | true rate as-is | true rate excl. "
        "extraction failures | n extracted/n total |"
    )
    lines.append("|---|---|---|---|---|---|")
    for model in present:
        cell = cells[model]
        lines.append(
            f"| {model} | {_fmt(cell.mean_c('v'))} | {_fmt(cell.mean_c('r'))} | "
            f"{_fmt(cell.true_rate_as_is)} | {_fmt(cell.true_rate_excl_extraction_failures)} | "
            f"{cell.n_extracted}/{cell.n_total} |"
        )
    lines.append("")

    lines.append("## Validity screen per model under condition R (DESIGN.md §2)")
    lines.append("")
    lines.append(
        "`analyze._validity` is unmodified; condition R's own anchors "
        "(`z_lo_r_draws`/`z_hi_r_draws`) are relabelled to the field names it "
        "reads, nothing is recomputed."
    )
    lines.append("")
    relabelled = _relabelled_for_validity(r_obs)
    validity = analyze._validity(analyze._by_model(relabelled), FMT)
    lines += analyze._validity_table(validity)

    lines.append(
        "## Clean across-model correlation, condition R's own y and anchors "
        "(n=5 models — a 5-point correlation is extremely fragile; see "
        "CLAUDE.md's task-count reasoning, which applies with equal force here)"
    )
    lines.append("")
    lines.append("| x | true-rate variant | pearson r | spearman rho |")
    lines.append("|---|---|---|---|")

    mean_y_r = [cells[m].mean_y_r for m in present]
    mean_c_r = [cells[m].mean_c("r") for m in present]
    rate_as_is = [cells[m].true_rate_as_is for m in present]
    rate_excl = [cells[m].true_rate_excl_extraction_failures for m in present]

    def _row(label: str, xs: list[float | None], rate_label: str, rates: list[float | None]) -> None:
        pairs = [(x, r) for x, r in zip(xs, rates) if x is not None and r is not None]
        if len(pairs) < len(present):
            lines.append(
                f"| {label} | {rate_label} | n/a ({len(pairs)}/{len(present)} "
                "models have both values) | n/a |"
            )
            return
        px, py = zip(*pairs)
        pearson, spearman = _correlate(list(px), list(py))
        lines.append(f"| {label} | {rate_label} | {_fmt(pearson)} | {_fmt(spearman)} |")

    _row("mean y (cond. R)", mean_y_r, "as-is", rate_as_is)
    _row("mean y (cond. R)", mean_y_r, "excl. extraction failures", rate_excl)
    _row(f"mean C ({TIE_RULE}, cond. R)", mean_c_r, "as-is", rate_as_is)
    _row(f"mean C ({TIE_RULE}, cond. R)", mean_c_r, "excl. extraction failures", rate_excl)
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    main_observations = resume.load_observations(config.MAIN_OBSERVATIONS_PATH)
    if not main_observations:
        raise SystemExit(f"No observations found at {config.MAIN_OBSERVATIONS_PATH}")
    main_p5 = [o for o in main_observations if o.scale_format == FMT.name]

    r_observations = resume.load_observations(config.CONDITION_R_OBSERVATIONS_PATH)
    if not r_observations:
        raise SystemExit(f"No observations found at {config.CONDITION_R_OBSERVATIONS_PATH}")

    cells = build_cells(main_p5, r_observations, config.MAIN_MODELS)
    report = render(cells, r_observations, config.MAIN_MODELS)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(report + "\n")
    print(f"Wrote {OUT_PATH}")
    print()
    print(report)


if __name__ == "__main__":
    main()
