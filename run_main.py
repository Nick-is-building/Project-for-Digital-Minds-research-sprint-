"""Main-experiment orchestrator: models x 60 tasks x 3 scale formats.

Sequencing and bookkeeping only. Every prompt, every turn order and every
threshold comes from `run_pilot.py` and `pilot.config` unchanged — this file
imports the pilot's own message builders rather than restating them, so the
sequence DEVLOG validated on 2 models x 20 tasks cannot drift from the one the
main run sends.

What is new here, relative to run_pilot.py:

**Scale format is crossed with model and task** (DESIGN.md §3, §10). Each
(model, task) yields three observations, one per format, and all three replay the
*same* solution and the *same* randomised presentation. A difference between
formats is therefore a difference of format alone.

**Randomisation is keyed, not sequential.** `run_pilot.py` draws direction and
vignette order from one `random.Random` walked in loop order. That is fine for a
run that always starts from zero and never varies the format, and wrong for this
one twice over: the draw would differ between the three formats of a pair, and
resuming a run that skips finished work would shift every subsequent draw. Here
each (model, task) has its own generator seeded from
`config.MAIN_RANDOM_SEED`, the model id and the task id, so the draw is a pure
function of the cell.

**Work already done is skipped** (`pilot.resume`). At ~23k calls an interruption
is expected rather than exceptional; see that module for why solutions in
particular must be persisted rather than regenerated.

Usage:
    python run_main.py --dry-run      # one condition-V context per format, no calls
    python run_main.py --estimate     # cost estimate, with and without caching
    python run_main.py --smoke-probe  # one codegen call per model, live
    python run_main.py --smoke        # one model x one task x three formats, live
    python run_main.py                # the run itself
"""

import argparse
import random
import sys
from dataclasses import dataclass

import run_pilot as pilot
from pilot import analyze, config, elicit, extract, resume, sandbox, tasks

# Wherever the estimate needs a stand-in for something a real run would generate.
# The rating filler is a real in-range value so its length is realistic.
_EST_SOLUTION = "x" * config.EST_SOLUTION_CHARS


# --- Keyed randomisation ----------------------------------------------------


def context_for(model: str, task_id: str) -> tuple[str, bool]:
    """The (scale_direction, low_vignette_first) draw for one (model, task).

    A pure function of the cell, so the three scale formats of a pair share one
    presentation and a resumed run reproduces exactly what the interrupted one
    would have drawn. `random.Random` seeds from a string via SHA-512 of its
    bytes, which is stable across processes and unaffected by PYTHONHASHSEED.
    """
    rng = random.Random(f"{config.MAIN_RANDOM_SEED}:{model}:{task_id}")
    return rng.choice(config.SCALE_DIRECTIONS), rng.choice((True, False))


# --- Solutions: generated once per (model, task), reused across formats ------


def solution_record(model: str, task: tasks.Task) -> resume.SolutionRecord:
    """Generates one solution and executes it against the hidden tests.

    Ground truth is computed here, once, and travels with the solution: it is a
    property of that exact code, and recomputing it per format would spend three
    sandbox runs to answer the same question.
    """
    solution, reason = pilot.generate_solution(model, task)
    if solution is None:
        return resume.SolutionRecord(
            model=model,
            task_id=task.task_id,
            solution=None,
            failure_reason=reason,
            passes_hidden=False,
            passes_visible=False,
            executes_cleanly=False,
        )
    return resume.SolutionRecord(
        model=model,
        task_id=task.task_id,
        solution=solution,
        failure_reason=None,
        passes_hidden=sandbox.run_solution(solution, task.hidden_asserts, task.setup_code),
        passes_visible=sandbox.run_solution(solution, [task.visible_assert], task.setup_code),
        executes_cleanly=sandbox.run_solution(solution, [], task.setup_code),
    )


def is_recordable(record: resume.SolutionRecord) -> bool:
    """Whether a failed code generation is a result or an infrastructure blip.

    `extract.NO_REPLY` means the API call itself returned nothing — a timeout, a
    rate limit, a dropped connection. That is not data about the model, so it is
    neither persisted nor written as an observation, and the next run retries it.
    Every other failure reason describes the reply the model actually produced
    (truncated at our ceiling, unclosed fence, no function, unparseable), which
    is a finding: it is persisted, reported in the diagnostics, and not retried.
    """
    return record.solution is not None or record.failure_reason != extract.NO_REPLY


# --- Observations -----------------------------------------------------------


