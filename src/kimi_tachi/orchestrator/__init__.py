"""
Kimi-Tachi Hybrid Orchestrator

SDK-based orchestration with kimi-cli execution.
Phase 3.0: Native Agent Tool Support
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
]
