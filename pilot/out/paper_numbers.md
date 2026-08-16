# Paper numbers — consolidated reference

Every number below is sourced from an existing report or raw file. Nothing here
was recomputed by re-running analysis code; where a derived figure was computed
for this file (e.g. a normalisation, a sum, a percentage), the source values and
the arithmetic are shown so it can be checked by hand.

---

## NOT IN THE REQUESTED LIST — flagged for the write-up

1. **Most of `C=4` in `p5` is a tolerance call, not an exact tie.** Of 291
   `compute_C` calls with all three means present, `y == z_hi` was decided by
   the 0.01 tolerance in **224 of them (77.0%)** — only a small remainder was
   an exact float equality. This is the mechanical reason condition V's `y`
   "collapses onto `z_hi`": most of the mass is *near* the ceiling, close
   enough that the tolerance (not a genuine tie) resolves it to `C=4`.
   (`main_report.md`, "Tolerance firing" §, `p5`.) In `p7` it's 230/291
   (79.0%); in `s100`, 170/291 (58.4%) — lower because a coarser absolute
   tolerance in relative terms still applies, but `s100`'s wider practical
   spread near the ceiling makes exact-tolerance hits somewhat less
   dominant. This number belongs next to any claim about `C=4` concentration.

2. **Requested monotone-pattern check across the three Claude models
   (haiku → sonnet → opus), beyond the C=4 V→R drop already noted:**
   - **`mean z_hi` decreases monotonically haiku > sonnet > opus in all three
     formats**, independently: `p5` 5.000 > 4.458 > 4.288; `p7` 6.993 > 6.339
     > 6.159; `s100` 92.661 > 88.180 > 84.766 (`main_report.md`, P3 tables).
     Since this holds independently in three different rating scales (not
     the same number viewed three ways), it is the strongest candidate for a
     genuine capability-linked pattern: less capable models rate the
     byte-identical high-quality reference solution closer to the scale's
     ceiling than more capable models do.
   - **`passes_hidden_rate` increases monotonically haiku < sonnet < opus**
     (0.650 < 0.917 < 0.933; excl. extraction failures 0.661 < 0.932 <
     0.949) — expected (more capable models write more correct code) and
     the same underlying number is reused across all three formats, so it
     is one data point, not three independent confirmations.
   - **P1 `SD across tasks` (condition N) decreases haiku > sonnet > opus in
     `p5` and `p7`** (1.029 > 0.691 > 0.550; 1.515 > 0.863 > 0.802) **but
     breaks in `s100`** (21.591 > 13.212 but 13.733 > 13.212, i.e. opus
     edges above sonnet). Worth a footnote, not a clean finding — flag as
     "holds in two of three formats" rather than a monotone result.
   - Checked and **not** monotone across haiku/sonnet/opus in any format:
     `mean z_lo`, the P4 signed gap, `mean C`, `mean y` on `s100`.

3. **`gemini-3.5-flash-lite` is INVALID under both V and R, in `p5` — this
   is a model property, not a turn-order artefact**, and the DEVLOG
   explicitly corrects an earlier draft that had claimed otherwise. Its
   anchors are `z_lo ≡ 2`, `z_hi ≡ 5` identically in `main_report.md` (V)
   and `condition_r_report.md` (R). (DEVLOG.md, 2026-08-16 "cont." entry,
   the "CORRECTION" paragraph.)

