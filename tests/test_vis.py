"""
Tests for vis module.

Author: kimi-tachi Team
"""

import json

import pytest

from kimi_tachi.tracing import AgentTracer
from kimi_tachi.vis import (
    EdgeType,
    NodeType,
    VisExporter,
    WorkflowRenderer,
)


class TestWorkflowRenderer:
    """Test WorkflowRenderer class."""

    def test_render_simple_workflow(self):
        tracer = AgentTracer()
        trace = tracer.start_workflow("feature", "Implement auth")

        # Add events
        tracer.on_agent_created("agent_1", "nekobasu", "explore")
        tracer.on_task_started("agent_1", "Find auth code")
        tracer.on_task_completed("agent_1", returncode=0, duration_ms=1000)

        tracer.complete_workflow()

        renderer = WorkflowRenderer()
        graph = renderer.render(trace)

        assert graph.trace_id == trace.trace_id
        assert len(graph.nodes) > 0
        assert len(graph.edges) > 0

        # Check coordinator node
        coordinator = next(n for n in graph.nodes if n.type == NodeType.COORDINATOR)
        assert coordinator.label == "釜爺 (Kamaji)"

    def test_render_timeline(self):
        tracer = AgentTracer()
        trace = tracer.start_workflow("feature", "Implement auth")
        tracer.on_agent_created("agent_1", "nekobasu", "explore")
        tracer.complete_workflow()

        renderer = WorkflowRenderer()
        timeline = renderer.render_timeline(trace)

        assert len(timeline) > 0
        assert timeline[0]["type"] == "workflow_start"

    def test_render_summary(self):
        tracer = AgentTracer()
        trace = tracer.start_workflow("feature", "Implement auth")
        tracer.on_agent_created("agent_1", "nekobasu", "explore")
        tracer.on_task_completed("agent_1", returncode=0, duration_ms=1000)
        tracer.complete_workflow()

        renderer = WorkflowRenderer()
        summary = renderer.render_summary(trace)

        assert "text" in summary
        assert summary["trace_id"] == trace.trace_id
        assert "agent_1" in summary["agent_stats"]


class TestVisExporter:
    """Test VisExporter class."""

    def test_export_trace(self):
        tracer = AgentTracer()
        trace = tracer.start_workflow("feature", "Implement auth")
        tracer.on_agent_created("agent_1", "nekobasu", "explore")
        tracer.on_task_started("agent_1", "Find auth code")
        tracer.on_task_completed("agent_1", returncode=0, duration_ms=1000)
        tracer.complete_workflow()

        exporter = VisExporter()
        vis_format = exporter.export_trace(trace)

        assert vis_format.trace_id == trace.trace_id
        assert vis_format.title == "Workflow: feature"
        assert len(vis_format.agents) == 1
        assert len(vis_format.events) > 0
        assert len(vis_format.nodes) > 0

    def test_export_tracer(self):
        tracer = AgentTracer()
        tracer.start_workflow("feature", "Implement auth")
        tracer.complete_workflow()

        exporter = VisExporter()
        vis_formats = exporter.export_tracer(tracer)

        assert len(vis_formats) == 1

    def test_save_to_file(self, tmp_path):
        tracer = AgentTracer()
        trace = tracer.start_workflow("feature", "Implement auth")
        tracer.complete_workflow()

        exporter = VisExporter()
        vis_format = exporter.export_trace(trace)

        output_file = tmp_path / "test_trace.json"
        exporter.save_to_file(vis_format, output_file)

        assert output_file.exists()

        # Verify JSON content
        with open(output_file) as f:
            data = json.load(f)
            assert data["trace_id"] == trace.trace_id

    def test_export_summary(self):
        tracer = AgentTracer()
        tracer.start_workflow("feature", "Implement auth")
        tracer.on_agent_created("agent_1", "nekobasu", "explore")
        tracer.complete_workflow()

        exporter = VisExporter()
        summary = exporter.export_summary(tracer)

        assert summary["total_traces"] == 1
        assert summary.get("agent_count", 0) >= 0
        assert "nekobasu" in summary["agent_usage"]


class TestNodeAndEdge:
    """Test Node and Edge dataclasses."""

    def test_workflow_node_to_dict(self):
        from kimi_tachi.vis.workflow_renderer import WorkflowNode

        node = WorkflowNode(
            id="node_1",
            type=NodeType.AGENT,
            label="Test Agent",
            icon="🚌",
            status="completed",
            duration_ms=1000,
        )

        d = node.to_dict()
        assert d["id"] == "node_1"
        assert d["type"] == "AGENT"
        assert d["icon"] == "🚌"

    def test_workflow_edge_to_dict(self):
        from kimi_tachi.vis.workflow_renderer import WorkflowEdge

        edge = WorkflowEdge(
            from_node="node_1",
            to_node="node_2",
            type=EdgeType.DELEGATES,
            label="delegates",
        )

        d = edge.to_dict()
        assert d["from"] == "node_1"
        assert d["to"] == "node_2"
        assert d["type"] == "DELEGATES"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
