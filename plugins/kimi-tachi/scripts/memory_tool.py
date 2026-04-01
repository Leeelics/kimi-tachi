#!/usr/bin/env python3
"""
Memory Tool for kimi-tachi plugin

Provides memory operations as tools for use within Kimi CLI conversations.
"""

import argparse
import asyncio
import contextlib
import json
import sys

# Add kimi-tachi to path
try:
    from kimi_tachi.memory import TachiMemory

    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False


async def search_memory(query: str, limit: int = 5) -> dict:
    """Search project memory."""
    if not MEMORY_AVAILABLE:
        return {"error": "Memory not available"}

    try:
        memory = await TachiMemory.init(".")
        results = await memory.search(query, limit=limit)

        return {
            "query": query,
            "results_found": len(results),
            "results": [
                {
                    "type": r.get("type", "unknown"),
                    "source": r.get("source", r.get("file", "unknown")),
                    "content": r.get("content", "")[:200],
                    "name": r.get("name", ""),
                    "signature": r.get("signature", ""),
                }
                for r in results[:limit]
            ],
        }
    except Exception as e:
        return {"error": str(e)}


async def global_search(query: str, limit: int = 5) -> dict:
    """Search across all projects."""
    if not MEMORY_AVAILABLE:
        return {"error": "Memory not available"}

    try:
        memory = await TachiMemory.init(".")
        results = await memory.search_global_memory(query, limit=limit)

        return {
            "query": query,
            "results_found": len(results),
            "projects": list({r.get("project", "unknown") for r in results}),
            "results": [
                {
                    "project": r.get("project", "unknown"),
                    "source": r.get("source", "unknown"),
                    "content": r.get("content", "")[:200],
                    "type": r.get("type", "unknown"),
                }
                for r in results[:limit]
            ],
        }
    except Exception as e:
        return {"error": str(e)}


async def recall_agent(agent: str, task: str = "") -> dict:
    """Recall context for an agent."""
    if not MEMORY_AVAILABLE:
        return {"error": "Memory not available"}

    try:
        memory = await TachiMemory.init(".")
        context = await memory.recall_agent_context(agent, query=task)

        return {
            "agent": agent,
            "session_id": context.session_id,
            "recent_memories_count": len(context.recent_memories),
            "relevant_code_count": len(context.relevant_code),
            "cross_project_knowledge_count": len(context.cross_project_knowledge),
            "recent_memories": [
                {"source": m.get("source"), "content": m.get("content", "")[:150]}
                for m in context.recent_memories[:3]
            ],
            "relevant_code": [
                {"name": c.get("name"), "file": c.get("file")} for c in context.relevant_code[:3]
            ],
            "cross_project_knowledge": [
                {"project": k.get("project"), "content": k.get("content", "")[:100]}
                for k in context.cross_project_knowledge[:2]
            ]
            if context.cross_project_knowledge
            else [],
        }
    except Exception as e:
        return {"error": str(e)}


async def store_decision(content: str, category: str = "finding", tags: list = None) -> dict:
    """Store a decision to memory."""
    if not MEMORY_AVAILABLE:
        return {"error": "Memory not available"}

    try:
        memory = await TachiMemory.init(".")

        # Store via context manager if available
        if memory._context_manager:
            memory_id = await memory._context_manager.store_agent_output(
                agent="user",
                content=content,
                memory_type=category,
                metadata={"tags": tags or [], "category": category},
            )
            return {
                "stored": True,
                "memory_id": memory_id[:8] if memory_id else None,
                "category": category,
                "tags": tags or [],
            }
        else:
            return {"error": "Context manager not available"}
    except Exception as e:
        return {"error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Memory tool for kimi-tachi")
    parser.add_argument("action", choices=["search", "global-search", "recall", "store"])

    args, unknown = parser.parse_known_args()

    # Parse additional arguments from JSON stdin (from kimi-cli)
    params = {}
    if not sys.stdin.isatty():
        with contextlib.suppress(json.JSONDecodeError):
            params = json.load(sys.stdin)

    # Also parse command line args
    for arg in unknown:
        if arg.startswith("--"):
            key = arg[2:].replace("-", "_")
            params[key] = True

    async def run():
        if args.action == "search":
            result = await search_memory(
                query=params.get("query", ""),
                limit=params.get("limit", 5),
            )
        elif args.action == "global-search":
            result = await global_search(
                query=params.get("query", ""),
                limit=params.get("limit", 5),
            )
        elif args.action == "recall":
            result = await recall_agent(
                agent=params.get("agent", ""),
                task=params.get("task", ""),
            )
        elif args.action == "store":
            result = await store_decision(
                content=params.get("content", ""),
                category=params.get("category", "finding"),
                tags=params.get("tags", []),
            )
        else:
            result = {"error": "Unknown action"}

        print(json.dumps(result, indent=2, default=str))

    asyncio.run(run())


if __name__ == "__main__":
    main()
