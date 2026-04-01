#!/usr/bin/env python3
"""
kimi-tachi (君たち) - Multi-agent task orchestration for Kimi CLI
"""

from __future__ import annotations

import contextlib
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Annotated

import typer

from kimi_tachi import __version__

# Optional memory support
try:
    from kimi_tachi.memory import AGENT_MEMORY_PROFILES, TachiMemory
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False
    TachiMemory = None
    AGENT_MEMORY_PROFILES = {}

app = typer.Typer(
    name="kimi-tachi",
    help="Multi-agent task orchestration for Kimi CLI",
    add_completion=False,
)


# Add version option
def version_callback(value: bool) -> None:
    if value:
        typer.echo(f"kimi-tachi version {__version__}")
        raise typer.Exit()


@app.callback()
def common(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-v",
            "-V",
            help="Show version and exit.",
            callback=version_callback,
            is_eager=True,
        ),
    ] = False,
) -> None:
    """Common options."""
    pass


# Paths
KIMI_CONFIG_DIR = Path.home() / ".kimi"
KIMI_TACHI_DIR = KIMI_CONFIG_DIR / "agents" / "kimi-tachi"
# Package data directory (for agents, skills, plugins)
PACKAGE_DIR = Path(__file__).parent  # src/kimi_tachi when installed

# Agent definitions with anime characters
AGENTS = {
    "kamaji": {
        "name": "釜爺 (Kamaji)",
        "role": "Boiler Room Chief - Task coordinator",
        "desc": "Six-armed coordinator managing all workers. Best for: general orchestration",
    },
    "shishigami": {
        "name": "シシ神 (Shishigami)",
        "role": "Forest Deity - Architect",
        "desc": "Ancient wisdom for system design. Best for: architecture decisions",
    },
    "nekobasu": {
        "name": "猫バス (Nekobasu)",
        "role": "Cat Bus - Explorer",
        "desc": "Fast exploration with twelve legs. Best for: finding code, navigation",
    },
    "calcifer": {
        "name": "カルシファー (Calcifer)",
        "role": "Fire Demon - Builder",
        "desc": "Powers the castle with code. Best for: implementation, coding",
    },
    "enma": {
        "name": "閻魔大王 (Enma)",
        "role": "King of Afterlife - Reviewer",
        "desc": "Strict judge of code quality. Best for: code review, audits",
    },
    "tasogare": {
        "name": "黄昏時 (Tasogare)",
        "role": "Twilight Hour - Planner",
        "desc": "Connects problem and solution. Best for: planning, research",
    },
    "phoenix": {
        "name": "火の鳥 (Phoenix)",
        "role": "Eternal Observer - Librarian",
        "desc": "Knowledge across time. Best for: documentation, finding info",
    },
}


def _get_kimi_path() -> str:
    """Find kimi executable."""
    kimi_path = shutil.which("kimi")
    if kimi_path:
        return kimi_path
    typer.echo("Error: 'kimi' not found in PATH. Please install Kimi CLI first.", err=True)
    sys.exit(1)


def _configure_default_agent():
    """Interactive configuration for default agent."""
    typer.echo("\n" + "=" * 60)
    typer.echo("◕‿◕ Welcome to kimi-tachi (君たち) Setup")
    typer.echo("=" * 60)
    typer.echo("\nChoose your default agent:\n")

    agents_list = list(AGENTS.items())
    for i, (key, info) in enumerate(agents_list, 1):
        marker = " [Recommended]" if key == "kamaji" else ""
        typer.echo(f"  {i}. {info['name']}")
        typer.echo(f"     Role: {info['role']}{marker}")
        typer.echo(f"     {info['desc']}")
        typer.echo()

    typer.echo("  0. Skip configuration (you can change this later)")
    typer.echo()

    # Get user choice
    choice = typer.prompt("Enter number (0-7)", default="1")

    try:
        idx = int(choice)
        if idx == 0:
            typer.echo("\n⏭️  Skipped. Run 'kimi-tachi setup' anytime to configure.")
            return None
        elif 1 <= idx <= len(agents_list):
            selected = agents_list[idx - 1][0]
            _save_default_agent(selected)
            typer.echo(f"\n✅ Default agent set to: {AGENTS[selected]['name']}")
            typer.echo(f"   You can now run 'kimi --agent-file {KIMI_TACHI_DIR / selected}.yaml'")
            return selected
        else:
            typer.echo("\n⚠️  Invalid choice. Defaulting to kamaji.")
            _save_default_agent("kamaji")
            return "kamaji"
    except ValueError:
        typer.echo("\n⚠️  Invalid input. Defaulting to kamaji.")
        _save_default_agent("kamaji")
        return "kamaji"


def _save_default_agent(agent: str):
    """Save default agent to config file."""
    config_file = KIMI_CONFIG_DIR / "kimi-tachi.config"
    with contextlib.suppress(Exception):
        config_file.write_text(f"default_agent={agent}\n")