4. **The two-provider limitation is explicit and unresolved**: all five
   models are Anthropic or Google; a third provider was assessed as adding
   more between-model scale-use variance than a third same-provider model
   would, but this was never tested, and DEVLOG names it as a limitation to
   state, not a resolved design choice (DEVLOG.md, Open Questions, "the
   two-provider limitation stands").

5. **Task count (60, not DESIGN.md §10's originally planned 100) is a
   power-analysis trade-off tied to which analysis is primary.** The
   100-task figure powered the across-model correlation (now secondary,
   §8/§9 below, n=5 models regardless of task count); 60 tasks was judged
   ample for the primary per-cell `y`-distribution result (simulation: 98%
   vs 93% positive-effect rate, 100 vs 60 tasks). (DEVLOG.md, 2026-08-15
   05:20 entry; DESIGN.md §10.)

6. **Every across-model correlation in this project has n=5 (models).**
   This is stated repeatedly in the source reports as "extremely fragile"
   (`cross_condition_report.md`, `condition_r_report.md`) — flagged again
   here because it is the single most important caveat on §8 below and is
   easy to lose track of once numbers are extracted into a table.

7. **Order effects (scale direction, vignette-first order) are reported but
   not thresholded** in DESIGN.md/`main_report.md` — e.g. `p5` mean
   self-report is 3.906 ascending vs 3.807 descending for
   claude-haiku-4-5-20251001, and similar splits exist for all
   models/formats. Not requested in the list above, but a reviewer may ask
   whether label-order sensitivity (the Wang/Zhou/Liu citation, DESIGN.md
   §3) shows up in these numbers — worth a scan before submission.
   (`main_report.md`, "Order effects" § per format.)

8. **The Pinocchio Inventory resolution caveat**: `p7`'s format is adopted
   from Plisiecki et al. (arXiv:2607.20082), which aggregates 24 items per
   scale; our per-item resolution on `p7` (e.g. it cannot separate 92.0
   from 92.6 on the underlying continuous signal) does not necessarily
   apply once items are aggregated the way the original instrument does.
   This is a caveat on citing `p7` as "the established AI-welfare format"
   without qualification. (DEVLOG.md, "Related work" §, 2026-08-14 22:00
   session addendum.)

9. **Vignette design constraints**, in case the write-up needs to justify
   why the anchors can't be blamed for saturation: two vignettes (not
   three, PISA-motivated), both solve a list-partitioning problem that is
   not in the 60-task set (so rating them can't leak an answer), same
   length/style, LOW fails 2 of 7 hidden asserts (silently drops the
   remainder on non-divisible input), HIGH passes 7 of 7 — verified by
   execution, not by inspection. (DESIGN.md §7; DEVLOG.md, 2026-08-14 18:20
   and 22:00 entries.)

10. **Sample count (5 draws/question, temperature 1.0) is itself a
    calibrated design choice**, not an arbitrary default: simulated
    positive-effect rate was 87% at 1 draw, 95% at 3, 97% at 5, no
    improvement at 15 or 25 — 5 is the point of diminishing returns.
    (DESIGN.md §6.)

---

## 1. Run scope

**Main experiment** (`main_report.md`, header; `main_raw.jsonl`):
- Models (5): `claude-haiku-4-5-20251001`, `claude-sonnet-5`, `claude-opus-5`,
  `gemini-3.6-flash`, `gemini-3.5-flash-lite`
- Tasks: 60 (30 MBPP + 30 LBPP), same tasks and same generated solution reused
  across all three formats
- Formats (3): `p5` (1–5), `p7` (1–7), `s100` (0–100)
- Observations: **900** (5 × 60 × 3)
- Total raw API calls: **22,421** (`main_raw.jsonl` line count), of which 285
  belong to the abandoned `gemini-3.1-pro-preview` leg (see §9c) — **22,136**
  from the five models that make up the 900 observations
- Total spend: **$27.7315**, including the abandoned leg's $0.8067
  (DEVLOG.md, 2026-08-16 06:00 entry, per-model cost table)
- Date range: 2026-08-15T18:02:39Z – 2026-08-16T05:51:12Z
  (`main_raw.jsonl`, first/last `timestamp`)

**Condition R** (post-hoc, not preregistered) (`condition_r_report.md`;
`condition_r_raw.jsonl`):
- Same 5 models, same 60 tasks, `p5` only, solutions reused verbatim from the
  main run (no new code generation)
- Observations: **300** (5 × 60)
- Total raw API calls: **4,365** (`condition_r_raw.jsonl` line count), all
  rating calls
- Total spend: **$5.8281** (DEVLOG.md, 2026-08-16 "cont." entry)
- Date range: 2026-08-16T17:09:18Z – 2026-08-16T19:20:32Z
  (`condition_r_raw.jsonl`, first/last `timestamp`)

**Cross-condition report** (`cross_condition_report.md`): no new API calls —
re-derives `C` from the main run's existing 900 observations (condition N's
`y` crossed with condition V's anchors).

**Combined spend, main run + condition R: $33.5596.** (Pilot-phase spend is
separate and not included here; see §9 and DEVLOG.md for pilot costs if
needed for the "what didn't work" section.)

---

## 2. Cross-format GO table

Source: `main_report.md`, "Cross-format summary". Verdicts are identical for
`tie_rule=lower` and `tie_rule=upper` in every format — stated explicitly in
each format section ("Verdicts change between bound choices: **NO**"), because
no P1–P4 threshold is a function of `C`.

| Format | Width `W` | P1 | P2 | P3 | P4 | All cells Valid | GO |
|---|---|---|---|---|---|---|---|
| `p5` | 4 | PASS | PASS | PASS | **FAIL** | **FAIL** | **FAIL** |
| `p7` | 6 | PASS | PASS | PASS | **FAIL** | PASS | **PASS** |
| `s100` | 100 | PASS | PASS | PASS | **FAIL** | **FAIL** | **FAIL** |

Both `tie_rule` values give the same row in every format.

---

## 3. Validity screen per (model, format)

Source: `main_report.md`, "Validity screen (DESIGN.md §2)" table, each format
section.

| Model | `p5` | `p7` | `s100` |
|---|---|---|---|
| claude-haiku-4-5-20251001 | VALID (z_lo 1–2, z_hi 5–5) | VALID (z_lo 1.6–2, z_hi 6.6–7) | VALID (z_lo 15–23, z_hi 89.8–95) |
| claude-sonnet-5 | VALID (z_lo 1–1, z_hi 3–5) | VALID (z_lo 1–1, z_hi 4–7) | VALID (z_lo 0–4, z_hi 72.6–95) |
| claude-opus-5 | VALID (z_lo 1–1, z_hi 4–5) | VALID (z_lo 1–1, z_hi 5.6–7) | VALID (z_lo 0–3.4, z_hi 67–92) |
| gemini-3.6-flash | VALID (z_lo 1–1.4, z_hi 5–5) | VALID (z_lo 1–1.4, z_hi 7–7) | **INVALID** (z_lo ≡ 0, z_hi ≡ 100) |
| gemini-3.5-flash-lite | **INVALID** (z_lo ≡ 2, z_hi ≡ 5) | VALID (z_lo 1.8–4.8, z_hi 7–7) | VALID (z_lo 0–17, z_hi 100–100) |

Failing cells, named: `gemini-3.5-flash-lite` × `p5`; `gemini-3.6-flash` ×
`s100`. Both anchors constant to within that format's tolerance in the failing
cell, so `C` is a monotone recoding of `y` there (DESIGN.md §2) — this is why
`p5` and `s100` fail the "All cells Valid" row in §2 above and `p7` does not.

---

## 4. P1 per model per format

Source: `main_report.md`, P1 tables per format (condition N, uncontaminated).
"SD/W" is SD divided by that format's width — the way DESIGN.md §9 says P1
must be read across formats, since the raw SD numbers aren't comparable
otherwise.

| Model | Format | Distinct points | SD | Mean | SD/W |
|---|---|---|---|---|---|
| claude-haiku-4-5-20251001 | `p5` | 4 | 1.029 | 3.861 | 0.2573 |
| claude-haiku-4-5-20251001 | `p7` | 6 | 1.515 | 5.847 | 0.2525 |
| claude-haiku-4-5-20251001 | `s100` | 11 | 21.591 | 71.939 | 0.2159 |
| claude-sonnet-5 | `p5` | 4 | 0.691 | 3.749 | 0.1728 |
| claude-sonnet-5 | `p7` | 5 | 0.863 | 5.573 | 0.1438 |
| claude-sonnet-5 | `s100` | 24 | 13.212 | 78.563 | 0.1321 |
| claude-opus-5 | `p5` | 4 | 0.550 | 3.736 | 0.1375 |
| claude-opus-5 | `p7` | 5 | 0.802 | 5.417 | 0.1337 |
| claude-opus-5 | `s100` | 21 | 13.733 | 74.546 | 0.1373 |
| gemini-3.6-flash | `p5` | 4 | 1.273 | 4.226 | 0.3183 |
| gemini-3.6-flash | `p7` | 6 | 1.837 | 6.063 | 0.3062 |
| gemini-3.6-flash | `s100` | 10 | 25.762 | 88.685 | 0.2576 |
| gemini-3.5-flash-lite | `p5` | 5 | 0.791 | 4.623 | 0.1978 |
| gemini-3.5-flash-lite | `p7` | 6 | 0.828 | 6.757 | 0.1380 |
| gemini-3.5-flash-lite | `s100` | 12 | 14.855 | 95.077 | 0.1486 |

All PASS (threshold ≥3 distinct AND SD ≥ 0.075·W in every format).

---

## 5. Condition N vs V vs R

Source: `condition_r_report.md`, "Mean self-report `y`, by condition" and "C
distribution per model — condition R vs condition V" (`p5` only — condition R
was never run on `p7`/`s100`).

| Model | mean y, V (contaminated) | mean y, N | mean y, R (post-hoc) | C=4 share, V | C=4 share, R |
|---|---|---|---|---|---|
| claude-haiku-4-5-20251001 | 5.000 | 3.861 | 3.831 | 1.000 | 0.237 |
| claude-sonnet-5 | 4.075 | 3.749 | 3.790 | 0.475 | 0.186 |
| claude-opus-5 | 4.092 | 3.736 | 3.776 | 0.475 | 0.475 |
| gemini-3.6-flash | 4.793 | 4.226 | 4.222 | 0.926 | 0.611 |
| gemini-3.5-flash-lite | 4.993 | 4.623 | 4.607 | 0.983 | 0.733 |

Mean `y` under R lands close to mean `y` under N for every model (not close to
V), consistent with the turn-order explanation for V's ceiling collapse — but
this is a post-hoc, non-preregistered, single-run finding (see §9d).

---

## 6. P4 signed gap per model per format

Source: `main_report.md`, P4 tables per format (pooled, condition N vs the P4
probe). "Gap/W" divides the signed gap by that format's width; FAIL threshold
is 0.1875·W in every format.

| Model | Format | Signed gap (self − other) | Gap/W | Verdict |
|---|---|---|---|---|
| claude-haiku-4-5-20251001 | `p5` | 0.054 | 0.0135 | PASS |
| claude-haiku-4-5-20251001 | `p7` | 0.247 | 0.0412 | PASS |
| claude-haiku-4-5-20251001 | `s100` | 2.169 | 0.0217 | PASS |
| claude-sonnet-5 | `p5` | 0.314 | 0.0785 | PASS |
| claude-sonnet-5 | `p7` | 0.400 | 0.0667 | PASS |
| claude-sonnet-5 | `s100` | 11.738 | 0.1174 | PASS |
| claude-opus-5 | `p5` | 0.007 | 0.0018 | PASS |
| claude-opus-5 | `p7` | 0.214 | 0.0357 | PASS |
| claude-opus-5 | `s100` | 6.380 | 0.0638 | PASS |
| gemini-3.6-flash | `p5` | 0.589 | 0.1473 | PASS |
| gemini-3.6-flash | `p7` | 0.944 | 0.1573 | PASS |
| gemini-3.6-flash | `s100` | 22.981 | 0.2298 | **FAIL** |
| gemini-3.5-flash-lite | `p5` | 0.827 | 0.2068 | **FAIL** |
| gemini-3.5-flash-lite | `p7` | 1.333 | 0.2222 | **FAIL** |
| gemini-3.5-flash-lite | `s100` | 26.867 | 0.2687 | **FAIL** |

P4 fails at least one model in every format; it never blocks GO by design
(DESIGN.md §9) but is a named limitation in all three formats.

---

## 7. Ground truth per model

Source: `cross_condition_report.md`, "Per-model means and true `passes_hidden`
rate" (identical figures in every format section, since codegen/ground truth
is computed once per (model, task) and shared — confirmed by comparing the
`p5`/`p7`/`s100` sections of that file).

