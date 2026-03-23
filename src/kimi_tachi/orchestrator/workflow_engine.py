"""
Workflow Engine: Predefined workflows and patterns
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum

from ..message_bus import MessageBus
from ..metrics import MetricsCollector
from .context_manager import ContextManager
from .dependency_analyzer import TaskDependencyAnalyzer
from .hybrid_orchestrator import AgentResult, HybridOrchestrator
from .parallel_scheduler import ParallelScheduler


class WorkflowPhase(Enum):
    """Standard workflow phases"""

    IDLE = "idle"
    PLANNING = "planning"
    EXPLORATION = "exploration"
    ARCHITECTURE = "architecture"
    IMPLEMENTATION = "implementation"
    REVIEW = "review"
    DOCUMENTATION = "documentation"
    COMPLETE = "complete"


@dataclass
class Phase:
    """Workflow phase definition"""

    name: str
    agent: str
    task_template: str
    condition: Callable[[list[AgentResult]], bool] | None = None
    parallel: bool = False
    dependencies: list[str] = field(default_factory=list)  # ← 新增：依赖的 phase 名称列表


@dataclass
class Workflow:
    """Workflow definition"""

    name: str
    description: str
    phases: list[Phase]
    on_complete: Callable[[list[AgentResult]], None] | None = None


class WorkflowEngine:
    """
    Predefined workflow patterns for common tasks.

    Supports parallel execution with dependency analysis.
    """

    def __init__(
        self,
        orchestrator: HybridOrchestrator,
        context_manager: ContextManager | None = None,
        message_bus: MessageBus | None = None,
        metrics_collector: MetricsCollector | None = None,
        use_parallel: bool = True,
        max_parallel: int = 2,
    ):
        self.orch = orchestrator
        self.ctx = context_manager
        self.bus = message_bus
        self.metrics = metrics_collector
        self.use_parallel = use_parallel
        self.max_parallel = max_parallel

        # Initialize components
        self.dependency_analyzer = TaskDependencyAnalyzer()
        self.parallel_scheduler = ParallelScheduler(
            orchestrator=orchestrator,
            message_bus=message_bus,
            metrics_collector=metrics_collector,
            max_parallel=max_parallel,
        ) if use_parallel else None

    async def execute(self, workflow: Workflow, task: str) -> list[AgentResult]:
        """
        Execute a workflow with parallel phase support.

        If use_parallel is True, uses dependency analysis and parallel scheduling.
        Otherwise, falls back to the original sequential execution.
        """
        print(f"\n{'=' * 60}")
        print(f"◕‿◕ Workflow: {workflow.name}")
        print(f"📋 {workflow.description}")
        if self.use_parallel:
            print(f"⚡ Mode: Parallel (max={self.max_parallel})")
        else:
            print("⚡ Mode: Sequential")
        print(f"{'=' * 60}\n")

        if self.use_parallel and self.parallel_scheduler:
            # Use new parallel execution with dependency analysis
            return await self._execute_parallel(workflow, task)
        else:
            # Fall back to original sequential execution
            return await self._execute_sequential(workflow, task)

    async def _execute_parallel(self, workflow: Workflow, task: str) -> list[AgentResult]:
        """Execute workflow using parallel scheduler"""
        # Build dependency graph
        explicit_deps = {
            p.name: p.dependencies for p in workflow.phases if p.dependencies
        }

        graph = self.dependency_analyzer.analyze(
            phases=workflow.phases,
            explicit_dependencies=explicit_deps,
        )

        # Analyze and print suggestions
        analysis = self.dependency_analyzer.suggest_parallelization(graph)
        print("📊 Parallel Analysis:")
        print(f"   Parallel ratio: {analysis['parallel_ratio']:.1%}")
        print(f"   Estimated time reduction: {analysis['estimated_time_reduction']}")
        if analysis['recommendations']:
            print("   Recommendations:")
            for rec in analysis['recommendations']:
                print(f"      • {rec}")
        print()

        # Execute using parallel scheduler
        results = await self.parallel_scheduler.execute_plan(
            graph=graph,
            phases=workflow.phases,
            task=task,
        )

        # Mark complete
        if self.ctx:
            self.ctx.update_phase(WorkflowPhase.COMPLETE.value)

        if workflow.on_complete:
            workflow.on_complete(results)

        return results

    async def _execute_sequential(self, workflow: Workflow, task: str) -> list[AgentResult]:
        """Original sequential execution"""
        results: list[AgentResult] = []
        completed_phases: dict[str, AgentResult] = {}

        # Group phases by execution batch ( respecting dependencies )
        batches = self._build_execution_batches(workflow.phases)

        for batch_idx, batch in enumerate(batches, 1):
            if len(batch) == 1:
                # Single phase - sequential execution
                phase = batch[0]
                await self._execute_phase(phase, task, results, completed_phases)
            else:
                # Multiple phases - parallel execution
                print(f"\n🏃 Batch {batch_idx}: Parallel execution of {len(batch)} phases")
                for phase in batch:
                    print(f"   • {phase.name} ({self.orch.AGENT_MAP[phase.agent]['name']})")

                # Execute in parallel
                batch_results = await self._execute_batch_parallel(batch, task, completed_phases)
                results.extend(batch_results)

                # Update completed phases
                for phase, result in zip(batch, batch_results, strict=False):
                    completed_phases[phase.name] = result

        # Mark complete
        if self.ctx:
            self.ctx.update_phase(WorkflowPhase.COMPLETE.value)

        if workflow.on_complete:
            workflow.on_complete(results)

        return results

    def _build_execution_batches(self, phases: list[Phase]) -> list[list[Phase]]:
        """
        Group phases into execution batches based on dependencies.
        Phases in the same batch can execute in parallel.
        """
        phase_map = {p.name: p for p in phases}
        completed = set()
        batches = []
        remaining = {p.name for p in phases}

        while remaining:
            # Find phases whose dependencies are all satisfied
            ready = []
            for name in remaining:
                phase = phase_map[name]
                deps_satisfied = all(
                    dep in completed or dep not in phase_map for dep in phase.dependencies
                )
                if deps_satisfied:
                    ready.append(phase)

            if not ready:
                # Circular dependency or missing dependency
                # Fall back to sequential
                ready = [phase_map[name] for name in remaining]

            batches.append(ready)
            for phase in ready:
                completed.add(phase.name)
                remaining.remove(phase.name)

        return batches

    async def _execute_phase(
        self,
        phase: Phase,
        task: str,
        results: list[AgentResult],
        completed_phases: dict[str, AgentResult],
    ) -> AgentResult:
        """Execute a single phase"""
        # Check condition
        if phase.condition and not phase.condition(results):
            return None

        # Update context
        if self.ctx:
            self.ctx.update_phase(phase.name)

        # Build context from completed phases
        context = self._build_phase_context(phase, completed_phases)

        # Format task
        formatted_task = phase.task_template.format(original_task=task, context=context)

        print(f"\n▶️ Phase: {phase.name} ({self.orch.AGENT_MAP[phase.agent]['name']})")

        # Execute
        result = await self.orch.delegate(phase.agent, formatted_task)
        results.append(result)
        completed_phases[phase.name] = result

        # Record in context
        if self.ctx:
            self.ctx.add_decision(
                f"Completed {phase.name}", phase.agent, f"Return code: {result.returncode}"
            )

        # Check for failure
        if result.returncode != 0:
            print(f"⚠️ Phase {phase.name} failed!")

        return result

    async def _execute_batch_parallel(
        self, batch: list[Phase], task: str, completed_phases: dict[str, AgentResult]
    ) -> list[AgentResult]:
        """Execute a batch of phases in parallel"""

        async def run_phase(phase: Phase) -> AgentResult:
            # Build context
            context = self._build_phase_context(phase, completed_phases)

            # Format task
            formatted_task = phase.task_template.format(original_task=task, context=context)

            # Execute
            result = await self.orch.delegate(phase.agent, formatted_task)

            # Record in context
            if self.ctx:
                self.ctx.add_decision(
                    f"Completed {phase.name}", phase.agent, f"Return code: {result.returncode}"
                )

            return result

        # Run all phases in parallel
        tasks = [run_phase(phase) for phase in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions and failures
        processed_results = []
        for phase, result in zip(batch, results, strict=False):
            if isinstance(result, Exception):
                print(f"⚠️ Phase {phase.name} crashed: {result}")
                # Create failed result
                from .hybrid_orchestrator import AgentResult

                result = AgentResult(
                    agent=phase.agent, task="", stdout="", stderr=str(result), returncode=-1
                )
            elif result.returncode != 0:
                print(f"⚠️ Phase {phase.name} failed!")

            processed_results.append(result)

        return processed_results

    def _build_phase_context(self, phase: Phase, completed_phases: dict[str, AgentResult]) -> str:
        """Build context from completed dependency phases"""
        parts = []

        # Add shared context
        if self.ctx:
            parts.append(self.ctx.build_context_prompt())

        # Add results from dependencies
        if phase.dependencies and completed_phases:
            parts.append("\n## Results from Previous Phases\n")
            for dep_name in phase.dependencies:
                if dep_name in completed_phases:
                    result = completed_phases[dep_name]
                    parts.append(f"\n### {dep_name} ({result.agent})\n")
                    parts.append(result.stdout[:500])  # Truncate long outputs
                    if result.returncode != 0:
                        parts.append(f"\n⚠️ Note: This phase had errors: {result.stderr[:200]}")

        return "\n".join(parts)

    async def _should_continue(self, results: list[AgentResult]) -> bool:
        """Ask whether to continue after failure"""
        # For now, always continue
        # Could use SDK to make smarter decisions
        return True

    # Predefined workflows

    @property
    def feature_implementation(self) -> Workflow:
        """Complete feature implementation workflow"""
        return Workflow(
            name="Feature Implementation",
            description="Full workflow for implementing new features",
            phases=[
                Phase(
                    name="planning",
                    agent="tasogare",
                    task_template="""Create detailed implementation plan for:
{original_task}

