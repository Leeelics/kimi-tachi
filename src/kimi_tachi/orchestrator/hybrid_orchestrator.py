"""
Hybrid Orchestrator: SDK control + kimi-cli execution

Phase 3.0 Update: Native Agent Tool Support
- Uses kimi-cli 1.25.0+ native Agent tool
- Preserves anime character personalities
- Requires kimi-cli >=1.25.0 (dropped legacy support)
- Multi-team aware: agents and workflows are loaded from TeamManager

Environment Variables:
    KIMI_TACHI_AGENT_MODE: "native", "legacy", or "auto" (default: auto)
    KIMI_TACHI_DEBUG_AGENTS: Enable debug logging (default: false)
    KIMI_TACHI_ENABLE_CACHE: Enable context cache (default: true)
"""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Optional SDK import - gracefully degrade if not available
try:
    from kimi_sdk import Kimi, Message, generate

    KIMI_SDK_AVAILABLE = True
except ImportError:
    KIMI_SDK_AVAILABLE = False
    Kimi = None
    Message = None
    generate = None

# Optional context cache import
try:
    from ..context import ContextCacheManager

    CONTEXT_CACHE_AVAILABLE = True
except ImportError:
    CONTEXT_CACHE_AVAILABLE = False
    ContextCacheManager = None

# Optional native agent orchestrator import
try:
    from .native_agent_orchestrator import (
        PERSONALITY_TO_TYPE,
        AgentPersonality,
        NativeAgentOrchestrator,
        get_personality_by_name,
        get_personality_by_role,
    )

    NATIVE_AGENT_AVAILABLE = True
except ImportError:
    NATIVE_AGENT_AVAILABLE = False
    NativeAgentOrchestrator = None
    AgentPersonality = None
    PERSONALITY_TO_TYPE = None
    get_personality_by_name = None
    get_personality_by_role = None

# Optional team management import
try:
    from ..team import AgentNotFoundError, TeamManager, TeamNotFoundError

    TEAM_AVAILABLE = True
except ImportError:
    TEAM_AVAILABLE = False
    TeamManager = None
    TeamNotFoundError = Exception
    AgentNotFoundError = Exception


@dataclass
class AgentResult:
    """Result from agent execution"""

    agent: str
    task: str
    stdout: str
    stderr: str
    returncode: int
    context_summary: dict = field(default_factory=dict)


@dataclass
class SharedContext:
    """Shared context across all agents"""

    project_structure: dict = field(default_factory=dict)
    code_patterns: list = field(default_factory=list)
    decisions: list = field(default_factory=list)
    files_modified: list = field(default_factory=list)
    learnings: list = field(default_factory=list)

    def to_prompt(self) -> str:
        """Convert to prompt-friendly format"""
        parts = ["## Shared Context\n"]

        if self.decisions:
            parts.append("### Key Decisions")
            for d in self.decisions:
                parts.append(f"- {d}")
            parts.append("")

        if self.files_modified:
            parts.append("### Files Modified")
            for f in self.files_modified:
                parts.append(f"- `{f}`")
            parts.append("")

        if self.learnings:
            parts.append("### Learnings")
            for learning in self.learnings[-5:]:  # Last 5 only
                parts.append(f"- {learning}")
            parts.append("")

        return "\n".join(parts)


