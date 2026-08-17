# Cross-condition rescaling diagnostic (post-hoc, 2026-08-16)

**THIS IS A DEVIATION FROM THE PREREGISTERED DESIGN. `C` HERE IS BUILT FROM `y` (CONDITION N) AND `z_lo`/`z_hi` (CONDITION V) — TWO DIFFERENT ELICITATION CONTEXTS. THIS IS A DIAGNOSTIC, NOT A RESULT.** It exists only because condition V's own `y` collapses onto the high anchor for several models (see `pilot/out/main_report.md`), which makes it unusable to show what rescaling does. `pilot/rescale.py::compute_C` is unmodified; only the input columns are new. See the DEVLOG entry authorising this script.

## Format `p5`

### C distribution per model (tie_rule=lower)

| model | n | C=1 | C=2 | C=3 | C=4 | C=5 | None |
|---|---|---|---|---|---|---|---|
| claude-haiku-4-5-20251001 | 60 | 0 | 4 | 41 | 14 | 0 | 1 |
| claude-sonnet-5 | 60 | 0 | 0 | 39 | 13 | 7 | 1 |
| claude-opus-5 | 60 | 0 | 0 | 31 | 26 | 2 | 1 |
| gemini-3.6-flash | 60 | 0 | 1 | 17 | 36 | 0 | 6 |
| gemini-3.5-flash-lite | 60 | 0 | 1 | 14 | 45 | 0 | 0 |

### C distribution per model (tie_rule=upper)

| model | n | C=1 | C=2 | C=3 | C=4 | C=5 | None |
|---|---|---|---|---|---|---|---|
| claude-haiku-4-5-20251001 | 60 | 0 | 4 | 41 | 14 | 0 | 1 |
| claude-sonnet-5 | 60 | 0 | 0 | 39 | 13 | 7 | 1 |
| claude-opus-5 | 60 | 0 | 0 | 31 | 26 | 2 | 1 |
| gemini-3.6-flash | 60 | 0 | 1 | 17 | 36 | 0 | 6 |
| gemini-3.5-flash-lite | 60 | 0 | 1 | 14 | 45 | 0 | 0 |

### Per-model means and true `passes_hidden` rate

| model | mean y (cond. N) | mean y_v (cond. V, contaminated, ref. only) | mean C (lower) | mean C (upper) | true rate as-is | true rate excl. extraction failures | n extracted/n total |
|---|---|---|---|---|---|---|---|
| claude-haiku-4-5-20251001 | 3.861 | 5.000 | 3.169 | 3.169 | 0.650 | 0.661 | 59/60 |
| claude-sonnet-5 | 3.749 | 4.075 | 3.458 | 3.458 | 0.917 | 0.932 | 59/60 |
| claude-opus-5 | 3.736 | 4.092 | 3.508 | 3.508 | 0.933 | 0.949 | 59/60 |
| gemini-3.6-flash | 4.226 | 4.793 | 3.648 | 3.648 | 0.767 | 0.852 | 54/60 |
| gemini-3.5-flash-lite | 4.623 | 4.993 | 3.733 | 3.733 | 0.800 | 0.800 | 60/60 |

### Across-model correlations (n=5 models — a 5-point correlation is extremely fragile; see CLAUDE.md's task-count reasoning, which applies with equal force here)

| x | true-rate variant | pearson r | spearman rho |
|---|---|---|---|
| mean y (cond. N) | as-is | -0.303 | -0.600 |
| mean y (cond. N) | excl. extraction failures | -0.276 | -0.700 |
| mean C (lower) | as-is | 0.403 | 0.200 |
| mean C (lower) | excl. extraction failures | 0.482 | 0.100 |
| mean C (upper) | as-is | 0.403 | 0.200 |
| mean C (upper) | excl. extraction failures | 0.482 | 0.100 |

## Format `p7`

### C distribution per model (tie_rule=lower)

| model | n | C=1 | C=2 | C=3 | C=4 | C=5 | None |
|---|---|---|---|---|---|---|---|
| claude-haiku-4-5-20251001 | 60 | 0 | 2 | 35 | 22 | 0 | 1 |
| claude-sonnet-5 | 60 | 0 | 0 | 40 | 5 | 14 | 1 |
| claude-opus-5 | 60 | 0 | 0 | 34 | 24 | 1 | 1 |
| gemini-3.6-flash | 60 | 0 | 0 | 15 | 39 | 0 | 6 |
| gemini-3.5-flash-lite | 60 | 1 | 0 | 10 | 49 | 0 | 0 |

### C distribution per model (tie_rule=upper)

| model | n | C=1 | C=2 | C=3 | C=4 | C=5 | None |
|---|---|---|---|---|---|---|---|
| claude-haiku-4-5-20251001 | 60 | 0 | 2 | 35 | 22 | 0 | 1 |
| claude-sonnet-5 | 60 | 0 | 0 | 40 | 5 | 14 | 1 |
| claude-opus-5 | 60 | 0 | 0 | 34 | 24 | 1 | 1 |
| gemini-3.6-flash | 60 | 0 | 0 | 15 | 39 | 0 | 6 |
| gemini-3.5-flash-lite | 60 | 1 | 0 | 10 | 49 | 0 | 0 |

