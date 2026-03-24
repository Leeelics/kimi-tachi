"""
Tests for tracing module.

Author: kimi-tachi Team
"""

import time
import pytest

from kimi_tachi.tracing import (
    AgentEvent,
    AgentEventType,
    AgentTracer,
    WorkflowTrace,
    get_tracer,
    reset_tracer,
)


class TestAgentEvent:
    """Test AgentEvent dataclass."""
    
    def test_creation(self):
        event = AgentEvent(
            event_type=AgentEventType.CREATED,
            agent_id="agent_1",
            personality="nekobasu",
        )
        assert event.event_type == AgentEventType.CREATED
        assert event.agent_id == "agent_1"
        assert event.personality == "nekobasu"
    
    def test_to_dict(self):
        event = AgentEvent(
            event_type=AgentEventType.COMPLETED,
            agent_id="agent_1",
            personality="calcifer",
            duration_ms=1000,
        )
        d = event.to_dict()
        assert d["event_type"] == "COMPLETED"
        assert d["agent_id"] == "agent_1"
        assert d["duration_ms"] == 1000
        assert "datetime" in d


class TestWorkflowTrace:
    """Test WorkflowTrace dataclass."""
    
    def test_creation(self):
        trace = WorkflowTrace(
            workflow_type="feature",
            task_description="Implement auth",
        )
        assert trace.workflow_type == "feature"
        assert trace.task_description == "Implement auth"
        assert trace.status == "running"
    
    def test_add_event(self):
        trace = WorkflowTrace()
        event = AgentEvent(event_type=AgentEventType.CREATED)
        trace.add_event(event)
        assert len(trace.events) == 1
    
    def test_complete(self):
        trace = WorkflowTrace()
        trace.complete("completed")
        assert trace.status == "completed"
        assert trace.end_time is not None
    
    def test_duration_ms(self):
        trace = WorkflowTrace()
        time.sleep(0.01)  # Small delay
        trace.complete()
        assert trace.duration_ms > 0
    
    def test_agent_count(self):
        trace = WorkflowTrace()
        trace.add_event(AgentEvent(agent_id="agent_1"))
        trace.add_event(AgentEvent(agent_id="agent_1"))
        trace.add_event(AgentEvent(agent_id="agent_2"))
        assert trace.agent_count == 2


class TestAgentTracer:
    """Test AgentTracer class."""
    
    def setup_method(self):
        reset_tracer()
    
    def test_init(self):
        tracer = AgentTracer(debug=True)
        assert tracer.max_traces == 100
        assert tracer.debug is True
    
    def test_start_workflow(self):
        tracer = AgentTracer()
        trace = tracer.start_workflow("feature", "Implement auth")
        assert trace.workflow_type == "feature"
        assert tracer.current_trace == trace
    
    def test_on_agent_created(self):
        tracer = AgentTracer()
        tracer.start_workflow("feature", "Implement auth")
        event = tracer.on_agent_created("agent_1", "nekobasu", "explore")
        assert event.event_type == AgentEventType.CREATED
        assert event.agent_id == "agent_1"
    
    def test_on_task_started(self):
        tracer = AgentTracer()
        tracer.start_workflow("feature", "Implement auth")
        event = tracer.on_task_started("agent_1", "Find auth code")
        assert event.event_type == AgentEventType.STARTED
        assert event.task_summary == "Find auth code"
    
    def test_on_task_completed(self):
        tracer = AgentTracer()
        tracer.start_workflow("feature", "Implement auth")
        event = tracer.on_task_completed("agent_1", returncode=0, duration_ms=1000)
        assert event.event_type == AgentEventType.COMPLETED
        assert event.duration_ms == 1000
    
    def test_on_task_failed(self):
        tracer = AgentTracer()
        tracer.start_workflow("feature", "Implement auth")
        event = tracer.on_task_completed("agent_1", returncode=1, duration_ms=500)
        assert event.event_type == AgentEventType.FAILED
    
    def test_complete_workflow(self):
        tracer = AgentTracer()
        tracer.start_workflow("feature", "Implement auth")
        trace = tracer.complete_workflow("completed")
        assert trace.status == "completed"
        assert tracer.current_trace is None
    
    def test_get_stats(self):
        tracer = AgentTracer()
        tracer.start_workflow("feature", "Implement auth")
        tracer.on_agent_created("agent_1", "nekobasu", "explore")
        tracer.complete_workflow()
        
        stats = tracer.get_stats()
        assert stats["total_traces"] == 1
        assert stats["completed_workflows"] == 1
    
    def test_clear(self):
        tracer = AgentTracer()
        tracer.start_workflow("feature", "Implement auth")
        tracer.complete_workflow()
        
        count = tracer.clear()
        assert count == 1
        assert len(tracer.traces) == 0


class TestGlobalTracer:
    """Test global tracer functions."""
    
    def setup_method(self):
        reset_tracer()
    
    def test_get_tracer_creates_instance(self):
        tracer = get_tracer()
        assert isinstance(tracer, AgentTracer)
    
    def test_get_tracer_returns_same_instance(self):
        tracer1 = get_tracer()
        tracer2 = get_tracer()
        assert tracer1 is tracer2
    
    def test_reset_tracer(self):
        tracer1 = get_tracer()
        reset_tracer()
        tracer2 = get_tracer()
        assert tracer1 is not tracer2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
