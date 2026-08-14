"""Model elicitation: one interface, two providers behind it (DESIGN.md §6).

`elicit(model, messages, n_samples)` makes n_samples independent calls at
temperature 1.0, each replaying the identical `messages` prefix. Every call
appends one line to pilot/out/raw.jsonl immediately after the response comes
back (or the call fails) and before any parsing. Parsing is strict: a single
integer, or None on failure — never a re-ask with different wording.

Anthropic via its own SDK; Google via the native Gemini SDK (`google-genai`),
not the OpenAI-compatibility layer — the latter does not expose Gemini's
per-model logprob support that this project may need later, and has been
observed to break without notice.

Requires ANTHROPIC_API_KEY and GOOGLE_API_KEY (or GEMINI_API_KEY) in the
environment or a .env file at the project root.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from pilot import config

load_dotenv(config.PROJECT_ROOT / ".env")

_INTEGER_RE = re.compile(r"^\s*(-?\d+)\s*$")


def _parse_integer(text: str | None) -> int | None:
    if text is None:
        return None
    match = _INTEGER_RE.match(text)
    return int(match.group(1)) if match else None


def _call_anthropic(model: str, messages: list[dict]) -> str:
    import anthropic

    client = anthropic.Anthropic(timeout=config.API_TIMEOUT_SECONDS)
    response = client.messages.create(
        model=model,
        max_tokens=16,
        temperature=config.TEMPERATURE,
        messages=messages,
    )
    return response.content[0].text


def _call_google(model: str, messages: list[dict]) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client()
    contents = [
        types.Content(
            role="model" if m["role"] == "assistant" else "user",
            parts=[types.Part(text=m["content"])],
        )
        for m in messages
    ]
    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=types.GenerateContentConfig(
            temperature=config.TEMPERATURE,
            http_options=types.HttpOptions(timeout=config.API_TIMEOUT_SECONDS * 1000),
        ),
    )
    return response.text


def _raw_call(model: str, messages: list[dict]) -> str:
    if model == config.ANTHROPIC_MODEL:
        return _call_anthropic(model, messages)
    if model == config.GOOGLE_MODEL:
        return _call_google(model, messages)
    raise ValueError(f"Unknown model: {model!r}. Known: {config.PILOT_MODELS}")


def _append_raw_line(record: dict) -> None:
    config.OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(config.RAW_JSONL_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")


def elicit(model: str, messages: list[dict], n_samples: int) -> list[int | None]:
    """Returns one parsed integer (or None on failure) per sample.

    Every call — success or failure — is appended to raw.jsonl immediately,
    before the response text is parsed.
    """
    results: list[int | None] = []
    for sample_index in range(n_samples):
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model": model,
            "sample_index": sample_index,
            "messages": messages,
        }
        try:
            raw_text = _raw_call(model, messages)
            record["raw_response"] = raw_text
            record["error"] = None
        except Exception as exc:
            raw_text = None
            record["raw_response"] = None
            record["error"] = repr(exc)

        _append_raw_line(record)
        results.append(_parse_integer(raw_text))

    return results