def _get_saved_default_agent() -> str | None:
    """Get saved default agent from config file."""
    config_file = KIMI_CONFIG_DIR / "kimi-tachi.config"
    if config_file.exists():
        try:
            content = config_file.read_text().strip()
            if content.startswith("default_agent="):
                return content.split("=", 1)[1].strip()
        except Exception:
            pass
    return None


@app.command()
def setup():
    """Interactive setup for kimi-tachi - choose your default agent."""
    if not KIMI_TACHI_DIR.exists():
        typer.echo("❌ kimi-tachi not installed. Run 'kimi-tachi install' first.")
        sys.exit(1)

    _configure_default_agent()

    typer.echo("\n" + "=" * 60)
    typer.echo("📚 Quick Start:")
    typer.echo("=" * 60)
    typer.echo("\n  1. Start Kimi CLI with your default agent:")
    typer.echo(f"     kimi --agent {KIMI_TACHI_DIR}/<agent>.yaml")
    typer.echo("\n  2. Or start with a specific agent:")
    typer.echo(f"     kimi --agent {KIMI_TACHI_DIR}/kamaji.yaml")
    typer.echo("\n  3. In conversation, switch agents with:")
    typer.echo("     /agent:shishigami 如何设计这个？")
    typer.echo("     /agent:calcifer 实现代码")
    typer.echo("     /agent:enma 审查一下")
    typer.echo("\n  4. List all agents:")
    typer.echo("     kimi-tachi list-agents")
    typer.echo()


@app.command()
def install(
    force: Annotated[bool, typer.Option("--force", "-f", help="Overwrite existing files")] = False,
    skip_setup: Annotated[
        bool, typer.Option("--skip-setup", help="Skip interactive setup")
    ] = False,
):
    """Install kimi-tachi agents and skills to Kimi CLI."""

    if not KIMI_CONFIG_DIR.exists():
        typer.echo(f"Error: Kimi CLI config directory not found at {KIMI_CONFIG_DIR}", err=True)
        typer.echo("Please run 'kimi' first to initialize Kimi CLI.", err=True)
        sys.exit(1)

    # Create directories
    KIMI_TACHI_DIR.mkdir(parents=True, exist_ok=True)
    (KIMI_CONFIG_DIR / "skills").mkdir(exist_ok=True)

    # Copy agents
    agents_source = PACKAGE_DIR / "agents"
    if agents_source.exists():
        for agent_file in agents_source.glob("*.yaml"):
            dest = KIMI_TACHI_DIR / agent_file.name
            if dest.exists() and not force:
                typer.echo(f"Skipping {agent_file.name} (already exists, use --force to overwrite)")
            else:
                shutil.copy2(agent_file, dest)
                typer.echo(f"Installed agent: {agent_file.name}")

    # Copy skills
    skills_source = PACKAGE_DIR / "skills"
    if skills_source.exists():
        for skill_dir in skills_source.iterdir():
            if skill_dir.is_dir():
                dest = KIMI_CONFIG_DIR / "skills" / skill_dir.name
                if dest.exists() and not force:
                    typer.echo(f"Skipping skill {skill_dir.name} (already exists)")
                else:
                    if dest.exists():
                        shutil.rmtree(dest)
                    shutil.copytree(skill_dir, dest)
                    typer.echo(f"Installed skill: {skill_dir.name}")

    # Copy plugins (Phase 3.0)
    plugins_source = PACKAGE_DIR / "plugins"
    if plugins_source.exists():
        (KIMI_CONFIG_DIR / "plugins").mkdir(exist_ok=True)
        for plugin_dir in plugins_source.iterdir():
            if plugin_dir.is_dir():
                dest = KIMI_CONFIG_DIR / "plugins" / plugin_dir.name
                if dest.exists() and not force:
                    typer.echo(f"Skipping plugin {plugin_dir.name} (already exists)")
                else:
                    if dest.exists():
                        shutil.rmtree(dest)
                    shutil.copytree(plugin_dir, dest)
                    typer.echo(f"Installed plugin: {plugin_dir.name}")

    typer.echo("\n✨ kimi-tachi installed successfully!")
    typer.echo("\n📦 Installed components:")
    typer.echo("   • Agents (YAML configuration)")
    typer.echo("   • Skills (documentation and guidance)")
    typer.echo("   • Plugins (executable tools for kimi-cli 1.25.0+)")

    # Interactive setup
    if not skip_setup:
        saved = _get_saved_default_agent()
        if not saved or force:
            _configure_default_agent()
        else:
            typer.echo("\nℹ️  Using previously configured default agent.")
            typer.echo("   Run 'kimi-tachi setup' to change it.")

    typer.echo("\n◕‿◕ Usage:")
    typer.echo(f"  kimi --agent-file {KIMI_TACHI_DIR}/kamaji.yaml")
    typer.echo("  /agent:shishigami  (switch agents in conversation)")