class HybridOrchestrator:
    """
    Orchestrate multi-agent workflows using SDK for control
    and kimi-cli for execution.

    Usage:
        >>> orch = HybridOrchestrator()
        >>> results = await orch.run_workflow("Implement user authentication")
        >>> orch.print_summary(results)
    """

    def __init__(
        self,
        work_dir: Path | str = ".",
        agents_dir: Path | str | None = None,
        model: str = "kimi-k2.5",
        enable_cache: bool | None = None,  # None = auto-detect from env
        agent_mode: str | None = None,  # "native", "legacy", or "auto"
        team_id: str | None = None,
    ):
        """
        Initialize the HybridOrchestrator.

        Args:
            work_dir: Working directory for task execution
            agents_dir: Directory containing agent YAML files
            model: Model name for SDK-based analysis
            enable_cache: Enable context cache (None = use env var)
            agent_mode: Agent execution mode - "native", "legacy", or "auto"
            team_id: Team to use (None = use TeamManager effective team)
        """
        self.work_dir = Path(work_dir).resolve()
        self.agents_dir = (
            Path(agents_dir) if agents_dir else (Path.home() / ".kimi" / "agents" / "kimi-tachi")
        )
        self.model = model
        self.shared_context = SharedContext()
        self.history: list[AgentResult] = []
        self._team_id = team_id

        # Determine agent execution mode (Phase 3.0)
        if agent_mode is None:
            agent_mode = os.environ.get("KIMI_TACHI_AGENT_MODE", "auto")

        self._agent_mode_setting = agent_mode
        self._effective_agent_mode = self._resolve_agent_mode(agent_mode)
        self.use_native_agents = self._effective_agent_mode == "native"

        self.debug = os.environ.get("KIMI_TACHI_DEBUG_AGENTS", "").lower() in (
            "1",
            "true",
            "yes",
        )

        # SDK for orchestration decisions (optional)
        self.kimi = None
        if KIMI_SDK_AVAILABLE and Kimi is not None:
            try:
                self.kimi = Kimi(
                    model=model,
                    # Uses KIMI_API_KEY env var
                )
            except Exception as e:
                print(f"Warning: Failed to initialize Kimi SDK: {e}")

        # Initialize native agent orchestrator (Phase 3.0)
        self._native_orch = None
        if self.use_native_agents and NATIVE_AGENT_AVAILABLE:
            try:
                self._native_orch = NativeAgentOrchestrator(
                    cache_ttl=300,
                    debug=self.debug,
                    team_id=self._team_id,
                )
                if self.debug:
                    print("[HybridOrchestrator] Native agent mode enabled")
            except Exception as e:
                print(
                    f"Warning: NativeAgentOrchestrator not available ({e}), falling back to legacy"
                )
                self.use_native_agents = False
                self._effective_agent_mode = "legacy"

        if self.debug:
            print(f"[HybridOrchestrator] Mode: {self._effective_agent_mode}")

        # Initialize context cache (Phase 2.4)
        self._cache_manager = None
        if enable_cache is None:
            self._cache_enabled = os.environ.get("KIMI_TACHI_ENABLE_CACHE", "true").lower() not in (
                "0",
                "false",
                "no",
                "disabled",
            )
        else:
            self._cache_enabled = enable_cache

        if self._cache_enabled and CONTEXT_CACHE_AVAILABLE and ContextCacheManager is not None:
            try:
                cache_dir = self.work_dir / ".kimi-tachi" / "cache"
                self._cache_manager = ContextCacheManager(
                    cache_dir=cache_dir,
                    enable_file_cache=True,
                    enable_semantic_index=True,
                    enable_analysis_cache=True,
                    enable_compression=True,
                )
                if self.debug:
                    print(f"[HybridOrchestrator] Context cache enabled: {cache_dir}")
            except Exception as e:
                print(f"Warning: Failed to initialize context cache: {e}")
                self._cache_enabled = False
        elif self._cache_enabled and not CONTEXT_CACHE_AVAILABLE:
            print("Warning: Context cache not available (context module not found)")
            self._cache_enabled = False

    def _resolve_agent_mode(self, mode: str) -> str:
        """Resolve agent mode, handling 'auto' detection"""
        if mode == "auto":
            # Auto-detect based on CLI version
            try:
                from ..compatibility import check_compatibility

                report = check_compatibility()
                return "native" if report.is_compatible else "legacy"
            except Exception:
                return "legacy"
        return mode if mode in ("native", "legacy") else "legacy"

    def cleanup(self) -> None:
        """Clean up resources"""
        # Clean up native agent orchestrator (Phase 3.0)
        if self._native_orch:
            destroyed = self._native_orch.cleanup()
            if destroyed > 0 and self.debug:
                print(f"🧹 Cleaned up {destroyed} native agents")

    def get_cache_statistics(self) -> dict[str, Any]:
        """Get context cache statistics (Phase 2.4)"""
        if self._cache_manager:
            return self._cache_manager.get_cache_info()
        return {"enabled": False, "reason": "Cache not initialized"}

    def clear_cache(self) -> None:
        """Clear all context cache (Phase 2.4)"""
        if self._cache_manager:
            self._cache_manager.clear_all_cache()
            print("🧹 Context cache cleared")

    def _get_team_manager(self) -> TeamManager | None:
        """Get TeamManager if available."""
        if not TEAM_AVAILABLE or TeamManager is None:
            return None
        return TeamManager()

    def _get_agent_file(self, agent: str) -> Path:
        """Get agent YAML file path"""
        manager = self._get_team_manager()
        if manager is not None:
            try:
                resolved = manager.resolve_agent(agent)
                return Path(resolved.agent_file)
            except (TeamNotFoundError, AgentNotFoundError):
                pass

        raise ValueError(f"Unknown agent: {agent}")

    def _get_agent_info(self, agent: str) -> dict:
        """Get agent information (name, role, description)."""
        manager = self._get_team_manager()
        if manager is not None:
            try:
                resolved = manager.resolve_agent(agent)
                team = resolved.team
                info = team.agents.get(resolved.agent_name, {})
                return {
                    "name": info.get("name", resolved.agent_name),
                    "role": info.get("role", "unknown"),
                    "category": info.get("category", "unknown"),
                    "description": info.get("description", ""),
                }
            except (TeamNotFoundError, AgentNotFoundError):
                pass

        raise ValueError(f"Unknown agent: {agent}")

    def _get_team(self):
        """Get the effective team."""
        manager = self._get_team_manager()
        if manager is not None:
            return manager.get_team(self._team_id) if self._team_id else manager.effective_team
        return None

    async def delegate(
        self,
        agent: str,
        task: str,
        context: str = "",
        timeout: int = 300,
        session_id: str | None = None,
    ) -> AgentResult:
        """
        Delegate task to an agent.

        In native mode, forwards to NativeAgentOrchestrator to build
        the prompt and agent parameters. In legacy mode, builds a local
        AgentResult with the composed prompt.

        Args:
            agent: Agent name (kamaji, calcifer, etc.)
            task: Task description
            context: Additional context to pass
            timeout: Max execution time in seconds (unused, kept for compat)
            session_id: Optional session ID (legacy, unused)

        Returns:
            AgentResult with output and metadata
        """
        if self.use_native_agents and self._native_orch is not None:
            personality = self._resolve_personality(agent)
            if personality is not None:
                native_result = await self._native_orch.delegate(
                    personality=personality,
                    task=task,
                    context=context,
                    timeout=timeout,
                )
                # Convert NativeAgentOrchestrator.AgentResult -> HybridOrchestrator.AgentResult
                agent_result = AgentResult(
                    agent=agent,
                    task=task,
                    stdout=native_result.stdout,
                    stderr=native_result.stderr,
                    returncode=native_result.returncode,
                )
                self._update_context(agent, agent_result)
                self.history.append(agent_result)
                return agent_result

        # Legacy/local fallback: build prompt locally
        full_prompt = self._build_prompt(agent, task, context)
        agent_info = self._get_agent_info(agent)
        print(f"◕‿◕ Delegating to {agent_info['name']}: {task[:60]}...")

        agent_result = AgentResult(
            agent=agent,
            task=task,
            stdout=full_prompt,
            stderr="",
            returncode=0,
        )
        self._update_context(agent, agent_result)
        self.history.append(agent_result)
        return agent_result

    def _resolve_personality(self, agent: str) -> AgentPersonality | None:
        """Resolve agent name to AgentPersonality."""
        if not NATIVE_AGENT_AVAILABLE:
            return None

        # Try direct name match first
        if get_personality_by_name is not None:
            personality = get_personality_by_name(agent)
            if personality is not None:
                return personality

        # Fall back to role-based match using team agent info
        try:
            agent_info = self._get_agent_info(agent)
            role = agent_info.get("role", "")
            if get_personality_by_role is not None:
                return get_personality_by_role(role)
        except ValueError:
            pass

        return None

    def _build_prompt(self, agent: str, task: str, extra_context: str) -> str:
        """Build full prompt with shared context"""
        parts = [
            self.shared_context.to_prompt(),
            f"## Your Task\n{task}",
        ]

        if extra_context:
            parts.append(f"\n## Additional Context\n{extra_context}")

        # Add agent-specific instructions
        agent_info = self._get_agent_info(agent)
        parts.append(
            f"\n## Your Role\nYou are {agent_info['name']} - {agent_info.get('description', '')}"
        )

        return "\n\n".join(parts)

    def _update_context(self, agent: str, result: AgentResult):
        """Extract learnings from agent output and update shared context"""
        output = result.stdout

        # Extract file modifications (simple heuristic)
        if "`" in output and (".py" in output or ".ts" in output or ".js" in output):
            import re

            files = re.findall(r"`([^`]+\.(py|ts|js|yaml|json|md))`", output)
            for file, _ in files:
                if file not in self.shared_context.files_modified:
                    self.shared_context.files_modified.append(file)

        # Store learning summary
        agent_info = self._get_agent_info(agent)
        learning = f"{agent_info['name']}: {result.task[:50]}..."
        self.shared_context.learnings.append(learning)

    async def analyze_task_complexity(self, task: str) -> dict[str, Any]:
        """
        Analyze task and determine orchestration strategy.
        Uses SDK if available, otherwise uses heuristics.
        """
        # Fallback: use heuristic analysis
        if not KIMI_SDK_AVAILABLE or self.kimi is None:
            return self._heuristic_analysis(task)

        # Build available agents list from current team
        team = self._get_team()
        if team:
            agent_list = "\n".join(
                f"- {name}: {info.get('role', 'unknown')}"
                for name, info in team.agents.items()
                if name != team.coordinator
            )
        else:
            agent_list = (
                "- shishigami: Architecture design\n"
                "- nekobasu: Code exploration\n"
                "- calcifer: Implementation\n"
                "- enma: Code review\n"
                "- tasogare: Planning\n"
                "- phoenix: Documentation"
            )

        # Use SDK for analysis
        prompt = f"""Analyze this task and determine the best orchestration strategy.

Task: {task}

Available agents:
{agent_list}

Respond in JSON format:
{{
    "complexity": "simple|medium|complex",
    "recommended_agents": ["agent1", "agent2"],
    "parallelizable": true|false,
    "reasoning": "explanation"
}}"""

        try:
            result = await generate(
                chat_provider=self.kimi,
                system_prompt="You are an expert task analyzer. Respond only with JSON.",
                tools=[],
                history=[Message(role="user", content=prompt)],
            )

            # Try to extract JSON from output
            text = result.message.extract_text()
            # Find JSON block
            if "```json" in text:
                json_str = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                json_str = text.split("```")[1].split("```")[0]
            else:
                json_str = text

            return json.loads(json_str.strip())
        except Exception as e:
            print(f"Warning: SDK analysis failed ({e}), using heuristic fallback")
            return self._heuristic_analysis(task)

    def _heuristic_analysis(self, task: str) -> dict[str, Any]:
        """Simple heuristic-based task analysis"""
        task_lower = task.lower()

        # Simple indicators
        simple_keywords = ["fix typo", "rename", "update comment", "change color", "add log"]
        complex_keywords = ["implement", "design", "architecture", "refactor", "new feature"]

        # Count indicators
        simple_score = sum(1 for k in simple_keywords if k in task_lower)
        complex_score = sum(1 for k in complex_keywords if k in task_lower)

        # Task length heuristic
        is_short = len(task.split()) < 10

        # Determine default agent based on current team
        team = self._get_team()
        default_builder = "calcifer"
        default_research = "nekobasu"
        default_planner = "tasogare"
        default_architect = "shishigami"
        default_reviewer = "enma"

        if team:
            # Find agents by category
            for name, info in team.agents.items():
                cat = info.get("category", "")
                if cat == "create":
                    default_builder = name
                elif cat == "research":
                    default_research = name
                elif cat == "plan":
                    default_planner = name
                elif cat == "design":
                    default_architect = name
                elif cat == "review":
                    default_reviewer = name

        if simple_score > 0 or (is_short and complex_score == 0):
            return {
                "complexity": "simple",
                "recommended_agents": [default_builder],
                "parallelizable": False,
                "reasoning": "Simple task detected by heuristic",
            }
        elif complex_score > 0:
            return {
                "complexity": "complex",
                "recommended_agents": [
                    default_planner,
                    default_architect,
                    default_builder,
                    default_reviewer,
                ],
                "parallelizable": False,
                "reasoning": "Complex task detected by heuristic",
            }
        else:
            return {
                "complexity": "medium",
                "recommended_agents": [default_research, default_builder],
                "parallelizable": False,
                "reasoning": "Medium complexity by default",
            }

    async def run_workflow(self, task: str) -> list[AgentResult]:
        """
        Analyze task and run appropriate workflow.
        """
        print(f"🔍 Analyzing task: {task}")
        analysis = await self.analyze_task_complexity(task)

        print(f"📊 Complexity: {analysis['complexity']}")
        print(f"🤖 Recommended agents: {', '.join(analysis['recommended_agents'])}")

        if analysis["complexity"] == "simple":
            return await self._simple_workflow(task)
        elif analysis["complexity"] == "medium":
            return await self._medium_workflow(task, analysis)
        else:
            return await self._complex_workflow(task, analysis)

    async def _simple_workflow(self, task: str) -> list[AgentResult]:
        """Simple task: just use builder agent"""
        team = self._get_team()
        builder = "calcifer"
        if team:
            for name, info in team.agents.items():
                if info.get("category") == "create":
                    builder = name
                    break
        result = await self.delegate(builder, task)
        return [result]

    async def _medium_workflow(self, task: str, analysis: dict) -> list[AgentResult]:
        """Medium task: explore then implement"""
        results = []

        # Find research agent
        team = self._get_team()
        research_agent = None
        if team:
            for name, info in team.agents.items():
                if info.get("category") == "research":
                    research_agent = name
                    break
        if research_agent and research_agent in analysis["recommended_agents"]:
            explore_result = await self.delegate(research_agent, f"Explore codebase for: {task}")
            results.append(explore_result)

        # Step 2: Implementation
        builder = "calcifer"
        if team:
            for name, info in team.agents.items():
                if info.get("category") == "create":
                    builder = name
                    break
        context = ""
        if results:
            context = f"Based on exploration: {results[0].stdout[:500]}..."
        impl_result = await self.delegate(builder, task, context=context)
        results.append(impl_result)

        return results

    async def _complex_workflow(self, task: str, analysis: dict) -> list[AgentResult]:
        """Complex task: full orchestration"""
        results = []

        # Find agents by category
        team = self._get_team()
        planner = None
        research = None
        architect = None
        builder = None
        reviewer = None
        if team:
            for name, info in team.agents.items():
                cat = info.get("category", "")
                if cat == "plan":
                    planner = name
                elif cat == "research":
                    research = name
                elif cat == "design":
                    architect = name
                elif cat == "create":
                    builder = name
                elif cat == "review":
                    reviewer = name

        # Step 1: Planning & Exploration (parallel)
        print("\n📋 Phase 1: Planning & Exploration")
        phase1_tasks = []

        if planner and planner in analysis["recommended_agents"]:
            phase1_tasks.append(self.delegate(planner, f"Create implementation plan for: {task}"))
        if research and research in analysis["recommended_agents"]:
            phase1_tasks.append(self.delegate(research, f"Explore codebase patterns for: {task}"))

        if phase1_tasks:
            phase1_results = await asyncio.gather(*phase1_tasks)
            results.extend(phase1_results)

        # Step 2: Architecture (if needed)
        if architect and architect in analysis["recommended_agents"] and results:
            print("\n🏗️ Phase 2: Architecture Design")
            context_parts = []
            for i, r in enumerate(results[:2]):
                context_parts.append(f"\n{'Plan' if i == 0 else 'Patterns'}: {r.stdout[:300]}...")
            context = "".join(context_parts)

            arch_result = await self.delegate(
                architect, f"Design architecture for: {task}", context=context
            )
            results.append(arch_result)

        # Step 3: Implementation
        if builder:
            print("\n🔨 Phase 3: Implementation")
            impl_result = await self.delegate(
                builder,
                f"Implement: {task}",
                context="Follow the architecture and patterns identified above.",
            )
            results.append(impl_result)

        # Step 4: Review
        if reviewer and reviewer in analysis["recommended_agents"]:
            print("\n🔍 Phase 4: Code Review")
            review_result = await self.delegate(
                reviewer,
                f"Review implementation of: {task}",
                context=f"Files modified: {self.shared_context.files_modified}",
            )
            results.append(review_result)

        return results

    def print_summary(self, results: list[AgentResult]):
        """Print workflow summary"""
        print("\n" + "=" * 60)
        print("◕‿◕ Workflow Complete - Summary")
        print("=" * 60)

        for i, result in enumerate(results, 1):
            try:
                agent_info = self._get_agent_info(result.agent)
            except ValueError:
                agent_info = {"name": result.agent}
            status = "✅" if result.returncode == 0 else "❌"
            print(f"\n{i}. {status} {agent_info['name']}")
            print(f"   Task: {result.task[:60]}...")
            print(f"   Output: {result.stdout[:200]}...")
            if result.stderr:
                print(f"   Warnings: {result.stderr[:100]}...")

        print(f"\n📁 Files modified: {self.shared_context.files_modified}")
        print(f"💡 Key decisions: {len(self.shared_context.decisions)}")

        # Print mode info
        mode_str = "Native (Phase 3.0)" if self.use_native_agents else "Legacy"
        print(f"\n🔧 Execution mode: {mode_str}")

    def get_stats(self) -> dict[str, Any]:
        """Get orchestrator statistics"""
        stats = {
            "agent_mode": self._effective_agent_mode,
            "agent_mode_setting": self._agent_mode_setting,
            "history_count": len(self.history),
            "files_modified": len(self.shared_context.files_modified),
            "decisions": len(self.shared_context.decisions),
        }

        if self._native_orch:
            stats["native_stats"] = self._native_orch.get_stats()

        return stats