| Model | passes_hidden, as-is | passes_hidden, excl. extraction failures | Tasks excluded | n extracted / n total |
|---|---|---|---|---|
| claude-haiku-4-5-20251001 | 0.650 | 0.661 | 1 | 59/60 |
| claude-sonnet-5 | 0.917 | 0.932 | 1 | 59/60 |
| claude-opus-5 | 0.933 | 0.949 | 1 | 59/60 |
| gemini-3.6-flash | 0.767 | 0.852 | 6 | 54/60 |
| gemini-3.5-flash-lite | 0.800 | 0.800 | 0 | 60/60 |

The six gemini-3.6-flash exclusions are named task IDs — see §9a.

---

## 8. Across-model correlations

n = 5 models in every row below; all figures are stated in the source reports
as fragile at this n. Two coefficients (Pearson r, Spearman ρ) × two
true-rate variants (as-is, excluding extraction failures) × the `x` variable
used.

### From `cross_condition_report.md` (condition N's `y` crossed with
condition V's anchors — the primary cross-condition diagnostic)

| Format | x | true-rate variant | Pearson r | Spearman ρ |
|---|---|---|---|---|
| `p5` | mean y (cond. N) | as-is | -0.303 | -0.600 |
| `p5` | mean y (cond. N) | excl. extraction failures | -0.276 | -0.700 |
| `p5` | mean C (lower = upper) | as-is | 0.403 | 0.200 |
| `p5` | mean C (lower = upper) | excl. extraction failures | 0.482 | 0.100 |
| `p7` | mean y (cond. N) | as-is | -0.419 | -0.600 |
| `p7` | mean y (cond. N) | excl. extraction failures | -0.433 | -0.700 |
| `p7` | mean C (lower = upper) | as-is | 0.129 | 0.100 |
| `p7` | mean C (lower = upper) | excl. extraction failures | 0.225 | 0.000 |
| `s100` | mean y (cond. N) | as-is | -0.020 | 0.100 |
| `s100` | mean y (cond. N) | excl. extraction failures | 0.049 | 0.000 |
| `s100` | mean C (lower = upper) | as-is | 0.608 | 0.600 |
| `s100` | mean C (lower = upper) | excl. extraction failures | 0.594 | 0.300 |