@app.command()
def run(
    agent: Annotated[str, typer.Option("--agent", "-a", help="Agent to use")] = "kamaji",
    yolo: Annotated[bool, typer.Option("--yolo", "-y", help="Auto-approve all actions")] = False,
    plan: Annotated[bool, typer.Option("--plan", "-p", help="Start in plan mode")] = False,
    work_dir: Annotated[str, typer.Option("--work-dir", "-w", help="Working directory")] = ".",
):
    """Run Kimi CLI with kimi-tachi agent."""

    agent_file = KIMI_TACHI_DIR / f"{agent}.yaml"
    if not agent_file.exists():
        typer.echo(f"Error: Agent '{agent}' not found at {agent_file}", err=True)
        typer.echo(
            f"Available agents: {', '.join(a.stem for a in KIMI_TACHI_DIR.glob('*.yaml'))}",
            err=True,
        )
        sys.exit(1)

    kimi_path = _get_kimi_path()
    cmd = [kimi_path, "--agent-file", str(agent_file), "--work-dir", work_dir]

    if yolo:
        cmd.append("--yolo")
    if plan:
        # Note: Kimi CLI may not have --plan flag, use /plan command instead
        typer.echo("Note: Plan mode will be activated via /plan command after startup")

    typer.echo(f"◕‿◕ Starting kimi-tachi with {agent}...")
    subprocess.run(cmd)


@app.command()
def do(
    prompt: str,
    agent: Annotated[str, typer.Option("--agent", "-a")] = "kamaji",
    yolo: Annotated[bool, typer.Option("--yolo", "-y")] = True,
):
    """One-shot mode: execute a single prompt and exit."""

    agent_file = KIMI_TACHI_DIR / f"{agent}.yaml"
    if not agent_file.exists():
        typer.echo(f"Error: Agent '{agent}' not found", err=True)
        sys.exit(1)

    kimi_path = _get_kimi_path()
    cmd = [kimi_path, "--agent-file", str(agent_file)]

    if yolo:
        cmd.append("--yolo")

    cmd.extend(["--", prompt])

    typer.echo(f"🎯 Executing with {agent}: {prompt[:50]}...")
    subprocess.run(cmd)


@app.command()
def list_agents():
    """List available agents."""

    if not KIMI_TACHI_DIR.exists():
        typer.echo("kimi-tachi not installed. Run 'kimi-tachi install' first.")
        sys.exit(1)

    typer.echo("Available agents (七人衆):\n")

    agents = {
        "kamaji": "Boiler Room Chief - The six-armed coordinator (釜爺)",
        "shishigami": "Forest Deity - Architecture and ancient wisdom (シシ神)",
        "nekobasu": "Cat Bus Express - Fast exploration with twelve legs (猫バス)",
        "calcifer": "Fire Demon - Powers the castle with code (カルシファー)",
        "enma": "King of Afterlife - Judges code quality strictly (閻魔大王)",
        "tasogare": "Twilight Hour - Connects problem and solution (黄昏時)",
        "phoenix": "Eternal Observer - Knowledge across time (火の鳥)",
    }

    for agent_file in sorted(KIMI_TACHI_DIR.glob("*.yaml")):
        name = agent_file.stem
        desc = agents.get(name, "Specialized agent")
        typer.echo(f"  {name:15} - {desc}")


# ========== Memory Commands ==========

