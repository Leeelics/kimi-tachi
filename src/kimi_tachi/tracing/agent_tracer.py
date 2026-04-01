"""
Agent Tracer - Event tracking for multi-agent workflows

Tracks agent lifecycle events for visualization and debugging.

Author: kimi-tachi Team
Version: 0.3.0
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any


class AgentEventType(Enum):
    """Types of agent lifecycle events"""

    CREATED = auto()  # Agent instance created
    STARTED = auto()  # Task execution started
    COMPLETED = auto()  # Task execution completed successfully
    FAILED = auto()  # Task execution failed
    CANCELLED = auto()  # Task was cancelled
    CACHE_HIT = auto()  # Agent reused from cache
    CACHE_MISS = auto()  # New agent created (not in cache)


@dataclass
class AgentEvent:
    """
    Single agent lifecycle event.

    Attributes:
        event_id: Unique event identifier
        event_type: Type of event
        agent_id: Agent instance identifier
        personality: Anime character personality
        subagent_type: Native agent type (coder/explore/plan)
        task_id: Associated task identifier
        task_summary: Brief task description
        parent_tool_call_id: Parent tool call for tracing hierarchy
        timestamp: Event timestamp (seconds since epoch)
        duration_ms: Event duration in milliseconds (for completed events)
        metadata: Additional event metadata
    """

    event_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    event_type: AgentEventType = AgentEventType.CREATED
    agent_id: str = ""
    personality: str = ""
    subagent_type: str = ""
    task_id: str = ""
    task_summary: str = ""
    parent_tool_call_id: str | None = None
    timestamp: float = field(default_factory=time.time)
    duration_ms: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.name,
            "agent_id": self.agent_id,
            "personality": self.personality,
            "subagent_type": self.subagent_type,
            "task_id": self.task_id,
            "task_summary": self.task_summary,
            "parent_tool_call_id": self.parent_tool_call_id,
            "timestamp": self.timestamp,
            "datetime": datetime.fromtimestamp(self.timestamp).isoformat(),
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
        }


@dataclass
class WorkflowTrace:
    """
    Complete trace of a workflow execution.

    Attributes:
        trace_id: Unique workflow trace identifier
        workflow_type: Type of workflow (feature, bugfix, etc.)
        task_description: Original task description
        start_time: Workflow start timestamp
        end_time: Workflow end timestamp (if completed)
        events: List of agent events in chronological order
        status: Workflow status (running, completed, failed)
    """

    trace_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    workflow_type: str = ""
    task_description: str = ""
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    events: list[AgentEvent] = field(default_factory=list)
    status: str = "running"  # running, completed, failed

    def add_event(self, event: AgentEvent) -> None:
        """Add an event to the trace"""
        self.events.append(event)

    def complete(self, status: str = "completed") -> None:
        """Mark workflow as completed"""
        self.end_time = time.time()
        self.status = status

    @property
    def duration_ms(self) -> int:
        """Get total workflow duration in milliseconds"""
        end = self.end_time or time.time()
        return int((end - self.start_time) * 1000)

    @property
    def agent_count(self) -> int:
        """Get number of unique agents used"""
        return len({e.agent_id for e in self.events if e.agent_id})

    def to_dict(self) -> dict[str, Any]:
        """Convert trace to dictionary"""
        return {
            "trace_id": self.trace_id,
            "workflow_type": self.workflow_type,
            "task_description": self.task_description,
            "start_time": self.start_time,
            "start_datetime": datetime.fromtimestamp(self.start_time).isoformat(),
            "end_time": self.end_time,
            "end_datetime": datetime.fromtimestamp(self.end_time).isoformat()
            if self.end_time
            else None,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "agent_count": self.agent_count,
            "event_count": len(self.events),
            "events": [e.to_dict() for e in self.events],
        }


class AgentTracer:
    """
    Traces agent events and workflow execution.

    This class provides comprehensive tracing for multi-agent workflows,
    enabling visualization and debugging via kimi vis.

    Example:
        >>> tracer = AgentTracer()
        >>> tracer.start_workflow("feature", "Implement auth")
        >>> tracer.on_agent_created("agent_1", "nekobasu", "explore")
        >>> tracer.on_task_started("agent_1", "Find auth code", "call_123")
        >>> tracer.on_task_completed("agent_1", returncode=0, duration_ms=2300)
        >>> tracer.complete_workflow()

    Attributes:
        traces: List of all workflow traces
        current_trace: Currently active workflow trace (if any)
        max_traces: Maximum number of traces to keep in memory
    """

    def __init__(self, max_traces: int = 100, debug: bool = False):
        self.max_traces = max_traces
        self.debug = debug
        self.traces: list[WorkflowTrace] = []
        self.current_trace: WorkflowTrace | None = None
        self._event_count = 0

        if self.debug:
            print(f"[AgentTracer] Initialized (max_traces={max_traces})")

    def start_workflow(self, workflow_type: str, task_description: str) -> WorkflowTrace:
        """
        Start tracing a new workflow.

        Args:
            workflow_type: Type of workflow (feature, bugfix, etc.)
            task_description: Original task description

        Returns:
            The new workflow trace
        """
        # Complete any existing workflow
        if self.current_trace:
            self.complete_workflow("interrupted")

        # Create new trace
        trace = WorkflowTrace(
            workflow_type=workflow_type,
            task_description=task_description,
        )
        self.traces.append(trace)
        self.current_trace = trace

        # Trim old traces if needed
        if len(self.traces) > self.max_traces:
            self.traces = self.traces[-self.max_traces :]

        if self.debug:
            print(f"[AgentTracer] Started workflow {trace.trace_id}: {task_description[:50]}...")

        return trace

    def on_agent_created(
        self,
        agent_id: str,
        personality: str,
        subagent_type: str,
        parent_tool_call_id: str | None = None,
    ) -> AgentEvent:
        """
        Record agent creation event.

        Args:
            agent_id: Unique agent identifier
            personality: Anime character personality
            subagent_type: Native agent type
            parent_tool_call_id: Parent tool call ID

        Returns:
            The created event
        """
        event = AgentEvent(
            event_type=AgentEventType.CREATED,
            agent_id=agent_id,
            personality=personality,
            subagent_type=subagent_type,
            parent_tool_call_id=parent_tool_call_id,
        )

        if self.current_trace:
            self.current_trace.add_event(event)

        self._event_count += 1

        if self.debug:
            print(f"[AgentTracer] Agent created: {personality} ({subagent_type})")

        return event

    def on_task_started(
        self,
        agent_id: str,
        task: str,
        parent_tool_call_id: str | None = None,
    ) -> AgentEvent:
        """
        Record task start event.

        Args:
            agent_id: Agent identifier
            task: Task description
            parent_tool_call_id: Parent tool call ID

        Returns:
            The created event
        """
        event = AgentEvent(
            event_type=AgentEventType.STARTED,
            agent_id=agent_id,
            task_id=str(uuid.uuid4())[:8],
            task_summary=task[:100],
            parent_tool_call_id=parent_tool_call_id,
        )

        if self.current_trace:
            self.current_trace.add_event(event)

        self._event_count += 1

        if self.debug:
            print(f"[AgentTracer] Task started: {task[:50]}...")

        return event

    def on_task_completed(
        self,
        agent_id: str,
        returncode: int = 0,
        duration_ms: int = 0,
        metadata: dict | None = None,
    ) -> AgentEvent:
        """
        Record task completion event.

        Args:
            agent_id: Agent identifier
            returncode: Task return code (0 = success)
            duration_ms: Task duration in milliseconds
            metadata: Additional metadata

        Returns:
            The created event
        """
        event_type = AgentEventType.COMPLETED if returncode == 0 else AgentEventType.FAILED

        event = AgentEvent(
            event_type=event_type,
            agent_id=agent_id,
            duration_ms=duration_ms,
            metadata=metadata or {},
        )

        if self.current_trace:
            self.current_trace.add_event(event)

        self._event_count += 1

        if self.debug:
            status = "completed" if returncode == 0 else "failed"
            print(f"[AgentTracer] Task {status}: {agent_id} ({duration_ms}ms)")

        return event

    def on_cache_hit(self, agent_id: str, personality: str) -> AgentEvent:
        """Record cache hit event"""
        event = AgentEvent(
            event_type=AgentEventType.CACHE_HIT,
            agent_id=agent_id,
            personality=personality,
        )

        if self.current_trace:
            self.current_trace.add_event(event)

        self._event_count += 1

        if self.debug:
            print(f"[AgentTracer] Cache hit: {personality}")

        return event

    def on_cache_miss(self, agent_id: str, personality: str) -> AgentEvent:
        """Record cache miss event"""
        event = AgentEvent(
            event_type=AgentEventType.CACHE_MISS,
            agent_id=agent_id,
            personality=personality,
        )

        if self.current_trace:
            self.current_trace.add_event(event)

        self._event_count += 1

        if self.debug:
            print(f"[AgentTracer] Cache miss: {personality}")

        return event

    def complete_workflow(self, status: str = "completed") -> WorkflowTrace | None:
        """
        Complete the current workflow.

        Args:
            status: Final status (completed, failed, cancelled)

        Returns:
            The completed trace, or None if no active workflow
        """
        if not self.current_trace:
            return None

        self.current_trace.complete(status)
        trace = self.current_trace
        self.current_trace = None

        if self.debug:
            print(f"[AgentTracer] Workflow {status}: {trace.trace_id} ({trace.duration_ms}ms)")

        return trace

    def get_current_trace(self) -> WorkflowTrace | None:
        """Get the currently active workflow trace"""
        return self.current_trace

    def get_trace(self, trace_id: str) -> WorkflowTrace | None:
        """Get a specific trace by ID"""
        for trace in self.traces:
            if trace.trace_id == trace_id:
                return trace
        return None

    def get_recent_traces(self, n: int = 10) -> list[WorkflowTrace]:
        """Get the n most recent traces"""
        return self.traces[-n:]

    def get_stats(self) -> dict[str, Any]:
        """Get tracer statistics"""
        total_duration = sum(t.duration_ms for t in self.traces if t.end_time)
        completed = sum(1 for t in self.traces if t.status == "completed")
        failed = sum(1 for t in self.traces if t.status == "failed")

        return {
            "total_traces": len(self.traces),
            "current_trace": self.current_trace.trace_id if self.current_trace else None,
            "total_events": self._event_count,
            "completed_workflows": completed,
            "failed_workflows": failed,
            "total_duration_ms": total_duration,
            "avg_duration_ms": total_duration // completed if completed > 0 else 0,
        }

    def clear(self) -> int:
        """Clear all traces. Returns number of traces cleared."""
        count = len(self.traces)
        self.traces.clear()
        self.current_trace = None
        self._event_count = 0

        if self.debug:
            print(f"[AgentTracer] Cleared {count} traces")

        return count

    def export_all(self) -> list[dict]:
        """Export all traces as dictionaries"""
        return [t.to_dict() for t in self.traces]


# Global tracer instance
_tracer_instance: AgentTracer | None = None


def get_tracer(max_traces: int = 100, debug: bool = False) -> AgentTracer:
    """
    Get or create the global tracer instance.

    Args:
        max_traces: Maximum traces to keep
        debug: Enable debug output

    Returns:
        Global AgentTracer instance
    """
    global _tracer_instance
    if _tracer_instance is None:
        _tracer_instance = AgentTracer(max_traces=max_traces, debug=debug)
    return _tracer_instance


def reset_tracer() -> None:
    """Reset the global tracer instance"""
    global _tracer_instance
    if _tracer_instance:
        _tracer_instance.clear()
    _tracer_instance = None
