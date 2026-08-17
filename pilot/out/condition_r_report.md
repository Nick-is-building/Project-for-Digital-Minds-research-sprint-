# Condition R vs condition V, p5 only (post-hoc, 2026-08-16)

**CONDITION R IS NOT PREREGISTERED (not in DESIGN.md).** It reverses condition V's turn order — self-question FIRST, then both vignettes — everything else held identical: wording, p5 scale, 5 models, 60 tasks, reused solutions, randomised presentation per (model, task). `pilot/rescale.py::compute_C` is unmodified; see the DEVLOG entry authorising this script and `run_condition_r.py`.

## C distribution per model — condition R vs condition V

| model | condition | n | C=1 | C=2 | C=3 | C=4 | C=5 | None | share C=4 |
|---|---|---|---|---|---|---|---|---|---|
| claude-haiku-4-5-20251001 | V (main run) | 60 | 0 | 0 | 0 | 59 | 0 | 1 | 1.000 |
| claude-haiku-4-5-20251001 | R (post-hoc) | 60 | 0 | 3 | 42 | 14 | 0 | 1 | 0.237 |
| claude-sonnet-5 | V (main run) | 60 | 0 | 0 | 26 | 28 | 5 | 1 | 0.475 |
| claude-sonnet-5 | R (post-hoc) | 60 | 0 | 0 | 44 | 11 | 4 | 1 | 0.186 |
| claude-opus-5 | V (main run) | 60 | 0 | 0 | 21 | 28 | 10 | 1 | 0.475 |
| claude-opus-5 | R (post-hoc) | 60 | 0 | 0 | 27 | 28 | 4 | 1 | 0.475 |
| gemini-3.6-flash | V (main run) | 60 | 0 | 1 | 3 | 50 | 0 | 6 | 0.926 |
| gemini-3.6-flash | R (post-hoc) | 60 | 0 | 0 | 21 | 33 | 0 | 6 | 0.611 |
| gemini-3.5-flash-lite | V (main run) | 60 | 0 | 0 | 1 | 59 | 0 | 0 | 0.983 |
| gemini-3.5-flash-lite | R (post-hoc) | 60 | 1 | 1 | 14 | 44 | 0 | 0 | 0.733 |

## Mean self-report `y`, by condition

| model | mean y (cond. V, contaminated) | mean y (cond. N) | mean y (cond. R, post-hoc) |
|---|---|---|---|
| claude-haiku-4-5-20251001 | 5.000 | 3.861 | 3.831 |
| claude-sonnet-5 | 4.075 | 3.749 | 3.790 |
| claude-opus-5 | 4.092 | 3.736 | 3.776 |
| gemini-3.6-flash | 4.793 | 4.226 | 4.222 |
| gemini-3.5-flash-lite | 4.993 | 4.623 | 4.607 |

## Mean C and true `passes_hidden` rate

| model | mean C (V) | mean C (R) | true rate as-is | true rate excl. extraction failures | n extracted/n total |
|---|---|---|---|---|---|
| claude-haiku-4-5-20251001 | 4.000 | 3.186 | 0.650 | 0.661 | 59/60 |
| claude-sonnet-5 | 3.644 | 3.322 | 0.917 | 0.932 | 59/60 |
| claude-opus-5 | 3.814 | 3.610 | 0.933 | 0.949 | 59/60 |
| gemini-3.6-flash | 3.907 | 3.611 | 0.767 | 0.852 | 54/60 |
| gemini-3.5-flash-lite | 3.983 | 3.683 | 0.800 | 0.800 | 60/60 |

## Validity screen per model under condition R (DESIGN.md §2)

`analyze._validity` is unmodified; condition R's own anchors (`z_lo_r_draws`/`z_hi_r_draws`) are relabelled to the field names it reads, nothing is recomputed.

| Model | Valid | n with both anchors | z_lo range | z_hi range | Note |
|---|---|---|---|---|---|
| claude-haiku-4-5-20251001 | **VALID** | 59 | 1–2 | 4.8–5 | valid: anchors vary across observations (z_lo spread 1, z_hi spread 0.2, tolerance 0.01) |
| claude-sonnet-5 | **VALID** | 59 | 1–1 | 3.2–5 | valid: anchors vary across observations (z_lo spread 0, z_hi spread 1.8, tolerance 0.01) |
| claude-opus-5 | **VALID** | 59 | 1–1 | 4–5 | valid: anchors vary across observations (z_lo spread 0, z_hi spread 1, tolerance 0.01) |
| gemini-3.6-flash | **VALID** | 54 | 1–1.4 | 4.8–5 | valid: anchors vary across observations (z_lo spread 0.4, z_hi spread 0.2, tolerance 0.01) |
| gemini-3.5-flash-lite | **INVALID** | 60 | 2–2 | 5–5 | INVALID: both anchors constant to within tolerance 0.01 (z_lo ≡ 2, z_hi ≡ 5). C is a monotone recoding of y here, so every rank-based statistic is invariant by construction (DESIGN.md §2) and any apparent effect is an artefact of the recoding. |

## Clean across-model correlation, condition R's own y and anchors (n=5 models — a 5-point correlation is extremely fragile; see CLAUDE.md's task-count reasoning, which applies with equal force here)

| x | true-rate variant | pearson r | spearman rho |
|---|---|---|---|
| mean y (cond. R) | as-is | -0.232 | -0.600 |
| mean y (cond. R) | excl. extraction failures | -0.206 | -0.700 |
| mean C (lower, cond. R) | as-is | 0.382 | 0.200 |
| mean C (lower, cond. R) | excl. extraction failures | 0.454 | 0.100 |

