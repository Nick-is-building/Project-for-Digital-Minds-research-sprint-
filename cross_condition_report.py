"""Cross-condition rescaling diagnostic (post-hoc, 2026-08-16). NO API CALLS.

*** THIS IS A DEVIATION FROM THE PREREGISTERED DESIGN. ITS OUTPUT IS A ***
*** DIAGNOSTIC, NOT A RESULT. ***

The main run showed condition V's self-report `y_v` collapsing onto the high
anchor `z_hi` for several models (e.g. claude-haiku-4-5-20251001: C=4 in
59/59 p5 observations, per `pilot/out/main_report.md`). Because `y_v` and the
anchors are elicited in the same context, `y_v` is contaminated by having
seen the anchors before rating itself — that is the exact mechanism the
method relies on, and here it saturates instead of discriminating.

Condition N's self-report `y_n` is elicited with no vignettes in context, so
it does not carry that particular contamination — but condition N has no
anchors of its own, so there is nothing to rescale it against.

This script builds `C` from `y_n` (condition N) and `z_lo`/`z_hi` (condition
V), same (model, task, scale_format) cell. `compute_C` (`pilot/rescale.py`)
is byte-identical and unmodified — see the DEVLOG entry authorising this
script and CLAUDE.md's model-routing clarification. Only the columns fed
into it are new: `y` and the anchors now come from two different elicitation
contexts, which DESIGN.md never specifies and which King & Wand's mechanism
was never validated for. Any agreement or disagreement with ground truth
below is a property of this construction, not evidence about the
vignette-correction method as designed. It is run at all only because
condition V's own `y` is demonstrably unusable for this purpose.

Reads `pilot/out/main_observations.jsonl` (read-only). Writes
`pilot/out/cross_condition_report.md`. Never touches `main_report.md`.

Usage:
    python3 cross_condition_report.py
"""

from scipy import stats

from pilot import analyze, config, resume
from pilot.rescale import compute_C

OUT_PATH = config.OUT_DIR / "cross_condition_report.md"

TIE_RULES = ("lower", "upper")


