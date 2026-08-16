"""Progress and stop-condition report for a main run in flight. Read-only.

Reads `main_raw.jsonl` for spend and liveness and `main_observations.jsonl` for
the per-model rates. Nothing here interprets a result — it reports the five
conditions the run is supposed to be stopped on, and whether each is tripped:

    1  parse-failure rate      > 5%   for any model
    2  any rating outside its format's range
    3  execution-failure rate  > 40%  for any model
    4  no completed call in the last 10 minutes
    5  truncation-failure rate > 5%   for any model

Condition 5 exists because a truncated rating is not a parse failure and not
off-scale: a `'100'` cut to `'10'` is a well-formed in-range integer, so the
first four conditions cannot see it.

Usage:
    python3 monitor_run.py
"""

import json
import subprocess
import sys
import time
from datetime import datetime, timezone

import run_pilot as pilot
from pilot import analyze, config, resume


def _mainrun_start_epoch() -> float | None:
    """When the digitalminds-mainrun.service last entered `active`, as epoch.

    Used as a floor for the stall check: if the raw log's last mtime pre-dates
    the current service start, "no calls since start" is the correct state and
    is bounded by service uptime, not by the previous run's last write. Without
    this floor, restarting the run trips the 10-min stall on the first check
    because the mtime is inherited from the earlier run.

    Returns None if systemctl is unavailable or the unit is not running under
    systemd — the caller falls back to raw-log mtime.
    """
    try:
        out = subprocess.check_output(
            ["systemctl", "--user", "show", "digitalminds-mainrun.service",
             "-p", "ActiveEnterTimestampMonotonic", "-p", "ActiveEnterTimestamp",
             "--value"],
            text=True, timeout=5,
        ).splitlines()
    except (OSError, subprocess.SubprocessError):
        return None
    ts_str = next((l for l in out if l and l != "0"), None)
    if not ts_str:
        return None
    # Format like "Sat 2026-08-16 02:59:57 UTC" per systemctl's --value output
    # for ActiveEnterTimestamp. Parse defensively.
    for fmt in ("%a %Y-%m-%d %H:%M:%S %Z", "%Y-%m-%d %H:%M:%S %Z"):
        try:
            return datetime.strptime(ts_str, fmt).replace(
                tzinfo=timezone.utc
            ).timestamp()
        except ValueError:
            continue
    return None

STALL_SECONDS = 10 * 60
MAX_PARSE_FAILURE_RATE = 0.05
MAX_TRUNCATION_RATE = 0.05
MAX_EXECUTION_FAILURE_RATE = 0.40


def _spend() -> tuple[int, dict[str, dict[str, int]], float]:
    """Call count, per-model token totals, and seconds since the last call."""
    path = config.MAIN_RAW_JSONL_PATH
    if not path.exists():
        return 0, {}, float("inf")

    totals: dict[str, dict[str, int]] = {}
    calls = 0
    with open(path) as f:
        for line in f:
            record = json.loads(line)
            calls += 1
            t = totals.setdefault(
                record["model"],
                {"in": 0, "out": 0, "thought": 0, "cache_read": 0,
                 "cache_write": 0, "errors": 0, "retries": 0, "err429": 0},
            )
            t["in"] += record.get("input_tokens") or 0
            t["out"] += record.get("output_tokens") or 0
            t["thought"] += record.get("thought_tokens") or 0
            t["cache_read"] += record.get("cached_input_tokens") or 0
            t["cache_write"] += record.get("cache_creation_tokens") or 0
            err = record.get("error") or ""
            t["errors"] += 1 if err else 0
            if "429" in err:
                t["err429"] += 1
            t["retries"] += record.get("retries") or 0

    # The reference time for "last call" is the more recent of the raw log's
    # last write and the current mainrun's start. Without the start-time floor,
    # a fresh restart trips the stall check on the previous run's stale mtime.
    reference = max(path.stat().st_mtime, _mainrun_start_epoch() or 0.0)
    return calls, totals, time.time() - reference


