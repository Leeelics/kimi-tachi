"""
指标收集器 - 提供易用的 API 来收集 Phase 2 指标
"""

from __future__ import annotations

import functools
import time
from collections.abc import Callable, Generator
from contextlib import contextmanager
from typing import Any

from .models import Phase2MetricsCollection


class MetricsCollector:
    """指标收集器"""

    _instance: MetricsCollector | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._metrics = Phase2MetricsCollection()
            cls._instance._enabled = True
        return cls._instance

    @property
    def metrics(self) -> Phase2MetricsCollection:
        """获取指标集合"""
        return self._metrics

    def enable(self):
        """启用收集"""
        self._enabled = True

    def disable(self):
        """禁用收集"""
        self._enabled = False

    def reset(self):
        """重置指标"""
        self._metrics = Phase2MetricsCollection()

    def finish(self):
        """完成收集"""
        self._metrics.finish()

    # ===== Agent 效率指标 =====

    def record_subagent_creation(self, agent_type: str, duration_ms: float):
        """记录 subagent 创建"""
        if self._enabled:
            self._metrics.agent_efficiency.record_subagent_creation(agent_type, duration_ms)

    def record_mcp_process(self, count: int):
        """记录 MCP 进程数量"""
        if self._enabled:
            self._metrics.agent_efficiency.record_mcp_process(count)

    # ===== 消息总线指标 =====

    def record_message(self, latency_ms: float, size_bytes: int = 0):
        """记录消息"""
        if self._enabled:
            self._metrics.message_bus.record_message(latency_ms, size_bytes)

    def record_broadcast(self):
        """记录广播"""
        if self._enabled:
            self._metrics.message_bus.record_broadcast()

    def record_multicast(self, recipient_count: int):
        """记录组播"""
        if self._enabled:
            self._metrics.message_bus.record_multicast(recipient_count)

    # ===== Workflow 指标 =====

    def record_phase(self, phase_name: str, duration_ms: float, success: bool = True):
        """记录 phase 执行"""
        if self._enabled:
            self._metrics.workflow.record_phase(phase_name, duration_ms, success)

    def record_parallel_execution(self, phase_count: int):
        """记录并行执行"""
        if self._enabled:
            self._metrics.workflow.record_parallel_execution(phase_count)

    def record_sequential_execution(self):
        """记录顺序执行"""
        if self._enabled:
            self._metrics.workflow.record_sequential_execution()

    def record_recovery(self, success: bool):
        """记录断点续传"""
        if self._enabled:
            self._metrics.workflow.record_recovery(success)

    def record_workflow(self, completed: bool = True):
        """记录 workflow 完成"""
        if self._enabled:
            self._metrics.workflow.record_workflow(completed)

    # ===== 上下文优化指标 =====

    def record_cache_access(self, hit: bool):
        """记录缓存访问"""
        if self._enabled:
            self._metrics.context_optimization.record_cache_access(hit)

    def record_file_read(self, filepath: str, was_cached: bool = False):
        """记录文件读取"""
        if self._enabled:
            self._metrics.context_optimization.record_file_read(filepath, was_cached)

    def record_index_build(self, duration_ms: float, symbol_count: int):
        """记录索引构建"""
        if self._enabled:
            self._metrics.context_optimization.record_index_build(duration_ms, symbol_count)

    def record_index_query(self, duration_ms: float):
        """记录索引查询"""
        if self._enabled:
            self._metrics.context_optimization.record_index_query(duration_ms)

    def record_symbol_lookup(self, found: bool):
        """记录符号查找"""
        if self._enabled:
            self._metrics.context_optimization.record_symbol_lookup(found)

    # ===== 输出 =====

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return self._metrics.to_dict()

    def to_json(self, indent: int = 2) -> str:
        """转换为 JSON"""
        return self._metrics.to_json(indent)

    def print_summary(self):
        """打印汇总"""

        data = self.to_dict()

        print("\n" + "=" * 80)
        print("📊 PHASE 2 指标汇总")
        print("=" * 80)

        # Agent 效率
        print("\n🔧 Agent 效率:")
        mcp = data["agent_efficiency"]["mcp"]
        status = mcp["status"]
        print(
            f"  MCP 进程: {mcp['current_count']} (峰值: {mcp['peak_count']}, "
            f"目标: {mcp['target']}) {status}"
        )
        sub = data["agent_efficiency"]["subagent"]
        print(
            f"  Subagent 创建: {sub['total_created']} 个, 平均耗时: {sub['avg_creation_time_ms']}ms"
        )

        # 消息总线
        print("\n📨 消息总线:")
        lat = data["message_bus"]["latency"]
        lat_status = lat["status"]
        print(
            f"  延迟: 平均 {lat['avg_ms']}ms, 最大 {lat['max_ms']}ms "
            f"(目标: {lat['target']}) {lat_status}"
        )

        # Workflow
        print("\n⚙️ Workflow:")
        phases = data["workflow"]["phases"]
        phase_status = phases["status"]
        print(
            f"  Phase 完成率: {phases['completion_rate']} (目标: {phases['target']}) {phase_status}"
        )
        exec_ = data["workflow"]["execution"]
        print(f"  并行比例: {exec_['parallel_ratio']}% (目标: {exec_['target']}) {exec_['status']}")

        # 上下文优化
        print("\n💾 上下文优化:")
        cache = data["context_optimization"]["cache"]
        print(f"  缓存命中率: {cache['hit_rate']}% (目标: {cache['target']}) {cache['status']}")
        idx = data["context_optimization"]["index"]
        idx_status = idx["status"]
        print(
            f"  索引构建: {idx['build_time_ms']}ms (目标: {idx['target_build_time']}) {idx_status}"
        )


# 全局收集器实例
collector = MetricsCollector()


@contextmanager
def metrics_context(operation: str) -> Generator[None, None, None]:
    """
    指标收集上下文管理器

    用法:
        with metrics_context("message_send"):
            # 执行操作
            send_message(data)
    """
    start = time.time()
    try:
        yield
    finally:
        duration_ms = (time.time() - start) * 1000
        collector.record_message(duration_ms)


def timed(metric_name: str, category: str = "message"):
    """
    装饰器：自动记录函数执行时间

    用法:
        @timed("phase_execution", "workflow")
        def execute_phase(phase_name):
            # 执行 phase
            pass
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                success = True
                return result
            except Exception:
                success = False
                raise
            finally:
                duration_ms = (time.time() - start) * 1000

                if category == "workflow":
                    # 假设第一个参数是 phase_name
                    phase_name = args[0] if args else metric_name
                    collector.record_phase(phase_name, duration_ms, success)
                elif category == "subagent":
                    agent_type = args[0] if args else metric_name
                    collector.record_subagent_creation(agent_type, duration_ms)
                else:
                    collector.record_message(duration_ms)

        return wrapper

    return decorator


def measure_subagent_creation(agent_type: str):
    """
    装饰器：测量 subagent 创建时间

    用法:
        @measure_subagent_creation("nekobasu")
        def create_nekobasu():
            # 创建 subagent
            pass
    """
    return timed(agent_type, "subagent")


def measure_phase(phase_name: str):
    """
    装饰器：测量 phase 执行时间

    用法:
        @measure_phase("planning")
        def run_planning(task):
            # 执行 planning phase
            pass
    """
    return timed(phase_name, "workflow")
