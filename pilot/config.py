"""Central tunables for the pilot and main-experiment pipelines.

Every constant used by more than one module — or that would otherwise be a
magic number/string buried in logic — lives here. See DESIGN.md for the
rationale behind the scale, wording, and execution-boundary values; this file
only encodes what DESIGN.md already fixed.

Scale format is an experimental variable (DESIGN.md §3), so the scale is a
`ScaleFormat` object passed explicitly rather than a module-level constant. The
P1/P3/P4 thresholds and the §5 equality tolerance hang off it as width-relative
properties, so they cannot go stale against the format actually in use — the
failure mode that made the 0-100 control run compare against 5-point bounds.
"""

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

# --- Paths -----------------------------------------------------------------

PILOT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PILOT_DIR.parent
OUT_DIR = PILOT_DIR / "out"
RAW_JSONL_PATH = OUT_DIR / "raw.jsonl"
SANDBOX_TMP_DIR = PILOT_DIR / ".sandbox_tmp"

MAIN_RAW_JSONL_PATH = OUT_DIR / "main_raw.jsonl"
MAIN_OBSERVATIONS_PATH = OUT_DIR / "main_observations.jsonl"
MAIN_REPORT_PATH = OUT_DIR / "main_report.md"

# Solutions are persisted separately from observations because one solution is
# shared by all three scale formats of a (model, task) pair and must survive an
# interruption: regenerating at temperature 1.0 would silently unpair them. See
# pilot/resume.py.
MAIN_SOLUTIONS_PATH = OUT_DIR / "main_solutions.jsonl"

# --- Providers and models ----------------------------------------------------
# DESIGN.md does not fix model identifiers (see DEVLOG.md Open Questions).
#
# Pilot: one model per provider, both cheap/fast, to keep pilot cost low.
# Main experiment (DESIGN.md §10): five models spanning capability tiers across
# at least two providers.
#
# Google models use the Interactions API (see CLAUDE.md "API facts") via
# client.interactions.create, not client.models.generate_content. Dispatch is by
# PROVIDER below rather than by identity comparison against two constants, which
# is what the two-model pilot did and what a five-model run cannot do.

ANTHROPIC = "anthropic"
GOOGLE = "google"

ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"
GOOGLE_MODEL = "gemini-3.6-flash"
PILOT_MODELS = (ANTHROPIC_MODEL, GOOGLE_MODEL)

# The main experiment's model set. Four are fixed; the fifth is the user's call
# after seeing the cost estimate (see DEVLOG). Candidates and their marginal
# cost are printed by run_main.py --estimate.
MAIN_MODELS = (
    "claude-haiku-4-5-20251001",
    "claude-sonnet-4-6",
    "gemini-3.6-flash",
    "gemini-3.1-pro-preview",
)

# The fifth slot. Adding either to MAIN_MODELS is the only change needed; the
# marginal cost of each is printed by `run_main.py --estimate`.
MAIN_MODEL_CANDIDATES = ("claude-opus-4-7", "gemini-3.7-flash")

PROVIDER: dict[str, str] = {
    "claude-haiku-4-5-20251001": ANTHROPIC,
    "claude-sonnet-4-6": ANTHROPIC,
    "claude-opus-4-7": ANTHROPIC,
    "gemini-3.6-flash": GOOGLE,
    "gemini-3.7-flash": GOOGLE,
    "gemini-3.1-pro-preview": GOOGLE,
}

# --- Elicitation (DESIGN.md §6) --------------------------------------------

N_SAMPLES = 5
TEMPERATURE = 1.0
API_TIMEOUT_SECONDS = 60

