"""Pre-run checks for the two code paths the smoke test did not reach.

Both are named in DEVLOG.md's Open Questions as of 2026-08-15 05:20:

  CHECK 1  `elicit.py`'s Gemini path has never been sent more than one message.
           It builds a thread from explicit `user_input`/`model_output` steps —
           stateless replay rather than `previous_interaction_id` chaining — and
           if that step encoding is wrong it is wrong on every Gemini cell.

  CHECK 2  claude-sonnet-5, gemini-3.6-flash and gemini-3.1-pro-preview have
           each made a single code-generation call and have never run a rating
           block, in any scale format.

Both drive `run_pilot`'s own message builders and `elicit`, not a copy, so what
is printed is what the main run would send. Each check writes its own raw log
under `pilot/out/`, so an interrupted check cannot make the real run skip a cell.

Usage:
    python3 -u check_untested_paths.py --check1
    python3 -u check_untested_paths.py --check2
"""

import argparse
import json
import sys

import run_main
import run_pilot as pilot
from pilot import config, elicit, tasks

CHECK1_RAW_PATH = config.OUT_DIR / "check1_gemini_thread_raw.jsonl"
CHECK2_RAW_PATH = config.OUT_DIR / "check2_rating_blocks_raw.jsonl"

CHECK2_MODELS = ("claude-sonnet-5", "gemini-3.6-flash", "gemini-3.1-pro-preview")

# A hand-written stand-in, not model output. CHECK 2 is about the rating block,
# and the user's budget for it is nine calls with no code generation. Holding the
# rated code fixed also means the only things varying across the nine cells are
# the model and the scale format.
STANDIN_SOLUTION = '''def remove_Occ(s, ch):
    first = s.find(ch)
    if first == -1:
        return s
    s = s[:first] + s[first + 1:]
    last = s.rfind(ch)
    if last == -1:
        return s
    return s[:last] + s[last + 1:]'''