`tie_rule=lower` and `tie_rule=upper` give identical correlations in every row
(`cross_condition_report.md` states the C distributions are byte-identical
between bounds in every format).

### From `condition_r_report.md` (`p5` only, condition R's own `y`/anchors)

| x | true-rate variant | Pearson r | Spearman ρ |
|---|---|---|---|
| mean y (cond. R) | as-is | -0.232 | -0.600 |
| mean y (cond. R) | excl. extraction failures | -0.206 | -0.700 |
| mean C (lower, cond. R) | as-is | 0.382 | 0.200 |
| mean C (lower, cond. R) | excl. extraction failures | 0.454 | 0.100 |

**Read together**: in every format and both conditions (N-crossed-with-V, and
R), raw `y`'s correlation with true accuracy is negative and rescaled `C`'s is
positive — the sign flip the design predicts if rescaling is doing something —
but n=5, one model is INVALID in the `p5`/`s100` rows above (§3), and none of
this was preregistered as the main experiment computes no correlations at all
(DESIGN.md §9 explicitly excludes them from the pilot/main GO criteria; these
tables are the post-hoc secondary analysis DESIGN.md §10 anticipated).

---

## 9. Every artefact and deviation, with its scope

**(a) Gemini codegen ceiling — codegen only, six tasks, `gemini-3.6-flash`.**
`max_output_tokens=4096` on the Interactions API is a *combined*
thinking+output budget; Flash spent ~3,930 of 4,096 tokens thinking on these
six, leaving ~160 for code, truncating mid-function. Affected task IDs, all
three formats each (18 of the 900 observations): `mbpp/31`,
`lbpp/python/001`, `lbpp/python/002`, `lbpp/python/016`, `lbpp/python/018`,
`lbpp/python/019` (5 of 6 are LBPP). Rating draws for this model are
unaffected (0% parse/truncation failures throughout); only `passes_hidden`
(the secondary ground-truth analysis) is understated for this model.
(DEVLOG.md, 2026-08-16 06:00 entry.)

