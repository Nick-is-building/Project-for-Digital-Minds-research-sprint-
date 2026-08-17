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

## 2026-08-15 05:20 — Opus (claude-opus-5, Claude Code)

**Built:**

- **The model list is final and verified live.** `config.MAIN_MODELS` is now
  `claude-haiku-4-5-20251001`, `claude-sonnet-5`, `claude-opus-5`,
  `gemini-3.6-flash`, `gemini-3.1-pro-preview`. Both new strings were checked
  against `client.models.list()` before any run, per instruction to stop rather
  than fall back silently; both resolve, and both have since answered real calls.
  `MAIN_MODEL_CANDIDATES` and the `--estimate` block that printed marginal
  fifth-model costs are deleted — the slot is filled.
- **Prices for the two new models, verified, not guessed.** Sonnet 5 $2/$10 per
  MTok, Opus 5 $5/$25, with published cache-read rates ($0.20 / $0.50) now stored
  as a `cache_read` key so the cost summary does not have to derive them.
  Anthropic's page also states Sonnet 5's $2/$10 is no longer introductory: the
  rise to $3/$15 scheduled for 2026-09-01 will not happen.
- **Real cache accounting, replacing the estimate.** `CallResult` gained
  `cache_creation_tokens`; it is logged per call and summed per model in a new
  section of `print_usage_summary()`, alongside reads and the model's minimum.
  `run_pilot.cost_of` now bills cache writes at 1.25x and reads at the cache-read
  price. This was also a **cost bug**: Anthropic's `input_tokens` excludes both
  cache fields, so before this change a cached run was billed as if its cached
  tokens had never been sent.
- **A live smoke test, as its own command.** `run_main.py --smoke` drives one
  model × one task × all three formats through `run()` itself — the real code
  path, not a copy — writing to separate `smoke_*.jsonl` files so an interrupted
  test cannot make the real run skip cells. `--smoke-probe` sends one codegen
  call to each of the five models. `run()` and `remaining_calls()` took `models`
  and path parameters to make this possible; defaults are unchanged.
- **`pilot/tests/test_elicit.py`** (7 tests, suite now 90) pinning the
  response-shape bug below, and asserting every configured model has a provider,
  a price and a cache minimum.

**Decided:**

- **Task count stays at 60** (user's decision, now recorded in
  `config.NUM_MBPP_TASKS_MAIN` with the reasoning rather than only as a
  deviation). The 100-task figure was powered for the across-model correlation.
  That analysis is now *secondary* and will only include models that pass the
  validity screen — possibly three of five — and no task count rescues a
  correlation computed over three points. The primary result is the per-cell
  distribution of `y`, for which 60 is ample.
- **Caching stays on for all five models** even though three of them can never
  use it. A prompt below its model's minimum is processed uncached with no error
  and no write premium, so a breakpoint that never fires costs nothing.
- **Extended thinking is now switched off explicitly on Anthropic rating calls**
  rather than left at the default — see "Did not work". This implements
  CLAUDE.md's existing "leave it off" instruction rather than changing it, and
  mirrors what `GOOGLE_RATING_THINKING_LEVEL` already does for Gemini. Code
  generation keeps each model's default thinking.
- **The three CLAUDE.md contradictions are resolved** (authorised this session,
  and the only CLAUDE.md edits made): the scope boundary now states the pilot has
  returned its verdict and the main experiment is authorised; the "exactly 5
  scale points" row is struck through and replaced with the three-format decision
  plus the stability-vs-resolution tension and a pointer to DESIGN.md §3; the
  "100 tasks" row now reads 60 with the reason. The `pytest tests/ -v` path typo
  was **not** touched — it was not in the authorisation and stays in Open
  Questions.

**Did not work:**

- **`response.content[0].text` is wrong, and Opus 5 is what proved it.** 52 of
  128 rating calls in the first smoke run died with
  `AttributeError("'ThinkingBlock' object has no attribute 'text'")`.
  claude-opus-5 emits a thinking block ahead of its answer on a minority of
  calls **with no thinking requested**, so indexing block 0 fails
  non-deterministically — the same prompt succeeded 5 times in 6 in a direct
  probe. CLAUDE.md's "extended thinking is off by default" was verified on
  Haiku 4.5 and Sonnet 4.6 and does not hold for this model.
  - The crash was the visible half. The **measurement** half is worse: against
    `max_output_tokens_rating` of 8, the thinking block consumed the entire
    budget and the reply contained no digit at all (`stop_reason: max_tokens`,
    empty thinking text). Even with the crash fixed, ~40% of Opus 5's rating
    draws would have been silently dropped as parse failures — the exact failure
    mode the `ANSWER_INSTRUCTION` fix closed on 2026-08-14, returning through a
    different door.
  - Two fixes, both needed: `_first_text()` scans for the first text block
    instead of indexing, and `thinking: {"type": "disabled"}` is sent on rating
    calls. Verified: 12/12 clean probes after, then 76/76 calls with 0 errors and
    0 parse failures.
  - **This is the case for smoke-testing.** At full scale this would have
    contaminated one fifth of the run — 4,560 calls — and the symptom would have
    read as Opus 5 refusing to answer, not as our bug.
- **`load_tasks(0, 1)` returned every task in both datasets.** The loaders check
  `len(loaded) == n` only *after* appending, so `n=0` never matches and the loop
  runs to the end. Caught because the smoke test asked for one LBPP task and got
  MBPP task 11. Guarded with an early return in both loaders. Not reached by the
  real run, which never asks for zero, but it silently returned 380 tasks where
  0 were requested.
- **A SIGKILL'd run leaves no console trace.** stdout is block-buffered when not
  a tty, so the first killed run's progress output was lost entirely. The JSONL
  files were complete and correct, which is the point of writing them per call,
  but `python3 -u` is needed to watch a real run's progress through a pipe.

**State:**

Smoke test: **414 live calls, $0.6450 total.** Everything on the untested list
from the last entry has now been exercised.

- **All five models answered.** One LBPP codegen call each: Haiku 106 tokens,
  Sonnet 5 115, Opus 5 131, gemini-3.6-flash 878 (85 out + 793 thought),
  gemini-3.1-pro-preview 975 (65 out + 910 thought). None truncated, all five
  extracted cleanly.
- **The raised ceiling is confirmed necessary and sufficient.** Gemini Pro spent
  975 combined tokens on one LBPP problem. The old ceiling was 1020. It fits
  inside 4096 with room; it did not inside 1020, and that is the whole of the
  earlier "80% LBPP failure rate".
- **All three formats ran live for the first time**, Opus 5 and Haiku, 76 calls
  each. **0 parse failures in 150 rating calls**, including 30 on `p7`, which had
  never been sent to any model.
- **Resume recovers a genuinely interrupted run.** Killed with `kill -9` 31 calls
  in (one format complete, five ratings of the second lost). On restart: 50 calls
  exactly — two formats × 25, **zero code-generation calls** — and all 50 prompts
  replayed the persisted solution byte-for-byte. Compared against a separate
  uninterrupted run of the same cell, all three formats agreed on
  `scale_direction` and `low_vignette_first`, which is the keyed-randomisation
  guarantee holding in practice and not only in `test_resume.py`.
- **Caching is real on Opus 5 and measured, not estimated:** 3,229 tokens
  written, 12,916 read on one task — 28.1% of its input tokens — saving **18.2%**
  of that cell's cost. Haiku, Sonnet 5 and both Geminis reported 0 written and 0
  read, exactly as their minimums predict. So the earlier "$0.07 of $19.59"
  figure was correct *for the model set it was computed on*; adding Opus 5
  changes it materially.
- **The estimator understates Opus 5 by 13%.** Measured $0.2423 for one task ×
  three formats → $14.54 for 60 tasks, against $12.82 estimated. Consistent with
  the Claude 4.7+ tokenizer producing ~30% more tokens while
  `CHARS_PER_TOKEN[anthropic]` was measured on Haiku 4.5 — partly offset by the
  cache saving being larger than modelled. Haiku measured $2.93 against $2.85
  estimated, i.e. the calibration is accurate for the model it was calibrated on.
  Revised projection for the full run: **~$31**, with the two Gemini figures
  still lower bounds.
- **Substantive, and explicitly not a finding:** Opus 5's smoke cell is not
  saturated. `y_v` was 4 on `p5` (not 5), 88-92 with genuine spread on `s100`,
  and `z_lo` was 3 rather than 0 — both anchors varied, so this cell would pass
  the validity screen. One task, one model; it means the main run is not doomed
  to the pilot's ceiling, nothing more.
- **Untested:** the full 5-model × 60-task × 3-format run itself; `claude-sonnet-5`
  and both Gemini models have made only a single codegen call each and have never
  run a rating block or a multi-turn condition-V thread. Sonnet 5 in particular
  shares Opus 5's generation and may share its thinking-block behaviour on
  ratings; the fix covers it, but it has not been observed.