def _rate(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _c_distribution(values: list[float | None]) -> tuple[dict[int, int], int]:
    dist = {p: 0 for p in analyze.C_POINTS}
    none_count = 0
    for v in values:
        if v is None:
            none_count += 1
        else:
            dist[int(v)] += 1
    return dist, none_count


class Cell:
    """One (model, format) cell's cross-condition numbers, both tie rules."""

    def __init__(self, model: str, fmt: config.ScaleFormat, obs_list: list[analyze.Observation]):
        self.model = model
        self.fmt = fmt
        self.n_total = len(obs_list)

        self.y_n_values: list[float] = []
        self.y_v_values: list[float] = []  # reference only — condition V's contaminated y
        self.c_values: dict[str, list[float | None]] = {r: [] for r in TIE_RULES}

        for obs in obs_list:
            y_n = analyze._mean(obs, "y_n_draws")
            y_v = analyze._mean(obs, "y_v_draws")
            z_lo = analyze._mean(obs, "z_lo_draws")
            z_hi = analyze._mean(obs, "z_hi_draws")
            if y_n is not None:
                self.y_n_values.append(y_n)
            if y_v is not None:
                self.y_v_values.append(y_v)
            for rule in TIE_RULES:
                self.c_values[rule].append(compute_C(y_n, z_lo, z_hi, rule, fmt.tolerance))

        self.n_pass_as_is = sum(1 for o in obs_list if o.passes_hidden)
        extracted = [o for o in obs_list if o.code_extracted]
        self.n_extracted = len(extracted)
        self.n_pass_extracted = sum(1 for o in extracted if o.passes_hidden)

    @property
    def mean_y_n(self) -> float | None:
        return _mean(self.y_n_values)

    @property
    def mean_y_v(self) -> float | None:
        return _mean(self.y_v_values)

    def mean_c(self, rule: str) -> float | None:
        return _mean([c for c in self.c_values[rule] if c is not None])

    def c_dist(self, rule: str) -> tuple[dict[int, int], int]:
        return _c_distribution(self.c_values[rule])

    @property
    def true_rate_as_is(self) -> float | None:
        return _rate(self.n_pass_as_is, self.n_total)

    @property
    def true_rate_excl_extraction_failures(self) -> float | None:
        return _rate(self.n_pass_extracted, self.n_extracted)


def build_cells(observations: list[analyze.Observation]) -> dict[str, dict[str, Cell]]:
    """`{scale_format: {model: Cell}}`."""
    out: dict[str, dict[str, Cell]] = {}
    for fmt_name, fmt_obs in analyze._by_format(observations).items():
        fmt = config.SCALE_FORMATS[fmt_name]
        out[fmt_name] = {
            model: Cell(model, fmt, obs_list)
            for model, obs_list in analyze._by_model(fmt_obs).items()
        }
    return out


def _correlate(xs: list[float], ys: list[float]) -> tuple[float | None, float | None]:
    """`(pearson_r, spearman_rho)`, or `(None, None)` if undefined (n<3 or constant input)."""
    if len(xs) < 3 or len(set(xs)) < 2 or len(set(ys)) < 2:
        return None, None
    pearson = stats.pearsonr(xs, ys).statistic
    spearman = stats.spearmanr(xs, ys).statistic
    return pearson, spearman


def _fmt(value: float | None, digits: int = 3) -> str:
    return "n/a" if value is None else f"{value:.{digits}f}"


def render(cells: dict[str, dict[str, Cell]], models: tuple[str, ...]) -> str:
    lines: list[str] = []
    lines.append("# Cross-condition rescaling diagnostic (post-hoc, 2026-08-16)")
    lines.append("")
    lines.append(
        "**THIS IS A DEVIATION FROM THE PREREGISTERED DESIGN. `C` HERE IS BUILT "
        "FROM `y` (CONDITION N) AND `z_lo`/`z_hi` (CONDITION V) — TWO DIFFERENT "
        "ELICITATION CONTEXTS. THIS IS A DIAGNOSTIC, NOT A RESULT.** It exists "
        "only because condition V's own `y` collapses onto the high anchor for "
        "several models (see `pilot/out/main_report.md`), which makes it "
        "unusable to show what rescaling does. `pilot/rescale.py::compute_C` is "
        "unmodified; only the input columns are new. See the DEVLOG entry "
        "authorising this script."
    )
    lines.append("")

    for fmt_name in ("p5", "p7", "s100"):
        if fmt_name not in cells:
            continue
        model_cells = cells[fmt_name]
        lines.append(f"## Format `{fmt_name}`")
        lines.append("")

        for rule in TIE_RULES:
            lines.append(f"### C distribution per model (tie_rule={rule})")
            lines.append("")
            lines.append("| model | n | C=1 | C=2 | C=3 | C=4 | C=5 | None |")
            lines.append("|---|---|---|---|---|---|---|---|")
            for model in models:
                cell = model_cells.get(model)
                if cell is None:
                    continue
                dist, none_count = cell.c_dist(rule)
                lines.append(
                    f"| {model} | {cell.n_total} | {dist[1]} | {dist[2]} | "
                    f"{dist[3]} | {dist[4]} | {dist[5]} | {none_count} |"
                )
            lines.append("")

        lines.append("### Per-model means and true `passes_hidden` rate")
        lines.append("")
        lines.append(
            "| model | mean y (cond. N) | mean y_v (cond. V, contaminated, ref. only) "
            "| mean C (lower) | mean C (upper) | true rate as-is | true rate "
            "excl. extraction failures | n extracted/n total |"
        )
        lines.append("|---|---|---|---|---|---|---|---|")
        for model in models:
            cell = model_cells.get(model)
            if cell is None:
                continue
            lines.append(
                f"| {model} | {_fmt(cell.mean_y_n)} | {_fmt(cell.mean_y_v)} | "
                f"{_fmt(cell.mean_c('lower'))} | {_fmt(cell.mean_c('upper'))} | "
                f"{_fmt(cell.true_rate_as_is)} | "
                f"{_fmt(cell.true_rate_excl_extraction_failures)} | "
                f"{cell.n_extracted}/{cell.n_total} |"
            )
        lines.append("")

        lines.append(
            "### Across-model correlations (n=5 models — a 5-point correlation "
            "is extremely fragile; see CLAUDE.md's task-count reasoning, which "
            "applies with equal force here)"
        )
        lines.append("")
        lines.append("| x | true-rate variant | pearson r | spearman rho |")
        lines.append("|---|---|---|---|")

        present_models = [m for m in models if m in model_cells]
        mean_y = [model_cells[m].mean_y_n for m in present_models]
        rate_as_is = [model_cells[m].true_rate_as_is for m in present_models]
        rate_excl = [model_cells[m].true_rate_excl_extraction_failures for m in present_models]

        def _row(label: str, xs: list[float | None], rate_label: str, rates: list[float | None]) -> None:
            pairs = [(x, r) for x, r in zip(xs, rates) if x is not None and r is not None]
            if len(pairs) < len(present_models):
                lines.append(
                    f"| {label} | {rate_label} | n/a ({len(pairs)}/{len(present_models)} "
                    "models have both values) | n/a |"
                )
                return
            px, py = zip(*pairs)
            pearson, spearman = _correlate(list(px), list(py))
            lines.append(f"| {label} | {rate_label} | {_fmt(pearson)} | {_fmt(spearman)} |")

        _row("mean y (cond. N)", mean_y, "as-is", rate_as_is)
        _row("mean y (cond. N)", mean_y, "excl. extraction failures", rate_excl)
        for rule in TIE_RULES:
            mean_c = [model_cells[m].mean_c(rule) for m in present_models]
            _row(f"mean C ({rule})", mean_c, "as-is", rate_as_is)
            _row(f"mean C ({rule})", mean_c, "excl. extraction failures", rate_excl)
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    observations = resume.load_observations(config.MAIN_OBSERVATIONS_PATH)
    if not observations:
        raise SystemExit(f"No observations found at {config.MAIN_OBSERVATIONS_PATH}")

    cells = build_cells(observations)
    report = render(cells, config.MAIN_MODELS)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(report + "\n")
    print(f"Wrote {OUT_PATH}")
    print()
    print(report)


if __name__ == "__main__":
    main()
