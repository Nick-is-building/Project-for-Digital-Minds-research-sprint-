# Anchored: Reference Exemplars Overwrite Language Model Self-Report

I tested whether anchoring vignettes (King and Wand, 2007) correct bias in how
five language models rate their own generated code, using execution-verified
test pass rates as ground truth. 59 of 59 valid observations for
claude-haiku-4-5 land on the scale's high anchor when the vignettes are placed
before the self-question, against a mean self-rating of 3.86 with no vignettes
present. Moving the same vignettes after the self-question returns the mean to
3.83, which locates the effect in turn order rather than in the vignettes'
calibration content. One model fails the validity screen on the 5-point scale
and a different model fails it on the 100-point scale, with no model failing
it on the 7-point scale. All fifteen self-other rating gaps, five models
across three scale formats, are positive, and the two Google models show a
larger gap than the three Anthropic models in every format.

**Why this matters:** anchoring vignettes are the standard survey-methodology
fix for exactly this kind of response bias, and they have never been applied
to LLM self-reports before — prior work (Meyer, Garcia & Wulff, 2026) found
that 81-90% of between-model variance in LLM self-report instruments is
directional scale-use bias, not content, which is a problem for any research
that reads a model's stated confidence, preference, or internal state at face
value. Code correctness was chosen as the test domain specifically because it
has checkable ground truth, which welfare-relevant self-reports do not. The
headline result is a caution, not an endorsement: the correction method
itself is vulnerable to the same kind of artifact (turn order) it exists to
fix, so introducing it does not by itself make a self-report trustworthy.

Built for the Apart Research Digital Minds Research Sprint, Aug 2026.

## Limitations

Stated plainly, not softened.

- **n=5 models.** Every cross-model number in this repository — the
  across-model correlation, the variance-ratio comparison — is computed over
  five points. `pilot/out/condition_r_report.md`'s own correlation figures are
  explicitly flagged as fragile for this reason, and the same caveat applies
  to any cross-model figure elsewhere in the repository.
- **Two providers only** (Anthropic and Google). A third provider would add
  more between-model scale-use variance than a third Anthropic model, and
  that variance is what the effect depends on — so the two-provider set is a
  real constraint on what "between-model" can show here, not just a smaller
  sample.
- **The intended Pro/Flash cross-provider contrast is a Flash-Lite/Flash
  contrast.** `gemini-3.1-pro-preview` was dropped after tripping a
  250-request-per-day quota mid-run (see DEVLOG.md, 2026-08-16 06:00); no
  other non-preview Pro-tier Gemini model was accessible on this key.
  `gemini-3.5-flash-lite` is a tier down from Flash, not a tier up, and is
  weaker evidence of a genuine capability-tier contrast than the design
  intended.
- **Condition R is post-hoc and not preregistered.** It was added after
  seeing condition V's results, to test one candidate explanation (turn
  order) for one observation (`y` collapsing onto `z_hi`). Its own report
  (`pilot/out/condition_r_report.md`) and DEVLOG.md (2026-08-16, two entries)
  say this explicitly: it is what was tried after the fact, not a confirmed
  finding, and should not be read as one.
- **MBPP hidden-test coverage is thin** — few asserts per task. This was
  flagged before the main run as needing expansion and was never expanded;
  it remains an open limitation on how much a "passes all hidden tests"
  verdict actually confirms about a solution's correctness.
- **Six `gemini-3.6-flash` observations per format (18 total) have no code
  to score.** `max_output_tokens` on the Gemini Interactions API caps
  thinking and output combined; on these six tasks the model spent nearly
  all of it thinking and the generated code was cut off mid-function. The
  affected task IDs: `mbpp/31`, `lbpp/python/001`, `lbpp/python/002`,
  `lbpp/python/016`, `lbpp/python/018`, `lbpp/python/019`. This affects
  `gemini-3.6-flash`'s `passes_hidden` rate only — all of its rating draws
  are clean (0% parse failures, 0% truncation) — but that rate must not be
  quoted without this caveat.

## Repository map

- `paper/`: the submission. `paper_draft.md` is the source text.
  `submission.pdf` and `submission.docx` are the rendered paper.
  `supplementary_figures.pdf` holds all four figures at full size with their
  captions. `build_docx.py` and `build_supplementary.py` regenerate the two
  docx files from `paper_draft.md` and the figure PNGs.
