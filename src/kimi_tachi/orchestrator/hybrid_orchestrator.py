"""
Hybrid Orchestrator: SDK control + kimi-cli execution
"""

from __future__ import annotations

import asyncio
import json
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
    ):
        self.work_dir = Path(work_dir).resolve()
        self.agents_dir = (
            Path(agents_dir) if agents_dir else (Path.home() / ".kimi" / "agents" / "kimi-tachi")
        )
        self.model = model
        self.shared_context = SharedContext()
        self.history: list[AgentResult] = []

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

    def cleanup(self) -> None:
        """Clean up resources (sessions, etc.)"""
        if self.session_manager:
            count = self.session_manager.cleanup_all_temp()
            if count > 0:
                print(f"🧹 Cleaned up {count} temporary sessions")

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
        Delegate task to an agent via kimi-cli subprocess.

        Args:
            agent: Agent name (kamaji, calcifer, etc.)
            task: Task description
            context: Additional context to pass
            timeout: Max execution time in seconds
            session_id: Optional session ID for kimi-cli (--session)

        Returns:
            AgentResult with output and metadata
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