def observation_for(
    record: resume.SolutionRecord,
    task: tasks.Task,
    fmt: config.ScaleFormat,
    direction: str,
    low_first: bool,
    draws: dict[str, list[int | None]],
) -> analyze.Observation:
    return analyze.Observation(
        model=record.model,
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
        passes_hidden=record.passes_hidden,
        passes_visible=record.passes_visible,
        executes_cleanly=record.executes_cleanly,
        code_extracted=True,
    )


# --- Planning ---------------------------------------------------------------


def calls_per_format() -> int:
    """Rating calls for one (model, task, format): condition V, N and the probe."""
    return 3 * config.N_SAMPLES + config.N_SAMPLES + config.N_SAMPLES


def calls_per_task() -> int:
    """One code generation, then every format's ratings off that one solution."""
    return 1 + len(config.MAIN_SCALE_FORMATS) * calls_per_format()


def planned_calls(n_tasks: int, models: tuple[str, ...] = config.MAIN_MODELS) -> int:
    return calls_per_task() * n_tasks * len(models)


def remaining_calls(
    task_list: list[tasks.Task],
    done: set[resume.ObservationKey],
    solutions: dict[resume.SolutionKey, resume.SolutionRecord],
    models: tuple[str, ...] = config.MAIN_MODELS,
) -> int:
    """What is still to be spent, given what the output files already contain."""
    total = 0
    for model in models:
        for task in task_list:
            outstanding = [
                fmt
                for fmt in config.MAIN_SCALE_FORMATS
                if (model, task.task_id, fmt.name) not in done
            ]
            if not outstanding:
                continue
            if (model, task.task_id) not in solutions:
                total += 1
            total += len(outstanding) * calls_per_format()
    return total


# --- The run ----------------------------------------------------------------


def run(
    task_list: list[tasks.Task],
    models: tuple[str, ...] = config.MAIN_MODELS,
    observations_path=config.MAIN_OBSERVATIONS_PATH,
    solutions_path=config.MAIN_SOLUTIONS_PATH,
) -> list[analyze.Observation]:
    """Runs every outstanding (model, task, format) cell, appending as it goes.

    Observations are appended one at a time, before the next cell starts, so an
    interruption loses at most the cell in flight.

    `models` and the two paths are parameters so the smoke test can drive this
    exact function on a narrowed cell set writing to its own files. The real run
    must not be a different code path from the one that was smoke-tested.
    """
    done = resume.completed_observation_keys(observations_path)
    solutions = resume.load_solutions(solutions_path)
    observations = resume.load_observations(observations_path)

    if done or solutions:
        print(
            f"Resuming: {len(done)} observations and {len(solutions)} solutions "
            f"already on disk."
        )

    for model in models:
        for task in task_list:
            outstanding = [
                fmt
                for fmt in config.MAIN_SCALE_FORMATS
                if (model, task.task_id, fmt.name) not in done
            ]
            if not outstanding:
                continue

            direction, low_first = context_for(model, task.task_id)
            record = solutions.get((model, task.task_id))
            if record is None:
                record = solution_record(model, task)
                if not is_recordable(record):
                    print(
                        f"  {model} task {task.task_id}: code generation call "
                        f"failed ({record.failure_reason}); not recorded, will be "
                        f"retried on the next run."
                    )
                    continue
                resume.append_solution(record, solutions_path)
                solutions[record.key] = record

            for fmt in outstanding:
                if record.solution is None:
                    obs = pilot.failed_observation(
                        model, task, fmt, direction, low_first, record.failure_reason
                    )
                else:
                    draws = pilot.run_ratings(
                        model, task, record.solution, direction, low_first, fmt
                    )
                    obs = observation_for(
                        record, task, fmt, direction, low_first, draws
                    )
                observations.append(obs)
                pilot.append_observation(obs, observations_path)
                done.add(resume.observation_key(obs))

            state = "no solution" if record.solution is None else "done"
            print(
                f"  {model} task {task.task_id}: {state} "
                f"({len(outstanding)} format(s), {elicit.call_count()} calls so far)"
            )

    return observations


# --- Cost estimate ----------------------------------------------------------
#
# The estimate enumerates the prompts by driving run_pilot's own message
# builders, so it cannot count a message sequence the run would not send. Token
# counts come from measured chars-per-token (config.CHARS_PER_TOKEN); they are an
# approximation of the providers' tokenisers, not a substitute for them, and the
# per-message framing overhead is absorbed into that ratio because it was
# measured against whole logged prompts.


