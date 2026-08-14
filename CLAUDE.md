# CLAUDE.md

## ⚠️ FIRST ACTION IN EVERY NEW SESSION — NO EXCEPTIONS

Before reading any other file, before answering, before writing any code:

1. Read `DEVLOG.md` **in full**. It carries the current state of the project.
   The last entry tells you what was just done. The "Open Questions" section at
   the bottom tells you what is unresolved.
2. Read `DESIGN.md`. It defines the instrument — scale, question wording,
   rescaling formula, metrics, thresholds. **It is descriptive, not a task list.**
   It does not tell you what to build. Do not start implementing from it.
3. State back to the user, in 3–5 lines: what the last session did, what the
   current state is, and what you understand the next step to be.
4. **Then wait.** The user assigns the work for this session. Do not select the
   next piece of work yourself and begin.

Do not start work until you have done this. A session that begins coding without
reading DEVLOG.md will repeat work, contradict earlier decisions, or reintroduce
a bug that was already fixed.

---

## 🔒 SCOPE — RULE ZERO

This project lives entirely inside this repository directory. Other folders on
this machine belong to unrelated projects. Never read, list, modify, or
reference anything outside this directory. If a path resolves outside it, stop
and ask.

---

## What this project is

We test whether **anchoring vignettes** (King & Wand 2007) can correct the
response-bias problem in LLM self-reports. Meyer, Garcia & Wulff (arXiv:2606.20205)
showed that 81–90 % of between-model variance in LLM self-report instruments is
directional response bias, not content (humans: 9–16 %). The established survey-
methodology fix has never been applied to LLMs, and could never be validated in
AI-welfare research because internal states have no checkable ground truth.

We use code generation as a **calibration domain**: whether a solution is correct
is decided by hidden tests — deterministic, no judge, no opinion. We ask the model
how confident it is, anchor its scale with two vignettes, and test whether the
correction makes self-reports match the truth better.

This is instrument validation. Code is the measuring weight, not the subject.
Precedent: Kapteyn, Smith & van Soest (2007) validated vignette corrections
against objective measurement in humans.

Target: Apart Research Digital Minds Research Sprint, 14–16 Aug 2026,
submission Monday 17 Aug 13:59 CEST. Track 4 (Preference Elicitation Methods).

---

## 🔴 THE ONE RULE THAT PROTECTS THE PROJECT

**Vignette ratings MUST be elicited fresh inside every task context.**

The vignette *texts* are fixed constants. The vignette *ratings* are re-elicited
every single time.

If vignette ratings are constant across observations, `compute_C` becomes a
monotone recoding of the self-report, and every rank-based metric is
**mathematically guaranteed** to show exactly zero change. Verified by simulation:

```
Spearman raw        : 0.35807
Spearman rescaled   : 0.35807
difference          : 0.00000   (exact, not approximate)
```

A pipeline that caches or reuses vignette ratings produces a guaranteed null
result and is worthless. `tests/test_rescale.py::test_invariance` exists solely
to catch this. **Never weaken, skip, or "temporarily disable" that test.**

---

## Locked decisions — do not change these

Each is traceable to a published result. If you believe one is wrong, **stop and
ask the user**. Do not silently substitute an alternative.

| Decision | Why |
|---|---|
| Exactly 5 scale points, fixed wording | Wang, Zhou & Liu (arXiv:2608.08869): all 10 frontier models sensitive to label/demonstration order; corrections unreliable; **lower cardinality** was the only consistent fix. |
| Exactly 2 vignettes, not 3 | PISA (He et al. 2017): 74–82 % clean orderings with 2 vignettes vs 63–72 % with 3. |
| Vignettes before self-assessment, as **separate** questions | King & Wand (2007): prior vignettes unify scale use (this is the mechanism). Merging them into one comparison question produces inconsistent, less informative responses. |
| Parallel question wording for vignette and self | Any asymmetry beyond the self/other pronoun manufactures a response-consistency violation for purely linguistic reasons. |
| Vignette texts kept general, not narrowly technical | Grol-Prokopczyk et al. (2015): vignette-equivalence violations markedly worse for highly specific texts. |
| 5 samples at temperature 1.0, no logprobs | Anthropic API exposes no logprobs; Gemini's support is per-model and has broken without notice. Simulation: 87 % positive at 1 sample, 95 % at 3, **97 % at 5**, no better at 15 or 25. |
| API models only. No GPU, no local serving. | Nothing measured requires weights or activations. Cross-provider diversity also increases the between-model scale-use variation the effect depends on. |
| No Brier score, no ECE, ever | Verified artifact: in a pure-noise world where the self-report carries zero information, Brier "improved" 0.3577 → 0.3016 purely because rescaling re-centres values on the base rate. |
| No LLM-as-judge anywhere in the measurement path | Ground truth is execution only. This is a stated strength of the design and the sprint's mandatory appendix asks for exactly this. |
| Do not import, vendor, or copy from `ast-guard` | The user's separate repo. Build fresh. It may be consulted for *how* to sandbox safely, nothing else. |
| Main experiment: 5 models × 100 tasks | Simulation: 5 models → effect positive in 100 % of runs; 3 models → only 90 %. 100 tasks → 98 %; 60 tasks → 93 %. |

