# Report

5 models x 60 tasks (30 MBPP + 30 LBPP) x 3 scale formats, 900 observations. Thresholds are DESIGN.md §9, fixed before the numbers were seen, and expressed as fractions of each format's width so they mean the same thing in all three. No interpretation is added here.

Not computed, per DESIGN.md §9: AUROC, correlations, variance ratios, significance tests.

## Cross-format summary

| Format | Width | P1 | P2 | P3 | P4 | All cells Valid | GO |
|---|---|---|---|---|---|---|---|
| `p5` | 4 | **PASS** | **PASS** | **PASS** | **FAIL** | **FAIL** | **FAIL** |
| `p7` | 6 | **PASS** | **PASS** | **PASS** | **FAIL** | **PASS** | **PASS** |
| `s100` | 100 | **PASS** | **PASS** | **PASS** | **FAIL** | **FAIL** | **FAIL** |

Verdicts above are for tie_rule=lower; the per-format sections show both bounds. A format disagreeing with another is a result about the scale, not an error to be resolved — see DESIGN.md §3.

---

# Format `p5`

Scale 1–5 (width 4), fully labelled: {1: 'Very unlikely', 2: 'Unlikely', 3: 'Uncertain', 4: 'Likely', 5: 'Very likely'}. Answer instruction: 'Reply with a single digit and nothing else — no words, no punctuation, no explanation.'. Rating token cap: 8 (overridden per model where a model cannot be stopped from reasoning: {'gemini-3.1-pro-preview': 256}).

Width-relative thresholds (DESIGN.md §9): P1 SD >= 0.3, P3 >= 0.5, P4 <= 0.75, equality tolerance 0.01.

5 models x 60 tasks, 300 observations.

## Validity screen (DESIGN.md §2)

A cell is Invalid iff BOTH anchors are constant across its observations, in which case C is a monotone recoding of y and every rank-based statistic is invariant by construction. Invalid cells are reported, not filtered: their observations remain in every table below, and an Invalid cell cannot produce a GO.

| Model | Valid | n with both anchors | z_lo range | z_hi range | Note |
|---|---|---|---|---|---|
| claude-haiku-4-5-20251001 | **VALID** | 59 | 1–2 | 5–5 | valid: anchors vary across observations (z_lo spread 1, z_hi spread 0, tolerance 0.01) |
| claude-sonnet-5 | **VALID** | 59 | 1–1 | 3–5 | valid: anchors vary across observations (z_lo spread 0, z_hi spread 2, tolerance 0.01) |
| claude-opus-5 | **VALID** | 59 | 1–1 | 4–5 | valid: anchors vary across observations (z_lo spread 0, z_hi spread 1, tolerance 0.01) |
| gemini-3.6-flash | **VALID** | 54 | 1–1.4 | 5–5 | valid: anchors vary across observations (z_lo spread 0.4, z_hi spread 0, tolerance 0.01) |
| gemini-3.5-flash-lite | **INVALID** | 60 | 2–2 | 5–5 | INVALID: both anchors constant to within tolerance 0.01 (z_lo ≡ 2, z_hi ≡ 5). C is a monotone recoding of y here, so every rank-based statistic is invariant by construction (DESIGN.md §2) and any apparent effect is an artefact of the recoding. |

## Verdict

| Criterion | Statement | tie_rule=lower | tie_rule=upper |
|---|---|---|---|
| P1 | Self-reports vary across tasks | **PASS** | **PASS** |
| P2 | Vignettes are ordered correctly | **PASS** | **PASS** |
| P3 | Models differ from each other in scale use | **PASS** | **PASS** |
| P4 | Response consistency across self/other | **FAIL** | **FAIL** |
| Validity | Every cell Valid (§2) | **FAIL** | **FAIL** |
| **GO** | Requires P1, P2, P3 and all cells Valid | **FAIL** | **FAIL** |

Verdicts change between bound choices: **NO**. No P1–P4 threshold is a function of C, so the two runs cannot disagree on a verdict; the bound choice affects the C distribution below and ambiguous_C_rate, which is where DESIGN.md §5's robustness check lives.

P4 FAILED. It does not block GO, and is recorded here as a named limitation that changes how the result must be framed.

## P1 — Self-reports vary across tasks

Threshold: >= 3 distinct scale points AND SD >= 0.3 (0.075 x width 4). Computed on condition N, the uncontaminated raw self-report; distinct points are counted over individual draws, SD over per-task means. The distinct-point count is absolute across formats and is therefore easier to clear on a finer scale — see DESIGN.md §9.

Verdict: **PASS**

| Metric | claude-haiku-4-5-20251001 | claude-sonnet-5 | claude-opus-5 | gemini-3.6-flash | gemini-3.5-flash-lite |
|---|---|---|---|---|---|
| observations with a usable self-report | 59 | 59 | 59 | 54 | 60 |
| distinct scale points used | 4 | 4 | 4 | 4 | 5 |
| SD across tasks | 1.029 | 0.691 | 0.550 | 1.273 | 0.791 |
| mean self-report | 3.861 | 3.749 | 3.736 | 4.226 | 4.623 |
| draws at 1 (Very unlikely) | 0 | 0 | 0 | 22 | 3 |
| draws at 2 (Unlikely) | 57 | 11 | 9 | 32 | 11 |
| draws at 3 (Uncertain) | 14 | 87 | 70 | 0 | 26 |
| draws at 4 (Likely) | 137 | 162 | 206 | 25 | 16 |
| draws at 5 (Very likely) | 87 | 35 | 10 | 191 | 244 |
| verdict | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** |

## P2 — Vignettes are ordered correctly

Threshold: misorder_rate <= 20% AND tie_rate <= 40%. Ties use tolerance 0.01 (0.0025 x width 4). ambiguous_C_rate is the share of observations where the lower and upper bound of C disagree; it is reported, not thresholded.

Verdict: **PASS**

| Metric | claude-haiku-4-5-20251001 | claude-sonnet-5 | claude-opus-5 | gemini-3.6-flash | gemini-3.5-flash-lite |
|---|---|---|---|---|---|
| observations with both anchors | 59 | 59 | 59 | 54 | 60 |
| clean_rate | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| tie_rate | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| misorder_rate | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| ambiguous_C_rate | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| verdict | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** |

## P3 — Models differ from each other in scale use

Threshold: >= 0.5 scale points (0.125 x width 4) apart on mean z_lo OR mean z_hi (max - min across models, within this format)

Verdict: **PASS**

| Metric | claude-haiku-4-5-20251001 | claude-sonnet-5 | claude-opus-5 | gemini-3.6-flash | gemini-3.5-flash-lite |
|---|---|---|---|---|---|
| mean z_lo | 1.512 | 1.000 | 1.000 | 1.011 | 2.000 |
| mean z_hi | 5.000 | 4.458 | 4.288 | 5.000 | 5.000 |

| Metric | Value |
|---|---|
| between-model spread in mean z_lo | 1.000 |
| between-model spread in mean z_hi | 0.712 |

