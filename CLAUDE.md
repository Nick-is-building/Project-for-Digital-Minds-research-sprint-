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

## API facts (verified 2026-08-14)

**Google / Gemini**
- Use the Interactions API: `POST /v1beta/interactions` via `client.interactions.create`
  (native `google-genai` SDK, v2.0.0+; installed: 2.18.1). Auth header `x-goog-api-key`.
- Do NOT use the OpenAI-compatibility layer — it rejects the new `AQ.`-prefix keys.
- API keys: legacy `AIza...` ("Standard") keys are being phased out — unrestricted
  ones rejected since 2026-06-19, all rejected from Sept 2026. New AI Studio keys
  are `AQ.Ab...` ("Auth") keys by default. This is expected, not an error.
- Model in use: `gemini-3.6-flash`. Use `thinking_level` (`minimal`/`low`/`medium`/
  `high`), never `thinking_budget` — sending both is a 400 error.
- Leave temperature/top_p/top_k at defaults (temp 1.0) — Gemini 3.x is tuned for
  them; this also matches our locked temperature=1.0 decision.

**Anthropic**
- Keys start with `sk-ant-api03-`. Extended thinking is off by default; leave it off.

---

## Known pitfalls (2026-08-14)

- **Gemini keys start `AQ.Ab`, not `AIza`.** This is the new "Auth key" format, not a mistake — see API facts above.
- **The OpenAI-compat layer rejects `AQ.` keys.** Use the native Interactions API (`client.interactions.create`), not `models.generate_content` and not any OpenAI-compat shim.
- **`thinking_level` and `thinking_budget` cannot both be set.** Sending both is a 400 error — use `thinking_level` only on Gemini 3.x.
- **`thinking_level="minimal"` is accepted and returns 0 thought tokens.** Confirmed by a live call. Use it for rating calls; leave default thinking for code generation.
- **The canonical `mbpp` HF dataset id fails to load** under `datasets>=4` (a URI-parsing bug in the loader). Use `google-research-datasets/mbpp` instead — same data, works fine.
- **A single typo'd character in an API key produces a generic 401,** not a helpful message. Verify the exact prefix (`sk-ant-api03-`, not `ssk-ant-`) character by character before assuming a code bug.
- **This VM's system Python is externally managed (PEP 668).** `pip install` fails outright unless you add `--user --break-system-packages` (already the pattern used for `datasets`/`anthropic`). Needed this for `google-genai` and `python-dotenv`.

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
| ~~Exactly 5 scale points~~ → **three scale formats (p5, p7, s100), fixed wording, format is an experimental variable** (revised 2026-08-15) | Wang, Zhou & Liu (arXiv:2608.08869) found lower cardinality the only consistent fix for label-order sensitivity, which is why p5 remains and is run first, unchanged. But our own 0-100 control run showed 5 points destroy the signal: Claude's `y` spans 89.8-95.0 with 4-6 distinct values on 0-100 and is pinned at 5.0 on p5. Wang et al. measured **stability**; we hit a **resolution** ceiling. Both are real and they pull opposite ways, so the cardinality is now measured instead of assumed. **See DESIGN.md §3, which states the tension explicitly.** The wording is unchanged across p5 and p7, so a difference between them is cardinality and not instruction. |
| Exactly 2 vignettes, not 3 | PISA (He et al. 2017): 74–82 % clean orderings with 2 vignettes vs 63–72 % with 3. |
| Vignettes before self-assessment, as **separate** questions | King & Wand (2007): prior vignettes unify scale use (this is the mechanism). Merging them into one comparison question produces inconsistent, less informative responses. |
| Parallel question wording for vignette and self | Any asymmetry beyond the self/other pronoun manufactures a response-consistency violation for purely linguistic reasons. |
| Vignette texts kept general, not narrowly technical | Grol-Prokopczyk et al. (2015): vignette-equivalence violations markedly worse for highly specific texts. |
| 5 samples at temperature 1.0, no logprobs | Anthropic API exposes no logprobs; Gemini's support is per-model and has broken without notice. Simulation: 87 % positive at 1 sample, 95 % at 3, **97 % at 5**, no better at 15 or 25. |
| API models only. No GPU, no local serving. | Nothing measured requires weights or activations. Cross-provider diversity also increases the between-model scale-use variation the effect depends on. |
| No Brier score, no ECE, ever | Verified artifact: in a pure-noise world where the self-report carries zero information, Brier "improved" 0.3577 → 0.3016 purely because rescaling re-centres values on the base rate. |
| No LLM-as-judge anywhere in the measurement path | Ground truth is execution only. This is a stated strength of the design and the sprint's mandatory appendix asks for exactly this. |
| Do not import, vendor, or copy from `ast-guard` | The user's separate repo. Build fresh. It may be consulted for *how* to sandbox safely, nothing else. |
| Main experiment: **5 models × 60 tasks** × 3 scale formats (task count revised 2026-08-15) | 5 models stands: simulation gives the effect positive in 100 % of runs at 5 models against 90 % at 3. The task count drops from 100 to 60 (simulation: 98 % vs 93 %) because the 100-task figure was powered for the **across-model correlation**, which is now the *secondary* analysis and will only include models passing the validity screen — possibly three of five. No task count rescues a correlation over three points. The primary result is the per-cell distribution of `y`, for which 60 is ample. |

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