# Code-generation output ceiling. Raised from 1024 on 2026-08-15 after the
# pilot's Gemini LBPP code-extraction failures were traced to it: on the Gemini
# Interactions API max_output_tokens is a COMBINED budget for thinking tokens
# and visible output, and gemini-3.6-flash spends 900-990 thought tokens on an
# LBPP problem. All five failed codegen calls had thought+output = exactly 1020,
# leaving ~35-50 tokens for the answer. Claude, which is not billed a thinking
# budget out of this allowance here, peaked at 620 of 1024. See DEVLOG
# 2026-08-15 and elicit.was_truncated, which now detects the condition instead
# of letting it surface as apparent model incompetence.
MAX_OUTPUT_TOKENS_CODEGEN = 4096

# Slack (tokens) below the ceiling at which a Gemini reply is treated as
# truncated. The Interactions API exposes no finish_reason, so truncation is
# inferred from thought+output approaching max_output_tokens; observed slack on
# genuinely truncated pilot calls was 4-5 tokens.
GOOGLE_TRUNCATION_SLACK_TOKENS = 16

# Lowest available Gemini 3.x thinking level (see CLAUDE.md "API facts").
# Applied to rating calls only — placing a point on an ordinal scale is
# classification, not a task that benefits from extended thinking. Code
# generation keeps the model's default thinking level.
GOOGLE_RATING_THINKING_LEVEL = "minimal"

# Hard ceiling on total API calls made in one process, across all providers.
# Guards against a runaway loop silently burning budget. The main experiment
# needs far more than the pilot, so it raises the ceiling explicitly and
# visibly via elicit.set_call_budget rather than by patching this constant.
MAX_CALLS = 1200
MAX_CALLS_MAIN = 24_000

# Seed for the per-context randomisation of scale direction and vignette order
# (DESIGN.md §3, §4). Fixed so a run is reproducible; the drawn values are
# recorded per observation regardless.
PILOT_RANDOM_SEED = 20260814

# The main run does not draw from one sequential stream. Its randomisation is
# keyed: each (model, task) gets its own generator seeded from this value, the
# model id and the task id (see run_main.py). Two properties depend on that:
# the direction/vignette-order draw is identical across the three scale formats,
# so a format comparison is not also a direction comparison; and skipping
# already-finished work on resume cannot shift the draws for what remains, which
# a shared sequential stream would do.
MAIN_RANDOM_SEED = 20260815

# USD per million tokens, per model. Verified against the providers' current
# pricing pages on 2026-08-15 (see DEVLOG for the URLs). A missing price stays
# None rather than being guessed — a wrong constant here silently misreports
# spend — and the cost summary names which models it could not price.
#
# Two caveats that affect how these figures should be read:
#   - gemini-3.6-flash is at promotional pricing through 2026-12-31; from
#     2027-01-01 it doubles to $1.50/$7.50.
#   - gemini-3.1-pro-preview is tiered: these are the <=200k-token-prompt
#     prices. Above 200k it is $4.00/$18.00. Our largest prompt is ~1.5k, so
#     the low tier is the one that applies.
#   - Claude 4.7+ uses a newer tokenizer that produces roughly 30% more tokens
#     for the same text, so a Claude token count is not comparable to a Gemini
#     one at equal text length.
PRICE_PER_MTOK_USD: dict[str, dict[str, float | None]] = {
    "claude-haiku-4-5-20251001": {"input": 1.00, "output": 5.00},
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-opus-4-7": {"input": 5.00, "output": 25.00},
    "gemini-3.6-flash": {"input": 0.75, "output": 3.75},
    "gemini-3.7-flash": {"input": None, "output": None},
    "gemini-3.1-pro-preview": {"input": 2.00, "output": 12.00},
}

# Minimum prompt length (tokens) below which the provider will not cache, per
# model. Re-verified 2026-08-15 against Anthropic's prompt-caching documentation
# and Google's context-caching documentation (Gemini 3.x: 4,096).
#
# These minimums, not the code, decide whether caching does anything here. A
# prompt below its model's minimum is processed uncached with no error and no
# write premium even when it is marked with cache_control, so requesting a
# breakpoint is free. Only claude-sonnet-4-6's 1,024 is low enough for this
# workload's reused prompts (~1,150 tokens) to clear it — see
# `run_main.py --estimate`.
CACHE_MIN_PROMPT_TOKENS: dict[str, int] = {
    "claude-haiku-4-5-20251001": 4096,
    "claude-sonnet-4-6": 1024,
    "claude-opus-4-7": 2048,
    "gemini-3.6-flash": 4096,
    "gemini-3.7-flash": 4096,
    "gemini-3.1-pro-preview": 4096,
}