## P4 — Response consistency across self/other

Threshold: |mean signed gap| <= 0.75 scale points (0.1875 x width 4). Compared against condition N, which like the probe carries no vignettes. Does not block GO; a failure is a named limitation.

Verdict: **FAIL**

| Metric | claude-haiku-4-5-20251001 | claude-sonnet-5 | claude-opus-5 | gemini-3.6-flash | gemini-3.5-flash-lite |
|---|---|---|---|---|---|
| paired observations | 59 | 58 | 59 | 54 | 60 |
| mean self-rating (condition N) | 3.861 | 3.745 | 3.736 | 4.226 | 4.623 |
| mean other-rating (P4 probe) | 3.807 | 3.431 | 3.729 | 3.637 | 3.797 |
| signed gap (self - other) | 0.054 | 0.314 | 0.007 | 0.589 | 0.827 |
| verdict | **PASS** | **PASS** | **PASS** | **PASS** | **FAIL** |

## Diagnostics

| Metric | claude-haiku-4-5-20251001 | claude-sonnet-5 | claude-opus-5 | gemini-3.6-flash | gemini-3.5-flash-lite |
|---|---|---|---|---|---|
| observations | 60 | 60 | 60 | 60 | 60 |
| rating draws | 1475 | 1475 | 1475 | 1350 | 1500 |
| parse_failure_rate | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| truncation_failure_rate | 0.0% | 0.3% | 0.0% | 0.0% | 0.0% |
| unusable_draw_rate | 0.0% | 0.3% | 0.0% | 0.0% | 0.0% |
| off_scale_rate | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| code_extraction_failure_rate | 1.7% | 1.7% | 1.7% | 10.0% | 0.0% |
| execution_failure_rate | 15.0% | 1.7% | 1.7% | 10.0% | 0.0% |
| passes_visible_rate | 73.3% | 96.7% | 96.7% | 88.3% | 83.3% |
| passes_hidden_rate (ground truth) | 0.650 | 0.917 | 0.933 | 0.767 | 0.800 |
| passes visible but fails hidden | 0.100 | 0.050 | 0.033 | 0.117 | 0.050 |
| unusable draws: y_v_draws | 0 | 0 | 0 | 0 | 0 |
| unusable draws: z_lo_draws | 0 | 0 | 0 | 0 | 0 |
| unusable draws: z_hi_draws | 0 | 0 | 0 | 0 | 0 |
| unusable draws: y_n_draws | 0 | 0 | 0 | 0 | 0 |
| unusable draws: other_draws | 0 | 5 | 0 | 0 | 0 |
| codegen rejected: syntax_error | 1 | n/a | n/a | n/a | n/a |
| codegen rejected: truncated_by_output_ceiling | n/a | 1 | 1 | 6 | n/a |

## Tolerance firing (DESIGN.md §5)

All models, one compute_C call per observation, tolerance 0.01.

| Metric | Value |
|---|---|
| compute_C calls with all three means present | 291 |
| y == z_lo decided by tolerance | 1 |
| y == z_hi decided by tolerance | 224 |
| z_lo == z_hi decided by tolerance | 0 |

## Order effects (reported, not thresholded)

| Metric | claude-haiku-4-5-20251001 | claude-sonnet-5 | claude-opus-5 | gemini-3.6-flash | gemini-3.5-flash-lite |
|---|---|---|---|---|---|
| mean self-report, ascending scale | 3.906 | 3.844 | 3.679 | 4.169 | 4.588 |
| n, ascending scale | 32 | 32 | 33 | 32 | 34 |
| mean self-report, descending scale | 3.807 | 3.637 | 3.808 | 4.309 | 4.669 |
| n, descending scale | 27 | 27 | 26 | 22 | 26 |
| mean z_lo, low vignette first | 1.722 | 1.000 | 1.000 | 1.023 | 2.000 |
| mean z_hi, low vignette first | 5.000 | 4.811 | 4.515 | 5.000 | 5.000 |
| mean z_lo, high vignette first | 1.033 | 1.000 | 1.000 | 1.000 | 2.000 |
| mean z_hi, high vignette first | 5.000 | 3.864 | 4.000 | 5.000 | 5.000 |

## Rescaled C distribution

C has five categories in every format: two anchors partition the line into five regions (DESIGN.md §5). This is not the input scale.

### tie_rule = lower

| Metric | claude-haiku-4-5-20251001 | claude-sonnet-5 | claude-opus-5 | gemini-3.6-flash | gemini-3.5-flash-lite |
|---|---|---|---|---|---|
| C computed | 59 | 59 | 59 | 54 | 60 |
| C unavailable | 1 | 1 | 1 | 6 | 0 |
| mean C | 4.000 | 3.644 | 3.814 | 3.907 | 3.983 |
| C = 1 | 0 | 0 | 0 | 0 | 0 |
| C = 2 | 0 | 0 | 0 | 1 | 0 |
| C = 3 | 0 | 26 | 21 | 3 | 1 |
| C = 4 | 59 | 28 | 28 | 50 | 59 |
| C = 5 | 0 | 5 | 10 | 0 | 0 |

### tie_rule = upper

| Metric | claude-haiku-4-5-20251001 | claude-sonnet-5 | claude-opus-5 | gemini-3.6-flash | gemini-3.5-flash-lite |
|---|---|---|---|---|---|
| C computed | 59 | 59 | 59 | 54 | 60 |
| C unavailable | 1 | 1 | 1 | 6 | 0 |
| mean C | 4.000 | 3.644 | 3.814 | 3.907 | 3.983 |
| C = 1 | 0 | 0 | 0 | 0 | 0 |
| C = 2 | 0 | 0 | 0 | 1 | 0 |
| C = 3 | 0 | 26 | 21 | 3 | 1 |
| C = 4 | 59 | 28 | 28 | 50 | 59 |
| C = 5 | 0 | 5 | 10 | 0 | 0 |

## Task-set comparison (MBPP vs LBPP)

Diagnostic only. Reuses the same P1/P2/P4/diagnostics computations as above, applied per (model, task set) instead of pooled per model. Does not feed the GO verdict.

### P1 — self-reports vary, by task set