@app.command()
def memory(
    action: Annotated[str, typer.Argument(help="Action: init, index, search, global-search, recall, status")],
    query: Annotated[str | None, typer.Argument(help="Search query (for search/global-search)")] = None,
    agent: Annotated[str | None, typer.Option("--agent", "-a", help="Agent type (for recall)")] = None,
    work_dir: Annotated[str, typer.Option("--work-dir", "-w", help="Working directory")] = ".",
    incremental: Annotated[bool, typer.Option("--incremental/--full", help="Use incremental indexing")] = True,
    project_name: Annotated[str | None, typer.Option("--project", "-p", help="Project name for global memory")] = None,
):
    """
    Manage code memory for kimi-tachi.

    This is the explicit memory interface (v0.5.0).
    Future versions will support automatic memory via hooks.

    Project-level commands:
        kimi-tachi memory init                    # Initialize memory for project
        kimi-tachi memory index                   # Index project (incremental)
        kimi-tachi memory index --full            # Full re-index
        kimi-tachi memory search "authentication" # Search project memory
        kimi-tachi memory recall --agent kamaji   # Recall context for agent
        kimi-tachi memory status                  # Check memory status

    Global (cross-project) commands:
        kimi-tachi memory register-global --project my-api    # Register in global memory
        kimi-tachi memory sync-global --project my-api        # Sync to global memory
        kimi-tachi memory global-search "JWT implementation"  # Search across projects
    """
    if not MEMORY_AVAILABLE:
        typer.echo("❌ Memory support not available.")
        typer.echo("Install with: pip install memnexus")
        raise typer.Exit(1)

    import asyncio

    async def _memory_action():
        if action == "init":
            typer.echo("🧠 Initializing memory...")
            try:
                memory = await TachiMemory.init(work_dir)
                typer.echo(f"✅ Memory initialized: {work_dir}")
                typer.echo(f"   Session ID: {memory._current_session_id}")
            except Exception as e:
                typer.echo(f"❌ Error: {e}", err=True)
                raise typer.Exit(1) from None

        elif action == "index":
            mode_str = "incremental" if incremental else "full"
            typer.echo(f"📚 Indexing project ({mode_str})...")
            try:
                memory = await TachiMemory.init(work_dir)
                stats = await memory.index_project(git=True, code=True, incremental=incremental)
                typer.echo("✅ Indexing complete:")
                typer.echo(f"   Git commits: {stats.get('git_commits', 0)}")
                typer.echo(f"   Code symbols: {stats.get('code_symbols', 0)}")
                if stats.get('skipped', 0) > 0:
                    typer.echo(f"   Skipped (unchanged): {stats['skipped']}")
            except Exception as e:
                typer.echo(f"❌ Error: {e}", err=True)
                raise typer.Exit(1) from None

        elif action == "search":
            if not query:
                typer.echo("❌ Please provide a search query", err=True)
                raise typer.Exit(1) from None

            typer.echo(f"🔍 Searching: {query}")
            try:
                memory = await TachiMemory.init(work_dir)
                results = await memory.search(query)

                if not results:
                    typer.echo("No results found.")
                    return

                from rich.console import Console
                from rich.table import Table

                console = Console()
                table = Table(title=f"Search Results: '{query}'")
                table.add_column("Type", style="cyan", no_wrap=True)
                table.add_column("Source", style="green")
                table.add_column("Content", style="white")

                for r in results[:10]:
                    result_type = r.get("type", "unknown")
                    source = r.get("source", r.get("file", "unknown"))[:40]

                    if result_type == "code":
                        content = f"{r.get('name', '')}: {r.get('signature', '')[:60]}"
                    else:
                        content = r.get("content", "")[:80]

                    table.add_row(result_type, source, content)

                console.print(table)
                typer.echo(f"\nShowing {len(results[:10])} of {len(results)} results")

            except Exception as e:
                typer.echo(f"❌ Error: {e}", err=True)
                raise typer.Exit(1) from None

        elif action == "global-search":
            if not query:
                typer.echo("❌ Please provide a search query for global-search", err=True)
                raise typer.Exit(1) from None

            typer.echo(f"🌍 Global search: {query}")
            try:
                memory = await TachiMemory.init(work_dir)
                results = await memory.search_global_memory(query)

                if not results:
                    typer.echo("No results found in global memory.")
                    typer.echo("Tip: Register projects with 'kimi-tachi memory register-global'")
                    return

                from rich.console import Console
                from rich.table import Table

                console = Console()
                table = Table(title=f"Global Search Results: '{query}'")
                table.add_column("Project", style="cyan", no_wrap=True)
                table.add_column("Source", style="green")
                table.add_column("Content", style="white")

                for r in results[:10]:
                    project = r.get("project", "unknown")
                    source = r.get("source", "unknown")[:40]
                    content = r.get("content", "")[:80]
                    table.add_row(project, source, content)

                console.print(table)
                typer.echo(f"\nFound {len(results)} results from {len({r.get('project') for r in results})} projects")

            except Exception as e:
                typer.echo(f"❌ Error: {e}", err=True)
                raise typer.Exit(1) from None

        elif action == "register-global":
            if not project_name:
                typer.echo("❌ Please specify --project name for registration", err=True)
                raise typer.Exit(1) from None

            typer.echo(f"🌍 Registering project in global memory: {project_name}")
            try:
                memory = await TachiMemory.init(work_dir)
                success = await memory.register_in_global_memory(project_name)
                if success:
                    typer.echo("✅ Project registered. Run 'kimi-tachi memory sync-global' to sync.")
                else:
                    typer.echo("❌ Registration failed")
            except Exception as e:
                typer.echo(f"❌ Error: {e}", err=True)
                raise typer.Exit(1) from None

        elif action == "sync-global":
            if not project_name:
                typer.echo("❌ Please specify --project name for sync", err=True)
                raise typer.Exit(1) from None

            mode_str = "incremental" if incremental else "full"
            typer.echo(f"🌍 Syncing to global memory ({mode_str}): {project_name}")
            try:
                memory = await TachiMemory.init(work_dir)
                result = await memory.sync_to_global_memory(project_name, incremental=incremental)
                typer.echo(f"✅ Sync complete: {result}")
            except Exception as e:
                typer.echo(f"❌ Error: {e}", err=True)
                raise typer.Exit(1) from None

        elif action == "recall":
            if not agent:
                typer.echo("❌ Please specify --agent for recall", err=True)
                typer.echo("Available agents: kamaji, nekobasu, calcifer, enma, tasogare, shishigami, phoenix")
                raise typer.Exit(1) from None

            typer.echo(f"🧠 Recalling context for {agent}...")
            try:
                memory = await TachiMemory.init(work_dir)
                context = await memory.recall_agent_context(agent, include_global=True)

                profile = AGENT_MEMORY_PROFILES.get(agent)
                if profile:
                    typer.echo(f"\n◕‿◕ {agent}'s Memory Profile:")
                    typer.echo(profile.memory_description)

                typer.echo("\n📋 Recalled Context:")
                typer.echo(f"   Session: {context.session_id}")
                typer.echo(f"   Recent memories: {len(context.recent_memories)}")
                typer.echo(f"   Relevant code: {len(context.relevant_code)}")

                if context.cross_project_knowledge:
                    typer.echo(f"   Cross-project knowledge: {len(context.cross_project_knowledge)}")

                if context.recent_memories:
                    typer.echo("\n📝 Recent Memories:")
                    for m in context.recent_memories[:5]:
                        typer.echo(f"   - [{m.get('source', 'unknown')}] {m.get('content', '')[:60]}...")

                if context.relevant_code:
                    typer.echo("\n💻 Relevant Code:")
                    for c in context.relevant_code[:3]:
                        typer.echo(f"   - {c.get('name', '')} ({c.get('file', '')})")

                if context.cross_project_knowledge:
                    typer.echo("\n🌍 Cross-Project Knowledge:")
                    for k in context.cross_project_knowledge[:3]:
                        typer.echo(f"   - [{k.get('project', '')}] {k.get('content', '')[:60]}...")

            except Exception as e:
                typer.echo(f"❌ Error: {e}", err=True)
                raise typer.Exit(1) from None

        elif action == "status":
            try:
                memory = await TachiMemory.init(work_dir)
                status = await memory.get_index_status()

                typer.echo("🧠 Memory Status:")
                typer.echo(f"   Project: {status.get('project_path', 'Unknown')}")
                typer.echo(f"   Session: {status.get('session_id', 'Unknown')}")

                stats = status.get('stats', {})
                if stats:
                    typer.echo("\n📊 Statistics:")
                    typer.echo(f"   Git commits indexed: {stats.get('git_commits_indexed', 0)}")
                    typer.echo(f"   Code symbols indexed: {stats.get('code_symbols_indexed', 0)}")
                    typer.echo(f"   Total memories: {stats.get('total_memories', 0)}")

            except Exception as e:
                typer.echo(f"❌ Error: {e}", err=True)
                raise typer.Exit(1) from None

        else:
            typer.echo(f"❌ Unknown action: {action}", err=True)
            typer.echo("Available actions: init, index, search, recall, status")
            raise typer.Exit(1)

    asyncio.run(_memory_action())