def _per_model(observations: list[analyze.Observation]) -> dict[str, dict[str, object]]:
    out: dict[str, dict[str, object]] = {}
    for obs in observations:
        m = out.setdefault(
            obs.model,
            {"obs": 0, "draws": 0, "null": 0, "truncated": 0, "off_scale": 0,
             "exec_fail": 0, "no_code": 0, "off_scale_examples": []},
        )
        m["obs"] += 1
        if not obs.executes_cleanly:
            m["exec_fail"] += 1
        if not obs.code_extracted:
            m["no_code"] += 1
        scale = obs.scale
        for name in analyze.RATING_FIELDS:
            draws = getattr(obs, name)
            m["draws"] += len(draws)
            m["null"] += sum(1 for d in draws if d is None)
            m["truncated"] += obs.truncated_draws.get(name.removesuffix("_draws"), 0)
            for d in draws:
                if d is not None and not scale.in_range(d):
                    m["off_scale"] += 1
                    if len(m["off_scale_examples"]) < 5:
                        m["off_scale_examples"].append(
                            f"{obs.task_id}/{obs.scale_format}/{name}={d}"
                        )
    return out


def main() -> int:
    calls, totals, since_last = _spend()
    observations = resume.load_observations(config.MAIN_OBSERVATIONS_PATH)
    per_model = _per_model(observations)

    planned = 22800
    print(f"--- Progress ---")
    print(f"calls completed : {calls} of {planned} ({calls / planned:.1%})")
    print(f"calls remaining : {planned - calls}")
    print(f"observations    : {len(observations)}")
    print(f"last call       : {since_last / 60:.1f} min ago")
    print()

    print("--- Spend ---")
    print(f"{'model':<28} {'in':>9} {'out':>8} {'thought':>8} "
          f"{'cache rd':>9} {'cache wr':>9} {'429':>4} {'retries':>7} "
          f"{'errors':>7} {'USD':>9}")
    total_cost = 0.0
    for model, t in totals.items():
        cost = pilot.cost_of(
            model, t["in"], t["out"] + t["thought"], t["cache_read"], t["cache_write"]
        )
        total_cost += cost or 0.0
        print(f"{model:<28} {t['in']:>9} {t['out']:>8} {t['thought']:>8} "
              f"{t['cache_read']:>9} {t['cache_write']:>9} {t['err429']:>4} "
              f"{t['retries']:>7} {t['errors']:>7} "
              f"{'n/a' if cost is None else f'{cost:.4f}':>9}")
    print(f"{'TOTAL':<28} {'':>9} {'':>8} {'':>8} {'':>9} {'':>9} {'':>4} "
          f"{'':>7} {'':>7} {total_cost:>9.4f}")
    print()

    print("--- Failure rates, per model ---")
    print(f"{'model':<28} {'obs':>5} {'draws':>7} {'parse':>8} {'trunc':>8} "
          f"{'offscale':>9} {'exec fail':>10} {'no code':>8}")
    tripped: list[str] = []
    for model, m in per_model.items():
        draws = m["draws"] or 1
        parse_rate = (m["null"] - m["truncated"]) / draws
        trunc_rate = m["truncated"] / draws
        exec_rate = m["exec_fail"] / (m["obs"] or 1)
        print(f"{model:<28} {m['obs']:>5} {m['draws']:>7} {parse_rate:>7.2%} "
              f"{trunc_rate:>7.2%} {m['off_scale']:>9} {exec_rate:>9.1%} "
              f"{m['no_code']:>8}")

        if parse_rate > MAX_PARSE_FAILURE_RATE:
            tripped.append(f"[1] {model} parse-failure rate {parse_rate:.2%} > 5%")
        if m["off_scale"]:
            tripped.append(
                f"[2] {model} returned {m['off_scale']} off-scale rating(s): "
                f"{', '.join(m['off_scale_examples'])}"
            )
        if exec_rate > MAX_EXECUTION_FAILURE_RATE:
            tripped.append(f"[3] {model} execution-failure rate {exec_rate:.1%} > 40%")
        if trunc_rate > MAX_TRUNCATION_RATE:
            tripped.append(f"[5] {model} truncation rate {trunc_rate:.2%} > 5%")
    if since_last > STALL_SECONDS:
        tripped.append(f"[4] no completed call in {since_last / 60:.1f} minutes")
    print()

    if tripped:
        print("--- STOP CONDITIONS TRIPPED ---")
        for line in tripped:
            print(line)
        return 1
    print("--- No stop condition tripped ---")
    return 0


if __name__ == "__main__":
    sys.exit(main())
