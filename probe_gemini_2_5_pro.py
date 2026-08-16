"""~30-call replacement-Gemini probe. Filename misleads by history.

Was written to probe `gemini-2.5-pro` after `gemini-3.1-pro-preview` tripped
its 250-request-per-day quota. That model returned 404 "no longer available
to new users", so the target switched to `gemini-3.5-flash-lite` in the
`MODEL` constant below. The filename stayed for git-history continuity —
`git log --follow probe_gemini_2_5_pro.py` retrieves the pivot.

Two full condition-V cells on separate tasks, format p5, driving run_pilot's
own message builders and elicit_call. If any request 429s, this reports it —
that is the deciding question. `PROVIDER` is patched in-process only, so
running this against a candidate does not touch config.py.

Usage:
    python3 -u probe_gemini_2_5_pro.py
"""

import collections
import json
import sys

import run_pilot as pilot
from pilot import config, elicit, tasks

MODEL = "gemini-3.5-flash-lite"
RAW_PATH = config.OUT_DIR / "probe_gemini_3_5_flash_lite_raw.jsonl"

# Google's published pricing for gemini-3.5-flash-lite at <=200k-token prompts,
# used here for the probe's cost readout only. Not persisted to config.
PRICE_INPUT_USD_PER_MTOK = 0.10
PRICE_OUTPUT_USD_PER_MTOK = 0.40


def _rule(t: str) -> None:
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


def _dump_call(record: dict, n: int, of: int) -> None:
    print("-" * 78)
    print(f"CALL {n} of {of}   is_rating={record['is_rating']}   "
          f"max_output_tokens={record['max_output_tokens']}   "
          f"error={record['error'] is not None}")
    if record["error"]:
        print(f"  error : {record['error'][:200]}")
    else:
        raw = record.get("raw_response")
        head = (raw if raw is None else raw[:80]).__repr__()
        print(f"  raw   : {head}")
    print(f"  tokens: in={record['input_tokens']} out={record['output_tokens']} "
          f"thought={record['thought_tokens']}   truncated={record['truncated']}")


def main() -> int:
    # Wire the new model into the provider dispatch table for this process only.
    config.PROVIDER[MODEL] = config.GOOGLE

    elicit.set_raw_log_path(RAW_PATH)
    elicit.set_call_budget(60)
    if RAW_PATH.exists():
        RAW_PATH.unlink()

    fmt = config.SCALE_P5
    two_tasks = tasks.load_tasks(2, 0)   # MBPP only, first two.
    direction = config.SCALE_ASCENDING
    low_first = True

    _rule(f"PROBE — {MODEL}")
    print(f"tasks         : {[t.task_id for t in two_tasks]}")
    print(f"scale format  : {fmt.name} (cap {config.rating_max_output_tokens(MODEL, fmt)})")
    print(f"thinking      : {config.rating_thinking_level(MODEL)}")
    print(f"raw log       : {RAW_PATH}")
    print("shape         : 2 tasks x (1 codegen + 5 samples x [low, high, self]) = 32 calls")

    per_task_results = []
    for task in two_tasks:
        _rule(f"{MODEL}  task {task.task_id}")
        solution, reason = pilot.generate_solution(MODEL, task)
        if solution is None:
            print(f"CODEGEN FAILED: {reason}. Continuing to next task.")
            per_task_results.append((task, None, {}))
            continue
        print("CODEGEN OK. First 200 chars of solution:")
        print(f"  {solution[:200]!r}")

        draws, truncations = pilot.run_condition_v(
            MODEL, task, solution, direction, low_first, fmt
        )
        per_task_results.append((task, solution, {"draws": draws, "trunc": truncations}))
        print("Draws (5 samples):")
        for key in ("low", "high", "self"):
            print(f"  {key:<5} {draws[key]}   truncated={truncations[key]}")

    # Aggregate every call from the raw log.
    records = [json.loads(l) for l in open(RAW_PATH)]
    errors = [r for r in records if r["error"]]
    error_kinds = collections.Counter()
    for r in errors:
        msg = r["error"] or ""
        for k in ("429", "500", "503", "InvalidArgument", "400", "Timeout"):
            if k in msg:
                error_kinds[k] += 1
                break
        else:
            error_kinds["other"] += 1

    _rule("Raw log — every call")
    for i, r in enumerate(records, 1):
        _dump_call(r, i, len(records))

    _rule("Probe summary")
    print(f"calls made          : {len(records)}")
    print(f"errors              : {len(errors)}  {dict(error_kinds) or ''}")
    print(f"429s specifically   : {error_kinds.get('429', 0)}")

    input_tok = sum((r["input_tokens"] or 0) for r in records)
    output_tok = sum((r["output_tokens"] or 0) for r in records)
    thought_tok = sum((r["thought_tokens"] or 0) for r in records)
    billed_output = output_tok + thought_tok
    cost = (input_tok / 1e6 * PRICE_INPUT_USD_PER_MTOK
            + billed_output / 1e6 * PRICE_OUTPUT_USD_PER_MTOK)
    print(f"tokens              : {input_tok} in / {output_tok} out / "
          f"{thought_tok} thought")
    print(f"cost                : ${cost:.4f}  "
          f"(hardcoded prices, source: Google published rates)")

    # Two-task extrapolation to a full leg (60 tasks x 3 formats), so the user
    # can decide on the go/no-go of a full run.
    if not errors:
        obs_shape_calls = 26   # codegen 1 + condition V/N/P4 = 15 + 5 + 5
        per_leg = 60 * obs_shape_calls
        cost_scale = cost / (len(records) or 1) * per_leg
        print()
        print("Projection (approximate):")
        print(f"  full leg: 60 tasks x 26 calls = {per_leg} calls, "
              f"budget-scaled cost ~${cost_scale:.1f} (probe was condition-V "
              f"only on p5, and ignores caching)")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
