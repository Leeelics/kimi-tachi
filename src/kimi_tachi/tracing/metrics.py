"""
Metrics collection for agent performance and workflow efficiency.

Author: kimi-tachi Team
Version: 0.3.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentMetrics:
    """Performance metrics for a single agent"""
    agent_id: str = ""
    personality: str = ""
    subagent_type: str = ""
    
    # Execution metrics
    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    total_duration_ms: int = 0
    
    # Cache metrics
    cache_hits: int = 0
    cache_misses: int = 0
    
    @property
    def avg_duration_ms(self) -> float:
        """Average task duration"""
        if self.total_tasks == 0:
            return 0.0
        return self.total_duration_ms / self.total_tasks
    
    @property
    def success_rate(self) -> float:
        """Task success rate (0-1)"""
        if self.total_tasks == 0:
            return 0.0
        return self.successful_tasks / self.total_tasks
    
    @property
    def cache_hit_rate(self) -> float:
        """Cache hit rate (0-1)"""
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return self.cache_hits / total
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "personality": self.personality,
            "subagent_type": self.subagent_type,
            "total_tasks": self.total_tasks,
            "successful_tasks": self.successful_tasks,
            "failed_tasks": self.failed_tasks,
            "success_rate": round(self.success_rate, 2),
            "total_duration_ms": self.total_duration_ms,
            "avg_duration_ms": round(self.avg_duration_ms, 1),
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": round(self.cache_hit_rate, 2),
        }


@dataclass
class WorkflowMetrics:
    """Performance metrics for a workflow"""
    trace_id: str = ""
    workflow_type: str = ""
    
    # Execution metrics
    duration_ms: int = 0
    agent_count: int = 0
    task_count: int = 0
    
    # Success metrics
    successful_tasks: int = 0
    failed_tasks: int = 0
    
    # Parallelization metrics
    sequential_tasks: int = 0
    parallel_tasks: int = 0
    
    @property
    def success_rate(self) -> float:
        """Task success rate"""
        if self.task_count == 0:
            return 0.0
        return self.successful_tasks / self.task_count
    
    @property
    def parallelization_ratio(self) -> float:
        """Ratio of parallel to total tasks"""
        if self.task_count == 0:
            return 0.0
        return self.parallel_tasks / self.task_count
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "workflow_type": self.workflow_type,
            "duration_ms": self.duration_ms,
            "agent_count": self.agent_count,
            "task_count": self.task_count,
            "successful_tasks": self.successful_tasks,
            "failed_tasks": self.failed_tasks,
            "success_rate": round(self.success_rate, 2),
            "sequential_tasks": self.sequential_tasks,
            "parallel_tasks": self.parallel_tasks,
            "parallelization_ratio": round(self.parallelization_ratio, 2),
        }


class MetricsCollector:
    """Collects and aggregates metrics from traces"""
    
    def __init__(self):
        self.agent_metrics: dict[str, AgentMetrics] = {}
        self.workflow_metrics: list[WorkflowMetrics] = []
    
    def record_agent_task(
        self,
        agent_id: str,
        personality: str,
        subagent_type: str,
        success: bool,
        duration_ms: int,
        cache_hit: bool = False,
    ) -> None:
        """Record metrics for an agent task"""
        if agent_id not in self.agent_metrics:
            self.agent_metrics[agent_id] = AgentMetrics(
                agent_id=agent_id,
                personality=personality,
                subagent_type=subagent_type,
            )
        
        metrics = self.agent_metrics[agent_id]
        metrics.total_tasks += 1
        metrics.total_duration_ms += duration_ms
        
        if success:
            metrics.successful_tasks += 1
        else:
            metrics.failed_tasks += 1
        
        if cache_hit:
            metrics.cache_hits += 1
        else:
            metrics.cache_misses += 1
    
    def record_workflow(self, workflow_metrics: WorkflowMetrics) -> None:
        """Record workflow metrics"""
        self.workflow_metrics.append(workflow_metrics)
    
    def get_agent_summary(self) -> list[dict]:
        """Get summary of all agent metrics"""
        return [m.to_dict() for m in self.agent_metrics.values()]
    
    def get_workflow_summary(self, n: int = 10) -> list[dict]:
        """Get summary of recent workflow metrics"""
        return [m.to_dict() for m in self.workflow_metrics[-n:]]
    
    def get_overall_stats(self) -> dict[str, Any]:
        """Get overall statistics"""
        if not self.workflow_metrics:
            return {"workflows": 0, "agents": 0}
        
        total_duration = sum(w.duration_ms for w in self.workflow_metrics)
        total_tasks = sum(w.task_count for w in self.workflow_metrics)
        
        return {
            "workflows": len(self.workflow_metrics),
            "agents": len(self.agent_metrics),
            "total_duration_ms": total_duration,
            "total_tasks": total_tasks,
            "avg_workflow_duration_ms": total_duration // len(self.workflow_metrics),
            "avg_tasks_per_workflow": total_tasks // len(self.workflow_metrics),
        }
