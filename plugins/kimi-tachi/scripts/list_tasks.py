#!/usr/bin/env python3
"""
List background tasks and subagents for the current or specified session.

Scans the kimi session directory for subagent metadata and produces a
human-readable summary. Plugin scripts run outside the kimi-cli runtime,
so this uses filesystem observation rather than the internal
BackgroundTaskManager API.
"""

from __future__ import annotations

import contextlib
import json
import os
import sys
from pathlib import Path


def _get_kimi_share_dir() -> Path | None:
    """Resolve the kimi data directory using known platform paths."""
    candidates = []
    if sys.platform == "darwin":
        candidates.append(Path.home() / "Library" / "Application Support" / "kimi")
    else:
        candidates.append(Path.home() / ".local" / "share" / "kimi")
    # Allow override via environment variable
    if os.getenv("KIMI_DATA_DIR"):
        candidates.insert(0, Path(os.getenv("KIMI_DATA_DIR")))
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _find_sessions_root() -> Path | None:
    """Find the sessions root directory."""
    share = _get_kimi_share_dir()
    if share is None:
        return None
    sessions = share / "sessions"
    return sessions if sessions.exists() else None


def _scan_subagents(session_dir: Path) -> list[dict]:
    """Read all subagent meta.json files in a session directory."""
    subagents_dir = session_dir / "subagents"
    if not subagents_dir.is_dir():
        return []

    results = []
    for entry in subagents_dir.iterdir():
        if not entry.is_dir():
            continue
        meta_path = entry / "meta.json"
        if not meta_path.exists():
            continue
        with contextlib.suppress(json.JSONDecodeError, OSError):
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            results.append(meta)

    results.sort(key=lambda m: m.get("created_at", 0))
    return results


def _summarize_subagent(meta: dict) -> dict:
    """Extract display fields from subagent metadata."""
    return {
        "agent_id": meta.get("agent_id", "unknown"),
        "subagent_type": meta.get("subagent_type", "unknown"),
        "status": meta.get("status", "unknown"),
        "description": meta.get("description", ""),
        "created_at": meta.get("created_at", 0),
        "updated_at": meta.get("updated_at", 0),
    }


def list_tasks(session_id: str | None = None) -> dict:
    """List subagents across all discovered sessions or a specific session."""
    sessions_root = _find_sessions_root()
    if sessions_root is None:
        return {
            "success": False,
            "error": "kimi data directory not found. Is kimi-cli installed?",
            "tasks": [],
        }

    # If a specific session is requested, try to find it
    target_sessions: list[Path] = []
    if session_id:
        found = False
        for work_dir_hash_dir in sessions_root.iterdir():
            if not work_dir_hash_dir.is_dir():
                continue
            candidate = work_dir_hash_dir / session_id
            if candidate.is_dir():
                target_sessions.append(candidate)
                found = True
                break
        if not found:
            return {
                "success": False,
                "error": f"Session '{session_id}' not found.",
                "tasks": [],
            }
    else:
        # Gather recent sessions (up to 10)
        all_sessions: list[tuple[float, Path]] = []
        for work_dir_hash_dir in sessions_root.iterdir():
            if not work_dir_hash_dir.is_dir():
                continue
            for session_dir in work_dir_hash_dir.iterdir():
                if not session_dir.is_dir():
                    continue
                mtime = 0.0
                for f in ("wire.jsonl", "context.jsonl", "state.json"):
                    fp = session_dir / f
                    if fp.exists():
                        mtime = max(mtime, fp.stat().st_mtime)
                all_sessions.append((mtime, session_dir))
        all_sessions.sort(reverse=True)
        target_sessions = [s for _, s in all_sessions[:10]]

    sessions_summary = []
    for session_dir in target_sessions:
        subagents = _scan_subagents(session_dir)
        sid = session_dir.name
        sessions_summary.append({
            "session_id": sid,
            "subagent_count": len(subagents),
            "subagents": [_summarize_subagent(m) for m in subagents],
        })

    return {
        "success": True,
        "tasks": sessions_summary,
        "note": (
            "This scans the filesystem because plugin scripts run outside "
            "the kimi-cli runtime. For real-time background task state, "
            "use TaskList() inside the coordinator agent."
        ),
    }


def main() -> None:
    params = {}
    if not sys.stdin.isatty():
        with contextlib.suppress(json.JSONDecodeError):
            params = json.load(sys.stdin)

    session_id = params.get("session_id")
    result = list_tasks(session_id)
    print(json.dumps(result, indent=2, default=str))
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
