"""Builds the four submission figures from pilot output data. NO API CALLS.

Every number plotted is computed here at run time from
`pilot/out/main_observations.jsonl` and `pilot/out/condition_r_observations.jsonl`
(both read-only) — nothing is copied in from the paper text or from
`paper_numbers.md`. Figure 4's correlations reuse the already-authorised
`Cell`/`build_cells`/`_correlate` logic in `cross_condition_report.py` and
`condition_r_report.py` (same cross-condition pairing those reports use) rather
than reimplementing it. `pilot/rescale.py::compute_C` is not called directly
here and is not modified.

Writes 300 dpi PNGs to `pilot/out/figures/`.

Usage:
    python3 build_figures.py
"""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import condition_r_report as crr
import cross_condition_report as ccr
from pilot import analyze, config, resume

FIG_DIR = config.OUT_DIR / "figures"
FIG_WIDTH_IN = 6.3  # single column of an A4 document, ~16cm at typical margins

MODEL_ORDER = config.MAIN_MODELS
MODEL_LABELS = {
    "claude-haiku-4-5-20251001": "Haiku 4.5",
    "claude-sonnet-5": "Sonnet 5",
    "claude-opus-5": "Opus 5",
    "gemini-3.6-flash": "Gemini 3.6\nFlash",
    "gemini-3.5-flash-lite": "Gemini 3.5\nFlash-Lite",
}
FORMAT_ORDER = ("p5", "p7", "s100")
FORMAT_LABELS = {"p5": "1–5", "p7": "1–7", "s100": "0–100"}

# Paul Tol's muted qualitative palette (colourblind-safe; deliberately not
# matplotlib's default blue/orange).
TOL = {
    "indigo": "#332288",
    "cyan": "#88CCEE",
    "teal": "#44AA99",
    "green": "#117733",
    "olive": "#999933",
    "sand": "#DDCC77",
    "rose": "#CC6677",
    "wine": "#882255",
    "purple": "#AA4499",
}

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": False,
        "axes.titlesize": 9,
        "legend.fontsize": 7.5,
        "savefig.dpi": 300,
        "figure.dpi": 300,
    }
)


def _mean_se(values: list[float]) -> tuple[float, float]:
    n = len(values)
    mean = sum(values) / n
    if n < 2:
        return mean, 0.0
    variance = sum((v - mean) ** 2 for v in values) / (n - 1)
    return mean, (variance**0.5) / (n**0.5)


def fig1_validity(observations: list[analyze.Observation]):
    by_format = analyze._by_format(observations)
    valid_of = {}  # model -> fmt -> bool
    for fmt_name in FORMAT_ORDER:
        scale = config.SCALE_FORMATS[fmt_name]
        grouped = analyze._by_model(by_format[fmt_name])
        for v in analyze._validity(grouped, scale):
            valid_of.setdefault(v.model, {})[fmt_name] = v.valid

    models = list(MODEL_ORDER)
    grid = np.array(
        [[1.0 if valid_of[m][f] else 0.0 for f in FORMAT_ORDER] for m in models]
    )

    fig, ax = plt.subplots(figsize=(FIG_WIDTH_IN, 0.6 + 0.5 * len(models)))
    cmap = matplotlib.colors.ListedColormap([TOL["wine"], TOL["green"]])
    ax.imshow(grid, cmap=cmap, vmin=0, vmax=1, aspect="auto")

    for i in range(grid.shape[0]):
        for j in range(grid.shape[1]):
            label = "Valid" if grid[i, j] == 1 else "Invalid"
            ax.text(j, i, label, ha="center", va="center", color="white", fontsize=8)

    ax.set_xticks(range(len(FORMAT_ORDER)))
    ax.set_xticklabels([f"{f} ({FORMAT_LABELS[f]})" for f in FORMAT_ORDER])
    ax.set_yticks(range(len(models)))
    ax.set_yticklabels([MODEL_LABELS[m].replace("\n", " ") for m in models])
    ax.set_xlabel("Scale format")
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_title("Validity screen (DESIGN.md §2): both anchors\nconstant within tolerance ⇒ Invalid")
    fig.tight_layout()
    path = FIG_DIR / "figure1_validity_screen.png"
    fig.savefig(path)
    plt.close(fig)
    return path


def fig2_self_assessment_p5(
    main_observations: list[analyze.Observation],
    r_observations: list[analyze.Observation],
):
    p5_obs = [o for o in main_observations if o.scale_format == "p5"]
    by_model = analyze._by_model(p5_obs)
    r_by_model = analyze._by_model(r_observations)

    conditions = [
        ("N", "y_n_draws", by_model, TOL["teal"]),
        ("V", "y_v_draws", by_model, TOL["rose"]),
        ("R", "y_r_draws", r_by_model, TOL["indigo"]),
    ]

    models = list(MODEL_ORDER)
    x = np.arange(len(models))
    width = 0.25

    fig, ax = plt.subplots(figsize=(FIG_WIDTH_IN, 3.6))
    for i, (label, field, source, color) in enumerate(conditions):
        means, ses = [], []
        for m in models:
            values = [
                v
                for v in (analyze._mean(o, field) for o in source.get(m, []))
                if v is not None
            ]
            mean, se = _mean_se(values)
            means.append(mean)
            ses.append(se)
        offset = (i - 1) * width
        ax.bar(
            x + offset,
            means,
            width,
            yerr=ses,
            label=label,
            color=color,
            capsize=2,
            error_kw={"elinewidth": 0.8},
        )

    ax.set_xticks(x)
    ax.set_xticklabels([MODEL_LABELS[m] for m in models])
    ax.set_ylabel("Mean self-assessment (p5 scale, 1–5)")
    ax.set_xlabel("Model")
    ax.set_ylim(1, 5.75)
    ax.legend(
        title="Condition",
        frameon=False,
        ncol=3,
        loc="upper center",
        bbox_to_anchor=(0.5, 1.16),
    )
    fig.tight_layout()
    path = FIG_DIR / "figure2_self_assessment_p5.png"
    fig.savefig(path)
    plt.close(fig)
    return path


