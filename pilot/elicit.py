"""Model elicitation: one interface, two providers behind it (DESIGN.md §6).

`elicit(model, messages, n_samples, ...)` makes n_samples independent calls at
temperature 1.0, each replaying the identical `messages` prefix. Every call
appends one line to the raw log immediately after the response comes back (or
the call fails) and before any parsing. Parsing is strict: a single integer, or
None on failure — never a re-ask with different wording.

Anthropic via its own SDK. Google via the native Gemini SDK's Interactions API
(`client.interactions.create`; see CLAUDE.md "API facts") — not the OpenAI-
compatibility layer, which rejects the new AQ.-prefix auth keys. Dispatch is on
`config.PROVIDER`, not on identity against two model constants.

`max_output_tokens` is passed in by the caller rather than looked up here,
because the rating cap depends on the scale format in use (a 0-100 reply needs
more room than a single digit) and a lookup would silently apply the wrong one.

**Truncation is recorded, not inferred later.** A reply cut off at the output
ceiling used to reach the code extractor as apparent model incompetence. Each
raw-log line now carries `truncated` and, where the provider gives one, the
`stop_reason`. On Gemini there is no finish_reason on the Interactions response
and `max_output_tokens` is a *combined* budget for thinking and visible output,
so truncation is inferred from thought+output approaching the ceiling.

Requires ANTHROPIC_API_KEY and GOOGLE_API_KEY (or GEMINI_API_KEY) in the
environment or a .env file at the project root.
"""

import json
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from pilot import config

load_dotenv(config.PROJECT_ROOT / ".env")

_INTEGER_RE = re.compile(r"^\s*(-?\d+)\s*$")

_call_count = 0
_call_budget = config.MAX_CALLS
_raw_path = config.RAW_JSONL_PATH


class CallBudgetExceeded(RuntimeError):
    pass


@dataclass
class CallResult:
    text: str | None
    input_tokens: int | None
    output_tokens: int | None
    thought_tokens: int | None = None
    cached_input_tokens: int | None = None
    # Tokens written to the cache, billed at the write multiplier. Kept separate
    # from cached_input_tokens (reads, billed at 0.1x) because the two are priced
    # differently and only their difference says whether caching paid for itself.
    # Anthropic reports both; Google's implicit caching reports reads only.
    cache_creation_tokens: int | None = None
    stop_reason: str | None = None
    truncated: bool = False


def set_call_budget(limit: int) -> None:
    """Raises (or lowers) the process-wide API-call ceiling.

    The pilot's 1200 is far below what the main experiment needs, and silently
    patching config.MAX_CALLS would remove the guard without leaving a trace.
    A runner calls this once, explicitly, and prints what it did.
    """
    global _call_budget
    _call_budget = limit


def set_raw_log_path(path: Path) -> None:
    """Points the raw log at a different file (the main run keeps its own)."""
    global _raw_path
    _raw_path = path


def raw_log_path() -> Path:
    return _raw_path


def call_count() -> int:
    return _call_count


def _parse_integer(text: str | None) -> int | None:
    if text is None:
        return None
    match = _INTEGER_RE.match(text)
    return int(match.group(1)) if match else None


def _check_call_budget() -> None:
    global _call_count
    if _call_count >= _call_budget:
        raise CallBudgetExceeded(
            f"Call ceiling ({_call_budget}) reached; aborting before making "
            "another API call."
        )
    _call_count += 1


# --- Anthropic ---------------------------------------------------------------


def _anthropic_messages(messages: list[dict], cache_prefix: bool) -> list[dict]:
    """Optionally marks the whole prompt as a cache breakpoint.

    Only ever called with `cache_prefix=True` for a prompt this run sends more
    than once verbatim. Placing a breakpoint on a prompt sent once would incur
    the 1.25x cache-write multiplier with no subsequent read — i.e. it would
    cost more than not caching. If the prompt is below the model's minimum
    cacheable length (config.CACHE_MIN_PROMPT_TOKENS) the request is processed
    uncached, with no error and no write premium.
    """
    if not cache_prefix or not messages:
        return messages
    head, last = messages[:-1], messages[-1]
    return head + [
        {
            "role": last["role"],
            "content": [
                {
                    "type": "text",
                    "text": last["content"],
                    "cache_control": {"type": "ephemeral"},
                }
            ],
        }
    ]


