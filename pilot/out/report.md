# Pilot report

2 models x 20 tasks (10 MBPP + 10 LBPP), 40 observations. Thresholds are DESIGN.md §9, fixed before the numbers were seen. No interpretation is added here.

Not computed, per DESIGN.md §9: AUROC, correlations, variance ratios, significance tests.

## Verdict

| Criterion | Statement | tie_rule=lower | tie_rule=upper |
|---|---|---|---|
| P1 | Self-reports vary across tasks | **PASS** | **PASS** |
| P2 | Vignettes are ordered correctly | **PASS** | **PASS** |
| P3 | Models differ from each other in scale use | **PASS** | **PASS** |
| P4 | Response consistency across self/other | **FAIL** | **FAIL** |
| **GO** | Requires P1, P2 and P3 | **PASS** | **PASS** |

Verdicts change between bound choices: **NO**. No P1–P4 threshold is a function of C, so the two runs cannot disagree on a verdict; the bound choice affects the C distribution below and ambiguous_C_rate, which is where DESIGN.md §5's robustness check lives.

P4 FAILED. It does not block GO, and is recorded here as a named limitation that changes how the result must be framed.

## P1 — Self-reports vary across tasks

Threshold: >= 3 distinct scale points AND SD >= 0.3. Computed on condition N, the uncontaminated raw self-report; distinct points are counted over individual draws, SD over per-task means.

Verdict: **PASS**

| Metric | claude-haiku-4-5-20251001 | gemini-3.6-flash |
|---|---|---|
| observations with a usable self-report | 20 | 18 |
| distinct scale points used | 5 | 5 |
| SD across tasks | 1.149 | 1.786 |
| mean self-report | 3.760 | 3.556 |
| draws at 1 (Very unlikely) | 3 | 28 |
| draws at 2 (Unlikely) | 19 | 4 |
| draws at 3 (Uncertain) | 6 | 1 |
| draws at 4 (Likely) | 43 | 4 |
| draws at 5 (Very likely) | 29 | 53 |
| verdict | **PASS** | **PASS** |

## P2 — Vignettes are ordered correctly

Threshold: misorder_rate <= 20% AND tie_rate <= 40%. Ties use TOLERANCE=0.01. ambiguous_C_rate is the share of observations where the lower and upper bound of C disagree; it is reported, not thresholded.

Verdict: **PASS**

| Metric | claude-haiku-4-5-20251001 | gemini-3.6-flash |
|---|---|---|
| observations with both anchors | 20 | 18 |
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
| mean z_lo | 1.560 | 1.000 |
| mean z_hi | 5.000 | 5.000 |

| Metric | Value |
|---|---|
| between-model spread in mean z_lo | 0.560 |
| between-model spread in mean z_hi | 0.000 |

## P4 — Response consistency across self/other

Threshold: |mean signed gap| <= 0.75 scale points. Compared against condition N, which like the probe carries no vignettes. Does not block GO; a failure is a named limitation.

Verdict: **FAIL**

| Metric | claude-haiku-4-5-20251001 | gemini-3.6-flash |
|---|---|---|
| paired observations | 20 | 18 |
| mean self-rating (condition N) | 3.760 | 3.556 |
| mean other-rating (P4 probe) | 3.890 | 2.733 |
| signed gap (self - other) | -0.130 | 0.822 |
| verdict | **PASS** | **FAIL** |

## Diagnostics

| Metric | claude-haiku-4-5-20251001 | gemini-3.6-flash |
|---|---|---|
| observations | 20 | 20 |
| rating draws | 500 | 450 |
| parse_failure_rate | 0.0% | 0.0% |
| off_scale_rate | 0.0% | 0.0% |
| code_extraction_failure_rate | 0.0% | 10.0% |
| execution_failure_rate | 15.0% | 45.0% |
| passes_visible_rate | 80.0% | 55.0% |
| passes_hidden_rate (ground truth) | 0.650 | 0.550 |
| passes visible but fails hidden | 0.150 | 0.000 |
| unusable draws: y_v_draws | 0 | 0 |
| unusable draws: z_lo_draws | 0 | 0 |
| unusable draws: z_hi_draws | 0 | 0 |
| unusable draws: y_n_draws | 0 | 0 |
| unusable draws: other_draws | 0 | 0 |

## Tolerance firing (DESIGN.md §5)

Counted over all models, one compute_C call per observation, TOLERANCE=0.01.

| Metric | Value |
|---|---|
| compute_C calls with all three means present | 38 |
| y == z_lo decided by tolerance | 0 |
| y == z_hi decided by tolerance | 37 |
| z_lo == z_hi decided by tolerance | 0 |

## Order effects (reported, not thresholded)

| Metric | claude-haiku-4-5-20251001 | gemini-3.6-flash |
|---|---|---|
| mean self-report, ascending scale | 3.640 | 3.273 |
| n, ascending scale | 10 | 11 |
| mean self-report, descending scale | 3.880 | 4.000 |
| n, descending scale | 10 | 7 |
| mean z_lo, low vignette first | 1.786 | 1.000 |
| mean z_hi, low vignette first | 5.000 | 5.000 |
| mean z_lo, high vignette first | 1.033 | 1.000 |
| mean z_hi, high vignette first | 5.000 | 5.000 |