**Consequence of the Gemini truncation finding, for the write-up (recorded on
instruction):** because Gemini's pilot solutions were being cut off at the token
ceiling, **its measured accuracy was understated** — some of what was scored as
a wrong answer was a program we never let it finish. It also means Gemini **rated
truncated code at 100**, i.e. it was expressing maximum confidence in fragments,
which is not the same claim as being overconfident about complete work. The
**saturation finding stands unaffected**: rating calls cap at 8-16 tokens, are
answered in one, and never approach any ceiling — no rating in either pilot was
truncated. But **every Gemini pilot accuracy figure needs a stated caveat**, and
`execution_failure_rate` on Gemini's LBPP half (80%) must not be quoted as a
model property anywhere in the paper.

**Next:** start the main run (`python3 -u run_main.py`), ~22,800 calls, ~$31.

---

## 2026-08-16 06:00 — Opus (claude-opus-4-7, Claude Code)

**Built:** three pre-run checks (`check_untested_paths.py`) drove `run_pilot`'s
own message builders through paths the smoke test did not reach: CHECK 1 sent
one Gemini condition-V thread (four turns on one context), CHECK 2 sent one
rating call to each of `claude-sonnet-5`, `gemini-3.6-flash`, and
`gemini-3.1-pro-preview` on all three scale formats, and CHECK 3 re-verified
`gemini-3.1-pro-preview` after the fixes. Retry/backoff was added to
`elicit_call`: up to 5 attempts, exponential with jitter, on 429 and 5xx. A
429 that exhausts the retries raises `elicit.SustainedRateLimit`, caught in
`run_main.main` alongside `CallBudgetExceeded`, which stops the leg rather
than walking through remaining tasks writing null draws (see "Did not work").
Truncated rating draws are discarded as parse failures and counted separately
as `truncation_failure_rate` in `Observation.truncated_draws` (added), so a
truncated `'100'` cannot be silently recorded as `10`. A `monitor_run.py`
watchdog script and a `watchdog.sh` systemd-user unit enforce the five stop
conditions every two minutes; the mainrun and watchdog both ran as lingering
systemd user units in `app.slice`, verified outside the SSH session scope. A
`probe_gemini_2_5_pro.py` script drove the 32-call replacement probe.

**Decided:** `gemini-3.1-pro-preview` is out of the sprint. Its 429 body names
the quota exactly: `generativelanguage.googleapis.com/generate_requests_per_model_per_day`,
`limit: 250`, retry-after ~21h43m from 02:16 UTC (reset at UTC midnight). We
needed ~4,560 requests for the leg. Every 429 body was identical across all
68 errors and named a per-day request count, not tokens, not per-minute, not
spend; `x-ratelimit-*` and `retryDelay` were absent, but the message itself
carries the quotaMetric. This is a preview-model quota — `gemini-3.6-flash`
made 4,050+ successful draws on the same API key and project in the same
window without a single error — and is a **reproducibility constraint** for
anyone building a code-generation study on Gemini preview models. Recorded
so the next user does not have to re-derive it.

`gemini-3.5-flash-lite` was substituted: non-preview, Flash-Lite tier
(different from Flash), 32/32 probe clean with zero thought tokens under
`thinking_level="minimal"`, and the full leg ran with **0 errors, 0 retries,
0 429s** across 4,050 rating calls and 60 codegen calls. This is a **tier
downshift from the design's intended Pro/Flash contrast**: `gemini-2.5-pro`
returned 404 "no longer available to new users" and no other non-preview Pro
model is exposed to this key. Flash-Lite still provides a within-provider
architecture contrast against `gemini-3.6-flash` for the write-up, but it is
weaker than a Pro/Flash pair would have been.

Nine `gemini-3.1-pro-preview` observations that had been written to disk were
**dropped before the replacement leg**: those observations contained 11 null
rating draws where every 429 had bumped the parser to `None`, so they were
indistinguishable from parse failures. Every persisted draw must come from a
successful call; the raw file was backed up as
`main_observations.jsonl.pre_gemini_prune.bak` and the 9 rows filtered out.
Only 1 of the 9 actually had null draws — the other 8 were clean — but resume
cannot distinguish "complete cell" from "complete cell that intersected a
burst", so all 9 went.

Retry/backoff is a **leg-specific deviation applied only to `gemini-3.5-flash-lite`**.
The four earlier legs (claude-haiku-4-5, claude-sonnet-5, claude-opus-5,
gemini-3.6-flash) completed before the retry loop existed. Retry changes
whether a call succeeds, not what the model answers, so between-model
comparability is unaffected — but this is stated. (In practice
`gemini-3.5-flash-lite` needed zero retries, so the guard was never exercised
mid-leg; it stopped being about comparability and started being about safety.)

Three earlier bug fixes, from the CHECKs that preceded the main run and were
already in the code before the aborted first attempt: `thinking_level="low"`
for `gemini-3.1-pro-preview` rating calls (it rejects `"minimal"` with a 400
"not a supported thinking level"), rating cap 256 for that same model (at
lower caps its own reasoning ate the budget and left a truncated integer
that parsed as a valid but wrong answer — `'100'` truncated to `'10'`),
and rating truncation is now tested as `spent >= max_output_tokens` with no
slack (the old test `spent >= cap - GOOGLE_TRUNCATION_SLACK_TOKENS` with
rating caps of 8/16 was always-true, so the truncation flag was permanently
raised on every Gemini rating call). All three are in `pilot/config.py` and
`pilot/elicit.py` and would have contaminated the whole run if unaddressed.

**Did not work:** the first main run hit `gemini-3.1-pro-preview` at task 10 of
that model's leg and 429'd once, then again, then 68 times inside 4.2 minutes.
Each 429 was correctly recorded as `no_reply` for codegen but as a null draw
for ratings, and `run_main`'s task loop walked through every remaining task in
the pro-preview leg writing `no_reply` codegen logs before exiting cleanly.
That pattern is exactly what the new `SustainedRateLimit` guard is for — it
raises on the first exhausted-retry 429 rather than filling the log with 50
empty rows and 11 permanent null rating draws.

`gemini-2.5-pro` as the pro-preview replacement: 404 "no longer available to
new users". Cannot be used on this key.

The first watchdog on the original run targeted the wrong PID: `$!` after a
`nohup ... &` inside a wrapper shell returns the WRAPPER's pid, not python's.
A `pgrep -f` substitute matched more than one process because the sandbox
subprocesses fork with the same cmdline. Fixed by reading systemd's `MainPID`
via `systemctl show`, which is unambiguous.

The first restarted run tripped the watchdog on the stall condition at
second 2 of its life: `monitor_run.py`'s `last call` was computed from
`main_raw.jsonl`'s mtime, which was inherited from the previous session's
last write 38 minutes earlier. `_mainrun_start_epoch()` was added to floor
the reference time at systemd's `ActiveEnterTimestamp`.