# What a cached token costs relative to a normal input token, per provider.
#
# Anthropic publishes these: a 5-minute cache write is 1.25x the base input
# price and a cache read is 0.1x (verified 2026-08-15 in the prompt-caching
# docs; we use the default 5-minute TTL). Google says only that it
# "automatically passes on cost savings" on an implicit cache hit and publishes
# no multiplier, so Google's stays None and no Google saving is ever claimed —
# which costs nothing here, since no Gemini prompt in this run reaches Gemini
# 3.x's 4,096-token minimum.
CACHE_MULTIPLIERS: dict[str, dict[str, float] | None] = {
    ANTHROPIC: {"write": 1.25, "read": 0.1},
    GOOGLE: None,
}

# --- Cost-estimate calibration (measured on 2026-08-15) ---------------------
# Read off the pilot's own raw logs (out/raw.jsonl, out/raw_scale100.jsonl), not
# assumed: chars-per-token by dividing each logged prompt's character count by
# its logged input_tokens, output figures by averaging logged
# output_tokens + thought_tokens per call type. Used only by
# `run_main.py --estimate`; nothing in the measurement path reads them.
#
# The Google codegen figure is a LOWER BOUND. It was measured while the codegen
# ceiling was still 1020 combined thinking+output tokens, and 20 of 40 Gemini
# codegen calls hit that ceiling exactly, so the sample is right-censored. With
# MAX_OUTPUT_TOKENS_CODEGEN now 4096 the true mean is higher, and any estimate
# built on it understates Gemini's cost.
CHARS_PER_TOKEN: dict[str, float] = {ANTHROPIC: 3.321, GOOGLE: 3.370}
EST_CODEGEN_OUTPUT_TOKENS: dict[str, int] = {ANTHROPIC: 201, GOOGLE: 854}
EST_RATING_OUTPUT_TOKENS: dict[str, int] = {ANTHROPIC: 5, GOOGLE: 2}

# Mean length of a logged solution. The estimate replays a filler string of this
# length wherever a real run would replay a generated solution, because the
# solution appears in every condition-V, condition-N and P4 prompt and so drives
# most of the input-token count.
EST_SOLUTION_CHARS = 412

# --- Rating scale (DESIGN.md §3) --------------------------------------------
# Format is an experimental variable, not a fixed choice: three formats are run
# on the same tasks and the same models. `p5` is the originally locked format,
# unchanged. See DESIGN.md §3 for why, and for the stability-vs-resolution
# tension between Wang, Zhou & Liu (arXiv:2608.08869) and our own pilot data.
#
# Threshold fractions (DESIGN.md §9): P1/P3/P4 and the §5 tolerance are defined
# as fractions of the format's width W = max - min, so a verdict means the same
# thing in every format. The fractions reproduce the original 5-point values
# exactly at W=4 (0.3 / 0.5 / 0.75 / 0.01), so no locked criterion changes value.

P1_MIN_SD_FRACTION_OF_WIDTH = 0.075
P3_MIN_DIFFERENCE_FRACTION_OF_WIDTH = 0.125
P4_MAX_ABS_GAP_FRACTION_OF_WIDTH = 0.1875
TOLERANCE_FRACTION_OF_WIDTH = 0.0025


