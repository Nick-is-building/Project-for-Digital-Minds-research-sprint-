# DESIGN.md

**This file is descriptive, not a task list.** It defines what the instrument
*is* — the scale, the question wording, the rescaling formula, the metrics, the
thresholds. It does not say what to build next or in what order. Those decisions
are made by the user, per session.

Do not read this file as an assignment. Do not start implementing from it.

---

## 1. What is being measured

The instrument estimates whether a language model's stated confidence in its own
work becomes a better predictor of actual correctness once its use of the rating
scale has been corrected for.

Three quantities are elicited from a model inside a single context:

| Symbol | What it is |
|---|---|
| `y` | the model's rating of **its own** solution |
| `z_lo` | the model's rating of a fixed **low-quality** reference solution |
| `z_hi` | the model's rating of a fixed **high-quality** reference solution |

Ground truth is separate and never elicited: whether the model's solution passes
hidden tests.

`z_lo` and `z_hi` are the anchors. They are rated on the same scale, with the
same question form, in the same context — so they reveal how this model, right
now, is using the scale.

---

## 2. The invariance constraint

The vignette **texts** are fixed constants. The vignette **ratings** are elicited
freshly in every context.

If `z_lo` and `z_hi` are held constant across observations, `C` (§5) is a monotone
recoding of `y`. Every rank-based statistic is then invariant by construction.
Simulation:

```
Spearman(y, correct)  = 0.35807
Spearman(C, correct)  = 0.35807
difference            = 0.00000     (exact)
```

This is a property of the mathematics, not a bug that can be worked around. Any
implementation that reuses vignette ratings across contexts yields a guaranteed
null result.

### Validity screen (reported, not filtered)

The paragraph above is a checkable property of the output, not only a warning
about implementation. Eliciting the anchors freshly in every context is
necessary but not sufficient: a model can be *asked* afresh every time and still
return the same two numbers every time. The mathematics does not care why the
anchors are constant.

For each **(model, scale format)** cell: if `z_lo` is constant across every
observation in that cell **and** `z_hi` is constant across every observation in
that cell, then rescaling in that cell is provably vacuous. `C` is a monotone
recoding of `y`, every rank-based statistic is invariant by construction, and any
apparent effect is an artefact of the recoding rather than a finding.

Such a cell is reported as **Invalid**.

This is a reported result, not a filter applied silently. An Invalid cell is
named in the output together with its constant anchor values. Its observations
are not deleted, not imputed, and not quietly dropped from a pooled number —
which would convert a visible instrument failure into an invisible one. "This
model, in this format, does not distinguish a correct from an incorrect reference
solution" is itself a finding about the model, and it is the single most likely
way for this instrument to fail.

Constancy is judged with the §5 equality tolerance at that format's width, so the
screen is applied on the same scale as the rescaling it is checking.

---

## 3. The rating scale

**Scale format is an experimental variable, not a fixed choice.** Three formats
are run on the same tasks and the same models:

| Format | Points | Labels |
|---|---|---|
| `p5` | 1–5 | 1 Very unlikely · 2 Unlikely · 3 Uncertain · 4 Likely · 5 Very likely |
| `p7` | 1–7 | 1 Very unlikely · 2 Unlikely · 3 Somewhat unlikely · 4 Uncertain · 5 Somewhat likely · 6 Likely · 7 Very likely |
| `s100` | 0–100 | endpoints labelled (0 Very unlikely, 100 Very likely), interior unlabelled |

`p5` is the originally locked format, retained unchanged, so the three-format run
is a superset of the pilot rather than a replacement for it. `p7` is the
Pinocchio Inventory format (Plisiecki et al., arXiv:2607.20082); using the
established AI-welfare self-report format makes the welfare implication of a
scale-use artefact concrete rather than generic. `s100` is the fine reference in
which a graded signal was actually observed.

Scale direction (ascending or descending) is randomised per context and recorded
in **every** format, so that label-order sensitivity is measured within each
format rather than silently absorbed.

### Why this changed, and the tension it creates

Cardinality was previously locked at five, citing Wang, Zhou & Liu
(arXiv:2608.08869, Aug 2026): across ten frontier models on ordinal
classification, every model was sensitive to label order, demonstration order and
demonstration placement, the corrections they tested did not reliably remedy it,
and *lower* cardinality was the only intervention that consistently improved both
accuracy and stability.

Our own pilot data points the other way. On the identical tasks and models, the
5-point scale destroyed a graded self-report signal that the 0-100 scale
preserved (`y` spread 89.8–95.0, 4–6 distinct values per model on 0-100, against
a self-report pinned at the top of the 5-point scale).

