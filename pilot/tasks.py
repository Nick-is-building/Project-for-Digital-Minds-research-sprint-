"""Loads the pilot's coding tasks.

Source: MBPP test split (`google-research-datasets/mbpp` on the HF Hub — the
canonical `mbpp` repo id fails to load under datasets>=4, see DEVLOG.md). Tasks
are filtered to those with >= config.MBPP_MIN_ASSERTS asserts, a single
consistent entry-point function name across all asserts, and no setup code
(keeps the sandbox's execution model simple: prompt + solution + one assert
per exec). The first assert becomes visible, the rest hidden.

VIGNETTE_LOW and VIGNETTE_HIGH are NOT written in this module — see DESIGN.md
§7. They are declared here as placeholders because tasks.py is the natural
home for task-shaped constants, not because they are ready.
"""

import re
from dataclasses import dataclass

from datasets import load_dataset

from pilot import config

_ENTRY_POINT_RE = re.compile(r"assert\s+(\w+)\(")


@dataclass(frozen=True)
class Task:
    task_id: int
    prompt: str
    visible_assert: str
    hidden_asserts: list[str]
    entry_point: str


def _entry_point(assert_stmt: str) -> str | None:
    match = _ENTRY_POINT_RE.match(assert_stmt)
    return match.group(1) if match else None


def _qualifies(row: dict) -> str | None:
    """Returns the entry point name if `row` qualifies, else None."""
    if row["test_setup_code"]:
        return None
    if len(row["test_list"]) < config.MBPP_MIN_ASSERTS:
        return None
    entry_points = {_entry_point(a) for a in row["test_list"]}
    if len(entry_points) != 1 or None in entry_points:
        return None
    return entry_points.pop()


def load_tasks(n: int = config.NUM_PILOT_TASKS) -> list[Task]:
    """Loads the first `n` qualifying MBPP test-split tasks, by task_id."""
    dataset = load_dataset("google-research-datasets/mbpp", split="test")
    rows = sorted(dataset, key=lambda r: r["task_id"])

    tasks: list[Task] = []
    for row in rows:
        entry_point = _qualifies(row)
        if entry_point is None:
            continue
        tasks.append(
            Task(
                task_id=row["task_id"],
                prompt=row["text"],
                visible_assert=row["test_list"][0],
                hidden_asserts=list(row["test_list"][1:]),
                entry_point=entry_point,
            )
        )
        if len(tasks) == n:
            break

    if len(tasks) < n:
        raise RuntimeError(
            f"Only found {len(tasks)} qualifying MBPP tasks, needed {n}."
        )
    return tasks


# Fixed constants, texts written in a later session — see DESIGN.md §7.
VIGNETTE_LOW = ""
VIGNETTE_HIGH = ""
