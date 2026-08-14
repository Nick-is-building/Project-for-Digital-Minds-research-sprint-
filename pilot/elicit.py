"""Model elicitation: one interface, two providers behind it (DESIGN.md §6).

`elicit(model, messages, n_samples)` makes n_samples independent calls at
temperature 1.0, each replaying the identical `messages` prefix. Every call
appends one line to pilot/out/raw.jsonl immediately after the response comes
back (or the call fails) and before any parsing. Parsing is strict: a single
integer, or None on failure — never a re-ask with different wording.

Anthropic via its own SDK. Google via the native Gemini SDK's Interactions API
(`client.interactions.create`; see CLAUDE.md "API facts") — not the OpenAI-
compatibility layer, which rejects the new AQ.-prefix auth keys.

Requires ANTHROPIC_API_KEY and GOOGLE_API_KEY (or GEMINI_API_KEY) in the
environment or a .env file at the project root.
"""

import json
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone

from dotenv import load_dotenv

from pilot import config

load_dotenv(config.PROJECT_ROOT / ".env")

_INTEGER_RE = re.compile(r"^\s*(-?\d+)\s*$")

_call_count = 0


class CallBudgetExceeded(RuntimeError):
    pass


@dataclass
class TokenUsage:
    input_tokens: int | None
    output_tokens: int | None
    thought_tokens: int | None = None


def _parse_integer(text: str | None) -> int | None:
    if text is None:
        return None
    match = _INTEGER_RE.match(text)
    return int(match.group(1)) if match else None


def _check_call_budget() -> None:
    global _call_count
    if _call_count >= config.MAX_CALLS:
        raise CallBudgetExceeded(
            f"MAX_CALLS ceiling ({config.MAX_CALLS}) reached; aborting before "
            "making another API call."
        )
    _call_count += 1


def _call_anthropic(
    model: str, messages: list[dict], is_rating: bool
) -> tuple[str, TokenUsage]:
    import anthropic

    client = anthropic.Anthropic(timeout=config.API_TIMEOUT_SECONDS)
    max_tokens = (
        config.MAX_OUTPUT_TOKENS_RATING if is_rating else config.MAX_OUTPUT_TOKENS_DEFAULT
    )
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=config.TEMPERATURE,
        messages=messages,
    )
    text = response.content[0].text
    usage = TokenUsage(
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
    )
    return text, usage


def _call_google(
    model: str, messages: list[dict], is_rating: bool
) -> tuple[str, TokenUsage]:
    from google import genai

    client = genai.Client()

    steps = [
        {
            "type": "model_output" if m["role"] == "assistant" else "user_input",
            "content": [{"type": "text", "text": m["content"]}],
        }
        for m in messages
    ]

    generation_config: dict = {
        "max_output_tokens": (
            config.MAX_OUTPUT_TOKENS_RATING if is_rating else config.MAX_OUTPUT_TOKENS_DEFAULT
        )
    }
    if is_rating:
        generation_config["thinking_level"] = config.GOOGLE_RATING_THINKING_LEVEL

    response = client.interactions.create(
        model=model,
        input=steps,
        generation_config=generation_config,
        timeout=config.API_TIMEOUT_SECONDS,
    )
    usage = response.usage
    token_usage = TokenUsage(
        input_tokens=usage.total_input_tokens if usage else None,
        output_tokens=usage.total_output_tokens if usage else None,
        thought_tokens=usage.total_thought_tokens if usage else None,
    )
    return response.output_text, token_usage


def _raw_call(
    model: str, messages: list[dict], is_rating: bool
) -> tuple[str, TokenUsage]:
    if model == config.ANTHROPIC_MODEL:
        return _call_anthropic(model, messages, is_rating)
    if model == config.GOOGLE_MODEL:
        return _call_google(model, messages, is_rating)
    raise ValueError(f"Unknown model: {model!r}. Known: {config.PILOT_MODELS}")


def _append_raw_line(record: dict) -> None:
    config.OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(config.RAW_JSONL_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")


def elicit(
    model: str,
    messages: list[dict],
    n_samples: int,
    is_rating: bool = True,
) -> list[int | None]:
    """Returns one parsed integer (or None on failure) per sample.

    `is_rating` selects the rating-call cost/thinking profile (short output,
    minimal Gemini thinking) versus the code-generation profile (default
    thinking, larger output budget). Every call — success or failure — is
    appended to raw.jsonl immediately, before the response text is parsed.

    Raises CallBudgetExceeded if config.MAX_CALLS would be exceeded; already-
    made calls in this batch remain logged.
    """
    results: list[int | None] = []
    for sample_index in range(n_samples):
        _check_call_budget()

        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model": model,
            "sample_index": sample_index,
            "is_rating": is_rating,
            "messages": messages,
        }
        try:
            raw_text, usage = _raw_call(model, messages, is_rating)
            record["raw_response"] = raw_text
            record["error"] = None
            record["input_tokens"] = usage.input_tokens
            record["output_tokens"] = usage.output_tokens
            record["thought_tokens"] = usage.thought_tokens
        except Exception as exc:
            raw_text = None
            record["raw_response"] = None
            record["error"] = repr(exc)
            record["input_tokens"] = None
            record["output_tokens"] = None
            record["thought_tokens"] = None

        _append_raw_line(record)
        results.append(_parse_integer(raw_text))

    return results


def print_usage_summary() -> None:
    """Reads raw.jsonl and prints total calls and total tokens per model."""
    totals: dict[str, dict[str, int]] = defaultdict(
        lambda: {"calls": 0, "input_tokens": 0, "output_tokens": 0, "thought_tokens": 0}
    )

    if not config.RAW_JSONL_PATH.exists():
        print("No raw.jsonl found; nothing to summarize.")
        return

    with open(config.RAW_JSONL_PATH) as f:
        for line in f:
            record = json.loads(line)
            model_totals = totals[record["model"]]
            model_totals["calls"] += 1
            model_totals["input_tokens"] += record.get("input_tokens") or 0
            model_totals["output_tokens"] += record.get("output_tokens") or 0
            model_totals["thought_tokens"] += record.get("thought_tokens") or 0

    print("--- Usage summary (pilot/out/raw.jsonl) ---")
    for model, model_totals in totals.items():
        print(
            f"{model}: {model_totals['calls']} calls, "
            f"{model_totals['input_tokens']} input tokens, "
            f"{model_totals['output_tokens']} output tokens, "
            f"{model_totals['thought_tokens']} thought tokens"
        )
