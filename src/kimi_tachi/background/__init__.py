"""
Background Task Support for kimi-tachi

Enables long-running tasks to execute asynchronously using kimi-cli 1.25.0+'s
background task functionality.

v0.4.0: Added background task support
"""

from .task_manager import BackgroundTaskManager, TaskStatus, TaskInfo

__all__ = ["BackgroundTaskManager", "TaskStatus", "TaskInfo"]
