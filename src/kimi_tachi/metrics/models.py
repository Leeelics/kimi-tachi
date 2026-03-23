"""
Phase 2 指标数据模型
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class AgentEfficiencyMetrics:
    """Agent 效率指标"""

    # MCP 进程指标
    mcp_process_count: int = 0
    mcp_process_peak: int = 0
    mcp_start_time_ms: float = 0.0

    # Subagent 指标
    subagent_creation_count: int = 0
    subagent_creation_time_ms: list[float] = field(default_factory=list)
    subagent_types: dict[str, int] = field(default_factory=dict)  # 各类型创建次数

    def record_subagent_creation(self, agent_type: str, duration_ms: float):
        """记录 subagent 创建"""
        self.subagent_creation_count += 1
        self.subagent_creation_time_ms.append(duration_ms)
        self.subagent_types[agent_type] = self.subagent_types.get(agent_type, 0) + 1

    def record_mcp_process(self, count: int):
        """记录 MCP 进程数量"""
        self.mcp_process_count = count
        self.mcp_process_peak = max(self.mcp_process_peak, count)

    @property
    def avg_subagent_creation_time(self) -> float:
        """平均 subagent 创建时间"""
        if not self.subagent_creation_time_ms:
            return 0.0
        return statistics.mean(self.subagent_creation_time_ms)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mcp": {
                "current_count": self.mcp_process_count,
                "peak_count": self.mcp_process_peak,
                "target": "≤2",
                "status": "✅" if self.mcp_process_count <= 2 else "❌",
                "start_time_ms": round(self.mcp_start_time_ms, 2),
            },
            "subagent": {
                "total_created": self.subagent_creation_count,
                "avg_creation_time_ms": round(self.avg_subagent_creation_time, 2),
                "types": self.subagent_types,
            },
        }


@dataclass
class MessageBusMetrics:
    """消息总线指标"""

    # 延迟指标
    message_latencies_ms: list[float] = field(default_factory=list)

    # 吞吐量指标
    messages_sent: int = 0
    messages_received: int = 0
    bytes_transferred: int = 0

    # 广播效率
    broadcast_count: int = 0
    multicast_count: int = 0
    unicast_count: int = 0

    def record_message(self, latency_ms: float, size_bytes: int = 0):
        """记录消息"""
        self.message_latencies_ms.append(latency_ms)
        self.messages_sent += 1
        self.bytes_transferred += size_bytes

    def record_broadcast(self):
        """记录广播"""
        self.broadcast_count += 1

    def record_multicast(self, recipient_count: int):
        """记录组播"""
        self.multicast_count += 1
        self.messages_sent += recipient_count

    @property
    def avg_latency_ms(self) -> float:
        """平均延迟"""
        if not self.message_latencies_ms:
            return 0.0
        return statistics.mean(self.message_latencies_ms)

    @property
    def max_latency_ms(self) -> float:
        """最大延迟"""
        if not self.message_latencies_ms:
            return 0.0
        return max(self.message_latencies_ms)

    @property
    def p95_latency_ms(self) -> float:
        """P95 延迟"""
        if len(self.message_latencies_ms) < 20:
            return self.max_latency_ms
        sorted_latencies = sorted(self.message_latencies_ms)
        idx = int(len(sorted_latencies) * 0.95)
        return sorted_latencies[idx]

    @property
    def throughput_msgs_per_sec(self) -> float:
        """吞吐量 (消息/秒)"""
        # 简化计算，假设总时间为所有延迟之和
        total_time_sec = sum(self.message_latencies_ms) / 1000
        if total_time_sec == 0:
            return 0.0
        return self.messages_sent / total_time_sec

    def to_dict(self) -> dict[str, Any]:
        return {
            "latency": {
                "avg_ms": round(self.avg_latency_ms, 2),
                "max_ms": round(self.max_latency_ms, 2),
                "p95_ms": round(self.p95_latency_ms, 2),
                "target": "<100ms",
                "status": "✅" if self.avg_latency_ms < 100 else "❌",
            },
            "throughput": {
                "messages_sent": self.messages_sent,
                "messages_received": self.messages_received,
                "bytes_transferred": self.bytes_transferred,
                "msgs_per_sec": round(self.throughput_msgs_per_sec, 2),
            },
            "distribution": {
                "broadcast": self.broadcast_count,
                "multicast": self.multicast_count,
                "unicast": self.unicast_count,
            },
        }


@dataclass
class WorkflowMetrics:
    """Workflow 引擎指标"""

    # Phase 执行指标
    phase_executions: dict[str, list[float]] = field(default_factory=dict)  # phase -> 执行时间列表
    phase_failures: dict[str, int] = field(default_factory=dict)

    # 并行/顺序执行比例
    parallel_executions: int = 0
    sequential_executions: int = 0

    # 断点续传
    recovery_attempts: int = 0
    recovery_successes: int = 0

    # Workflow 状态
    workflow_starts: int = 0
    workflow_completions: int = 0
    workflow_failures: int = 0

    def record_phase(self, phase_name: str, duration_ms: float, success: bool = True):
        """记录 phase 执行"""
        if phase_name not in self.phase_executions:
            self.phase_executions[phase_name] = []
        self.phase_executions[phase_name].append(duration_ms)

        if not success:
            self.phase_failures[phase_name] = self.phase_failures.get(phase_name, 0) + 1

    def record_parallel_execution(self, phase_count: int):
        """记录并行执行"""
        self.parallel_executions += phase_count

    def record_sequential_execution(self):
        """记录顺序执行"""
        self.sequential_executions += 1

    def record_recovery(self, success: bool):
        """记录断点续传"""
        self.recovery_attempts += 1
        if success:
            self.recovery_successes += 1

    def record_workflow(self, completed: bool = True):
        """记录 workflow 完成"""
        self.workflow_starts += 1
        if completed:
            self.workflow_completions += 1
        else:
            self.workflow_failures += 1

    @property
    def phase_completion_rate(self) -> dict[str, float]:
        """各 phase 完成率"""
        rates = {}
        for phase, times in self.phase_executions.items():
            failures = self.phase_failures.get(phase, 0)
            total = len(times) + failures
            rates[phase] = (len(times) / total * 100) if total > 0 else 0.0
        return rates

    @property
    def avg_phase_time(self) -> dict[str, float]:
        """各 phase 平均执行时间"""
        return {
            phase: statistics.mean(times) if times else 0.0
            for phase, times in self.phase_executions.items()
        }

    @property
    def parallel_ratio(self) -> float:
        """并行执行比例"""
        total = self.parallel_executions + self.sequential_executions
        if total == 0:
            return 0.0
        return self.parallel_executions / total * 100

    @property
    def recovery_success_rate(self) -> float:
        """断点续传成功率"""
        if self.recovery_attempts == 0:
            return 100.0
        return self.recovery_successes / self.recovery_attempts * 100

    @property
    def workflow_completion_rate(self) -> float:
        """Workflow 完成率"""
        if self.workflow_starts == 0:
            return 0.0
        return self.workflow_completions / self.workflow_starts * 100

    def to_dict(self) -> dict[str, Any]:
        return {
            "phases": {
                "completion_rate": {k: round(v, 2) for k, v in self.phase_completion_rate.items()},
                "avg_time_ms": {k: round(v, 2) for k, v in self.avg_phase_time.items()},
                "target": "≥90%",
                "status": "✅"
                if all(r >= 90 for r in self.phase_completion_rate.values())
                else "❌",
            },
            "execution": {
                "parallel_ratio": round(self.parallel_ratio, 2),
                "parallel_count": self.parallel_executions,
                "sequential_count": self.sequential_executions,
                "target": "≥40%",
                "status": "✅" if self.parallel_ratio >= 40 else "❌",
            },
            "recovery": {
                "attempts": self.recovery_attempts,
                "successes": self.recovery_successes,
                "success_rate": round(self.recovery_success_rate, 2),
            },
            "workflow": {
                "started": self.workflow_starts,
                "completed": self.workflow_completions,
                "failed": self.workflow_failures,
                "completion_rate": round(self.workflow_completion_rate, 2),
            },
        }


@dataclass
class ContextOptimizationMetrics:
    """上下文优化指标"""

    # 缓存指标
    cache_hits: int = 0
    cache_misses: int = 0
    cache_evictions: int = 0
    cache_size: int = 0

    # 文件读取去重
    file_read_requests: int = 0
    file_read_unique: int = 0
    file_read_duplicates: int = 0

    # 代码库索引
    index_build_time_ms: float = 0.0
    index_size: int = 0  # 索引的符号数量
    index_query_count: int = 0
    index_query_time_ms: list[float] = field(default_factory=list)

    # 符号查找
    symbol_lookups: int = 0
    symbol_lookup_hits: int = 0

    def record_cache_access(self, hit: bool):
        """记录缓存访问"""
        if hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1

    def record_file_read(self, filepath: str, was_cached: bool = False):
        """记录文件读取"""
        self.file_read_requests += 1
        if was_cached:
            self.file_read_duplicates += 1
        else:
            self.file_read_unique += 1

    def record_index_build(self, duration_ms: float, symbol_count: int):
        """记录索引构建"""
        self.index_build_time_ms = duration_ms
        self.index_size = symbol_count

    def record_index_query(self, duration_ms: float):
        """记录索引查询"""
        self.index_query_count += 1
        self.index_query_time_ms.append(duration_ms)

    def record_symbol_lookup(self, found: bool):
        """记录符号查找"""
        self.symbol_lookups += 1
        if found:
            self.symbol_lookup_hits += 1

    @property
    def cache_hit_rate(self) -> float:
        """缓存命中率"""
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return self.cache_hits / total * 100

    @property
    def file_read_dedup_rate(self) -> float:
        """文件读取去重率"""
        if self.file_read_requests == 0:
            return 0.0
        return self.file_read_duplicates / self.file_read_requests * 100

    @property
    def avg_index_query_time(self) -> float:
        """平均索引查询时间"""
        if not self.index_query_time_ms:
            return 0.0
        return statistics.mean(self.index_query_time_ms)

    @property
    def symbol_lookup_hit_rate(self) -> float:
        """符号查找命中率"""
        if self.symbol_lookups == 0:
            return 0.0
        return self.symbol_lookup_hits / self.symbol_lookups * 100

    def to_dict(self) -> dict[str, Any]:
        return {
            "cache": {
                "hits": self.cache_hits,
                "misses": self.cache_misses,
                "hit_rate": round(self.cache_hit_rate, 2),
                "evictions": self.cache_evictions,
                "size": self.cache_size,
                "target": "≥80%",
                "status": "✅" if self.cache_hit_rate >= 80 else "❌",
            },
            "file_dedup": {
                "total_reads": self.file_read_requests,
                "unique_reads": self.file_read_unique,
                "duplicate_reads": self.file_read_duplicates,
                "dedup_rate": round(self.file_read_dedup_rate, 2),
            },
            "index": {
                "build_time_ms": round(self.index_build_time_ms, 2),
                "symbol_count": self.index_size,
                "query_count": self.index_query_count,
                "avg_query_time_ms": round(self.avg_index_query_time, 2),
                "target_build_time": "<2000ms",
                "status": "✅" if self.index_build_time_ms < 2000 else "❌",
            },
            "symbol_lookup": {
                "total": self.symbol_lookups,
                "hits": self.symbol_lookup_hits,
                "hit_rate": round(self.symbol_lookup_hit_rate, 2),
            },
        }


@dataclass
class Phase2MetricsCollection:
    """Phase 2 指标集合"""

    # 时间戳
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: datetime | None = None

    # 四大指标类别
    agent_efficiency: AgentEfficiencyMetrics = field(default_factory=AgentEfficiencyMetrics)
    message_bus: MessageBusMetrics = field(default_factory=MessageBusMetrics)
    workflow: WorkflowMetrics = field(default_factory=WorkflowMetrics)
    context_optimization: ContextOptimizationMetrics = field(
        default_factory=ContextOptimizationMetrics
    )

    def finish(self):
        """标记结束"""
        self.end_time = datetime.utcnow()

    @property
    def duration_seconds(self) -> float:
        """总耗时"""
        if self.end_time is None:
            return 0.0
        return (self.end_time - self.start_time).total_seconds()

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "metadata": {
                "start_time": self.start_time.isoformat(),
                "end_time": self.end_time.isoformat() if self.end_time else None,
                "duration_seconds": round(self.duration_seconds, 2),
            },
            "agent_efficiency": self.agent_efficiency.to_dict(),
            "message_bus": self.message_bus.to_dict(),
            "workflow": self.workflow.to_dict(),
            "context_optimization": self.context_optimization.to_dict(),
        }

    def to_json(self, indent: int = 2) -> str:
        """转换为 JSON 字符串"""
        import json

        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
