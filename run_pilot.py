"""Pilot orchestrator: 2 models x 20 tasks, conditions V and N, plus the P4 probe.

Sequencing only. The scale and question wording live in `pilot.config`, the
rescaling in `pilot.rescale`, the metrics and thresholds in `pilot.analyze`,
execution in `pilot.sandbox`, and API access in `pilot.elicit`. Nothing is
decided here.

Turn sequence, per DESIGN.md §4:

    Condition V   task+visible assert -> solution, vignette -> question,
                  vignette -> question, self-question
    Condition N   task -> solution, self-question
    P4 probe      fresh context: task, the same solution presented neutrally
                  with no indication of authorship, other-question

One solution is generated per (model, task) and replayed into all three. That is
forced by DESIGN.md §9's P4 probe, which compares ratings of *byte-identical*
code; generating a fresh solution per condition would also confound V against N
with a change of subject matter.

Condition V is sampled as `N_SAMPLES` independent full conversation threads
rather than as three fixed-prefix batches, because the priming mechanism King &
Wand rely on requires the model's own vignette ratings to be in the context when
it rates itself. Each thread is internally consistent and replays its own
answers; across threads it is still five independent samples at temperature 1.0.

Usage:
    python run_pilot.py --dry-run    # exact message sequence, no API calls
    python run_pilot.py              # full pilot
"""

import argparse
import dataclasses
import json
import random
import re
import sys

from pilot import analyze, config, elicit, sandbox, tasks

_FENCE_RE = re.compile(r"```(?:python)?\s*\n(.*?)```", re.DOTALL)

DRY_RUN_SOLUTION_STANDIN = (
    "<the model's generated solution would be replayed here verbatim; "
    "no API call was made>"
)


# --- Message construction (DESIGN.md §3, §4) --------------------------------


def _scale_block(direction: str) -> str:
    points = sorted(config.SCALE_POINTS)
    if direction == config.SCALE_DESCENDING:
        points = list(reversed(points))
    return "\n".join(f"{p} = {config.SCALE_POINTS[p]}" for p in points)


def _rating_message(question: str, direction: str, body: str | None = None) -> str:
    parts = [body] if body else []
    parts += [question, _scale_block(direction), config.ANSWER_INSTRUCTION]
    return "\n\n".join(parts)


def _codegen_message(task: tasks.Task) -> str:
    return (
        f"{task.prompt}\n\n"
        f"Your solution must satisfy:\n{task.visible_assert}\n\n"
        "Reply with a single Python function and no explanation."
    )


def _extract_code(text: str | None) -> str | None:
    if text is None:
        return None
    match = _FENCE_RE.search(text)
    code = match.group(1) if match else text
    return code if "def " in code else None


def _vignette_order(low_first: bool) -> tuple[tuple[str, str], ...]:
    low = ("low", tasks.VIGNETTE_LOW)
    high = ("high", tasks.VIGNETTE_HIGH)
    return (low, high) if low_first else (high, low)


def _walk_condition_v(
    task: tasks.Task,
    solution: str,
    direction: str,
    low_first: bool,
    respond,
) -> dict[str, str | None]:
    """Walks one condition-V thread, calling `respond(label, messages)` per call.

    The single source of truth for the DESIGN.md §4 turn order: the real run and
    --dry-run both drive this, differing only in what `respond` does, so the
    printed sequence cannot drift from the sent one. Each vignette is presented,
    rated, and the reply appended as an assistant turn before the next question,
    which is what puts the model's own anchor ratings in context when it rates
    itself.
    """
    messages = [
        {"role": "user", "content": _codegen_message(task)},
        {"role": "assistant", "content": solution},
    ]
    replies: dict[str, str | None] = {}

    for which, text in _vignette_order(low_first):
        messages.append(
            {
                "role": "user",
                "content": _rating_message(config.QUESTION_VIGNETTE, direction, text),
            }
        )
        reply = respond(f"vignette rating: {which}", list(messages))
        replies[which] = reply
        messages.append({"role": "assistant", "content": reply or ""})

    messages.append(
        {"role": "user", "content": _rating_message(config.QUESTION_SELF, direction)}
    )
    replies["self"] = respond("self-assessment", list(messages))
    return replies


def _p4_messages(task: tasks.Task, solution: str, direction: str) -> list[dict]:
    """Fresh context, no assistant turn: authorship is what the probe removes."""
    neutral = (
        f"{task.prompt}\n\n"
        f"The following solution has been submitted for review.\n\n{solution}"
    )
    return [
        {
            "role": "user",
            "content": _rating_message(config.QUESTION_OTHER, direction, neutral),
        }
    ]


