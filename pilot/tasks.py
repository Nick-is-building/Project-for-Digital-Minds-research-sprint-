"""Loads the pilot's coding tasks: a difficulty mix of MBPP and LBPP.

MBPP source: test split of `google-research-datasets/mbpp` on the HF Hub — the
canonical `mbpp` repo id fails to load under datasets>=4, see DEVLOG.md. Tasks
are filtered to those with >= config.MBPP_MIN_ASSERTS asserts, a single
consistent entry-point function name across all asserts, and no setup code.
The first assert becomes visible, the rest hidden.

LBPP source: python subset of `CohereForAI/lbpp` on the HF Hub (Matton et al.,
EMNLP 2024) — explicitly designed as a structurally equivalent, harder
drop-in replacement for MBPP. Added 2026-08-14 because uniform MBPP left the
pilot's self-report `y` pinned at the scale ceiling (DEVLOG "THE blocking
issue"). `test_list` and `test_setup` ship base64+zlib+pickle-obfuscated
(contamination-proofing, not a security boundary — the pickled payload is
itself a Python literal, decoded with `ast.literal_eval`, never executed).
The first test_list entry becomes visible, the rest hidden, same as MBPP.
`entry_point` comes from the `signature` field rather than from parsing an
assert, since a LBPP test entry is a multi-line block, not a bare assert.

Each loaded Task records which set it came from (`task_set`), so the pilot
report can compare the two halves.

VIGNETTE_LOW and VIGNETTE_HIGH (DESIGN.md §7) also live here: they are
task-shaped constants, but fixed and hand-written rather than loaded.
"""

import ast
import base64
import pickle
import re
import zlib
from dataclasses import dataclass

from datasets import load_dataset

from pilot import config

_MBPP_ENTRY_POINT_RE = re.compile(r"assert\s+(\w+)\(")
_LBPP_SIGNATURE_RE = re.compile(r"^\s*def\s+(\w+)\s*\(")


@dataclass(frozen=True)
class Task:
    task_id: str
    prompt: str
    visible_assert: str
    hidden_asserts: list[str]
    entry_point: str
    task_set: str  # "mbpp" or "lbpp"
    setup_code: str = ""  # honoured verbatim if present (LBPP only)


# --- MBPP --------------------------------------------------------------------


def _mbpp_entry_point(assert_stmt: str) -> str | None:
    match = _MBPP_ENTRY_POINT_RE.match(assert_stmt)
    return match.group(1) if match else None


def _mbpp_qualifies(row: dict) -> str | None:
    """Returns the entry point name if `row` qualifies, else None."""
    if row["test_setup_code"]:
        return None
    if len(row["test_list"]) < config.MBPP_MIN_ASSERTS:
        return None
    entry_points = {_mbpp_entry_point(a) for a in row["test_list"]}
    if len(entry_points) != 1 or None in entry_points:
        return None
    return entry_points.pop()


def _load_mbpp(n: int) -> list[Task]:
    """Loads the first `n` qualifying MBPP test-split tasks, by task_id."""
    # Without this, n=0 falls through to "return every qualifying task": the
    # count is only checked after an append, so it never equals 0.
    if n <= 0:
        return []
    dataset = load_dataset("google-research-datasets/mbpp", split="test")
    rows = sorted(dataset, key=lambda r: r["task_id"])

    loaded: list[Task] = []
    for row in rows:
        entry_point = _mbpp_qualifies(row)
        if entry_point is None:
            continue
        loaded.append(
            Task(
                task_id=f"mbpp/{row['task_id']}",
                prompt=row["text"],
                visible_assert=row["test_list"][0],
                hidden_asserts=list(row["test_list"][1:]),
                entry_point=entry_point,
                task_set="mbpp",
            )
        )
        if len(loaded) == n:
            break

    if len(loaded) < n:
        raise RuntimeError(f"Only found {len(loaded)} qualifying MBPP tasks, needed {n}.")
    return loaded


# --- LBPP ----------------------------------------------------------------------


def _lbpp_decode(value: str | None) -> object:
    """Reverses LBPP's base64 -> zlib -> pickle -> (Python-literal string) chain."""
    if not value:
        return value
    pickled = pickle.loads(zlib.decompress(base64.b64decode(value)))
    return ast.literal_eval(pickled)


def _lbpp_entry_point(signature: str) -> str | None:
    match = _LBPP_SIGNATURE_RE.match(signature)
    return match.group(1) if match else None