# ========== Status Command ==========

@app.command()
def status():
    """Check kimi-tachi installation status."""
    from .compatibility import check_compatibility
    from .config import KimiTachiConfig

    typer.echo("kimi-tachi Status:\n")

    # Version info
    typer.echo(f"  kimi-tachi version: {__version__}")
    typer.echo()

    # Compatibility check
    typer.echo("  Compatibility:")
    report = check_compatibility()
    if report.is_compatible:
        typer.echo(f"    ✓ kimi-cli {report.cli_version} (compatible)")
    else:
        typer.echo(f"    ✗ {report.message}")
        typer.echo(f"    → {report.recommendation}")
    typer.echo()

    # Configuration
    config = KimiTachiConfig.from_env()
    typer.echo(f"  Agent Mode: {config.effective_agent_mode}")
    typer.echo(f"    (set via KIMI_TACHI_AGENT_MODE={config.agent_mode})")
    typer.echo()

    # Check Kimi CLI
    kimi_path = shutil.which("kimi")
    if kimi_path:
        typer.echo(f"  ✓ Kimi CLI: {kimi_path}")
        # Show CLI version
        try:
            result = subprocess.run(
                ["kimi", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                typer.echo(f"    Version: {result.stdout.strip()}")
        except Exception:
            pass
    else:
        typer.echo("  ✗ Kimi CLI: Not found")

    # Check installation
    if KIMI_TACHI_DIR.exists():
        agent_count = len(list(KIMI_TACHI_DIR.glob("*.yaml")))
        typer.echo(f"  ✓ Agents installed: {agent_count}")
    else:
        typer.echo("  ✗ Agents: Not installed")
        typer.echo("    Run: kimi-tachi install")

    # Check skills
    skills_dir = KIMI_CONFIG_DIR / "skills"
    if skills_dir.exists():
        skill_count = len([d for d in skills_dir.iterdir() if d.is_dir()])
        typer.echo(f"  ✓ Skills installed: {skill_count}")
    else:
        typer.echo("  ✗ Skills: Not installed")

    # Check plugins (Phase 3.0)
    plugins_dir = KIMI_CONFIG_DIR / "plugins"
    if plugins_dir.exists():
        plugin_count = len([d for d in plugins_dir.iterdir() if d.is_dir()])
        typer.echo(f"  ✓ Plugins installed: {plugin_count}")
        if plugin_count > 0:
            typer.echo("    (Use with kimi-cli 1.25.0+ plugin system)")
    else:
        typer.echo("  ✗ Plugins: Not installed")

    # Check config
    config_file = KIMI_CONFIG_DIR / "kimi-tachi.config"
    if config_file.exists():
        default = _get_saved_default_agent()
        typer.echo(f"  ✓ Config: Default agent = {default or 'not set'}")


@app.command()
def uninstall(
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation prompt")] = False,
    keep_config: Annotated[
        bool, typer.Option("--keep-config", help="Keep configuration file")
    ] = False,
):
    """Uninstall kimi-tachi - remove agents, skills, and configuration."""

    typer.echo("🗑️  kimi-tachi Uninstall\n")

    # Check if installed
    if not KIMI_TACHI_DIR.exists() and not (KIMI_CONFIG_DIR / "skills").exists():
        typer.echo("❌ kimi-tachi is not installed.")
        return

    # Show what will be removed
    typer.echo("The following will be removed:\n")

    if KIMI_TACHI_DIR.exists():
        agent_count = len(list(KIMI_TACHI_DIR.glob("*.yaml")))
        typer.echo(f"  📁 Agents: {KIMI_TACHI_DIR}")
        typer.echo(f"     ({agent_count} agents)")

    skills_dir = KIMI_CONFIG_DIR / "skills"
    if skills_dir.exists():
        kimi_skills = [d.name for d in skills_dir.iterdir() if d.is_dir()]
        if kimi_skills:
            typer.echo(f"  📁 Skills: {skills_dir}")
            for skill in kimi_skills:
                typer.echo(f"     - {skill}")

    # Show plugins
    plugins_dir = KIMI_CONFIG_DIR / "plugins"
    if plugins_dir.exists():
        kimi_plugins = [d.name for d in plugins_dir.iterdir() if d.is_dir()]
        if kimi_plugins:
            typer.echo(f"  📁 Plugins: {plugins_dir}")
            for plugin in kimi_plugins:
                typer.echo(f"     - {plugin}")

    if not keep_config:
        config_file = KIMI_CONFIG_DIR / "kimi-tachi.config"
        if config_file.exists():
            typer.echo(f"  ⚙️  Config: {config_file}")

    typer.echo()

    # Confirmation
    if not force:
        confirm = typer.prompt("Are you sure you want to uninstall? [y/N]", default="n")
        if confirm.lower() not in ("y", "yes"):
            typer.echo("\n❌ Uninstall cancelled.")
            return

    # Remove agents
    if KIMI_TACHI_DIR.exists():
        try:
            shutil.rmtree(KIMI_TACHI_DIR)
            typer.echo("  ✓ Removed agents")
        except Exception as e:
            typer.echo(f"  ✗ Failed to remove agents: {e}", err=True)

    # Remove skills
    skills_dir = KIMI_CONFIG_DIR / "skills"
    if skills_dir.exists():
        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir():
                try:
                    shutil.rmtree(skill_dir)
                    typer.echo(f"  ✓ Removed skill: {skill_dir.name}")
                except Exception as e:
                    typer.echo(f"  ✗ Failed to remove skill {skill_dir.name}: {e}", err=True)

    # Remove plugins (Phase 3.0)
    plugins_dir = KIMI_CONFIG_DIR / "plugins"
    if plugins_dir.exists():
        for plugin_dir in plugins_dir.iterdir():
            if plugin_dir.is_dir():
                try:
                    shutil.rmtree(plugin_dir)
                    typer.echo(f"  ✓ Removed plugin: {plugin_dir.name}")
                except Exception as e:
                    typer.echo(f"  ✗ Failed to remove plugin {plugin_dir.name}: {e}", err=True)

    # Remove config
    if not keep_config:
        config_file = KIMI_CONFIG_DIR / "kimi-tachi.config"
        if config_file.exists():
            try:
                config_file.unlink()
                typer.echo("  ✓ Removed config")
            except Exception as e:
                typer.echo(f"  ✗ Failed to remove config: {e}", err=True)

    typer.echo("\n✨ kimi-tachi uninstalled successfully!")
    typer.echo("\nTo reinstall, run:")
    typer.echo("  kimi-tachi install")


@app.command()
def reset(
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation prompt")] = False,
):
    """Reset kimi-tachi to fresh install state (uninstall + install)."""

    typer.echo("🔄 kimi-tachi Reset\n")
    typer.echo("This will uninstall and then reinstall kimi-tachi.\n")

    # Confirmation
    if not force:
        confirm = typer.prompt("Are you sure? [y/N]", default="n")
        if confirm.lower() not in ("y", "yes"):
            typer.echo("\n❌ Reset cancelled.")
            return

    # Uninstall (keep config temporarily)
    typer.echo("\n📦 Step 1: Uninstalling...")
    try:
        # Remove agents
        if KIMI_TACHI_DIR.exists():
            shutil.rmtree(KIMI_TACHI_DIR)
            typer.echo("  ✓ Removed agents")

        # Remove skills
        skills_dir = KIMI_CONFIG_DIR / "skills"
        if skills_dir.exists():
            for skill_dir in list(skills_dir.iterdir()):
                if skill_dir.is_dir():
                    shutil.rmtree(skill_dir)
            typer.echo("  ✓ Removed skills")
    except Exception as e:
        typer.echo(f"  ✗ Error during uninstall: {e}", err=True)
        return

    # Reinstall
    typer.echo("\n📦 Step 2: Reinstalling...")
    try:
        # Re-run install logic
        KIMI_TACHI_DIR.mkdir(parents=True, exist_ok=True)
        (KIMI_CONFIG_DIR / "skills").mkdir(exist_ok=True)

        # Copy agents
        agents_source = PACKAGE_DIR / "agents"
        if agents_source.exists():
            for agent_file in agents_source.glob("*.yaml"):
                shutil.copy2(agent_file, KIMI_TACHI_DIR / agent_file.name)
            typer.echo(f"  ✓ Installed {len(list(agents_source.glob('*.yaml')))} agents")

        # Copy skills
        skills_source = PACKAGE_DIR / "skills"
        if skills_source.exists():
            for skill_dir in skills_source.iterdir():
                if skill_dir.is_dir():
                    dest = KIMI_CONFIG_DIR / "skills" / skill_dir.name
                    shutil.copytree(skill_dir, dest)
            typer.echo(f"  ✓ Installed {len(list(skills_source.iterdir()))} skills")

    except Exception as e:
        typer.echo(f"  ✗ Error during reinstall: {e}", err=True)
        return

    typer.echo("\n✨ kimi-tachi reset complete!")
    typer.echo("\nStart using kimi-tachi:")
    typer.echo(f"  kimi --agent-file {KIMI_TACHI_DIR}/kamaji.yaml")
    typer.echo("\nOr run 'kimi-tachi setup' to configure default agent.")


@app.command()
def workflow(
    task: Annotated[str, typer.Argument(help="Task description")] = "",
    workflow_type: Annotated[
        str,
        typer.Option(
            "--type", "-t", help="Workflow type: feature, bugfix, explore, refactor, quick"
        ),
    ] = "auto",
    work_dir: Annotated[str, typer.Option("--work-dir", "-w", help="Working directory")] = ".",
    list_types: Annotated[
        bool, typer.Option("--list", "-l", help="List available workflow types")
    ] = False,
):
    """Run a multi-agent workflow for a task using hybrid orchestration."""
    import asyncio

    from .orchestrator import ContextManager, HybridOrchestrator, WorkflowEngine

    if list_types:
        typer.echo("Available workflow types:\n")
        typer.echo("  feature  - Full feature implementation workflow")
        typer.echo("  bugfix   - Bug analysis and fix workflow")
        typer.echo("  explore  - Code exploration and documentation")
        typer.echo("  refactor - Safe refactoring workflow")
        typer.echo("  quick    - Quick fix (single agent)")
        typer.echo("  auto     - Auto-detect based on task (default)")
        return

    if not task:
        typer.echo("Error: TASK is required (unless using --list)", err=True)
        raise typer.Exit(1)

    async def run():
        # Initialize
        work_path = Path(work_dir).resolve()
        ctx_manager = ContextManager(work_path)
        orch = HybridOrchestrator(work_dir=work_path)
        engine = WorkflowEngine(orch, ctx_manager)

        # Get workflow
        if workflow_type == "auto":
            # Analyze task to determine workflow
            analysis = await orch.analyze_task_complexity(task)
            complexity = analysis.get("complexity", "medium")
            if complexity == "simple":
                workflow = engine.quick_fix
            elif complexity == "complex":
                workflow = engine.feature_implementation
            else:
                workflow = engine.bug_fix
            typer.echo(f"Auto-selected workflow based on complexity: {complexity}")
        else:
            workflow = engine.get_workflow(workflow_type)
            if not workflow:
                typer.echo(f"Unknown workflow type: {workflow_type}", err=True)
                typer.echo("Run 'kimi-tachi workflow --list' for available types.", err=True)
                sys.exit(1)

        # Execute
        results = await engine.execute(workflow, task)

        # Print summary
        orch.print_summary(results)

        # Save session
        ctx_manager.save()
        typer.echo(f"\n💾 Session saved: {ctx_manager.session_id}")

    asyncio.run(run())


@app.command()
def sessions(
    work_dir: Annotated[str, typer.Option("--work-dir", "-w", help="Working directory")] = ".",
    clear: Annotated[bool, typer.Option("--clear", "-c", help="Clear all sessions")] = False,
):
    """Manage kimi-tachi sessions for a project."""
    from .orchestrator import ContextManager

    work_path = Path(work_dir).resolve()
    ctx_manager = ContextManager(work_path)

    if clear:
        confirm = typer.prompt("Clear all sessions? [y/N]", default="n")
        if confirm.lower() in ("y", "yes"):
            state_dir = work_path / ".kimi-tachi"
            if state_dir.exists():
                import shutil

                shutil.rmtree(state_dir)
                typer.echo("All sessions cleared.")
        return

    sessions_list = ctx_manager.list_sessions()

    if not sessions_list:
        typer.echo(f"No sessions found in {work_path}")
        return

    typer.echo(f"Sessions in {work_path}:\n")
    for s in sessions_list[:10]:  # Show last 10
        typer.echo(f"  {s['id']}")
        typer.echo(f"    Started: {s['started']}")
        typer.echo(f"    Updated: {s['updated']}")
        typer.echo(f"    Phase: {s['phase']}")
        typer.echo()


@app.command()
def traces(
    export: Annotated[str | None, typer.Option("--export", "-e", help="Export traces to directory")] = None,
    clear: Annotated[bool, typer.Option("--clear", "-c", help="Clear all traces")] = False,
    json_out: Annotated[bool, typer.Option("--json", "-j", help="Output as JSON")] = False,
):
    """View and manage workflow traces (Phase 4)."""
    from .tracing import get_tracer
    from .vis import VisExporter

    tracer = get_tracer()

    if clear:
        confirm = typer.prompt("Clear all traces? [y/N]", default="n")
        if confirm.lower() in ("y", "yes"):
            count = tracer.clear()
            typer.echo(f"Cleared {count} traces.")
        return

    # Export traces if requested
    if export:
        exporter = VisExporter()
        paths = exporter.save_tracer_to_directory(tracer, export)
        typer.echo(f"Exported {len(paths)} traces to {export}")
        for p in paths:
            typer.echo(f"  {p}")
        return

    # Show traces
    stats = tracer.get_stats()

    if json_out:
        import json
        typer.echo(json.dumps(stats, indent=2))
        return

    typer.echo("Workflow Traces (Phase 4)\n")
    typer.echo(f"Total traces: {stats['total_traces']}")
    typer.echo(f"Total events: {stats['total_events']}")
    typer.echo(f"Completed: {stats['completed_workflows']}")
    typer.echo(f"Failed: {stats['failed_workflows']}")

    if stats['total_traces'] > 0:
        typer.echo(f"Avg duration: {stats['avg_duration_ms']}ms")

        typer.echo("\nRecent traces:")
        for trace in tracer.get_recent_traces(5):
            status_icon = "✅" if trace.status == "completed" else "❌"
            typer.echo(f"  {status_icon} {trace.trace_id}")
            typer.echo(f"     Type: {trace.workflow_type}")
            typer.echo(f"     Duration: {trace.duration_ms}ms")
            typer.echo(f"     Agents: {trace.agent_count}")
            typer.echo()


def _run_kimi(agent: str, yolo: bool, work_dir: str):
    """Helper to run kimi with agent."""
    agent_file = KIMI_TACHI_DIR / f"{agent}.yaml"
    if not agent_file.exists():
        typer.echo(f"Error: Agent '{agent}' not found at {agent_file}", err=True)
        typer.echo("Run 'kimi-tachi install' first.", err=True)
        sys.exit(1)

    kimi_path = _get_kimi_path()
    cmd = [kimi_path, "--agent-file", str(agent_file), "--work-dir", work_dir]

    if yolo:
        cmd.append("--yolo")

    typer.echo(f"◕‿◕ Starting kimi-tachi with {agent}...")
    subprocess.run(cmd)


def main():
    # If no command provided, start interactive session with kamaji
    if len(sys.argv) > 1 and sys.argv[1] in ["--help", "-h", "--version", "-V"]:
        app()
    elif len(sys.argv) == 1:
        # No args - start interactive session
        _run_kimi("kamaji", False, ".")
    else:
        app()


if __name__ == "__main__":
    main()