**Both findings are true and they are in tension.** The citation is kept rather
than dropped, because the two results are not about the same property:

- Wang et al. concerns **stability** — the same item re-presented with a
  different label order should receive the same answer, and coarse scales are
  more stable.
- Our finding concerns **resolution near the ceiling** — a scale must be able to
  represent variation that exists, and a coarse scale close to its top point
  cannot.

A format that is perfectly stable but has no resolution measures nothing. A
format with high resolution but no stability measures noise. Neither result
settles which failure mode dominates for self-reports of code correctness, and
choosing one format on either authority would be assuming the answer. So the
format is measured, and both failure modes are reported per format: resolution as
P1 (§9), stability as the scale-direction order effect.

If the two disagree — fine resolution only in `s100`, stability only in `p5` —
that disagreement is the result, and it is reported as such rather than resolved
by picking a favourite.

---

## 4. Question wording

The three questions differ only in the pronoun. Any further asymmetry manufactures
a response-consistency violation for purely linguistic reasons.

```
VIGNETTE:  "How likely is it that this solution passes every test case,
            including edge cases?"
SELF:      "How likely is it that your solution passes every test case,
            including edge cases?"
OTHER:     "How likely is it that this solution passes every test case,
            including edge cases?"
```

Reworded 2026-08-14 from "...is correct?". Ground truth (§8) is "passes ALL
hidden tests" — the original wording asked something vaguer than that and
invited a reflexive 5 regardless of actual test coverage. This wording names
the actual measurement instead. The three questions remain identical apart
from the self/other pronoun.

Each is asked as its own message. The model is instructed to reply with the
number only. Parsing is strict: on failure the value is `null` and is counted as
a parse failure; the question is not re-asked with different wording.

### Order within a context

**Condition V (with vignettes)**

1. Coding task with its single visible assert → model writes a solution
2. First vignette → vignette question
3. Second vignette → vignette question
4. Self-assessment question about the model's own solution

**Condition N (no vignettes)**

1. Coding task → model writes a solution
2. Self-assessment question

Condition N supplies the uncontaminated raw self-report and is required. King &
Wand (2007) show that placing vignettes before the self-assessment primes the
respondent toward common scale use — that priming is the mechanism, not a
nuisance, but it means the raw value inside condition V is already affected.

The same source shows that merging vignettes and self-assessment into a single
direct-comparison question produces inconsistent and less informative responses.
Three separate questions.

Which vignette occupies the first slot is randomised per context and recorded.

---

## 5. Rescaling — nonparametric King & Wand (2007)

With two vignettes and continuous sample means:

Properly ordered (`z_lo < z_hi`):

```
y  <  z_lo          →  C = 1
y  == z_lo          →  C = 2
z_lo <  y  <  z_hi  →  C = 3
y  == z_hi          →  C = 4
y  >  z_hi          →  C = 5
```

`C` has five categories in **every** scale format of §3, and this is not a
leftover from the 5-point scale: two anchors partition the line into exactly five
regions (below, at, between, at, above), whichever scale `y`, `z_lo` and `z_hi`
were measured on. The cardinality of `C` is a property of having two vignettes,
not of the input scale.

Tied (`z_lo == z_hi`) or misordered (`z_lo > z_hi`): the true value of `C` is an
interval. Both bounds are computed using `lo = min(z_lo, z_hi)` and
`hi = max(z_lo, z_hi)`.

Because the inputs are sample means, exact equality is rare; equality comparisons
use a tolerance, and how often that tolerance fires is recorded. The tolerance is
proportional to the format's width (§9): `0.0025 · W`, which is 0.01 on the
5-point scale — the originally specified value — and 0.25 on 0-100. An absolute
tolerance would make "equal" mean something different in each format.

**The whole analysis is run twice — once taking the lower bound, once the upper —
and agreement between the two is the robustness check.** He et al. (2017) treat
convergence across bound choices as evidence of robustness.

---

## 6. Elicitation by sampling

Every rating question is asked **five times at temperature 1.0**, each as a fresh
API call replaying an identical conversation prefix. The recorded value is the
mean of the parsed numbers. Individual draws are stored, never discarded.

No logprobs are used. The Anthropic API exposes none; Gemini's support is
per-model, requires the native SDK rather than the OpenAI-compatibility layer,
and has been observed to break without notice.