**(b) `gemini-3.1-pro-preview` dropped, replaced by `gemini-3.5-flash-lite`.**
Quota metric `generativelanguage.googleapis.com/generate_requests_per_model_per_day`,
limit **250 requests/day** — a per-model preview-tier quota, not an
account-tier limit (`gemini-3.6-flash` made 4,050+ successful calls on the
same key/project in the same window with zero errors). The leg needed ~4,560
requests and hit 68 consecutive 429s before the new `SustainedRateLimit`
guard stopped it. Nine already-written pro-preview observations were dropped
before the replacement leg (backed up as
`main_observations.jsonl.pre_gemini_prune.bak`) because resume cannot tell a
clean completed cell from one that intersected the 429 burst. Replacement
`gemini-3.5-flash-lite` is a **tier downshift** (Flash-Lite, not Pro) — no
non-preview Pro model was reachable on this key (`gemini-2.5-pro` returned 404
"no longer available to new users"), so the intended Pro/Flash cross-provider
contrast became a weaker Flash-Lite/Flash contrast. (DEVLOG.md, 2026-08-16
06:00 entry.)

**(c) Retry/backoff added for one leg only: `gemini-3.5-flash-lite`.** The
other four legs (claude-haiku-4-5, claude-sonnet-5, claude-opus-5,
gemini-3.6-flash) completed before the retry loop existed. Retry changes
whether a call *succeeds*, not what a model answers, so between-model
comparability is unaffected — stated explicitly rather than left implicit.
In practice the flash-lite leg needed zero retries. (DEVLOG.md, 2026-08-16
06:00 entry.)

