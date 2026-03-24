"""
Kimi-Tachi Hybrid Orchestrator

SDK-based orchestration with kimi-cli execution.
Phase 3.0/4.0: Native Agent Tool Support + Tracing
"""

from .context_manager import ContextManager
from .hybrid_orchestrator import HybridOrchestrator
from .native_agent_orchestrator import (
    AgentPersonality,
    AgentResult,
    AgentType,
    NativeAgentInstance,
    NativeAgentOrchestrator,
    PERSONALITY_TO_TYPE,
    AGENT_PERSONALITIES,
    get_personality_by_name,
    get_personality_by_role,
)
from .session_manager import SessionManager
from .workflow_engine import Phase, Workflow, WorkflowEngine, WorkflowPhase

# Optional tracing imports (Phase 4)
try:
    from ..tracing import (
        AgentEvent,
        AgentEventType,
        AgentTracer,
        WorkflowTrace,
        get_tracer,
        reset_tracer,
    )
    TRACING_EXPORTS = [
        "AgentEvent",
        "AgentEventType",
        "AgentTracer",
        "WorkflowTrace",
        "get_tracer",
        "reset_tracer",
    ]
except ImportError:
    TRACING_EXPORTS = []

# Optional vis imports (Phase 4)
try:
    from ..vis import (
        WorkflowRenderer,
        VisExporter,
        export_for_kimi_vis,
    )
    VIS_EXPORTS = [
        "WorkflowRenderer",
        "VisExporter",
        "export_for_kimi_vis",
    ]
except ImportError:
    VIS_EXPORTS = []

__all__ = [
    "HybridOrchestrator",
    "NativeAgentOrchestrator",
    "ContextManager",
    "WorkflowEngine",
    "Phase",
    "Workflow",
    "WorkflowPhase",
    "SessionManager",
    # Native agent exports
    "AgentPersonality",
    "AgentType",
    "AgentResult",
    "NativeAgentInstance",
    "PERSONALITY_TO_TYPE",
    "AGENT_PERSONALITIES",
    "get_personality_by_name",
    "get_personality_by_role",
] + TRACING_EXPORTS + VIS_EXPORTS