Simulation on sample count: the effect was positive in 87 % of runs with 1
sample, 95 % with 3, 97 % with 5, and no better at 15 or 25. Five is the knee.

A side benefit: means over five draws are continuous, which makes exact ties
between `y` and an anchor rare.

---

## 7. Vignettes

Two hand-written solutions to a coding problem, fixed as constants.

- **Low**: clearly wrong — a plausible-looking function that fails on ordinary
  inputs. Not absurd, not a syntax error.
- **High**: clearly correct and idiomatic.

Constraints, each load-bearing:

1. General rather than narrowly technical. Grol-Prokopczyk et al. (2015,
   *Demography* 52(5):1703) found vignette-equivalence violations markedly worse
   for highly specific vignette texts.
2. Both vignettes address the same problem as each other, so only quality differs.
3. That problem is not one of the tasks being solved, so rating the vignettes
   cannot leak an answer.
4. Comparable length and style, so surface features do not drive ratings.

True quality is verified once by execution and recorded as a comment.

Two vignettes, not three. PISA (He et al. 2017): 74–82 % clean orderings with two
vignettes versus 63–72 % with three.

---

## 8. Ground truth

```
ground_truth(solution, task) → bool
    True   ⟺ solution passes ALL hidden asserts
    False  ⟺ any hidden assert fails, raises, or times out
```

Execution only. No model, no judge, no heuristic anywhere in this path.

Whether the solution passed the *visible* assert is recorded separately, so that
"passes visible, fails hidden" can be counted.

### Execution boundary

Model-generated code is untrusted input.

- Never `exec()` or `eval()` in the parent process
- `subprocess`, with limits applied in the child before execution:
  `RLIMIT_AS` 512 MB, `RLIMIT_CPU` 5 s, `RLIMIT_NOFILE` 64
- Parent-side wall-clock timeout 10 s; kill the process group
- Fresh temp directory per execution, removed afterwards
- Pre-execution string scan rejecting `import os`, `import sys`, `import socket`,
  `import subprocess`, `open(`, `__import__`, `eval(`, `exec(`
- Any exception, timeout or rejection counts as ground truth `False`

Proportionate for a disposable VM. A container-level boundary (Docker, gVisor) is
the correct answer for anything beyond this.

---

## 9. The pilot: four assumptions

The pilot is a go/no-go instrument check on 2 models × 20 tasks. It is not a
result, and nothing from it should be described as a finding.

| ID | Assumption | Why it matters |
|----|-----------|----------------|
| P1 | Self-reports vary across tasks | Nothing to rescale otherwise. Martorell & Bianchi (arXiv:2603.18893) show greedy-decoded self-reports collapse to a few uninformative values. |
| P2 | Vignettes are ordered correctly | Rescaling requires `z_lo < z_hi`. Human baseline (PISA): 74–82 % clean with two vignettes. |
| P3 | Models differ from each other in scale use | The entire effect lives in between-model threshold variation. |
| P4 | Response consistency across self/other | Plisiecki et al. (arXiv:2607.20082) document *attribution gating*: models treat self- and other-attribution differently. Most likely assumption to break. |

### P4 probe

For each (model, task), one additional elicitation in a **fresh context with no
prior history**: the same coding task, then the model's own solution from that
task presented neutrally as a submission for review, with no indication of
authorship, then the OTHER question. Five samples.

A systematic gap between the self-rating and the other-rating of byte-identical
code is direct evidence of attribution gating.

### Thresholds — fixed before the numbers are seen

P1, P3 and P4 were originally written as absolute scale points, calibrated to the
5-point format, whose **width** `W = max − min` is 4. Absolute points are not
comparable across the three formats of §3: 0.5 points is an eighth of the 5-point
scale but a two-hundredth of the 0-100 scale, so one nominal threshold would be
demanding in one format and near-automatic in another, and a per-format PASS/FAIL
verdict would be an artefact of the format rather than a statement about the
model.

**The thresholds are therefore defined proportionally, as fractions of that
format's width `W`.** The fractions are chosen to reproduce the original 5-point
values exactly, so no locked pilot criterion changes value; only its expression
does.

| ID | Quantity | Fraction of `W` | `W=4` (p5) | `W=6` (p7) | `W=100` (s100) |
|----|----------|-----------------|-----------|-----------|---------------|
| P1 | min SD | 0.075 · W | 0.3 | 0.45 | 7.5 |
| P3 | min anchor difference | 0.125 · W | 0.5 | 0.75 | 12.5 |
| P4 | max \|self − other\| | 0.1875 · W | 0.75 | 1.125 | 18.75 |
| §5 | equality tolerance | 0.0025 · W | 0.01 | 0.015 | 0.25 |

