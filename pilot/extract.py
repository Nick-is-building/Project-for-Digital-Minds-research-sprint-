"""Pulling a runnable solution out of a code-generation reply.

Split out of run_pilot.py on 2026-08-15 because the previous extractor was
silently manufacturing wrong answers, and the fix needs to be testable without
importing a runner.

The old version was:

    match = _FENCE_RE.search(text)
    code = match.group(1) if match else text
    return code if "def " in code else None

The fallback in line two is the bug. A reply truncated at the output ceiling has
an *opening* fence and no closing one, so the fence regex does not match, so the
whole reply — including the literal "```python" prefix — became "the solution".
That is a guaranteed SyntaxError, and it was scored as the model getting the task
wrong. On the pilot's Gemini half that turned a config problem (a 1024-token
combined thinking+output ceiling, see config.MAX_OUTPUT_TOKENS_CODEGEN) into an
80% LBPP execution-failure rate that looked like model incompetence.

So: no fallback that accepts a partial fence, and `ast.parse` as the last gate,
because syntactically invalid text is never a solution and pretending otherwise
only moves the failure downstream into the sandbox where it is indistinguishable
from a genuine wrong answer. `ast.parse` only builds a tree; it does not execute
anything, and untrusted code still runs exclusively through pilot.sandbox.

Every rejection carries a reason, so "our ceiling cut the reply off" is
distinguishable in the output from "the model emitted something unparseable".
"""

import ast
import re

_FENCE_RE = re.compile(r"```(?:[a-zA-Z0-9_+-]*)\s*\n(.*?)```", re.DOTALL)
_FENCE_MARKER = "```"

# Rejection reasons, recorded per observation.
NO_REPLY = "no_reply"
TRUNCATED = "truncated_by_output_ceiling"
UNCLOSED_FENCE = "unclosed_code_fence"
NO_FUNCTION = "no_function_definition"
SYNTAX_ERROR = "syntax_error"


def extract_code(text: str | None, truncated: bool = False) -> tuple[str | None, str | None]:
    """Returns `(code, None)` on success or `(None, reason)` on rejection.

    `truncated` is the provider's own signal (see elicit.CallResult) and is
    checked first: a reply cut off at the ceiling says nothing about the model's
    ability, so it must not be reported under the same label as a bad answer.
    """
    if text is None:
        return None, NO_REPLY
    if truncated:
        return None, TRUNCATED

    match = _FENCE_RE.search(text)
    if match:
        code = match.group(1)
    elif _FENCE_MARKER in text:
        return None, UNCLOSED_FENCE
    else:
        code = text

    if "def " not in code:
        return None, NO_FUNCTION

    try:
        ast.parse(code)
    except (SyntaxError, ValueError, RecursionError, MemoryError):
        return None, SYNTAX_ERROR

    return code, None
