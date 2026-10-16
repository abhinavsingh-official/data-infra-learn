"""Runs a learner's submitted Python function and grades its return
value against a set of test cases. Neither node_practice.py nor
mongo_node_practice.py executes arbitrary code - they run submitted SQL
text or a JSON Mongo command against a real, role-isolated database - so
this module handles code execution on its own.

Runs in a fresh subprocess (python -I -c <script>), not exec() in-process
- a crash or infinite loop in submitted code can't take down the FastAPI
process, and a hard wall-clock timeout via subprocess.run(timeout=...)
kills it outright. A CPU-time rlimit is set as a second layer. This isn't
a full per-submission container (Docker/gVisor/etc.) - this is a local,
single-user project, not a multi-tenant code judge grading adversarial
strangers' code, so the isolation is scoped to that threat model rather
than maximal sandboxing for its own sake."""

import json
import resource
import subprocess
import sys

TIMEOUT_SECONDS = 5
CPU_TIME_LIMIT_SECONDS = 5
RESULT_MARKER = "__DAILY_CHALLENGE_RESULT__"


def _limit_resources() -> None:
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_TIME_LIMIT_SECONDS, CPU_TIME_LIMIT_SECONDS))


def _build_script(code: str, function_name: str, test_cases: list[dict]) -> str:
    # Embedding the test cases as a JSON-encoded *string literal* (not
    # splicing Python values directly into the template) avoids any
    # quoting/escaping hazard from a test case's own content.
    test_cases_literal = json.dumps(json.dumps(test_cases))
    return (
        code
        + "\n\n"
        + "import json as _json\n"
        + f"_test_cases = _json.loads({test_cases_literal})\n"
        + "_results = []\n"
        + "for _tc in _test_cases:\n"
        + "    try:\n"
        + f"        _actual = {function_name}(*_tc['args'])\n"
        + "        _results.append({'passed': _actual == _tc['expected'], 'actual': _actual})\n"
        + "    except Exception as _e:\n"
        + "        _results.append({'passed': False, 'error': str(_e)})\n"
        + f"print({RESULT_MARKER!r} + _json.dumps(_results))\n"
    )


def run_python_submission(code: str, function_name: str, test_cases: list[dict]) -> dict:
    """Runs `code` (expected to define `function_name`) against each test
    case's `args`/`expected`, in a fresh subprocess. Always returns a
    structured result - never raises, mirroring node_practice.py's own
    never-crash contract for a bad SQL submission."""
    script = _build_script(code, function_name, test_cases)

    try:
        proc = subprocess.run(
            [sys.executable, "-I", "-c", script],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            preexec_fn=_limit_resources,
        )
    except subprocess.TimeoutExpired:
        return {
            "passed": False,
            "error_code": "ERR_TIMEOUT",
            "error_message": f"Submission didn't finish within {TIMEOUT_SECONDS} seconds.",
            "results": [],
        }

    if proc.returncode != 0:
        stderr_lines = proc.stderr.strip().splitlines()
        last_line = stderr_lines[-1] if stderr_lines else "The submission crashed with no error output."
        return {"passed": False, "error_code": "ERR_RUNTIME", "error_message": last_line, "results": []}

    result_line = next((line for line in proc.stdout.splitlines() if line.startswith(RESULT_MARKER)), None)
    if result_line is None:
        return {
            "passed": False,
            "error_code": "ERR_NO_OUTPUT",
            "error_message": f"Expected a function named '{function_name}' - none was found, or it never ran.",
            "results": [],
        }

    results = json.loads(result_line[len(RESULT_MARKER):])
    all_passed = bool(results) and all(r.get("passed") for r in results)
    return {"passed": all_passed, "error_code": None, "error_message": None, "results": results}
