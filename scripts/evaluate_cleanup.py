#!/usr/bin/env python3
"""
Kimi-Tachi Cleanup Evaluation Script

Runs regression checks and measures plan quality before/after cleanup.
Helps answer: "Is this an optimization or a degradation?"
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
SRC_DIR = PROJECT_ROOT / "src" / "kimi_tachi"


PYTHON = str(PROJECT_ROOT / ".venv" / "bin" / "python")


def run(cmd: list[str], timeout: int = 120) -> tuple[int, str, str]:
    proc = subprocess.run(
        cmd,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return proc.returncode, proc.stdout, proc.stderr


def eval_tests() -> dict:
    code, out, err = run(["make", "test"], timeout=180)
    passed = "passed" in out and "failed" not in out.lower().split("passed")[-1][:20]
    return {
        "name": "pytest",
        "passed": code == 0 and passed,
        "details": f"exit={code}, output={out[-500:]}",
    }


def eval_ruff() -> dict:
    code, out, err = run(["make", "check"], timeout=60)
    return {
        "name": "ruff_check",
        "passed": code == 0,
        "details": f"exit={code}",
    }


def eval_build() -> dict:
    code, out, err = run(["make", "build"], timeout=120)
    return {
        "name": "build",
        "passed": code == 0,
        "details": f"exit={code}",
    }


def eval_dead_code() -> dict:
    """Check that dead modules are actually gone."""
    dead_paths = [
        SRC_DIR / "config.py",
        SRC_DIR / "message_bus",
        SRC_DIR / "metrics",
        SRC_DIR / "adapters",
        SRC_DIR / "tracing" / "metrics.py",
        SRC_DIR / "memory" / "tachi_memory_v2.py",
    ]
    found = [str(p) for p in dead_paths if p.exists()]
    return {
        "name": "dead_code_removed",
        "passed": len(found) == 0,
        "details": f"remaining: {found}" if found else "all cleared",
    }


def eval_lines_of_code() -> dict:
    code, out, _ = run(
        [
            PYTHON,
            "-c",
            f"import pathlib; files=list(pathlib.Path('{SRC_DIR}').rglob('*.py')); total=sum(len(f.read_text().splitlines()) for f in files); print(total)",
        ]
    )
    try:
        total = int(out.strip().splitlines()[-1])
    except (ValueError, IndexError):
        total = 0
    return {
        "name": "lines_of_code",
        "passed": True,
        "details": f"{total} lines in src/kimi_tachi/",
    }


def eval_workflow_plan() -> dict:
    """Benchmark workflow.py output quality."""
    code, out, err = run(
        [
            PYTHON,
            "-c",
            "import sys; sys.path.insert(0, 'src'); sys.path.insert(0, 'plugins/kimi-tachi/scripts'); "
            "from workflow import generate_workflow_plan; print('OK')",
        ],
        timeout=30,
    )
    if code != 0:
        return {"name": "workflow_plan", "passed": False, "details": err or out}
    # Now import in-process using the same Python (we are already running under .venv python if launched correctly)
    # Fallback: exec the function via subprocess and capture JSON result
    tasks = [
        ("fix typo in readme", "auto"),
        ("implement user authentication with jwt", "auto"),
    ]
    checks = []
    for task, wtype in tasks:
        code, out, err = run(
            [
                PYTHON,
                "-c",
                "import json, sys; sys.path.insert(0, 'src'); sys.path.insert(0, 'plugins/kimi-tachi/scripts'); "
                "from workflow import generate_workflow_plan; "
                f"r=generate_workflow_plan({task!r}, {wtype!r}); "
                "print(json.dumps(r, default=str))",
            ],
            timeout=30,
        )
        if code != 0:
            checks.append({"task": task, "ok": False, "error": err or out})
            continue
        plan = json.loads(out)
        ok = (
            plan.get("success") is True
            and "phases" in plan
            and "recommendations" in plan
            and "parallel_steps" in plan["recommendations"]
            and "plan_mode_reason" in plan["recommendations"]
            and all(
                "subagent_type" in p
                and "recommended_timeout" in p
                and "can_background" in p
                and "resume" in p
                for p in plan.get("phases", [])
            )
        )
        checks.append({"task": task, "ok": ok, "phases": len(plan.get("phases", []))})

    all_ok = all(c["ok"] for c in checks)
    return {
        "name": "workflow_plan",
        "passed": all_ok,
        "details": checks,
    }


def eval_subagent_type_mapping() -> dict:
    """Ensure workflow.py outputs valid builtin subagent types, not anime names."""
    valid_types = {"coder", "explore", "plan"}
    code, out, err = run(
        [
            PYTHON,
            "-c",
            "import json, sys; sys.path.insert(0, 'src'); sys.path.insert(0, 'plugins/kimi-tachi/scripts'); "
            "from workflow import generate_workflow_plan; "
            "r=generate_workflow_plan('refactor auth module', 'feature'); "
            "print(json.dumps(r, default=str))",
        ],
        timeout=30,
    )
    if code != 0:
        return {"name": "subagent_type_mapping", "passed": False, "details": err or out}
    plan = json.loads(out)
    invalid = [
        p["subagent_type"]
        for p in plan.get("phases", [])
        if p.get("subagent_type") not in valid_types
    ]
    return {
        "name": "subagent_type_mapping",
        "passed": len(invalid) == 0,
        "details": f"invalid types: {invalid}" if invalid else "all valid",
    }


def main():
    evaluators = [
        eval_tests,
        eval_ruff,
        eval_build,
        eval_dead_code,
        eval_lines_of_code,
        eval_workflow_plan,
        eval_subagent_type_mapping,
    ]

    results = []
    for fn in evaluators:
        try:
            results.append(fn())
        except Exception as e:
            results.append({"name": fn.__name__, "passed": False, "details": str(e)})

    all_passed = all(r["passed"] for r in results)
    report = {
        "overall_passed": all_passed,
        "results": results,
    }

    print(json.dumps(report, indent=2, default=str))
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