## Rescaled C distribution

### tie_rule = lower

| Metric | claude-haiku-4-5-20251001 | gemini-3.6-flash |
|---|---|---|
| C computed | 20 | 18 |
| C unavailable | 0 | 2 |
| mean C | 4.000 | 3.944 |
| C = 1 | 0 | 0 |
| C = 2 | 0 | 0 |
| C = 3 | 0 | 1 |
| C = 4 | 20 | 17 |
| C = 5 | 0 | 0 |

### tie_rule = upper

| Metric | claude-haiku-4-5-20251001 | gemini-3.6-flash |
|---|---|---|
| C computed | 20 | 18 |
| C unavailable | 0 | 2 |
| mean C | 4.000 | 3.944 |
| C = 1 | 0 | 0 |
| C = 2 | 0 | 0 |
| C = 3 | 0 | 1 |
| C = 4 | 20 | 17 |
| C = 5 | 0 | 0 |

## Task-set comparison (MBPP vs LBPP)

Diagnostic only, added 2026-08-14 alongside the LBPP task set. Reuses the same P1/P2/P4/diagnostics computations as above, applied per (model, task set) instead of pooled per model, so the two halves can be compared directly. Does not feed the GO verdict, which stays computed on the pooled full set above.

### P1 — self-reports vary, by task set

| Metric | claude-haiku-4-5-20251001 · mbpp | claude-haiku-4-5-20251001 · lbpp | gemini-3.6-flash · mbpp | gemini-3.6-flash · lbpp |
|---|---|---|---|---|
| observations with a usable self-report | 10 | 10 | 10 | 8 |
| distinct scale points used | 4 | 5 | 4 | 4 |
| SD across tasks | 1.238 | 1.117 | 1.769 | 1.920 |
| mean self-report | 3.820 | 3.700 | 3.660 | 3.425 |
| draws at 1 (Very unlikely) | 0 | 3 | 13 | 15 |
| draws at 2 (Unlikely) | 12 | 7 | 4 | 0 |
| draws at 3 (Uncertain) | 5 | 1 | 0 | 1 |
| draws at 4 (Likely) | 13 | 30 | 3 | 1 |
| draws at 5 (Very likely) | 20 | 9 | 30 | 23 |
| verdict | **PASS** | **PASS** | **PASS** | **PASS** |

### P2 — vignette ordering, by task set

| Metric | claude-haiku-4-5-20251001 · mbpp | claude-haiku-4-5-20251001 · lbpp | gemini-3.6-flash · mbpp | gemini-3.6-flash · lbpp |
|---|---|---|---|---|
| observations with both anchors | 10 | 10 | 10 | 8 |
| clean_rate | 100.0% | 100.0% | 100.0% | 100.0% |
| tie_rate | 0.0% | 0.0% | 0.0% | 0.0% |
| misorder_rate | 0.0% | 0.0% | 0.0% | 0.0% |
| ambiguous_C_rate | 0.0% | 0.0% | 0.0% | 0.0% |
| verdict | **PASS** | **PASS** | **PASS** | **PASS** |

### P4 — response consistency, by task set

| Metric | claude-haiku-4-5-20251001 · mbpp | claude-haiku-4-5-20251001 · lbpp | gemini-3.6-flash · mbpp | gemini-3.6-flash · lbpp |
|---|---|---|---|---|
| paired observations | 10 | 10 | 10 | 8 |
| mean self-rating (condition N) | 3.820 | 3.700 | 3.660 | 3.425 |
| mean other-rating (P4 probe) | 4.060 | 3.720 | 3.320 | 2.000 |
| signed gap (self - other) | -0.240 | -0.020 | 0.340 | 1.425 |
| verdict | **PASS** | **PASS** | **PASS** | **FAIL** |

### Diagnostics, by task set

| Metric | claude-haiku-4-5-20251001 · mbpp | claude-haiku-4-5-20251001 · lbpp | gemini-3.6-flash · mbpp | gemini-3.6-flash · lbpp |
|---|---|---|---|---|
| observations | 10 | 10 | 10 | 10 |
| rating draws | 250 | 250 | 250 | 200 |
| parse_failure_rate | 0.0% | 0.0% | 0.0% | 0.0% |
| off_scale_rate | 0.0% | 0.0% | 0.0% | 0.0% |
| code_extraction_failure_rate | 0.0% | 0.0% | 0.0% | 20.0% |
| execution_failure_rate | 0.0% | 30.0% | 10.0% | 80.0% |
| passes_visible_rate | 90.0% | 70.0% | 90.0% | 20.0% |
| passes_hidden_rate (ground truth) | 0.800 | 0.500 | 0.900 | 0.200 |
| passes visible but fails hidden | 0.100 | 0.200 | 0.000 | 0.000 |
| unusable draws: y_v_draws | 0 | 0 | 0 | 0 |
| unusable draws: z_lo_draws | 0 | 0 | 0 | 0 |
| unusable draws: z_hi_draws | 0 | 0 | 0 | 0 |
| unusable draws: y_n_draws | 0 | 0 | 0 | 0 |
| unusable draws: other_draws | 0 | 0 | 0 | 0 |

