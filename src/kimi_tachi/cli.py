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
PACKAGE_DIR = Path(__file__).parent.parent.parent

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

    typer.echo("\n✨ kimi-tachi installed successfully!")

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


@app.command()
def status():
    """Check kimi-tachi installation status."""
    from .compatibility import check_compatibility, print_compatibility_status
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