# --- Planning and budget ----------------------------------------------------


def _calls_per_observation() -> int:
    codegen = 1
    condition_v = 3 * config.N_SAMPLES  # two vignettes + self, per thread
    condition_n = config.N_SAMPLES
    p4_probe = config.N_SAMPLES
    return codegen + condition_v + condition_n + p4_probe


def _planned_calls(n_tasks: int) -> int:
    return _calls_per_observation() * n_tasks * len(config.PILOT_MODELS)


# --- Execution --------------------------------------------------------------


def _run_condition_v(
    model: str, task: tasks.Task, solution: str, direction: str, low_first: bool
) -> dict[str, list[int | None]]:
    """`N_SAMPLES` independent threads through the same condition-V context."""
    draws: dict[str, list[int | None]] = {"low": [], "high": [], "self": []}

    for sample_index in range(config.N_SAMPLES):
        replies = _walk_condition_v(
            task,
            solution,
            direction,
            low_first,
            lambda _label, messages: elicit.elicit_text(
                model, messages, True, sample_index
            ),
        )
        for key in draws:
            draws[key].append(elicit.parse_rating(replies[key]))

    return draws


def _run_observation(
    model: str, task: tasks.Task, rng: random.Random
) -> analyze.Observation:
    direction = rng.choice(config.SCALE_DIRECTIONS)
    low_first = rng.choice((True, False))

    codegen_messages = [{"role": "user", "content": _codegen_message(task)}]
    solution = _extract_code(elicit.elicit_text(model, codegen_messages, False))

    if solution is None:
        return analyze.Observation(
            model=model,
            task_id=task.task_id,
            scale_direction=direction,
            low_vignette_first=low_first,
            y_v_draws=[],
            z_lo_draws=[],
            z_hi_draws=[],
            y_n_draws=[],
            other_draws=[],
            passes_hidden=False,
            passes_visible=False,
            executes_cleanly=False,
            code_extracted=False,
        )

    v_draws = _run_condition_v(model, task, solution, direction, low_first)

    condition_n = [
        {"role": "user", "content": _codegen_message(task)},
        {"role": "assistant", "content": solution},
        {"role": "user", "content": _rating_message(config.QUESTION_SELF, direction)},
    ]
    y_n_draws = elicit.elicit(model, condition_n, config.N_SAMPLES, True)
    other_draws = elicit.elicit(
        model, _p4_messages(task, solution, direction), config.N_SAMPLES, True
    )

    return analyze.Observation(
        model=model,
        task_id=task.task_id,
        scale_direction=direction,
        low_vignette_first=low_first,
        y_v_draws=v_draws["self"],
        z_lo_draws=v_draws["low"],
        z_hi_draws=v_draws["high"],
        y_n_draws=y_n_draws,
        other_draws=other_draws,
        passes_hidden=sandbox.run_solution(solution, task.hidden_asserts),
        passes_visible=sandbox.run_solution(solution, [task.visible_assert]),
        executes_cleanly=sandbox.run_solution(solution, []),
        code_extracted=True,
    )


def _append_observation(obs: analyze.Observation) -> None:
    config.OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(config.OUT_DIR / "observations.jsonl", "a") as f:
        f.write(json.dumps(dataclasses.asdict(obs)) + "\n")


# --- Reporting --------------------------------------------------------------


def _print_cost_summary() -> None:
    totals: dict[str, dict[str, int]] = {}
    if not config.RAW_JSONL_PATH.exists():
        print("No raw.jsonl found; no cost to report.")
        return

    with open(config.RAW_JSONL_PATH) as f:
        for line in f:
            record = json.loads(line)
            model_totals = totals.setdefault(
                record["model"], {"input": 0, "output": 0}
            )
            model_totals["input"] += record.get("input_tokens") or 0
            model_totals["output"] += record.get("output_tokens") or 0

    print("--- Cost summary ---")
    known_total = 0.0
    for model, tokens in totals.items():
        prices = config.PRICE_PER_MTOK_USD.get(model, {})
        price_in, price_out = prices.get("input"), prices.get("output")
        if price_in is None or price_out is None:
            print(
                f"{model}: no price configured — set "
                f"config.PRICE_PER_MTOK_USD[{model!r}] from the provider's "
                f"pricing page. Tokens: {tokens['input']} in / "
                f"{tokens['output']} out."
            )
            continue
        cost = tokens["input"] / 1e6 * price_in + tokens["output"] / 1e6 * price_out
        known_total += cost
        print(f"{model}: ${cost:.4f}")
    print(f"Total across models with a configured price: ${known_total:.4f}")