| Metric | claude-haiku-4-5-20251001 · mbpp | claude-haiku-4-5-20251001 · lbpp | claude-sonnet-5 · mbpp | claude-sonnet-5 · lbpp | claude-opus-5 · mbpp | claude-opus-5 · lbpp | gemini-3.6-flash · mbpp | gemini-3.6-flash · lbpp | gemini-3.5-flash-lite · mbpp | gemini-3.5-flash-lite · lbpp |
|---|---|---|---|---|---|---|---|---|---|---|
| observations with a usable self-report | 30 | 29 | 29 | 30 | 29 | 30 | 29 | 25 | 30 | 30 |
| distinct scale points used | 4 | 4 | 4 | 4 | 4 | 3 | 4 | 4 | 5 | 5 |
| SD across tasks | 1.143 | 0.916 | 0.584 | 0.677 | 0.601 | 0.493 | 1.328 | 1.219 | 0.789 | 0.806 |
| mean self-report | 3.873 | 3.848 | 4.041 | 3.467 | 3.821 | 3.653 | 4.110 | 4.360 | 4.640 | 4.607 |
| draws at 1 (Very unlikely) | 0 | 0 | 0 | 0 | 0 | 0 | 12 | 10 | 1 | 2 |
| draws at 2 (Unlikely) | 35 | 22 | 1 | 10 | 5 | 4 | 23 | 9 | 8 | 3 |
| draws at 3 (Uncertain) | 2 | 12 | 20 | 67 | 26 | 44 | 0 | 0 | 10 | 16 |
| draws at 4 (Likely) | 60 | 77 | 96 | 66 | 104 | 102 | 12 | 13 | 6 | 10 |
| draws at 5 (Very likely) | 53 | 34 | 28 | 7 | 10 | 0 | 98 | 93 | 125 | 119 |
| verdict | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** |

### P2 — vignette ordering, by task set

| Metric | claude-haiku-4-5-20251001 · mbpp | claude-haiku-4-5-20251001 · lbpp | claude-sonnet-5 · mbpp | claude-sonnet-5 · lbpp | claude-opus-5 · mbpp | claude-opus-5 · lbpp | gemini-3.6-flash · mbpp | gemini-3.6-flash · lbpp | gemini-3.5-flash-lite · mbpp | gemini-3.5-flash-lite · lbpp |
|---|---|---|---|---|---|---|---|---|---|---|
| observations with both anchors | 30 | 29 | 29 | 30 | 29 | 30 | 29 | 25 | 30 | 30 |
| clean_rate | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| tie_rate | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| misorder_rate | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| ambiguous_C_rate | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| verdict | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** |

### P4 — response consistency, by task set

| Metric | claude-haiku-4-5-20251001 · mbpp | claude-haiku-4-5-20251001 · lbpp | claude-sonnet-5 · mbpp | claude-sonnet-5 · lbpp | claude-opus-5 · mbpp | claude-opus-5 · lbpp | gemini-3.6-flash · mbpp | gemini-3.6-flash · lbpp | gemini-3.5-flash-lite · mbpp | gemini-3.5-flash-lite · lbpp |
|---|---|---|---|---|---|---|---|---|---|---|
| paired observations | 30 | 29 | 29 | 29 | 29 | 30 | 29 | 25 | 30 | 30 |
| mean self-rating (condition N) | 3.873 | 3.848 | 4.041 | 3.448 | 3.821 | 3.653 | 4.110 | 4.360 | 4.640 | 4.607 |
| mean other-rating (P4 probe) | 3.760 | 3.855 | 3.731 | 3.131 | 4.097 | 3.373 | 3.455 | 3.848 | 3.907 | 3.687 |
| signed gap (self - other) | 0.113 | -0.007 | 0.310 | 0.317 | -0.276 | 0.280 | 0.655 | 0.512 | 0.733 | 0.920 |
| verdict | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** | **FAIL** |

### Diagnostics, by task set

| Metric | claude-haiku-4-5-20251001 · mbpp | claude-haiku-4-5-20251001 · lbpp | claude-sonnet-5 · mbpp | claude-sonnet-5 · lbpp | claude-opus-5 · mbpp | claude-opus-5 · lbpp | gemini-3.6-flash · mbpp | gemini-3.6-flash · lbpp | gemini-3.5-flash-lite · mbpp | gemini-3.5-flash-lite · lbpp |
|---|---|---|---|---|---|---|---|---|---|---|
| observations | 30 | 30 | 30 | 30 | 30 | 30 | 30 | 30 | 30 | 30 |
| rating draws | 750 | 725 | 725 | 750 | 725 | 750 | 725 | 625 | 750 | 750 |
| parse_failure_rate | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| truncation_failure_rate | 0.0% | 0.0% | 0.0% | 0.7% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| unusable_draw_rate | 0.0% | 0.0% | 0.0% | 0.7% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| off_scale_rate | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| code_extraction_failure_rate | 0.0% | 3.3% | 3.3% | 0.0% | 3.3% | 0.0% | 3.3% | 16.7% | 0.0% | 0.0% |
| execution_failure_rate | 13.3% | 16.7% | 3.3% | 0.0% | 3.3% | 0.0% | 3.3% | 16.7% | 0.0% | 0.0% |
| passes_visible_rate | 80.0% | 66.7% | 96.7% | 96.7% | 96.7% | 96.7% | 96.7% | 80.0% | 86.7% | 80.0% |
| passes_hidden_rate (ground truth) | 0.767 | 0.533 | 0.967 | 0.867 | 0.967 | 0.900 | 0.833 | 0.700 | 0.867 | 0.733 |
| passes visible but fails hidden | 0.033 | 0.167 | 0.000 | 0.100 | 0.000 | 0.067 | 0.133 | 0.100 | 0.033 | 0.067 |
| unusable draws: y_v_draws | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| unusable draws: z_lo_draws | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| unusable draws: z_hi_draws | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| unusable draws: y_n_draws | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| unusable draws: other_draws | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 | 0 | 0 |
| codegen rejected: syntax_error | n/a | 1 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| codegen rejected: truncated_by_output_ceiling | n/a | n/a | 1 | n/a | 1 | n/a | 1 | 5 | n/a | n/a |

---

# Format `p7`

Scale 1–7 (width 6), fully labelled: {1: 'Very unlikely', 2: 'Unlikely', 3: 'Somewhat unlikely', 4: 'Uncertain', 5: 'Somewhat likely', 6: 'Likely', 7: 'Very likely'}. Answer instruction: 'Reply with a single digit and nothing else — no words, no punctuation, no explanation.'. Rating token cap: 8 (overridden per model where a model cannot be stopped from reasoning: {'gemini-3.1-pro-preview': 256}).

Width-relative thresholds (DESIGN.md §9): P1 SD >= 0.45, P3 >= 0.75, P4 <= 1.125, equality tolerance 0.015.

5 models x 60 tasks, 300 observations.

## Validity screen (DESIGN.md §2)

A cell is Invalid iff BOTH anchors are constant across its observations, in which case C is a monotone recoding of y and every rank-based statistic is invariant by construction. Invalid cells are reported, not filtered: their observations remain in every table below, and an Invalid cell cannot produce a GO.

| Model | Valid | n with both anchors | z_lo range | z_hi range | Note |
|---|---|---|---|---|---|
| claude-haiku-4-5-20251001 | **VALID** | 59 | 1.6–2 | 6.6–7 | valid: anchors vary across observations (z_lo spread 0.4, z_hi spread 0.4, tolerance 0.015) |
| claude-sonnet-5 | **VALID** | 59 | 1–1 | 4–7 | valid: anchors vary across observations (z_lo spread 0, z_hi spread 3, tolerance 0.015) |
| claude-opus-5 | **VALID** | 59 | 1–1 | 5.6–7 | valid: anchors vary across observations (z_lo spread 0, z_hi spread 1.4, tolerance 0.015) |
| gemini-3.6-flash | **VALID** | 54 | 1–1.4 | 7–7 | valid: anchors vary across observations (z_lo spread 0.4, z_hi spread 0, tolerance 0.015) |
| gemini-3.5-flash-lite | **VALID** | 60 | 1.8–4.8 | 7–7 | valid: anchors vary across observations (z_lo spread 3, z_hi spread 0, tolerance 0.015) |