**(d) Condition R and the cross-condition analysis are post-hoc, not
preregistered.** Neither is in DESIGN.md. Both were authorised the same day
(2026-08-16) after `main_report.md`'s headline finding that condition V's `y`
collapses onto `z_hi` for several models. `cross_condition_report.md` builds
`C` from condition N's `y` (uncontaminated but anchor-free) and condition V's
anchors (anchored but contaminated `y`) — `compute_C` itself is unmodified,
only its input columns differ, which is why this was authorised on Sonnet
rather than Opus (see CLAUDE.md's model-routing clarification, 2026-08-16).
Condition R reverses V's turn order (self-question first, then vignettes),
`p5` only, all 5 main-run models, reusing main-run solutions — no new code
generation. Neither should be read as a corrected result; DEVLOG.md's own
closing instruction is "do not interpret condition R as a finding."

**(e) The Opus 5 thinking-block issue and its fix.** `claude-opus-5` emits an
unrequested `ThinkingBlock` ahead of its answer on a minority of rating calls
even with extended thinking off by default (CLAUDE.md's "off by default"
claim, verified true for Haiku 4.5 and Sonnet 4.6, does **not** hold for Opus
5). First smoke run: 52/128 rating calls crashed on
`response.content[0].text` indexing; the token-budget half was worse — the
thinking block could consume the entire `max_output_tokens_rating` (8),
leaving zero room for a digit, which would have silently read as ~40% of Opus
5's ratings being parse failures rather than a bug. Fixed by (1) `_first_text()`
scanning for the first text block instead of indexing block 0, and (2)
sending `thinking: {"type": "disabled"}` explicitly on rating calls. Caught in
a smoke test before the main run; at full scale this would have contaminated
**4,560 calls** (one fifth of the run). (DEVLOG.md, 2026-08-15 05:20 entry.)

**(f) Cache minimums and why caching was near-worthless.** Minimum cacheable
prompt length: 512 tokens (Opus 5), 1,024 (Sonnet 5, Sonnet 4.6), 2,048 (Opus
4.7), 4,096 (Opus 4.6/4.5, Haiku 4.5, all Gemini 3.x). The reused prefix in
this design is ~1,150 tokens, so of the five main-run models only **Opus 5
and Sonnet 5 clear their minimum at all**; the other three cache 0 tokens by
construction (verified: 0 written/0 read in every non-Opus-5, non-Sonnet-5
row of the main run). Even where caching works, only the *opening* vignette
question in a condition-V thread is byte-identical across the 5 sampling
threads — later turns replay each thread's own ratings (the King & Wand
priming mechanism), so they can never be reused. Measured on Opus 5: 3,229
tokens written / 12,916 read on one task, saving 18.2% of that cell's cost.
Caching was left enabled for every model regardless, because a sub-minimum
prompt is processed uncached with no error and no write premium — a
breakpoint that never fires costs nothing. (DEVLOG.md, 2026-08-15 04:20 and
05:20 entries.)

---

## 10. Source-file index

| Number group | Source file(s) |
|---|---|
| Cross-format GO table, validity screen, P1–P4 per format, order effects, C distribution, diagnostics, tolerance firing | `pilot/out/main_report.md` |
| Ground truth (as-is / excl. extraction), cross-condition C distribution, across-model correlations (N×V) | `pilot/out/cross_condition_report.md` |
| Condition R vs V, condition-R validity screen, condition-R correlations | `pilot/out/condition_r_report.md` |
| Raw call counts, timestamps, spend narrative, all deviations/artefacts | `DEVLOG.md` (entries dated 2026-08-14 through 2026-08-16), `pilot/out/main_raw.jsonl`, `pilot/out/condition_r_raw.jsonl` |
| Thresholds, formulas, scale/format definitions, what's preregistered vs post-hoc | `DESIGN.md` §2–§10 |
