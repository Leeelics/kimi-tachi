#!/usr/bin/env python3
"""
Kimi-Tachi Workflow Tool

Execute multi-agent workflows via the plugin system.
Receives parameters from stdin, outputs results to stdout.

Usage:
    echo '{"task": "implement auth", "workflow_type": "feature"}' | python3 workflow.py
"""

import json
import sys
from pathlib import Path

# Add kimi-tachi to path if available
try:
    from kimi_tachi.config import KimiTachiConfig
    from kimi_tachi.orchestrator import ContextManager, HybridOrchestrator, WorkflowEngine

    KIMI_TACHI_AVAILABLE = True
except ImportError:
    KIMI_TACHI_AVAILABLE = False


def run_workflow(task: str, workflow_type: str = "auto", work_dir: str = ".") -> dict:
    """
    Run a kimi-tachi workflow.

    Args:
        task: Task description
        workflow_type: Type of workflow (auto, feature, bugfix, explore, refactor, quick)
        work_dir: Working directory

    Returns:
        Result dictionary with status, output, and metadata
    """
    if not KIMI_TACHI_AVAILABLE:
        return {
            "success": False,
            "error": "kimi-tachi not installed. Install with: pip install kimi-tachi",
            "output": "",
        }

    import asyncio

    async def async_run():
        work_path = Path(work_dir).resolve()

        # Initialize orchestrator
        _ = KimiTachiConfig.from_env()  # Ensure config is loaded
        orch = HybridOrchestrator(work_dir=work_path)
        ctx_manager = ContextManager(work_path)
        engine = WorkflowEngine(orch, ctx_manager)

        # Analyze task if auto
        if workflow_type == "auto":
            analysis = await orch.analyze_task_complexity(task)
            complexity = analysis.get("complexity", "medium")
            if complexity == "simple":
                workflow = engine.quick_fix
            elif complexity == "complex":
                workflow = engine.feature_implementation
            else:
                workflow = engine.bug_fix
        else:
            workflow = engine.get_workflow(workflow_type)
            if not workflow:
                return {
                    "success": False,
                    "error": f"Unknown workflow type: {workflow_type}",
                    "output": "",
                }

        # Execute workflow
        results = await engine.execute(workflow, task)

        # Build output
        output_lines = []
        output_lines.append(f"✨ Workflow completed: {workflow_type}")
        output_lines.append(f"📁 Working directory: {work_path}")
        output_lines.append("")

        for i, result in enumerate(results, 1):
            status = "✅" if result.returncode == 0 else "❌"
            output_lines.append(f"{i}. {status} {result.agent}: {result.task[:50]}...")

        output_lines.append("")
        output_lines.append(f"📊 Total steps: {len(results)}")

        # Save session
        ctx_manager.save()
        output_lines.append(f"💾 Session saved: {ctx_manager.session_id}")

        return {
            "success": True,
            "output": "\n".join(output_lines),
            "results": [
                {
                    "agent": r.agent,
                    "task": r.task,
                    "returncode": r.returncode,
                    "stdout": r.stdout[:500],  # Truncate for JSON
                }
                for r in results
            ],
        }

    return asyncio.run(async_run())


def main():
    """Main entry point - reads JSON from stdin, outputs JSON to stdout"""
    try:
        # Read parameters from stdin
        params = json.load(sys.stdin)

        task = params.get("task", "")
        workflow_type = params.get("workflow_type", "auto")
        work_dir = params.get("work_dir", ".")

        if not task:
            result = {"success": False, "error": "Missing required parameter: task", "output": ""}
        else:
            result = run_workflow(task, workflow_type, work_dir)

        # Output result as JSON
        print(json.dumps(result, indent=2))

        # Exit with appropriate code
        sys.exit(0 if result.get("success") else 1)

    except json.JSONDecodeError as e:
        print(json.dumps({"success": False, "error": f"Invalid JSON input: {e}", "output": ""}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"success": False, "error": f"Unexpected error: {e}", "output": ""}))
        sys.exit(1)


if __name__ == "__main__":
    main()
