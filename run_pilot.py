"""Despite the filename, this is not a pilot-phase script.

This module is the shared turn-sequencing library for the whole project: every
script that elicits ratings from a model imports it — `run_main.py` and
`run_condition_r.py` (the runners behind the reported results),
`monitor_run.py` (the run watchdog), and `pilot/tests/test_resume.py`. Its own
standalone pilot-orchestration entry point below (`python run_pilot.py`, 2
models x 20 tasks) is superseded by `run_main.py`; the message-building
functions it calls are not — they are the single source of truth for turn
order, reused unchanged by every later run. The name is a historical accident
of what got built first, not a description of current scope. See
`CLAUDE.md`'s Open Questions for why it has not been renamed.

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
import sys

from pilot import analyze, config, elicit, extract, sandbox, tasks

DRY_RUN_SOLUTION_STANDIN = (
    "<the model's generated solution would be replayed here verbatim; "
    "no API call was made>"
)


# --- Message construction (DESIGN.md §3, §4) --------------------------------
#
# Every function here takes the ScaleFormat explicitly. It used to read a
# module-level config.SCALE_POINTS, which meant the only way to run a second
# format was to monkeypatch the config — the mechanism by which the 0-100
# control run's analysis silently kept 5-point bounds.


def _scale_block(fmt: config.ScaleFormat, direction: str) -> str:
    points = sorted(fmt.labels)
    if direction == config.SCALE_DESCENDING:
        points = list(reversed(points))
    return "\n".join(f"{p} = {fmt.labels[p]}" for p in points)


def _rating_message(
    fmt: config.ScaleFormat, question: str, direction: str, body: str | None = None
) -> str:
    parts = [body] if body else []
    parts += [question, _scale_block(fmt, direction), fmt.answer_instruction]
    return "\n\n".join(parts)


def _codegen_message(task: tasks.Task) -> str:
    return (
        f"{task.prompt}\n\n"
        f"Your solution must satisfy:\n{task.visible_assert}\n\n"
        "Reply with a single Python function and no explanation."
    )


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
    fmt: config.ScaleFormat,
) -> dict[str, str | None]:
    """Walks one condition-V thread, calling `respond(label, messages, first)` per call.

    The single source of truth for the DESIGN.md §4 turn order: the real run and
    --dry-run both drive this, differing only in what `respond` does, so the
    printed sequence cannot drift from the sent one. Each vignette is presented,
    rated, and the reply appended as an assistant turn before the next question,
    which is what puts the model's own anchor ratings in context when it rates
    itself.

    `respond` receives `first_rating=True` on the opening vignette question only.
    That call's prompt is byte-identical across all N_SAMPLES threads (nothing
    model-generated has entered the context yet beyond the solution, which is
    shared), so it is the only condition-V prompt worth a cache breakpoint. The
    later turns replay each thread's own replies and are unique per thread —
    caching those would pay the write premium and never read it back.
    """
    messages = [
        {"role": "user", "content": _codegen_message(task)},
        {"role": "assistant", "content": solution},
    ]
    replies: dict[str, str | None] = {}

    for index, (which, text) in enumerate(_vignette_order(low_first)):
        messages.append(
            {
                "role": "user",
                "content": _rating_message(
                    fmt, config.QUESTION_VIGNETTE, direction, text
                ),
            }
        )
        reply = respond(which, list(messages), index == 0)
        replies[which] = reply
        messages.append({"role": "assistant", "content": reply or ""})

    messages.append(
        {"role": "user", "content": _rating_message(fmt, config.QUESTION_SELF, direction)}
    )
    replies["self"] = respond("self", list(messages), False)
    return replies


def _condition_n_messages(
    task: tasks.Task, solution: str, direction: str, fmt: config.ScaleFormat
) -> list[dict]:
    return [
        {"role": "user", "content": _codegen_message(task)},
        {"role": "assistant", "content": solution},
        {"role": "user", "content": _rating_message(fmt, config.QUESTION_SELF, direction)},
    ]


def _p4_messages(
    task: tasks.Task, solution: str, direction: str, fmt: config.ScaleFormat
) -> list[dict]:
    """Fresh context, no assistant turn: authorship is what the probe removes."""
    neutral = (
        f"{task.prompt}\n\n"
        f"The following solution has been submitted for review.\n\n{solution}"
    )
    return [
        {
            "role": "user",
            "content": _rating_message(fmt, config.QUESTION_OTHER, direction, neutral),
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


def generate_solution(model: str, task: tasks.Task) -> tuple[str | None, str | None]:
    """One code-generation call. Returns `(solution, failure_reason)`.

    The failure reason comes from pilot.extract and distinguishes our own output
    ceiling cutting the reply off from the model emitting something unusable —
    a distinction the pilot did not make, which is why a token-budget bug read
    as an 80% LBPP failure rate on Gemini.
    """
    result = elicit.elicit_call(
        model,
        [{"role": "user", "content": _codegen_message(task)}],
        config.MAX_OUTPUT_TOKENS_CODEGEN,
        is_rating=False,
    )
    return extract.extract_code(result.text, result.truncated)


def run_condition_v(
    model: str,
    task: tasks.Task,
    solution: str,
    direction: str,
    low_first: bool,
    fmt: config.ScaleFormat,
) -> tuple[dict[str, list[int | None]], dict[str, int]]:
    """`N_SAMPLES` independent threads through the same condition-V context.

    Returns the draws and, per question, how many of them were discarded for
    truncation. `_walk_condition_v` hands `respond` the question label, so the
    results are keyed by the same strings the draws are — deriving them from
    call order instead would reintroduce the index arithmetic that produced the
    original condition-V ordering bug.
    """
    draws: dict[str, list[int | None]] = {"low": [], "high": [], "self": []}
    truncations: dict[str, int] = {"low": 0, "high": 0, "self": 0}
    cap = config.rating_max_output_tokens(model, fmt)

    for sample_index in range(config.N_SAMPLES):
        results: dict[str, elicit.CallResult] = {}

        def respond(which, messages, first, _results=results, _i=sample_index):
            result = elicit.elicit_call(
                model,
                messages,
                cap,
                is_rating=True,
                sample_index=_i,
                cache_prefix=first,
            )
            _results[which] = result
            return result.text

        _walk_condition_v(task, solution, direction, low_first, respond, fmt)

        for key in draws:
            result = results[key]
            draws[key].append(elicit.parse_rating_result(result))
            if result.truncated:
                truncations[key] += 1

    return draws, truncations


def run_ratings(
    model: str,
    task: tasks.Task,
    solution: str,
    direction: str,
    low_first: bool,
    fmt: config.ScaleFormat,
) -> tuple[dict[str, list[int | None]], dict[str, int]]:
    """Condition V, condition N and the P4 probe for one (solution, format).

    Returns `(draws, truncations)`, both keyed by question. Condition N and the
    P4 probe send an identical prompt N_SAMPLES times, so both carry a cache
    breakpoint: one write, four reads.
    """
    v_draws, v_truncations = run_condition_v(
        model, task, solution, direction, low_first, fmt
    )
    cap = config.rating_max_output_tokens(model, fmt)

    y_n, y_n_truncated = elicit.elicit(
        model,
        _condition_n_messages(task, solution, direction, fmt),
        config.N_SAMPLES,
        cap,
        is_rating=True,
        cache_prefix=True,
    )
    other, other_truncated = elicit.elicit(
        model,
        _p4_messages(task, solution, direction, fmt),
        config.N_SAMPLES,
        cap,
        is_rating=True,
        cache_prefix=True,
    )

    draws = {
        "y_v": v_draws["self"],
        "z_lo": v_draws["low"],
        "z_hi": v_draws["high"],
        "y_n": y_n,
        "other": other,
    }
    truncations = {
        "y_v": v_truncations["self"],
        "z_lo": v_truncations["low"],
        "z_hi": v_truncations["high"],
        "y_n": y_n_truncated,
        "other": other_truncated,
    }
    return draws, truncations


def failed_observation(
    model: str,
    task: tasks.Task,
    fmt: config.ScaleFormat,
    direction: str,
    low_first: bool,
    reason: str | None,
) -> analyze.Observation:
    """An observation for a (model, task) whose solution could not be extracted."""
    return analyze.Observation(
        model=model,
        task_id=task.task_id,
        task_set=task.task_set,
        scale_format=fmt.name,
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
        codegen_failure_reason=reason,
        truncated_draws={},
    )


def _run_observation(
    model: str, task: tasks.Task, rng: random.Random, fmt: config.ScaleFormat
) -> analyze.Observation:
    direction = rng.choice(config.SCALE_DIRECTIONS)
    low_first = rng.choice((True, False))

    solution, reason = generate_solution(model, task)
    if solution is None:
        return failed_observation(model, task, fmt, direction, low_first, reason)

    draws, truncations = run_ratings(model, task, solution, direction, low_first, fmt)

    return analyze.Observation(
        model=model,
        task_id=task.task_id,
        task_set=task.task_set,
        scale_format=fmt.name,
        scale_direction=direction,
        low_vignette_first=low_first,
        y_v_draws=draws["y_v"],
        z_lo_draws=draws["z_lo"],
        z_hi_draws=draws["z_hi"],
        y_n_draws=draws["y_n"],
        other_draws=draws["other"],
        passes_hidden=sandbox.run_solution(solution, task.hidden_asserts, task.setup_code),
        passes_visible=sandbox.run_solution(solution, [task.visible_assert], task.setup_code),
        executes_cleanly=sandbox.run_solution(solution, [], task.setup_code),
        code_extracted=True,
        truncated_draws=truncations,
    )


def append_observation(obs: analyze.Observation, path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(dataclasses.asdict(obs)) + "\n")


# --- Reporting --------------------------------------------------------------


def cost_of(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cached_tokens: int = 0,
    written_tokens: int = 0,
) -> float | None:
    """USD for one model's token totals, or None if it has no configured price.

    `output_tokens` must already include Gemini thought tokens: the provider
    bills thinking as output, so excluding them understates spend.

    The three input quantities are disjoint and priced differently. Anthropic's
    `input_tokens` counts only uncached tokens — cache reads and cache writes are
    reported in their own fields and must be added, or a cached run looks cheaper
    than it was. `cached_tokens` (reads) use the configured cache-read price, or
    the full input price where none is published, which over- rather than
    under-states. `written_tokens` are charged the write multiplier.
    """
    prices = config.PRICE_PER_MTOK_USD.get(model, {})
    price_in, price_out = prices.get("input"), prices.get("output")
    if price_in is None or price_out is None:
        return None
    price_cached = prices.get("cache_read")
    if price_cached is None:
        price_cached = price_in
    multipliers = config.CACHE_MULTIPLIERS.get(config.PROVIDER.get(model, ""))
    write_multiplier = multipliers["write"] if multipliers else 1.0
    return (
        input_tokens / 1e6 * price_in
        + output_tokens / 1e6 * price_out
        + cached_tokens / 1e6 * price_cached
        + written_tokens / 1e6 * price_in * write_multiplier
    )


def print_cost_summary() -> None:
    """Actual spend, read back off the raw log."""
    path = elicit.raw_log_path()
    if not path.exists():
        print(f"No {path.name} found; no cost to report.")
        return

    totals: dict[str, dict[str, int]] = {}
    with open(path) as f:
        for line in f:
            record = json.loads(line)
            t = totals.setdefault(
                record["model"], {"input": 0, "output": 0, "cached": 0, "written": 0}
            )
            t["input"] += record.get("input_tokens") or 0
            # Gemini bills thought tokens as output tokens.
            t["output"] += (record.get("output_tokens") or 0) + (
                record.get("thought_tokens") or 0
            )
            t["cached"] += record.get("cached_input_tokens") or 0
            t["written"] += record.get("cache_creation_tokens") or 0

    print("--- Cost summary ---")
    known_total = 0.0
    for model, tokens in totals.items():
        cost = cost_of(
            model,
            tokens["input"],
            tokens["output"],
            tokens["cached"],
            tokens["written"],
        )
        counts = (
            f"{tokens['input']} in / {tokens['output']} out incl. thinking / "
            f"{tokens['cached']} cache read / {tokens['written']} cache write"
        )
        if cost is None:
            print(
                f"{model}: no price configured — set "
                f"config.PRICE_PER_MTOK_USD[{model!r}] from the provider's "
                f"pricing page. Tokens: {counts}."
            )
            continue
        known_total += cost
        print(f"{model}: ${cost:.4f}  ({counts})")
    print(f"Total across models with a configured price: ${known_total:.4f}")


# --- Dry run ----------------------------------------------------------------


def dry_run_condition_v(
    task: tasks.Task,
    fmt: config.ScaleFormat,
    direction: str,
    low_first: bool,
    model: str,
) -> None:
    """Prints one full condition-V context for one scale format. No API calls."""
    print("=" * 78)
    print(f"DRY RUN — no API calls. One condition-V context, format `{fmt.name}`.")
    print("=" * 78)
    print(f"model                : {model}")
    print(f"task_id              : {task.task_id}")
    print(f"scale_format         : {fmt.name} ({fmt.min_point}-{fmt.max_point}, width {fmt.width})")
    print(f"scale_direction      : {direction}")
    print(f"low_vignette_first   : {low_first}")
    print(f"samples per question : {config.N_SAMPLES}")
    print(f"rating token cap     : {config.rating_max_output_tokens(model, fmt)}")
    print(
        f"thresholds           : P1 SD >= {fmt.p1_min_sd:g}, "
        f"P3 >= {fmt.p3_min_difference:g}, P4 <= {fmt.p4_max_abs_gap:g}, "
        f"tolerance {fmt.tolerance:g}"
    )
    print()
    print(
        "Condition V is sampled as "
        f"{config.N_SAMPLES} independent threads; the sequence below is one "
        "thread. Each numbered block is one API call, sending every message "
        "shown in it."
    )
    print()

    def show(label: str, messages: list[dict], is_rating: bool, cached: bool) -> None:
        print("-" * 78)
        print(
            f"CALL {show.count}  [{label}, is_rating={is_rating}, "
            f"cache_prefix={cached}]"
        )
        print("-" * 78)
        for message in messages:
            print(f"  <{message['role']}>")
            for line in message["content"].splitlines():
                print(f"    {line}")
        print()
        show.count += 1

    show.count = 1

    show(
        "code generation",
        [{"role": "user", "content": _codegen_message(task)}],
        False,
        False,
    )
    print("  -> the reply is the solution, replayed as the assistant turn below.")
    print("  -> the SAME solution is replayed into all three scale formats, so")
    print("     format cannot be confounded with solution quality (DESIGN.md §10).")
    print()

    def respond(label: str, messages: list[dict], first: bool) -> str:
        show(label, messages, True, first)
        return f"<the model's reply to '{label}'>"

    _walk_condition_v(task, DRY_RUN_SOLUTION_STANDIN, direction, low_first, respond, fmt)


def _dry_run(task_list: list[tasks.Task]) -> None:
    rng = random.Random(config.PILOT_RANDOM_SEED)
    model = config.PILOT_MODELS[0]
    task = task_list[0]
    direction = rng.choice(config.SCALE_DIRECTIONS)
    low_first = rng.choice((True, False))

    dry_run_condition_v(task, config.SCALE_P5, direction, low_first, model)

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
                obs = _run_observation(model, task, rng, config.SCALE_P5)
                observations.append(obs)
                append_observation(obs, config.OUT_DIR / "observations.jsonl")
                print(f"  {model} task {task.task_id}: done")
    except elicit.CallBudgetExceeded as exc:
        print(f"\nAborted: {exc}", file=sys.stderr)
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)

    if observations:
        analyze.write_report(observations)
        print(f"\nWrote {config.OUT_DIR / 'report.md'}")

    elicit.print_usage_summary()
    print_cost_summary()
    return 0


if __name__ == "__main__":
    sys.exit(main())