---

## Which model to use for which work

Claude Code runs on API tokens; budget is tight (€200 total for everything).

**Sonnet is sufficient for:** `config.py`, `tasks.py`, `sandbox.py`, `elicit.py`,
logging, plumbing, refactors, test scaffolding.

**Switch to Opus for:** `rescale.py` and its invariance test, the vignette texts,
`analyze.py` and the pass/fail thresholds. These are where a plausible-looking
mistake silently invalidates the whole result.

If you are Sonnet and the task in front of you is on the Opus list, say so and
stop rather than attempting it.

---

## Commands

```bash
pytest tests/ -v                 # all must pass before any API call
python run_pilot.py --dry-run    # prints exact message sequence, no API calls
python run_pilot.py              # full pilot
```

Never mark work complete without running the tests and showing the output.

---

## Working conventions

- **Read before you write.** Open the file you are about to change. Do not edit
  from memory or from what the spec says it should contain.
- **Do not invent requirements.** If DESIGN.md and DEVLOG.md do not answer a
  question, ask. Do not pick a plausible default and proceed silently.
- **Stop on contradiction.** If two instructions conflict, halt and report both.
  Never improvise a compromise.
- **No placeholder implementations.** No `pass`, no `TODO`, no mock that returns
  a fixed value. If something cannot be built yet, say so.
- **Do not modify tests to make them pass.** Fix the implementation.
- **Be token-frugal.** Do not print whole files when a range suffices. Do not
  re-read a file you already read this session. Do not paste large outputs back
  as confirmation — summarise. Prefer targeted greps over full reads.
- **One coherent piece of work at a time.** Finish and log it before starting the
  next.
- Python 3.11+, type hints on public functions, plain functions and dataclasses,
  no class hierarchies. All tunables live in `config.py`.
- Every API call appends one line to `out/raw.jsonl` **immediately**, before any
  processing, including on failure. Runs must be resumable and auditable.

---

## DEVLOG obligation

At the end of every unit of work — and **before** the user switches sessions —
append an entry to `DEVLOG.md` in this exact format:

```markdown
## YYYY-MM-DD HH:MM — <model used>

**Built:** <what now exists that did not before>

**Decided:** <any choice made, and the reason>

**Did not work:** <what was tried and failed, and why>

**State:** <what runs, what does not, what is untested>

**Next:** <the single next step>
```

The "Did not work" field is not optional and not a formality. The submission
template asks under Methods: *"What did you try that didn't work?"* Nobody can
answer that from memory on Sunday night. This is the primary source for that
section of the paper.

Keep the **Open Questions** section at the bottom of DEVLOG.md current: add
anything unresolved, remove anything answered.

---

## Timeline discipline

Work done **before** Friday 14 Aug is pre-sprint preparation and must be
disclosed in the submission. The git history is the evidence. Do not rewrite,
squash, or amend commits — the honest timestamps are worth more than a clean log.

---

## Scope boundary

Right now we are building **the pilot only**: a go/no-go instrument check on
2 models × 20 tasks. It answers whether four assumptions hold (see DESIGN.md §9).
It does not answer the research question, and no result from it should be
described as a finding.

Do not build the main experiment, expand the model list, add analysis beyond
DESIGN.md §9, or write anything paper-facing until the pilot has returned a GO.