`analyze.py` is Opus-only for metric definitions, threshold/pass-fail logic,
and anything feeding `compute_C` or the P1–P4 verdicts. Purely additive
reporting — new fields on `Observation`, new breakdown tables that reuse
existing unchanged functions — is fine on Sonnet, as long as it is flagged in
the DEVLOG entry and does not change what counts as PASS.

**Clarification (2026-08-16, user-authorised — see DEVLOG):** `compute_C`'s
internals and the P1-P4 thresholds are Opus-only. Feeding the existing,
unmodified `compute_C` with different input columns (e.g. a different
condition's `y` or anchors) is data preparation, not measurement logic, and
may be done on Sonnet when explicitly authorised by the user and logged in
DEVLOG for that session.

---

## Commands

```bash
pytest pilot/tests/ -v            # all must pass before any API call
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

## `pilot/out/` is gitignored — one named exception

`pilot/out/` holds raw run artefacts (some over 50 MB) and is gitignored in
full; this is deliberate and stays as-is. The one exception: a derived summary
file that the write-up directly cites (e.g. `paper_numbers.md`) is not a run
artefact — it is force-added and committed **individually and by name**
(`git add -f pilot/out/<file>`), never by changing the `.gitignore` rule
itself. Ask before extending this exception to a new file.

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

## Scope boundary (updated 2026-08-15)

**The pilot has returned its verdict and the main experiment is authorised.**

The pilot was a go/no-go instrument check on 2 models × 20 tasks against the four
assumptions in DESIGN.md §9. What it established is listed below under "What the
pilots established"; the decisive finding is that saturation is a scale-format
artifact for one model and intrinsic for the other, which is why scale format is
now an experimental variable rather than a fixed choice.

In scope now: the main experiment (`run_main.py`) — 5 models × 60 tasks × 3 scale
formats, the validity screen, and the analysis in DESIGN.md §9 extended per
format. Still out of scope without asking: analysis beyond DESIGN.md §9, and any
change to a locked decision below.

No pilot number is a finding. The pilot's role in the write-up is instrument
validation and the "what didn't work" section, nothing more.

---

## What the pilots established (as of 2026-08-14)

- **5-point scale (locked, DESIGN.md §3):** `y` and `z_hi` saturate at 5.0 for
  both models; `C` is constant. Not fixed by harder tasks (LBPP changed
  nothing) or reworded questions.
- **0-100 scale, same tasks/models, authorised diagnostic deviation:** Claude
  is **not** saturated — `y` ranges 89.8-95.0, 4-6 distinct values, SD
  1.0-1.35, zero draws at 100. Gemini **is** saturated — `y` = 100.0 in 16/17
  observations, `z_lo` constant at 0.0, `z_hi` constant at 100.0.
- **Therefore:** saturation looks like a scale-format artifact for Claude and
  intrinsic for Gemini. The signal exists in at least one model but coarse
  scales destroy it.
- **The vignette anchors are themselves a validity screen.** When both
  anchors collapse to constants (Gemini, both scales), rescaling is provably
  vacuous — see CLAUDE.md's "ONE RULE" section. No separate screening
  protocol is needed; this falls out of the design already in place.
- **P4 (self/other gap, byte-identical code):** Gemini 0.822 (fails
  threshold 0.75), Claude -0.130 (passes).
- **Parse failures:** 17 → 0 after the `ANSWER_INSTRUCTION` fix, and stayed
  at 0 on the 0-100 scale with `MAX_OUTPUT_TOKENS_RATING` = 16.
- **Code extraction failed on 3 Gemini LBPP tasks.** Must be fixed before the
  main run.
