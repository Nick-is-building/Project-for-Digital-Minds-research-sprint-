"""Condition R orchestrator (post-hoc, DEVLOG 2026-08-16). REAL API CALLS.

*** THIS IS A DEVIATION FROM THE PREREGISTERED DESIGN. CONDITION R WAS NOT ***
*** IN DESIGN.md. ITS OUTPUT IS POST-HOC, NOT A PREREGISTERED RESULT.      ***

The main run's condition V asks the two vignettes, then the self-question, in
one shared context (DESIGN.md §4) — that turn order is the mechanism King &
Wand rely on, and it is also why `y_v` collapses onto `z_hi` for several
models (see `pilot/out/main_report.md`): by the time the model rates itself,
it has already seen and rated the high anchor in the same context.

Condition R reverses the order: self-question FIRST, then both vignettes.
Everything else is held identical to condition V — wording, the p5 scale
format only, 5 samples at temperature 1.0, the same randomised scale
direction and vignette order per (model, task) via `run_main.context_for`
(unchanged, so this run's presentation is the one the main run's p5 cell
would have drawn), retry/backoff, stop conditions, MAX_CALLS_MAIN
enforcement. Vignette ratings are still elicited fresh inside this context —
THE ONE RULE (CLAUDE.md) applies regardless of turn order.

Solutions are REUSED from the main run (`config.MAIN_SOLUTIONS_PATH`,
read-only) — no code-generation calls are made here. A fresh solution at
temperature 1.0 would be different code than the one condition V/N and the
hidden-test result already describe for that (model, task), which would
break the pairing this condition needs.

Scope: p5 format only, all 5 main-run models, all 60 main-run tasks.

Writes to `pilot/out/condition_r_raw.jsonl` and
`pilot/out/condition_r_observations.jsonl` only. Never opens
`main_raw.jsonl`, `main_observations.jsonl` or `main_report.md` for writing.

Usage:
    python3 run_condition_r.py --dry-run   # one condition-R context, no calls
    python3 run_condition_r.py             # the run itself
"""

import argparse
import sys

import run_main
import run_pilot as pilot
from pilot import analyze, config, elicit, resume, tasks

FMT = config.SCALE_P5


# --- Message construction ----------------------------------------------------


def _walk_condition_r(
    task: tasks.Task,
    solution: str,
    direction: str,
    low_first: bool,
    respond,
    fmt: config.ScaleFormat,
) -> dict[str, str | None]:
    """Walks one condition-R thread: self-question first, then both vignettes.

    Mirror image of `run_pilot._walk_condition_v`. The self-question is asked
    with no vignette in context yet; each vignette is then presented, rated,
    and the reply appended as an assistant turn before the next — vignette
    ratings are still elicited fresh in this context, just after the
    self-report instead of before it.

    `respond` receives `first_rating=True` on the opening self-question only:
    that prompt is byte-identical across all N_SAMPLES threads (same solution,
    nothing model-generated in context yet), so it is the only condition-R
    prompt worth a cache breakpoint. The two vignette turns replay this
    thread's own self-answer and are unique per thread.
    """
    messages = [
        {"role": "user", "content": pilot._codegen_message(task)},
        {"role": "assistant", "content": solution},
    ]
    replies: dict[str, str | None] = {}

    messages.append(
        {"role": "user", "content": pilot._rating_message(fmt, config.QUESTION_SELF, direction)}
    )
    replies["self"] = respond("self", list(messages), True)
    messages.append({"role": "assistant", "content": replies["self"] or ""})

    for which, text in pilot._vignette_order(low_first):
        messages.append(
            {
                "role": "user",
                "content": pilot._rating_message(
                    fmt, config.QUESTION_VIGNETTE, direction, text
                ),
            }
        )
        reply = respond(which, list(messages), False)
        replies[which] = reply
        messages.append({"role": "assistant", "content": reply or ""})

    return replies


# --- Planning -----------------------------------------------------------------


def calls_per_task_r() -> int:
    """One thread is self + two vignettes; no code generation."""
    return 3 * config.N_SAMPLES


def planned_calls_r(n_tasks: int, models: tuple[str, ...] = config.MAIN_MODELS) -> int:
    return calls_per_task_r() * n_tasks * len(models)


def remaining_calls_r(
    task_list: list[tasks.Task],
    done: set[resume.ObservationKey],
    models: tuple[str, ...] = config.MAIN_MODELS,
) -> int:
    return sum(
        calls_per_task_r()
        for model in models
        for task in task_list
        if (model, task.task_id, FMT.name) not in done
    )


# --- Execution ------------------------------------------------------------