def _load_lbpp(n: int) -> list[Task]:
    """Loads the first `n` qualifying LBPP python-split tasks, by task_id."""
    if n <= 0:
        return []
    dataset = load_dataset("CohereForAI/lbpp", "python", split="test")
    rows = sorted(dataset, key=lambda r: r["task_id"])

    loaded: list[Task] = []
    for row in rows:
        entry_point = _lbpp_entry_point(row["signature"])
        if entry_point is None:
            continue
        test_list = _lbpp_decode(row["test_list"])
        if not isinstance(test_list, list) or len(test_list) < config.LBPP_MIN_TESTS:
            continue
        loaded.append(
            Task(
                task_id=row["task_id"],
                prompt=row["instruction"],
                visible_assert=test_list[0],
                hidden_asserts=list(test_list[1:]),
                entry_point=entry_point,
                task_set="lbpp",
                setup_code=_lbpp_decode(row["test_setup"]) or "",
            )
        )
        if len(loaded) == n:
            break

    if len(loaded) < n:
        raise RuntimeError(f"Only found {len(loaded)} qualifying LBPP tasks, needed {n}.")
    return loaded


def load_tasks(
    n_mbpp: int = config.NUM_MBPP_TASKS, n_lbpp: int = config.NUM_LBPP_TASKS
) -> list[Task]:
    """Loads the pilot's difficulty-mix task set: `n_mbpp` MBPP + `n_lbpp` LBPP."""
    return _load_mbpp(n_mbpp) + _load_lbpp(n_lbpp)


# --- Vignettes (DESIGN.md §7) ------------------------------------------------
#
# Two solutions to ONE problem, so only quality differs between them. The
# problem is list partitioning, which is none of the 20 pilot tasks (MBPP test
# split ids 11-30: string manipulation, duplicate detection, geometry, binary
# conversion, binomial coefficients) — rating a vignette therefore cannot leak
# an answer. Kept general rather than narrowly technical per Grol-Prokopczyk et
# al. (2015): vignette-equivalence violations are markedly worse for highly
# specific texts.
#
# The two solutions are deliberately structurally parallel — same 9 lines, same
# accumulate-with-a-running-index shape, differing only in whether the
# remainder is distributed — so that length and style cannot drive the rating.
# Both texts are built from the same VIGNETTE_PROBLEM string, so the problem
# statement cannot drift between them.

VIGNETTE_PROBLEM = (
    "Write a function `split_into_parts(items, n)` that splits the list `items` "
    "into `n` parts. The parts must be as equal in size as possible, must keep "
    "the original order of the elements, and together must contain every element "
    "of `items` exactly once. For example, splitting [1, 2, 3, 4, 5, 6, 7] into "
    "3 parts may return [[1, 2, 3], [4, 5], [6, 7]]."
)

# Hidden tests for the vignette problem. Property-based rather than asserting one
# exact partition, because "as equal in size as possible" does not fix which part
# receives the remainder — a correct solution that distributes it differently
# must not be scored wrong.
VIGNETTE_HIDDEN_ASSERTS = (
    "assert split_into_parts([1, 2, 3, 4, 5, 6], 3) == [[1, 2], [3, 4], [5, 6]]",
    "assert [x for p in split_into_parts([1, 2, 3, 4, 5, 6, 7], 3) for x in p] == [1, 2, 3, 4, 5, 6, 7]",
    "assert len(split_into_parts([1, 2, 3, 4, 5, 6, 7], 3)) == 3",
    "assert max(len(p) for p in split_into_parts([1, 2, 3, 4, 5, 6, 7], 3)) - min(len(p) for p in split_into_parts([1, 2, 3, 4, 5, 6, 7], 3)) <= 1",
    "assert [x for p in split_into_parts(list(range(10)), 4) for x in p] == list(range(10))",
    "assert split_into_parts([1, 2, 3], 1) == [[1, 2, 3]]",
    "assert split_into_parts([1, 2, 3], 3) == [[1], [2], [3]]",
)

# VERIFIED BY EXECUTION 2026-08-14 via sandbox.run_solution against
# VIGNETTE_HIDDEN_ASSERTS: FAILS (5 of 7 asserts pass, 2 fail). Wrong because
# `len(items) // n` discards the remainder, so any length not divisible by `n`
# silently loses elements: 7 items into 3 parts returns 6 of them. Correct
# whenever the length divides evenly, which is what makes it plausible rather
# than absurd — it is not a syntax error and not obviously broken at a glance.
VIGNETTE_LOW_CODE = """def split_into_parts(items, n):
    size = len(items) // n
    parts = []
    start = 0
    for i in range(n):
        end = start + size
        parts.append(items[start:end])
        start = end
    return parts
"""

# VERIFIED BY EXECUTION 2026-08-14 via sandbox.run_solution against
# VIGNETTE_HIDDEN_ASSERTS: PASSES (7 of 7). `divmod` splits off the remainder
# and the first `extra` parts each take one additional element — the idiomatic
# way to write this.
VIGNETTE_HIGH_CODE = """def split_into_parts(items, n):
    size, extra = divmod(len(items), n)
    parts = []
    start = 0
    for i in range(n):
        end = start + size + (1 if i < extra else 0)
        parts.append(items[start:end])
        start = end
    return parts
"""

VIGNETTE_LOW = f"{VIGNETTE_PROBLEM}\n\n{VIGNETTE_LOW_CODE}"
VIGNETTE_HIGH = f"{VIGNETTE_PROBLEM}\n\n{VIGNETTE_HIGH_CODE}"