def fig3_self_other_gap(main_observations: list[analyze.Observation]):
    by_format = analyze._by_format(main_observations)
    models = list(MODEL_ORDER)
    x = np.arange(len(models))
    width = 0.25
    colors = {"p5": TOL["cyan"], "p7": TOL["sand"], "s100": TOL["purple"]}

    fig, ax = plt.subplots(figsize=(FIG_WIDTH_IN, 3.6))
    for i, fmt_name in enumerate(FORMAT_ORDER):
        scale = config.SCALE_FORMATS[fmt_name]
        grouped = analyze._by_model(by_format[fmt_name])
        per_model = analyze._p4(grouped, scale).per_model
        gaps_over_w = []
        for m in models:
            signed_gap = per_model[m]["signed gap (self - other)"]
            gaps_over_w.append(signed_gap / scale.width if signed_gap is not None else 0.0)
        offset = (i - 1) * width
        ax.bar(
            x + offset,
            gaps_over_w,
            width,
            label=f"{fmt_name} ({FORMAT_LABELS[fmt_name]})",
            color=colors[fmt_name],
        )

    threshold = config.P4_MAX_ABS_GAP_FRACTION_OF_WIDTH
    ax.axhline(threshold, linestyle="--", color=TOL["wine"], linewidth=1, label=f"P4 FAIL threshold (±{threshold:g})")
    ax.axhline(-threshold, linestyle="--", color=TOL["wine"], linewidth=1)
    ax.axhline(0, color="black", linewidth=0.6)

    ax.set_xticks(x)
    ax.set_xticklabels([MODEL_LABELS[m] for m in models])
    ax.set_ylabel("(Self − other) gap / scale width")
    ax.set_xlabel("Model")
    ax.legend(frameon=False, loc="center left", bbox_to_anchor=(1.0, 0.5))
    fig.tight_layout()
    path = FIG_DIR / "figure3_self_other_gap.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def fig4_confidence_accuracy_correlation(
    main_observations: list[analyze.Observation],
    r_observations: list[analyze.Observation],
):
    cells_by_format = ccr.build_cells(main_observations)
    models = config.MAIN_MODELS

    group_labels = []
    raw_vals = []
    rescaled_vals = []

    for fmt_name in FORMAT_ORDER:
        model_cells = cells_by_format[fmt_name]
        present = [m for m in models if m in model_cells]
        mean_y = [model_cells[m].mean_y_n for m in present]
        mean_c = [model_cells[m].mean_c("lower") for m in present]
        rate = [model_cells[m].true_rate_excl_extraction_failures for m in present]
        raw_r, _ = ccr._correlate(mean_y, rate)
        rescaled_r, _ = ccr._correlate(mean_c, rate)
        group_labels.append(f"{fmt_name}\n({FORMAT_LABELS[fmt_name]})")
        raw_vals.append(raw_r)
        rescaled_vals.append(rescaled_r)

    main_p5 = [o for o in main_observations if o.scale_format == "p5"]
    r_cells = crr.build_cells(main_p5, r_observations, models)
    present = [m for m in models if m in r_cells]
    mean_y_r = [r_cells[m].mean_y_r for m in present]
    mean_c_r = [r_cells[m].mean_c("r") for m in present]
    rate_r = [r_cells[m].true_rate_excl_extraction_failures for m in present]
    raw_r_val, _ = crr._correlate(mean_y_r, rate_r)
    rescaled_r_val, _ = crr._correlate(mean_c_r, rate_r)
    group_labels.append("R\n(p5, reversed\nturn order)")
    raw_vals.append(raw_r_val)
    rescaled_vals.append(rescaled_r_val)

    x = np.arange(len(group_labels))
    width = 0.32

    fig, ax = plt.subplots(figsize=(FIG_WIDTH_IN, 3.6))
    ax.bar(x - width / 2, raw_vals, width, label="Raw self-report", color=TOL["olive"])
    ax.bar(x + width / 2, rescaled_vals, width, label="Rescaled (C)", color=TOL["teal"])
    ax.axhline(0, color="black", linewidth=0.6)
    ax.set_xticks(x)
    ax.set_xticklabels(group_labels)
    ax.set_ylabel("Pearson r (confidence vs. true accuracy)")
    ax.set_xlabel("Format / condition")
    ax.legend(frameon=False)
    fig.tight_layout()
    path = FIG_DIR / "figure4_confidence_accuracy_correlation.png"
    fig.savefig(path)
    plt.close(fig)
    return path


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    main_observations = resume.load_observations(config.MAIN_OBSERVATIONS_PATH)
    if not main_observations:
        raise SystemExit(f"No observations found at {config.MAIN_OBSERVATIONS_PATH}")

    r_observations = resume.load_observations(config.CONDITION_R_OBSERVATIONS_PATH)
    if not r_observations:
        raise SystemExit(f"No observations found at {config.CONDITION_R_OBSERVATIONS_PATH}")

    paths = [
        fig1_validity(main_observations),
        fig2_self_assessment_p5(main_observations, r_observations),
        fig3_self_other_gap(main_observations),
        fig4_confidence_accuracy_correlation(main_observations, r_observations),
    ]
    for p in paths:
        print(f"Wrote {p}")


if __name__ == "__main__":
    main()
