"""Checks on code extraction (see pilot/extract.py for the bug being fixed).

The central assertions are `test_truncated_reply_is_rejected_not_repaired` and
`test_unclosed_fence_is_rejected_not_passed_through`. Both encode the same rule:
extraction must never hand the sandbox something it knows is not a complete
program. The old extractor did, and every such case was scored as the model
answering incorrectly, which is how a token-ceiling misconfiguration was read as
an 80% LBPP failure rate on Gemini.
"""

import pytest

from pilot.extract import (
    NO_FUNCTION,
    NO_REPLY,
    SYNTAX_ERROR,
    TRUNCATED,
    UNCLOSED_FENCE,
    extract_code,
)

MASKING_REF = (
    "Extraction must reject what it cannot parse, with a reason. Accepting a "
    "partial reply makes our own output ceiling indistinguishable from a wrong "
    "answer — see pilot/extract.py and DEVLOG 2026-08-15."
)

GOOD = "def f(x):\n    return x + 1\n"


# --- Success cases -----------------------------------------------------------


@pytest.mark.parametrize(
    "reply",
    [
        f"```python\n{GOOD}```",
        f"```py\n{GOOD}```",
        f"```\n{GOOD}```",
        f"Here you go:\n\n```python\n{GOOD}```\n\nHope that helps.",
        GOOD,
    ],
)
def test_accepts_a_complete_function(reply: str):
    code, reason = extract_code(reply)
    assert reason is None
    assert "def f(x):" in code


def test_first_fence_wins():
    reply = f"```python\n{GOOD}```\n\nAlternative:\n\n```python\ndef g():\n    pass\n```"
    code, reason = extract_code(reply)
    assert reason is None
    assert "def f(x):" in code and "def g():" not in code


# --- The regression: nothing partial is ever accepted ------------------------


def test_truncated_reply_is_rejected_not_repaired():
    """The provider's truncation signal short-circuits everything else.

    The reply below would parse fine, which is the point: even a syntactically
    valid prefix of a longer program is not that program, and the ceiling is our
    fault rather than the model's.
    """
    code, reason = extract_code(f"```python\n{GOOD}```", truncated=True)
    assert code is None, MASKING_REF
    assert reason == TRUNCATED


def test_unclosed_fence_is_rejected_not_passed_through():
    """The exact shape of a reply cut off mid-code: opening fence, no closing one."""
    code, reason = extract_code("```python\ndef f(x):\n    return x +")
    assert code is None, MASKING_REF
    assert reason == UNCLOSED_FENCE


def test_unclosed_fence_rejected_even_when_the_prefix_would_parse():
    """The old extractor's failure, stated as an assertion.

    Regex misses -> whole reply used as code -> the literal "```python" line is
    included -> guaranteed SyntaxError in the sandbox -> scored as a wrong
    answer. Rejecting here is what keeps that off the results.
    """
    code, reason = extract_code(f"```python\n{GOOD}")
    assert code is None, MASKING_REF
    assert reason == UNCLOSED_FENCE


def test_fence_marker_is_never_part_of_returned_code():
    for reply in (f"```python\n{GOOD}```", GOOD):
        code, _ = extract_code(reply)
        assert "```" not in code


# --- Other rejections, each with its own reason ------------------------------


def test_no_reply_is_its_own_reason():
    assert extract_code(None) == (None, NO_REPLY)


def test_no_reply_takes_precedence_over_truncation():
    assert extract_code(None, truncated=True) == (None, NO_REPLY)


def test_prose_without_a_function_is_rejected():
    code, reason = extract_code("I'm not able to help with that.")
    assert code is None
    assert reason == NO_FUNCTION


def test_unparseable_function_is_rejected():
    code, reason = extract_code("def f(x):\nreturn x")  # missing indent
    assert code is None
    assert reason == SYNTAX_ERROR


def test_null_byte_is_rejected_as_a_syntax_error():
    """ast.parse raises ValueError, not SyntaxError, on an embedded NUL.

    Worth pinning: a bare `except SyntaxError` would let this through and the
    failure would surface inside the sandbox instead, where it is
    indistinguishable from a wrong answer.
    """
    code, reason = extract_code("def f():\n    return 1\x00\n")
    assert code is None
    assert reason == SYNTAX_ERROR


def test_every_rejection_reason_is_distinct():
    """The reasons are reported as diagnostic counts, so collisions would merge
    an infrastructure problem into a model result."""
    reasons = (NO_REPLY, TRUNCATED, UNCLOSED_FENCE, NO_FUNCTION, SYNTAX_ERROR)
    assert len(set(reasons)) == len(reasons)
