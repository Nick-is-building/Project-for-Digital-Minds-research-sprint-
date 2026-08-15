# DEVLOG

Running record of every unit of work. This file is the **state carrier** between
Claude Code sessions. A new session reads this first (see CLAUDE.md) and learns
from it what exists, what was decided, what failed, and what comes next.

Newest entry goes at the **bottom**, directly above "Open Questions".

## Entry format — use exactly this

```markdown
## YYYY-MM-DD HH:MM — <model used>

**Built:** <what now exists that did not before; name the files>

**Decided:** <any choice made, and the reason it was made>

**Did not work:** <what was tried and failed, and why — never leave empty>

**State:** <what runs, what does not, what is untested>

**Next:** <the single next step>
```

Two rules that make this file worth keeping:

**"Did not work" is mandatory.** Write "nothing failed" only if that is literally
true. The submission template asks under Methods: *"What did you try that didn't
work?"* That question cannot be answered from memory on Sunday night. This file
is the primary source for that section of the paper.

**"State" must be honest about what is untested.** Code that was written but never
run is not built. Say so.

---

# Entries

## 2026-08-14 — Planning (chat session, not Claude Code)

**Built:** Nothing yet in code. Repository created on GitHub (public, MIT
licence, otherwise empty). `CLAUDE.md` and `DEVLOG.md` written.

**Decided:**

- *Research question.* Do anchoring vignettes (King & Wand 2007) correct
  response bias in LLM self-reports? Validated in a domain with checkable ground
  truth — code correctness via hidden tests. Instrument validation, not a study
  of code confidence. Precedent: Kapteyn, Smith & van Soest (2007) validated
  vignette corrections against objective measurement in humans.
- *Why this question.* Meyer, Garcia & Wulff (arXiv:2606.20205, June 2026) found
  81–90 % of between-model variance in LLM self-report instruments is directional
  response bias (humans 9–16 %). The standard survey-methodology fix has never
  been applied to LLMs; novelty check returned zero hits for "anchoring
  vignettes" across the whole arXiv corpus.
- *API models only, no GPU.* Nothing measured requires weights or activations.
  Cross-provider diversity increases the between-model scale-use variation the
  effect depends on. Also removes ~€60 of GPU cost and ~2 h of setup.
- *Models for the main run:* 5, spanning capability tiers across Anthropic and
  Google. Simulation: 5 models → effect positive in 100 % of runs; 3 → 90 %.
- *Pilot before anything else:* 2 models × 20 tasks, go/no-go on four
  assumptions (self-report varies; vignettes ordered correctly; models differ in
  scale use; response consistency across self/other).

**Did not work:**

- *A first design was mathematically broken and was discarded.* It compared raw
  vs vignette-corrected self-report **within one model with fixed vignette
  ratings**. Under fixed vignettes, `C` is a monotone recoding of the raw score,
  so all rank-based metrics are invariant. Simulation confirmed: Spearman
  0.35807 raw vs 0.35807 corrected, difference exactly 0.00000. The design would
  have produced a guaranteed null result. Fix: elicit vignette ratings **per
  context**, and make the primary comparison **across models**.
- *Brier score and ECE were considered as primary metrics and rejected.* In a
  simulated pure-noise world where the self-report carried zero information,
  Brier "improved" from 0.3577 to 0.3016 — purely because rescaling re-centres
  values on the base rate. A spurious improvement that would have been read as a
  finding. Both metrics are banned from this project.
- *Logprob-based elicitation was planned and abandoned.* The Anthropic API
  exposes no logprobs. Gemini supports them only per-model, via the native SDK
  (not the OpenAI-compat layer), and has been observed to break without notice.
  Replaced by repeated sampling at temperature 1.0, which also has the side
  benefit of producing continuous means and thereby fewer exact ties.
