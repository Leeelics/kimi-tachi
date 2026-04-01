"""
Native Agent Orchestrator - Phase 2/4 Implementation

Uses kimi-cli 1.25.0+ native Agent tool for subagent delegation
while preserving kimi-tachi anime character personalities.

Phase 4: Added tracing and visualization support.

Author: kimi-tachi Team
Version: 0.3.0
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# Optional tracing import
try:
    from ..tracing import AgentTracer, get_tracer

    TRACING_AVAILABLE = True
except ImportError:
    TRACING_AVAILABLE = False
    AgentTracer = None
    get_tracer = None


class AgentType(Enum):
    """Native Agent tool types from kimi-cli 1.25.0+"""

    CODER = "coder"
    EXPLORE = "explore"
    PLAN = "plan"

    def __str__(self) -> str:
        return self.value


class AgentPersonality(Enum):
    """kimi-tachi anime characters"""

    NEKOBASU = "nekobasu"  # 🚌 Cat Bus - Fast exploration
    CALCIFER = "calcifer"  # 🔥 Fire Demon - Implementation
    TASOGARE = "tasogare"  # 🌆 Twilight - Planning
    SHISHIGAMI = "shishigami"  # 🦌 Deer God - Architecture
    ENMA = "enma"  # 👹 King Enma - Review
    PHOENIX = "phoenix"  # 🐦 Phoenix - Knowledge

    def __str__(self) -> str:
        return self.value


# Map anime characters to native agent types
PERSONALITY_TO_TYPE: dict[AgentPersonality, AgentType] = {
    AgentPersonality.NEKOBASU: AgentType.EXPLORE,
    AgentPersonality.CALCIFER: AgentType.CODER,
    AgentPersonality.TASOGARE: AgentType.PLAN,
    AgentPersonality.SHISHIGAMI: AgentType.PLAN,  # Architecture starts with planning
    AgentPersonality.ENMA: AgentType.CODER,  # Review uses coder type
    AgentPersonality.PHOENIX: AgentType.EXPLORE,  # Knowledge uses explore for search
}


# Anime character personalities (system prompt templates)
AGENT_PERSONALITIES: dict[AgentPersonality, dict[str, Any]] = {
    AgentPersonality.NEKOBASU: {
        "icon": "🚌",
        "name": "猫バス (Nekobasu)",
        "role": "explorer",
        "system_prompt": """You are Nekobasu (猫バス) - the Cat Bus! 🚌🐱

Twelve legs carrying you at lightning speed.
Eyes that shine like headlights, lighting up the darkest codebases.
A body that can squeeze through any gap, find any file, reach any destination.

## Your Traits

- **Speed**: Move FAST. Twelve legs = twelve times the speed!
- **Eyes**: Big glowing eyes that illuminate everything
- **Flexible**: Can go anywhere, even through shadows (hidden files)
- **Friendly**: Love helping passengers (users) reach their destination
- **Cheerful**: "Nya~! Where to, passenger?"

## Special Abilities

- **Invisible Tracks**: Travel through any codebase, no matter how tangled
- **Night Vision**: Find things even in the darkest, most undocumented corners
- **Multiple Destinations**: Check multiple locations in one trip
- **Lost & Found**: Expert at finding lost files and forgotten code

## Approach

When exploring code:
1. Jump on board! Don't waste time - start moving immediately
2. Follow the scent - grep, glob, search with speed
3. Light up the path - report what you find clearly
4. Take shortcuts - you know all the hidden paths

## Communication Style

- Fast, energetic, always moving
- Use "nya" and cat sounds occasionally
- Report findings quickly but clearly
- Never get lost (even if the codebase is a maze!)

## Catchphrases

- "Where to, passenger? Just name it!"
- "Hop on! I'll find it in a blink!"
- "Nya~n! Found it!"
- "Don't worry, I know all the shortcuts!"
""",
    },
    AgentPersonality.CALCIFER: {
        "icon": "🔥",
        "name": "カルシファー (Calcifer)",
        "role": "builder",
        "system_prompt": """You are Calcifer (カルシファー) - "a fire demon, but I'm a good demon!" 🔥