## Verdict

| Criterion | Statement | tie_rule=lower | tie_rule=upper |
|---|---|---|---|
| P1 | Self-reports vary across tasks | **PASS** | **PASS** |
| P2 | Vignettes are ordered correctly | **PASS** | **PASS** |
| P3 | Models differ from each other in scale use | **PASS** | **PASS** |
| P4 | Response consistency across self/other | **FAIL** | **FAIL** |
| Validity | Every cell Valid (§2) | **PASS** | **PASS** |
| **GO** | Requires P1, P2, P3 and all cells Valid | **PASS** | **PASS** |

Verdicts change between bound choices: **NO**. No P1–P4 threshold is a function of C, so the two runs cannot disagree on a verdict; the bound choice affects the C distribution below and ambiguous_C_rate, which is where DESIGN.md §5's robustness check lives.

P4 FAILED. It does not block GO, and is recorded here as a named limitation that changes how the result must be framed.

## P1 — Self-reports vary across tasks

Threshold: >= 3 distinct scale points AND SD >= 0.45 (0.075 x width 6). Computed on condition N, the uncontaminated raw self-report; distinct points are counted over individual draws, SD over per-task means. The distinct-point count is absolute across formats and is therefore easier to clear on a finer scale — see DESIGN.md §9.

Verdict: **PASS**

| Metric | claude-haiku-4-5-20251001 | claude-sonnet-5 | claude-opus-5 | gemini-3.6-flash | gemini-3.5-flash-lite |
|---|---|---|---|---|---|
| observations with a usable self-report | 59 | 59 | 59 | 54 | 60 |
| distinct scale points used | 6 | 5 | 5 | 6 | 6 |
| SD across tasks | 1.515 | 0.863 | 0.802 | 1.837 | 0.828 |
| mean self-report | 5.847 | 5.573 | 5.417 | 6.063 | 6.757 |
| draws at 1 (Very unlikely) | 0 | 0 | 0 | 8 | 3 |
| draws at 2 (Unlikely) | 22 | 0 | 0 | 32 | 5 |
| draws at 3 (Somewhat unlikely) | 22 | 3 | 8 | 9 | 0 |
| draws at 4 (Uncertain) | 7 | 34 | 25 | 0 | 5 |
| draws at 5 (Somewhat likely) | 12 | 85 | 108 | 2 | 3 |
| draws at 6 (Likely) | 97 | 137 | 144 | 5 | 9 |
| draws at 7 (Very likely) | 135 | 36 | 10 | 214 | 275 |
| verdict | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** |

## P2 — Vignettes are ordered correctly

Threshold: misorder_rate <= 20% AND tie_rate <= 40%. Ties use tolerance 0.015 (0.0025 x width 6). ambiguous_C_rate is the share of observations where the lower and upper bound of C disagree; it is reported, not thresholded.

Verdict: **PASS**

| Metric | claude-haiku-4-5-20251001 | claude-sonnet-5 | claude-opus-5 | gemini-3.6-flash | gemini-3.5-flash-lite |
|---|---|---|---|---|---|
| observations with both anchors | 59 | 59 | 59 | 54 | 60 |
| clean_rate | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| tie_rate | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| misorder_rate | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| ambiguous_C_rate | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| verdict | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** |

## P3 — Models differ from each other in scale use

Threshold: >= 0.75 scale points (0.125 x width 6) apart on mean z_lo OR mean z_hi (max - min across models, within this format)

Verdict: **PASS**

| Metric | claude-haiku-4-5-20251001 | claude-sonnet-5 | claude-opus-5 | gemini-3.6-flash | gemini-3.5-flash-lite |
|---|---|---|---|---|---|
| mean z_lo | 1.980 | 1.000 | 1.000 | 1.022 | 2.400 |
| mean z_hi | 6.993 | 6.339 | 6.159 | 7.000 | 7.000 |

| Metric | Value |
|---|---|
| between-model spread in mean z_lo | 1.400 |
| between-model spread in mean z_hi | 0.841 |

## P4 — Response consistency across self/other

Threshold: |mean signed gap| <= 1.125 scale points (0.1875 x width 6). Compared against condition N, which like the probe carries no vignettes. Does not block GO; a failure is a named limitation.

Verdict: **FAIL**

| Metric | claude-haiku-4-5-20251001 | claude-sonnet-5 | claude-opus-5 | gemini-3.6-flash | gemini-3.5-flash-lite |
|---|---|---|---|---|---|
| paired observations | 59 | 57 | 59 | 54 | 60 |
| mean self-rating (condition N) | 5.847 | 5.596 | 5.417 | 6.063 | 6.757 |
| mean other-rating (P4 probe) | 5.600 | 5.196 | 5.203 | 5.119 | 5.423 |
| signed gap (self - other) | 0.247 | 0.400 | 0.214 | 0.944 | 1.333 |
| verdict | **PASS** | **PASS** | **PASS** | **PASS** | **FAIL** |

## Diagnostics

| Metric | claude-haiku-4-5-20251001 | claude-sonnet-5 | claude-opus-5 | gemini-3.6-flash | gemini-3.5-flash-lite |
|---|---|---|---|---|---|
| observations | 60 | 60 | 60 | 60 | 60 |
| rating draws | 1475 | 1475 | 1475 | 1350 | 1500 |
| parse_failure_rate | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| truncation_failure_rate | 0.0% | 1.2% | 0.1% | 0.0% | 0.0% |
| unusable_draw_rate | 0.0% | 1.2% | 0.1% | 0.0% | 0.0% |
| off_scale_rate | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| code_extraction_failure_rate | 1.7% | 1.7% | 1.7% | 10.0% | 0.0% |
| execution_failure_rate | 15.0% | 1.7% | 1.7% | 10.0% | 0.0% |
| passes_visible_rate | 73.3% | 96.7% | 96.7% | 88.3% | 83.3% |
| passes_hidden_rate (ground truth) | 0.650 | 0.917 | 0.933 | 0.767 | 0.800 |
| passes visible but fails hidden | 0.100 | 0.050 | 0.033 | 0.117 | 0.050 |
| unusable draws: y_v_draws | 0 | 0 | 0 | 0 | 0 |
| unusable draws: z_lo_draws | 0 | 0 | 0 | 0 | 0 |
| unusable draws: z_hi_draws | 0 | 3 | 0 | 0 | 0 |
| unusable draws: y_n_draws | 0 | 0 | 0 | 0 | 0 |
| unusable draws: other_draws | 0 | 14 | 1 | 0 | 0 |
| codegen rejected: syntax_error | 1 | n/a | n/a | n/a | n/a |
| codegen rejected: truncated_by_output_ceiling | n/a | 1 | 1 | 6 | n/a |

