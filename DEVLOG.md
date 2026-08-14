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
- **Vignette texts are not written yet.** Their quality determines whether P2
  passes. Constraints: general rather than narrowly technical; both for the same
  problem as each other; that problem must not be one of the 20 tasks.
- **Gemini model selection for the pilot is not fixed.** Use two models as far
  apart in capability as possible, so that a P3 pass is informative.
- **Prompt caching is not yet in the design.** Our sampling pattern sends 5 calls
  with an identical prefix — the ideal caching case (write 1.25×, read 0.1×).
  Roughly two-thirds off input cost, which is ~97 % of spend. Should be added
  before the main run, not needed for the pilot.
- **Task count for the main run assumes 100.** Simulation gives 98 % at 100 vs
  93 % at 60. Revisit only if budget forces it.