### Per-model means and true `passes_hidden` rate

| model | mean y (cond. N) | mean y_v (cond. V, contaminated, ref. only) | mean C (lower) | mean C (upper) | true rate as-is | true rate excl. extraction failures | n extracted/n total |
|---|---|---|---|---|---|---|---|
| claude-haiku-4-5-20251001 | 5.847 | 6.993 | 3.339 | 3.339 | 0.650 | 0.661 | 59/60 |
| claude-sonnet-5 | 5.573 | 6.414 | 3.559 | 3.559 | 0.917 | 0.932 | 59/60 |
| claude-opus-5 | 5.417 | 5.861 | 3.441 | 3.441 | 0.933 | 0.949 | 59/60 |
| gemini-3.6-flash | 6.063 | 6.696 | 3.722 | 3.722 | 0.767 | 0.852 | 54/60 |
| gemini-3.5-flash-lite | 6.757 | 6.980 | 3.783 | 3.783 | 0.800 | 0.800 | 60/60 |

### Across-model correlations (n=5 models — a 5-point correlation is extremely fragile; see CLAUDE.md's task-count reasoning, which applies with equal force here)

| x | true-rate variant | pearson r | spearman rho |
|---|---|---|---|
| mean y (cond. N) | as-is | -0.419 | -0.600 |
| mean y (cond. N) | excl. extraction failures | -0.433 | -0.700 |
| mean C (lower) | as-is | 0.129 | 0.100 |
| mean C (lower) | excl. extraction failures | 0.225 | 0.000 |
| mean C (upper) | as-is | 0.129 | 0.100 |
| mean C (upper) | excl. extraction failures | 0.225 | 0.000 |

## Format `s100`

### C distribution per model (tie_rule=lower)

| model | n | C=1 | C=2 | C=3 | C=4 | C=5 | None |
|---|---|---|---|---|---|---|---|
| claude-haiku-4-5-20251001 | 60 | 2 | 0 | 54 | 2 | 1 | 1 |
| claude-sonnet-5 | 60 | 0 | 0 | 43 | 0 | 16 | 1 |
| claude-opus-5 | 60 | 0 | 0 | 43 | 3 | 13 | 1 |
| gemini-3.6-flash | 60 | 0 | 1 | 26 | 27 | 0 | 6 |
| gemini-3.5-flash-lite | 60 | 0 | 0 | 12 | 48 | 0 | 0 |

### C distribution per model (tie_rule=upper)

| model | n | C=1 | C=2 | C=3 | C=4 | C=5 | None |
|---|---|---|---|---|---|---|---|
| claude-haiku-4-5-20251001 | 60 | 2 | 0 | 54 | 2 | 1 | 1 |
| claude-sonnet-5 | 60 | 0 | 0 | 43 | 0 | 16 | 1 |
| claude-opus-5 | 60 | 0 | 0 | 43 | 3 | 13 | 1 |
| gemini-3.6-flash | 60 | 0 | 1 | 26 | 27 | 0 | 6 |
| gemini-3.5-flash-lite | 60 | 0 | 0 | 12 | 48 | 0 | 0 |

### Per-model means and true `passes_hidden` rate

| model | mean y (cond. N) | mean y_v (cond. V, contaminated, ref. only) | mean C (lower) | mean C (upper) | true rate as-is | true rate excl. extraction failures | n extracted/n total |
|---|---|---|---|---|---|---|---|
| claude-haiku-4-5-20251001 | 71.939 | 92.400 | 3.000 | 3.000 | 0.650 | 0.661 | 59/60 |
| claude-sonnet-5 | 78.563 | 83.836 | 3.542 | 3.542 | 0.917 | 0.932 | 59/60 |
| claude-opus-5 | 74.546 | 83.441 | 3.492 | 3.492 | 0.933 | 0.949 | 59/60 |
| gemini-3.6-flash | 88.685 | 97.037 | 3.481 | 3.481 | 0.767 | 0.852 | 54/60 |
| gemini-3.5-flash-lite | 95.077 | 99.000 | 3.800 | 3.800 | 0.800 | 0.800 | 60/60 |

### Across-model correlations (n=5 models — a 5-point correlation is extremely fragile; see CLAUDE.md's task-count reasoning, which applies with equal force here)

| x | true-rate variant | pearson r | spearman rho |
|---|---|---|---|
| mean y (cond. N) | as-is | -0.020 | 0.100 |
| mean y (cond. N) | excl. extraction failures | 0.049 | 0.000 |
| mean C (lower) | as-is | 0.608 | 0.600 |
| mean C (lower) | excl. extraction failures | 0.594 | 0.300 |
| mean C (upper) | as-is | 0.608 | 0.600 |
| mean C (upper) | excl. extraction failures | 0.594 | 0.300 |

