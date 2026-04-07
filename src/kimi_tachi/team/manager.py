"""
Team Manager - Central management for multi-team support

This module provides:
- Team registration and discovery
- Current team management (persistent)
- Agent resolution (both implicit and explicit)
- Session isolation by team
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml

from .exceptions import AgentNotFoundError, TeamConfigError, TeamNotFoundError


@dataclass
class Team:
    """Team definition."""

    id: str
    name: str
    description: str
    coordinator: str
    theme: str
    icon: str
    agent_count: int
    agents_dir: str
    memory_namespace: str
    workflow_patterns: dict[str, str]
    agents: dict[str, dict]  # agent_name -> agent_info


@dataclass
class ResolvedAgent:
    """Resolved agent reference."""

    team_id: str
    agent_name: str
    agent_file: str
    team: Team


class TeamManager:
    """
    Team management center.

    Singleton pattern ensures consistent team state across the application.
    """

    _instance: TeamManager | None = None

    # Configuration paths
    _TEAMS_CONFIG_PATH: Path = Path(__file__).parent.parent.parent.parent / "agents" / "teams.yaml"

    # User state storage
    _USER_STATE_DIR: Path = Path.home() / ".kimi-tachi"
    _CURRENT_TEAM_FILE: Path = _USER_STATE_DIR / "current_team"

    def __new__(cls) -> TeamManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return

        self._teams: dict[str, Team] = {}
        self._current_team_id: str | None = None
        self._explicit_team: str | None = None  # Temporary override

        self._load_teams()
        self._load_user_state()
        self._initialized = True

    # ========== Loading Methods ==========

    def _load_teams(self) -> None:
        """Load all team definitions from teams.yaml."""
        if not self._TEAMS_CONFIG_PATH.exists():
            raise TeamConfigError(f"Teams config not found: {self._TEAMS_CONFIG_PATH}")

        with open(self._TEAMS_CONFIG_PATH) as f:
            config = yaml.safe_load(f)

        for team_id, team_config in config.get("teams", {}).items():
            self._teams[team_id] = Team(
                id=team_id,
                name=team_config["name"],
                description=team_config.get("description", ""),
                coordinator=team_config["coordinator"],
                theme=team_config.get("theme", "default"),
                icon=team_config.get("icon", "🤖"),
                agent_count=team_config.get("agent_count", 0),
                agents_dir=team_config["agents_dir"],
                memory_namespace=team_config.get("memory_namespace", team_id),
                workflow_patterns=team_config.get("workflow_patterns", {}),
                agents=team_config.get("agents", {}),
            )

    def _load_user_state(self) -> None:
        """Load user state (current team)."""
        self._USER_STATE_DIR.mkdir(parents=True, exist_ok=True)

        # Check environment variable first (highest priority for persistence)
        env_team = os.getenv("KIMI_TACHI_DEFAULT_TEAM")
        if env_team and env_team in self._teams:
            self._current_team_id = env_team
            return

        # Check saved state file
        if self._CURRENT_TEAM_FILE.exists():
            saved_team = self._CURRENT_TEAM_FILE.read_text().strip()
            if saved_team in self._teams:
                self._current_team_id = saved_team
                return

        # Fall back to default from config
        with open(self._TEAMS_CONFIG_PATH) as f:
            config = yaml.safe_load(f)
        default_team = config.get("default_team")
        if default_team and default_team in self._teams:
            self._current_team_id = default_team
        else:
            # Last resort: first team in list
            self._current_team_id = list(self._teams.keys())[0]

        self._save_current_team()

    def _save_current_team(self) -> None:
        """Persist current team to state file."""
        self._CURRENT_TEAM_FILE.write_text(self._current_team_id)

    # ========== Query Methods ==========

    @property
    def current_team(self) -> Team:
        """Get the currently active team."""
        if self._current_team_id not in self._teams:
            raise TeamNotFoundError(f"Current team '{self._current_team_id}' not found")
        return self._teams[self._current_team_id]

    def get_team(self, team_id: str) -> Team:
        """Get a specific team by ID."""
        if team_id not in self._teams:
            available = list(self._teams.keys())
            raise TeamNotFoundError(f"Team '{team_id}' not found. Available: {available}")
        return self._teams[team_id]

    def list_teams(self) -> list[Team]:
        """List all available teams."""
        return list(self._teams.values())

    def resolve_agent(self, agent_ref: str) -> ResolvedAgent:
        """
        Resolve an agent reference.

        Args:
            agent_ref: Agent reference in format:
                - "agent_name" (implicit, uses current team)
                - "team_id.agent_name" (explicit)

        Returns:
            ResolvedAgent with team_id, agent_name, agent_file, and team

        Raises:
            TeamNotFoundError: If explicit team doesn't exist
            AgentNotFoundError: If agent doesn't exist in team
        """
        if "." in agent_ref:
            # Explicit team specification: "team.agent"
            team_id, agent_name = agent_ref.split(".", 1)
            team = self.get_team(team_id)
        else:
            # Implicit: use current team
            team = self.current_team
            agent_name = agent_ref

        # Verify agent file exists
        agent_file = self._get_agent_file(team, agent_name)
        if not agent_file.exists():
            available = self._list_available_agents(team)
            raise AgentNotFoundError(
                f"Agent '{agent_name}' not found in team '{team.id}'. Available: {available}"
            )

        return ResolvedAgent(
            team_id=team.id,
            agent_name=agent_name,
            agent_file=str(agent_file),
            team=team,
        )

    def _get_agent_file(self, team: Team, agent_name: str) -> Path:
        """Get the file path for an agent."""
        agents_dir = Path(__file__).parent.parent.parent.parent / "agents" / team.agents_dir
        return agents_dir / f"{agent_name}.yaml"

    def _list_available_agents(self, team: Team) -> list[str]:
        """List all available agent names in a team."""
        agents_dir = Path(__file__).parent.parent.parent.parent / "agents" / team.agents_dir
        if not agents_dir.exists():
            return []
        return sorted([f.stem for f in agents_dir.glob("*.yaml")])

    # ========== Switching Methods ==========

    def switch_team(self, team_id: str, *, persist: bool = True) -> None:
        """
        Switch the current team.

        Args:
            team_id: Target team ID
            persist: Whether to persist the change (default: True)

        Raises:
            TeamNotFoundError: If team doesn't exist
        """
        if team_id not in self._teams:
            available = list(self._teams.keys())
            raise TeamNotFoundError(f"Team '{team_id}' not found. Available: {available}")

        old_team = self._current_team_id
        self._current_team_id = team_id

        if persist:
            self._save_current_team()

        # Trigger team switch callback
        self._on_team_switched(old_team, team_id)

    def set_explicit_team(self, team_id: str | None) -> None:
        """
        Set an explicit team override (temporary, not persisted).

        Used for CLI --team flag to temporarily use a different team
        without changing the default.
        """
        if team_id is not None and team_id not in self._teams:
            available = list(self._teams.keys())
            raise TeamNotFoundError(f"Team '{team_id}' not found. Available: {available}")
        self._explicit_team = team_id

    @property
    def effective_team(self) -> Team:
        """
        Get the effective team (considering explicit override).

        Returns the explicit team if set, otherwise the current team.
        """
        if self._explicit_team:
            return self._teams[self._explicit_team]
        return self.current_team

    def get_effective_team_id(self) -> str:
        """Get the effective team ID."""
        return self._explicit_team or self._current_team_id

    # ========== Context Manager for Temporary Switching ==========

    def with_team(self, team_id: str):
        """
        Context manager for temporary team switching.

        Usage:
            with team_manager.with_team("content"):
                # Within this block, effective_team is "content"
                result = orchestrator.execute(task)
            # Outside block, reverts to previous team
        """
        return _TeamContext(self, team_id)

    # ========== Coordinator Access ==========

    def get_coordinator_agent(self, team_id: str | None = None) -> ResolvedAgent:
        """
        Get the coordinator agent for a team.

        Args:
            team_id: Team ID (default: effective team)

        Returns:
            ResolvedAgent for the coordinator
        """
        team = self.get_team(team_id) if team_id else self.effective_team
        return self.resolve_agent(f"{team.id}.{team.coordinator}")

    # ========== Session Helpers ==========

    def make_session_id(self, base_id: str) -> str:
        """
        Create a team-scoped session ID.

        Args:
            base_id: Base session identifier

        Returns:
            Team-scoped ID: "{team_id}.{base_id}"
        """
        return f"{self.get_effective_team_id()}.{base_id}"

    def parse_session_id(self, session_id: str) -> tuple[str, str]:
        """
        Parse a team-scoped session ID.

        Args:
            session_id: Session ID (format: "team_id.base_id")

        Returns:
            Tuple of (team_id, base_id)
        """
        if "." in session_id:
            team_id, base_id = session_id.split(".", 1)
            return team_id, base_id
        # Legacy format (no team prefix)
        return self.get_effective_team_id(), session_id

    def is_current_team_session(self, session_id: str) -> bool:
        """Check if a session belongs to the current team."""
        team_id, _ = self.parse_session_id(session_id)
        return team_id == self.get_effective_team_id()

    # ========== Internal Callbacks ==========

    def _on_team_switched(self, old_team: str | None, new_team: str) -> None:
        """Called when team is switched. Override for custom behavior."""
        # Clear any team-specific caches
        pass


class _TeamContext:
    """Context manager for temporary team switching."""

    def __init__(self, manager: TeamManager, team_id: str):
        self.manager = manager
        self.team_id = team_id
        self._previous_team: str | None = None

    def __enter__(self) -> _TeamContext:
        self._previous_team = self.manager._current_team_id
        self.manager.switch_team(self.team_id, persist=False)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if self._previous_team:
            self.manager.switch_team(self._previous_team, persist=False)
        return False


# Convenience function for getting the singleton
def get_team_manager() -> TeamManager:
    """Get the singleton TeamManager instance."""
    return TeamManager()
