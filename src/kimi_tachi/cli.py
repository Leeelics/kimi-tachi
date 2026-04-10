#!/usr/bin/env python3
"""kimi-tachi (君たち) - Multi-agent task orchestration for Kimi CLI"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Annotated

import typer

from kimi_tachi import __version__

# Optional memory support (import guard for backward compatibility)
try:
    from kimi_tachi.memory import AGENT_MEMORY_PROFILES, TachiMemory

    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False
    TachiMemory = None
    AGENT_MEMORY_PROFILES = {}

# Team management
try:
    from kimi_tachi.team import AgentNotFoundError, TeamManager, TeamNotFoundError

    TEAM_AVAILABLE = True
except ImportError:
    TEAM_AVAILABLE = False
    TeamManager = None
    TeamNotFoundError = Exception
    AgentNotFoundError = Exception

app = typer.Typer(
    name="kimi-tachi",
    help="Multi-agent task orchestration for Kimi CLI",
    add_completion=False,
)

# Paths
KIMI_CONFIG_DIR = Path.home() / ".kimi"
KIMI_TACHI_DIR = KIMI_CONFIG_DIR / "agents" / "kimi-tachi"
PACKAGE_DIR = Path(__file__).parent


def _resolve_data_dir(name: str) -> Path:
    """Resolve package data directory, handling both production and editable installs."""
    path = PACKAGE_DIR / name
    if path.exists():
        return path
    # Fallback for editable installs where force-include data isn't symlinked
    return Path(__file__).parent.parent.parent / name


def _get_kimi_path() -> str:
    """Find kimi executable."""
    kimi_path = shutil.which("kimi")
    if not kimi_path:
        typer.echo("Error: 'kimi' not found in PATH. Please install Kimi CLI first.", err=True)
        raise typer.Exit(1)
    return kimi_path


def _run_kimi(agent: str | None, yolo: bool, work_dir: str) -> None:
    """Helper to run kimi with an agent."""
    if TEAM_AVAILABLE:
        manager = TeamManager()
        if agent is None:
            coordinator = manager.get_coordinator_agent()
            agent_file = Path(coordinator.agent_file)
            agent_name = coordinator.agent_name
            team_name = manager.current_team.name
            typer.echo(f"🎭 Starting {team_name} with {agent_name}...")
        else:
            try:
                resolved = manager.resolve_agent(agent)
                agent_file = Path(resolved.agent_file)
                agent_name = resolved.agent_name
            except AgentNotFoundError as e:
                typer.echo(f"Error: {e}", err=True)
                raise typer.Exit(1) from None
    else:
        if agent is None:
            agent = "kamaji"
        agent_file = KIMI_TACHI_DIR / f"{agent}.yaml"
        agent_name = agent

    if not agent_file.exists():
        typer.echo(f"Error: Agent '{agent_name}' not found at {agent_file}", err=True)
        raise typer.Exit(1)

    cmd = [_get_kimi_path(), "--agent-file", str(agent_file), "--work-dir", work_dir]
    if yolo:
        cmd.append("--yolo")
    subprocess.run(cmd)


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


@app.command()
def install(
    skip_existing: Annotated[
        bool, typer.Option("--skip-existing", help="Skip files that already exist")
    ] = False,
):
    """Install or upgrade kimi-tachi agents and skills to Kimi CLI."""
    if not KIMI_CONFIG_DIR.exists():
        typer.echo(f"Error: Kimi CLI config directory not found at {KIMI_CONFIG_DIR}", err=True)
        raise typer.Exit(1)

    KIMI_TACHI_DIR.mkdir(parents=True, exist_ok=True)
    (KIMI_CONFIG_DIR / "skills").mkdir(exist_ok=True)

    # Copy agents (including teams.yaml and all team subdirectories)
    agents_source = _resolve_data_dir("agents")
    if agents_source.exists():
        teams_yaml = agents_source / "teams.yaml"
        if teams_yaml.exists():
            dest = KIMI_TACHI_DIR / "teams.yaml"
            if dest.exists() and skip_existing:
                typer.echo("Skipping teams.yaml (already exists)")
            else:
                shutil.copy2(teams_yaml, dest)
                action = "Updated" if dest.exists() else "Installed"
                typer.echo(f"{action}: teams.yaml")

        for item in agents_source.iterdir():
            if item.is_dir():
                dest = KIMI_TACHI_DIR / item.name
                existed = dest.exists()
                if existed and skip_existing:
                    typer.echo(f"Skipping team {item.name} (already exists)")
                else:
                    if existed:
                        shutil.rmtree(dest)
                    shutil.copytree(item, dest)
                    yaml_count = len(list(dest.glob("*.yaml")))
                    action = "Updated" if existed else "Installed"
                    typer.echo(f"{action} team: {item.name} ({yaml_count} agents)")

    # Copy skills
    skills_source = _resolve_data_dir("skills")
    if skills_source.exists():
        for skill_dir in skills_source.iterdir():
            if skill_dir.is_dir():
                dest = KIMI_CONFIG_DIR / "skills" / skill_dir.name
                existed = dest.exists()
                if existed and skip_existing:
                    typer.echo(f"Skipping skill {skill_dir.name} (already exists)")
                else:
                    if existed:
                        shutil.rmtree(dest)
                    shutil.copytree(skill_dir, dest)
                    action = "Updated" if existed else "Installed"
                    typer.echo(f"{action} skill: {skill_dir.name}")

    # Copy plugins
    plugins_source = _resolve_data_dir("plugins")
    if plugins_source.exists():
        (KIMI_CONFIG_DIR / "plugins").mkdir(exist_ok=True)
        for plugin_dir in plugins_source.iterdir():
            if plugin_dir.is_dir():
                dest = KIMI_CONFIG_DIR / "plugins" / plugin_dir.name
                existed = dest.exists()
                if existed and skip_existing:
                    typer.echo(f"Skipping plugin {plugin_dir.name} (already exists)")
                else:
                    if existed:
                        shutil.rmtree(dest)
                    shutil.copytree(plugin_dir, dest)
                    action = "Updated" if existed else "Installed"
                    typer.echo(f"{action} plugin: {plugin_dir.name}")

    typer.echo("\n✨ kimi-tachi installed successfully!")
    typer.echo("\nUsage:")
    typer.echo("  kimi-tachi                    # Start with current team's coordinator")
    typer.echo("  kimi-tachi teams switch <id>  # Switch team")


@app.command()
def uninstall(
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation prompt")] = False,
):
    """Uninstall kimi-tachi."""
    typer.echo("🗑️  kimi-tachi Uninstall\n")

    if not KIMI_TACHI_DIR.exists() and not (KIMI_CONFIG_DIR / "skills").exists():
        typer.echo("❌ kimi-tachi is not installed.")
        return

    if not force:
        confirm = typer.prompt("Are you sure? [y/N]", default="n")
        if confirm.lower() not in ("y", "yes"):
            typer.echo("\n❌ Uninstall cancelled.")
            return

    if KIMI_TACHI_DIR.exists():
        shutil.rmtree(KIMI_TACHI_DIR)
        typer.echo("  ✓ Removed agents")

    skills_dir = KIMI_CONFIG_DIR / "skills"
    if skills_dir.exists():
        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir():
                shutil.rmtree(skill_dir)
        typer.echo("  ✓ Removed skills")

    plugins_dir = KIMI_CONFIG_DIR / "plugins"
    if plugins_dir.exists():
        for plugin_dir in plugins_dir.iterdir():
            if plugin_dir.is_dir():
                shutil.rmtree(plugin_dir)
        typer.echo("  ✓ Removed plugins")

    config_file = KIMI_CONFIG_DIR / "kimi-tachi.config"
    if config_file.exists():
        config_file.unlink()
        typer.echo("  ✓ Removed config")

    typer.echo("\n✨ kimi-tachi uninstalled successfully!")


@app.command()
def teams(
    action: Annotated[str, typer.Argument(help="Action: list, switch, info, current")] = "list",
    team_id: Annotated[str | None, typer.Argument(help="Team ID (for switch/info)")] = None,
):
    """Manage kimi-tachi teams."""
    if not TEAM_AVAILABLE:
        typer.echo("❌ Team management not available.", err=True)
        raise typer.Exit(1)

    manager = TeamManager()

    if action == "list":
        _list_teams(manager)
    elif action == "switch":
        if not team_id:
            typer.echo("Error: team_id required for switch", err=True)
            raise typer.Exit(1)
        try:
            old_team = manager.current_team
            manager.switch_team(team_id)
            new_team = manager.current_team
            typer.echo(f"\n✅ Switched from '{old_team.name}' to '{new_team.name}'")
            typer.echo(f"   Coordinator: {new_team.coordinator}")
        except TeamNotFoundError as e:
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(1) from None
    elif action == "info":
        if not team_id:
            team_id = manager.current_team.id
        try:
            team = manager.get_team(team_id)
            is_current = team.id == manager.current_team.id
            typer.echo(f"\nTeam: {team.name}{' [CURRENT]' if is_current else ''}")
            typer.echo(f"ID: {team.id}")
            typer.echo(f"Description: {team.description}")
            typer.echo(f"Coordinator: {team.coordinator}")
            agents = manager._list_available_agents(team)
            typer.echo(f"\nAgents ({len(agents)}):")
            for agent in agents:
                info = team.agents.get(agent, {})
                icon = info.get("icon", "🤖")
                name = info.get("name", agent)
                role = info.get("role", "unknown")
                prefix = "  → " if agent == team.coordinator else "    "
                typer.echo(f"{prefix}{icon} {agent:<15} {name} ({role})")
            if team.workflow_patterns:
                typer.echo("\nWorkflow patterns:")
                for pattern, flow in team.workflow_patterns.items():
                    typer.echo(f"  {pattern}: {flow}")
        except TeamNotFoundError as e:
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(1) from None
    elif action == "current":
        team = manager.current_team
        typer.echo(f"Current team: {team.name} ({team.id})")
        typer.echo(f"Coordinator: {team.coordinator}")
    else:
        typer.echo(f"Unknown action: {action}", err=True)
        typer.echo("Available actions: list, switch, info, current", err=True)
        raise typer.Exit(1)


def _list_teams(manager: TeamManager) -> None:
    """List all available teams with their agents."""
    teams = manager.list_teams()
    current = manager.current_team
    typer.echo("\n" + "=" * 60)
    typer.echo("Available Teams")
    typer.echo("=" * 60)
    for team in teams:
        marker = " → " if team.id == current.id else "   "
        typer.echo(f"{marker}{team.id:<20} {team.name}")
        typer.echo(f"   {' ' * 20} {team.description}")
        agents = manager._list_available_agents(team)
        for agent in agents:
            info = team.agents.get(agent, {})
            icon = info.get("icon", "🤖")
            name = info.get("name", agent)
            role = info.get("role", "unknown")
            prefix = "     → " if agent == team.coordinator else "       "
            typer.echo(f"{prefix}{icon} {agent:<15} {name} ({role})")
    typer.echo("=" * 60)
    typer.echo(f"\nCurrent: {current.name} ({current.id})")


@app.command()
def status():
    """Check kimi-tachi installation status."""
    from .compatibility import check_compatibility
    from .config import KimiTachiConfig

    typer.echo("kimi-tachi Status:\n")
    typer.echo(f"  kimi-tachi version: {__version__}")
    typer.echo()

    report = check_compatibility()
    if report.is_compatible:
        typer.echo(f"    ✓ kimi-cli {report.cli_version} (compatible)")
    else:
        typer.echo(f"    ✗ {report.message}")
        typer.echo(f"    → {report.recommendation}")
    typer.echo()

    config = KimiTachiConfig.from_env()
    typer.echo(f"  Agent Mode: {config.effective_agent_mode}")
    typer.echo(f"    (set via KIMI_TACHI_AGENT_MODE={config.agent_mode})")
    typer.echo()

    kimi_path = shutil.which("kimi")
    if kimi_path:
        typer.echo(f"  ✓ Kimi CLI: {kimi_path}")
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

    if KIMI_TACHI_DIR.exists():
        if TEAM_AVAILABLE:
            try:
                manager = TeamManager()
                teams = manager.list_teams()
                total_agents = sum(len(manager._list_available_agents(t)) for t in teams)
                typer.echo(f"  ✓ Agents installed: {total_agents} across {len(teams)} teams")
                for team in teams:
                    count = len(manager._list_available_agents(team))
                    typer.echo(f"    • {team.id}: {count} agents")
            except Exception:
                count = len(list(KIMI_TACHI_DIR.glob("*.yaml")))
                typer.echo(f"  ✓ Agents installed: {count}")
        else:
            count = len(list(KIMI_TACHI_DIR.glob("*.yaml")))
            typer.echo(f"  ✓ Agents installed: {count}")
    else:
        typer.echo("  ✗ Agents: Not installed")
        typer.echo("    Run: kimi-tachi install")

    skills_dir = KIMI_CONFIG_DIR / "skills"
    if skills_dir.exists():
        skill_count = len([d for d in skills_dir.iterdir() if d.is_dir()])
        typer.echo(f"  ✓ Skills installed: {skill_count}")

    plugins_dir = KIMI_CONFIG_DIR / "plugins"
    if plugins_dir.exists():
        plugin_count = len([d for d in plugins_dir.iterdir() if d.is_dir()])
        typer.echo(f"  ✓ Plugins installed: {plugin_count}")
        if plugin_count > 0:
            typer.echo("    (Use with kimi-cli 1.25.0+ plugin system)")


def main():
    """Main entry point."""
    if len(sys.argv) > 1 and sys.argv[1] in ("--help", "-h", "--version", "-V"):
        app()
    elif len(sys.argv) == 1:
        _run_kimi(None, False, ".")
    else:
        app()


if __name__ == "__main__":
    main()