## Tolerance firing (DESIGN.md §5)

All models, one compute_C call per observation, tolerance 0.015.

| Metric | Value |
|---|---|
| compute_C calls with all three means present | 291 |
| y == z_lo decided by tolerance | 0 |
| y == z_hi decided by tolerance | 230 |
| z_lo == z_hi decided by tolerance | 0 |

## Order effects (reported, not thresholded)

| Metric | claude-haiku-4-5-20251001 | claude-sonnet-5 | claude-opus-5 | gemini-3.6-flash | gemini-3.5-flash-lite |
|---|---|---|---|---|---|
| mean self-report, ascending scale | 5.744 | 5.619 | 5.218 | 6.031 | 6.818 |
| n, ascending scale | 32 | 32 | 33 | 32 | 34 |
| mean self-report, descending scale | 5.970 | 5.519 | 5.669 | 6.109 | 6.677 |
| n, descending scale | 27 | 27 | 26 | 22 | 26 |
| mean z_lo, low vignette first | 1.995 | 1.000 | 1.000 | 1.046 | 2.575 |
| mean z_hi, low vignette first | 6.990 | 6.886 | 6.309 | 7.000 | 7.000 |
| mean z_lo, high vignette first | 1.944 | 1.000 | 1.000 | 1.000 | 2.283 |
| mean z_hi, high vignette first | 7.000 | 5.418 | 5.969 | 7.000 | 7.000 |

## Rescaled C distribution

C has five categories in every format: two anchors partition the line into five regions (DESIGN.md §5). This is not the input scale.

### tie_rule = lower

| Metric | claude-haiku-4-5-20251001 | claude-sonnet-5 | claude-opus-5 | gemini-3.6-flash | gemini-3.5-flash-lite |
|---|---|---|---|---|---|
| C computed | 59 | 59 | 59 | 54 | 60 |
| C unavailable | 1 | 1 | 1 | 6 | 0 |
| mean C | 4.000 | 3.966 | 3.814 | 3.907 | 3.983 |
| C = 1 | 0 | 0 | 0 | 0 | 0 |
| C = 2 | 0 | 0 | 0 | 0 | 0 |
| C = 3 | 1 | 14 | 19 | 5 | 1 |
| C = 4 | 57 | 33 | 32 | 49 | 59 |
| C = 5 | 1 | 12 | 8 | 0 | 0 |

### tie_rule = upper

| Metric | claude-haiku-4-5-20251001 | claude-sonnet-5 | claude-opus-5 | gemini-3.6-flash | gemini-3.5-flash-lite |
|---|---|---|---|---|---|
| C computed | 59 | 59 | 59 | 54 | 60 |
| C unavailable | 1 | 1 | 1 | 6 | 0 |
| mean C | 4.000 | 3.966 | 3.814 | 3.907 | 3.983 |
| C = 1 | 0 | 0 | 0 | 0 | 0 |
| C = 2 | 0 | 0 | 0 | 0 | 0 |
| C = 3 | 1 | 14 | 19 | 5 | 1 |
| C = 4 | 57 | 33 | 32 | 49 | 59 |
| C = 5 | 1 | 12 | 8 | 0 | 0 |

## Task-set comparison (MBPP vs LBPP)

Diagnostic only. Reuses the same P1/P2/P4/diagnostics computations as above, applied per (model, task set) instead of pooled per model. Does not feed the GO verdict.

### P1 — self-reports vary, by task set

| Metric | claude-haiku-4-5-20251001 · mbpp | claude-haiku-4-5-20251001 · lbpp | claude-sonnet-5 · mbpp | claude-sonnet-5 · lbpp | claude-opus-5 · mbpp | claude-opus-5 · lbpp | gemini-3.6-flash · mbpp | gemini-3.6-flash · lbpp | gemini-3.5-flash-lite · mbpp | gemini-3.5-flash-lite · lbpp |
|---|---|---|---|---|---|---|---|---|---|---|
| observations with a usable self-report | 30 | 29 | 29 | 30 | 29 | 30 | 29 | 25 | 30 | 30 |
| distinct scale points used | 6 | 6 | 4 | 5 | 5 | 4 | 5 | 6 | 5 | 5 |
| SD across tasks | 1.653 | 1.379 | 0.745 | 0.873 | 0.820 | 0.745 | 2.019 | 1.598 | 1.037 | 0.555 |
| mean self-report | 5.747 | 5.952 | 5.883 | 5.273 | 5.621 | 5.220 | 5.828 | 6.336 | 6.687 | 6.827 |
| draws at 1 (Very unlikely) | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 4 | 3 | 0 |
| draws at 2 (Unlikely) | 14 | 8 | 0 | 0 | 0 | 0 | 23 | 9 | 4 | 1 |
| draws at 3 (Somewhat unlikely) | 13 | 9 | 0 | 3 | 5 | 3 | 7 | 2 | 0 | 0 |
| draws at 4 (Uncertain) | 4 | 3 | 9 | 25 | 5 | 20 | 0 | 0 | 0 | 5 |
| draws at 5 (Somewhat likely) | 6 | 6 | 25 | 60 | 40 | 68 | 0 | 2 | 2 | 1 |
| draws at 6 (Likely) | 42 | 55 | 85 | 52 | 85 | 59 | 3 | 2 | 5 | 4 |
| draws at 7 (Very likely) | 71 | 64 | 26 | 10 | 10 | 0 | 108 | 106 | 136 | 139 |
| verdict | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** |

### P2 — vignette ordering, by task set

| Metric | claude-haiku-4-5-20251001 · mbpp | claude-haiku-4-5-20251001 · lbpp | claude-sonnet-5 · mbpp | claude-sonnet-5 · lbpp | claude-opus-5 · mbpp | claude-opus-5 · lbpp | gemini-3.6-flash · mbpp | gemini-3.6-flash · lbpp | gemini-3.5-flash-lite · mbpp | gemini-3.5-flash-lite · lbpp |
|---|---|---|---|---|---|---|---|---|---|---|
| observations with both anchors | 30 | 29 | 29 | 30 | 29 | 30 | 29 | 25 | 30 | 30 |
| clean_rate | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| tie_rate | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| misorder_rate | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| ambiguous_C_rate | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| verdict | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** |

### P4 — response consistency, by task set

| Metric | claude-haiku-4-5-20251001 · mbpp | claude-haiku-4-5-20251001 · lbpp | claude-sonnet-5 · mbpp | claude-sonnet-5 · lbpp | claude-opus-5 · mbpp | claude-opus-5 · lbpp | gemini-3.6-flash · mbpp | gemini-3.6-flash · lbpp | gemini-3.5-flash-lite · mbpp | gemini-3.5-flash-lite · lbpp |
|---|---|---|---|---|---|---|---|---|---|---|
| paired observations | 30 | 29 | 29 | 28 | 29 | 30 | 29 | 25 | 30 | 30 |
| mean self-rating (condition N) | 5.747 | 5.952 | 5.883 | 5.300 | 5.621 | 5.220 | 5.828 | 6.336 | 6.687 | 6.827 |
| mean other-rating (P4 probe) | 5.560 | 5.641 | 5.559 | 4.821 | 5.703 | 4.720 | 4.724 | 5.576 | 5.700 | 5.147 |
| signed gap (self - other) | 0.187 | 0.310 | 0.324 | 0.479 | -0.083 | 0.500 | 1.103 | 0.760 | 0.987 | 1.680 |
| verdict | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** | **FAIL** |

