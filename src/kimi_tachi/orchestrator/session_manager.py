"""
Session Manager for kimi-tachi

Manages kimi-cli sessions to prevent resource leaks.
"""

from __future__ import annotations

import shutil
import time
import uuid
from pathlib import Path


class SessionManager:
    """
    Manages kimi-cli sessions to prevent disk space leaks.

    Strategies:
    1. TEMP: Create temp session and delete after use (default)
    2. REUSE: Reuse same session ID for all agents
    3. CLEANUP: Periodically clean old sessions
    """

    def __init__(
        self,
        strategy: str = "temp",  # temp, reuse, cleanup
        sessions_dir: Path | None = None,
        max_age_hours: int = 24,
    ):
        self.strategy = strategy
        self.sessions_dir = sessions_dir or (Path.home() / ".kimi" / "sessions")
        self.max_age_hours = max_age_hours

        # For reuse strategy
        self._reuse_session_id: str | None = None

        # For temp strategy
        self._temp_sessions: list[str] = []

    def get_session_id(self, agent: str) -> str:
        """
        Get session ID for an agent.

        Args:
            agent: Agent name (e.g., "calcifer")

        Returns:
            Session ID to use with kimi-cli --session
        """
        if self.strategy == "reuse":
            # Reuse same session for all agents
            if self._reuse_session_id is None:
                self._reuse_session_id = f"kimi-tachi-{uuid.uuid4().hex[:8]}"
            return self._reuse_session_id

        elif self.strategy == "temp":
            # Create unique temp session
            session_id = f"kimi-tachi-temp-{agent}-{uuid.uuid4().hex[:8]}"
            self._temp_sessions.append(session_id)
            return session_id

        else:  # cleanup strategy
            # Use default session creation
            return None

    def cleanup_session(self, session_id: str) -> bool:
        """
        Delete a specific session directory.

        Args:
            session_id: Session ID to delete

        Returns:
            True if deleted successfully
        """
        if not session_id or not session_id.startswith("kimi-tachi"):
            # Only delete our managed sessions
            return False

        session_path = self.sessions_dir / session_id
        if session_path.exists():
            try:
                shutil.rmtree(session_path)
                print(f"🧹 Cleaned up session: {session_id}")
                return True
            except Exception as e:
                print(f"⚠️ Failed to cleanup session {session_id}: {e}")
                return False
        return False

    def cleanup_all_temp(self) -> int:
        """
        Clean up all temporary sessions created by this manager.

        Returns:
            Number of sessions cleaned up
        """
        count = 0
        for session_id in self._temp_sessions:
            if self.cleanup_session(session_id):
                count += 1
        self._temp_sessions.clear()
        return count

    def cleanup_old_sessions(self, max_age_hours: int | None = None) -> int:
        """
        Clean up old sessions (global cleanup).

        Args:
            max_age_hours: Delete sessions older than this

        Returns:
            Number of sessions cleaned up
        """
        if max_age_hours is None:
            max_age_hours = self.max_age_hours

        count = 0
        current_time = time.time()

        for session_path in self.sessions_dir.iterdir():
            if not session_path.is_dir():
                continue

            # Check age
            try:
                stat = session_path.stat()
                age_hours = (current_time - stat.st_mtime) / 3600

                if age_hours > max_age_hours:
                    shutil.rmtree(session_path)
                    print(f"🧹 Cleaned up old session: {session_path.name} (age: {age_hours:.1f}h)")
                    count += 1
            except Exception as e:
                print(f"⚠️ Failed to check session {session_path.name}: {e}")

        return count

    def get_disk_usage(self) -> dict[str, int]:
        """
        Get disk usage of sessions directory.

        Returns:
            Dict with session counts and sizes
        """
        total_size = 0
        session_count = 0
        kimi_tachi_count = 0
        kimi_tachi_size = 0

        for session_path in self.sessions_dir.iterdir():
            if not session_path.is_dir():
                continue

            session_count += 1
            try:
                size = sum(f.stat().st_size for f in session_path.rglob("*") if f.is_file())
                total_size += size

                if session_path.name.startswith("kimi-tachi"):
                    kimi_tachi_count += 1
                    kimi_tachi_size += size
            except Exception:
                pass

        return {
            "total_sessions": session_count,
            "total_size_mb": total_size // (1024 * 1024),
            "kimi_tachi_sessions": kimi_tachi_count,
            "kimi_tachi_size_mb": kimi_tachi_size // (1024 * 1024),
        }

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup temp sessions"""
        if self.strategy == "temp":
            self.cleanup_all_temp()


def cleanup_sessions_cmd(max_age_hours: int = 24) -> None:
    """
    Command-line utility to clean up old sessions.

    Usage:
        python -m kimi_tachi.cleanup_sessions --age 24
    """
    import argparse

    parser = argparse.ArgumentParser(description="Clean up kimi-tachi sessions")
    parser.add_argument("--age", type=int, default=max_age_hours, help="Max age in hours")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted")
    args = parser.parse_args()

    manager = SessionManager()
    usage = manager.get_disk_usage()

    print("Current usage:")
    print(f"  Total sessions: {usage['total_sessions']}")
    print(f"  Total size: {usage['total_size_mb']} MB")
    print(f"  kimi-tachi sessions: {usage['kimi_tachi_sessions']}")
    print(f"  kimi-tachi size: {usage['kimi_tachi_size_mb']} MB")

    if args.dry_run:
        print(f"\nWould delete sessions older than {args.age} hours")
    else:
        print(f"\nCleaning up sessions older than {args.age} hours...")
        count = manager.cleanup_old_sessions(args.age)
        print(f"Deleted {count} sessions")

        # Show new usage
        usage = manager.get_disk_usage()
        print("\nNew usage:")
        print(f"  Total sessions: {usage['total_sessions']}")
        print(f"  Total size: {usage['total_size_mb']} MB")


if __name__ == "__main__":
    cleanup_sessions_cmd()
