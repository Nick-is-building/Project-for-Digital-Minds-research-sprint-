"""Five required checks on the execution boundary (DESIGN.md §8)."""

import time
from unittest.mock import patch

from pilot import sandbox

CORRECT_SOLUTION = "def add(a, b):\n    return a + b\n"
WRONG_SOLUTION = "def add(a, b):\n    return a - b\n"
INFINITE_LOOP_SOLUTION = "def add(a, b):\n    while True:\n        pass\n"
MEMORY_BOMB_SOLUTION = "def add(a, b):\n    x = [0] * (10 ** 12)\n    return a + b\n"
IMPORT_OS_SOLUTION = "import os\n\ndef add(a, b):\n    return a + b\n"

ASSERTS = ["assert add(1, 2) == 3"]


def test_correct_solution_passes():
    assert sandbox.run_solution(CORRECT_SOLUTION, ASSERTS) is True


def test_wrong_solution_fails():
    assert sandbox.run_solution(WRONG_SOLUTION, ASSERTS) is False


def test_infinite_loop_times_out_within_15s():
    start = time.monotonic()
    result = sandbox.run_solution(INFINITE_LOOP_SOLUTION, ASSERTS)
    elapsed = time.monotonic() - start
    assert result is False
    assert elapsed < 15


def test_memory_bomb_returns_false_without_killing_parent():
    result = sandbox.run_solution(MEMORY_BOMB_SOLUTION, ASSERTS)
    assert result is False
    # If we reach this line, the parent process (running this test) is alive.


def test_import_os_rejected_before_execution():
    with patch("pilot.sandbox.subprocess.Popen") as mock_popen:
        result = sandbox.run_solution(IMPORT_OS_SOLUTION, ASSERTS)
    assert result is False
    mock_popen.assert_not_called()