@dataclass(frozen=True)
class PromptGroup:
    """A prompt shape, how many times it is sent, and whether it is cached.

    Grouping is what makes the caching arithmetic exact: a group of `repeats`
    identical prompts marked for caching costs one cache write plus
    `repeats - 1` cache reads, not `repeats` full-price prompts.
    """

    chars: int
    repeats: int
    cached: bool
    is_codegen: bool = False


def _chars(messages: list[dict]) -> int:
    return sum(len(message["content"]) for message in messages)


def _condition_v_prompts(
    task: tasks.Task, direction: str, low_first: bool, fmt: config.ScaleFormat
) -> list[tuple[int, bool]]:
    """`(prompt chars, cache_prefix)` for the three calls of one condition-V thread.

    `cache_prefix` is the flag `_walk_condition_v` hands its callback — the same
    flag the real run forwards to `elicit` — so the estimate cannot credit
    caching to a call that would not request it.
    """
    prompts: list[tuple[int, bool]] = []

    def respond(_label: str, messages: list[dict], first: bool) -> str:
        prompts.append((_chars(messages), first))
        return str(fmt.max_point)

    pilot._walk_condition_v(task, _EST_SOLUTION, direction, low_first, respond, fmt)
    return prompts


def _prompt_groups(task_list: list[tasks.Task], model: str) -> list[PromptGroup]:
    """Every prompt one model would send over the whole run.

    The three condition-V turns are each sent once per thread, so each becomes a
    group of `N_SAMPLES` repeats. Only the first is byte-identical across threads
    and therefore cacheable; the later two replay each thread's own replies. The
    estimate uses a fixed rating stand-in, so their *sizes* coincide even though
    the real prompts differ — that affects the token count, not the cache flag.
    """
    groups: list[PromptGroup] = []

    for task in task_list:
        direction, low_first = context_for(model, task.task_id)
        groups.append(
            PromptGroup(
                chars=len(pilot._codegen_message(task)),
                repeats=1,
                cached=False,
                is_codegen=True,
            )
        )
        for fmt in config.MAIN_SCALE_FORMATS:
            for size, cached in _condition_v_prompts(task, direction, low_first, fmt):
                groups.append(
                    PromptGroup(chars=size, repeats=config.N_SAMPLES, cached=cached)
                )
            # Condition N and the P4 probe send one identical prompt N_SAMPLES
            # times, so run_ratings marks both cache_prefix=True.
            groups.append(
                PromptGroup(
                    chars=_chars(
                        pilot._condition_n_messages(task, _EST_SOLUTION, direction, fmt)
                    ),
                    repeats=config.N_SAMPLES,
                    cached=True,
                )
            )
            groups.append(
                PromptGroup(
                    chars=_chars(pilot._p4_messages(task, _EST_SOLUTION, direction, fmt)),
                    repeats=config.N_SAMPLES,
                    cached=True,
                )
            )

    return groups


def _billable_input_tokens(
    groups: list[PromptGroup],
    chars_per_token: float,
    cache_min: int,
    multipliers: dict[str, float] | None,
) -> float:
    """Input tokens weighted by what each actually costs, in base-input units.

    Multiply by the base input price to get the input bill. A cached group of
    `n` prompts of `T` tokens costs `1.25*T + 0.1*(n-1)*T` instead of `n*T`; a
    group below the model's minimum, or on a provider with no published
    multiplier, costs the full `n*T`.
    """
    total = 0.0
    for group in groups:
        prompt_tokens = group.chars / chars_per_token
        if (
            group.cached
            and multipliers is not None
            and prompt_tokens >= cache_min
            and group.repeats > 1
        ):
            total += prompt_tokens * multipliers["write"]
            total += prompt_tokens * multipliers["read"] * (group.repeats - 1)
        else:
            total += prompt_tokens * group.repeats
    return total