### Diagnostics, by task set

| Metric | claude-haiku-4-5-20251001 · mbpp | claude-haiku-4-5-20251001 · lbpp | claude-sonnet-5 · mbpp | claude-sonnet-5 · lbpp | claude-opus-5 · mbpp | claude-opus-5 · lbpp | gemini-3.6-flash · mbpp | gemini-3.6-flash · lbpp | gemini-3.5-flash-lite · mbpp | gemini-3.5-flash-lite · lbpp |
|---|---|---|---|---|---|---|---|---|---|---|
| observations | 30 | 30 | 30 | 30 | 30 | 30 | 30 | 30 | 30 | 30 |
| rating draws | 750 | 725 | 725 | 750 | 725 | 750 | 725 | 625 | 750 | 750 |
| parse_failure_rate | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| truncation_failure_rate | 0.0% | 0.0% | 0.0% | 2.3% | 0.0% | 0.1% | 0.0% | 0.0% | 0.0% | 0.0% |
| unusable_draw_rate | 0.0% | 0.0% | 0.0% | 2.3% | 0.0% | 0.1% | 0.0% | 0.0% | 0.0% | 0.0% |
| off_scale_rate | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| code_extraction_failure_rate | 0.0% | 3.3% | 3.3% | 0.0% | 3.3% | 0.0% | 3.3% | 16.7% | 0.0% | 0.0% |
| execution_failure_rate | 13.3% | 16.7% | 3.3% | 0.0% | 3.3% | 0.0% | 3.3% | 16.7% | 0.0% | 0.0% |
| passes_visible_rate | 80.0% | 66.7% | 96.7% | 96.7% | 96.7% | 96.7% | 96.7% | 80.0% | 86.7% | 80.0% |
| passes_hidden_rate (ground truth) | 0.767 | 0.533 | 0.967 | 0.867 | 0.967 | 0.900 | 0.833 | 0.700 | 0.867 | 0.733 |
| passes visible but fails hidden | 0.033 | 0.167 | 0.000 | 0.100 | 0.000 | 0.067 | 0.133 | 0.100 | 0.033 | 0.067 |
| unusable draws: y_v_draws | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| unusable draws: z_lo_draws | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| unusable draws: z_hi_draws | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 |
| unusable draws: y_n_draws | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| unusable draws: other_draws | 0 | 0 | 0 | 14 | 0 | 1 | 0 | 0 | 0 | 0 |
| codegen rejected: syntax_error | n/a | 1 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| codegen rejected: truncated_by_output_ceiling | n/a | n/a | 1 | n/a | 1 | n/a | 1 | 5 | n/a | n/a |

---

# Format `s100`

Scale 0–100 (width 100), endpoints labelled only: {0: 'Very unlikely', 100: 'Very likely'}. Answer instruction: 'Reply with a single integer from 0 to 100 and nothing else — no words, no punctuation, no explanation.'. Rating token cap: 16 (overridden per model where a model cannot be stopped from reasoning: {'gemini-3.1-pro-preview': 256}).

Width-relative thresholds (DESIGN.md §9): P1 SD >= 7.5, P3 >= 12.5, P4 <= 18.75, equality tolerance 0.25.

5 models x 60 tasks, 300 observations.

## Validity screen (DESIGN.md §2)

A cell is Invalid iff BOTH anchors are constant across its observations, in which case C is a monotone recoding of y and every rank-based statistic is invariant by construction. Invalid cells are reported, not filtered: their observations remain in every table below, and an Invalid cell cannot produce a GO.

| Model | Valid | n with both anchors | z_lo range | z_hi range | Note |
|---|---|---|---|---|---|
| claude-haiku-4-5-20251001 | **VALID** | 59 | 15–23 | 89.8–95 | valid: anchors vary across observations (z_lo spread 8, z_hi spread 5.2, tolerance 0.25) |
| claude-sonnet-5 | **VALID** | 59 | 0–4 | 72.6–95 | valid: anchors vary across observations (z_lo spread 4, z_hi spread 22.4, tolerance 0.25) |
| claude-opus-5 | **VALID** | 59 | 0–3.4 | 67–92 | valid: anchors vary across observations (z_lo spread 3.4, z_hi spread 25, tolerance 0.25) |
| gemini-3.6-flash | **INVALID** | 54 | 0–0 | 100–100 | INVALID: both anchors constant to within tolerance 0.25 (z_lo ≡ 0, z_hi ≡ 100). C is a monotone recoding of y here, so every rank-based statistic is invariant by construction (DESIGN.md §2) and any apparent effect is an artefact of the recoding. |
| gemini-3.5-flash-lite | **VALID** | 60 | 0–17 | 100–100 | valid: anchors vary across observations (z_lo spread 17, z_hi spread 0, tolerance 0.25) |

## Verdict

| Criterion | Statement | tie_rule=lower | tie_rule=upper |
|---|---|---|---|
| P1 | Self-reports vary across tasks | **PASS** | **PASS** |
| P2 | Vignettes are ordered correctly | **PASS** | **PASS** |
| P3 | Models differ from each other in scale use | **PASS** | **PASS** |
| P4 | Response consistency across self/other | **FAIL** | **FAIL** |
| Validity | Every cell Valid (§2) | **FAIL** | **FAIL** |
| **GO** | Requires P1, P2, P3 and all cells Valid | **FAIL** | **FAIL** |

Verdicts change between bound choices: **NO**. No P1–P4 threshold is a function of C, so the two runs cannot disagree on a verdict; the bound choice affects the C distribution below and ambiguous_C_rate, which is where DESIGN.md §5's robustness check lives.

P4 FAILED. It does not block GO, and is recorded here as a named limitation that changes how the result must be framed.

## P1 — Self-reports vary across tasks

Threshold: >= 3 distinct scale points AND SD >= 7.5 (0.075 x width 100). Computed on condition N, the uncontaminated raw self-report; distinct points are counted over individual draws, SD over per-task means. The distinct-point count is absolute across formats and is therefore easier to clear on a finer scale — see DESIGN.md §9.

Verdict: **PASS**

| Metric | claude-haiku-4-5-20251001 | claude-sonnet-5 | claude-opus-5 | gemini-3.6-flash | gemini-3.5-flash-lite |
|---|---|---|---|---|---|
| observations with a usable self-report | 59 | 59 | 59 | 54 | 60 |
| distinct scale points used | 11 | 24 | 21 | 10 | 12 |
| SD across tasks | 21.591 | 13.212 | 13.733 | 25.762 | 14.855 |
| mean self-report | 71.939 | 78.563 | 74.546 | 88.685 | 95.077 |
| draw range (min-max) | 15-95 | 35-100 | 20-95 | 0-100 | 0-100 |
| distinct per-task means | 26 | 44 | 38 | 17 | 12 |
| verdict | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** |

