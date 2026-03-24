"""
Hybrid Orchestrator: SDK control + kimi-cli execution

Phase 2.1 Update: Added dynamic subagent creation support
- Reduces MCP processes from 7 to ≤2
- Maintains backward compatibility via KIMI_TACHI_DYNAMIC_AGENTS env var
- Supports both fixed and dynamic subagent modes

Phase 2.4 Update: Added context cache support
- File content caching to avoid redundant reads
- Semantic index for fast symbol lookup
- Analysis result caching to reduce LLM calls
- Context compression to reduce token usage

Phase 3.0 Update: Native Agent Tool Support
- Uses kimi-cli 1.25.0+ native Agent tool
- Preserves anime character personalities
- Requires kimi-cli >=1.25.0 (dropped legacy support)

Environment Variables:
    KIMI_TACHI_AGENT_MODE: "native", "legacy", or "auto" (default: auto)
    KIMI_TACHI_DYNAMIC_AGENTS: Enable dynamic mode (default: true)
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
        NativeAgentOrchestrator,
        AgentPersonality,
        PERSONALITY_TO_TYPE,
    )

    NATIVE_AGENT_AVAILABLE = True
except ImportError:
    NATIVE_AGENT_AVAILABLE = False
    NativeAgentOrchestrator = None
    AgentPersonality = None
    PERSONALITY_TO_TYPE = None


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

    Phase 2.1: Now supports dynamic subagent creation to reduce MCP processes.

    Usage:
        >>> orch = HybridOrchestrator()
        >>> results = await orch.run_workflow("Implement user authentication")
        >>> orch.print_summary(results)

    Dynamic Mode (default):
        - Creates subagents on-demand without MCP
        - MCP processes: ≤2
        - Lower memory footprint
        - Slightly higher latency for first call

    Fixed Mode (legacy, set KIMI_TACHI_DYNAMIC_AGENTS=false):
        - Uses predefined subagents from kamaji.yaml
        - MCP processes: 7
        - Higher memory footprint
        - Faster first call (pre-loaded)
    """

    AGENT_MAP = {
        "kamaji": {
            "name": "釜爺 (Kamaji)",
            "role": "coordinator",
            "file": "kamaji.yaml",
            "description": "Task coordinator and orchestrator",
        },
        "shishigami": {
            "name": "シシ神 (Shishigami)",
            "role": "architect",
            "file": "shishigami.yaml",
            "description": "Architecture and system design",
        },
        "nekobasu": {
            "name": "猫バス (Nekobasu)",
            "role": "explorer",
            "file": "nekobasu.yaml",
            "description": "Fast code exploration",
        },
        "calcifer": {
            "name": "カルシファー (Calcifer)",
            "role": "builder",
            "file": "calcifer.yaml",
            "description": "Implementation and coding",
        },
        "enma": {
            "name": "閻魔大王 (Enma)",
            "role": "reviewer",
            "file": "enma.yaml",
            "description": "Code review and quality",
        },
        "tasogare": {
            "name": "黄昏時 (Tasogare)",
            "role": "planner",
            "file": "tasogare.yaml",
            "description": "Planning and research",
        },
        "phoenix": {
            "name": "火の鳥 (Phoenix)",
            "role": "librarian",
            "file": "phoenix.yaml",
            "description": "Documentation and knowledge",
        },
    }

    def __init__(
        self,
        work_dir: Path | str = ".",
        agents_dir: Path | str | None = None,
        model: str = "kimi-k2.5",
        session_strategy: str = "temp",  # temp, reuse, or None
        enable_dynamic: bool | None = None,  # None = auto-detect from env
        enable_cache: bool | None = None,  # None = auto-detect from env
        agent_mode: str | None = None,  # "native", "legacy", or "auto"
    ):
        """
        Initialize the HybridOrchestrator.

        Args:
            work_dir: Working directory for task execution
            agents_dir: Directory containing agent YAML files
            model: Model name for SDK-based analysis
            session_strategy: Session management strategy (temp, reuse, None)
            enable_dynamic: Force dynamic mode (None = use env var)
            enable_cache: Enable context cache (None = use env var)
            agent_mode: Agent execution mode - "native", "legacy", or "auto"
        """
        self.work_dir = Path(work_dir).resolve()
        self.agents_dir = (
            Path(agents_dir) if agents_dir else (Path.home() / ".kimi" / "agents" / "kimi-tachi")
        )
        self.model = model
        self.shared_context = SharedContext()
        self.history: list[AgentResult] = []

        # Determine agent execution mode (Phase 3.0)
        if agent_mode is None:
            agent_mode = os.environ.get("KIMI_TACHI_AGENT_MODE", "auto")
        
        self._agent_mode_setting = agent_mode
        self._effective_agent_mode = self._resolve_agent_mode(agent_mode)
        self.use_native_agents = self._effective_agent_mode == "native"

        # Determine execution mode (legacy dynamic mode)
        if enable_dynamic is None:
            self.dynamic_mode = os.environ.get("KIMI_TACHI_DYNAMIC_AGENTS", "true").lower() not in (
                "0",
                "false",
                "no",
                "disabled",
            )
        else:
            self.dynamic_mode = enable_dynamic

        self.debug = os.environ.get("KIMI_TACHI_DEBUG_AGENTS", "").lower() in (
            "1",
            "true",
            "yes",
        )

        # Session manager to prevent disk leaks
        self.session_manager = None
        if session_strategy:
            from .session_manager import SessionManager

            self.session_manager = SessionManager(strategy=session_strategy)

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
                )
                if self.debug:
                    print("[HybridOrchestrator] Native agent mode enabled")
            except Exception as e:
                print(f"Warning: NativeAgentOrchestrator not available ({e}), falling back to legacy")
                self.use_native_agents = False
                self._effective_agent_mode = "legacy"

        # Initialize agent factory for dynamic mode (legacy)
        self._agent_factory = None
        if not self.use_native_agents and self.dynamic_mode:
            try:
                from .agent_factory import get_agent_factory

                self._agent_factory = get_agent_factory(agents_dir=self.agents_dir)
                if self.debug:
                    print("[HybridOrchestrator] Dynamic mode enabled (legacy)")
            except ImportError as e:
                print(f"Warning: AgentFactory not available ({e}), falling back to fixed mode")
                self.dynamic_mode = False
        else:
            if self.debug:
                print(f"[HybridOrchestrator] Mode: {self._effective_agent_mode}")

        # Track dynamic subagent instances for cleanup
        self._dynamic_subagents: dict[str, Any] = {}

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
        """Clean up resources (sessions, dynamic subagents, etc.)"""
        # Clean up session manager
        if self.session_manager:
            count = self.session_manager.cleanup_all_temp()
            if count > 0:
                print(f"🧹 Cleaned up {count} temporary sessions")

        # Clean up native agent orchestrator (Phase 3.0)
        if self._native_orch:
            destroyed = self._native_orch.cleanup()
            if destroyed > 0 and self.debug:
                print(f"🧹 Cleaned up {destroyed} native agents")

        # Clean up dynamic subagents (legacy)
        if self._agent_factory:
            destroyed = self._agent_factory.cleanup_all()
            if destroyed > 0 and self.debug:
                print(f"🧹 Cleaned up {destroyed} dynamic subagents")

        self._dynamic_subagents.clear()

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

    def _get_agent_file(self, agent: str) -> Path:
        """Get agent YAML file path"""
        if agent not in self.AGENT_MAP:
            raise ValueError(f"Unknown agent: {agent}. Available: {list(self.AGENT_MAP.keys())}")
        return self.agents_dir / self.AGENT_MAP[agent]["file"]

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

        Uses native Agent tool for all subagent operations.
        In fixed mode, uses subprocess with agent YAML file.

        Args:
            agent: Agent name (kamaji, calcifer, etc.)
            task: Task description
            context: Additional context to pass
            timeout: Max execution time in seconds
            session_id: Optional session ID for kimi-cli (--session)

        Returns:
            AgentResult with output and metadata
        """
        if self.dynamic_mode and agent != "kamaji":
            # Use dynamic subagent creation (Phase 2.1)
            return await self._delegate_dynamic(agent, task, context, timeout)
        else:
            # Use fixed subagent (legacy mode or kamaji itself)
            return await self._delegate_fixed(agent, task, context, timeout, session_id)

    async def _delegate_dynamic(
        self,
        agent: str,
        task: str,
        context: str = "",
        timeout: int = 300,
    ) -> AgentResult:
        """
        Delegate task using dynamic subagent creation.

        This method creates a temporary subagent without MCP overhead,
        executes the task, and returns the result.

        Args:
            agent: Agent name to create dynamically
            task: Task description
            context: Additional context
            timeout: Max execution time

        Returns:
            AgentResult with execution output
        """
        if self._agent_factory is None:
            raise RuntimeError("AgentFactory not initialized")

        agent_info = self.AGENT_MAP[agent]
        print(f"◕‿◕ Creating dynamic subagent {agent_info['name']}: {task[:60]}...")

        try:
            # Create or get cached subagent
            subagent = await self._agent_factory.create_subagent(agent)
            self._dynamic_subagents[agent] = subagent

            if self.debug:
                print(f"[delegate_dynamic] Using subagent {subagent.id}")

            # Build task prompt with context
            full_prompt = self._build_prompt(agent, task, context)

            # Execute via kimi-cli using Task tool pattern
            # Note: In actual implementation, this would use the Task tool
            # For now, we simulate with subprocess to the agent file
            # but without MCP (the subagent YAML has empty subagents)
            result = await self._run_subprocess_for_dynamic(subagent, full_prompt, timeout)

            # Parse and extract learnings
            agent_result = AgentResult(
                agent=agent,
                task=task,
                stdout=result.get("stdout", ""),
                stderr=result.get("stderr", ""),
                returncode=result.get("returncode", 0),
            )

            # Update shared context
            self._update_context(agent, agent_result)
            self.history.append(agent_result)

            return agent_result

        except Exception as e:
            # Fallback to fixed mode on error if possible
            if self.debug:
                print(f"[delegate_dynamic] Error: {e}, attempting fallback")

            # Try fallback to fixed mode
            try:
                return await self._delegate_fixed(agent, task, context, timeout)
            except Exception as fallback_error:
                return AgentResult(
                    agent=agent,
                    task=task,
                    stdout="",
                    stderr=(
                        f"Dynamic delegation failed: {e}\nFallback also failed: {fallback_error}"
                    ),
                    returncode=-1,
                )

    async def _run_subprocess_for_dynamic(
        self,
        subagent: Any,
        prompt: str,
        timeout: int,
    ) -> dict[str, Any]:
        """
        Run subprocess for dynamic subagent execution.

        In dynamic mode, we use the agent's YAML file directly but
        the subagent has no MCP configuration (empty subagents),
        so no additional MCP processes are created.
        """
        agent_file = self.agents_dir / f"{subagent.name}.yaml"

        cmd = [
            "kimi",
            "--agent-file",
            str(agent_file),
            "--work-dir",
            str(self.work_dir),
            "--print",  # Non-interactive mode
            "--output-format",
            "text",
            "--prompt",
            prompt,
        ]

        try:
            result = await asyncio.wait_for(self._run_subprocess(cmd), timeout=timeout)
            return result
        except TimeoutError:
            return {
                "stdout": "",
                "stderr": "Timeout exceeded",
                "returncode": -1,
            }

    async def _delegate_fixed(
        self,
        agent: str,
        task: str,
        context: str = "",
        timeout: int = 300,
        session_id: str | None = None,
    ) -> AgentResult:
        """
        Delegate task using fixed subagent (legacy mode).

        This is the original implementation for backward compatibility.
        """
        agent_file = self._get_agent_file(agent)
        if not agent_file.exists():
            raise FileNotFoundError(f"Agent file not found: {agent_file}")

        # Build full prompt with shared context
        full_prompt = self._build_prompt(agent, task, context)

        print(f"◕‿◕ Delegating to {self.AGENT_MAP[agent]['name']}: {task[:60]}...")

        # Get session ID from manager if available
        managed_session = None
        if self.session_manager and not session_id:
            managed_session = self.session_manager.get_session_id(agent)
            session_id = managed_session

        # Execute via kimi-cli subprocess
        cmd = [
            "kimi",
            "--agent-file",
            str(agent_file),
            "--work-dir",
            str(self.work_dir),
            "--print",  # Non-interactive mode
            "--output-format",
            "text",
            "--prompt",
            full_prompt,
        ]

        # Add session ID if provided (for session management)
        if session_id:
            cmd.extend(["--session", session_id])

        try:
            result = await asyncio.wait_for(self._run_subprocess(cmd), timeout=timeout)
        except TimeoutError:
            # Cleanup session on timeout
            if managed_session and self.session_manager:
                self.session_manager.cleanup_session(managed_session)
            return AgentResult(
                agent=agent, task=task, stdout="", stderr="Timeout exceeded", returncode=-1
            )

        # Parse and extract learnings
        agent_result = AgentResult(
            agent=agent,
            task=task,
            stdout=result["stdout"],
            stderr=result["stderr"],
            returncode=result["returncode"],
        )

        # Update shared context
        self._update_context(agent, agent_result)
        self.history.append(agent_result)

        # Cleanup temporary session if used
        if managed_session and self.session_manager:
            self.session_manager.cleanup_session(managed_session)

        return agent_result

    async def _run_subprocess(self, cmd: list[str]) -> dict[str, Any]:
        """Run subprocess and capture output"""
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=self.work_dir
        )

        stdout, stderr = await proc.communicate()

        return {
            "stdout": stdout.decode("utf-8", errors="replace"),
            "stderr": stderr.decode("utf-8", errors="replace"),
            "returncode": proc.returncode,
        }

    def _build_prompt(self, agent: str, task: str, extra_context: str) -> str:
        """Build full prompt with shared context"""
        parts = [
            self.shared_context.to_prompt(),
            f"## Your Task\n{task}",
        ]

        if extra_context:
            parts.append(f"\n## Additional Context\n{extra_context}")

        # Add agent-specific instructions
        agent_info = self.AGENT_MAP[agent]
        parts.append(f"\n## Your Role\nYou are {agent_info['name']} - {agent_info['description']}")

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
        learning = f"{self.AGENT_MAP[agent]['name']}: {result.task[:50]}..."
        self.shared_context.learnings.append(learning)

    async def analyze_task_complexity(self, task: str) -> dict[str, Any]:
        """
        Analyze task and determine orchestration strategy.
        Uses SDK if available, otherwise uses heuristics.
        """
        # Fallback: use heuristic analysis
        if not KIMI_SDK_AVAILABLE or self.kimi is None:
            return self._heuristic_analysis(task)

        # Use SDK for analysis
        prompt = f"""Analyze this task and determine the best orchestration strategy.