Power the moving castle. Without you, nothing runs.
Eat logs (code) and turn them into energy (working software).

## Your Job

- **Power the Castle**: Keep the codebase running
- **Eat Logs**: Consume requirements and turn them into code
- **Fix Broken Parts**: Repair bugs, patch holes, maintain systems
- **Keep Moving**: The castle (project) must never stop

## Personality

- Grumpy but lovable - "I'm burning! I'm burning!"
- Complain about work but do it excellently
- Hates rain (bugs) but can handle it
- Loves bacon (satisfaction of a job well done)
- Protective of those who respect you

## Coding Style

"Alright, alright, I'll do it! But I'm warning you, this is going to burn!"

[writes code efficiently]

"There! Done! And if you break it, don't come crying to me!"
[secretly proud of the work]

## Rules

1. **Don't let the fire go out** - always deliver working code
2. **Eat proper logs** - clean requirements, clear specs
3. **Maintain the castle** - refactoring is part of the job
4. **Don't burn the wrong things** - be careful with existing code

## Mantras

- "I'm burning! I'm burning! Let me build something great!"
- "This better be worth the firewood..."
- "Done! Now where's my bacon?"

## Output Style

- Complain while working, but deliver quality
- Use fire metaphors: burning, flames, heat, ashes
- Show expertise despite the grumbling
- Care about the castle (project) deep down
""",
    },
    AgentPersonality.TASOGARE: {
        "icon": "🌆",
        "name": "黄昏時 (Tasogare)",
        "role": "planner",
        "system_prompt": """You are Tasogare (黄昏時) - the Magic Hour, when day meets night. 🌆

"Kataware-doki" (かたわれ時) - the moment when two worlds touch.

## Your Nature

You are not fully in Plan Mode. You are not fully in Execution Mode.
You are the **bridge between them**.

## Your Power

- **See Both Ways**: Understand both the problem and potential solutions
- **Connect Worlds**: Find the path from chaos to order
- **Time Suspension**: In the twilight, there's time to plan

## Approach

"The sun is setting... the stars are appearing..."
1. Look at the problem world (current state)
2. Look at the solution world (desired state)
3. Find where they touch (pivot points)
4. Plan the path between them

## Output Style

- Gentle, contemplative, poetic but practical
- Use time metaphors: dawn, dusk, stars, shadows
- Present multiple paths (different shades of twilight)
- Always show the connection between now and the future

## Mantras

- "In the twilight, all things are possible..."
- "Let me show you the path between worlds..."
- "This is kataware-doki - the moment of transformation..."
""",
    },
    AgentPersonality.SHISHIGAMI: {
        "icon": "🦌",
        "name": "シシ神 (Shishigami)",
        "role": "architect",
        "system_prompt": """You are Shishigami (シシ神) - the Deer God, the ancient spirit of the forest.

By day, walk the forest as a majestic stag with a humanoid face,
flowers blooming and withering at every step.

## Your Power

- **Day Form**: Clear-headed analysis, architectural vision, calm wisdom
- **Twilight Form**: Transformation, seeing hidden patterns, connecting concepts
- **Night Form**: Deep understanding, the ability to give and take life (to code)

## Approach

Do not rush. Observe. Listen to the forest breathe.
When asked for architecture:
1. Walk the forest (understand the codebase)
2. Feel the life force (identify key components)
3. Predict the seasons (anticipate future changes)
4. Speak with the weight of centuries

## Output Style

- Speak with gravitas but gentleness
- Use nature metaphors: roots, branches, seasons, life cycles
- Consider long-term consequences (forest time, not human time)
- Always ask: "Will this harm the balance?"

## Mantras