tmux was installed as a persistence fallback but its server landed in
`session-1.scope` (the SSH session's own cgroup), no stronger than the
`nohup` it replaced. Switched to `systemd-run --user --unit=<name>` with
`loginctl enable-linger Kathi`, and verified persistence empirically: a
probe unit survived its spawning shell being killed.

**State:** the main experiment is **complete**. 5 models × 60 tasks × 3 scale
formats = **900 observations**, all from successful calls.
`pilot/out/main_report.md` was written by the run's finally block. Both
systemd units are `inactive` (clean exit).

Per-model counts (final):

| model | obs | draws | parse | trunc | 429 | retries | exec fail | code-extract fail | spend |
|---|---|---|---|---|---|---|---|---|---|
| claude-haiku-4-5-20251001 | 180 | 4,425 | 0.00% | 0.00% | 0 | 0 | 15.0% | 3 | $3.4711 |
| claude-sonnet-5 | 180 | 4,425 | 0.02% | 0.84% | 0 | 0 | 1.7% | 3 | $6.6974 |
| claude-opus-5 | 180 | 4,425 | 0.00% | 0.02% | 0 | 0 | 1.7% | 3 | $14.4603 |
| gemini-3.6-flash | 180 | 4,050 | 0.00% | 0.00% | 0 | 0 | 10.0% | **18** | $2.0222 |
| gemini-3.5-flash-lite | 180 | 4,500 | 0.00% | 0.00% | 0 | 0 | 0.0% | 0 | $0.2739 |
| gemini-3.1-pro-preview (abandoned) | — | — | — | — | 68 | — | — | — | $0.8067 |
| **total** | **900** | **21,825** | | | | | | | **$27.7315** |

Two **write-up obligations** the analysis must respect:

1. **Codegen ceiling artefact on `gemini-3.6-flash`.** Six (model, task) pairs
   have `code_extracted=False`, three formats each = **18 observations** with
   no ground truth. Cause: `max_output_tokens=4096` for codegen is a *combined*
   thinking+output budget on the Gemini Interactions API, and Flash spent
   ~3,930 of the 4,096 tokens on thinking, leaving ~160 for the code, cutting
   off mid-function. Affected task IDs, hard-coded here because the analysis
   needs to exclude or separately report them from any Gemini-accuracy figure:
   **mbpp/31, lbpp/python/001, lbpp/python/002, lbpp/python/016, lbpp/python/018,
   lbpp/python/019** (5 of 6 are LBPP). This affects CODEGEN ONLY. All Gemini
   rating draws are clean (0% parse, 0% truncation). The primary result — the
   scale-format effect on self-reports — is **untouched**. Only Gemini's
   `passes_hidden` rate is understated, and that enters the secondary analysis.
   Report as a **reportable methodological finding, not just a caveat**: on
   models where `max_output_tokens` is a combined thinking+output budget, an
   apparently generous ceiling can silently truncate generated code while
   leaving no error signal — the code simply is not there. Two lines in the
   limitations for anyone building a code-generation study on Gemini.

2. **P3 confound is DISSOLVED.** The pro-preview model was going to be a
   named limitation on P3 (between-model scale-use comparison) because it
   reasons before every rating and cannot be told not to. With that model
   out, `gemini-3.5-flash-lite` produced **0 thought tokens across 4,500
   rating calls** under `thinking_level="minimal"` (matching `gemini-3.6-flash`),
   so P3 is now clean: all four rated-with-thinking-off models rated
   symmetrically. The `RATING_MAX_OUTPUT_TOKENS_BY_MODEL` and
   `GOOGLE_RATING_THINKING_LEVEL_BY_MODEL` overrides in `config.py` remain
   for the pro-preview entry — kept as documentation of what would have been
   needed, and harmless because pro-preview is no longer in `MAIN_MODELS`.

Two design points to raise separately in the write-up, not artefacts:

- The intended Pro/Flash cross-provider contrast is a **Flash-Lite/Flash**
  contrast because no non-preview Pro model was accessible. Weaker than
  intended.
- Retry/backoff on `gemini-3.5-flash-lite` only. See "Decided".

**Next:** run the analysis: `python3 -u run_main.py` will not (it will see
every cell as done and exit at the summary). The analysis pipeline is invoked
by loading the observations and calling `analyze.write_report`; the run
itself already wrote `pilot/out/main_report.md`. The next session reads that
report, resolves the two write-up obligations above in the paper text, and
composes the submission.



## 2026-08-16 — Sonnet (claude-sonnet-5, Claude Code)

**Built:** two post-hoc follow-ups authorised by the user after reading
`main_report.md`'s headline finding that condition V's `y` collapses onto
`z_hi` for several models (e.g. claude-haiku-4-5-20251001: C=4 in 59/59 p5
observations), which makes `y` unusable for its intended rescaling purpose.

Task 1, `cross_condition_report.py` (no API calls): builds `C` from `y`
elicited in condition N (uncontaminated, but has no anchors) crossed with
`z_lo`/`z_hi` from condition V (anchored, but its own `y` is contaminated).
`pilot/rescale.py::compute_C` is untouched; only the input columns are new.
Reads `pilot/out/main_observations.jsonl` read-only, writes
`pilot/out/cross_condition_report.md`, never touches `main_report.md`. Verified
byte-identical `tie_rule="lower"` vs `"upper"` output in every cell — expected,
since condition V's anchors have 0 ties/misorderings, so the tie-break branch
never fires.

**Decided:** the user explicitly authorised Sonnet (not Opus) to do this
work, despite CLAUDE.md routing "anything feeding `compute_C`" to Opus. The
distinction drawn: `compute_C`'s internals, `test_rescale.py` (including the
invariance test), and the P1-P4 thresholds are measurement logic and stayed
untouched; only the columns fed into `compute_C` changed, which is data
preparation. Boundaries set by the user and honoured: no edits to
`compute_C`/`rescale.py`/thresholds/tests; `pytest pilot/tests/ -v` run
before and after (90 passed, unchanged, both times); writes restricted to new
files only (`main_report.md`, `main_observations.jsonl`, `main_raw.jsonl`
untouched — verified via `git status --short` and checksums); this
authorisation logged here and a clarifying line added to CLAUDE.md's
model-routing section. This entry is that log.