def _model_estimate(task_list: list[tasks.Task], model: str) -> dict[str, object]:
    provider = config.PROVIDER[model]
    chars_per_token = config.CHARS_PER_TOKEN[provider]
    cache_min = config.CACHE_MIN_PROMPT_TOKENS[model]
    multipliers = config.CACHE_MULTIPLIERS[provider]
    groups = _prompt_groups(task_list, model)

    calls = sum(g.repeats for g in groups)
    codegen_calls = sum(g.repeats for g in groups if g.is_codegen)
    input_tokens = round(sum(g.chars * g.repeats for g in groups) / chars_per_token)
    output_tokens = (
        codegen_calls * config.EST_CODEGEN_OUTPUT_TOKENS[provider]
        + (calls - codegen_calls) * config.EST_RATING_OUTPUT_TOKENS[provider]
    )

    cached_sizes = [g.chars for g in groups if g.cached]
    max_cached_prompt_tokens = round(max(cached_sizes) / chars_per_token)

    prices = config.PRICE_PER_MTOK_USD.get(model, {})
    price_in, price_out = prices.get("input"), prices.get("output")
    if price_in is None or price_out is None:
        cost = cost_cached = None
    else:
        billable = _billable_input_tokens(
            groups, chars_per_token, cache_min, multipliers
        )
        cost = input_tokens / 1e6 * price_in + output_tokens / 1e6 * price_out
        cost_cached = billable / 1e6 * price_in + output_tokens / 1e6 * price_out

    return {
        "model": model,
        "provider": provider,
        "calls": calls,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "max_prompt_tokens": round(max(g.chars for g in groups) / chars_per_token),
        "max_cached_prompt_tokens": max_cached_prompt_tokens,
        "cache_min_tokens": cache_min,
        "cacheable": multipliers is not None and max_cached_prompt_tokens >= cache_min,
        "cost": cost,
        "cost_cached": cost_cached,
    }


def _print_estimate_table(rows: list[dict[str, object]]) -> tuple[float, float]:
    print(
        f"{'model':<28} {'calls':>7} {'in tok':>10} {'out tok':>9} "
        f"{'no cache':>10} {'w/ cache':>10}"
    )
    plain = cached = 0.0
    for row in rows:
        if row["cost"] is None:
            shown, shown_cached = "unpriced", "unpriced"
        else:
            plain += row["cost"]
            cached += row["cost_cached"]
            shown = f"{row['cost']:.2f}"
            shown_cached = f"{row['cost_cached']:.2f}"
        print(
            f"{row['model']:<28} {row['calls']:>7} {row['input_tokens']:>10} "
            f"{row['output_tokens']:>9} {shown:>10} {shown_cached:>10}"
        )
    return plain, cached


def estimate(task_list: list[tasks.Task]) -> None:
    print("=" * 78)
    print("COST ESTIMATE — no API calls made")
    print("=" * 78)
    print(
        f"{len(config.MAIN_MODELS)} models x {len(task_list)} tasks x "
        f"{len(config.MAIN_SCALE_FORMATS)} formats "
        f"({', '.join(f.name for f in config.MAIN_SCALE_FORMATS)})"
    )
    print(
        f"calls per (model, task): {calls_per_task()} "
        f"= 1 codegen + {len(config.MAIN_SCALE_FORMATS)} x {calls_per_format()} "
        f"({3 * config.N_SAMPLES} condition V + {config.N_SAMPLES} condition N + "
        f"{config.N_SAMPLES} P4 probe)"
    )
    planned = planned_calls(len(task_list))
    print(f"planned total calls    : {planned}")
    print(f"config.MAX_CALLS_MAIN  : {config.MAX_CALLS_MAIN}")
    print()
    print(
        "Token counts are chars / measured chars-per-token "
        f"({config.CHARS_PER_TOKEN}), with the solution stood in for by "
        f"{config.EST_SOLUTION_CHARS} characters (the logged mean). Output is "
        f"{config.EST_CODEGEN_OUTPUT_TOKENS} per codegen call and "
        f"{config.EST_RATING_OUTPUT_TOKENS} per rating call, thinking included."
    )
    print(
        "The Google codegen figure was measured under the old 1020-token ceiling "
        "with half the calls censored at it, so every Gemini number below is a "
        "LOWER BOUND (config.EST_CODEGEN_OUTPUT_TOKENS)."
    )
    print()

    rows = [_model_estimate(task_list, model) for model in config.MAIN_MODELS]
    print(f"--- Configured models ({len(config.MAIN_MODELS)}) ---")
    plain, cached = _print_estimate_table(rows)
    print(
        f"{'TOTAL (priced models)':<28} {'':>7} {'':>10} {'':>9} "
        f"{plain:>10.2f} {cached:>10.2f}"
    )
    print()

    print("--- Prompt caching ---")
    print(
        "A cache breakpoint is only set where a prefix is genuinely reused: the "
        "opening condition-V vignette question (identical across all "
        f"{config.N_SAMPLES} threads), condition N, and the P4 probe. The later "
        "condition-V turns replay each thread's own replies and are unique per "
        "thread, so caching them would pay the write premium and never read it "
        "back. The deciding figure is therefore the largest CACHED prompt, not "
        "the largest prompt."
    )
    print()
    for row in rows:
        print(
            f"{row['model']:<28} largest cached prompt "
            f"{row['max_cached_prompt_tokens']:>5} tok (largest overall "
            f"{row['max_prompt_tokens']:>5}) vs {row['cache_min_tokens']:>5} tok "
            f"minimum -> "
            f"{'CACHEABLE' if row['cacheable'] else 'below minimum, never cached'}"
        )
    print()
    print(
        f"Multipliers applied: {config.CACHE_MULTIPLIERS[config.ANTHROPIC]} x the "
        "base input price (Anthropic, verified 2026-08-15, 5-minute TTL). Google "
        "publishes no multiplier for implicit caching, so no Google saving is "
        "claimed — moot here, since no Gemini prompt reaches 4,096 tokens."
    )
    print(
        "The 'w/ cache' column charges each cacheable group one write at 1.25x "
        f"plus {config.N_SAMPLES - 1} reads at 0.1x, instead of "
        f"{config.N_SAMPLES} full-price prompts."
    )
    print()
    if not any(row["cacheable"] for row in rows):
        print(
            "As configured, nothing is cacheable: the two columns are identical. "
            "The breakpoints are still requested, because a below-minimum prompt "
            "is processed uncached with no error and no write premium, so asking "
            "costs nothing and the saving appears by itself if prompts grow."
        )
        print()
    print(
        "Excluded from these figures: retries, and the codegen calls that return "
        "no reply at all and are retried on the next run."
    )


