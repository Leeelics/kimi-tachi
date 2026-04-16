"""Unit tests for the workflow orchestrator module."""

from __future__ import annotations

from kimi_tachi.orchestrator.plan import WorkflowPhase, WorkflowPlan


class TestWorkflowPhase:
    def test_to_dict_includes_all_fields(self):
        phase = WorkflowPhase(
            agent="nekobasu",
            description="Explore codebase",
            prompt="Find auth code",
            subagent_type="explore",
            can_background=False,
            recommended_timeout=300,
            resume=None,
            model=None,
        )
        d = phase.to_dict()
        assert d["agent"] == "nekobasu"
        assert d["description"] == "Explore codebase"
        assert d["prompt"] == "Find auth code"
        assert d["subagent_type"] == "explore"
        assert d["can_background"] is False
        assert d["recommended_timeout"] == 300
        assert "resume" in d
        assert d["resume"] is None
        assert "model" not in d

    def test_to_dict_with_optional_fields(self):
        phase = WorkflowPhase(
            agent="calcifer",
            description="Implement feature",
            prompt="Write code",
            subagent_type="coder",
            can_background=True,
            recommended_timeout=600,
            resume="a1b2c3d4",
            model="kimi-k2.5",
        )
        d = phase.to_dict()
        assert d["resume"] == "a1b2c3d4"
        assert d["model"] == "kimi-k2.5"


class TestWorkflowPlan:
    def test_to_dict_success(self):
        phases = [
            WorkflowPhase(
                agent="tasogare",
                description="Plan",
                prompt="Plan it",
                subagent_type="plan",
                can_background=True,
                recommended_timeout=300,
            ),
            WorkflowPhase(
                agent="nekobasu",
                description="Explore",
                prompt="Explore it",
                subagent_type="explore",
                can_background=True,
                recommended_timeout=300,
            ),
        ]
        plan = WorkflowPlan(
            success=True,
            workflow_type="feature",
            team="coding",
            task="implement auth",
            work_dir=".",
            complexity="complex",
            phases=phases,
            parallel_batches=[[0, 1]],
            recommendations={"use_plan_mode": True},
            output="Plan generated",
        )
        d = plan.to_dict()
        assert d["success"] is True
        assert d["workflow_type"] == "feature"
        assert d["team"] == "coding"
        assert d["task"] == "implement auth"
        assert d["complexity"] == "complex"
        assert len(d["phases"]) == 2
        assert d["recommendations"]["use_plan_mode"] is True
        assert d["output"] == "Plan generated"
        assert "error" not in d

    def test_to_dict_with_error(self):
        plan = WorkflowPlan(
            success=False,
            workflow_type="unknown",
            team="coding",
            task="",
            work_dir=".",
            complexity="unknown",
            phases=[],
            parallel_batches=[],
            recommendations={},
            output="",
            error="Missing task",
        )
        d = plan.to_dict()
        assert d["success"] is False
        assert d["error"] == "Missing task"

    def test_execution_batches(self):
        phases = [
            WorkflowPhase("a1", "d1", "p1", "plan", True, 300),
            WorkflowPhase("a2", "d2", "p2", "explore", True, 300),
            WorkflowPhase("a3", "d3", "p3", "coder", False, 600),
        ]
        plan = WorkflowPlan(
            success=True,
            workflow_type="feature",
            team="coding",
            task="t",
            work_dir=".",
            complexity="medium",
            phases=phases,
            parallel_batches=[[0, 1], [2]],
            recommendations={},
            output="o",
        )
        batches = plan.execution_batches()
        assert len(batches) == 2
        assert [p.agent for p in batches[0]] == ["a1", "a2"]
        assert [p.agent for p in batches[1]] == ["a3"]

    def test_execution_batches_empty(self):
        plan = WorkflowPlan(
            success=True,
            workflow_type="quick",
            team="coding",
            task="t",
            work_dir=".",
            complexity="simple",
            phases=[],
            parallel_batches=[],
            recommendations={},
            output="o",
        )
        assert plan.execution_batches() == []
