"""Unit tests for the workflow execution engine."""

from __future__ import annotations

from kimi_tachi.orchestrator.executor import ExecutionState, execute_workflow
from kimi_tachi.orchestrator.plan import WorkflowPhase, WorkflowPlan


def _make_plan(phases: list[WorkflowPhase], parallel_batches: list[list[int]]) -> WorkflowPlan:
    return WorkflowPlan(
        success=True,
        workflow_type="feature",
        team="coding",
        task="test task",
        work_dir=".",
        complexity="medium",
        phases=phases,
        parallel_batches=parallel_batches,
        recommendations={},
        output="plan output",
        todo_items=[{"title": f"{p.agent}: {p.description}", "status": "pending"} for p in phases],
    )


class TestExecuteWorkflow:
    def test_error_when_plan_not_successful(self):
        plan = WorkflowPlan(
            success=False,
            workflow_type="auto",
            team="coding",
            task="",
            work_dir=".",
            complexity="unknown",
            phases=[],
            parallel_batches=[],
            recommendations={},
            output="",
            error="bad plan",
        )
        state = ExecutionState()
        result = execute_workflow(plan, state)

        assert result.action == "error"
        assert result.error == "bad plan"

    def test_complete_when_no_phases(self):
        plan = _make_plan(phases=[], parallel_batches=[])
        state = ExecutionState()
        result = execute_workflow(plan, state)

        assert result.action == "complete"

    def test_spawn_single_phase(self):
        phases = [
            WorkflowPhase(
                agent="calcifer",
                description="Do work",
                prompt="Work hard",
                subagent_type="coder",
                can_background=False,
                recommended_timeout=300,
            ),
        ]
        plan = _make_plan(phases, [[0]])
        state = ExecutionState()
        result = execute_workflow(plan, state)

        assert result.action == "spawn"
        assert len(result.spawn) == 1
        assert result.spawn[0].agent == "calcifer"
        assert result.spawn[0].phase_index == 0
        assert result.spawn[0].resume is None
        assert len(result.todo_updates) == 1
        assert result.todo_updates[0]["status"] == "in_progress"

    def test_spawn_parallel_phases(self):
        phases = [
            WorkflowPhase(
                agent="nekobasu",
                description="Explore",
                prompt="Find files",
                subagent_type="explore",
                can_background=False,
                recommended_timeout=300,
            ),
            WorkflowPhase(
                agent="tasogare",
                description="Plan",
                prompt="Plan task",
                subagent_type="plan",
                can_background=False,
                recommended_timeout=300,
            ),
        ]
        plan = _make_plan(phases, [[0, 1]])
        state = ExecutionState()
        result = execute_workflow(plan, state)

        assert result.action == "spawn"
        assert len(result.spawn) == 2
        agents = {s.agent for s in result.spawn}
        assert agents == {"nekobasu", "tasogare"}
        assert all(s.resume is None for s in result.spawn)
        assert len(result.todo_updates) == 2
        assert all(u["status"] == "in_progress" for u in result.todo_updates)

    def test_advance_to_next_batch_after_first_completed(self):
        phases = [
            WorkflowPhase(
                agent="nekobasu",
                description="Explore",
                prompt="Find files",
                subagent_type="explore",
                can_background=False,
                recommended_timeout=300,
            ),
            WorkflowPhase(
                agent="calcifer",
                description="Implement",
                prompt="Write code",
                subagent_type="coder",
                can_background=False,
                recommended_timeout=300,
            ),
        ]
        plan = _make_plan(phases, [[0], [1]])
        state = ExecutionState(completed_phase_indices=[0], current_batch_index=1)
        result = execute_workflow(plan, state)

        assert result.action == "spawn"
        assert len(result.spawn) == 1
        assert result.spawn[0].agent == "calcifer"
        assert result.todo_updates[0]["status"] == "done"
        assert result.todo_updates[1]["status"] == "in_progress"

    def test_complete_after_all_batches_done(self):
        phases = [
            WorkflowPhase(
                agent="calcifer",
                description="Do work",
                prompt="Work",
                subagent_type="coder",
                can_background=False,
                recommended_timeout=300,
            ),
        ]
        plan = _make_plan(phases, [[0]])
        state = ExecutionState(completed_phase_indices=[0], current_batch_index=1)
        result = execute_workflow(plan, state)

        assert result.action == "complete"
        assert result.todo_updates[0]["status"] == "done"

    def test_wait_for_background_tasks_at_end(self):
        phases = [
            WorkflowPhase(
                agent="tasogare",
                description="Plan",
                prompt="Plan",
                subagent_type="plan",
                can_background=True,
                recommended_timeout=300,
            ),
        ]
        plan = _make_plan(phases, [[0]])
        state = ExecutionState(
            completed_phase_indices=[],
            background_tasks=["bg_123"],
            current_batch_index=1,
        )
        result = execute_workflow(plan, state)

        assert result.action == "wait"
        assert result.wait_tasks == ["bg_123"]

    def test_wait_for_background_tasks_before_next_batch(self):
        """Background tasks must block subsequent batches even if not at end."""
        phases = [
            WorkflowPhase(
                agent="tasogare",
                description="Plan",
                prompt="Plan",
                subagent_type="plan",
                can_background=True,
                recommended_timeout=300,
            ),
            WorkflowPhase(
                agent="calcifer",
                description="Implement",
                prompt="Write code",
                subagent_type="coder",
                can_background=False,
                recommended_timeout=300,
            ),
        ]
        plan = _make_plan(phases, [[0], [1]])
        # Batch 0 spawned in background, batch index advanced to 1
        state = ExecutionState(
            completed_phase_indices=[],
            background_tasks=["bg_123"],
            current_batch_index=1,
        )
        result = execute_workflow(plan, state)

        assert result.action == "wait"
        assert result.wait_tasks == ["bg_123"]

    def test_resume_when_same_agent_consecutive(self):
        phases = [
            WorkflowPhase(
                agent="nekobasu",
                description="Explore 1",
                prompt="Find files",
                subagent_type="explore",
                can_background=False,
                recommended_timeout=300,
            ),
            WorkflowPhase(
                agent="nekobasu",
                description="Explore 2",
                prompt="Analyze files",
                subagent_type="explore",
                can_background=False,
                recommended_timeout=300,
            ),
        ]
        plan = _make_plan(phases, [[0], [1]])
        state = ExecutionState(
            completed_phase_indices=[0],
            agent_ids={"0": "agent_abc"},
            current_batch_index=1,
        )
        result = execute_workflow(plan, state)

        assert result.action == "spawn"
        assert len(result.spawn) == 1
        assert result.spawn[0].agent == "nekobasu"
        assert result.spawn[0].resume == "agent_abc"

    def test_no_resume_when_previous_not_completed(self):
        phases = [
            WorkflowPhase(
                agent="nekobasu",
                description="Explore 1",
                prompt="Find files",
                subagent_type="explore",
                can_background=False,
                recommended_timeout=300,
            ),
            WorkflowPhase(
                agent="nekobasu",
                description="Explore 2",
                prompt="Analyze files",
                subagent_type="explore",
                can_background=False,
                recommended_timeout=300,
            ),
        ]
        plan = _make_plan(phases, [[0, 1]])
        state = ExecutionState()
        result = execute_workflow(plan, state)

        # Both phases in same batch, neither completed
        assert result.action == "spawn"
        assert all(s.resume is None for s in result.spawn)
