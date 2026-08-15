"""Checks on how a provider response is turned into a CallResult.

The subject here is `_first_text`. It exists because of a live failure: on
2026-08-15 claude-opus-5 returned a thinking block ahead of its answer on 52 of
128 smoke-test rating calls, and the old `response.content[0].text` raised
AttributeError on every one of them. The calls were logged as errors and the
ratings were lost.

The failure was intermittent — the same prompt produced a text-first response
most of the time — which is the reason this is pinned by a test rather than left
to the next live run to re-discover.
"""

import pytest

from pilot import config, elicit


class _Block:
    """The two response-block shapes that matter, minus the SDK."""

    def __init__(self, type_: str, text: str | None = None):
        self.type = type_
        if text is not None:
            self.text = text


def test_plain_text_response():
    assert elicit._first_text([_Block("text", "4")]) == "4"


def test_thinking_block_before_the_answer_does_not_raise():
    """The exact shape that broke the smoke test."""
    content = [_Block("thinking"), _Block("text", "4")]
    assert elicit._first_text(content) == "4"


def test_thinking_block_alone_yields_no_text_rather_than_an_exception():
    """A rating truncated inside its thinking block has no answer in it.

    Returning "" makes it a parse failure, which is counted and dropped.
    Raising made it an API error, which is a different diagnostic and hid the
    cause behind a stack trace.
    """
    assert elicit._first_text([_Block("thinking")]) == ""


@pytest.mark.parametrize("content", [None, []])
def test_empty_content_is_empty_text(content):
    assert elicit._first_text(content) == ""


def test_parse_rating_turns_a_missing_answer_into_a_dropped_draw():
    """`_first_text` and `parse_rating` compose into "no rating", not a zero."""
    assert elicit.parse_rating(elicit._first_text([_Block("thinking")])) is None


def test_every_anthropic_model_has_a_cache_minimum_configured():
    """A missing entry would silently read as "no minimum" in the cache report."""
    for model in config.MAIN_MODELS:
        assert model in config.CACHE_MIN_PROMPT_TOKENS
        assert model in config.PROVIDER
        assert model in config.PRICE_PER_MTOK_USD