def run_condition_r(
    model: str,
    task: tasks.Task,
    solution: str,
    direction: str,
    low_first: bool,
    fmt: config.ScaleFormat,
) -> tuple[dict[str, list[int | None]], dict[str, int]]:
    """`N_SAMPLES` independent threads through one condition-R context.

    Mirror of `run_pilot.run_condition_v`. Returns draws and per-question
    truncation counts, keyed "self"/"low"/"high" — the keys `_walk_condition_r`
    hands `respond`.
    """
    draws: dict[str, list[int | None]] = {"self": [], "low": [], "high": []}
    truncations: dict[str, int] = {"self": 0, "low": 0, "high": 0}
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

        _walk_condition_r(task, solution, direction, low_first, respond, fmt)

        for key in draws:
            result = results[key]
            draws[key].append(elicit.parse_rating_result(result))
            if result.truncated:
                truncations[key] += 1

    return draws, truncations


def observation_for_r(
    record: resume.SolutionRecord,
    task: tasks.Task,
    direction: str,
    low_first: bool,
    draws: dict[str, list[int | None]],
    truncations: dict[str, int],
) -> analyze.Observation:
    return analyze.Observation(
        model=record.model,
        task_id=task.task_id,
        task_set=task.task_set,
        scale_format=FMT.name,
        scale_direction=direction,
        low_vignette_first=low_first,
        y_v_draws=[],
        z_lo_draws=[],
        z_hi_draws=[],
        y_n_draws=[],
        other_draws=[],
        passes_hidden=record.passes_hidden,
        passes_visible=record.passes_visible,
        executes_cleanly=record.executes_cleanly,
        code_extracted=True,
        truncated_draws={
            "y_r": truncations["self"],
            "z_lo_r": truncations["low"],
            "z_hi_r": truncations["high"],
        },
        y_r_draws=draws["self"],
        z_lo_r_draws=draws["low"],
        z_hi_r_draws=draws["high"],
    )


def failed_observation_r(
    model: str, task: tasks.Task, direction: str, low_first: bool, reason: str | None
) -> analyze.Observation:
    """An observation for a (model, task) whose main-run solution had no code."""
    return analyze.Observation(
        model=model,
        task_id=task.task_id,
        task_set=task.task_set,
        scale_format=FMT.name,
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
        y_r_draws=[],
        z_lo_r_draws=[],
        z_hi_r_draws=[],
    )


def run(
    task_list: list[tasks.Task],
    solutions: dict[resume.SolutionKey, resume.SolutionRecord],
    models: tuple[str, ...] = config.MAIN_MODELS,
    observations_path=config.CONDITION_R_OBSERVATIONS_PATH,
) -> list[analyze.Observation]:
    """Runs every outstanding (model, task) cell for condition R, p5 only.

    Solutions are read from the main run's already-persisted solutions and
    are never generated here (see module docstring). An observation is
    appended immediately after its cell finishes, so an interruption loses at
    most the cell in flight — same resumability contract as `run_main.run`.
    """
    done = resume.completed_observation_keys(observations_path)
    observations = resume.load_observations(observations_path)

    if done:
        print(f"Resuming: {len(done)} condition-R observations already on disk.")

    for model in models:
        for task in task_list:
            if (model, task.task_id, FMT.name) in done:
                continue

            direction, low_first = run_main.context_for(model, task.task_id)
            record = solutions.get((model, task.task_id))
            if record is None:
                print(
                    f"  {model} task {task.task_id}: no main-run solution on "
                    f"disk; skipped (condition R reuses solutions, it does "
                    f"not generate them)."
                )
                continue

            if record.solution is None:
                obs = failed_observation_r(
                    model, task, direction, low_first, record.failure_reason
                )
            else:
                draws, truncations = run_condition_r(
                    model, task, record.solution, direction, low_first, FMT
                )
                obs = observation_for_r(
                    record, task, direction, low_first, draws, truncations
                )

            observations.append(obs)
            pilot.append_observation(obs, observations_path)
            done.add(resume.observation_key(obs))
            print(
                f"  {model} task {task.task_id}: done "
                f"({elicit.call_count()} calls so far)"
            )

    return observations


# --- Dry run ----------------------------------------------------------------


