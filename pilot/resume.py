"""Resuming an interrupted run from the files it already wrote.

The main experiment is ~23,000 API calls over many hours. An interruption — a
timeout, a rate limit, a dropped connection, Ctrl-C — must not cost the whole
run, so both artefacts a run produces are keyed and replayable:

**Observations** are keyed by `(model, task_id, scale_format)`. A key already
present in the observations file is finished work and is skipped.

**Solutions** are keyed by `(model, task_id)` and persisted separately. This is
not an optimisation. DESIGN.md §10 requires one solution per (model, task) reused
across all three scale formats, so that a format difference cannot be a solution
difference. Sampling is at temperature 1.0, so re-generating a solution after an
interruption would produce a *different* one, and the three formats of that pair
would silently stop being paired. Persisting the solution is what makes the
within-subject design survive a restart.

Ground truth is stored alongside the solution rather than recomputed, for the
same reason: it is a property of that exact solution text.
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from pilot.analyze import Observation

ObservationKey = tuple[str, str, str]
SolutionKey = tuple[str, str]


@dataclass(frozen=True)
class SolutionRecord:
    """One (model, task) code-generation result and its ground truth."""

    model: str
    task_id: str
    solution: str | None
    failure_reason: str | None
    passes_hidden: bool
    passes_visible: bool
    executes_cleanly: bool

    @property
    def key(self) -> SolutionKey:
        return (self.model, self.task_id)


def _read_jsonl(path: Path) -> list[dict]:
    """Reads a jsonl file, tolerating a truncated final line.

    A run killed mid-write can leave a partial last line. Dropping it is correct
    — the work it represents is simply not recorded, so it will be redone — but
    silently dropping a line *earlier* in the file would hide real data loss, so
    only the final line is forgiven.
    """
    if not path.exists():
        return []
    lines = path.read_text().splitlines()
    records = []
    for index, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            if index == len(lines) - 1:
                break
            raise
    return records


def observation_key(obs: Observation) -> ObservationKey:
    return (obs.model, obs.task_id, obs.scale_format)


def load_observations(path: Path) -> list[Observation]:
    return [Observation(**record) for record in _read_jsonl(path)]


def completed_observation_keys(path: Path) -> set[ObservationKey]:
    return {observation_key(obs) for obs in load_observations(path)}


def load_solutions(path: Path) -> dict[SolutionKey, SolutionRecord]:
    return {
        record.key: record
        for record in (SolutionRecord(**r) for r in _read_jsonl(path))
    }


def append_solution(record: SolutionRecord, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(asdict(record)) + "\n")