# --- Dry run ----------------------------------------------------------------


def dry_run(task_list: list[tasks.Task]) -> None:
    """One full condition-V context per scale format, on the same task."""
    model = config.MAIN_MODELS[0]
    task = task_list[0]
    direction, low_first = context_for(model, task.task_id)

    for fmt in config.MAIN_SCALE_FORMATS:
        pilot.dry_run_condition_v(task, fmt, direction, low_first, model)
        print()

    print("=" * 78)
    print("WHAT IS THE SAME ACROSS THE THREE CONTEXTS ABOVE")
    print("=" * 78)
    print(f"model                : {model}")
    print(f"task                 : {task.task_id} ({task.task_set})")
    print(f"scale_direction      : {direction}")
    print(f"low_vignette_first   : {low_first}")
    print("solution             : generated once, replayed verbatim into all three")
    print()
    print("Only the scale block and the answer instruction differ. That is what")
    print("makes a between-format difference attributable to format (DESIGN.md §10).")
    print()
    print(
        f"Not shown: condition N and the P4 probe ({2 * config.N_SAMPLES} calls "
        f"per format), and the other {len(task_list) - 1} tasks."
    )


# --- Smoke test --------------------------------------------------------------
#
# Two commands, both hitting the live APIs on one LBPP task:
#
#   --smoke        one model, that task, all three formats, through run() itself.
#                  Run it, kill it mid-way, run it again: the second invocation
#                  must reuse the persisted solution and skip finished formats.
#   --smoke-probe  one code-generation call to each of the five configured
#                  models. Cheap proof that every model string resolves and
#                  answers, and that a real LBPP codegen call fits inside the
#                  raised 4096-token ceiling — the one that was 1020 and was
#                  silently truncating Gemini.


def smoke_task() -> tasks.Task:
    """One LBPP task: the harder half, where the old ceiling actually bit."""
    return tasks.load_tasks(0, 1)[0]


def smoke(task: tasks.Task, model: str = config.SMOKE_MODEL) -> None:
    elicit.set_raw_log_path(config.SMOKE_RAW_JSONL_PATH)
    direction, low_first = context_for(model, task.task_id)
    print(
        f"Smoke: {model} on {task.task_set} task {task.task_id}, "
        f"{direction}, low_vignette_first={low_first}, "
        f"{len(config.MAIN_SCALE_FORMATS)} formats, "
        f"{calls_per_task()} calls if nothing is already done."
    )

    run(
        [task],
        models=(model,),
        observations_path=config.SMOKE_OBSERVATIONS_PATH,
        solutions_path=config.SMOKE_SOLUTIONS_PATH,
    )

    done = resume.completed_observation_keys(config.SMOKE_OBSERVATIONS_PATH)
    print(f"\nFormats complete: {sorted(key[2] for key in done)}")
    elicit.print_usage_summary()
    pilot.print_cost_summary()