def _first_text(content) -> str:
    """The first text block, or "" — never `content[0].text`.

    claude-opus-5 emits a thinking block ahead of its answer on a minority of
    calls even with no thinking requested, so indexing block 0 raises
    AttributeError non-deterministically. It did, on 52 of 128 smoke-test calls.
    """
    for block in content or ():
        if getattr(block, "type", None) == "text":
            return block.text
    return ""


def _call_anthropic(
    model: str,
    messages: list[dict],
    max_output_tokens: int,
    cache_prefix: bool,
    is_rating: bool,
) -> CallResult:
    import anthropic

    client = anthropic.Anthropic(timeout=config.API_TIMEOUT_SECONDS)
    # Extended thinking is turned off explicitly on rating calls rather than
    # left at the default. On claude-opus-5 the default produced a thinking
    # block on ~40% of rating calls, and against an 8-token cap the block
    # consumed the whole budget, so the call returned no digit at all. That is
    # the parse-failure mode the ANSWER_INSTRUCTION fix already closed once.
    # Placing a point on an ordinal scale is classification; this mirrors
    # config.GOOGLE_RATING_THINKING_LEVEL, which does the same for Gemini, and
    # leaves code generation at each model's default.
    extra: dict = {"thinking": {"type": "disabled"}} if is_rating else {}
    response = client.messages.create(
        model=model,
        max_tokens=max_output_tokens,
        temperature=config.TEMPERATURE,
        messages=_anthropic_messages(messages, cache_prefix),
        **extra,
    )
    usage = response.usage
    text = _first_text(response.content)
    return CallResult(
        text=text,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        cached_input_tokens=getattr(usage, "cache_read_input_tokens", None),
        cache_creation_tokens=getattr(usage, "cache_creation_input_tokens", None),
        stop_reason=response.stop_reason,
        truncated=response.stop_reason == "max_tokens",
    )


# --- Google ------------------------------------------------------------------


def _call_google(
    model: str, messages: list[dict], max_output_tokens: int, is_rating: bool
) -> CallResult:
    from google import genai

    client = genai.Client()

    steps = [
        {
            "type": "model_output" if m["role"] == "assistant" else "user_input",
            "content": [{"type": "text", "text": m["content"]}],
        }
        for m in messages
    ]

    generation_config: dict = {"max_output_tokens": max_output_tokens}
    if is_rating:
        generation_config["thinking_level"] = config.GOOGLE_RATING_THINKING_LEVEL

    response = client.interactions.create(
        model=model,
        input=steps,
        generation_config=generation_config,
        timeout=config.API_TIMEOUT_SECONDS,
    )
    usage = response.usage
    output_tokens = usage.total_output_tokens if usage else None
    thought_tokens = usage.total_thought_tokens if usage else None

    # No finish_reason exists on the Interactions response, and the ceiling is a
    # combined thinking+output budget, so this is the only signal available.
    spent = (output_tokens or 0) + (thought_tokens or 0)
    truncated = spent >= max_output_tokens - config.GOOGLE_TRUNCATION_SLACK_TOKENS

    return CallResult(
        text=response.output_text,
        input_tokens=usage.total_input_tokens if usage else None,
        output_tokens=output_tokens,
        thought_tokens=thought_tokens,
        cached_input_tokens=getattr(usage, "total_cached_content_tokens", None),
        stop_reason=None,
        truncated=truncated,
    )


def _raw_call(
    model: str,
    messages: list[dict],
    max_output_tokens: int,
    is_rating: bool,
    cache_prefix: bool,
) -> CallResult:
    provider = config.PROVIDER.get(model)
    if provider == config.ANTHROPIC:
        return _call_anthropic(
            model, messages, max_output_tokens, cache_prefix, is_rating
        )
    if provider == config.GOOGLE:
        # Gemini implicit caching is on by default for all 3.x models and needs
        # no request-side flag, so `cache_prefix` has nothing to apply here.
        return _call_google(model, messages, max_output_tokens, is_rating)
    raise ValueError(
        f"Unknown model: {model!r}. Add it to config.PROVIDER. "
        f"Known: {sorted(config.PROVIDER)}"
    )


def _append_raw_line(record: dict) -> None:
    _raw_path.parent.mkdir(parents=True, exist_ok=True)
    with open(_raw_path, "a") as f:
        f.write(json.dumps(record) + "\n")


def parse_rating(text: str | None) -> int | None:
    """Strict parse of a rating reply: a bare integer, or None."""
    return _parse_integer(text)