def _rule(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def _dump_messages(messages: list[dict]) -> None:
    for i, message in enumerate(messages):
        print(f"  [{i}] role={message['role']}")
        for line in message["content"].split("\n"):
            print(f"      | {line}")


def _dump_raw_log(path) -> None:
    """Prints every call from the raw log: what was sent, and what came back.

    The raw log is the record of what actually went over the wire — it is written
    inside `elicit.elicit_call` before any parsing — so printing it, rather than
    printing the caller's idea of the messages, is what makes this a check.
    """
    with open(path) as f:
        records = [json.loads(line) for line in f]

    for n, record in enumerate(records, start=1):
        _rule(f"CALL {n} of {len(records)}  —  {record['model']}  "
              f"(is_rating={record['is_rating']}, "
              f"max_output_tokens={record['max_output_tokens']})")
        print("MESSAGE SEQUENCE SENT (all turns):")
        _dump_messages(record["messages"])
        print()
        print("RAW RESPONSE:")
        print(f"  {record['raw_response']!r}")
        print()
        print(f"  error         : {record['error']}")
        print(f"  stop_reason   : {record['stop_reason']}")
        print(f"  truncated     : {record['truncated']}")
        print(f"  tokens        : in={record['input_tokens']} "
              f"out={record['output_tokens']} thought={record['thought_tokens']}")
        if record["is_rating"]:
            print(f"  PARSED VALUE  : {elicit.parse_rating(record['raw_response'])!r}")


def check1() -> int:
    """One condition-V context for gemini-3.6-flash on a single task: 4 calls."""
    model = config.GOOGLE_MODEL
    fmt = config.SCALE_P5
    task = tasks.load_tasks(1, 0)[0]
    # The real run's draw for this cell, not a fresh one, so this is literally
    # the context run_main would build for (this model, this task).
    direction, low_first = run_main.context_for(model, task.task_id)

    elicit.set_raw_log_path(CHECK1_RAW_PATH)
    if CHECK1_RAW_PATH.exists():
        CHECK1_RAW_PATH.unlink()

    _rule("CHECK 1 — Gemini condition-V thread")
    print(f"model            : {model}")
    print(f"task             : {task.task_id} ({task.task_set})")
    print(f"scale format     : {fmt.name}")
    print(f"scale_direction  : {direction}   (keyed draw, run_main.context_for)")
    print(f"low_vignette_first: {low_first}  (keyed draw, run_main.context_for)")
    print(f"raw log          : {CHECK1_RAW_PATH}")

    solution, reason = pilot.generate_solution(model, task)
    if solution is None:
        print(f"\nCode generation failed: {reason}. Stopping — no thread to walk.")
        _dump_raw_log(CHECK1_RAW_PATH)
        return 1

    replies = pilot._walk_condition_v(
        task,
        solution,
        direction,
        low_first,
        lambda _label, messages, first: elicit.elicit_text(
            model,
            messages,
            fmt.max_output_tokens_rating,
            is_rating=True,
            sample_index=0,
            cache_prefix=first,
        ),
        fmt,
    )

    _dump_raw_log(CHECK1_RAW_PATH)

    _rule("CHECK 1 — parsed ratings")
    for key in ("low", "high", "self"):
        print(f"  {key:<5} raw={replies[key]!r}  parsed="
              f"{elicit.parse_rating(replies[key])!r}  "
              f"in_range={_in_range(fmt, elicit.parse_rating(replies[key]))}")

    elicit.print_usage_summary()
    return 0


def _in_range(fmt: config.ScaleFormat, value: int | None) -> str:
    if value is None:
        return "n/a (parse failure)"
    return str(fmt.in_range(value))


def check2() -> int:
    """One rating call per (model, format) for the three untested models: 9 calls."""
    task = tasks.load_tasks(1, 0)[0]
    direction = config.SCALE_ASCENDING

    elicit.set_raw_log_path(CHECK2_RAW_PATH)
    if CHECK2_RAW_PATH.exists():
        CHECK2_RAW_PATH.unlink()

    _rule("CHECK 2 — rating blocks, three untested models x three formats")
    print(f"models   : {', '.join(CHECK2_MODELS)}")
    print(f"formats  : {', '.join(f.name for f in config.MAIN_SCALE_FORMATS)}")
    print(f"task     : {task.task_id}")
    print(f"direction: {direction} (held fixed; the variables here are model and format)")
    print("shape    : condition-N (task -> solution as an assistant turn -> self-question)")
    print("solution : a fixed hand-written stand-in, NOT model output — see module docstring")
    print(f"raw log  : {CHECK2_RAW_PATH}")

    results = []
    for model in CHECK2_MODELS:
        for fmt in config.MAIN_SCALE_FORMATS:
            messages = pilot._condition_n_messages(
                task, STANDIN_SOLUTION, direction, fmt
            )
            text = elicit.elicit_text(
                model, messages, fmt.max_output_tokens_rating, is_rating=True
            )
            results.append((model, fmt, text, elicit.parse_rating(text)))

    _dump_raw_log(CHECK2_RAW_PATH)

    _rule("CHECK 2 — summary: raw response and parsed value per cell")
    print(f"{'model':<26} {'fmt':<6} {'raw':<12} {'parsed':<8} in range?")
    for model, fmt, text, parsed in results:
        print(f"{model:<26} {fmt.name:<6} {text!r:<12} {str(parsed):<8} "
              f"{_in_range(fmt, parsed)}")

    failures = [r for r in results if r[3] is None]
    off_scale = [r for r in results if r[3] is not None and not r[1].in_range(r[3])]
    print()
    print(f"parse failures : {len(failures)} of {len(results)}")
    print(f"off-scale      : {len(off_scale)} of {len(results)}")

    elicit.print_usage_summary()
    return 0


CHECK3_RAW_PATH = config.OUT_DIR / "check3_recheck_raw.jsonl"
CHECK3_MODEL = "gemini-3.1-pro-preview"


def check3() -> int:
    """Re-verification after the three fixes: 3 calls, one per format.

    CHECK 2 found this model's rating calls returning 400 on
    `thinking_level="minimal"`, and — once that was worked around — returning a
    truncated `'10'` where the true answer was `'100'`. Both are settings
    changes, so the only thing that establishes they took is a live call at the
    settings the run will actually use, read back off the raw log.
    """
    task = tasks.load_tasks(1, 0)[0]
    direction = config.SCALE_ASCENDING

    elicit.set_raw_log_path(CHECK3_RAW_PATH)
    if CHECK3_RAW_PATH.exists():
        CHECK3_RAW_PATH.unlink()

    _rule("CHECK 3 — re-verification at the new settings")
    print(f"model         : {CHECK3_MODEL}")
    print(f"thinking_level: {config.rating_thinking_level(CHECK3_MODEL)}")
    print("rating caps   : " + ", ".join(
        f"{f.name}={config.rating_max_output_tokens(CHECK3_MODEL, f)}"
        for f in config.MAIN_SCALE_FORMATS
    ))
    print(f"raw log       : {CHECK3_RAW_PATH}")

    results = []
    for fmt in config.MAIN_SCALE_FORMATS:
        messages = pilot._condition_n_messages(
            task, STANDIN_SOLUTION, direction, fmt
        )
        result = elicit.elicit_call(
            CHECK3_MODEL,
            messages,
            config.rating_max_output_tokens(CHECK3_MODEL, fmt),
            is_rating=True,
        )
        results.append((fmt, result))

    _dump_raw_log(CHECK3_RAW_PATH)

    _rule("CHECK 3 — summary")
    print(f"{'fmt':<6} {'raw':<10} {'parsed':<8} {'truncated':<10} "
          f"{'thought':<8} {'out':<5} in range?")
    for fmt, result in results:
        parsed = elicit.parse_rating_result(result)
        print(f"{fmt.name:<6} {result.text!r:<10} {str(parsed):<8} "
              f"{str(result.truncated):<10} {str(result.thought_tokens):<8} "
              f"{str(result.output_tokens):<5} {_in_range(fmt, parsed)}")

    s100 = next(r for f, r in results if f.name == "s100")
    s100_value = elicit.parse_rating_result(s100)
    print()
    print(f"s100 returned {s100.text!r}, parsed {s100_value!r}.")
    if s100.text is not None and s100.text.strip() == "100":
        print("s100 is the full '100', not a truncated '10'. Fix confirmed.")
    else:
        print("s100 is NOT '100'. Do not start the run.")

    bad = [f.name for f, r in results
           if r.truncated or elicit.parse_rating_result(r) is None]
    print(f"formats with a truncation or a null parse: {bad or 'none'}")

    elicit.print_usage_summary()
    return 1 if bad else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check1", action="store_true",
                        help="Gemini condition-V thread (4 calls)")
    parser.add_argument("--check2", action="store_true",
                        help="Rating blocks, 3 models x 3 formats (9 calls)")
    parser.add_argument("--check3", action="store_true",
                        help="Re-verify gemini-3.1-pro-preview at the new settings (3 calls)")
    args = parser.parse_args()

    if not (args.check1 or args.check2 or args.check3):
        parser.error("pass --check1, --check2 or --check3")

    status = 0
    if args.check1:
        status |= check1()
    if args.check2:
        status |= check2()
    if args.check3:
        status |= check3()
    return status


if __name__ == "__main__":
    sys.exit(main())