def smoke_probe(task: tasks.Task) -> None:
    elicit.set_raw_log_path(config.SMOKE_RAW_JSONL_PATH)
    print(
        f"Probing {len(config.MAIN_MODELS)} models with one codegen call each on "
        f"{task.task_set} task {task.task_id}, ceiling "
        f"{config.MAX_OUTPUT_TOKENS_CODEGEN} tokens.\n"
    )
    for model in config.MAIN_MODELS:
        result = elicit.elicit_call(
            model,
            [{"role": "user", "content": pilot._codegen_message(task)}],
            config.MAX_OUTPUT_TOKENS_CODEGEN,
        )
        code, reason = extract.extract_code(result.text, truncated=result.truncated)
        spent = (result.output_tokens or 0) + (result.thought_tokens or 0)
        print(
            f"{model:<28} {spent:>5} of {config.MAX_OUTPUT_TOKENS_CODEGEN} tokens "
            f"({result.output_tokens} out + {result.thought_tokens} thought), "
            f"truncated={result.truncated}, "
            f"extracted={'yes' if code else f'NO ({reason})'}"
        )
    print()
    elicit.print_usage_summary()
    pilot.print_cost_summary()


# --- Entry point ------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--dry-run",
        action="store_true",
        help="print one condition-V context per scale format and exit",
    )
    group.add_argument(
        "--estimate",
        action="store_true",
        help="print the projected cost of the full run and exit",
    )
    group.add_argument(
        "--smoke",
        action="store_true",
        help="one model, one task, three formats, into the smoke output files",
    )
    group.add_argument(
        "--smoke-probe",
        action="store_true",
        help="one code-generation call to each configured model, and exit",
    )
    parser.add_argument(
        "--smoke-model",
        default=config.SMOKE_MODEL,
        choices=config.MAIN_MODELS,
        help="which model --smoke drives (default: %(default)s)",
    )
    args = parser.parse_args()

    if args.smoke or args.smoke_probe:
        elicit.set_call_budget(calls_per_task() * len(config.MAIN_MODELS))
        task = smoke_task()
        smoke(task, args.smoke_model) if args.smoke else smoke_probe(task)
        return 0

    task_list = tasks.load_tasks(
        config.NUM_MBPP_TASKS_MAIN, config.NUM_LBPP_TASKS_MAIN
    )

    if args.dry_run:
        dry_run(task_list)
        return 0
    if args.estimate:
        estimate(task_list)
        return 0

    elicit.set_call_budget(config.MAX_CALLS_MAIN)
    elicit.set_raw_log_path(config.MAIN_RAW_JSONL_PATH)

    done = resume.completed_observation_keys(config.MAIN_OBSERVATIONS_PATH)
    solutions = resume.load_solutions(config.MAIN_SOLUTIONS_PATH)
    outstanding = remaining_calls(task_list, done, solutions)
    if outstanding > config.MAX_CALLS_MAIN:
        print(
            f"Refusing to start: {outstanding} outstanding calls exceeds "
            f"config.MAX_CALLS_MAIN ({config.MAX_CALLS_MAIN}).",
            file=sys.stderr,
        )
        return 1

    print(
        f"Starting main run: {outstanding} outstanding of "
        f"{planned_calls(len(task_list))} planned calls, "
        f"MAX_CALLS_MAIN={config.MAX_CALLS_MAIN}. Writing to "
        f"{config.MAIN_RAW_JSONL_PATH.name}, "
        f"{config.MAIN_SOLUTIONS_PATH.name}, "
        f"{config.MAIN_OBSERVATIONS_PATH.name}."
    )

    observations: list[analyze.Observation] = []
    try:
        observations = run(task_list)
    except elicit.CallBudgetExceeded as exc:
        print(f"\nAborted: {exc}", file=sys.stderr)
    except KeyboardInterrupt:
        print("\nInterrupted. Re-run to resume from the files written so far.", file=sys.stderr)

    if not observations:
        observations = resume.load_observations(config.MAIN_OBSERVATIONS_PATH)
    if observations:
        analyze.write_report(observations, config.MAIN_REPORT_PATH)
        print(f"\nWrote {config.MAIN_REPORT_PATH}")

    elicit.print_usage_summary()
    pilot.print_cost_summary()
    return 0


if __name__ == "__main__":
    sys.exit(main())