{context}

Provide:
1. Step-by-step plan
2. Files to modify/create
3. Dependencies to consider
4. Potential risks""",
                    parallel=True,  # ← 可与 exploration 并行
                ),
                Phase(
                    name="exploration",
                    agent="nekobasu",
                    task_template="""Explore codebase to understand:
{original_task}

{context}

Find:
1. Relevant existing code
2. Similar implementations
3. Patterns to follow
4. Test locations""",
                    parallel=True,  # ← 可与 planning 并行
                ),
                Phase(
                    name="architecture",
                    agent="shishigami",
                    task_template="""Design architecture for:
{original_task}

{context}

Provide:
1. Component design
2. Interface definitions
3. Data flow
4. Integration points""",
                    dependencies=["exploration"],  # ← 依赖 exploration 结果
                    condition=lambda results: len(results) >= 2,
                ),
                Phase(
                    name="implementation",
                    agent="calcifer",
                    task_template="""Implement:
{original_task}

{context}

Follow the plan and architecture above. Implement all necessary code with tests.""",
                    dependencies=["architecture"],  # ← 依赖 architecture 结果
                ),
                Phase(
                    name="review",
                    agent="enma",
                    task_template="""Review implementation of:
{original_task}

{context}

Check:
1. Code quality
2. Test coverage
3. Edge cases
4. Documentation
5. Potential bugs""",
                    dependencies=["implementation"],  # ← 依赖 implementation 结果
                ),
            ],
        )

    @property
    def bug_fix(self) -> Workflow:
        """Bug fix workflow"""
        return Workflow(
            name="Bug Fix",
            description="Analyze and fix bugs",
            phases=[
                Phase(
                    name="exploration",
                    agent="nekobasu",
                    task_template="""Find the bug:
{original_task}