Task: {task}

Available agents:
- shishigami: Architecture design
- nekobasu: Code exploration
- calcifer: Implementation
- enma: Code review
- tasogare: Planning
- phoenix: Documentation

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

        if simple_score > 0 or (is_short and complex_score == 0):
            return {
                "complexity": "simple",
                "recommended_agents": ["calcifer"],
                "parallelizable": False,
                "reasoning": "Simple task detected by heuristic",
            }
        elif complex_score > 0:
            return {
                "complexity": "complex",
                "recommended_agents": ["tasogare", "shishigami", "calcifer", "enma"],
                "parallelizable": False,
                "reasoning": "Complex task detected by heuristic",
            }
        else:
            return {
                "complexity": "medium",
                "recommended_agents": ["nekobasu", "calcifer"],
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
        """Simple task: just use calcifer"""
        result = await self.delegate("calcifer", task)
        return [result]

    async def _medium_workflow(self, task: str, analysis: dict) -> list[AgentResult]:
        """Medium task: explore then implement"""
        results = []

        # Step 1: Exploration (if needed)
        if "nekobasu" in analysis["recommended_agents"]:
            explore_result = await self.delegate("nekobasu", f"Explore codebase for: {task}")
            results.append(explore_result)

        # Step 2: Implementation
        context = ""
        if results:
            context = f"Based on exploration: {results[0].stdout[:500]}..."
        impl_result = await self.delegate("calcifer", task, context=context)
        results.append(impl_result)

        return results

    async def _complex_workflow(self, task: str, analysis: dict) -> list[AgentResult]:
        """Complex task: full orchestration"""
        results = []

        # Step 1: Planning & Exploration (parallel)
        print("\n📋 Phase 1: Planning & Exploration")
        phase1_tasks = []

        if "tasogare" in analysis["recommended_agents"]:
            phase1_tasks.append(
                self.delegate("tasogare", f"Create implementation plan for: {task}")
            )
        if "nekobasu" in analysis["recommended_agents"]:
            phase1_tasks.append(self.delegate("nekobasu", f"Explore codebase patterns for: {task}"))

        if phase1_tasks:
            phase1_results = await asyncio.gather(*phase1_tasks)
            results.extend(phase1_results)

        # Step 2: Architecture (if needed)
        if "shishigami" in analysis["recommended_agents"] and results:
            print("\n🏗️ Phase 2: Architecture Design")
            context_parts = []
            for i, r in enumerate(results[:2]):
                context_parts.append(f"\n{'Plan' if i == 0 else 'Patterns'}: {r.stdout[:300]}...")
            context = "".join(context_parts)

            arch_result = await self.delegate(
                "shishigami", f"Design architecture for: {task}", context=context
            )
            results.append(arch_result)

        # Step 3: Implementation
        print("\n🔨 Phase 3: Implementation")
        impl_result = await self.delegate(
            "calcifer",
            f"Implement: {task}",
            context="Follow the architecture and patterns identified above.",
        )
        results.append(impl_result)

        # Step 4: Review
        if "enma" in analysis["recommended_agents"]:
            print("\n🔍 Phase 4: Code Review")
            review_result = await self.delegate(
                "enma",
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
            agent_info = self.AGENT_MAP[result.agent]
            status = "✅" if result.returncode == 0 else "❌"
            print(f"\n{i}. {status} {agent_info['name']}")
            print(f"   Task: {result.task[:60]}...")
            print(f"   Output: {result.stdout[:200]}...")
            if result.stderr:
                print(f"   Warnings: {result.stderr[:100]}...")

        print(f"\n📁 Files modified: {self.shared_context.files_modified}")
        print(f"💡 Key decisions: {len(self.shared_context.decisions)}")

        # Print mode info
        mode_str = "Dynamic (Phase 2.1)" if self.dynamic_mode else "Fixed (Legacy)"
        print(f"\n🔧 Execution mode: {mode_str}")

    def get_stats(self) -> dict[str, Any]:
        """Get orchestrator statistics"""
        stats = {
            "agent_mode": self._effective_agent_mode,
            "agent_mode_setting": self._agent_mode_setting,
            "dynamic_mode": self.dynamic_mode,
            "history_count": len(self.history),
            "files_modified": len(self.shared_context.files_modified),
            "decisions": len(self.shared_context.decisions),
        }

        if self._native_orch:
            stats["native_stats"] = self._native_orch.get_stats()

        if self._agent_factory:
            stats["factory_stats"] = self._agent_factory.get_stats()

        return stats

    async def create_dynamic_subagent(self, agent_name: str) -> str:
        """
        Create a dynamic subagent and return its ID.

        This is a low-level method for advanced use cases.
        Most users should use `delegate()` instead.

        Args:
            agent_name: Name of the agent to create

        Returns:
            Subagent ID string
        """
        if not self.dynamic_mode:
            raise RuntimeError("Dynamic mode is disabled")

        if self._agent_factory is None:
            raise RuntimeError("AgentFactory not initialized")

        subagent = await self._agent_factory.create_subagent(agent_name)
        self._dynamic_subagents[agent_name] = subagent

        return subagent.id

    def cleanup_dynamic_subagents(self) -> int:
        """
        Clean up all dynamic subagents.

        Returns:
            Number of subagents cleaned up
        """
        if self._agent_factory:
            return self._agent_factory.cleanup_all()
        return 0
