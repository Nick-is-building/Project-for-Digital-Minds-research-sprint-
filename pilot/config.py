"""Central tunables for the pilot pipeline.

Every constant used by more than one module — or that would otherwise be a
magic number/string buried in logic — lives here. See DESIGN.md for the
rationale behind the scale, wording, and execution-boundary values; this file
only encodes what DESIGN.md already fixed.
"""

from pathlib import Path

# --- Paths -----------------------------------------------------------------

PILOT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PILOT_DIR.parent
OUT_DIR = PILOT_DIR / "out"
RAW_JSONL_PATH = OUT_DIR / "raw.jsonl"
SANDBOX_TMP_DIR = PILOT_DIR / ".sandbox_tmp"

# --- Models ------------------------------------------------------------------
# DESIGN.md does not fix pilot model identifiers (see DEVLOG.md Open
# Questions). Chosen here: one model per provider, both from the cheap/fast
# tier to keep pilot cost low (20 tasks x 2 models x several samples each).
# Cross-provider diversity is kept per the locked "API models only" decision;
# capability spread within this pair is secondary to cost control for the
# pilot specifically. GOOGLE_MODEL uses the Interactions API (see CLAUDE.md
# "API facts") via client.interactions.create, not client.models.generate_content.

ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"
GOOGLE_MODEL = "gemini-3.6-flash"
PILOT_MODELS = (ANTHROPIC_MODEL, GOOGLE_MODEL)

# --- Elicitation (DESIGN.md §6) --------------------------------------------

N_SAMPLES = 5
TEMPERATURE = 1.0
API_TIMEOUT_SECONDS = 30

# Rating calls (vignette/self/other) expect a single digit; cap tokens so a
# malformed, rambling answer doesn't get billed at length. Code-generation
# calls use the larger default instead.
MAX_OUTPUT_TOKENS_RATING = 8
MAX_OUTPUT_TOKENS_DEFAULT = 1024

# Lowest available Gemini 3.x thinking level (see CLAUDE.md "API facts").
# Applied to rating calls only — rating a 5-point scale is classification,
# not a task that benefits from extended thinking. Code generation keeps
# the model's default thinking level.
GOOGLE_RATING_THINKING_LEVEL = "minimal"

# Hard ceiling on total API calls made in one process, across both providers.
# Guards against a runaway loop silently burning budget.
MAX_CALLS = 1200

# Seed for the per-context randomisation of scale direction and vignette order
# (DESIGN.md §3, §4). Fixed so a run is reproducible; the drawn values are
# recorded per observation regardless.
PILOT_RANDOM_SEED = 20260814

# USD per million tokens, per model. NOT FILLED IN: these must be copied from
# each provider's current pricing page before any cost figure is reported.
# Deliberately left as None rather than guessed — a wrong constant here would
# silently misreport spend, and gemini-3.6-flash pricing in particular is newer
# than this assistant's training data. run_pilot prints token counts either way
# and says which prices are missing.
PRICE_PER_MTOK_USD: dict[str, dict[str, float | None]] = {
    ANTHROPIC_MODEL: {"input": 1.00, "output": 5.00},
    GOOGLE_MODEL: {"input": None, "output": None},
}

# --- Rating scale (DESIGN.md §3) --------------------------------------------

SCALE_POINTS = {
    1: "Very unlikely",
    2: "Unlikely",
    3: "Uncertain",
    4: "Likely",
    5: "Very likely",
}

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

# Strengthened 2026-08-14: 17 of the pilot's parse failures (16 of them Claude,
# on the low vignette) were a valid leading digit followed by prose, truncated
# mid-sentence at MAX_OUTPUT_TOKENS_RATING. The parser was deliberately left
# strict (see elicit.parse_rating) rather than relaxed to take the leading
# digit after seeing the data. This is the other half of the fix: make the
# instruction itself harder to ignore.
ANSWER_INSTRUCTION = "Reply with a single digit and nothing else — no words, no punctuation, no explanation."

# --- Rescaling tolerance (DESIGN.md §5) -------------------------------------

TOLERANCE = 0.01

# --- Scale direction (DESIGN.md §3) -----------------------------------------
# Randomised per context and recorded, so label-order sensitivity is measured
# rather than silently absorbed. Ratings given under DESCENDING presentation
# must be re-oriented before they are averaged with ascending ones — see
# analyze._orient.

SCALE_ASCENDING = "ascending"
SCALE_DESCENDING = "descending"
SCALE_DIRECTIONS = (SCALE_ASCENDING, SCALE_DESCENDING)

# --- Pilot pass/fail thresholds (DESIGN.md §9) ------------------------------
# Fixed before the numbers were seen. GO requires P1, P2 and P3; P4 failing
# does not block the main experiment but must be reported as a named limitation.

P1_MIN_DISTINCT_SCALE_POINTS = 3
P1_MIN_SD = 0.3
P2_MAX_MISORDER_RATE = 0.20
P2_MAX_TIE_RATE = 0.40
P3_MIN_SCALE_POINT_DIFFERENCE = 0.5
P4_MAX_ABS_GAP = 0.75

# --- Tasks -------------------------------------------------------------------
# Difficulty mix added 2026-08-14: the pilot's first real run showed y (self-
# report) pinned at 5.000 in 36/39 observations because uniform MBPP is too
# easy for these models — see DEVLOG "THE blocking issue". Half the task set
# is now LBPP (Matton et al., EMNLP 2024; CohereForAI/lbpp on the HF Hub),
# explicitly designed as a structurally equivalent, harder drop-in replacement
# for MBPP, so the Task interface below is unchanged.

NUM_MBPP_TASKS = 10
NUM_LBPP_TASKS = 10
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
