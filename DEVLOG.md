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

# Open Questions

Add anything unresolved. Remove anything answered. This section is the handover
between sessions.

- **THE blocking issue: `y` has no variance, because MBPP is too easy for these
  models.** `y_v` is exactly 5.000 in 36/39 observations and `z_hi` in 39/39, so
  `y == z_hi` and `C = 4` almost everywhere; both bound choices give byte-identical
  C distributions. No P1–P4 threshold asks whether `C` varies, which is why the
  pilot returns GO anyway. **Do not "fix" this by lowering the high anchor** —
  simulation shows that with `y` pinned at the ceiling, `C` collapses to a constant
  5 in 94 % of cases, i.e. strictly worse. The fix is a harder task set, so the
  models are not uniformly maximally confident. Vignettes, anchors and the 5-point
  scale all stay as they are; the locked scale decision does not need reopening.
- **P1 does not catch collapse to the endpoints.** It passed at its floor: 3
  distinct points, zero draws at 3 and 4, mass at 1, 2 and 5. It was written to
  catch collapse to a single value. Consider adding an interior-use or
  endpoint-share check before the main run, so a bimodal response style cannot
  pass as graded confidence.
- **The between-model bias the method targets is real and measurable.** P3: mean
  `z_lo` 1.890 (Claude) vs 1.021 (Gemini), spread 0.869, on byte-identical
  vignettes. Worth keeping in view — it is the evidence that the correction has
  something genuine to act on once `y` can vary, and it belongs in the write-up.
- **`_orient` has no regression test.** It silently inverted every descending
  observation and produced a false NO-GO on the first run; the fix is a one-liner
  and nothing in the 27 tests would catch a regression. A test asserting that a
  descending draw is returned unchanged, and that raw anchor orderings are
  direction-independent, belongs in `pilot/tests/`.
- **`MAX_OUTPUT_TOKENS_RATING = 8` costs real measurements, unevenly.** 17 of
  Claude's rating replies were truncated mid-sentence after a valid leading digit,
  16 of them on the low vignette. Raising the ceiling would recover them; relaxing
  the parser to take the leading digit would too, but after seeing the data that
  is fitting the instrument to the results, so it was not done. Decide before the
  main run, where the same 3 % loss lands on ~15,600 calls.
- **P4 (response consistency) passed in the pilot but on a saturated scale.**
  Signed gaps were -0.320 (Claude) and -0.042 (Gemini), well inside the 0.75
  threshold. With self- and other-ratings both near the ceiling, the probe had
  little room to show a gap, so this is weak evidence of consistency rather than
  strong evidence. Original concern retained below.
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
- **Resumability is REQUIRED before the main experiment (~15,600 calls).** Decided
  2026-08-14: deliberately not built for the pilot, because a re-run costs under a
  dollar. Every call already appends to `raw.jsonl` before parsing, but nothing
  reads that file back to skip completed work, so an interrupted run restarts from
  zero. At main-experiment scale that is no longer an acceptable loss, and the
  append-immediately log is only half a resume mechanism until something consumes
  it.
- **CLAUDE.md's Commands block says `pytest tests/ -v`; the real path is
  `pytest pilot/tests/ -v`.** Left unedited because CLAUDE.md is the user's
  control document — worth a one-character fix by the user.
- **Prompt caching is not yet in the design, and condition V now benefits less
  from it than this note originally assumed.** Condition N and the P4 probe do
  send 5 calls with an identical prefix — the ideal caching case (write 1.25×,
  read 0.1×). Condition V's 5 threads share only the code-generation prefix; from
  the first vignette rating onward each thread diverges, because the ratings are
  re-elicited per thread on purpose. The cacheable share is therefore smaller than
  "two-thirds off input cost" implies. Recompute against real token counts from
  the pilot before deciding for the main run.
- **Task count for the main run assumes 100.** Simulation gives 98 % at 100 vs
  93 % at 60. Revisit only if budget forces it.
- **`MAX_OUTPUT_TOKENS_DEFAULT` (1024) is still a guess.** The code-generation
  prompt now exists (one MBPP problem, its visible assert, "reply with a single
  Python function and no explanation"), so 1024 should be ample — but a truncated
  reply would surface as an `_extract_code` failure, i.e. as apparent model
  incompetence rather than as a config problem. `code_extraction_failure_rate` is
  in the report for exactly this reason; check it first if it is non-zero.
- **`PRICE_PER_MTOK_USD` is set for Anthropic ($1.00 in / $5.00 out per Mtok,
  user-supplied 2026-08-14) and deliberately still `None` for Gemini** — the user
  has no verified figure and will not guess. Any total cost reported is therefore
  Anthropic-only; Gemini appears as token counts. Fill in before the main
  experiment, where spend actually matters.
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
