"""
Workflow Renderer - Visualize multi-agent workflows

Renders workflow traces as nodes and edges for visualization.

Author: kimi-tachi Team
Version: 0.3.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from ..tracing.agent_tracer import AgentEvent, AgentEventType, WorkflowTrace


class NodeType(Enum):
    """Types of workflow nodes"""
    COORDINATOR = auto()   # kamaji
    AGENT = auto()         # Worker agent
    TASK = auto()          # Individual task
    DECISION = auto()      # Decision point


class EdgeType(Enum):
    """Types of workflow edges"""
    DELEGATES = auto()     # Coordinator -> Agent
    EXECUTES = auto()      # Agent -> Task
    DEPENDS = auto()       # Task -> Task (dependency)
    RETURNS = auto()       # Task -> Coordinator (result)


@dataclass
class WorkflowNode:
    """Node in workflow visualization"""
    id: str
    type: NodeType
    label: str
    icon: str = ""
    status: str = "pending"  # pending, running, completed, failed
    duration_ms: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.name,
            "label": self.label,
            "icon": self.icon,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
        }


@dataclass
class WorkflowEdge:
    """Edge in workflow visualization"""
    from_node: str
    to_node: str
    type: EdgeType
    label: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "from": self.from_node,
            "to": self.to_node,
            "type": self.type.name,
            "label": self.label,
        }


@dataclass
class WorkflowGraph:
    """Complete workflow graph for visualization"""
    trace_id: str
    nodes: list[WorkflowNode] = field(default_factory=list)
    edges: list[WorkflowEdge] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
        }


class WorkflowRenderer:
    """
    Renders workflow traces as visualizable graphs.

    Converts event traces into node-edge graphs suitable for
    visualization in kimi vis or other tools.

    Example:
        >>> renderer = WorkflowRenderer()
        >>> graph = renderer.render(trace)
        >>> print(graph.to_dict())
    """

    # Icon mapping for personalities
    ICONS = {
        "kamaji": "◕‿◕",
        "shishigami": "🦌",
        "nekobasu": "🚌",
        "calcifer": "🔥",
        "enma": "👹",
        "tasogare": "🌆",
        "phoenix": "🐦",
    }

    def __init__(self):
        self.node_counter = 0

    def _create_node_id(self, prefix: str = "node") -> str:
        """Generate unique node ID"""
        self.node_counter += 1
        return f"{prefix}_{self.node_counter}"

    def render(self, trace: WorkflowTrace) -> WorkflowGraph:
        """
        Render a workflow trace as a graph.

        Args:
            trace: Workflow trace to render

        Returns:
            WorkflowGraph with nodes and edges
        """
        self.node_counter = 0
        graph = WorkflowGraph(trace_id=trace.trace_id)

        # Create coordinator node (kamaji)
        coordinator_id = self._create_node_id("kamaji")
        graph.nodes.append(WorkflowNode(
            id=coordinator_id,
            type=NodeType.COORDINATOR,
            label="釜爺 (Kamaji)",
            icon="◕‿◕",
            status=self._get_workflow_status(trace),
            duration_ms=trace.duration_ms,
        ))

        # Group events by agent
        agent_events: dict[str, list[AgentEvent]] = {}
        for event in trace.events:
            if event.agent_id:
                if event.agent_id not in agent_events:
                    agent_events[event.agent_id] = []
                agent_events[event.agent_id].append(event)

        # Create agent nodes and connect to coordinator
        agent_nodes: dict[str, str] = {}
        for agent_id, events in agent_events.items():
            # Get agent info from first event
            first_event = events[0]
            personality = first_event.personality or agent_id
            subagent_type = first_event.subagent_type or "unknown"

            # Create agent node
            agent_node_id = self._create_node_id(f"agent_{personality}")
            agent_nodes[agent_id] = agent_node_id

            # Calculate agent duration
            agent_duration = sum(
                e.duration_ms for e in events
                if e.event_type in (AgentEventType.COMPLETED, AgentEventType.FAILED)
            )

            # Determine agent status
            has_failed = any(e.event_type == AgentEventType.FAILED for e in events)
            agent_status = "failed" if has_failed else "completed"

            graph.nodes.append(WorkflowNode(
                id=agent_node_id,
                type=NodeType.AGENT,
                label=f"{self.ICONS.get(personality, '🔧')} {personality}",
                icon=self.ICONS.get(personality, "🔧"),
                status=agent_status,
                duration_ms=agent_duration,
                metadata={
                    "subagent_type": subagent_type,
                    "event_count": len(events),
                },
            ))

            # Connect coordinator to agent
            graph.edges.append(WorkflowEdge(
                from_node=coordinator_id,
                to_node=agent_node_id,
                type=EdgeType.DELEGATES,
                label="delegates",
            ))

            # Create task nodes for this agent
            task_events = [e for e in events if e.event_type == AgentEventType.STARTED]
            for i, task_event in enumerate(task_events):
                task_node_id = self._create_node_id(f"task_{personality}_{i}")

                # Find completion event
                completion = next(
                    (e for e in events
                     if e.event_type in (AgentEventType.COMPLETED, AgentEventType.FAILED)
                     and e.timestamp > task_event.timestamp),
                    None
                )

                task_status = "completed"
                task_duration = 0
                if completion:
                    task_status = "completed" if completion.event_type == AgentEventType.COMPLETED else "failed"
                    task_duration = completion.duration_ms

                graph.nodes.append(WorkflowNode(
                    id=task_node_id,
                    type=NodeType.TASK,
                    label=task_event.task_summary[:30] + "..." if len(task_event.task_summary) > 30 else task_event.task_summary,
                    status=task_status,
                    duration_ms=task_duration,
                ))

                # Connect agent to task
                graph.edges.append(WorkflowEdge(
                    from_node=agent_node_id,
                    to_node=task_node_id,
                    type=EdgeType.EXECUTES,
                    label="executes",
                ))

        return graph

    def _get_workflow_status(self, trace: WorkflowTrace) -> str:
        """Determine overall workflow status"""
        if trace.status == "failed":
            return "failed"
        elif trace.status == "completed":
            return "completed"
        else:
            return "running"

    def render_timeline(self, trace: WorkflowTrace) -> list[dict]:
        """
        Render workflow as a timeline.

        Returns:
            List of timeline events sorted by timestamp
        """
        timeline = []

        # Add workflow start
        timeline.append({
            "time": trace.start_time,
            "type": "workflow_start",
            "label": f"Workflow started: {trace.workflow_type}",
            "description": trace.task_description[:50],
        })

        # Add agent events
        for event in trace.events:
            entry = {
                "time": event.timestamp,
                "type": event.event_type.name.lower(),
                "agent_id": event.agent_id,
                "personality": event.personality,
            }

            if event.event_type == AgentEventType.STARTED:
                entry["label"] = f"🚀 {event.personality}: Task started"
                entry["description"] = event.task_summary
            elif event.event_type == AgentEventType.COMPLETED:
                entry["label"] = f"✅ {event.personality}: Task completed"
                entry["duration_ms"] = event.duration_ms
            elif event.event_type == AgentEventType.FAILED:
                entry["label"] = f"❌ {event.personality}: Task failed"
                entry["duration_ms"] = event.duration_ms
            elif event.event_type == AgentEventType.CREATED:
                entry["label"] = f"🆕 {event.personality}: Agent created"
            elif event.event_type == AgentEventType.CACHE_HIT:
                entry["label"] = f"💾 {event.personality}: Cache hit"
            elif event.event_type == AgentEventType.CACHE_MISS:
                entry["label"] = f"🔄 {event.personality}: Cache miss"

            timeline.append(entry)

        # Add workflow end
        if trace.end_time:
            timeline.append({
                "time": trace.end_time,
                "type": "workflow_end",
                "label": f"Workflow {trace.status}",
                "duration_ms": trace.duration_ms,
            })

        # Sort by timestamp
        timeline.sort(key=lambda x: x["time"])

        return timeline

    def render_summary(self, trace: WorkflowTrace) -> dict[str, Any]:
        """
        Render a text summary of the workflow.

        Returns:
            Dictionary with summary information
        """
        lines = [
            f"Workflow: {trace.workflow_type}",
            f"Task: {trace.task_description}",
            f"Status: {trace.status}",
            f"Duration: {trace.duration_ms}ms",
            f"Agents: {trace.agent_count}",
            f"Events: {len(trace.events)}",
            "",
            "Agent Activity:",
        ]

        # Group events by agent
        agent_stats: dict[str, dict] = {}
        for event in trace.events:
            if event.agent_id:
                if event.agent_id not in agent_stats:
                    agent_stats[event.agent_id] = {
                        "personality": event.personality,
                        "tasks": 0,
                        "duration_ms": 0,
                    }

                if event.event_type in (AgentEventType.COMPLETED, AgentEventType.FAILED):
                    agent_stats[event.agent_id]["tasks"] += 1
                    agent_stats[event.agent_id]["duration_ms"] += event.duration_ms

        for _agent_id, stats in agent_stats.items():
            icon = self.ICONS.get(stats["personality"], "🔧")
            lines.append(f"  {icon} {stats['personality']}: {stats['tasks']} tasks, {stats['duration_ms']}ms")

        return {
            "text": "\n".join(lines),
            "trace_id": trace.trace_id,
            "workflow_type": trace.workflow_type,
            "status": trace.status,
            "duration_ms": trace.duration_ms,
            "agent_count": trace.agent_count,
            "agent_stats": agent_stats,
        }
