from app.modules.daily_challenge.content import PYTHON_CHALLENGE_POOL
from app.modules.daily_challenge.python_execution import run_python_submission


def test_every_reference_solution_in_the_pool_passes():
    references = {
        "dedupe_preserve_order": "def dedupe_preserve_order(items):\n"
        "    seen = set()\n    out = []\n"
        "    for x in items:\n"
        "        if x not in seen:\n"
        "            seen.add(x)\n            out.append(x)\n"
        "    return out\n",
        "total_amount": "def total_amount(transactions):\n    return sum(t['amount'] for t in transactions)\n",
        "group_by_key": "def group_by_key(records, key):\n"
        "    groups = {}\n"
        "    for r in records:\n"
        "        groups.setdefault(r[key], []).append(r)\n"
        "    return groups\n",
        "running_total": "def running_total(amounts):\n"
        "    out = []\n    total = 0\n"
        "    for a in amounts:\n        total += a\n        out.append(total)\n"
        "    return out\n",
        "dedupe_by_key_keep_latest": "def dedupe_by_key_keep_latest(records, key, timestamp_key):\n"
        "    winners = {}\n"
        "    for r in records:\n"
        "        existing = winners.get(r[key])\n"
        "        if existing is None or r[timestamp_key] > existing[timestamp_key]:\n"
        "            winners[r[key]] = r\n"
        "    return winners\n",
        "parse_fixed_width": "def parse_fixed_width(line, widths):\n"
        "    out = []\n    pos = 0\n"
        "    for w in widths:\n        out.append(line[pos:pos + w].strip())\n        pos += w\n"
        "    return out\n",
    }
    for problem in PYTHON_CHALLENGE_POOL:
        code = references[problem["function_name"]]
        result = run_python_submission(code, problem["function_name"], problem["test_cases"])
        assert result["passed"] is True, f"{problem['id']} failed: {result}"


def test_wrong_submission_fails_not_crashes():
    code = "def dedupe_preserve_order(items):\n    return items\n"  # doesn't dedupe at all
    test_cases = [{"args": [[1, 1, 2]], "expected": [1, 2]}]
    result = run_python_submission(code, "dedupe_preserve_order", test_cases)
    assert result["passed"] is False
    assert result["error_code"] is None


def test_runtime_error_returns_structured_error():
    code = "def broken(items):\n    return 1 / 0\n"
    result = run_python_submission(code, "broken", [{"args": [[]], "expected": None}])
    assert result["passed"] is False
    assert result["error_code"] is None
    assert result["results"][0]["error"]


def test_missing_function_returns_structured_error():
    code = "x = 1\n"
    result = run_python_submission(code, "does_not_exist", [{"args": [], "expected": None}])
    assert result["passed"] is False
    assert result["error_code"] is None
    assert result["results"][0]["error"]


def test_infinite_loop_times_out_instead_of_hanging():
    code = "def spin(x):\n    while True:\n        pass\n"
    result = run_python_submission(code, "spin", [{"args": [1], "expected": 1}])
    assert result["passed"] is False
    assert result["error_code"] in ("ERR_TIMEOUT", "ERR_RUNTIME")
