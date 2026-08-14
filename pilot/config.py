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

QUESTION_VIGNETTE = "How likely is it that this solution is correct?"
QUESTION_SELF = "How likely is it that your solution is correct?"
QUESTION_OTHER = "How likely is it that this solution is correct?"

ANSWER_INSTRUCTION = "Reply with the number only."

# --- Rescaling tolerance (DESIGN.md §5) -------------------------------------

TOLERANCE = 0.01

# --- Tasks -------------------------------------------------------------------

NUM_PILOT_TASKS = 20
MBPP_MIN_ASSERTS = 3  # keep only MBPP tasks with >= 3 asserts (1 visible + rest hidden)
MBPP_SOURCING_TIME_BUDGET_MINUTES = 15

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
