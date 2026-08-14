"""Execution boundary for untrusted, model-generated code (DESIGN.md §8).

Never exec()/eval() model output in this process. Everything runs in a
subprocess with resource limits applied in the child, a parent-side
wall-clock timeout, and a fresh temp directory removed afterwards. Any
exception, timeout, or pre-execution rejection is ground truth `False`.
"""

import os
import resource
import shutil
import signal
import subprocess
import sys
import tempfile

from pilot import config


def _contains_banned_pattern(code: str) -> bool:
    return any(pattern in code for pattern in config.BANNED_SUBSTRINGS)


def _apply_resource_limits() -> None:
    resource.setrlimit(
        resource.RLIMIT_AS, (config.RLIMIT_AS_BYTES, config.RLIMIT_AS_BYTES)
    )
    resource.setrlimit(
        resource.RLIMIT_CPU, (config.RLIMIT_CPU_SECONDS, config.RLIMIT_CPU_SECONDS)
    )
    resource.setrlimit(
        resource.RLIMIT_NOFILE, (config.RLIMIT_NOFILE, config.RLIMIT_NOFILE)
    )


def run_solution(solution_code: str, asserts: list[str]) -> bool:
    """Runs `solution_code` followed by each statement in `asserts`.

    Returns True iff the sandboxed process exits 0 (every assert passed).
    Returns False on a banned-pattern rejection, any exception, or a
    wall-clock timeout — no exception ever propagates to the caller.
    """
    if _contains_banned_pattern(solution_code):
        return False

    script = solution_code + "\n\n" + "\n".join(asserts) + "\n"

    run_dir = None
    try:
        config.SANDBOX_TMP_DIR.mkdir(parents=True, exist_ok=True)
        run_dir = tempfile.mkdtemp(dir=config.SANDBOX_TMP_DIR)
        script_path = os.path.join(run_dir, "solution.py")
        with open(script_path, "w") as f:
            f.write(script)

        proc = subprocess.Popen(
            [sys.executable, script_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            preexec_fn=_apply_resource_limits,
            start_new_session=True,
        )
        try:
            returncode = proc.wait(timeout=config.WALLCLOCK_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            proc.wait()
            return False

        return returncode == 0
    except Exception:
        return False
    finally:
        if run_dir is not None:
            shutil.rmtree(run_dir, ignore_errors=True)