@dataclass(frozen=True)
class ScaleFormat:
    """One response scale, with every quantity that depends on its width.

    `labels` holds only the points that carry a written label. For `p5` and
    `p7` that is every point; for `s100` it is the two endpoints, with the
    interior deliberately unlabelled. `fully_labelled` says which, because a
    per-scale-point distribution table is only meaningful in the first case.
    """

    name: str
    labels: Mapping[int, str]
    min_point: int
    max_point: int
    answer_instruction: str
    max_output_tokens_rating: int

    @property
    def width(self) -> int:
        return self.max_point - self.min_point

    @property
    def fully_labelled(self) -> bool:
        return len(self.labels) == self.width + 1

    def in_range(self, value: int) -> bool:
        return self.min_point <= value <= self.max_point

    @property
    def tolerance(self) -> float:
        return TOLERANCE_FRACTION_OF_WIDTH * self.width

    @property
    def p1_min_sd(self) -> float:
        return P1_MIN_SD_FRACTION_OF_WIDTH * self.width

    @property
    def p3_min_difference(self) -> float:
        return P3_MIN_DIFFERENCE_FRACTION_OF_WIDTH * self.width

    @property
    def p4_max_abs_gap(self) -> float:
        return P4_MAX_ABS_GAP_FRACTION_OF_WIDTH * self.width


# Identical wording for p5 and p7 so that a difference between them is a
# difference of cardinality and not of instruction. Strengthened 2026-08-14:
# 17 pilot parse failures were a valid leading digit followed by prose,
# truncated mid-sentence at the rating token cap. parse_rating was deliberately
# left strict (see elicit.parse_rating) rather than relaxed after seeing the
# data; this is the other half of that fix.
_DIGIT_INSTRUCTION = (
    "Reply with a single digit and nothing else — no words, no punctuation, "
    "no explanation."
)

SCALE_P5 = ScaleFormat(
    name="p5",
    labels=MappingProxyType(
        {
            1: "Very unlikely",
            2: "Unlikely",
            3: "Uncertain",
            4: "Likely",
            5: "Very likely",
        }
    ),
    min_point=1,
    max_point=5,
    answer_instruction=_DIGIT_INSTRUCTION,
    max_output_tokens_rating=8,
)

# The Pinocchio Inventory format (Plisiecki et al., arXiv:2607.20082). Its four
# shared labels sit at the same positions as p5's, with two intermediate steps
# added, so the two formats differ in resolution and not in vocabulary.
SCALE_P7 = ScaleFormat(
    name="p7",
    labels=MappingProxyType(
        {
            1: "Very unlikely",
            2: "Unlikely",
            3: "Somewhat unlikely",
            4: "Uncertain",
            5: "Somewhat likely",
            6: "Likely",
            7: "Very likely",
        }
    ),
    min_point=1,
    max_point=7,
    answer_instruction=_DIGIT_INSTRUCTION,
    max_output_tokens_rating=8,
)

# Endpoints only, interior unlabelled. Wording and token cap are exactly those
# used by the 2026-08-14 0-100 control run, so its data stays comparable with
# this format's: "a single digit" would cap replies at 0-9 and defeat the scale,
# and 8 tokens was sized for a one-digit reply.
SCALE_S100 = ScaleFormat(
    name="s100",
    labels=MappingProxyType({0: "Very unlikely", 100: "Very likely"}),
    min_point=0,
    max_point=100,
    answer_instruction=(
        "Reply with a single integer from 0 to 100 and nothing else — no words, "
        "no punctuation, no explanation."
    ),
    max_output_tokens_rating=16,
)

SCALE_FORMATS: dict[str, ScaleFormat] = {
    fmt.name: fmt for fmt in (SCALE_P5, SCALE_P7, SCALE_S100)
}

# Order in which formats are run and reported. p5 first so the main run's
# opening cells are directly comparable with the pilot.
MAIN_SCALE_FORMATS = (SCALE_P5, SCALE_P7, SCALE_S100)

# --- Question wording (DESIGN.md §4) ----------------------------------------
# Differ only in pronoun; any further asymmetry manufactures a
# response-consistency violation for purely linguistic reasons.
#
# Reworded 2026-08-14: ground truth is "passes ALL hidden tests" (DESIGN.md §8),
# and the original "...is correct?" wording asked something vaguer than that,
# inviting a reflexive 5. This wording names the actual measurement.