- *An earlier project direction — using the author's `ast-guard` repository to
  study whether blocking reward hacking induces welfare-relevant states — was
  explored and set aside.* Novelty was confirmed (zero arXiv hits for "reward
  hacking" + welfare), but the design hinged on whether an effect exists at all,
  giving it unbounded discovery risk within a 3-day window.

**State:** No code. No tests. Nothing has been run. Design validated only in
simulation, never against a real model.

**Next:** Build the pilot. Start with `config.py`, `tasks.py`, `sandbox.py`.

---

## 2026-08-14 17:54 — Sonnet (claude-sonnet-5, Claude Code)

**Built:** `CLAUDE.md` (renamed from a stray `CLAUDE-1.md`; added the rule-zero
scope section, an "API facts" section, and a "Known pitfalls" section),
`.gitignore`, `README.md`, `pilot/config.py`, `pilot/tasks.py`,
`pilot/sandbox.py`, `pilot/tests/test_sandbox.py` (5/5 passing),
`pilot/elicit.py`. Repo initialized locally and committed one module at a time.
Not built: `rescale.py`, `analyze.py`, `run_pilot.py`, vignette texts —
explicitly out of scope this session.

**Decided:**

- Pilot models: `claude-haiku-4-5-20251001` + `gemini-3.6-flash`. DESIGN.md
  left this open; user chose cost control over maximal capability spread for
  the pilot specifically (no Opus-tier or equivalent-cost models).
- Task source: MBPP test split via `google-research-datasets/mbpp`, filtered
  to tasks with ≥3 asserts, one consistent entry-point function, no setup
  code. 496/500 tasks qualified — no need for the hand-written fallback.
- Gemini calls go through the native SDK's **Interactions API**
  (`client.interactions.create`), not `models.generate_content` — Google
  rolled this out with a new auth-key format (`AQ.` prefix) since our training
  data; verified independently via web search, official docs, and SDK
  introspection before trusting it (see CLAUDE.md "API facts" and "Known
  pitfalls"). `thinking_level="minimal"` is used for rating calls only; code
  generation keeps default thinking.
- Added a per-process `MAX_CALLS` ceiling (1200) and per-call token logging
  (input/output/thought, read from actual response `usage` fields, never
  estimated) in `elicit.py`, plus `print_usage_summary()` over `raw.jsonl`.
  Not wired into an automatic end-of-run hook — there is no `run_pilot.py` to
  hook it into yet; call it manually until one exists.

**Did not work:**

- Loading MBPP via the canonical `mbpp` Hugging Face repo id fails outright
  under `datasets>=4` (a URI-parsing bug in the loader itself, not our code).
  Fixed by using the `google-research-datasets/mbpp` mirror instead.
- Three rounds of bad API keys cost most of the session's wall-clock time:
  an Anthropic key with a stray leading `s` (`ssk-ant-` instead of
  `sk-ant-`), a Google key that was a malformed concatenation of both key
  formats (`AIza-AQ.`), and then a first "corrected" Anthropic key that was
  still rejected (`401 API key is invalid`) and had to be replaced with a
  different one entirely. None of this was a code bug; each failure was
  logged correctly and immediately to `raw.jsonl` with the real error.
- A prior instruction (relayed through this session, not verified at first)
  claimed Google had migrated key formats and endpoints in ways that
  contradicted this assistant's training data. Rather than either blindly
  trusting or blindly rejecting it, it was checked against independent web
  sources, official Google docs, and the already-installed SDK's own type
  definitions before any code or documentation was changed. All of it
  checked out — Google genuinely shipped this.
- `pip install` fails outright on this VM (externally-managed Python,
  PEP 668) unless `--user --break-system-packages` is passed. Needed for
  `google-genai` and `python-dotenv`.

**State:** `pytest pilot/tests/ -v` passes 5/5. `pilot/tasks.py` verified
against a real MBPP load (20 tasks, correct visible/hidden split).
`pilot/elicit.py` verified against real API calls to both providers: one
trivial call and one throwaway rating call each. Anthropic
(`claude-haiku-4-5-20251001`): 5 calls total this session, 95 input / 10
output tokens. Gemini (`gemini-3.6-flash`): 2 calls, 75 input / 2 output
tokens, 0 thought tokens on both — confirms `thinking_level="minimal"` is
actually taking effect, not just being silently ignored. Total smoke-test
spend was a small fraction of the $0.10 budget.

Untested: `pilot/sandbox.py` has only ever run hand-written fixtures, never
real model-generated code. `elicit.py`'s code-generation profile
(`is_rating=False`) has never been called — only the rating profile has been
exercised. The full DESIGN.md §4 turn sequence (vignettes then self-question
in one context) has never been run; every smoke-test call so far has been a
single isolated question. `CallBudgetExceeded` has never actually fired.
There is no end-to-end pipeline.

**Next:** Write the `VIGNETTE_LOW` / `VIGNETTE_HIGH` texts (DESIGN.md §7,
Opus per CLAUDE.md's model-routing rule) — `rescale.py` and `run_pilot.py`
both need real vignette content to be exercised against, so nothing else in
the pipeline can be run end-to-end until these exist.

---

## 2026-08-14 18:20 — Opus (claude-opus-5, Claude Code)

**Built:** `pilot/rescale.py` (`compute_C`, plus the `tolerance_counts` /
`reset_tolerance_counts` diagnostic pair), `pilot/tests/test_rescale.py`
(22 tests), and the two vignette texts in `pilot/tasks.py` (`VIGNETTE_PROBLEM`,
`VIGNETTE_LOW_CODE`, `VIGNETTE_HIGH_CODE`, `VIGNETTE_LOW`, `VIGNETTE_HIGH`,
`VIGNETTE_HIDDEN_ASSERTS`). Still not built, deliberately: `analyze.py`,
`run_pilot.py`.

**Decided:**

- *`compute_C` uses one construction for all three ordering cases instead of
  three branches.* `y` is compared to each anchor separately and each comparison
  alone constrains `C` (`y<z_lo→{1}`, `y==z_lo→{2}`, `y>z_lo→{3,4,5}`;
  `y>z_hi→{5}`, `y==z_hi→{4}`, `y<z_hi→{1,2,3}`). Two properties earn this:
  a non-empty intersection is always a singleton and on ordered anchors
  reproduces the DESIGN.md §5 ladder exactly, equality cases included; and the
  intersection is empty **iff** `z_hi <= y <= z_lo`, i.e. exactly the tied and
  misordered cases. The degeneracy is detected by the arithmetic rather than
  tested for separately. Where the intersection is empty, `C` is the hull of the
  two constraints and `tie_rule` picks a bound.
- *A misordered anchor pair is not automatically discarded as uninformative.*
  With `z_lo=4, z_hi=2, y=5`, `y` is above both anchors and `C=5` under either
  bound; only `y` inside the crossed region `[z_hi, z_lo]` loses identification.
  Those cases return an interval whose bounds coincide. DESIGN.md §5 says
  tied/misordered `C` "is an interval", which this satisfies as a degenerate
  interval — flagged rather than treated as a contradiction, but worth a second
  pair of eyes.
- *Tolerance firing is counted in three named categories* (`y_vs_z_lo`,
  `y_vs_z_hi`, `z_lo_vs_z_hi`) plus a call count, so the rate is computable and
  the P2 tie diagnostic falls out of the same counter. The counter is
  process-global, which the docstring states explicitly.
- *`compute_C` returns `None` if any input is `None`*, propagating an upstream
  parse failure (DESIGN.md §4) rather than guessing a rating. An unknown
  `tie_rule` raises instead of silently defaulting.
- *Vignette problem: list partitioning* (`split_into_parts(items, n)`). None of
  the 20 pilot tasks (MBPP ids 11–30) involve partitioning, so rating a vignette
  cannot leak an answer. Both solutions are 9 lines with an identical
  accumulate-with-a-running-index shape, differing only in whether the remainder
  is distributed, and both texts are built from one shared `VIGNETTE_PROBLEM`
  string so the statement cannot drift between them.
- *The vignettes' hidden tests are property-based, not one exact partition.*
  "As equal in size as possible" does not fix which part receives the remainder,
  so asserting a single expected output would score a correct-but-differently-
  distributed solution as wrong.
- *`scipy` added as a dependency* for `spearmanr`, rather than hand-rolling a
  tie-corrected Spearman inside the project's most safety-critical test — a bug
  in a hand-rolled version would silently make the invariance test vacuous.
  `analyze.py` will need it anyway.

**Did not work:**

- *The invariance test as first framed could not pass, and the reason matters.*
  The natural reading — 500 fully continuous `y` values (means over 5 draws),
  constant anchors, assert `Spearman(y,truth) == Spearman(C,truth)` to 6 dp —
  is false. `C` has five categories, so applied to a continuous `y` it is a
  step function: it creates rank ties and moves Spearman through pure
  information *loss*. The exact-zero-difference result requires the recoding to
  be **injective on the observed support of `y`**, which needs `y` to take at
  most five distinct values. Fixed by drawing `y` from five attainable 5-draw
  means (1.4, 2.2, 3.0, 3.8, 4.6) with the constant anchors sitting on two of
  them (2.2, 3.8), giving a genuine non-identity but strictly rank-preserving
  recoding — difference `0.00e+00`, and `C_A` is not elementwise equal to `y`,
  so the test is not vacuous. The support-free version of the same claim is
  kept alongside as `test_constant_anchors_add_no_information`. **This is a
  caveat on the CLAUDE.md/DESIGN.md §2 framing, not a contradiction of it:**
  with a richer support, constant anchors still add no information, they merely
  coarsen. Anyone who "improves" the test to use fully continuous `y` will see
  it fail for this reason and should not weaken the assertion.
- *Deriving the bounds from the sorted `lo`/`hi` ladder alone was tried first
  and rejected.* Sorting the anchors and applying the five-case ladder is
  equivalent to King & Wand's counting form `C = 1 + 2·#{z<y} + #{z==y}`, which
  for tied anchors and `y` equal to them returns the single value 3. Both bounds
  would then be identical, "lower" and "upper" would agree by construction, and
  DESIGN.md §5's robustness check across bound choices would be vacuous rather
  than informative. The separate-constraints construction returns [2, 4] there.
- *`scipy` was not installed* and, as CLAUDE.md's known pitfalls already record,
  `pip install` needed `--user --break-system-packages` (PEP 668).
- Nothing else failed: no API calls were made this session, so no spend.

**State:** `pytest pilot/tests/ -v` passes **27/27** (22 new in
`test_rescale.py`, 5 pre-existing in `test_sandbox.py`). `test_invariance` was
mutation-checked rather than merely run: with the tie categories dropped from
`compute_C` it fails on the first assertion (raw 0.551871 vs rescaled 0.480006),
and with the anchors ignored entirely it fails on the second (constant and
per-context both 0.551871) — each caught by the assertion intended to catch it,
and the real implementation passes. Both vignettes verified by execution through
`sandbox.run_solution` against `VIGNETTE_HIDDEN_ASSERTS`: LOW fails (5 of 7
asserts pass — correct only when the length divides evenly, which is what makes
it plausible rather than absurd), HIGH passes 7 of 7. Verdicts recorded as
comments above each constant.

Untested: `compute_C` has never seen a real elicited rating — every input so far
has been synthetic. The `tolerance_counts` diagnostic is not wired into any run,
because there is still no `run_pilot.py` to reset it or report it.
`VIGNETTE_HIDDEN_ASSERTS` was verified by a one-off command, not by pytest, so
the vignettes' ground truth is not currently protected by a regression test.
`sandbox.py` has now executed hand-written vignette code but still no
model-generated code. No end-to-end pipeline; the DESIGN.md §4 turn sequence
remains unexercised.

**Next:** `run_pilot.py` — the last piece needed before anything can run
end-to-end, and the first thing that will exercise the §4 turn sequence, the
code-generation profile of `elicit.py`, and `sandbox.py` on real model output.

---

## 2026-08-14 — Claude Opus 4.7 (claude-opus-5)

**Built:** `pilot/analyze.py` and `run_pilot.py` — the pipeline now exists end to
end. `analyze.py` implements DESIGN.md §9's four criteria and nothing beyond
them, runs the whole analysis twice (once per bound choice) and writes
`out/report.md` with the two verdict columns side by side. `ambiguous_C_rate`
sits next to `misorder_rate` and `tie_rate` per the user's decision. Tolerance
firing is now counted and reported (DESIGN.md §5), closing the "nothing resets or
reports `tolerance_counts`" gap from the last entry. `run_pilot.py` drives 2
models x 20 tasks x conditions V and N plus the P4 probe, with `--dry-run`.
`elicit.py` gained `elicit_text` (returns raw text, so a reply can be replayed
verbatim as an assistant turn — `str(int)` would not preserve it) and
`parse_rating`; `elicit` is now a thin wrapper over it, so every call still logs
to `raw.jsonl` before parsing. `config.py` gained the §9 thresholds, the scale-
direction constants, `PILOT_RANDOM_SEED` and `PRICE_PER_MTOK_USD`.

**Decided:** *Condition V is sampled as 5 independent conversation threads, not 5
replays of a fixed prefix.* Each thread re-elicits both vignette ratings and then
the self-rating in one context, so the model's own anchors are in its context
when it rates itself — that is the mechanism King & Wand (2007) identify, and the
reason for CLAUDE.md's one rule. *One solution per (model, task), generated once
and reused across V, N and the P4 probe.* Forced by P4, which only means anything
if the code rated as "yours" and the code rated as "someone else's" are
byte-identical. *No AUROC, correlations, variance ratios or significance tests,*
per the user's instruction: 20 tasks makes any such number noise. *The two
bound-choice runs are reported as structurally unable to disagree on a verdict,*
because no P1–P4 threshold is a function of C; the bound choice moves the C
distribution and `ambiguous_C_rate`, which is where §5's robustness check
actually lives. *`PRICE_PER_MTOK_USD` left as `None` rather than guessed* — a
wrong constant there would silently misreport spend, and `gemini-3.6-flash`
pricing is newer than this assistant's training data. The cost summary prints
token counts and names which prices are missing.

**Did not work:** *The first `run_pilot.py` built condition V's message sequence
wrongly, and the first `--dry-run` caught it before any API spend.* The deleted
`_condition_v_thread` pre-appended both vignette questions and then spliced the
answers back with `messages.insert(2 + position + 1, ...)`. The index arithmetic
was off: call 3's prefix omitted the high-vignette question entirely, two
consecutive `assistant` turns appeared, and the high vignette text landed after
both ratings instead of before the second. Worse, the dry-run had its own copy of
the sequencing logic, so it reproduced the bug faithfully instead of exposing it
— the transcript looked plausible line by line. Fixed by making `_walk_condition_v`
the single source of truth: it builds the thread incrementally with no index
arithmetic and both the real run and the dry-run pass it a `respond` callback.
Verified programmatically afterwards, not by eye: 3 calls per thread, roles
strictly alternating u/a/u → u/a/u/a/u → u/a/u/a/u/a/u, every prefix ending on a
user turn, vignette texts at indices 2 and 4, LOW before HIGH. *A first
`analyze.py` smoke test wrote synthetic numbers to `out/report.md`*; deleted,
because a file of made-up results sitting in `out/` is exactly what gets mistaken
for data later.

**State:** `pytest pilot/tests/ -v` passes **27/27**. `python run_pilot.py
--dry-run` prints the full corrected condition-V transcript and the budget:
26 calls per (model, task) = 1 code generation + 15 condition V (5 threads x 3
questions) + 5 condition N + 5 P4 probe; x 20 tasks x 2 models = **1040 planned
calls against `MAX_CALLS` 1200, headroom 160**. `raw.jsonl` is still 8 lines —
**zero API calls and zero spend across both sessions so far.**

Untested: everything that needs a real API response. `analyze.py` has only ever
seen synthetic observations (the four criteria, orientation, off-scale exclusion,
tie/misorder/ambiguous counting and the C distribution were each exercised
against hand-built inputs, but never against elicited ratings). `run_pilot.py`
has never made a call, so the Gemini multi-turn path, `_extract_code`,
`MAX_OUTPUT_TOKENS_DEFAULT=1024` for code generation, and `sandbox.py` on
model-generated code are all unexercised. Resumability is claimed by the
append-immediately design but has never been tested by interrupting a run.

**Next:** run the real pilot — but not before the user says so; this session was
instructed to stop at the dry-run.

---

## 2026-08-14 — Claude Opus 4.7 (claude-opus-5)

**Built:** The pilot ran for real. `pilot/out/raw.jsonl` (1015 pilot calls appended
to the 8 pre-existing connectivity-test lines), `pilot/out/observations.jsonl` (40
observations), `pilot/out/report.md`, `pilot/out/run_log.txt`, and
`pilot/out/raw.pre_pilot_backup.jsonl` (the 8 pre-pilot lines, kept so pilot-only
usage can be separated from the totals the built-in summary prints).
Anthropic pricing filled in ($1.00 in / $5.00 out per Mtok, user-supplied).

**Decided:** *26 calls per (model, task), not 27* — stated and justified before
spending. There is one code-generation call per (model, task), and that single
solution is replayed into condition V, condition N and the P4 probe. §9's P4
compares byte-identical code, and an `Observation` carries one `passes_hidden`, so
a second generation would give `y_v` and `y_n` different subject matter and
different ground truths. *Gemini pricing left `None`* on the user's instruction —
no verified figure, and it will not be guessed; cost is therefore Anthropic-only.
*Resumability deliberately not built for the pilot* — a re-run costs under a
dollar. Required before the main experiment (~15,600 calls); logged.

**Did not work:** **`_orient` silently inverted every descending observation, and
the first report.md was invalid.** `_orient` applied `6 - draw` whenever
`scale_direction == "descending"`, on the assumption that descending presentation
reverses the number-to-label mapping. It does not. DESIGN.md §3 fixes the wording
(`1 = Very unlikely` ... `5 = Very likely`) and randomises only the order the five
lines are *printed* in, which is what `_scale_block` implements — a reply of `5`
means "Very likely" under both directions. Subtracting from 6 therefore flipped
the meaning of half the data. Evidence: on raw draws all **39/39** usable
observations have cleanly ordered anchors, zero misorderings; after `_orient`, all
19 descending observations become misordered. The first run reported
`misorder_rate` 50.0 % / 47.4 % — matching the descending counts (10 and 9)
exactly — and **P2 and P3 both FAILED, giving a NO-GO.** Corrected numbers:
`misorder_rate` 0.0 %, `clean_rate` 100 %, and P1–P4 all PASS, **GO**. The
tell was in the report's own order-effects table: mean self-report 4.16
(ascending) against 1.66 (descending) after orientation, a 2.5-point gap that
orientation exists to remove. Raw, those means are 4.16 / 4.20 and 4.34 / 4.49 —
no material direction effect. `_orient` is now the identity and still validates
the direction string; direction sensitivity is measured in `_order_effects` by
comparing raw means, which is what §3 asks for. Re-analysis used the saved
`observations.jsonl` and cost nothing. No test covered `_orient`; the 27 passing
tests passed before and after the fix, which is exactly why this survived to a
live run.

Also did not work: *`MAX_OUTPUT_TOKENS_RATING = 8` truncates Claude mid-sentence
and the strict parser then discards a rating the model did give.* All 17 of
Claude's parse failures are of the form `"2\n\nThe solution doesn't handle"` — a
valid digit followed by prose cut off at the token ceiling. The loss is not
random: **16 of 17 fall on the low vignette** (`z_lo`), the one question where the
model wants to explain the bug it found. No observation lost all five draws, so no
observation was dropped. The parser was left alone deliberately — relaxing it to
take the leading digit after seeing the data would be fitting the instrument to
the results.

**State:** `pytest pilot/tests/ -v` passes **27/27**. Zero API errors and zero
aborted calls across 1015 calls. Claude 520 calls / 230,591 input / 5,472 output
tokens = **$0.2581**; Gemini 495 calls / 164,899 input / 1,236 output / 12,424
thought tokens, cost not computable. Gemini made 495 rather than 520 because one
observation (task 13) failed `_extract_code` and returned after its single
generation call, skipping the other 25. Verdicts are identical under
`tie_rule="lower"` and `"upper"`, and `ambiguous_C_rate` is 0.0 %, so the two
bound choices produce byte-identical C distributions.

Two measurement-quality facts that the thresholds do not capture and that the
numbers should not be read without: **the scale is saturating at the ceiling.**
`z_hi` is exactly 5.000 for 39/39 observations, and the condition-V self-report
`y_v` is exactly 5.000 for 20/20 Claude and 16/19 Gemini observations. Because
`y_v` and `z_hi` are pinned at the same ceiling, the equality tolerance fired on
`y == z_hi` in **36 of 39** observations, so `C = 4` for 36 of them and `C` carries
almost no variation. DESIGN.md §6 predicts the opposite ("means over five draws
are continuous, which makes exact ties rare"); that prediction assumes the means
are not both at a boundary. Relatedly, P1 passes at exactly its floor — 3 distinct
points for both models, with **zero draws at 3 and 4** and the mass at 1, 2 and 5.

Untested: resumability. `analyze.py` has now run on real data, but `_orient`'s
correction is not covered by a test.

**Conclusion — read this before trusting the GO.** The pilot returned **GO on all
four preregistered criteria**, and that GO is nonetheless *not* the result. The
thresholds passed while missing the decisive fact.

*What the thresholds missed.* `z_hi` is exactly 5.000 in **39/39** observations
and the condition-V self-report `y_v` is exactly 5.000 in **36/39**. So
`y == z_hi` almost always, and `C = 4` almost everywhere. The rescaling carries
**almost no variation despite P2 being perfect** — anchors 100 % cleanly ordered,
zero ties, zero misorderings. A criterion set can be fully satisfied while the
instrument transmits nothing, because nothing in P1–P4 asks whether `C` varies.

*Root cause is NOT anchor placement.* The tempting fix — lower the high anchor so
`z_hi` sits below the ceiling — was tested by independent simulation and is
**worse**: with `y` still pinned at the ceiling, `C` collapses to a constant 5 in
**94 %** of cases. Moving the anchor cannot help while the quantity being anchored
has no variance. **The root cause is that `y` itself has no variance:** the models
are uniformly maximally confident in their own code, because MBPP tasks are too
easy for them. The ceiling is a property of the task set, not of the vignettes.

*Supporting evidence that the design itself works.* P3 found **real between-model
scale-use variation**: mean `z_lo` 1.890 (Claude) against 1.021 (Gemini), spread
0.869. Two models shown byte-identical vignettes used the scale measurably
differently. That is precisely the response bias the method exists to correct, and
it is present and measurable. It simply **cannot reach `C` while `y` is pinned at
the ceiling** — the correction has a real input and no room to act.

*P1 passed at its floor, and the shape matters more than the verdict.* 3 distinct
points for both models, **zero draws at 3 and 4**, with the mass at 1, 2 and 5.
That is a response style at the extremes, not graded confidence. P1 was written to
catch collapse to a single value; it does not catch collapse to the endpoints.

*Measurement loss.* 17 parse failures, all Claude, **16 of them on the low
vignette**: a valid digit followed by prose, truncated at
`MAX_OUTPUT_TOKENS_RATING = 8`. The parser was **deliberately not relaxed** —
taking the leading digit after seeing the data would be fitting the instrument to
its own results. Fix the token ceiling instead, before the next run.

**Next:** raise task difficulty until `y` varies — that is the one blocking issue,
and neither the vignettes nor the anchors nor the scale need touching to address
it. Do not treat the GO as licence to start the main experiment. Also still owed:
a regression test around `_orient`, and a higher `MAX_OUTPUT_TOKENS_RATING`.

---

## 2026-08-14 21:30 — Sonnet (claude-sonnet-5, Claude Code)

**Built:** A difficulty-mix task set and a reworded question, addressing the
previous entry's root cause and its two related open items.

- `pilot/tasks.py`: `_load_mbpp` (renamed from the old loader) + new
  `_load_lbpp`, loading the python subset of `CohereForAI/lbpp` (Matton et al.,
  EMNLP 2024). `Task` gains `task_set` ("mbpp"/"lbpp") and `setup_code`
  (default `""`); `task_id` is now a string (`"mbpp/11"`, `"lbpp/python/000"`)
  so the two sources can't collide in one field. `load_tasks()` now returns
  `n_mbpp + n_lbpp` concatenated instead of one uniform pull.
- `pilot/sandbox.py`: `run_solution` gains an optional `setup_code` parameter
  (default `""`, so MBPP and vignette calls are byte-identical to before). It
  strips LBPP's `from code import <fn>` line (assumes a separate module this
  sandbox doesn't have) and keeps the rest — e.g. `import numpy as np` —
  appended between the inlined solution and the asserts.
- `pilot/analyze.py`: `Observation` gains `task_set` (Sonnet, per the new
  CLAUDE.md line below); a new "Task-set comparison (MBPP vs LBPP)" section in
  `report.md` reuses `_p1`/`_p2`/`_p4`/`_diagnostics` completely unchanged,
  grouped by `"<model> · <task_set>"` instead of by model alone. `compute_C`,
  every P1–P4 threshold, and the pooled GO verdict (still computed via
  `_by_model`) are untouched.
- `run_pilot.py`: passes `task.setup_code` into all three `sandbox.run_solution`
  calls and `task.task_set` into both `Observation` constructions.
- `pilot/config.py`: `NUM_MBPP_TASKS=10` / `NUM_LBPP_TASKS=10` replace
  `NUM_PILOT_TASKS=20`; `QUESTION_VIGNETTE`/`SELF`/`OTHER` reworded to "...passes
  every test case, including edge cases?"; `ANSWER_INSTRUCTION` strengthened to
  "Reply with a single digit and nothing else — no words, no punctuation, no
  explanation."
- `DESIGN.md` §4 updated to the new wording with the reason recorded inline.
- `CLAUDE.md`: one line added to the model-routing rule, per the user —
  `analyze.py` is Opus-only for metric definitions, threshold/pass-fail logic,
  and anything feeding `compute_C`; purely additive reporting is fine on
  Sonnet if flagged here.
- `pilot/tests/test_sandbox.py`: two new tests for `setup_code` (the
  from-code-import line is stripped and ignored; other imports are honoured).

**Decided:**

- *`task_id` is a string, not an int.* MBPP's native ids (11–30) and LBPP's
  native ids (`lbpp/python/NNN`) don't share a type; prefixing both
  (`f"mbpp/{id}"`) keeps one field, globally unique, with no computation
  depending on it being numeric.
- *LBPP's `entry_point` comes from the `signature` field via
  `^\s*def\s+(\w+)\s*\(`, not from parsing a test statement.* A LBPP
  `test_list` entry is a multi-line block (setup lines, then an assert), not a
  bare `assert f(...)` like MBPP's, so MBPP's assert-parsing regex does not
  apply and `signature` is the more direct source anyway.
- *LBPP qualification bar: >= `config.LBPP_MIN_TESTS` (3) test_list entries*,
  mirroring MBPP's >=3-assert bar, plus a regex-extractable entry point. Hand-
  checked the resulting first 10 python-split tasks (ids 000–009): only numpy
  and pandas are required beyond stdlib (both installed in this venv), and
  none touch list partitioning, so rating the vignette still can't leak an
  answer into this half of the set either.
- *`setup_code` stripping lives in `sandbox.py`, not `tasks.py`.* `tasks.py`
  loads `test_setup` verbatim — "honour test_setup if present," read literally
  — and script assembly (solution + setup + asserts, one process, no separate
  `code.py` module) is already `sandbox.py`'s job.
- *The by-task-set report addition was cleared with the user as "purely
  additive reporting"* before any `analyze.py` edit, per CLAUDE.md's model-
  routing rule (Sonnet this session). Two hard boundaries were set and held:
  no changes to any P1–P4 threshold value, pass/fail logic, `compute_C`, or
  `rescale.py`. Verified by rerunning the full suite after every `analyze.py`
  edit and by never touching `_by_model` (still the sole input to the pooled
  `PilotReport`).

**Did not work:**

- *LBPP's `test_list` and `test_setup` are double-encoded, not plain values.*
  The real chain is `base64 -> zlib.decompress -> pickle.loads -> (still a
  string!) -> ast.literal_eval`. `pickle.loads` alone returns a string that
  *prints* like a Python list or a Python string with real newlines, which is
  misleading: `len()` on the post-`pickle.loads` "test_list" gave 576 (a
  string length) instead of 3 (the actual number of test entries), and the
  post-`pickle.loads` "test_setup" contained literal `\n` two-character
  escapes rather than real newlines, so a first attempt at detecting
  `"from code import"` in it silently found nothing. Both were caught before
  they reached the sandbox, by checking `type()` and length by hand rather
  than trusting a `print()` that happened to look right.
- *Nearly repeated a mistake this file already warned about.* A synthetic
  smoke test of the new by-task-set `analyze.py` code called `write_report()`
  with hand-built `Observation` objects to check it didn't crash. `write_report`
  writes to the fixed path `config.OUT_DIR / "report.md"` regardless of caller,
  so this overwrote the real pilot's `report.md` with made-up numbers — the
  exact failure mode the 2026-08-14 (condition-V ordering bug) entry already
  named ("a file of made-up results sitting in `out/` is exactly what gets
  mistaken for data later"). Caught immediately via `git status` before doing
  anything else; restored with `git checkout -- pilot/out/report.md`.
  `observations.jsonl` (the source of truth) was never touched, so no data was
  lost, but the near-miss is logged here rather than quietly fixed and
  forgotten. Any future smoke test of `analyze.py`/`write_report` should assert
  on the returned markdown string, not call it against the real `out/` path.

**State:** `pytest pilot/tests/ -v` passes **29/29** (27 pre-existing + 2 new).
`python run_pilot.py --dry-run` prints the corrected sequence end to end: the
new question wording and the strengthened answer instruction appear in every
rating block, `task_id` displays as a string (`mbpp/11`), and the planned
budget is unchanged at **1040 calls / 1200 MAX_CALLS** — still 20 tasks total,
now 10 MBPP + 10 LBPP instead of 20 MBPP. Verified by hand (not pytest): a
real LBPP task (`lbpp/python/000`, `add_avg_and_std_cols_numpy`) loads
end-to-end through `sandbox.run_solution`, and a solution that never imports
numpy itself still resolves `np` at assert time via the honoured
`test_setup`, correctly for both a right and a wrong reference solution.
Re-ran `VIGNETTE_LOW`/`VIGNETTE_HIGH` through `sandbox.run_solution` under the
new wording (the vignette texts themselves are unchanged): LOW still fails
2/7 hidden asserts — asserts[1] and [4], the same two failures as the original
verification — and passes the other 5/7; HIGH still passes 7/7. **Zero API
calls, zero spend this session** —
`pilot/out/raw.jsonl` is unchanged at 1023 lines.

Untested: the new task-set comparison section has only been exercised against
hand-built synthetic `Observation` objects (see "Did not work" above), never
against a real elicited run — `pilot/out/report.md` on disk still reflects
the pre-LBPP, pre-wording-change pilot and is now stale relative to the code.
The reworded questions and the strengthened single-digit instruction have
never been sent to a real model; whether the instruction change actually
reduces Claude's parse-failure rate is unverified until the next real run. No
LBPP task has been attempted by a real model — only a hand-written reference
solution has been run through the sandbox.

**Next:** run the real pilot (2 models x 20 tasks, new mix + new wording) —
held per the user's explicit instruction to stop after the dry-run and wait
for confirmation.

---

## 2026-08-14 22:00 — Sonnet (claude-sonnet-5, Claude Code)

**Built:** Nothing new in code. Two pieces of bookkeeping ahead of the real
pilot run: a correction to this file, and a literature note that reframes what
a flat self-report distribution means.

**Decided:**

- *The previous entry's "LOW still fails 5/7 hidden asserts" was wrong and is
  now corrected in place (see above): LOW fails 2/7 (asserts[1] and [4]) and
  passes the other 5/7, HIGH passes 7/7.* Re-verified fresh, per-assert, this
  session, in direct response to the user flagging a discrepancy against an
  earlier session's "2 of 7 fail" claim. All three data points — the original
  session, the prior verification run's raw boolean list
  (`[True, False, True, True, False, True, True]`), and this session's fresh
  rerun — agree on 2/7 failing. The only thing that was ever wrong was this
  file's prose, which reported the pass-count as if it were the fail-count.
  The vignette code and `VIGNETTE_HIDDEN_ASSERTS` were not touched.
- *Confidence saturation is being reframed as a validity question, not just a
  calibration nuisance*, per three sources the user supplied: "Verbal
  Confidence Saturation in 3-9B Open-Weight Instruction-Tuned LLMs: A
  Pre-Registered Psychometric Validity Screen" (arXiv:2604.22215), arXiv:2607.19367,
  and Wang and Stengel-Eskin (2026). arXiv:2604.22215's argument: a distribution
  collapsed to the ceiling cannot support item-level discrimination, because the
  ordinal relationships between items are lost at the moment of elicitation, not
  afterward — so post-hoc rescaling cannot recover what was never elicited in the
  first place. The other two sources report the same ceiling/floor concentration
  on unrelated tasks (verbal and logit-based confidence generally; TriviaQA and
  SimpleQA respectively), so this is not specific to our coding-task setup.
- *This gives anchoring vignettes a second job beyond bias correction: telling
  apart two explanations for a flat self-report that are otherwise
  indistinguishable* — either the model has no graded internal signal to
  report, or it has one but cannot express it on this response scale. If the
  vignette ratings (`z_lo`, `z_hi`) vary across models/tasks while the
  self-rating `y` does not, the scale itself is shown to be usable by this
  model in this context, which means the flat `y` is evidence about the model,
  not an artifact of an unusable scale.
- *Our own pilot-1 numbers already look like the direction-specific case*: mean
  `z_lo` differed sharply between models (1.890 vs 1.021) while `z_hi` and `y`
  were both pinned at the ceiling (5.000) for both models. Read against the
  above, this suggests saturation here is one-directional — the top of the
  scale is unusable, the bottom is not — rather than the whole scale being
  dead. Flagged here as a framing candidate for the writeup, not asserted as a
  finding; pilot-1 is a go/no-go check on the old MBPP-only, old-wording setup
  and this reframing has not yet been checked against the reworded questions or
  the harder LBPP half.

**Did not work:** N/A this entry — bookkeeping only.

**State:** No code changed. `pilot/out/raw.jsonl` and `observations.jsonl` were
reset to empty and the pilot-1 data (1023 / 40 lines, old wording, MBPP-only)
was preserved as `pilot/out/raw.pilot1_mbpp_only_backup.jsonl` and
`observations.pilot1_mbpp_only_backup.jsonl`, mirroring the existing
`raw.pre_pilot_backup.jsonl` precedent — so the next run's cost/token/call
summary (which reads the whole file) reports only the new run, not a mix of
old-wording and new-wording data.

**Next:** run the real pilot (`python run_pilot.py`, 2 models x 20 tasks, 10
MBPP + 10 LBPP, reworded questions) and report per DESIGN.md §9/§10 plus the
per-task-set `y`/`z_lo`/`z_hi` distributions and `y == z_hi` share the user
asked for, raw and uninterpreted.

---

## 2026-08-14 22:40 — Sonnet (claude-sonnet-5, Claude Code)

**Built:** The second real pilot run, on the difficulty-mixed task set and
reworded questions from the previous entry. `pilot/out/report.md`,
`raw.jsonl` (990 lines), `observations.jsonl` (40 lines) now reflect this run
only — the first pilot's data was moved to `raw.pilot1_mbpp_only_backup.jsonl`
/ `observations.pilot1_mbpp_only_backup.jsonl` beforehand, per the previous
entry's decision.

**Decided:** Nothing new. This entry is a run record, not a design change.

**Did not work:**

- *Gemini made 470 calls against a planned 520, not a bug.* 2 of its 10 LBPP
  tasks failed code extraction (`code_extraction_failure_rate` 20% on the LBPP
  half); the early-return-on-failed-codegen path in `run_pilot.py` skips the
  25 downstream rating calls for a task once code generation itself is
  unusable, rather than rating a nonexistent solution. `470 = 520 - 2*25`,
  exactly. Confirmed by counting `code_extraction_failure_rate` against the
  gap rather than assumed.

**State:** `GO` on P1, P2, P3 (both tie_rule bounds agree, as always). **P4
FAILED** for gemini-3.6-flash (signed self/other gap 0.822, threshold 0.75) —
driven entirely by its LBPP half (gap 1.425 on LBPP vs 0.340 on MBPP); claude
passed P4 on both halves. Verdicts do not change between tie_rule bounds — no
P1-P4 threshold is a function of C, so the bound choice affects only the C
distribution and `ambiguous_C_rate` (0% for both models, both bounds).

The pattern the user's literature note anticipated is present in this run's
numbers, not just pilot-1's: `y` (condition-V self-rating) and `z_hi` are
both saturated at or near 5.0 for both models on both task sets — mean C is
4.000 (claude) and 3.944 (gemini) pooled, with **every non-null C value equal
to 3 or 4**, none at 1, 2, or 5. `z_lo` is the only quantity with real spread
(claude: 1.0-2.0 depending on task; gemini: pinned at exactly 1.0 on every
single observation in both halves). `y == z_hi` (tolerance 0.01): claude
20/20 pooled (10/10 MBPP, 10/10 LBPP), gemini 17/18 pooled (9/10 MBPP, 8/8
LBPP). Full per-task-set `y`/`z_lo`/`z_hi` distributions are in the chat
report to the user for this entry's date, not duplicated here.

Cost: $0.3506 (claude-haiku, 520 calls). Gemini has no configured price
(`PRICE_PER_MTOK_USD['gemini-3.6-flash']` still `None`) — 470 calls, 212393 in
/ 1398 out / 16388 thought tokens, reported as tokens only.

**Next:** Decide how to frame P4's failure and the near-total C=3/4 collapse
in the sprint writeup — both are now reproduced across two independent runs
(different task mix, different wording), so they look like properties of
these models/this scale rather than an artifact of the first pilot's setup.
The task-set split suggests LBPP (harder, more execution failures) is what
pushes gemini's P4 gap over threshold — worth checking against MBPP-only
numbers before generalizing.

---

## 2026-08-14 23:10 — Sonnet (claude-sonnet-5, Claude Code) — session close, no code changed

**Built:** Nothing. This entry exists so the next session can read the
conclusion of pilot 2 in one place instead of reconstructing it from the two
entries above. No control experiment was started, per explicit instruction.

**Decided:** Nothing new.

**Did not work:** N/A.

**State — the conclusion, stated plainly:**

- The run returned **GO on P1-P3**, but **the GO is hollow**: pooled across
  both models and both task sets, `y` (condition-V self-rating) is 5.0 in
  **37 of 38** valid observations, `z_hi` is 5.0 in **38 of 38**, and
  `y == z_hi` in **37 of 38** (tolerance 0.01). With `y` and `z_hi` this
  close to identical this close to always, `C` is constant almost everywhere
  no rescaling can improve a correlation between confidence and correctness
  that the elicitation never captured in the first place.
- **Saturation survived both attempted fixes.** The 10 MBPP + 10 LBPP
  difficulty mix (2026-08-14 21:30) and the "passes every test case,
  including edge cases" wording (same entry) were both tried specifically to
  break this. Claude gave `y = 5.0` on all 10 MBPP tasks **and** all 10 LBPP
  tasks — harder tasks changed `execution_failure_rate` (0% to 30% for
  claude, 10% to 80% for gemini) but did not move stated self-confidence at
  all.
- **This is not an inability to grade — it is specific to grading one's own
  code.** Claude's `z_lo` (rating of the fixed low-quality *foreign* vignette)
  took **six distinct values**: 1.0, 1.2, 1.4, 1.6, 1.8, 2.0, spread across
  tasks. The same model, same scale, same context format, produces graded,
  varying output when the code is not its own, and a flat ceiling value when
  it is. The scale is usable by this model; the model does not use it on
  itself.
- **The effect is model-specific, and for one model the correction is
  mathematically vacuous.** Gemini's `z_lo` was **constant at exactly 1.0**
  across every single observation in both task sets (see the per-task-set
  distributions in the previous entry / the chat report of this date). With
  both anchors constant for gemini, `compute_C` degenerates to a monotone
  recoding of `y` for every gemini observation — this is the exact invariance
  case CLAUDE.md's "ONE RULE" section warns about ("if vignette ratings are
  constant across observations, `compute_C` becomes a monotone recoding of
  the self-report, and every rank-based metric is mathematically guaranteed to
  show exactly zero change"), now observed in real elicited data rather than
  only in simulation. Claude's `z_lo` varying is what keeps claude's
  correction non-vacuous; gemini's does not have that.
- **P4 (response consistency): gemini FAILED, claude PASSED.** Signed
  self-minus-other gap on byte-identical code: gemini **0.822** (threshold
  0.75), claude **-0.130**. This reverses pilot 1, where both models passed
  P4 on the easier, saturated MBPP-only set — see the P4 bullet in Open
  Questions below for the full before/after.
- **Parse failures: 17 (pilot 1) to 0 (pilot 2)**, after strengthening
  `ANSWER_INSTRUCTION` to demand a single digit and nothing else. Neither the
  parser nor `MAX_OUTPUT_TOKENS_RATING = 8` was touched.
- **Next step, not yet started: a control experiment on scale granularity.**
  Same 20 tasks (10 MBPP + 10 LBPP), same two models, but a 0-100 scale
  instead of 1-5, to rule out that a 5-point scale is simply too coarse to
  register near-ceiling distinctions a finer scale could show. This would be
  a deviation from the locked "exactly 5 scale points" decision in CLAUDE.md
  (justified there by Wang, Zhou & Liu, arXiv:2608.08869) — it is a
  *diagnostic* run to characterize the saturation, not a change to the
  main-experiment design, and should be labeled as such wherever it is
  reported. **Not started this session, per explicit instruction to close
  without beginning it.**

**Next:** Design and run the 0-100 control experiment described above, as its
own clearly-labeled pilot variant, once a session is authorized to start it.

---

## 2026-08-14 22:33 — Sonnet (claude-sonnet-5, Claude Code)

**Built:** The 0-100 scale control experiment authorized this session as a
one-off diagnostic exception to CLAUDE.md's locked "exactly 5 scale points"
decision (DESIGN.md §3 unchanged; the 5-point pilot's data untouched).
`run_control_scale100.py` (new, project root): monkeypatches
`pilot.config.SCALE_POINTS`, `ANSWER_INSTRUCTION`, `MAX_OUTPUT_TOKENS_RATING`
and `RAW_JSONL_PATH` at process start, then drives the run entirely through
`run_pilot.py`'s own unmodified `_run_observation`, `_dry_run`,
`_walk_condition_v`, `_planned_calls`, `_print_cost_summary` — the turn-
sequencing logic already validated in the two real pilot runs cannot drift
between the two scripts because there is only one copy of it. Wrote its own
`_append_observation` and `render_report`/`write_report` (does not import or
call any of `analyze.py`'s P1-P4 functions). Output kept fully separate:
`pilot/out/raw_scale100.jsonl`, `observations_scale100.jsonl`,
`report_scale100.md`, `run_log_scale100.txt`. `pilot/out/raw.jsonl`,
`observations.jsonl`, `report.md` (the 5-point run) were never opened for
writing this session — sizes/timestamps confirmed unchanged before and after.

**Decided:**

- *`SCALE_POINTS_WIDE = {0: "Very unlikely", 100: "Very likely"}`* — two
  labelled endpoints, not a fully enumerated 0-100 dict. This incidentally
  solves the "101-line legend" problem named in this session's task brief:
  since `run_pilot.py`'s `_scale_block` iterates `sorted(config.SCALE_POINTS)`
  and that dict now has 2 keys, the legend prints 2 lines with no change to
  `run_pilot.py` itself. Direction randomisation (DESIGN.md §3) still applies
  to which of the two lines prints first.
- *`ANSWER_INSTRUCTION` reworded from "a single digit" to "a single integer
  from 0 to 100"* — flagged to the user before running: the literal 5-point
  wording would have capped every reply at 0-9 and silently defeated the
  point of the control. Confirmed with the user as a deliberate deviation
  that preserves the instruction's strict, no-prose intent rather than its
  digit count.
- *`MAX_OUTPUT_TOKENS_RATING` raised from 8 to 16 for this script only*, per
  the user — headroom for a multi-digit reply plus tokenisation overhead, not
  a parser relaxation. `elicit.parse_rating` is untouched and still strict.
- *`TOLERANCE` for the near-ceiling share is 0.25, not the 5-point run's
  0.01* — the proportional equivalent on a width-100 scale (`0.01 * 100/4`),
  per the user's instruction, stated in the report itself.
- *`analyze.py`'s `_c_distribution`/P1-P4 machinery is not touched or
  imported for analysis* — only `analyze.Observation` (the dataclass) is
  reused, for serialization. No `compute_C` call, no threshold check anywhere
  in this script. `analyze.py`'s module-level `_MIN_POINT`/`_MAX_POINT`
  (computed from `config.SCALE_POINTS` at import time, before this script's
  override runs) are consequently stale at 1/5 for the rest of the process,
  but nothing in this script reads them.
- *Reused `run_pilot._run_observation` and `_dry_run` unmodified* rather than
  writing parallel versions, specifically to avoid re-introducing the
  condition-V sequencing bug the 2026-08-14 entry ("Claude Opus 4.7") already
  fixed and verified once.

**Did not work:** Nothing failed. Zero parse failures and zero off-scale
draws across all 4 (model, task-set) groups (see numbers below) — the
reworded instruction held up cleanly on the wide scale too, on the first
attempt, with no relaxation of `parse_rating`.

**State:** `python3 run_control_scale100.py --dry-run` printed the corrected
2-line endpoints legend and confirmed 1040 planned calls (identical to the
5-point pilot's budget), within `MAX_CALLS`=1200. The real run made 965 calls
(520 claude, 445 gemini — 3 gemini LBPP tasks lost to code-extraction failure,
skipping their 25 downstream calls each: `520 - 3*25 = 445`, exactly). Cost:
claude-haiku $0.3277 (296,853 in / 6,168 out tokens); gemini has no configured
price, 198,883 in / 1,970 out / 15,783 thought tokens, reported as tokens
only. Under the $1 budget on the priced side.

Numbers as requested, per model and per task set, uninterpreted (full detail
in `pilot/out/report_scale100.md`):

| Group | n | distinct y | distinct z_lo | distinct z_hi | y min/max/mean/sd | share \|y-z_hi\|<=0.25 |
|---|---|---|---|---|---|---|
| claude · mbpp | 10 | 4 | 4 | 6 | 92.000 / 95.000 / 92.540 / 1.037 | 0.300 |
| claude · lbpp | 10 | 6 | 5 | 4 | 89.800 / 94.400 / 92.520 / 1.347 | 0.500 |
| gemini · mbpp | 10 | 2 | 1 | 1 | 80.000 / 100.000 / 98.000 / 6.325 | 0.900 |
| gemini · lbpp | 7 | 1 | 1 | 1 | 100.000 / 100.000 / 100.000 / 0.000 | 1.000 |

y distributions (sorted, per-observation mean of 5 draws):
- claude · mbpp: [92.0, 92.0, 92.0, 92.0, 92.0, 92.0, 92.0, 92.6, 93.8, 95.0]
- claude · lbpp: [89.8, 91.6, 92.0, 92.0, 92.6, 92.6, 92.6, 93.2, 94.4, 94.4]
- gemini · mbpp: [80.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0]
- gemini · lbpp: [100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0]

z_lo distributions (sorted): claude · mbpp [15,15,15,15,15,17,17,19,19,21];
claude · lbpp [15,15,15,15,15,17,17,19,21,25]; gemini · mbpp all 0.0 (n=10);
gemini · lbpp all 0.0 (n=7).

z_hi distributions (sorted): claude · mbpp [91.2,92.0,92.6,92.6,92.6,92.6,
92.6,93.8,94.4,95.0]; claude · lbpp [91.8,92.6,92.6,93.2,93.2,93.2,93.2,93.2,
93.2,94.4]; gemini · mbpp all 100.0 (n=10); gemini · lbpp all 100.0 (n=7).

Parse failures: 0 for both models, both task sets (250 rating draws per
claude group, 250/175 per gemini group). Off-scale draws: 0 throughout.

Untested / not done, deliberately: no P1-P4 verdict, no `compute_C`, no
cross-run statistical comparison against the 5-point pilot's numbers. Not
started: anything paper-facing that interprets these numbers.

**Next:** None assigned. This was a bounded diagnostic run; per this
session's explicit instruction, print the numbers, log them, commit, and
stop — not the researcher's job to interpret them in this session.

---

# Related work that now anchors this project

- **Cacioli, arXiv:2604.22215.** Seven 3-9B open-weight models, TriviaQA,
  numeric 0-100 and categorical 10-class elicitation: all seven Invalid, mean
  ceiling rate 91.7 %. Categorical did not rescue validity. Concludes internal
  representations are not necessarily absent — minimal verbal elicitation
  fails to preserve them at the output interface "in this model-size regime."
  Our frontier-scale result splits that regime: Claude's 0-100 signal
  survived: Gemini's did not.
- **Panickssery, Bowman & Feng, arXiv:2404.13076.** Self-preference: LLM
  evaluators score their own outputs higher than others' where humans see
  them as equal; self-recognition causally drives it. Our P4 is a cleaner
  isolation — byte-identical code, authorship framing as the only
  difference, execution ground truth instead of human annotators.
- **Okada, Furukawa & Bunji, arXiv:2602.17262.** Likert formats show large
  socially desirable responding; desirability-matched graded forced-choice
  attenuates it; the trade-off is model-dependent. Establishes response
  format as a first-class variable and model-dependence, both matching our
  results.
- **Zhang et al., arXiv:2606.05122.** Reframes judge-aligned self-evaluation
  as a problem of elicitation rather than acquisition. That is precisely our
  Claude result.

Also record: the Pinocchio Inventory (Plisiecki et al., arXiv:2607.20082)
uses a uniform 7-point response scale with decoding constrained to scale
integers, aggregated over 24 items per scale. On our measured signal band a
7-point scale would not resolve 92.0 from 92.6. Caveat to state honestly:
aggregation over 24 items restores resolution at the scale level, so the
concern is item-level, not necessarily scale-level.

---

## 2026-08-15 00:20 — Sonnet (claude-sonnet-5, Claude Code) — session close, no experiments

**Built:** No new experiments this session, per explicit instruction. Three
pieces of bookkeeping: (1) the repository is now connected to a GitHub
remote — `git remote add origin` to
`https://github.com/nick-is-building/Digital-Minds-research-sprint.git`,
plus local `user.name`, `user.email`, `credential.helper=store` — verified
with `git remote -v` and `git config --list --local`; **no push was made**,
per explicit instruction, and no token was requested. (2) `CLAUDE.md` gained
a "What the pilots established" section (22 lines) consolidating the
5-point/0-100 saturation results, the P4 gap, the parse-failure fix, and the
Gemini LBPP extraction failures — so no future session has to reconstruct
this from the raw entries. (3) `DEVLOG.md` gained a "Related work that now
anchors this project" section (four papers plus the Pinocchio Inventory
resolution caveat), placed above Open Questions.

**Decided:** Editing `CLAUDE.md` and `DESIGN.md` is normally off-limits for
this assistant without flagging errors and logging them in Open Questions
instead (established convention this session, not previously written down
anywhere the assistant could cite) — overridden here only because the user,
who owns both files, explicitly asked for this specific addition to
`CLAUDE.md` in this message. `DESIGN.md` was not touched.

**Did not work:** N/A — bookkeeping only, nothing run.

**State:** `git status --short` clean after the commit below. `pytest
pilot/tests/ -v` not re-run this session (no code changed under `pilot/`).
Remote configured, not pushed. The two pilot runs' data and the 0-100 control
run's data are unchanged from the previous entry.

**Next:** The user will run the first `git push` themselves. Before the main
experiment can start, still needed (not built this session): fix the Gemini
LBPP code-extraction failures (3/10 tasks lost), fill in
`PRICE_PER_MTOK_USD` for Gemini, add resumability for ~15,600 planned calls,
add a regression test for `_orient`, decide how to frame saturation
(format-artifact for Claude, intrinsic for Gemini) and the P4 asymmetry in
the write-up, and decide whether/how the main experiment's response scale
should differ from the locked 5-point default given this session's result.

---

## 2026-08-15 04:20 — Opus (claude-opus-5, Claude Code)

**Built:**

- **DESIGN.md updated** for the three decisions the user made this session, and
  only those. §3 now defines three scale formats (`p5` 1-5 unchanged, `p7` 1-7
  after the Pinocchio Inventory, `s100` 0-100) and names the Wang/Zhou/Liu
  tension explicitly instead of dropping the citation: their result is about
  *stability* against label order, ours is about *resolution* near the ceiling,
  and both hold. §2 gained a "validity screen (reported, not filtered)"
  subsection. §5 records that `C` has five categories in every format (two
  anchors partition the line into five regions, regardless of input cardinality)
  and that the tolerance is `0.0025·W`. §9's thresholds are now a table of
  fractions of `W`, printed as both the fraction and the value in that format's
  points. §10 records that all three formats run on the same tasks, models and
  solutions.
- **`config.ScaleFormat`** — the scale is now an object passed explicitly, with
  `width`, `fully_labelled`, `in_range`, and the width-relative `tolerance`,
  `p1_min_sd`, `p3_min_difference`, `p4_max_abs_gap` hanging off it. The
  module-level `SCALE_POINTS`/`TOLERANCE`/`P1_MIN_SD`/`P3_MIN_SCALE_POINT_
  DIFFERENCE`/`P4_MAX_ABS_GAP`/`MAX_OUTPUT_TOKENS_RATING` constants are deleted,
  so a threshold can no longer go stale against the format in use. Verified at
  W=4 the fractions reproduce the locked values exactly: 0.3 / 0.5 / 0.75 / 0.01.
- **`pilot/extract.py`** — code extraction split out of `run_pilot.py`, with a
  rejection reason per failure mode (`no_reply`, `truncated_by_output_ceiling`,
  `unclosed_code_fence`, `no_function_definition`, `syntax_error`) recorded on
  the observation as `codegen_failure_reason`. `ast.parse` is the last gate.
- **`pilot/resume.py`** — observations keyed `(model, task_id, scale_format)`,
  solutions keyed `(model, task_id)` and persisted separately with their ground
  truth. `_read_jsonl` forgives a truncated *final* line only.
- **`run_main.py`** — the main-experiment runner. Imports `run_pilot`'s message
  builders rather than restating them, crosses scale format with model and task,
  skips completed cells, and has `--dry-run` and `--estimate` modes.
- **Prompt caching** in `elicit.py` (Anthropic explicit `cache_control`, Gemini
  implicit), requested only where a prefix is genuinely reused ≥2×.
- **56 new tests** in `test_analyze.py` (the `_orient` regression), 
  `test_extract.py` and `test_resume.py`. `pytest pilot/tests/ -v`: **83 passed**,
  `test_invariance` included and untouched.

**Decided:**

- **The (a) root cause was Gemini's combined thinking+output budget, not code
  extraction.** `max_output_tokens` on the Interactions API caps thinking *plus*
  output together. All 5 failed codegen calls had thought+output = exactly 1020;
  20 of 40 Gemini codegen calls hit that ceiling; Claude peaked at 620/1024 with
  none at the ceiling. The extractor's `else text` fallback then *masked* it: a
  truncated reply has an opening fence and no closing one, so the fence regex
  misses, so the literal ```` ```python ```` prefix was included in "the
  solution" — a guaranteed SyntaxError, scored as the model answering
  incorrectly. Gemini's 80 % LBPP `execution_failure_rate` was measuring our
  token ceiling, on roughly 12-13 calls. Fixed at the root (ceiling 4096,
  truncation detected and logged, masking fallback removed), not with a fallback.
- **Randomisation in the main run is keyed, not sequential.** Each (model, task)
  seeds its own generator from `(MAIN_RANDOM_SEED, model, task_id)`. Two things
  depend on this: the three formats of a pair share one presentation, so a format
  difference is not a direction difference; and skipping finished work on resume
  cannot shift the draws for what remains, which a shared sequential stream would.
- **Solutions are persisted, not regenerated.** Sampling is at temperature 1.0,
  so regenerating after an interruption yields a *different* solution and the
  three formats of that pair silently stop being paired. Ground truth is stored
  alongside for the same reason — it is a property of that exact text.
- **A failed codegen call is only recorded if the failure is about the reply.**
  `no_reply` means the API call itself returned nothing (timeout, rate limit,
  dropped connection); that is infrastructure, not data, so nothing is persisted
  and the next run retries it. Every other reason describes what the model
  actually emitted, which is a finding: persisted, reported, not retried.
- **Pricing verified, nothing guessed.** gemini-3.6-flash $0.75/$3.75
  (promotional through 2026-12-31, then $1.50/$7.50); gemini-3.1-pro-preview
  $2.00/$12.00 (≤200k tier); Haiku 4.5 $1/$5; Sonnet 4.6 $3/$15; Opus 4.7
  $5/$25. **gemini-3.7-flash left `None`** and shows as "unpriced". No
  `gemini-3.6-pro` exists — confirmed against a live `models.list()`.
- **Cost estimate, 4 models × 60 tasks × 3 formats = 18,240 calls: $19.59
  without caching, $19.52 with.** Per model: Haiku $2.85, Sonnet $8.54, Gemini
  Flash $2.20, Gemini Pro $6.00. Fifth-model candidates, marginal: Opus 4.7
  **$14.24**, gemini-3.7-flash unpriced. Gemini figures are a **lower bound** —
  the codegen output constant was measured under the old 1020-token ceiling with
  half the calls censored at it.

**Did not work:**

- **The assignment's premise that our sampling pattern is "the ideal caching
  case" does not survive contact with the minimum cacheable prompt lengths.**
  Caching is implemented and requested, and saves **$0.07 of $19.59 (0.4 %)**.
  Two independent reasons. First, the reused prompts are ~1,150 tokens, against
  minimums of 4,096 (Haiku 4.5, all Gemini 3.x), 2,048 (Opus 4.7) and 1,024
  (Sonnet 4.6) — only Sonnet clears its minimum at all. Second, condition V's
  cacheable share is small by design: only the *opening* vignette question is
  byte-identical across the 5 threads, because the later turns replay each
  thread's own ratings, which is the King & Wand priming mechanism and not
  something to trade away for a discount. The breakpoints are left in because a
  below-minimum prompt is processed uncached with no error and no write premium,
  so asking costs nothing.
- **My first version of the estimate reported Sonnet as broadly cacheable and it
  was wrong.** It compared the largest prompt overall (1,506 tokens, the
  self-assessment turn at the end of a condition-V thread) against the minimum —
  but that prompt carries no cache breakpoint. Fixed to compare the largest
  *cached* prompt (1,152), which is the figure that decides anything.
- **`run_control_scale100.py`'s monkeypatching had to be deleted, not adapted.**
  It patched four `pilot.config` attributes at process start. Once format became
  a parameter the patches were both inert and misleading, and they were the
  mechanism by which that run's analysis silently kept 5-point bounds while
  rating on a 0-100 scale.

**State:**

- `pytest pilot/tests/ -v` → **83 passed** (27 before this session).
- `python3 run_main.py --dry-run` prints one full condition-V context per format,
  12 call blocks, showing the width-proportional thresholds per format and
  `cache_prefix` per call. No API calls.
- `python3 run_main.py --estimate` prints the table above. No API calls.
- **The main run has NOT been started, as instructed.**
- **Untested against a live API:** every code path added this session. The
  `p7` format has never been sent to a model; `s100` has, but under the old
  monkeypatching runner. Resume has unit tests but has not been exercised by
  actually interrupting a real run.
- `MAIN_MODELS` has **four** entries. The fifth is the user's choice.

**Next:** the user picks the fifth model (Opus 4.7 at $14.24 marginal, or price
gemini-3.7-flash first), then start the main run.

---

# Open Questions

Add anything unresolved. Remove anything answered. This section is the handover
between sessions.

- **THE blocking issue: `y` has no variance, because MBPP is too easy for these
  models.** **Fix attempted 2026-08-14 21:30 (10 MBPP + 10 LBPP mix) did NOT
  work, confirmed by the 2026-08-14 22:40 real run.** `y` (condition-V
  self-rating) is 5.0 in every single claude observation on both halves (20/20)
  and in 17/18 non-null gemini observations, on MBPP *and* LBPP alike —
  `execution_failure_rate` on gemini's LBPP half jumped to 80 % (vs 10 % on its
  MBPP half), so the tasks plainly got harder, but the model's *stated*
  confidence did not move off the ceiling regardless. `z_hi` is 5.0 in every
  observation on both halves too. Non-null `C` is 3 or 4 for all 38 computed
  values, none at 1, 2 or 5, on both tie_rule bounds. **Making the coding task
  harder is not sufficient to break self-rating saturation** — the saturation
  looks like it lives in how the model uses the response scale, not in whether
  it is actually uncertain about its own code. This is exactly the split the
  2026-08-14 22:00 literature note (arXiv:2604.22215 etc.) predicted: `z_lo`
  still varies substantially (claude 1.0-2.0 across tasks; gemini flat at
  exactly 1.0) while `y`/`z_hi` do not, so the scale is demonstrably usable by
  these models in this context — the flat `y` is a fact about the models, not
  proof the scale can't carry information. **Do not "fix" this by lowering the
  high anchor** — unchanged from the original concern, simulation still shows
  `C` collapsing to a constant 5 in 94 % of cases if `y` stays pinned at the
  ceiling. Next candidate interventions, not yet tried: adversarial/edge-case-
  heavy tasks specifically designed to induce doubt, or accepting saturation as
  a reportable finding about these models rather than something to engineer
  away.
- **The 0-100 scale control (2026-08-14 22:33 entry) has been run; numbers are
  in `pilot/out/report_scale100.md`, not yet interpreted.** Raw facts only,
  per that entry: on the wide scale, claude's `y` took 4 (mbpp) / 6 (lbpp)
  distinct values in the 89.8-95.0 range (not a single collapsed value, not
  spread across 0-100 either); gemini's `y` was constant at exactly 100.0 on
  lbpp (7/7 usable) and 100.0 in 9/10 mbpp observations (one at 80.0), with
  `z_lo` constant at exactly 0.0 for gemini in every usable observation on
  both task sets. Zero parse failures, zero off-scale draws. Whether this
  rules in or out "scale coarseness" as the explanation for the 5-point run's
  saturation is an open interpretive question for the write-up, not decided
  here.
- **P1 does not catch collapse to the endpoints.** It passed at its floor: 3
  distinct points, zero draws at 3 and 4, mass at 1, 2 and 5. It was written to
  catch collapse to a single value. Consider adding an interior-use or
  endpoint-share check before the main run, so a bimodal response style cannot
  pass as graded confidence.
- **The between-model bias the method targets is real and measurable.** P3: mean
  `z_lo` 1.890 (Claude) vs 1.021 (Gemini), spread 0.869, on byte-identical
  vignettes. Worth keeping in view — it is the evidence that the correction has
  something genuine to act on once `y` can vary, and it belongs in the write-up.
- ~~**`_orient` has no regression test.**~~ **Closed 2026-08-15:**
  `pilot/tests/test_analyze.py` asserts a descending draw is returned unchanged
  in all three formats, that the mean is direction-independent, and that a clean
  anchor ordering survives a direction flip (the exact quantity P2 counts).
- **`MAX_OUTPUT_TOKENS_RATING = 8` costs real measurements, unevenly.**
  **Attempted fix (2026-08-14 21:30, strengthened `ANSWER_INSTRUCTION`) WORKED,
  confirmed by the 2026-08-14 22:40 real run: `parse_failure_rate` is 0.0 % for
  both models, pooled and per task set** — zero parse failures out of 990 raw
  calls, versus 17 in the first pilot (all Claude, all on the low vignette).
  The parser and `MAX_OUTPUT_TOKENS_RATING = 8` were left unchanged, as
  instructed; the instruction wording alone was sufficient this time. Keep
  watching this at main-experiment scale (~15,600 calls) rather than treating
  one clean run as proof it can never recur.
- **P4 (response consistency) passed in pilot 1 but FAILED in the 2026-08-14
  22:40 real run, for gemini only.** Pilot 1 (MBPP-only, old wording): signed
  gaps -0.320 (Claude) / -0.042 (Gemini), both well inside 0.75, but on a
  saturated scale with little room to show a gap — flagged at the time as weak
  evidence. Pilot 2 (10 MBPP + 10 LBPP, new wording): Claude still passes
  (-0.130), but gemini's gap widened to **0.822**, over threshold, driven
  almost entirely by its LBPP half (gap 1.425 on LBPP vs 0.340 on MBPP — LBPP
  is also where gemini's execution_failure_rate jumps to 80 %). Reading these
  two runs together: P4 passing in pilot 1 looks like it was an artifact of
  easy tasks giving the probe no room to disagree, not evidence that
  attribution gating is absent. The harder task set gave the gap room to show
  up, and it did, in exactly the direction Plisiecki et al. predict. Does not
  block GO but must be named as a limitation in the writeup, with this
  reversal shown, not just the latest number.
- **P4 (response consistency) is untested and is the assumption most likely to
  fail.** Plisiecki et al. (arXiv:2607.20082) document "attribution gating":
  models treat self-attribution differently from other-attribution. If a model
  rates byte-identical code differently depending on whether it is presented as
  its own, the response-consistency assumption underlying the whole method is
  violated. Failing P4 does not block the main experiment but changes how the
  result must be framed.
- **MBPP hidden-test coverage is thin** (few asserts per task). Acceptable for
  the pilot. Must be expanded before the main run, or ground truth will be
  noisy — a solution that passes all hidden tests is not thereby correct.
- **Vignette texts now exist and are verified by execution, but their quality is
  still what determines whether P2 passes** — and that can only be settled by
  real ratings. The open risk is specific: the LOW solution is wrong by
  *reasoning* (it silently drops the remainder) rather than wrong by
  *appearance*, which is what the "plausible, not absurd" constraint demands. If
  the pilot's models do not notice, P2 fails as ties rather than as misordering.
  The problem statement includes a non-divisible example precisely so a competent
  rater has the means to detect the bug.
- **The vignettes' ground truth is not protected by a regression test.** It was
  verified by a one-off sandbox run, so a future edit to either constant could
  silently invert LOW and HIGH. A `test_vignettes.py` asserting LOW fails and
  HIGH passes against `VIGNETTE_HIDDEN_ASSERTS` would close this; it was left out
  this session only to stay inside the assigned scope.
- ~~**Resumability is REQUIRED before the main experiment.**~~ **Closed
  2026-08-15:** `pilot/resume.py` plus `run_main.py`. Not yet exercised by
  interrupting a real run, only by unit tests — see the untested list below.
- ~~**Prompt caching is not yet in the design.**~~ **Closed 2026-08-15:**
  implemented, measured, and it does almost nothing (**$0.07 of $19.59**). This
  note's own suspicion was right and understated: the cacheable share of
  condition V is one call in three, *and* the reused prompts (~1,150 tokens) sit
  below every model's minimum except Sonnet 4.6's 1,024.
- ~~**`MAX_OUTPUT_TOKENS_DEFAULT` (1024) is still a guess.**~~ **Closed
  2026-08-15, and it was actively harmful:** it was the cause of Gemini's 80 %
  LBPP failure rate, because Gemini's `max_output_tokens` is a combined
  thinking+output budget. Now `MAX_OUTPUT_TOKENS_CODEGEN = 4096`, truncation is
  detected from the provider's own signal, and `codegen_failure_reason`
  distinguishes our ceiling from a bad reply. This note called it exactly right —
  "apparent model incompetence rather than a config problem" is what happened.
- ~~**`PRICE_PER_MTOK_USD` is `None` for Gemini.**~~ **Closed 2026-08-15** for
  the four configured models (verified against the providers' pricing pages, see
  this session's entry). **`gemini-3.7-flash` is still `None`** and must stay
  that way until someone verifies it; `--estimate` prints "unpriced" rather than
  a number.
- **CLAUDE.md's "Scope boundary" section now contradicts the work in progress.**
  It says "we are building **the pilot only**… Do not build the main experiment,
  expand the model list, add analysis beyond DESIGN.md §9" and gates all of that
  on the pilot returning a GO. This session was instructed to build exactly those
  things, and the pilot has not returned a GO. The instruction was followed and
  the contradiction is logged here rather than resolved by editing CLAUDE.md,
  which is the user's control document. **The user should decide whether that
  section is now superseded**, because as written it forbids the next step too.
- **CLAUDE.md's "Locked decisions" table still says "Exactly 5 scale points".**
  Superseded for the main run by this session's authorised decision, and recorded
  in DESIGN.md §3 — but the two documents now disagree. Same for "Main
  experiment: 5 models × 100 tasks", where the instruction was 60 tasks.
- **CLAUDE.md's Commands block says `pytest tests/ -v`; the real path is
  `pytest pilot/tests/ -v`.** Still unedited. A one-character fix for the user.
- **Task count for the main run is 60, not DESIGN.md §10's 100.** Simulation
  gives 98 % of runs positive at 100 vs 93 % at 60, so this costs about 5
  percentage points of power. 60 is the user's instruction for this run;
  `config.NUM_MBPP_TASKS_MAIN`/`NUM_LBPP_TASKS_MAIN` carry the note. At $19.59
  for 60 tasks, 100 tasks would be roughly $33 — budget is not the binding
  constraint here, so this is worth revisiting on the merits.
- **The fifth model is not chosen.** `MAIN_MODELS` has four. Marginal cost of a
  fifth: `claude-opus-4-7` **$14.24** (which would nearly double the run's total
  to ~$34), or `gemini-3.7-flash` at an unknown price. A third provider would add
  more between-model scale-use variance than a second Anthropic model, which is
  what the effect depends on — but no third provider is currently wired up.
- **DESIGN.md §4's condition-N wording implies a second code-generation call.**
  Step 1 reads "Coding task → model writes a solution", but the implementation
  generates one solution per (model, task) and replays it into V, N and the P4
  probe — forced by §9's byte-identical requirement, and necessary so that `y_v`
  and `y_n` rate the same code against the same ground truth. §4 also gives the
  visible assert to V's step 1 but not N's, whereas the implementation sends the
  identical prompt in both, so the conditions differ only in the vignettes. Both
  are wording fixes for the user to make in §4; the code is not changing.
- **The full multi-turn DESIGN.md §4 flow (vignettes + self-question replayed
  in one context) is untested.** Only single-turn rating questions have been
  run so far. `elicit.py`'s Gemini path builds this via explicit
  `user_input`/`model_output` steps (stateless replay, not
  `previous_interaction_id` chaining) to match "fresh context every time" —
  this has not yet been exercised with more than one message in the list.
- **Everything added on 2026-08-15 is untested against a live API.** Specifically:
  the `p7` format has never been sent to any model; `s100` has, but through the
  old monkeypatching runner, not the current one; the raised codegen ceiling has
  never been exercised, so it is not yet confirmed that 4096 combined
  thinking+output tokens is actually enough for Gemini on LBPP; the two new
  models (`claude-sonnet-4-6`, `gemini-3.1-pro-preview`) have never been called
  at all; and resume has unit tests but has never recovered a genuinely
  interrupted run. **A small live smoke test — one model, one task, all three
  formats, then kill it and restart — would cost cents and would exercise every
  one of these before ~18,000 calls are committed.** It was not run this session
  because the instruction was to stop before the main run.
- **The cost estimate's Gemini figures are a lower bound and should be checked
  against the first real spend.** `EST_CODEGEN_OUTPUT_TOKENS[google] = 854` was
  measured while the ceiling was 1020 combined tokens with 20 of 40 calls
  censored at it, so the true mean is higher — possibly much higher, since the
  distribution was cut off precisely where it mattered. If actual Gemini spend
  runs well above $2.20 (Flash) / $6.00 (Pro), this is why, and it is not a
  pricing error.