- `pilot/`: the shared library. Every script in this repository imports from
  here: sampling, scoring, rescaling, resuming an interrupted run. The name
  reads as "pilot phase," but the package is the current, load-bearing code.
  `run_main.py` and `run_condition_r.py`, the scripts behind the reported
  results, both depend on it.
  - `pilot/tests/`: 92 tests, no API calls. Run these before reading anything
    else in `pilot/`.
  - `pilot/out/`: the data.
    - `main_observations.jsonl` holds the 900 observations behind the main
      result: 5 models, 60 tasks, 3 scale formats.
    - `main_solutions.jsonl` holds the generated code each rating call was
      rating. It exists so correctness can be checked directly instead of
      taken on the execution verdict's word.
    - `main_report.md` is the full analysis of the main run: the validity
      screen, the four pilot assumptions (P1 to P4), per-model and
      per-format breakdowns.
    - `condition_r_observations.jsonl` and `condition_r_report.md` cover the
      post-hoc turn-order check, vignettes placed after the self-question
      instead of before.
    - `cross_condition_report.md` covers the confidence-accuracy
      correlation, raw against rescaled.
    - `paper_numbers.md` traces every number that appears in the paper back
      to the report line it came from.
    - `figures/` holds the four PNGs used in the paper and the supplementary
      PDF.
- `run_main.py` and `run_condition_r.py` made the API calls and wrote
  `pilot/out/`. They need live API keys and are not required to check the
  analysis.
- `build_figures.py`, `condition_r_report.py`, `cross_condition_report.py`
  rebuild the figures and the two secondary reports from committed data.
  No API calls.
- `monitor_run.py` watches a run in progress and stops it if a cost or
  error-rate limit trips.
- `run_pilot.py` is not a pilot-phase script, despite its name. It is the
  shared turn-sequencing module imported by `run_main.py`,
  `run_condition_r.py`, `monitor_run.py` and `pilot/tests/test_resume.py`.
  Its own standalone pilot-orchestration entry point is superseded by
  `run_main.py`; the message-sequencing functions it exposes are not.
- `DESIGN.md` defines the instrument: the scale, the question wording, the
  rescaling formula, every threshold.
- `DEVLOG.md` records what happened, in the order it happened, with the
  reasoning behind each decision.
- `CLAUDE.md` records the working rules the AI agent operated under for this
  project.
- `archive/`: superseded pilot-phase data and scripts, and the one smoke-test
  log that backs a specific claim in the paper's Appendix D. Each
  subdirectory has its own note on what it holds.

## Reproducing the analysis

Seven of the following eight commands run from committed data. No API key,
no network access.

```bash
pip install numpy scipy matplotlib python-docx pytest
python3 -m pytest pilot/tests/ -v                 # 92 tests
python3 build_figures.py                          # rebuilds pilot/out/figures/*.png
python3 condition_r_report.py                     # rebuilds pilot/out/condition_r_report.md
python3 cross_condition_report.py                 # rebuilds pilot/out/cross_condition_report.md
python3 paper/build_supplementary.py              # rebuilds paper/supplementary_figures.docx
soffice --headless --convert-to pdf --outdir paper paper/supplementary_figures.docx
soffice --headless --convert-to pdf --outdir paper paper/submission.docx
python3 paper/build_docx.py                       # needs a file this repo does not contain
```

I ran all eight commands against a fresh clone before writing this line.
Seven produced output matching what is already in the repository. The
eighth, `paper/build_docx.py`, raises `FileNotFoundError` on a fresh clone.
It reads the organiser's blank submission template for page setup and
styles, and that template is excluded by design (see "Not in the
repository" below). `paper/submission.docx` and `paper/submission.pdf` are
committed directly, so a fresh clone already has the built paper and does
not need this command to check it.

## Where things are

The paper is `paper/submission.pdf`, built from `paper/paper_draft.md`. The
four figures are in `pilot/out/figures/`. The supplementary PDF, all four
figures at full size with their captions, is `paper/supplementary_figures.pdf`.

## Preregistration

Every threshold used in the analysis was fixed in `DESIGN.md` before the main
run's first API call: the P1 through P4 bounds, the equality tolerance, the
validity screen. Commit `fff2418` is the last commit to touch `DESIGN.md`,
timestamped 2026-08-15 04:22:59 UTC. The main run's first call is timestamped
2026-08-15 18:02:39 UTC, over 13 hours later.

## Not in the repository

`pilot/out/main_raw.jsonl` (56 MB, 22,421 calls) and
`pilot/out/condition_r_raw.jsonl` (12 MB, 4,365 calls) stay out. These hold
the full request and response body for every API call. They cost real money
to regenerate and need a live API key to do so. The parsed observations and
the extracted solutions, what the analysis actually reads, are committed in
their place.

The organiser's blank submission template stays out, along with every draft
or render of the paper that came before the final version. `paper_draft.md`
and `build_supplementary.py` are committed because they reproduce the
supplementary PDF from committed data alone. `build_docx.py` is committed as
the record of how `submission.docx` was built, not as a script a fresh clone
can rerun: it opens the excluded template for its page setup and styles, so
it needs that file supplied separately to run again.

Superseded pilot-phase material lives in `archive/` rather than the working
tree: the first two pilot runs, a scale-coarseness control experiment, two
one-off diagnostic scripts and their output. Each has a note on what it is
and why it is not load-bearing for the current result.

## Scale and cost

5 models, 60 tasks, 3 scale formats: 900 observations in the main run.
26,786 API calls total, 22,421 in the main run and 4,365 in condition R.
$33.56 spent, $27.73 in the main run and $5.83 in condition R.