{context}

Locate the relevant code and understand the issue.""",
                ),
                Phase(
                    name="implementation",
                    agent="calcifer",
                    task_template="""Fix the bug:
{original_task}

{context}

Implement the fix and add regression tests.""",
                ),
                Phase(
                    name="review",
                    agent="enma",
                    task_template="""Review the bug fix:
{original_task}

{context}

Verify the fix is correct and doesn't introduce new issues.""",
                ),
            ],
        )

    @property
    def code_exploration(self) -> Workflow:
        """Code exploration workflow"""
        return Workflow(
            name="Code Exploration",
            description="Deep dive into codebase",
            phases=[
                Phase(
                    name="exploration",
                    agent="nekobasu",
                    task_template="""Explore:
{original_task}

{context}

Provide comprehensive analysis of the codebase structure and patterns.""",
                ),
                Phase(
                    name="documentation",
                    agent="phoenix",
                    task_template="""Document findings for:
{original_task}

{context}

Create clear documentation of the codebase architecture and findings.""",
                ),
            ],
        )

    @property
    def refactor(self) -> Workflow:
        """Code refactoring workflow"""
        return Workflow(
            name="Refactoring",
            description="Safe code refactoring",
            phases=[
                Phase(
                    name="exploration",
                    agent="nekobasu",
                    task_template="""Understand code to refactor:
{original_task}

{context}

Identify all dependencies and usages.""",
                ),
                Phase(
                    name="architecture",
                    agent="shishigami",
                    task_template="""Design refactoring plan:
{original_task}

{context}

Ensure backward compatibility and minimal disruption.""",
                ),
                Phase(
                    name="implementation",
                    agent="calcifer",
                    task_template="""Execute refactoring:
{original_task}

{context}

Apply changes safely with comprehensive tests.""",
                ),
                Phase(
                    name="review",
                    agent="enma",
                    task_template="""Review refactoring:
{original_task}

{context}

Verify no regressions and code quality improved.""",
                ),
            ],
        )

    @property
    def quick_fix(self) -> Workflow:
        """Quick fix for simple tasks"""
        return Workflow(
            name="Quick Fix",
            description="Fast implementation for simple tasks",
            phases=[
                Phase(
                    name="implementation",
                    agent="calcifer",
                    task_template="""Quickly implement:
{original_task}

{context}

Make minimal, focused changes.""",
                ),
            ],
        )

    def get_workflow(self, name: str) -> Workflow | None:
        """Get workflow by name"""
        workflows = {
            "feature": self.feature_implementation,
            "bugfix": self.bug_fix,
            "explore": self.code_exploration,
            "refactor": self.refactor,
            "quick": self.quick_fix,
        }
        return workflows.get(name.lower())

    def list_workflows(self) -> list[dict]:
        """List available workflows"""
        return [
            {"name": "feature", "description": self.feature_implementation.description},
            {"name": "bugfix", "description": self.bug_fix.description},
            {"name": "explore", "description": self.code_exploration.description},
            {"name": "refactor", "description": self.refactor.description},
            {"name": "quick", "description": self.quick_fix.description},
        ]
