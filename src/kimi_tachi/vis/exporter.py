"""
Vis Exporter - Export traces for kimi vis integration

Formats workflow traces for consumption by kimi-cli's vis command.

Author: kimi-tachi Team
Version: 0.3.0
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..tracing.agent_tracer import AgentTracer, WorkflowTrace
from .workflow_renderer import WorkflowRenderer


@dataclass
class VisFormat:
    """
    Format compatible with kimi vis.
    
    This structure matches what kimi vis expects for displaying
    agent workflows and events.
    """
    version: str = "1.0"
    trace_id: str = ""
    title: str = ""
    description: str = ""
    
    # Timeline data
    start_time: float = 0.0
    end_time: float | None = None
    duration_ms: int = 0
    
    # Agents
    agents: list[dict] = None
    
    # Events (for timeline view)
    events: list[dict] = None
    
    # Graph data (for graph view)
    nodes: list[dict] = None
    edges: list[dict] = None
    
    # Metrics
    metrics: dict[str, Any] = None
    
    def __post_init__(self):
        if self.agents is None:
            self.agents = []
        if self.events is None:
            self.events = []
        if self.nodes is None:
            self.nodes = []
        if self.edges is None:
            self.edges = []
        if self.metrics is None:
            self.metrics = {}
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "trace_id": self.trace_id,
            "title": self.title,
            "description": self.description,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "agents": self.agents,
            "events": self.events,
            "nodes": self.nodes,
            "edges": self.edges,
            "metrics": self.metrics,
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Export as JSON string"""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


class VisExporter:
    """
    Exports workflow traces to kimi vis compatible format.
    
    Example:
        >>> exporter = VisExporter()
        >>> vis_format = exporter.export_trace(trace)
        >>> exporter.save_to_file(vis_format, "/path/to/trace.json")
    """
    
    def __init__(self):
        self.renderer = WorkflowRenderer()
    
    def export_trace(self, trace: WorkflowTrace) -> VisFormat:
        """
        Export a single workflow trace to vis format.
        
        Args:
            trace: Workflow trace to export
        
        Returns:
            VisFormat structure
        """
        # Render graph
        graph = self.renderer.render(trace)
        timeline = self.renderer.render_timeline(trace)
        
        # Build agents list
        agents = []
        agent_ids = set()
        for event in trace.events:
            if event.agent_id and event.agent_id not in agent_ids:
                agent_ids.add(event.agent_id)
                agents.append({
                    "id": event.agent_id,
                    "personality": event.personality,
                    "subagent_type": event.subagent_type,
                    "icon": self.renderer.ICONS.get(event.personality, "🔧"),
                })
        
        # Calculate metrics
        metrics = {
            "total_events": len(trace.events),
            "agent_count": len(agents),
            "completion_rate": self._calculate_completion_rate(trace),
        }
        
        return VisFormat(
            trace_id=trace.trace_id,
            title=f"Workflow: {trace.workflow_type}",
            description=trace.task_description,
            start_time=trace.start_time,
            end_time=trace.end_time,
            duration_ms=trace.duration_ms,
            agents=agents,
            events=timeline,
            nodes=[n.to_dict() for n in graph.nodes],
            edges=[e.to_dict() for e in graph.edges],
            metrics=metrics,
        )
    
    def export_tracer(self, tracer: AgentTracer) -> list[VisFormat]:
        """
        Export all traces from a tracer.
        
        Args:
            tracer: AgentTracer instance
        
        Returns:
            List of VisFormat structures
        """
        return [self.export_trace(t) for t in tracer.traces]
    
    def save_to_file(self, vis_format: VisFormat, path: str | Path) -> None:
        """
        Save vis format to JSON file.
        
        Args:
            vis_format: VisFormat to save
            path: Output file path
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, "w", encoding="utf-8") as f:
            f.write(vis_format.to_json())
    
    def save_tracer_to_directory(
        self,
        tracer: AgentTracer,
        directory: str | Path,
    ) -> list[Path]:
        """
        Save all traces from tracer to a directory.
        
        Args:
            tracer: AgentTracer instance
            directory: Output directory
        
        Returns:
            List of saved file paths
        """
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        
        saved_paths = []
        for trace in tracer.traces:
            vis_format = self.export_trace(trace)
            filename = f"trace_{trace.trace_id}.json"
            filepath = directory / filename
            self.save_to_file(vis_format, filepath)
            saved_paths.append(filepath)
        
        return saved_paths
    
    def export_summary(self, tracer: AgentTracer) -> dict[str, Any]:
        """
        Export a summary of all traces.
        
        Args:
            tracer: AgentTracer instance
        
        Returns:
            Summary dictionary
        """
        traces = tracer.traces
        
        if not traces:
            return {
                "total_traces": 0,
                "message": "No traces available",
            }
        
        total_duration = sum(t.duration_ms for t in traces if t.end_time)
        completed = sum(1 for t in traces if t.status == "completed")
        failed = sum(1 for t in traces if t.status == "failed")
        
        # Collect agent usage
        agent_usage: dict[str, int] = {}
        for trace in traces:
            for event in trace.events:
                if event.personality:
                    agent_usage[event.personality] = agent_usage.get(event.personality, 0) + 1
        
        return {
            "total_traces": len(traces),
            "completed_workflows": completed,
            "failed_workflows": failed,
            "total_duration_ms": total_duration,
            "avg_duration_ms": total_duration // len(traces) if traces else 0,
            "agent_usage": agent_usage,
            "recent_traces": [
                {
                    "trace_id": t.trace_id,
                    "workflow_type": t.workflow_type,
                    "status": t.status,
                    "duration_ms": t.duration_ms,
                }
                for t in traces[-5:]  # Last 5
            ],
        }
    
    def _calculate_completion_rate(self, trace: WorkflowTrace) -> float:
        """Calculate task completion rate for a trace"""
        from ..tracing.agent_tracer import AgentEventType
        
        completed = sum(1 for e in trace.events if e.event_type == AgentEventType.COMPLETED)
        failed = sum(1 for e in trace.events if e.event_type == AgentEventType.FAILED)
        total = completed + failed
        
        if total == 0:
            return 0.0
        return completed / total


def export_for_kimi_vis(tracer: AgentTracer, output_dir: str | Path) -> list[Path]:
    """
    Convenience function to export tracer data for kimi vis.
    
    Args:
        tracer: AgentTracer instance
        output_dir: Output directory for vis files
    
    Returns:
        List of saved file paths
    
    Example:
        >>> tracer = get_tracer()
        >>> paths = export_for_kimi_vis(tracer, "~/.kimi/vis/kimi-tachi")
        >>> print(f"Exported {len(paths)} traces")
    """
    exporter = VisExporter()
    return exporter.save_tracer_to_directory(tracer, output_dir)