def dry_run_condition_r(
    task: tasks.Task,
    fmt: config.ScaleFormat,
    direction: str,
    low_first: bool,
    model: str,
) -> None:
    """Prints one full condition-R context. No API calls. Mirror of
    `run_pilot.dry_run_condition_v`."""
    print("=" * 78)
    print(f"DRY RUN — no API calls. One condition-R context, format `{fmt.name}`.")
    print("=" * 78)
    print(f"model                : {model}")
    print(f"task_id              : {task.task_id}")
    print(
        f"scale_format         : {fmt.name} ({fmt.min_point}-{fmt.max_point}, "
        f"width {fmt.width})"
    )
    print(f"scale_direction      : {direction}")
    print(f"low_vignette_first   : {low_first}")
    print(f"samples per question : {config.N_SAMPLES}")
    print(f"rating token cap     : {config.rating_max_output_tokens(model, fmt)}")
    print()
    print(
        "Condition R is sampled as "
        f"{config.N_SAMPLES} independent threads, mirroring condition V's "
        "sampling; the sequence below is one thread. Turn order is the self "
        "question FIRST, then both vignettes — the reverse of condition V."
    )
    print()
    print(
        "The solution below is REUSED verbatim from the main run's stored "
        "solution for this (model, task) — no code-generation call is made "
        "in condition R."
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

    def respond(label: str, messages: list[dict], first: bool) -> str:
        show(label, messages, True, first)
        return f"<the model's reply to '{label}'>"

    _walk_condition_r(
        task, pilot.DRY_RUN_SOLUTION_STANDIN, direction, low_first, respond, fmt
    )


def _dry_run(task_list: list[tasks.Task]) -> None:
    model = config.MAIN_MODELS[0]
    task = task_list[0]
    direction, low_first = run_main.context_for(model, task.task_id)

    dry_run_condition_r(task, FMT, direction, low_first, model)

    planned = planned_calls_r(len(task_list))
    print("=" * 78)
    print("PLANNED CALL BUDGET (condition R)")
    print("=" * 78)
    print(
        f"calls per (model, task) : {calls_per_task_r()} "
        f"({config.N_SAMPLES} threads x 3 questions: self + 2 vignettes)"
    )
    print(f"tasks                   : {len(task_list)}")
    print(f"models                  : {len(config.MAIN_MODELS)}")
    print(f"planned total calls     : {planned}")
    print(f"config.MAX_CALLS_MAIN   : {config.MAX_CALLS_MAIN}")
    print(
        f"headroom                : {config.MAX_CALLS_MAIN - planned} "
        f"({'WITHIN budget' if planned <= config.MAX_CALLS_MAIN else 'EXCEEDS BUDGET'})"
    )
    print()
    print(
        "No code-generation calls: every (model, task) solution is reused "
        "from config.MAIN_SOLUTIONS_PATH, read-only."
    )


# --- Entry point --------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print one condition-R context and the planned call budget; no API calls",
    )
    args = parser.parse_args()

    task_list = tasks.load_tasks(config.NUM_MBPP_TASKS_MAIN, config.NUM_LBPP_TASKS_MAIN)

    if args.dry_run:
        _dry_run(task_list)
        return 0

    solutions = resume.load_solutions(config.MAIN_SOLUTIONS_PATH)
    if not solutions:
        print(
            f"No solutions found at {config.MAIN_SOLUTIONS_PATH}; condition R "
            "reuses the main run's solutions and cannot generate its own.",
            file=sys.stderr,
        )
        return 1

    elicit.set_call_budget(config.MAX_CALLS_MAIN)
    elicit.set_raw_log_path(config.CONDITION_R_RAW_JSONL_PATH)

    done = resume.completed_observation_keys(config.CONDITION_R_OBSERVATIONS_PATH)
    outstanding = remaining_calls_r(task_list, done)
    if outstanding > config.MAX_CALLS_MAIN:
        print(
            f"Refusing to start: {outstanding} outstanding calls exceeds "
            f"config.MAX_CALLS_MAIN ({config.MAX_CALLS_MAIN}).",
            file=sys.stderr,
        )
        return 1

    print(
        f"Starting condition R: {outstanding} outstanding of "
        f"{planned_calls_r(len(task_list))} planned calls, "
        f"MAX_CALLS_MAIN={config.MAX_CALLS_MAIN}. Writing to "
        f"{config.CONDITION_R_RAW_JSONL_PATH.name}, "
        f"{config.CONDITION_R_OBSERVATIONS_PATH.name}."
    )

    observations: list[analyze.Observation] = []
    try:
        observations = run(task_list, solutions)
    except elicit.CallBudgetExceeded as exc:
        print(f"\nAborted: {exc}", file=sys.stderr)
    except elicit.SustainedRateLimit as exc:
        print(f"\nAborted on sustained 429: {exc}", file=sys.stderr)
    except KeyboardInterrupt:
        print("\nInterrupted. Re-run to resume from the files written so far.", file=sys.stderr)

    if not observations:
        observations = resume.load_observations(config.CONDITION_R_OBSERVATIONS_PATH)

    elicit.print_usage_summary()
    pilot.print_cost_summary()
    print(
        f"\n{len(observations)} condition-R observations on disk at "
        f"{config.CONDITION_R_OBSERVATIONS_PATH}."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
