"""
Context Manager: Persistent state between agent executions
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class SessionState:
    """Full session state"""

    session_id: str
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())

    # Workflow progress
    current_phase: str = "idle"
    completed_phases: list[str] = field(default_factory=list)

    # Context
    shared_context: dict = field(default_factory=dict)
    file_states: dict = field(default_factory=dict)
    decisions: list[dict] = field(default_factory=list)
    messages: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> SessionState:
        return cls(**data)


class ContextManager:
    """
    Manages persistent context and state across agent workflows.
    """

    def __init__(self, work_dir: Path | str, session_id: str | None = None):
        self.work_dir = Path(work_dir).resolve()
        self.state_dir = self.work_dir / ".kimi-tachi"

        # Generate or use session ID
        self.session_id = session_id or self._generate_session_id()
        self.state_file = self.state_dir / f"{self.session_id}.json"

        # Ensure state directory exists
        self.state_dir.mkdir(parents=True, exist_ok=True)

        # Load or create state
        self.state = self._load_state()

    def _generate_session_id(self) -> str:
        """Generate unique session ID"""
        from uuid import uuid4

        return datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + str(uuid4())[:8]

    def _load_state(self) -> SessionState:
        """Load state from disk or create new"""
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text())
                return SessionState.from_dict(data)
            except Exception:
                pass
        return SessionState(session_id=self.session_id)

    def save(self):
        """Save state to disk"""
        self.state.last_updated = datetime.now().isoformat()
        self.state_file.write_text(json.dumps(self.state.to_dict(), indent=2))

    def add_decision(self, decision: str, agent: str, reason: str = ""):
        """Record a decision"""
        self.state.decisions.append(
            {
                "timestamp": datetime.now().isoformat(),
                "agent": agent,
                "decision": decision,
                "reason": reason,
            }
        )
        self.save()

    def add_message(self, agent: str, role: str, content: str):
        """Add a message to the conversation history"""
        self.state.messages.append(
            {
                "timestamp": datetime.now().isoformat(),
                "agent": agent,
                "role": role,
                "content": content[:1000],  # Truncate long messages
            }
        )
        # Keep only last 100 messages
        if len(self.state.messages) > 100:
            self.state.messages = self.state.messages[-100:]
        self.save()

    def update_file_state(self, filepath: str, status: str, checksum: str = ""):
        """Track file modifications"""
        self.state.file_states[filepath] = {
            "last_modified": datetime.now().isoformat(),
            "status": status,  # created, modified, deleted
            "checksum": checksum,
        }
        self.save()

    def update_phase(self, phase: str, completed: bool = False):
        """Update current workflow phase"""
        self.state.current_phase = phase
        if completed and phase not in self.state.completed_phases:
            self.state.completed_phases.append(phase)
        self.save()

    def get_shared_context(self) -> dict:
        """Get shared context"""
        return self.state.shared_context

    def set_shared_context(self, key: str, value: Any):
        """Set shared context value"""
        self.state.shared_context[key] = value
        self.save()

    def build_context_prompt(self) -> str:
        """Build context prompt for agents"""
        lines = ["## Session Context\n"]

        if self.state.completed_phases:
            lines.append("### Completed Phases")
            for phase in self.state.completed_phases:
                lines.append(f"- ✅ {phase}")
            lines.append("")

        if self.state.current_phase != "idle":
            lines.append(f"### Current Phase: {self.state.current_phase}\n")

        if self.state.decisions:
            lines.append("### Key Decisions")
            for d in self.state.decisions[-5:]:  # Last 5
                lines.append(f"- **{d['agent']}**: {d['decision']}")
            lines.append("")

        if self.state.file_states:
            modified = [
                f
                for f, s in self.state.file_states.items()
                if s["status"] in ("created", "modified")
            ]
            if modified:
                lines.append("### Files Modified")
                for f in modified[-10:]:
                    lines.append(f"- `{f}`")
                lines.append("")

        return "\n".join(lines)

    def list_sessions(self) -> list[dict]:
        """List all sessions in this work directory"""
        sessions = []
        for f in self.state_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                sessions.append(
                    {
                        "id": data["session_id"],
                        "started": data["started_at"],
                        "updated": data["last_updated"],
                        "phase": data["current_phase"],
                    }
                )
            except Exception:
                pass
        return sorted(sessions, key=lambda x: x["updated"], reverse=True)
