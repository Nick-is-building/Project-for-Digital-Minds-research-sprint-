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

# Open Questions

Add anything unresolved. Remove anything answered. This section is the handover
between sessions.

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
- **Is a misordered anchor pair with `y` outside the crossed region acceptable as
  point-identified?** `rescale.py` returns `C=5` under both bounds for
  `z_lo=4, z_hi=2, y=5`, because `y` is above both anchors regardless of the
  ordering violation. This is more informative than discarding every misordered
  observation, but DESIGN.md §5 reads as though tied/misordered always yields a
  genuine interval. Confirm the reading before `analyze.py` counts misorderings.
- **`tolerance_counts` is process-global and nothing resets or reports it.**
  Whoever writes `run_pilot.py` must call `reset_tolerance_counts()` at the start
  and record the counts at the end, or the DESIGN.md §5 requirement to record how
  often the tolerance fires goes unmet in practice.
- **CLAUDE.md's Commands block says `pytest tests/ -v`; the real path is
  `pytest pilot/tests/ -v`.** Left unedited because CLAUDE.md is the user's
  control document — worth a one-character fix by the user.
- **Prompt caching is not yet in the design.** Our sampling pattern sends 5 calls
  with an identical prefix — the ideal caching case (write 1.25×, read 0.1×).
  Roughly two-thirds off input cost, which is ~97 % of spend. Should be added
  before the main run, not needed for the pilot.
- **Task count for the main run assumes 100.** Simulation gives 98 % at 100 vs
  93 % at 60. Revisit only if budget forces it.
- **`MAX_OUTPUT_TOKENS_DEFAULT` (1024) for code-generation calls is a
  provisional guess**, never exercised against a real code-gen prompt.
  Revisit once the actual code-generation prompt is designed in `run_pilot.py`.
- **The full multi-turn DESIGN.md §4 flow (vignettes + self-question replayed
  in one context) is untested.** Only single-turn rating questions have been
  run so far. `elicit.py`'s Gemini path builds this via explicit
  `user_input`/`model_output` steps (stateless replay, not
  `previous_interaction_id` chaining) to match "fresh context every time" —
  this has not yet been exercised with more than one message in the list.
