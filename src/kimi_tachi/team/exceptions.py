"""
Team Management Exceptions
"""


class TeamError(Exception):
    """Base exception for team-related errors."""

    pass


class TeamNotFoundError(TeamError):
    """Raised when a team is not found."""

    pass


class AgentNotFoundError(TeamError):
    """Raised when an agent is not found in a team."""

    pass


class TeamConfigError(TeamError):
    """Raised when there's an error in team configuration."""

    pass
