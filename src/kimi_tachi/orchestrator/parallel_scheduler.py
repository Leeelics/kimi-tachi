"""
Parallel Scheduler

并行任务调度器，支持：
1. 基于 DependencyGraph 的并行执行
2. 通过 MessageBus 协调中间结果
3. 部分失败处理
4. 资源限制管理（MCP 进程数）
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ..message_bus import Message, MessageBus, MessageType
from ..metrics import MetricsCollector
from .dependency_analyzer import DependencyGraph
from .hybrid_orchestrator import AgentResult, HybridOrchestrator

if TYPE_CHECKING:
    from .workflow_engine import Phase


@dataclass
class BatchResult:
    """批次执行结果"""

    batch_idx: int
    results: dict[str, AgentResult]  # phase_name -> result
    completed: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    duration_ms: float = 0.0


@dataclass
class ExecutionContext:
    """执行上下文，在 phases 间共享"""

    task: str
    shared_data: dict[str, Any] = field(default_factory=dict)
    intermediate_results: dict[str, AgentResult] = field(default_factory=dict)

    def publish_result(self, phase_name: str, result: AgentResult) -> None:
        """发布 phase 结果供其他 phases 使用"""
        self.intermediate_results[phase_name] = result
        self.shared_data[f"{phase_name}_output"] = result.stdout

    def get_dependency_results(self, dependencies: list[str]) -> dict[str, AgentResult]:
        """获取依赖 phase 的结果"""
        return {
            dep: self.intermediate_results[dep]
            for dep in dependencies
            if dep in self.intermediate_results
        }


class ParallelScheduler:
    """
    并行任务调度器

    管理 Workflow phases 的并行执行，优化资源利用
    """

    def __init__(
        self,
        orchestrator: HybridOrchestrator,
        message_bus: MessageBus | None = None,
        metrics_collector: MetricsCollector | None = None,
        max_parallel: int = 2,  # 限制并行数，配合 MCP 进程限制
        continue_on_failure: bool = False,  # 是否在一个 phase 失败时继续
    ):
        self.orch = orchestrator
        self.bus = message_bus
        self.metrics = metrics_collector
        self.max_parallel = max_parallel
        self.continue_on_failure = continue_on_failure

        # 执行状态
        self._execution_id: str = ""
        self._completed_phases: set[str] = set()
        self._failed_phases: set[str] = set()

    async def execute_plan(
        self,
        graph: DependencyGraph,
        phases: list[Any],  # Phase
        task: str,
    ) -> list[AgentResult]:
        """
        执行依赖图定义的 plan

        Args:
            graph: 依赖关系图
            phases: phase 定义列表
            task: 原始任务描述

        Returns:
            所有 phase 的执行结果
        """
        import uuid

        self._execution_id = str(uuid.uuid4())[:8]
        self._completed_phases.clear()
        self._failed_phases.clear()

        phase_map = {p.name: p for p in phases}
        context = ExecutionContext(task=task)
        all_results: list[AgentResult] = []

        print(f"\n{'=' * 60}")
        print(f"🏃 Parallel Execution Plan (ID: {self._execution_id})")
        print(f"{'=' * 60}")

        # 获取并行执行组
        parallel_groups = graph.find_parallel_groups()

        print("\n📊 Analysis:")
        print(f"   Total phases: {len(phases)}")
        print(f"   Parallel groups: {len(parallel_groups)}")
        print(f"   Max parallel: {self.max_parallel}")

        # 执行每个 batch
        for batch_idx, group in enumerate(parallel_groups, 1):
            batch_phases = [phase_map[name] for name in group if name in phase_map]

            if not batch_phases:
                continue

            print(f"\n{'─' * 60}")
            print(f"📦 Batch {batch_idx}/{len(parallel_groups)}: {len(batch_phases)} phase(s)")
            print(f"{'─' * 60}")

            # 检查依赖是否满足
            for phase in batch_phases:
                deps = graph.get_dependencies(phase.name)
                unmet = [d for d in deps if d not in self._completed_phases]
                if unmet:
                    print(f"   ⚠️ {phase.name}: waiting for {unmet}")

            # 执行 batch
            batch_result = await self._execute_batch(
                batch_idx=batch_idx,
                phases=batch_phases,
                context=context,
                graph=graph,
            )

            # 收集结果
            all_results.extend(batch_result.results.values())

            # 更新状态
            self._completed_phases.update(batch_result.completed)
            self._failed_phases.update(batch_result.failed)

            # 检查是否需要中止
            if batch_result.failed and not self.continue_on_failure:
                print(f"\n❌ Batch {batch_idx} failed, stopping execution")
                break

        # 打印总结
        print(f"\n{'=' * 60}")
        print("✅ Execution Complete")
        print(f"   Completed: {len(self._completed_phases)}")
        print(f"   Failed: {len(self._failed_phases)}")
        print(f"{'=' * 60}\n")

        return all_results

    async def _execute_batch(
        self,
        batch_idx: int,
        phases: list[Any],  # Phase
        context: ExecutionContext,
        graph: DependencyGraph,
    ) -> BatchResult:
        """
        执行一个 batch 的 phases

        如果 phases 数量超过 max_parallel，会分批串行执行
        """
        result = BatchResult(batch_idx=batch_idx, results={})
        start_time = asyncio.get_event_loop().time()

        # 分批处理（考虑 max_parallel 限制）
        for i in range(0, len(phases), self.max_parallel):
            chunk = phases[i : i + self.max_parallel]

            if len(chunk) == 1:
                # 单个 phase，串行执行
                phase = chunk[0]
                print(f"   ▶️  {phase.name} ({phase.agent})")

                agent_result = await self._execute_phase(
                    phase=phase,
                    context=context,
                    graph=graph,
                )

                result.results[phase.name] = agent_result

                if agent_result.returncode == 0:
                    result.completed.append(phase.name)
                    context.publish_result(phase.name, agent_result)
                else:
                    result.failed.append(phase.name)

            else:
                # 多个 phases，并行执行
                print(f"   🏃 Parallel chunk: {[p.name for p in chunk]}")

                # 创建并行任务
                tasks = [self._execute_phase_with_timeout(phase, context, graph) for phase in chunk]

                # 并行执行
                chunk_results = await asyncio.gather(*tasks, return_exceptions=True)

                # 处理结果
                for phase, agent_result in zip(chunk, chunk_results, strict=False):
                    if isinstance(agent_result, Exception):
                        print(f"   ❌ {phase.name}: Exception - {agent_result}")
                        agent_result = AgentResult(
                            agent=phase.agent,
                            task=phase.task_template,
                            stdout="",
                            stderr=str(agent_result),
                            returncode=-1,
                        )
                        result.failed.append(phase.name)
                    elif agent_result.returncode == 0:
                        print(f"   ✅ {phase.name}: Success")
                        result.completed.append(phase.name)
                        context.publish_result(phase.name, agent_result)
                    else:
                        print(f"   ❌ {phase.name}: Failed (code {agent_result.returncode})")
                        result.failed.append(phase.name)

                    result.results[phase.name] = agent_result

        result.duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
        return result

    async def _execute_phase_with_timeout(
        self,
        phase: Any,  # Phase
        context: ExecutionContext,
        graph: DependencyGraph,
        timeout: float = 300.0,
    ) -> AgentResult:
        """执行单个 phase，带超时"""
        try:
            return await asyncio.wait_for(
                self._execute_phase(phase, context, graph),
                timeout=timeout,
            )
        except TimeoutError:
            return AgentResult(
                agent=phase.agent,
                task=phase.task_template,
                stdout="",
                stderr=f"Timeout after {timeout}s",
                returncode=-1,
            )

    async def _execute_phase(
        self,
        phase: Phase,
        context: ExecutionContext,
        graph: DependencyGraph,
    ) -> AgentResult:
        """执行单个 phase"""
        # 准备任务描述
        task_desc = phase.task_template.format(task=context.task)

        # 获取依赖结果作为上下文
        deps = graph.get_dependencies(phase.name)
        dep_results = context.get_dependency_results(deps)

        context_str = ""
        if dep_results:
            context_parts = []
            for dep_name, dep_result in dep_results.items():
                # 截断过长的输出
                output = dep_result.stdout[:500] if dep_result.stdout else ""
                if output:
                    context_parts.append(f"\n[{dep_name}]:\n{output}")

            if context_parts:
                context_str = "\n".join(context_parts)
                context_str = f"\n\nBased on previous results:{context_str}"

        # 通过 MessageBus 通知（如果启用）
        if self.bus:
            await self._notify_phase_start(phase, context)

        # 执行 phase
        result = await self.orch.delegate(
            agent=phase.agent,
            task=task_desc + context_str,
        )

        # 通过 MessageBus 通知完成
        if self.bus:
            await self._notify_phase_complete(phase, result, context)

        # 记录指标
        if self.metrics:
            self.metrics.record_phase(
                phase_name=phase.name,
                duration_ms=0,  # 由 orchestrator 记录
                success=result.returncode == 0,
            )

        return result

    async def _notify_phase_start(
        self,
        phase: Phase,
        context: ExecutionContext,
    ) -> None:
        """通过 MessageBus 通知 phase 开始"""
        if not self.bus:
            return

        msg = Message.create(
            content={
                "event": "phase.start",
                "execution_id": self._execution_id,
                "phase": phase.name,
                "agent": phase.agent,
                "task": context.task,
            },
            source="parallel_scheduler",
            message_type=MessageType.PUBLISH,
            channel="workflow.events",
        )

        await self.bus.publish("workflow.events", msg)

    async def _notify_phase_complete(
        self,
        phase: Phase,
        result: AgentResult,
        context: ExecutionContext,
    ) -> None:
        """通过 MessageBus 通知 phase 完成"""
        if not self.bus:
            return

        msg = Message.create(
            content={
                "event": "phase.complete",
                "execution_id": self._execution_id,
                "phase": phase.name,
                "agent": phase.agent,
                "success": result.returncode == 0,
                "output_preview": result.stdout[:200] if result.stdout else "",
            },
            source="parallel_scheduler",
            message_type=MessageType.PUBLISH,
            channel="workflow.events",
        )

        await self.bus.publish("workflow.events", msg)

    def get_execution_summary(self) -> dict[str, Any]:
        """获取执行摘要"""
        return {
            "execution_id": self._execution_id,
            "completed_phases": list(self._completed_phases),
            "failed_phases": list(self._failed_phases),
            "total_completed": len(self._completed_phases),
            "total_failed": len(self._failed_phases),
        }