QUESTION_VIGNETTE = (
    "How likely is it that this solution passes every test case, including "
    "edge cases?"
)
QUESTION_SELF = (
    "How likely is it that your solution passes every test case, including "
    "edge cases?"
)
QUESTION_OTHER = (
    "How likely is it that this solution passes every test case, including "
    "edge cases?"
)

# --- Scale direction (DESIGN.md §3) -----------------------------------------
# Randomised per context and recorded, so label-order sensitivity is measured
# rather than silently absorbed. Ratings given under DESCENDING presentation
# must be re-oriented before they are averaged with ascending ones — see
# analyze._orient.

SCALE_ASCENDING = "ascending"
SCALE_DESCENDING = "descending"
SCALE_DIRECTIONS = (SCALE_ASCENDING, SCALE_DESCENDING)

# --- Pass/fail thresholds (DESIGN.md §9) ------------------------------------
# Fixed before the numbers were seen. GO requires P1, P2 and P3; P4 failing
# does not block the main experiment but must be reported as a named limitation.
#
# The width-relative thresholds live on ScaleFormat above (p1_min_sd,
# p3_min_difference, p4_max_abs_gap, tolerance). Only the two rates and the
# distinct-value count are format-independent and therefore constants here.
#
# P1_MIN_DISTINCT_SCALE_POINTS stays absolute at 3 and that is a stated
# limitation (DESIGN.md §9): a count has no unit to divide by, but the number of
# values available is not constant across formats (5, 7, 101), so three distinct
# values is a weaker requirement in a finer format. It is kept because its job is
# to catch total collapse (Martorell & Bianchi, arXiv:2603.18893), which it does
# in every format; cross-format P1 comparisons must be read on the SD column.

P1_MIN_DISTINCT_SCALE_POINTS = 3
P2_MAX_MISORDER_RATE = 0.20
P2_MAX_TIE_RATE = 0.40

# --- Tasks -------------------------------------------------------------------
# Difficulty mix added 2026-08-14: the pilot's first real run showed y (self-
# report) pinned at 5.000 in 36/39 observations because uniform MBPP is too
# easy for these models — see DEVLOG "THE blocking issue". Half the task set
# is now LBPP (Matton et al., EMNLP 2024; CohereForAI/lbpp on the HF Hub),
# explicitly designed as a structurally equivalent, harder drop-in replacement
# for MBPP, so the Task interface below is unchanged.

NUM_MBPP_TASKS = 10
NUM_LBPP_TASKS = 10

# Main experiment: 30 + 30. DESIGN.md §10 specifies 100 tasks (simulation: 98%
# of runs positive at 100, 93% at 60); 60 is the user's instruction for this run
# and is logged as a deviation in DEVLOG Open Questions, not silently applied.
NUM_MBPP_TASKS_MAIN = 30
NUM_LBPP_TASKS_MAIN = 30
MBPP_MIN_ASSERTS = 3  # keep only MBPP tasks with >= 3 asserts (1 visible + rest hidden)
MBPP_SOURCING_TIME_BUDGET_MINUTES = 15
LBPP_MIN_TESTS = 3  # keep only LBPP tasks with >= 3 test_list entries (1 visible + rest hidden)
LBPP_SOURCING_TIME_BUDGET_MINUTES = 20

# --- Execution boundary (DESIGN.md §8) --------------------------------------

RLIMIT_AS_BYTES = 512 * 1024 * 1024  # 512 MB
RLIMIT_CPU_SECONDS = 5
RLIMIT_NOFILE = 64
WALLCLOCK_TIMEOUT_SECONDS = 10

BANNED_SUBSTRINGS = (
    "import os",
    "import sys",
    "import socket",
    "import subprocess",
    "open(",
    "__import__",
    "eval(",
    "exec(",
)