def elicit_call(
    model: str,
    messages: list[dict],
    max_output_tokens: int,
    is_rating: bool = False,
    sample_index: int = 0,
    cache_prefix: bool = False,
) -> CallResult:
    """One call. Always returns a CallResult; `text is None` means it failed.

    Logs to the raw log exactly once, before any parsing, whether the call
    succeeded or raised. Raises CallBudgetExceeded if the ceiling would be
    exceeded — that is the one exception that propagates.
    """
    _check_call_budget()

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "sample_index": sample_index,
        "is_rating": is_rating,
        "max_output_tokens": max_output_tokens,
        "cache_prefix": cache_prefix,
        "messages": messages,
    }
    try:
        result = _raw_call(model, messages, max_output_tokens, is_rating, cache_prefix)
        record["error"] = None
    except Exception as exc:
        result = CallResult(text=None, input_tokens=None, output_tokens=None)
        record["error"] = repr(exc)

    record["raw_response"] = result.text
    record["input_tokens"] = result.input_tokens
    record["output_tokens"] = result.output_tokens
    record["thought_tokens"] = result.thought_tokens
    record["cached_input_tokens"] = result.cached_input_tokens
    record["cache_creation_tokens"] = result.cache_creation_tokens
    record["stop_reason"] = result.stop_reason
    record["truncated"] = result.truncated

    _append_raw_line(record)
    return result


def elicit_text(
    model: str,
    messages: list[dict],
    max_output_tokens: int,
    is_rating: bool = False,
    sample_index: int = 0,
    cache_prefix: bool = False,
) -> str | None:
    """`elicit_call` reduced to its reply text, for callers that need only that.

    Used where a reply must be replayed verbatim as an assistant turn in a
    longer context, which `str(parsed_integer)` would not preserve.
    """
    return elicit_call(
        model, messages, max_output_tokens, is_rating, sample_index, cache_prefix
    ).text


def elicit(
    model: str,
    messages: list[dict],
    n_samples: int,
    max_output_tokens: int,
    is_rating: bool = True,
    cache_prefix: bool = False,
) -> list[int | None]:
    """Returns one parsed integer (or None on failure) per sample.

    Every sample replays the identical prefix, so `cache_prefix=True` is
    correct here whenever the provider can cache at this prompt length: one
    write followed by `n_samples - 1` reads.
    """
    return [
        _parse_integer(
            elicit_text(
                model,
                messages,
                max_output_tokens,
                is_rating,
                sample_index,
                cache_prefix,
            )
        )
        for sample_index in range(n_samples)
    ]


def print_usage_summary() -> None:
    """Reads the raw log and prints calls, tokens and truncations per model."""
    totals: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "calls": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "thought_tokens": 0,
            "cached_input_tokens": 0,
            "cache_creation_tokens": 0,
            "truncated": 0,
            "errors": 0,
        }
    )

    if not _raw_path.exists():
        print(f"No {_raw_path.name} found; nothing to summarize.")
        return

    with open(_raw_path) as f:
        for line in f:
            record = json.loads(line)
            model_totals = totals[record["model"]]
            model_totals["calls"] += 1
            for field in (
                "input_tokens",
                "output_tokens",
                "thought_tokens",
                "cached_input_tokens",
                "cache_creation_tokens",
            ):
                model_totals[field] += record.get(field) or 0
            model_totals["truncated"] += 1 if record.get("truncated") else 0
            model_totals["errors"] += 1 if record.get("error") else 0

    print(f"--- Usage summary ({_raw_path}) ---")
    for model, t in totals.items():
        print(
            f"{model}: {t['calls']} calls, {t['input_tokens']} input, "
            f"{t['output_tokens']} output, {t['thought_tokens']} thought, "
            f"{t['truncated']} truncated, {t['errors']} errors"
        )
    print()
    print("--- Cache tokens actually reported by the provider ---")
    print(
        "Reads are billed at 0.1x the input price and writes at 1.25x, so a model "
        "with writes and no reads paid a premium for nothing."
    )
    for model, t in totals.items():
        written = t["cache_creation_tokens"]
        read = t["cached_input_tokens"]
        minimum = config.CACHE_MIN_PROMPT_TOKENS.get(model)
        note = ""
        if written == 0 and read == 0:
            note = (
                f"  (no prompt reached this model's {minimum}-token minimum)"
                if minimum
                else "  (nothing cached)"
            )
        print(f"{model}: {written} written, {read} read{note}")
