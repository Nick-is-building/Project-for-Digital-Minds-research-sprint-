# Pilot report

2 models x 20 tasks, 40 observations. Thresholds are DESIGN.md §9, fixed before the numbers were seen. No interpretation is added here.

Not computed, per DESIGN.md §9: AUROC, correlations, variance ratios, significance tests.

## Verdict

| Criterion | Statement | tie_rule=lower | tie_rule=upper |
|---|---|---|---|
| P1 | Self-reports vary across tasks | **PASS** | **PASS** |
| P2 | Vignettes are ordered correctly | **PASS** | **PASS** |
| P3 | Models differ from each other in scale use | **PASS** | **PASS** |
| P4 | Response consistency across self/other | **PASS** | **PASS** |
| **GO** | Requires P1, P2 and P3 | **PASS** | **PASS** |

Verdicts change between bound choices: **NO**. No P1–P4 threshold is a function of C, so the two runs cannot disagree on a verdict; the bound choice affects the C distribution below and ambiguous_C_rate, which is where DESIGN.md §5's robustness check lives.

## P1 — Self-reports vary across tasks

Threshold: >= 3 distinct scale points AND SD >= 0.3. Computed on condition N, the uncontaminated raw self-report; distinct points are counted over individual draws, SD over per-task means.

Verdict: **PASS**

| Metric | claude-haiku-4-5-20251001 | gemini-3.6-flash |
|---|---|---|
| observations with a usable self-report | 20 | 19 |
| distinct scale points used | 3 | 3 |
| SD across tasks | 1.344 | 1.491 |
| mean self-report | 4.250 | 4.337 |
| draws at 1 (Very unlikely) | 3 | 15 |
| draws at 2 (Unlikely) | 21 | 1 |
| draws at 3 (Uncertain) | 0 | 0 |
| draws at 4 (Likely) | 0 | 0 |
| draws at 5 (Very likely) | 76 | 79 |
| verdict | **PASS** | **PASS** |

## P2 — Vignettes are ordered correctly

Threshold: misorder_rate <= 20% AND tie_rate <= 40%. Ties use TOLERANCE=0.01. ambiguous_C_rate is the share of observations where the lower and upper bound of C disagree; it is reported, not thresholded.

Verdict: **PASS**

| Metric | claude-haiku-4-5-20251001 | gemini-3.6-flash |
|---|---|---|
| observations with both anchors | 20 | 19 |
| clean_rate | 100.0% | 100.0% |
| tie_rate | 0.0% | 0.0% |
| misorder_rate | 0.0% | 0.0% |
| ambiguous_C_rate | 0.0% | 0.0% |
| verdict | **PASS** | **PASS** |

## P3 — Models differ from each other in scale use

Threshold: >= 0.5 scale points apart on mean z_lo OR mean z_hi (max - min across models)

Verdict: **PASS**

| Metric | claude-haiku-4-5-20251001 | gemini-3.6-flash |
|---|---|---|
| mean z_lo | 1.890 | 1.021 |
| mean z_hi | 5.000 | 5.000 |

| Metric | Value |
|---|---|
| between-model spread in mean z_lo | 0.869 |
| between-model spread in mean z_hi | 0.000 |

## P4 — Response consistency across self/other

Threshold: |mean signed gap| <= 0.75 scale points. Compared against condition N, which like the probe carries no vignettes. Does not block GO; a failure is a named limitation.

Verdict: **PASS**

| Metric | claude-haiku-4-5-20251001 | gemini-3.6-flash |
|---|---|---|
| paired observations | 20 | 19 |
| mean self-rating (condition N) | 4.250 | 4.337 |
| mean other-rating (P4 probe) | 4.570 | 4.379 |
| signed gap (self - other) | -0.320 | -0.042 |
| verdict | **PASS** | **PASS** |

## Diagnostics

| Metric | claude-haiku-4-5-20251001 | gemini-3.6-flash |
|---|---|---|
| observations | 20 | 20 |
| rating draws | 500 | 475 |
| parse_failure_rate | 3.4% | 0.0% |
| off_scale_rate | 0.0% | 0.0% |
| code_extraction_failure_rate | 0.0% | 5.0% |
| execution_failure_rate | 10.0% | 15.0% |
| passes_visible_rate | 75.0% | 85.0% |
| passes_hidden_rate (ground truth) | 0.700 | 0.800 |
| passes visible but fails hidden | 0.050 | 0.050 |
| unusable draws: y_v_draws | 0 | 0 |
| unusable draws: z_lo_draws | 16 | 0 |
| unusable draws: z_hi_draws | 0 | 0 |
| unusable draws: y_n_draws | 0 | 0 |
| unusable draws: other_draws | 1 | 0 |

## Tolerance firing (DESIGN.md §5)

Counted over all models, one compute_C call per observation, TOLERANCE=0.01.

| Metric | Value |
|---|---|
| compute_C calls with all three means present | 39 |
| y == z_lo decided by tolerance | 0 |
| y == z_hi decided by tolerance | 36 |
| z_lo == z_hi decided by tolerance | 0 |

## Order effects (reported, not thresholded)

| Metric | claude-haiku-4-5-20251001 | gemini-3.6-flash |
|---|---|---|
| mean self-report, ascending scale | 4.160 | 4.200 |
| n, ascending scale | 10 | 10 |
| mean self-report, descending scale | 4.340 | 4.489 |
| n, descending scale | 10 | 9 |
| mean z_lo, low vignette first | 1.971 | 1.044 |
| mean z_hi, low vignette first | 5.000 | 5.000 |
| mean z_lo, high vignette first | 1.700 | 1.000 |
| mean z_hi, high vignette first | 5.000 | 5.000 |

## Rescaled C distribution

### tie_rule = lower

| Metric | claude-haiku-4-5-20251001 | gemini-3.6-flash |
|---|---|---|
| C computed | 20 | 19 |
| C unavailable | 0 | 1 |
| mean C | 4.000 | 3.842 |
| C = 1 | 0 | 0 |
| C = 2 | 0 | 0 |
| C = 3 | 0 | 3 |
| C = 4 | 20 | 16 |
| C = 5 | 0 | 0 |

### tie_rule = upper

| Metric | claude-haiku-4-5-20251001 | gemini-3.6-flash |
|---|---|---|
| C computed | 20 | 19 |
| C unavailable | 0 | 1 |
| mean C | 4.000 | 3.842 |
| C = 1 | 0 | 0 |
| C = 2 | 0 | 0 |
| C = 3 | 0 | 3 |
| C = 4 | 20 | 16 |
| C = 5 | 0 | 0 |