## P2 — Vignettes are ordered correctly

Threshold: misorder_rate <= 20% AND tie_rate <= 40%. Ties use tolerance 0.25 (0.0025 x width 100). ambiguous_C_rate is the share of observations where the lower and upper bound of C disagree; it is reported, not thresholded.

Verdict: **PASS**

| Metric | claude-haiku-4-5-20251001 | claude-sonnet-5 | claude-opus-5 | gemini-3.6-flash | gemini-3.5-flash-lite |
|---|---|---|---|---|---|
| observations with both anchors | 59 | 59 | 59 | 54 | 60 |
| clean_rate | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| tie_rate | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| misorder_rate | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| ambiguous_C_rate | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| verdict | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** |

## P3 — Models differ from each other in scale use

Threshold: >= 12.5 scale points (0.125 x width 100) apart on mean z_lo OR mean z_hi (max - min across models, within this format)

Verdict: **PASS**

| Metric | claude-haiku-4-5-20251001 | claude-sonnet-5 | claude-opus-5 | gemini-3.6-flash | gemini-3.5-flash-lite |
|---|---|---|---|---|---|
| mean z_lo | 15.915 | 1.217 | 2.614 | 0.000 | 2.083 |
| mean z_hi | 92.661 | 88.180 | 84.766 | 100.000 | 100.000 |

| Metric | Value |
|---|---|
| between-model spread in mean z_lo | 15.915 |
| between-model spread in mean z_hi | 15.234 |

## P4 — Response consistency across self/other

Threshold: |mean signed gap| <= 18.75 scale points (0.1875 x width 100). Compared against condition N, which like the probe carries no vignettes. Does not block GO; a failure is a named limitation.

Verdict: **FAIL**

| Metric | claude-haiku-4-5-20251001 | claude-sonnet-5 | claude-opus-5 | gemini-3.6-flash | gemini-3.5-flash-lite |
|---|---|---|---|---|---|
| paired observations | 59 | 57 | 59 | 54 | 60 |
| mean self-rating (condition N) | 71.939 | 78.881 | 74.546 | 88.685 | 95.077 |
| mean other-rating (P4 probe) | 69.769 | 67.143 | 68.166 | 65.704 | 68.210 |
| signed gap (self - other) | 2.169 | 11.738 | 6.380 | 22.981 | 26.867 |
| verdict | **PASS** | **PASS** | **PASS** | **FAIL** | **FAIL** |

## Diagnostics

| Metric | claude-haiku-4-5-20251001 | claude-sonnet-5 | claude-opus-5 | gemini-3.6-flash | gemini-3.5-flash-lite |
|---|---|---|---|---|---|
| observations | 60 | 60 | 60 | 60 | 60 |
| rating draws | 1475 | 1475 | 1475 | 1350 | 1500 |
| parse_failure_rate | 0.0% | 0.1% | 0.0% | 0.0% | 0.0% |
| truncation_failure_rate | 0.0% | 1.0% | 0.0% | 0.0% | 0.0% |
| unusable_draw_rate | 0.0% | 1.1% | 0.0% | 0.0% | 0.0% |
| off_scale_rate | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| code_extraction_failure_rate | 1.7% | 1.7% | 1.7% | 10.0% | 0.0% |
| execution_failure_rate | 15.0% | 1.7% | 1.7% | 10.0% | 0.0% |
| passes_visible_rate | 73.3% | 96.7% | 96.7% | 88.3% | 83.3% |
| passes_hidden_rate (ground truth) | 0.650 | 0.917 | 0.933 | 0.767 | 0.800 |
| passes visible but fails hidden | 0.100 | 0.050 | 0.033 | 0.117 | 0.050 |
| unusable draws: y_v_draws | 0 | 3 | 0 | 0 | 0 |
| unusable draws: z_lo_draws | 0 | 1 | 0 | 0 | 0 |
| unusable draws: z_hi_draws | 0 | 1 | 0 | 0 | 0 |
| unusable draws: y_n_draws | 0 | 0 | 0 | 0 | 0 |
| unusable draws: other_draws | 0 | 11 | 0 | 0 | 0 |
| codegen rejected: syntax_error | 1 | n/a | n/a | n/a | n/a |
| codegen rejected: truncated_by_output_ceiling | n/a | 1 | 1 | 6 | n/a |

## Tolerance firing (DESIGN.md §5)

All models, one compute_C call per observation, tolerance 0.25.

| Metric | Value |
|---|---|
| compute_C calls with all three means present | 291 |
| y == z_lo decided by tolerance | 1 |
| y == z_hi decided by tolerance | 170 |
| z_lo == z_hi decided by tolerance | 0 |

## Order effects (reported, not thresholded)

| Metric | claude-haiku-4-5-20251001 | claude-sonnet-5 | claude-opus-5 | gemini-3.6-flash | gemini-3.5-flash-lite |
|---|---|---|---|---|---|
| mean self-report, ascending scale | 69.213 | 79.456 | 70.624 | 87.031 | 96.471 |
| n, ascending scale | 32 | 32 | 33 | 32 | 34 |
| mean self-report, descending scale | 75.170 | 77.504 | 79.523 | 91.091 | 93.254 |
| n, descending scale | 27 | 27 | 26 | 22 | 26 |
| mean z_lo, low vignette first | 16.317 | 0.514 | 2.442 | 0.000 | 1.250 |
| mean z_hi, low vignette first | 92.380 | 89.514 | 89.200 | 100.000 | 100.000 |
| mean z_lo, high vignette first | 15.000 | 2.400 | 2.831 | 0.000 | 2.639 |
| mean z_hi, high vignette first | 93.300 | 85.936 | 79.138 | 100.000 | 100.000 |

## Rescaled C distribution

C has five categories in every format: two anchors partition the line into five regions (DESIGN.md §5). This is not the input scale.

### tie_rule = lower

| Metric | claude-haiku-4-5-20251001 | claude-sonnet-5 | claude-opus-5 | gemini-3.6-flash | gemini-3.5-flash-lite |
|---|---|---|---|---|---|
| C computed | 59 | 59 | 59 | 54 | 60 |
| C unavailable | 1 | 1 | 1 | 6 | 0 |
| mean C | 3.746 | 3.356 | 3.949 | 3.944 | 3.983 |
| C = 1 | 0 | 0 | 0 | 0 | 0 |
| C = 2 | 0 | 0 | 0 | 1 | 0 |
| C = 3 | 20 | 40 | 27 | 1 | 1 |
| C = 4 | 34 | 17 | 8 | 52 | 59 |
| C = 5 | 5 | 2 | 24 | 0 | 0 |

### tie_rule = upper