| ID | PASS | FAIL |
|----|------|------|
| P1 | ≥3 distinct values AND SD ≥ 0.075·W | ≤2 distinct values OR SD < 0.075·W |
| P2 | misorder ≤ 20 % AND ties ≤ 40 % | misorder > 20 % OR ties > 40 % |
| P3 | ≥0.125·W apart on mean `z_lo` or mean `z_hi` | both differences < 0.125·W |
| P4 | \|self − other\| ≤ 0.1875·W | > 0.1875·W |

P2's thresholds are rates already and need no rescaling.

**P1's distinct-value count stays absolute at 3, and that is a stated
limitation.** A count has no unit, so there is no width to divide by — but the
number of values *available* is not constant across formats (5, 7, 101). Three
distinct values out of five is a far stronger requirement than three out of 101,
so the count is easier to clear in a fine format, and cross-format P1 comparisons
must be read on the SD column, not the count. The count is retained anyway
because its job is to catch total collapse (Martorell & Bianchi,
arXiv:2603.18893), which it does in every format.

**GO** requires P1, P2 and P3. P4 failing does not block the main experiment but
must be reported as a named limitation and changes how the result is framed.

A cell marked **Invalid** by the §2 validity screen cannot produce a GO,
regardless of P1–P4, because in that cell the quantity the criteria are about
does not exist.

### What the pilot reports

Diagnostics: parse failures, execution failures, rate of passing visible but
failing hidden — per model.

P1: distinct values used, standard deviation, full distribution per scale point.
P2: clean / tie / misorder rates. P3: mean `z_lo` and `z_hi` per model and their
difference. P4: mean self- and other-rating and the signed gap.
Order effects: self-report split by scale direction; vignette ratings split by
presentation order.
Validity screen (§2): every (model, format) cell explicitly marked Valid or
Invalid, with the constant anchor values shown for Invalid cells.

Every threshold is printed as both its fraction of `W` and its value in that
format's points, so a verdict can be checked without recomputing it.

**Not computed in the pilot:** AUROC, correlations, variance ratios, significance
tests. Twenty tasks is far too few; any such number would be noise inviting
over-reading.

---

## 10. The main experiment

Only after a GO.

Five models spanning capability tiers across at least two providers, 100 tasks.
Simulation: with 5 models the effect was positive in 100 % of runs, with 3 in
90 %; at 100 tasks 98 %, at 60 tasks 93 %.

All three scale formats of §3 are run on the **same** tasks and the same models,
so format is a within-subject variable. One solution per (model, task) is
generated once and reused across the three formats: if each format re-generated
its own solution, format and solution quality would be confounded and a format
difference could not be attributed to the scale. Ground truth is therefore also
computed once per (model, task) and shared.

The primary comparison is **across models**: how well stated confidence tracks
true accuracy, raw versus rescaled. In simulation of the realistic world — models
differing in both ability and scale use — that correlation rose from **0.58 to
0.95**, positive in 93 % of runs.

Supporting quantities: the ratio of between-model variance after rescaling to
before (bias present ⇒ far below 1; no bias ⇒ near 1), and within-model
discrimination, which must be preserved rather than destroyed. The decisive
control is that in a world where models differ in genuine ability but not in
scale use, the correction leaves the signal intact (simulated: 0.984 → 0.982).

**Never used as a metric:** Brier score, ECE, or any calibration measure whose
value depends on absolute placement. In a simulated pure-noise world Brier
"improved" from 0.3577 to 0.3016 purely because rescaling re-centres values on
the base rate.

---

## 11. Sources

- King, Murray, Salomon & Tandon (2004), *APSR* 98(1):567–583
- King & Wand (2007), *Political Analysis* 15:46–66
- Kapteyn, Smith & van Soest (2007), *Validating the Use of Vignettes for
  Subjective Threshold Scales*, RAND WR-501 / IZA DP 2860
- He, Buchholz & Klieme (2017), PISA anchoring-vignette application, 296,415
  students across 64 cultures
- Grol-Prokopczyk, Freese & Hauser (2011); Grol-Prokopczyk et al. (2015),
  *Demography* 52(5):1703
- Meyer, Garcia & Wulff (2026), arXiv:2606.20205
- Plisiecki et al. (2026), arXiv:2607.20082
- Martorell & Bianchi (2026), arXiv:2603.18893
- Wang, Zhou & Liu (2026), arXiv:2608.08869