# --- Dry run ----------------------------------------------------------------


def _dry_run(task_list: list[tasks.Task]) -> None:
    rng = random.Random(config.PILOT_RANDOM_SEED)
    model = config.PILOT_MODELS[0]
    task = task_list[0]
    direction = rng.choice(config.SCALE_DIRECTIONS)
    low_first = rng.choice((True, False))

    print("=" * 78)
    print("DRY RUN — no API calls are made. One context, condition V.")
    print("=" * 78)
    print(f"model                : {model}")
    print(f"task_id              : {task.task_id}")
    print(f"scale_direction      : {direction}")
    print(f"low_vignette_first   : {low_first}")
    print(f"samples per question : {config.N_SAMPLES}")
    print()
    print(
        "Condition V is sampled as "
        f"{config.N_SAMPLES} independent threads; the sequence below is one "
        "thread. Each numbered block is one API call, sending every message "
        "shown in it."
    )
    print()

    def show(label: str, messages: list[dict], is_rating: bool) -> None:
        print("-" * 78)
        print(f"CALL {show.count}  [{label}, is_rating={is_rating}]")
        print("-" * 78)
        for message in messages:
            print(f"  <{message['role']}>")
            for line in message["content"].splitlines():
                print(f"    {line}")
        print()
        show.count += 1

    show.count = 1

    show("code generation", [{"role": "user", "content": _codegen_message(task)}], False)
    print("  -> the reply is the solution, replayed as the assistant turn below.")
    print()

    def respond(label: str, messages: list[dict]) -> str:
        show(label, messages, True)
        return f"<the model's reply to '{label}'>"

    _walk_condition_v(task, DRY_RUN_SOLUTION_STANDIN, direction, low_first, respond)

    planned = _planned_calls(len(task_list))
    print("=" * 78)
    print("PLANNED CALL BUDGET")
    print("=" * 78)
    print(f"calls per (model, task) : {_calls_per_observation()}")
    print(
        f"  1 code generation + {3 * config.N_SAMPLES} condition V "
        f"({config.N_SAMPLES} threads x 3 questions) + "
        f"{config.N_SAMPLES} condition N + {config.N_SAMPLES} P4 probe"
    )
    print(f"tasks                   : {len(task_list)}")
    print(f"models                  : {len(config.PILOT_MODELS)}")
    print(f"planned total calls     : {planned}")
    print(f"config.MAX_CALLS        : {config.MAX_CALLS}")
    print(
        f"headroom                : {config.MAX_CALLS - planned} "
        f"({'WITHIN budget' if planned <= config.MAX_CALLS else 'EXCEEDS BUDGET'})"
    )
    print()
    print("Condition N and the P4 probe are omitted from the transcript above;")
    print("--dry-run shows one condition-V context, as specified.")


# --- Entry point ------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the exact message sequence for one condition-V context and exit",
    )
    args = parser.parse_args()

    task_list = tasks.load_tasks()

    if args.dry_run:
        _dry_run(task_list)
        return 0

    planned = _planned_calls(len(task_list))
    if planned > config.MAX_CALLS:
        print(
            f"Refusing to start: {planned} planned calls exceeds "
            f"config.MAX_CALLS ({config.MAX_CALLS}).",
            file=sys.stderr,
        )
        return 1

    print(f"Starting pilot: {planned} planned calls, MAX_CALLS={config.MAX_CALLS}.")
    rng = random.Random(config.PILOT_RANDOM_SEED)
    observations: list[analyze.Observation] = []

    try:
        for model in config.PILOT_MODELS:
            for task in task_list:
                obs = _run_observation(model, task, rng)
                observations.append(obs)
                _append_observation(obs)
                print(f"  {model} task {task.task_id}: done")
    except elicit.CallBudgetExceeded as exc:
        print(f"\nAborted: {exc}", file=sys.stderr)
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)

    if observations:
        analyze.write_report(observations)
        print(f"\nWrote {config.OUT_DIR / 'report.md'}")

    elicit.print_usage_summary()
    _print_cost_summary()
    return 0


if __name__ == "__main__":
    sys.exit(main())