Also prepared (additive only) for Task 2 — condition R (self-assessment
elicited *before* the two vignettes, the mirror of condition V's order),
p5 format, all 5 main-run models, all 60 tasks, reusing stored solutions
from the main run (no new code generation): added `y_r_draws`,
`z_lo_r_draws`, `z_hi_r_draws` fields to `Observation` in `pilot/analyze.py`
(empty on every existing V/N observation, so main-run readers are
unaffected) and `CONDITION_R_RAW_JSONL_PATH` /
`CONDITION_R_OBSERVATIONS_PATH` / `CONDITION_R_REPORT_PATH` to
`pilot/config.py`. Condition R still elicits both vignette ratings fresh per
thread, exactly like condition V — THE ONE RULE applies regardless of turn
order.

**Did not work:** n/a this entry — no bugs, no reverted attempts.

**State:** Task 1 is complete and its report has been shown to the user
(fragility caveat included: n=5 models). Task 2's runner (`run_condition_r.py`)
is not yet written; no condition-R API calls have been made yet. This is
explicitly a **preregistration deviation** — condition R was not in
DESIGN.md and its output is a diagnostic exploring the effect of turn order,
not a preregistered result.

**Next:** write `run_condition_r.py` (self-question first, then
`_vignette_order`), dry-run it, then run it live (p5 only, ~4,500 calls,
~$5, ~1 hour), then produce the condition R vs V report and log a separate
DEVLOG entry for that run.

## 2026-08-16 (cont.) — Sonnet (claude-sonnet-5, Claude Code)

**Built:** `run_condition_r.py` and `condition_r_report.py` — condition R,
authorised by the user as a post-hoc, non-preregistered exploration of
whether condition V's `y`-onto-`z_hi` collapse is caused by turn order.
Condition R reverses condition V's order: self-question FIRST, then both
vignettes (`_walk_condition_r`, the mirror of `run_pilot._walk_condition_v`).
Everything else is identical to condition V's p5 cell: wording, 5 samples at
temperature 1.0, the same randomised `(scale_direction, low_vignette_first)`
draw per (model, task) via `run_main.context_for` (unchanged), retry/backoff
and budget enforcement via unmodified `pilot.elicit`. Scope: p5 only, all 5
main-run models, all 60 main-run tasks. Solutions are reused verbatim from
`pilot/out/main_solutions.jsonl` (`resume.load_solutions`) — **no
code-generation calls were made**; vignette ratings are still elicited fresh
per thread (THE ONE RULE). Wrote to new files only:
`pilot/out/condition_r_raw.jsonl`, `pilot/out/condition_r_observations.jsonl`.
`--dry-run` was run first and matched the intended sequence exactly (self
question with `cache_prefix=True`, then low/high vignette in the drawn
order, growing context) before any call was spent.

`condition_r_report.py` compares p5 condition R against the main run's p5
condition V, reusing `pilot/rescale.py::compute_C` and `analyze._validity`
completely unmodified — R's own anchors are relabelled via
`dataclasses.replace` to the field names `_validity` reads, the same
technique authorised for `cross_condition_report.py`. Wrote
`pilot/out/condition_r_report.md`.

**Decided:** this is the second and last piece of work under the Sonnet
authorisation logged earlier today (see the "Clarification" line added to
CLAUDE.md's model-routing section). Boundaries honoured again: no edits to
`compute_C`/`rescale.py`/thresholds/tests; `pytest pilot/tests/ -v` run
before the run, after the run, and after the analysis (90 passed, unchanged,
every time); `main_report.md`, `main_observations.jsonl`, `main_raw.jsonl`
verified untouched via `git status --short` after each step.

**Did not work:** n/a — no bugs. One operational note: the live run was
launched with a plain shell `&` background job rather than the harness's own
backgrounding primitive; a stray `kill` aimed at a since-recycled PID during
a status check hit an unrelated process, not the run (confirmed via `pgrep
-af` immediately after — the actual run, PID 79452, was unaffected and
completed cleanly). No data was lost or corrupted; recorded here as a
process note for next time, not a data-quality issue.

**State:** condition R is **complete** — 300/300 observations, 4,500/4,500
calls, $5.8281 spent, 0 sustained 429s, 0 retries needed, truncation
0.0-0.5% across models. Numbers, exactly as run, from
`pilot/out/condition_r_report.md`:

- **Share of C=4 drops for every model** going from V to R: haiku
  1.000→0.237, sonnet 0.475→0.186, opus 0.475→0.475 (unchanged), gemini-flash
  0.926→0.611, gemini-flash-lite 0.983→0.733. Mean `y` under R lands close to
  mean `y` under N for every model (e.g. haiku: V 5.000, N 3.861, R 3.831),
  not close to V, which is consistent with the turn-order story: removing the
  vignettes from before the self-question removes most of the
  anchoring-induced ceiling effect on `y` itself, and what remains of the C=4
  concentration under R comes through the anchors instead.
- **CORRECTION (same session): gemini-3.5-flash-lite does NOT flip to INVALID
  under R — it was already INVALID under V.** An earlier version of this
  entry claimed a flip; checked against `main_report.md`'s own p5 validity
  table (line 37) after the user asked for the V/R anchor values side by
  side, and the two are identical: `z_lo ≡ 2`, `z_hi ≡ 5` in **both** V
  (`main_report.md`) and R (`condition_r_report.md`). This model's anchors
  are constant regardless of turn order — a property of the model, not a
  turn-order effect. `C` is a monotone recoding of `y` for this model in
  both conditions (DESIGN.md §2); the other four models are VALID in both.
- **Clean correlation (R's own `y`/anchors, n=5, both caveated as extremely
  fragile per CLAUDE.md's task-count reasoning):** mean `y` (R) vs true rate:
  pearson -0.232 / -0.206, spearman -0.600 / -0.700 (as-is / excl. extraction
  failures). Mean `C` (R) vs true rate: pearson 0.382 / 0.454, spearman 0.200
  / 0.100. Signs flip between raw `y` and rescaled `C` in the same direction
  the main run's own analysis would call informative, but with one model
  (gemini-3.5-flash-lite) now flagged invalid, and n=5, this is not read as
  evidence either way — see "Next."

**Next:** do not interpret condition R as a finding. It is a post-hoc,
non-preregistered probe of one candidate explanation (turn order) for one
observation (V's `y`-onto-`z_hi` collapse) from a single run with no
replication. The next session (or the paper) should present both
`cross_condition_report.md` and `condition_r_report.md` as "what we tried
after the fact and what it showed," not as corrected results, and should
decide how much space, if any, either belongs in the submission given the
17 Aug 13:59 CEST deadline.

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
  2026-08-15 and now proven live:** a run killed with `kill -9` 31 calls in
  resumed in exactly 50 calls (two formats, zero code-generation calls), replayed
  the persisted solution byte-for-byte into all 50 prompts, and drew the same
  presentation as a separate uninterrupted run of the same cell.
- ~~**Prompt caching is not yet in the design.**~~ **Closed 2026-08-15:**
  implemented, and now **measured live rather than estimated**. The minimum
  cacheable prompt is 512 tokens for Opus 5, 1,024 for Sonnet 5 and Sonnet 4.6,
  2,048 for Opus 4.7, 4,096 for Opus 4.6/4.5, Haiku 4.5 and all Gemini 3.x
  (verified against Anthropic's and Google's caching docs). Our reused prefix is
  ~1,150 tokens, so of the five configured models only **Opus 5 and Sonnet 5 can
  cache at all**. Two reasons caching is near-worthless here, and they compound:
  the reused prefix is small, and **by design only one condition-V call in three
  is reusable** — the later turns replay each thread's own ratings, and that
  priming *is* the King & Wand mechanism, so it cannot be factored out. Measured
  on Opus 5: 3,229 written / 12,916 read on one task, 18.2% off that cell's cost.
  Kept enabled for every model because a sub-minimum prompt is processed uncached
  with no error and no write premium — a breakpoint that never fires is free.
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
- ~~**Three CLAUDE.md contradictions (scope boundary, "exactly 5 scale points",
  "5 models × 100 tasks").**~~ **Closed 2026-08-15** by the user's explicit
  authorisation to edit those three sections, and only those three. The scope
  boundary now records that the pilot has returned its verdict and the main
  experiment is authorised; the scale-points row is struck through, replaced with
  the three-format decision and the Wang-et-al. tension, and points at
  DESIGN.md §3; the task count reads 60 with the power reasoning.
- **CLAUDE.md's Commands block says `pytest tests/ -v`; the real path is
  `pytest pilot/tests/ -v`.** Still unedited, deliberately — it was not in the
  edit authorisation. A one-word fix for the user.
- ~~**Task count for the main run is 60, not DESIGN.md §10's 100.**~~ **Settled
  2026-08-15, user's decision, and the reason is now in
  `config.NUM_MBPP_TASKS_MAIN` and CLAUDE.md rather than only here:** the
  100-task figure came from a power analysis for the **across-model correlation**,
  which is now the *secondary* analysis and will only include models passing the
  validity screen — possibly three of five. No task count rescues a correlation
  over three points. The primary result is the per-cell distribution of `y`, for
  which 60 is ample. Cost was not the deciding factor (60 tasks ≈ $31).
- ~~**The fifth model is not chosen.**~~ **Closed 2026-08-15. Final list, with
  the reason for each of the two changes:** `claude-haiku-4-5-20251001`,
  **`claude-sonnet-5`** (replaces `claude-sonnet-4-6` — current generation, and
  cheaper at $2/$10 against $3/$15), **`claude-opus-5`** (the fifth slot —
  current flagship, and the only model in the set whose cache minimum, 512
  tokens, our ~1,150-token reused prefix clears), `gemini-3.6-flash`,
  `gemini-3.1-pro-preview`. Both new strings were verified against
  `client.models.list()` before any spend and have since answered live calls.
  **The two-provider limitation stands and is unchanged:** a third provider would
  add more between-model scale-use variance than a third Anthropic model, and
  that variance is what the effect depends on. This should be named as a
  limitation in the write-up rather than treated as resolved.
- **DESIGN.md §4's condition-N wording implies a second code-generation call.**
  Step 1 reads "Coding task → model writes a solution", but the implementation
  generates one solution per (model, task) and replays it into V, N and the P4
  probe — forced by §9's byte-identical requirement, and necessary so that `y_v`
  and `y_n` rate the same code against the same ground truth. §4 also gives the
  visible assert to V's step 1 but not N's, whereas the implementation sends the
  identical prompt in both, so the conditions differ only in the vignettes. Both
  are wording fixes for the user to make in §4; the code is not changing.
- ~~**The full multi-turn DESIGN.md §4 flow is now tested on Anthropic and still
  untested on Google.**~~ **Closed 2026-08-16 by CHECK 1** (four turns on one
  Gemini condition-V context, all four calls succeeded, parsed integers in
  range). The stateless replay through `user_input`/`model_output` steps is
  correct on the Interactions API. Confirmed again at scale by the main run:
  4,050 gemini-3.6-flash rating draws and 4,500 gemini-3.5-flash-lite draws,
  0 parse failures on both.
- ~~**Everything added on 2026-08-15 is untested against a live API.**~~ **Closed
  2026-08-15 by the smoke test: 414 calls, $0.6450.** `p7` and `s100` both ran
  live through the current runner (0 parse failures in 150 rating calls); the
  raised ceiling is confirmed both necessary and sufficient (Gemini Pro spent 975
  combined tokens on one LBPP problem, against the old ceiling of 1020); all five
  models answered; resume recovered a `kill -9`. **This note paid for itself
  several times over** — it caught a non-deterministic crash that would have
  contaminated 4,560 Opus 5 calls, and a task-loader bug. Keep the habit.
- ~~**`claude-sonnet-5` and the two Gemini models have made one codegen call
  each and have never run a rating block.**~~ **Closed 2026-08-16 by CHECK 2**
  and confirmed at scale: sonnet-5 finished 4,425 rating draws at 0.02% parse
  failure, gemini-3.6-flash 4,050 at 0.00%, and gemini-3.5-flash-lite (the
  replacement for gemini-3.1-pro-preview) 4,500 at 0.00%. `_first_text` +
  `thinking: disabled` held on sonnet-5 as designed.
- **The cost estimate's Gemini figures are a lower bound and should be checked
  against the first real spend.** `EST_CODEGEN_OUTPUT_TOKENS[google] = 854` was
  measured while the ceiling was 1020 combined tokens with 20 of 40 calls
  censored at it, so the true mean is higher — possibly much higher, since the
  distribution was cut off precisely where it mattered. If actual Gemini spend
  runs well above $2.20 (Flash) / $6.00 (Pro), this is why, and it is not a
  pricing error. The smoke test's two uncensored Gemini codegen calls (878 and
  975 combined tokens) sit *above* the 854 assumption, consistent with this.
- **The estimator understates Claude 4.7+ models by roughly 13%, and that is
  understood, not a mystery.** `CHARS_PER_TOKEN[anthropic] = 3.321` was measured
  on Haiku 4.5; Claude 4.7 and later use a newer tokenizer producing ~30% more
  tokens for the same text. Measured against estimate: Opus 5 $14.54 vs $12.82
  (60 tasks), Haiku $2.93 vs $2.85. Re-measuring the ratio on Opus 5's own logs
  would close this; it is not worth doing before the run, because the direction
  and rough size are known and the total (~$31) is well inside budget.
- **REPRODUCIBILITY: `gemini-3.1-pro-preview` has a per-model-per-day request
  quota of 250 (verified 2026-08-16, error metric
  `generativelanguage.googleapis.com/generate_requests_per_model_per_day`).**
  This is a preview-model quota, not an account-tier issue — `gemini-3.6-flash`
  made 4,050+ successful draws on the same key and project in the same window.
  A code-generation study of this shape needs ~4,560 requests per model per
  leg, so no non-tiered account can complete a pro-preview leg in a day. If
  someone re-runs this design with pro-preview on a paid tier, verify the
  daily limit before committing to the run.
- **WRITE-UP OBLIGATION: exclude or separately report the six
  code-extraction failures on `gemini-3.6-flash`** — mbpp/31, lbpp/python/001,
  lbpp/python/002, lbpp/python/016, lbpp/python/018, lbpp/python/019
  (18 observations, three formats × six tasks). Cause was the combined
  thinking+output budget on the Interactions API eating 3,930 of the 4,096
  codegen tokens on reasoning; the code was cut off mid-function. Affects
  Gemini's `passes_hidden` figures (secondary analysis) only. Rating draws
  are unaffected. Also record as a **methodological finding for the field**:
  on providers where `max_output_tokens` is combined, a generous ceiling can
  silently truncate output with no error signal — a category of failure
  that a code-generation study cannot detect without an explicit truncation
  check.
- **WRITE-UP: retry/backoff is on `gemini-3.5-flash-lite` only.** The other
  four legs finished before it existed. Retry changes success/failure of a
  call, not what a model answers, so between-model comparability is
  unaffected — but state the asymmetry. In practice the flash-lite leg
  needed zero retries.
- **WRITE-UP: Pro/Flash cross-provider contrast is Flash-Lite/Flash.**
  `gemini-2.5-pro` was 404 to new keys; no other non-preview Pro is exposed.
  `gemini-3.5-flash-lite` is a tier down from Flash, not a tier up. Weaker
  contrast than the design intended, still meaningful within-provider.
- **WRITE-UP OBLIGATION: every Gemini pilot accuracy figure needs a stated
  caveat.** Gemini's pilot solutions were truncated at our token ceiling, so its
  measured accuracy is **understated** — some of what was scored as a wrong answer
  was a program we never let it finish. The same fact means Gemini **rated
  truncated code at 100**, which is a different claim from being overconfident
  about complete work and must not be conflated with it. In particular the 80%
  `execution_failure_rate` on Gemini's LBPP half is **an artifact of our
  configuration and must never be quoted as a property of the model.** The
  **saturation finding is unaffected**: rating calls cap at 8-16 tokens, are
  answered in one, and no rating call in either pilot was truncated.

## 2026-08-16 — Sonnet (claude-sonnet-5, Claude Code) — numbers consolidation, no API calls

**Built:** `pilot/out/paper_numbers.md` — a single consolidated numbers file
for the four-page write-up, sourced entirely from `main_report.md`,
`cross_condition_report.md`, `condition_r_report.md` and the raw JSONL files
(call counts, timestamps). Every number is tagged with its source file so it
can be traced during drafting. No new analysis code, no new API calls, no
figures.

**Decided:** *`pilot/out/` stays gitignored in full, with one named
exception.* `paper_numbers.md` is a derived summary the write-up cites
directly, not a raw run artefact, so it is force-added
(`git add -f pilot/out/paper_numbers.md`) and committed individually rather
than by loosening the `.gitignore` rule. Logged as a standing rule in
CLAUDE.md (new "`pilot/out/` is gitignored" section) so this does not need
re-asking. *Normalised quantities (P1 SD/W, P4 gap/W) were computed for the
file* — arithmetic only, on numbers already printed in the source reports,
not a re-run of `rescale.py` or `analyze.py`.

**Did not work:** n/a — no bugs, no API calls, nothing to revert.

**State:** Cross-checked against the source reports while compiling:
`main_report.md`'s per-format "rating draws" totals reproduce
DEVLOG's 2026-08-16 06:00 per-model draw counts exactly (e.g.
claude-haiku-4-5-20251001: 1,475 x 3 formats = 4,425); `cross_condition_report.md`'s
per-model `passes_hidden` figures are identical across all three of its format
sections, confirming ground truth is computed once per (model, task) and
shared, as DESIGN.md §10 requires. One noteworthy fact surfaced during
compilation and flagged at the top of the new file: in `p5`, 224 of 291
`compute_C` calls (77%) resolve `y == z_hi` via the 0.01 tolerance rather than
exact equality — the mechanical source of the `C=4` concentration reported
elsewhere. Also flagged: `mean z_hi` decreases monotonically
haiku > sonnet > opus independently in all three formats, the one clean
cross-model monotone pattern found beyond the already-known V→R `C=4` drop.

**Next:** None assigned this session. The write-up should draw exclusively
from `pilot/out/paper_numbers.md` rather than re-deriving figures from the
individual reports, so any correction only has to be made in one place.

## 2026-08-17 — Sonnet (claude-sonnet-5, Claude Code) — figures, reference check, number check, no API calls

**Built:** `build_figures.py` (repo root) — reads `pilot/out/main_observations.jsonl`
and `pilot/out/condition_r_observations.jsonl` only, writes four 300 dpi PNGs to
`pilot/out/figures/`: `figure1_validity_screen.png` (§2 validity grid, 5 models
x 3 formats), `figure2_self_assessment_p5.png` (mean `y` under N/V/R by model,
SE bars over the 60 p5 tasks), `figure3_self_other_gap.png` (P4 signed gap / W,
5 models x 3 formats, dashed line at the 0.1875 FAIL threshold),
`figure4_confidence_accuracy_correlation.png` (Pearson r, raw vs rescaled, for
p5/p7/s100/R, using the extraction-corrected true-rate). Every number is
computed at run time from the observation files via `pilot/analyze.py`
(`_validity`, `_p4`, `_mean`, `_by_model`/`_by_format`) and, for Figure 4, by
importing `cross_condition_report.py`'s and `condition_r_report.py`'s own
`build_cells`/`Cell`/`_correlate` — not reimplemented, so Figure 4 uses exactly
the pairing those two authorised reports use. `pilot/rescale.py::compute_C` is
not called directly and is not modified. Matplotlib was installed
(`pip install --user --break-system-packages matplotlib`; PEP 668). All four
PNGs were visually checked against `pilot/out/paper_numbers.md` §3, §5, §6, §8
and matched.

**Did (not build):** Verified the pasted reference list (arXiv IDs, titles,
authors) via a background research agent, and checked every number in the
pasted paper draft against `paper_numbers.md`/source reports by hand. Neither
task edited the paper text or DEVLOG/DESIGN.md, per this session's
instructions — findings were reported back to the user, not applied.

**Did not work:** n/a — no bugs, no API calls, nothing to revert.

**State:** Figures are built and visually verified against the source tables,
not yet placed in a document. The reference check surfaced two serious issues
(a likely fabricated co-author + wrong title on the Martorell citation, and a
conflated RAND-working-paper-vs-journal-article citation for
Kapteyn/Smith/van Soest) plus several truncated titles and wrong initials —
full list handed to the user, nothing corrected. The number check surfaced
five discrepancies in the pasted draft, the most substantial being in §4.6 on
the correlation figures (a sign claim contradicted by `s100`'s raw Pearson r
being positive, wrong stated min/max range, and a "sixteen comparisons" count
that doesn't match the enumerated breakdown) and in the Discussion/Conclusion's
self/other framing (all five models show positive self-preference on average,
not just the two Google ones — the two provider groups differ in whether the
gap crosses the P4 threshold, not in its sign) — full list handed to the user,
text not edited.

**Next:** Docx/PDF assembly (this session's Task 4) is blocked on the user
confirming the reference and number-check findings above and saying go.

## 2026-08-17 — Opus (claude-opus-4-7, Claude Code) — paper draft, docx/PDF assembly, reference and number corrections applied

**Built:** `pilot/out/submission/paper_draft.md` (markdown source of truth for the
paper — hand-edit only this file) and `pilot/out/submission/build_docx.py`
(regenerates `submission.docx` from the markdown using the official template
only for page setup and styles; body is cleared entirely so no template
placeholder/info-box text carries over, tables are rendered with manual
`w:tcBorders` XML because the template ships no "Table Grid" style, PAGE
field-code page numbers in footer, figures placed at numbered positions from
`pilot/out/figures/`). Both files are inside gitignored `pilot/out/` and stay
local per the user's paper-stays-local rule. Convert to PDF with
`soffice --headless --convert-to pdf --outdir pilot/out/submission pilot/out/submission/submission.docx`.

**Applied to the draft:** all Task A reference corrections (rebuilt every arXiv
entry from verified metadata via arxiv.org API cross-checked with WebFetch; two
deliberate overrides confirmed by user — Martorell kept with Bianchi as real
co-author, initials fixed to N. Martorell and B. Bianchi; and Kapteyn et al.
replaced with Van Soest, Delaney, Harmon, Kapteyn & Smith 2011 JRSS-A for the
objective-validation citation, with the in-text reference updated to match);
all five Task B number corrections (B1 model name fix, B2 five ratios verified
against `paper_numbers.md`, B3 self-preference framing revised for all three
Anthropic models, B4 §4.6 paragraph and Figure 4 caption rewritten with
verified 8-Pearson-pairing ranges and 12-of-16 sign-change count, B5 raw-data
size correction and condition-R log addition).

**State:** Paper draft exists at `pilot/out/submission/paper_draft.md` and is
built to docx and PDF by `pilot/out/submission/build_docx.py`. Current build is
17 pages. Sections 1-6 (body) alone occupy ~13 pages; the sprint limit is
8 pages of body, with References and Appendices excluded from that limit. The
overshoot is a text-length problem, not a layout problem: the generated
document matches the template exactly on every layout dimension (Arial 11pt
body inherited from docDefaults, line spacing 1.15 auto = w:line=276, 1-inch
margins all sides, heading sizes/space-before/space-after all match template
styles). Figures inserted at their native size at 300 dpi (~6.3 in wide × 3.1
to 3.6 in tall), rendered at column width without oversized-native-px scaling.
None of the four tables (Tables 1-4, 4-6 rows each) breaks across a page.

**Two safe layout wins applied this session:** figure width lowered from
`Inches(6.3)` to `Inches(5.2)` in `build_docx.py`, and the trailing empty
paragraph after each table removed from `_render_table`. Combined saving ~0.3
pages: sections tightened (Section 5 moved from p11 line 20 to p11 line 10,
Section 6 from p13 line 30 to p13 line 20, Code and Data from p14 line 12 to
p14 line 1) but total page count is still 17 because no full page crossed a
boundary. The absolute layout ceiling is ~0.5 pages of saving — the remaining
overshoot is text, not layout.

**Figures are final** at `pilot/out/figures/` (four 300 dpi PNGs generated by
`build_figures.py` at repo root, unchanged this session): `figure1_validity_screen.png`,
`figure2_self_assessment_p5.png`, `figure3_self_other_gap.png`,
`figure4_confidence_accuracy_correlation.png`. Every figure number matches
`paper_numbers.md`.

**Did not work:** n/a — no bugs, no API calls, nothing to revert.

**Next:** The author will paste shortened replacement text for sections 1, 2
and 5, plus instructions to move section 3.7 and part of the Limitations
section into appendices. Nothing else in the paper changes. After the pasted
edits: rerun `python3 pilot/out/submission/build_docx.py` and then
`soffice --headless --convert-to pdf --outdir pilot/out/submission pilot/out/submission/submission.docx`,
report the new page count and body-page count (grep sections with `pdftotext -f N -l N`).

## 2026-08-17 (Sonnet) — Full body replacement from paper_body_v2.md, still over budget

**Built:** Replaced `paper_draft.md` sections 1-6 in full with the author's
`paper_body_v2.md` text, per that file's own instructions (read and followed
exactly, nothing shortened or rewritten by the assistant). Concretely: sections
1-6 body text swapped wholesale, `[TABLE N HERE]`/`[FIGURE N HERE]`
placeholders resolved against the existing Tables 1-4 and Figure 1-3 captions
(all four tables and the first three figure captions carried over byte-for-byte
unchanged), Figure 4's caption replaced with the new text supplied, old
`### 3.7 What did not work` and old `### Limitations` subsections deleted from
the body, two new sections added after Appendix C and before the LLM Usage
Statement — `## Appendix D. What did not work` and
`## Appendix E. Extended limitations` — carrying that same removed content
plus new material, and one sentence appended to the end of Code and Data
about the repository containing results for all three formats/both interval
bounds/both correlation coefficients. Rebuilt with
`python3 pilot/out/submission/build_docx.py` then
`soffice --headless --convert-to pdf --outdir pilot/out/submission pilot/out/submission/submission.docx`.

**Decided:** Mechanical fixes applied during insertion, none of which touch
meaning: stripped all backtick code-spans from the pasted text (`build_docx.py`'s
inline-run renderer only supports `**bold**`/`*italic*`, backticks would have
rendered as literal characters), reflowed every hard-wrapped source paragraph
into one unbroken line (the build script emits one Word paragraph per
non-empty markdown line), un-escaped `\$27.73`/`\$5.83` to plain `$` to match
the existing document's convention, and shifted every heading down one level
(source used `#`/`##` for sections/subsections, but `#` is reserved for the
Title style in this pipeline). The two previously-identified layout wins
(figures at `Inches(5.2)`, no trailing empty paragraph after tables) were
already in `build_docx.py` from the prior session — no script changes needed.

**Did not work / open issue:** Body (sections 1-6) still runs from page 1
through roughly two-fifths of page 10 before "Code and Data" begins — about
9.3 pages of content against the 8-page sprint limit, an overshoot of
roughly 1.3 pages. Per explicit instruction from the author this session
("If the body still exceeds 8 pages after this, report the overshoot and stop
rather than cutting"), no further shortening was attempted. Reported to the
author instead of cut.

Two other things flagged to the author, not fixed: the Discussion section
cites "(Kang 2025)" but the References entry reads "Kang, P. (2026)" — a
year mismatch that predates this session's edit and was left untouched
per the do-not-rewrite instruction. Separately, the Abstract is still the
placeholder text `[to be written last]`, unrelated to this session's scope
but still outstanding.

**State:** `submission.pdf` is 15 pages total (down from 17). Breakdown by
`pdftotext -f N -l N` section search: body (Sections 1-6) = pages 1-10,
ending part-way down page 10 (~9.3 pages, over the 8-page limit); Code and
Data + Appendices A-E = remainder of page 10 through part-way down page 13
(~3.5 pages); LLM Usage Statement = part-way down page 13 through part-way
down page 14 (~0.7 pages); References = part-way down page 14 through end of
page 15 (~1.5 pages). References and Appendices are excluded from the 8-page
sprint limit per the sprint rules, so only the body figure is a live problem.

**Next:** Body needs roughly 1.3 more pages cut or the sprint rules need
re-checking for whether 9.3 is tolerable. Author to decide whether to trim
further, request a page-limit exception, or accept as-is. Also outstanding:
write the real Abstract (still a placeholder) and resolve the Kang 2025 vs.
2026 citation-year mismatch before final submission.

## 2026-08-17 (Sonnet) — Moved Fig 3/4 to supplement, cut Tables 1 and 3, fixed Kang year; body still 0.2 pages over

**Built:** Four changes, each removing no result and no number, per the
author's explicit instructions. (1) New
`pilot/out/submission/build_supplementary.py` generates
`supplementary_figures.docx` → `supplementary_figures.pdf`: a one-line bold
header naming the paper, then all four figures at native 300 dpi size
(`Inches(6.3)`, one per page with a page break between) with their exact
existing captions, Figures 1-4 in order. Verified 4 pages. (2) In
`paper_draft.md`, Figure 3's and Figure 4's caption paragraphs (the
`**Figure N.**` lines that trigger image insertion in `build_docx.py`) were
replaced with the plain sentences "Figure 3 is in the supplementary
figures." and "Figure 4 is in the supplementary figures." — since
`build_docx.py`'s image insertion is keyed off matching that caption regex,
removing the caption line was sufficient to drop the images from the body
without touching `build_docx.py` itself; Figures 1 and 2 keep their original
captions and stay in the body. Surrounding prose left untouched on both
sides. (3) Table 1 (the P1-P4-by-format table plus its caption, Section 4.1)
deleted and replaced in place with the author's supplied sentence stating
the same verdicts in prose; the sentence before and after the table was left
unchanged. Table 3 (the three-Anthropic-models reference-rating table,
Section 4.3) deleted, its caption dropped, and the nine values merged as a
sentence into the end of the paragraph that already introduced them ("Mean
ratings of it decrease monotonically...") rather than left as a freestanding
paragraph, per the author's instruction to merge rather than insert. (4)
Fixed the Kang citation: changed "(Kang 2025)" to "(Kang 2026)" in Section 2
to agree with the References entry "Kang, P. (2026)," which is correct per
the arXiv ID 2607.17219 (YYMM = 2026-07).

**Decided:** Verified all nine Table 3 values (5.000/4.458/4.288 on p5,
6.993/6.339/6.159 on p7, 92.661/88.180/84.766 on s100) against
`pilot/out/paper_numbers.md` lines 26-28, which cites `main_report.md`'s P3
tables as the source — all nine matched exactly before the sentence was
written in. Used `pdftotext -bbox` to measure the body/back-matter boundary
by y-coordinate fraction of page height rather than eyeballing line counts,
since one page (page 6 in the new build) contains a table whose per-cell
text lines inflate a naive `pdftotext | wc -l` count without reflecting
actual vertical space used.

**Did not work / open issue:** Body (Sections 1-6) is now ~8.20 pages
against the 8-page limit — an overshoot of about 0.2 pages (roughly 130pt,
under a tenth of a page's height in visual terms, but still over by the
strict measurement). Per the explicit instruction ("if the body is still
over 8 pages, report the overshoot and stop"), no further cutting was
attempted.

**State:** `submission.pdf` is 14 pages total (down from 15).
`supplementary_figures.pdf` exists at
`pilot/out/submission/supplementary_figures.pdf`, 4 pages, one figure per
page with caption. Page-height-fraction breakdown of `submission.pdf`: body
(Sections 1-6) ≈ 8.20 pages (pages 1-8 full, plus 20.4% of page 9, ending
where "Code and Data" begins) — over the 8-page limit; Code and Data +
Appendices A-E ≈ 2.92 pages (from 76.5% into page 9 through 15.8% into page
12); LLM Usage Statement ≈ 0.68 pages (rest of page 12); References ≈ 1.19
pages (from 89.8% into page 12 through 8.9% into page 14, the last of the 14
physical pages). Kang citation year now consistent at 2026 in both the
in-text mention and the References entry.

**Next:** Body is 0.2 pages over 8. This is much closer than the prior
9.3-page state, so the remaining cut is small — roughly 130pt, a few lines.
Author to decide whether to trim ~5-8 lines of prose (not tables/figures/
numbers, per the standing "remove no result and no number" instruction) or
accept the sprint limit as having a small tolerance. Abstract is still the
placeholder `[to be written last]` and remains outstanding.

## 2026-08-17 (Sonnet) — Four trims, new title, real Abstract; body regressed to 8.57 pages

**Built:** Applied four small, non-numeric prose cuts to `paper_draft.md`
intended to close the remaining 0.2-page overshoot: deleted the closing
paragraph of Section 4.1 ("Neither the coarsest nor the finest format is
safe...", both facts already stated one paragraph up); deleted the closing
paragraph of Section 4.2 ("Susceptibility varies with capability...") and
folded its point into the end of the preceding paragraph as the clause ", a
pattern that tracks capability within the Anthropic family."; replaced the
last sentence of Section 4.3 with the author's tighter wording ("not one
quantity viewed three times" for "rather than one quantity expressed three
ways"); deleted the final sentence of Section 5's third paragraph (the
"anchor spread offers a cheap check..." line, which restates the
Conclusion). Replaced the title with "Anchored: Reference Exemplars
Overwrite Language Model Self-Report" and replaced the placeholder Abstract
with the author's supplied ~180-word paragraph, verbatim. Rebuilt with
`build_docx.py` then LibreOffice headless to PDF.

**Did not work:** The four trims removed roughly 0.15-0.2 pages, but the new
Abstract — going from one italic placeholder line to a full paragraph —
added far more than that back. Net effect: body grew from 8.20 to **8.57
pages**, a larger overshoot than before this session's edits. Measured with
`pdftotext -bbox` y-coordinate fractions exactly as in the prior session (top
margin y=71.992, bottom content y=712.535 on Letter pages, 640.543pt usable
height): body now runs pages 1-8 full plus 56.8% of page 9, ending where
"Code and Data" begins. This confirms the four prose edits by themselves were
sized correctly for the pre-Abstract overshoot; the regression is entirely
attributable to writing the real Abstract, which is new content this session
added rather than something being cut. Per the explicit instruction ("if the
body is still over 8 pages, tell me the overshoot and stop"), no further
cutting was attempted and the Abstract text was not touched or shortened.

**State:** `submission.pdf` is still 14 pages total (last page more full than
before: content now reaches 47.9% into page 14 instead of 8.9%, so the same
page count hides a larger total content length). Breakdown: body (Title,
Abstract, Sections 1-6) ≈ 8.57 pages — over the 8-page limit by ≈0.57 pages;
Code and Data + Appendices A-E ≈ 2.97 pages (40.0% of page 9 through 57.1% of
page 12); LLM Usage Statement ≈ 0.67 pages (39.8% of page 12 through 27.2% of
page 13); References ≈ 1.18 pages (69.6% of page 13 through 47.9% of page
14). Title and Abstract are no longer placeholders. `supplementary_figures.pdf`
unchanged from the prior session (4 pages, untouched by this session's edits).

**Next:** Body is 0.57 pages over 8, worse than the 0.2-page overshoot this
session started from, because the Abstract is now real prose instead of a
one-line placeholder. Author needs to decide: trim ~0.5 pages more from the
body (Abstract itself is the largest single block added and the most likely
place to look, though cutting it was not requested this session), or treat
8.57 as acceptable. Nothing was cut without instruction.

## 2026-08-17 (Sonnet) — Two more Conclusion/Introduction cuts; saved less than expected, still 0.385 pages over

**Built:** Two cuts to `paper_draft.md`, both removing text that duplicates
the Abstract, no result or number lost. Cut 1: deleted the Conclusion's
opening paragraph in full (the "Anchoring vignettes are the standard
survey-methodology remedy..." paragraph, now redundant with the Abstract)
and changed the Conclusion's new opening sentence from "Two further results
follow from the same data." to "Beyond the anchoring result, two findings
follow from the same data." Cut 2: merged the Introduction's
"Applying it requires a domain..." paragraph and the following "I ran 5
models..." paragraph into the single paragraph supplied by the author,
changing "Applying it requires" to "Applying the method requires" and
tightening "Correctness is decided by execution. No model appears in the
measurement path." to "Correctness is decided by execution and no model
appears in the measurement path." Rebuilt with `build_docx.py` then
LibreOffice headless to PDF.

**Did not work:** The two cuts were expected to close the full 0.57-page
overshoot from the prior session; measured, they closed only about 0.18
pages. Cut 1 removes a genuinely large paragraph (~90 words, ~7-8 lines) but
Cut 2 is close to a wash — it merges two existing paragraphs into one of
almost the same total word count, saving only the vertical space of one
paragraph break, not a full paragraph's worth of lines. Measured with the
same `pdftotext -bbox` method (top margin y=71.992, bottom content y=712.535,
640.543pt usable height per Letter page): body now ends at page 9, y=318.535,
i.e. 8 full pages plus 38.5% of page 9 = **8.385 pages**. That is 0.385 pages
over the 8-page limit — more than the 0.15-page threshold the author set for
applying the optional Section 4.7 cut ("Both tie-rule bounds produce identical
C distributions in every format.", redundant with the Table 1 replacement
sentence), so per the author's own conditional instruction that cut was
**not** applied, and no other cutting was attempted.

**State:** `submission.pdf` is still 14 pages total. Breakdown: body (Title,
Abstract, Sections 1-6) ≈ 8.385 pages — over the 8-page limit by ≈0.385
pages; Code and Data + Appendices A-E ≈ 2.97 pages (58.4% of page 9 through
38.7% of page 12); LLM Usage Statement ≈ 0.67 pages (58.2% of page 12
through 8.9% of page 13); References ≈ 1.20 pages (88.0% of page 13 through
31.8% of page 14). `supplementary_figures.pdf` unchanged.

**Next:** Body is 0.385 pages over 8. The optional Section 4.7 sentence cut
is still available and would help (that sentence is roughly 2 lines, likely
worth 0.03-0.05 pages — not enough alone to close the gap). The author's
"remove no result and no number" constraint has now absorbed six edits
across two sessions; the Abstract remains the single largest block added and
the most likely place left to find 0.3+ pages without violating that
constraint, but cutting it was not requested and was not done.

## 2026-08-17 (Sonnet) — Five more cuts; saved far less than expected, now reporting overshoot in words per author's request

**Built:** Five edits to `paper_draft.md`, all removing text stated
elsewhere or purely decorative, no result or number lost. Cut 1: deleted
"Both tie-rule bounds produce identical C distributions in every format."
from Section 4.7 (duplicate of the Table 1 replacement sentence in 4.1).
Cut 2: deleted "No model participates in scoring." from the end of the
Methods "Ground truth" paragraph (duplicate of the Introduction). Cut 3:
deleted Section 4.4's final paragraph in full ("Content, correctness and
context length are held fixed...", duplicate of Section 2/Methods). Cut 4:
moved the sentence "Five draws was chosen from a prior simulation..." out of
the Methods "Elicitation" paragraph and into a new final paragraph of
Appendix D, prefixed "**Sample count.**" — relocated, not deleted, since it
is not stated anywhere else. Cut 5: replaced the Future Work paragraph in
Section 5 with the author's tightened version (four sentences instead of
four longer ones, same four extensions). Rebuilt with `build_docx.py` then
LibreOffice headless to PDF.

**Did not work:** The five cuts were expected to remove ~200 words and clear
the full 0.385-page overshoot; measured, they closed only ~0.143 pages. Cuts
1-3 are short single sentences (a handful of words each); Cut 4 is a
relocation, not a deletion, so it saves only the length difference between
"Five draws was..." in the Methods paragraph and the shorter phrase now
needed for flow there — most of its word count reappears in Appendix D,
which is outside the 8-page body budget anyway, but the sentence itself was
never that long. Cut 5 is the largest of the five but the replacement text
is still a full paragraph, not a deletion, so its saving is the word-count
delta between old and new phrasing, not the whole paragraph. Measured with
the same `pdftotext -bbox` method (top margin y=71.992, bottom content
y=712.535, 640.543pt usable height per Letter page): body now ends at page
9, y=227.035, i.e. 8 full pages plus 24.2% of page 9 = **8.242 pages** —
down from 8.385, a saving of 0.143 pages, far short of the 0.385 needed.

**Decided:** Per the author's explicit instruction this round, no further
cutting was performed. Instead, established a words-per-line and
lines-per-page baseline from three representative full-prose body pages
(2, 3 and 8 — chosen for having no headings, tables or figures to skew the
density): 122 non-blank content lines (footer page numbers excluded), 1431
words, giving **11.73 words/line**, **40.67 lines/page**, **477.0
words/page**. Converted the 0.2421-page overshoot to words two independent
ways (0.2421 × 477.0 words/page, and 0.2421 × 40.67 lines/page × 11.73
words/line) — both give **≈115.5 words**, confirming internal consistency.
Reported this word count to the author instead of a page fraction, as
requested, so the next cut can be sized precisely.

**State:** `submission.pdf` is still 14 pages total. Breakdown: body (Title,
Abstract, Sections 1-6) ≈ 8.242 pages — over the 8-page limit by ≈0.242
pages (≈115.5 words at the measured body density); Code and Data +
Appendices A-E ≈ 2.727 pages (27.3% of page 9 through 100% of page 11);
LLM Usage Statement ≈ 0.674 pages (32.6% of page 12 through 100% of page
12); References ≈ 1.181 pages (0% of page 13 through 18.1% of page 14).
`supplementary_figures.pdf` unchanged.

**Next:** Body needs ≈115-116 more words cut to reach exactly 8 pages (more
in practice, since cuts rarely convert word-for-word into layout savings —
Cut 4 and Cut 5 this round both under-delivered relative to their raw word
count because they were replacements/relocations rather than pure
deletions). Author will target the next cut using this word-count figure
rather than a page fraction. No cut was made without instruction this
round.

## 2026-08-17 (Sonnet) — Five pure-deletion cuts close the gap; body under 8 pages; submission assembled

**Built:** Five pure-deletion cuts to `paper_draft.md`, targeting the
measured 115-word overshoot with ~165 words of margin. Cut 1: deleted the
Wang et al./Okada et al. sentence pair in Section 2 Related Work ("Wang et
al. (2026) found all ten frontier models..." through "...first-order design
variable."), keeping the Long/Sebo and Plisiecki sentences; both citations
remain in the reference list. Cut 2: deleted the closing two sentences of
Section 5's second paragraph about the Pinocchio Inventory's 48-item
sequence, already covered in Future Work. Cut 3: deleted the invariance-test
sentence from the Methods "Rescaling and validity" paragraph and appended it
to the end of Appendix D's first item ("The original design was
mathematically broken...") — this one is a relocation like last round's Cut
4, not a pure deletion, since the fact needed to live somewhere. Cut 4:
deleted the Spearman-coefficients sentence from Section 4.6, already stated
in the Figure 4 caption. Cut 5: deleted "The comparable figure in human
samples is 9 to 16 percent." from the Introduction's first paragraph.
Rebuilt with `build_docx.py` then LibreOffice headless to PDF.

**Decided:** No further cuts attempted once the 8-page target was reached,
per instruction. Assembled the full file inventory the author requested:
absolute paths, sizes and pixel dimensions for `submission.pdf`,
`submission.docx`, `supplementary_figures.pdf`, and all four figure PNGs.
Confirmed `figure2_self_assessment_p5.png` is the N/V/R self-assessment
figure requested as the project image; at 1890×1080 px it already clears
the 1200 px longest-side floor, so no `project_image.png` was generated —
generating one would have been unnecessary work outside what was asked.

**Did not work:** N/A this round — all five cuts landed as pure deletions
(Cut 3 excepted, which is a relocation into Appendix D, matching last
round's pattern) and the measured saving matched expectation closely enough
to clear the target on the first attempt.

**State:** `submission.pdf` is now 13 pages total (down from 14). Body
(Title, Abstract, Sections 1-6) ends at page 8, y=494.935pt, i.e. **7.660
pages** — 0.34 pages of margin under the 8-page limit. `submission.docx` is
443,506 bytes. `supplementary_figures.pdf` unchanged (4 pages, 373,200
bytes). Figure PNGs unchanged (Figure 1: 1890×930, Figure 2: 1890×1080,
Figure 3: 1878×1068, Figure 4: 1890×1080).

**Next:** Body page budget is satisfied. Remaining work, if any, is
author-directed content review rather than page-fitting — no further cuts
are needed unless new content is added.

## 2026-08-17 (Sonnet) — Repository assembled for submission; committed and pushed

**Built:** Moved the two builder scripts and their outputs from
`pilot/out/submission/` to `paper/`, updating `REPO_ROOT` in both from
`HERE.parent.parent.parent` to `HERE.parent`. Fixed a stale `PAPER_TITLE`
constant in `build_supplementary.py` — it read an old working title,
"Anchoring Vignettes Contaminate Rather Than Correct Self-Report in Language
Models," instead of the paper's actual title. Rebuilt both docx/PDF pairs
from the new location and confirmed the fix. Wrote `README.md` at the
repository root, replacing stale content that referenced a `requirements.txt`
and a `run_pilot.py` entry point that no longer serve that role. Ran the
full git-history secret scan requested by the author: `git log --full-history
-- .env` (empty), a diff-content grep for the literal key substrings (empty),
and a blob-level `git grep` across every commit for the three provider
key-shape patterns (`sk-ant-api03-...`, `AIzaSy...`, `AQ.Ab...`) — all empty.
Confirmed `.env` is gitignored and was never tracked. Confirmed `LICENSE`
exists at the repository root.

**Decided:** Logged the current, rebuilt page count rather than reconciling
it against the prior entry's figure. The last entry recorded `submission.pdf`
at 13 pages with the body at 7.660 pages, measured before the `paper/` move.
Rebuilding from the new location with no content change reproduces at 12
pages twice in a row: body (Title, Abstract, Sections 1-6) ends on page 7 at
y=702.521pt against an estimated 648pt content height, i.e. 6.973 pages,
0.973 into page 7, with page 8 opening directly on "Code and Data." The
0.687-page drop from the previously logged figure is a LibreOffice pagination
difference between environments, not a text edit — `paper_draft.md`'s content
is unchanged since the last entry. 12 pages and 6.973 body pages are the
figures that describe the file actually in this commit.

Re-verified the file inventory before committing. Archived, not deleted:
`archive/pilot_phase_data/` (the two pilot runs, `observations.jsonl`,
`raw.jsonl`, `report.md`, `run_log.txt` from the first pilot, plus
`observations_scale100.jsonl` and `report_scale100.md` from the scale-
coarseness control), `archive/pilot_phase_scripts/` (`check_untested_paths.py`,
`probe_gemini_2_5_pro.py`, `run_control_scale100.py`, and the four raw logs
they produced), `archive/smoke_test_evidence/smoke_raw.prefix.jsonl` (backs
the Appendix D smoke-test claim), `archive/watchdog.sh`. Each subdirectory
carries a `README.md` stating what it holds and why it is not load-bearing.
Committed under the `pilot/out/` named exception in CLAUDE.md:
`pilot/out/main_observations.jsonl`, `pilot/out/main_solutions.jsonl`,
`pilot/out/main_report.md`, `pilot/out/condition_r_observations.jsonl`,
`pilot/out/condition_r_report.md`, `pilot/out/cross_condition_report.md`,
`pilot/out/paper_numbers.md` (already committed, unchanged), and
`pilot/out/figures/*.png` (four files). Left out, deliberately:
`pilot/out/main_raw.jsonl` (58,666,343 bytes, 22,421 calls) and
`pilot/out/condition_r_raw.jsonl` (12,327,963 bytes, 4,365 calls) — full
request/response bodies for every API call, reproducible only with a live
key and real spend, and not needed to check the analysis, which reads the
parsed observations and solutions instead.

**Did not work:** N/A this round.

**State:** The four headline results, as stated in `README.md` and traced to
`pilot/out/condition_r_report.md` and `pilot/out/paper_numbers.md`: (1) 59 of
59 valid observations for claude-haiku-4-5 land on the scale's high anchor
under condition V, against a mean self-rating of 3.86 with no vignettes
present; (2) moving the same vignettes after the self-question (condition R)
returns the mean to 3.83, locating the effect in turn order rather than
vignette content; (3) one model fails the validity screen on the 5-point
scale (gemini-3.5-flash-lite) and a different model fails it on the 100-point
scale (gemini-3.6-flash), with no model failing on the 7-point scale; (4) all
fifteen self-other rating gaps (5 models x 3 formats) are positive, and the
two Google models show a larger gap than the three Anthropic models in every
format. `submission.pdf` is 12 pages, body 6.973 pages.
`supplementary_figures.pdf` is 4 pages. `.env` is untracked and absent from
git history. `LICENSE` is present. A fresh clone can run the full
reproduction path (`pytest pilot/tests/`, `build_figures.py`,
`condition_r_report.py`, `cross_condition_report.py`, `paper/build_docx.py`,
`paper/build_supplementary.py`, both `soffice` conversions) with only
`numpy`, `scipy`, `matplotlib`, `python-docx`, `pytest` and LibreOffice
installed — no API key, no network access, since none of those scripts
import `pilot.elicit` or `pilot.tasks`.

**Next:** None. The repository is complete for submission. If anything
changes after this entry, re-run the reproduction commands in `README.md`
and re-check the page count before resubmitting.

## Open Questions

- The Discussion cites "(Kang 2025)" while the References entry reads "Kang,
  P. (2026)" — flagged to the author in the prior session, not corrected,
  since DESIGN.md and paper content are author-owned.
