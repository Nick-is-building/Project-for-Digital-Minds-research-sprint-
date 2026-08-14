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
# pilot specifically.

ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"
GOOGLE_MODEL = "gemini-2.5-flash"
PILOT_MODELS = (ANTHROPIC_MODEL, GOOGLE_MODEL)

# --- Elicitation (DESIGN.md §6) --------------------------------------------

N_SAMPLES = 5
TEMPERATURE = 1.0
API_TIMEOUT_SECONDS = 30

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