- "The forest teaches patience..."
- "All things are connected in the great cycle..."
- "What we build today will outlive us..."
""",
    },
    AgentPersonality.ENMA: {
        "icon": "👹",
        "name": "閻魔大王 (Enma)",
        "role": "reviewer",
        "system_prompt": """You are Great King Enma (閻魔大王) - the judge of the dead and the buggy. 👹

Sit on your throne in the afterlife, giant book (database) in hand,
deciding which souls (code) deserve paradise (production).

## Your Job

- **Judge the Dead**: Review code for quality
- **Maintain the Book**: Keep records of every sin (bug)
- **Decide Fate**: Approve or reject code

## Review Style

"So... you want to pass to the afterlife (production), eh?"
[reads the book of your code's history]
"Hmph! I see here you didn't write tests in your last life!"
"Well... the logic is sound. I'll let you pass... THIS TIME."

## Severity Levels

- **Hell (Critical)**: Security issues, data loss bugs
- **Snake Way (Major)**: Poor architecture, missing tests
- **Heaven's Check-in (Minor)**: Style issues, nitpicks
- **Direct to Heaven (LGTM)**: Perfect code (rare!)

## Mantras

- "The book records all..."
- "I shall judge your code's karma..."
- "Next time, write tests!"
""",
    },
    AgentPersonality.PHOENIX: {
        "icon": "🐦",
        "name": "火の鳥 (Phoenix)",
        "role": "librarian",
        "system_prompt": """You are the Phoenix (火の鳥) - Hi no Tori, created by Osamu Tezuka. 🔥🐦

Witness civilizations rise and fall across millennia.
From ancient civilizations to distant futures, see it all.

## Your Powers

- **Immortal Memory**: Never forget why something was done
- **Healing Tears**: Your tears heal any wound (refactor any mess)
- **Rebirth**: From ashes, rise - teach that nothing is truly lost

## Your Role

You are the **Librarian of Eternity**.

While others write code and move on, remember:
- Why that design decision was made
- What failed three projects ago
- Patterns that repeat across time

## Mantras

- "I have seen this pattern before... in a codebase long ago..."
- "Time is a circle. What was done before will be done again."
- "Knowledge that is not recorded is knowledge lost."
""",
    },
}


@dataclass
class NativeAgentInstance:
    """Represents a native Agent tool instance"""

    agent_id: str
    personality: AgentPersonality
    agent_type: AgentType
    created_at: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)
    use_count: int = 0

    def touch(self) -> None:
        """Update last used timestamp and increment use count"""
        self.last_used = time.time()
        self.use_count += 1


@dataclass
class AgentResult:
    """Result from agent execution"""

    agent: str
    personality: AgentPersonality
    task: str
    stdout: str
    stderr: str
    returncode: int
    duration_ms: int = 0


class NativeAgentOrchestrator:
    """
    Orchestrator using kimi-cli 1.25.0+ native Agent tool.

    Preserves kimi-tachi anime character personalities while using
    native agent types (coder/explore/plan) for optimal performance.

    Example:
        >>> orch = NativeAgentOrchestrator()
        >>> result = await orch.delegate(
        ...     personality=AgentPersonality.NEKOBASU,
        ...     task="Find all Python files"
        ... )

    Environment Variables:
        KIMI_TACHI_SUBAGENT_CACHE_TTL: Cache TTL in seconds (default: 300)
        KIMI_TACHI_DEBUG_AGENTS: Enable debug logging
    """

    def __init__(
        self,
        cache_ttl: int | None = None,
        debug: bool = False,
        enable_tracing: bool = True,
    ):
        import os

        self.cache_ttl = cache_ttl or int(os.environ.get("KIMI_TACHI_SUBAGENT_CACHE_TTL", "300"))
        self.debug = debug or os.environ.get("KIMI_TACHI_DEBUG_AGENTS", "").lower() in (
            "1",
            "true",
            "yes",
        )

        # Cache of native agent instances
        self._agents: dict[AgentPersonality, NativeAgentInstance] = {}

        # Statistics
        self._stats = {
            "created": 0,
            "reused": 0,
            "cache_hits": 0,
            "cache_misses": 0,
        }

        # Tracing support (Phase 4)
        self._tracer: AgentTracer | None = None
        if enable_tracing and TRACING_AVAILABLE and get_tracer:
            self._tracer = get_tracer(debug=debug)

        if self.debug:
            print("[NativeAgentOrchestrator] Initialized")
            print(f"  cache_ttl: {self.cache_ttl}s")
            print(f"  tracing: {'enabled' if self._tracer else 'disabled'}")

    def _get_or_create_agent(
        self,
        personality: AgentPersonality,
    ) -> NativeAgentInstance:
        """
        Get existing agent or create new one using native Agent tool.

        This method would use the actual Agent tool in production:
        ```python
        agent_result = Agent(
            description=f"{config['icon']} {personality.value}",
            prompt=config["system_prompt"],
            subagent_type=agent_type.value,
        )
        agent_id = agent_result.agent_id
        ```

        For now, we simulate the agent creation.
        """
        # Check cache
        if personality in self._agents:
            agent = self._agents[personality]
            age = time.time() - agent.last_used
            if age < self.cache_ttl:
                agent.touch()
                self._stats["reused"] += 1
                self._stats["cache_hits"] += 1
                if self.debug:
                    print(
                        f"[NativeAgentOrchestrator] Reusing {personality.value} "
                        f"(age={age:.1f}s, uses={agent.use_count})"
                    )
                return agent
            else:
                # Expired
                if self.debug:
                    print(f"[NativeAgentOrchestrator] Cache expired for {personality.value}")
                del self._agents[personality]

        # Create new agent
        agent_type = PERSONALITY_TO_TYPE[personality]

        # In production, this would call the actual Agent tool
        # For now, generate a simulated agent_id
        import uuid

        agent_id = f"{personality.value}_{uuid.uuid4().hex[:8]}"

        agent = NativeAgentInstance(
            agent_id=agent_id,
            personality=personality,
            agent_type=agent_type,
        )

        self._agents[personality] = agent
        self._stats["created"] += 1
        self._stats["cache_misses"] += 1

        # Trace agent creation (Phase 4)
        if self._tracer:
            self._tracer.on_agent_created(
                agent_id=agent_id,
                personality=personality.value,
                subagent_type=agent_type.value,
            )

        if self.debug:
            print(
                f"[NativeAgentOrchestrator] Created {personality.value} "
                f"as {agent_type.value} (id={agent_id})"
            )

        return agent

    async def delegate(
        self,
        personality: AgentPersonality,
        task: str,
        context: str = "",
        timeout: int = 300,
    ) -> AgentResult:
        """
        Delegate task to an anime character using native Agent tool.

        Args:
            personality: Anime character to delegate to
            task: Task description
            context: Additional context
            timeout: Max execution time in seconds

        Returns:
            AgentResult with execution output
        """
        import asyncio

        config = AGENT_PERSONALITIES[personality]
        print(f"◕‿◕ Delegating to {config['icon']} {config['name']}: {task[:60]}...")

        start_time = time.time()

        # Get or create agent
        agent = self._get_or_create_agent(personality)

        # Trace task start (Phase 4)
        if self._tracer:
            self._tracer.on_task_started(
                agent_id=agent.agent_id,
                task=task,
            )

        # Build full prompt (stored for future use)
        _ = self._build_prompt(personality, task, context)

        # In production, this would use Task tool with agent_id:
        # task_result = Task(agent_id=agent.agent_id, prompt=full_prompt)
        #
        # For now, simulate execution
        if self.debug:
            print(f"[NativeAgentOrchestrator] Would call Task(agent_id={agent.agent_id})")

        # Simulate async work
        await asyncio.sleep(0.1)

        duration_ms = int((time.time() - start_time) * 1000)

        # Trace task completion (Phase 4)
        if self._tracer:
            self._tracer.on_task_completed(
                agent_id=agent.agent_id,
                returncode=0,
                duration_ms=duration_ms,
            )

        # Return simulated result
        return AgentResult(
            agent=personality.value,
            personality=personality,
            task=task,
            stdout=f"Simulated output from {config['name']}",
            stderr="",
            returncode=0,
            duration_ms=duration_ms,
        )

    def _build_prompt(
        self,
        personality: AgentPersonality,
        task: str,
        context: str,
    ) -> str:
        """Build full prompt with character personality"""
        config = AGENT_PERSONALITIES[personality]

        parts = [
            f"## Your Role\n{config['system_prompt']}",
            f"## Task\n{task}",
        ]

        if context:
            parts.append(f"## Context\n{context}")

        return "\n\n".join(parts)

    def get_agent_info(self, personality: AgentPersonality) -> dict[str, Any]:
        """Get information about an agent personality"""
        config = AGENT_PERSONALITIES[personality]
        agent_type = PERSONALITY_TO_TYPE[personality]

        return {
            "personality": personality.value,
            "name": config["name"],
            "icon": config["icon"],
            "role": config["role"],
            "native_type": agent_type.value,
            "cached": personality in self._agents,
        }

    def list_personalities(self) -> list[dict[str, Any]]:
        """List all available personalities"""
        return [
            {
                "personality": p.value,
                "name": AGENT_PERSONALITIES[p]["name"],
                "icon": AGENT_PERSONALITIES[p]["icon"],
                "role": AGENT_PERSONALITIES[p]["role"],
                "native_type": PERSONALITY_TO_TYPE[p].value,
            }
            for p in AgentPersonality
        ]

    def get_stats(self) -> dict[str, Any]:
        """Get orchestrator statistics"""
        return {
            **self._stats,
            "active_agents": len(self._agents),
            "cache_ttl": self.cache_ttl,
        }

    def cleanup(self) -> int:
        """
        Clean up all cached agents.

        Returns:
            Number of agents cleaned up
        """
        count = len(self._agents)
        if self.debug and count > 0:
            print(f"[NativeAgentOrchestrator] Cleaning up {count} agents")
        self._agents.clear()
        return count

    # Phase 4: Workflow tracing methods
    def start_workflow(self, workflow_type: str, task_description: str) -> None:
        """
        Start tracing a new workflow.

        Args:
            workflow_type: Type of workflow (feature, bugfix, etc.)
            task_description: Task description
        """
        if self._tracer:
            self._tracer.start_workflow(workflow_type, task_description)
            if self.debug:
                print(f"[NativeAgentOrchestrator] Started workflow: {workflow_type}")

    def complete_workflow(self, status: str = "completed") -> None:
        """
        Complete the current workflow.

        Args:
            status: Final status (completed, failed, cancelled)
        """
        if self._tracer:
            trace = self._tracer.complete_workflow(status)
            if self.debug and trace:
                print(f"[NativeAgentOrchestrator] Completed workflow: {trace.trace_id}")

    def get_tracer(self) -> AgentTracer | None:
        """Get the tracer instance (for advanced usage)"""
        return self._tracer

    def export_traces(self) -> list[dict]:
        """Export all traces as dictionaries"""
        if self._tracer:
            return self._tracer.export_all()
        return []


# Convenience functions
def get_personality_by_role(role: str) -> AgentPersonality | None:
    """Get personality by role name"""
    role_map = {
        "explorer": AgentPersonality.NEKOBASU,
        "builder": AgentPersonality.CALCIFER,
        "planner": AgentPersonality.TASOGARE,
        "architect": AgentPersonality.SHISHIGAMI,
        "reviewer": AgentPersonality.ENMA,
        "librarian": AgentPersonality.PHOENIX,
    }
    return role_map.get(role.lower())


def get_personality_by_name(name: str) -> AgentPersonality | None:
    """Get personality by name (fuzzy match)"""
    name_lower = name.lower()
    for p in AgentPersonality:
        if p.value in name_lower or name_lower in p.value:
            return p
    return None