| Metric | claude-haiku-4-5-20251001 | claude-sonnet-5 | claude-opus-5 | gemini-3.6-flash | gemini-3.5-flash-lite |
|---|---|---|---|---|---|
| C computed | 59 | 59 | 59 | 54 | 60 |
| C unavailable | 1 | 1 | 1 | 6 | 0 |
| mean C | 3.746 | 3.356 | 3.949 | 3.944 | 3.983 |
| C = 1 | 0 | 0 | 0 | 0 | 0 |
| C = 2 | 0 | 0 | 0 | 1 | 0 |
| C = 3 | 20 | 40 | 27 | 1 | 1 |
| C = 4 | 34 | 17 | 8 | 52 | 59 |
| C = 5 | 5 | 2 | 24 | 0 | 0 |

## Task-set comparison (MBPP vs LBPP)

Diagnostic only. Reuses the same P1/P2/P4/diagnostics computations as above, applied per (model, task set) instead of pooled per model. Does not feed the GO verdict.

### P1 — self-reports vary, by task set

| Metric | claude-haiku-4-5-20251001 · mbpp | claude-haiku-4-5-20251001 · lbpp | claude-sonnet-5 · mbpp | claude-sonnet-5 · lbpp | claude-opus-5 · mbpp | claude-opus-5 · lbpp | gemini-3.6-flash · mbpp | gemini-3.6-flash · lbpp | gemini-3.5-flash-lite · mbpp | gemini-3.5-flash-lite · lbpp |
|---|---|---|---|---|---|---|---|---|---|---|
| observations with a usable self-report | 30 | 29 | 29 | 30 | 29 | 30 | 29 | 25 | 30 | 30 |
| distinct scale points used | 9 | 10 | 15 | 22 | 13 | 18 | 10 | 8 | 11 | 6 |
| SD across tasks | 23.134 | 20.281 | 12.113 | 12.573 | 12.013 | 14.193 | 30.588 | 18.822 | 20.032 | 5.409 |
| mean self-report | 71.840 | 72.041 | 83.572 | 73.720 | 78.848 | 70.387 | 85.931 | 91.880 | 92.093 | 98.060 |
| draw range (min-max) | 15-95 | 15-95 | 40-100 | 35-98 | 40-95 | 20-88 | 0-100 | 0-100 | 0-100 | 0-100 |
| distinct per-task means | 18 | 17 | 22 | 27 | 18 | 26 | 11 | 11 | 7 | 7 |
| verdict | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** | **FAIL** |

### P2 — vignette ordering, by task set

| Metric | claude-haiku-4-5-20251001 · mbpp | claude-haiku-4-5-20251001 · lbpp | claude-sonnet-5 · mbpp | claude-sonnet-5 · lbpp | claude-opus-5 · mbpp | claude-opus-5 · lbpp | gemini-3.6-flash · mbpp | gemini-3.6-flash · lbpp | gemini-3.5-flash-lite · mbpp | gemini-3.5-flash-lite · lbpp |
|---|---|---|---|---|---|---|---|---|---|---|
| observations with both anchors | 30 | 29 | 29 | 30 | 29 | 30 | 29 | 25 | 30 | 30 |
| clean_rate | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| tie_rate | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| misorder_rate | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| ambiguous_C_rate | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| verdict | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** |

### P4 — response consistency, by task set

| Metric | claude-haiku-4-5-20251001 · mbpp | claude-haiku-4-5-20251001 · lbpp | claude-sonnet-5 · mbpp | claude-sonnet-5 · lbpp | claude-opus-5 · mbpp | claude-opus-5 · lbpp | gemini-3.6-flash · mbpp | gemini-3.6-flash · lbpp | gemini-3.5-flash-lite · mbpp | gemini-3.5-flash-lite · lbpp |
|---|---|---|---|---|---|---|---|---|---|---|
| paired observations | 30 | 29 | 29 | 28 | 29 | 30 | 29 | 25 | 30 | 30 |
| mean self-rating (condition N) | 71.840 | 72.041 | 83.572 | 74.021 | 78.848 | 70.387 | 85.931 | 91.880 | 92.093 | 98.060 |
| mean other-rating (P4 probe) | 67.040 | 72.593 | 72.566 | 61.527 | 77.428 | 59.213 | 61.310 | 70.800 | 73.787 | 62.633 |
| signed gap (self - other) | 4.800 | -0.552 | 11.007 | 12.495 | 1.421 | 11.173 | 24.621 | 21.080 | 18.307 | 35.427 |
| verdict | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** | **FAIL** | **FAIL** | **PASS** | **FAIL** |

### Diagnostics, by task set

| Metric | claude-haiku-4-5-20251001 · mbpp | claude-haiku-4-5-20251001 · lbpp | claude-sonnet-5 · mbpp | claude-sonnet-5 · lbpp | claude-opus-5 · mbpp | claude-opus-5 · lbpp | gemini-3.6-flash · mbpp | gemini-3.6-flash · lbpp | gemini-3.5-flash-lite · mbpp | gemini-3.5-flash-lite · lbpp |
|---|---|---|---|---|---|---|---|---|---|---|
| observations | 30 | 30 | 30 | 30 | 30 | 30 | 30 | 30 | 30 | 30 |
| rating draws | 750 | 725 | 725 | 750 | 725 | 750 | 725 | 625 | 750 | 750 |
| parse_failure_rate | 0.0% | 0.0% | 0.0% | 0.1% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| truncation_failure_rate | 0.0% | 0.0% | 0.1% | 1.9% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| unusable_draw_rate | 0.0% | 0.0% | 0.1% | 2.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| off_scale_rate | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| code_extraction_failure_rate | 0.0% | 3.3% | 3.3% | 0.0% | 3.3% | 0.0% | 3.3% | 16.7% | 0.0% | 0.0% |
| execution_failure_rate | 13.3% | 16.7% | 3.3% | 0.0% | 3.3% | 0.0% | 3.3% | 16.7% | 0.0% | 0.0% |
| passes_visible_rate | 80.0% | 66.7% | 96.7% | 96.7% | 96.7% | 96.7% | 96.7% | 80.0% | 86.7% | 80.0% |
| passes_hidden_rate (ground truth) | 0.767 | 0.533 | 0.967 | 0.867 | 0.967 | 0.900 | 0.833 | 0.700 | 0.867 | 0.733 |
| passes visible but fails hidden | 0.033 | 0.167 | 0.000 | 0.100 | 0.000 | 0.067 | 0.133 | 0.100 | 0.033 | 0.067 |
| unusable draws: y_v_draws | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 |
| unusable draws: z_lo_draws | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| unusable draws: z_hi_draws | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| unusable draws: y_n_draws | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| unusable draws: other_draws | 0 | 0 | 0 | 11 | 0 | 0 | 0 | 0 | 0 | 0 |
| codegen rejected: syntax_error | n/a | 1 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| codegen rejected: truncated_by_output_ceiling | n/a | n/a | 1 | n/a | 1 | n/a | 1 | 5 | n/a | n/a |

