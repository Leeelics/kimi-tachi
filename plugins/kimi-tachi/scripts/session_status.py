#!/usr/bin/env python3
"""
Get detailed status for a specific kimi-cli session.

Reads the session directory on disk to report subagents, file sizes,
and last activity. Plugin scripts run outside the kimi-cli runtime,
so this uses filesystem observation rather than internal APIs.
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
    if os.getenv("KIMI_DATA_DIR"):
        candidates.insert(0, Path(os.getenv("KIMI_DATA_DIR")))
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _find_session_dir(session_id: str) -> Path | None:
    """Locate a session directory by its ID."""
    share = _get_kimi_share_dir()
    if share is None:
        return None
    sessions = share / "sessions"
    if not sessions.exists():
        return None
    for work_dir_hash_dir in sessions.iterdir():
        if not work_dir_hash_dir.is_dir():
            continue
        candidate = work_dir_hash_dir / session_id
        if candidate.is_dir():
            return candidate
    return None


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
            # Add wire/context size for quick diagnostics
            wire_path = entry / "wire.jsonl"
            context_path = entry / "context.jsonl"
            meta["wire_size"] = wire_path.stat().st_size if wire_path.exists() else 0
            meta["context_size"] = context_path.stat().st_size if context_path.exists() else 0
            results.append(meta)

    results.sort(key=lambda m: m.get("created_at", 0))
    return results


def session_status(session_id: str) -> dict:
    """Build a status summary for the given session."""
    session_dir = _find_session_dir(session_id)
    if session_dir is None:
        return {
            "success": False,
            "error": f"Session '{session_id}' not found.",
        }

    wire_path = session_dir / "wire.jsonl"
    context_path = session_dir / "context.jsonl"
    state_path = session_dir / "state.json"

    mtimes = []
    sizes = {}
    for name, path in (
        ("wire", wire_path),
        ("context", context_path),
        ("state", state_path),
    ):
        if path.exists():
            st = path.stat()
            mtimes.append(st.st_mtime)
            sizes[name] = st.st_size
        else:
            sizes[name] = 0

    subagents = _scan_subagents(session_dir)
    running = [s for s in subagents if s.get("status", "").startswith("running")]
    failed = [s for s in subagents if s.get("status") == "failed"]

    return {
        "success": True,
        "session_id": session_id,
        "session_dir": str(session_dir),
        "last_updated": max(mtimes) if mtimes else 0,
        "files": sizes,
        "subagent_count": len(subagents),
        "running_subagents": len(running),
        "failed_subagents": len(failed),
        "subagents": [
            {
                "agent_id": s.get("agent_id", "unknown"),
                "subagent_type": s.get("subagent_type", "unknown"),
                "status": s.get("status", "unknown"),
                "description": s.get("description", ""),
                "created_at": s.get("created_at", 0),
                "updated_at": s.get("updated_at", 0),
                "wire_size": s.get("wire_size", 0),
                "context_size": s.get("context_size", 0),
            }
            for s in subagents
        ],
        "note": (
            "This scans the filesystem because plugin scripts run outside "
            "the kimi-cli runtime. For real-time status, use TaskList() "
            "or TaskOutput() inside the coordinator agent."
        ),
    }


def main() -> None:
    params = {}
    if not sys.stdin.isatty():
        with contextlib.suppress(json.JSONDecodeError):
            params = json.load(sys.stdin)

    session_id = params.get("session_id", "")
    if not session_id:
        print(json.dumps({"success": False, "error": "Missing required parameter: session_id"}))
        sys.exit(1)

    result = session_status(session_id)
    print(json.dumps(result, indent=2, default=str))
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
