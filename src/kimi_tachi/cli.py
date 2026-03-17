#!/usr/bin/env python3
"""
kimi-tachi (君たち) - Multi-agent task orchestration for Kimi CLI
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import typer
from typing_extensions import Annotated

app = typer.Typer(
    name="kimi-tachi",
    help="Multi-agent task orchestration for Kimi CLI",
    add_completion=False,
)

# Paths
KIMI_CONFIG_DIR = Path.home() / ".kimi"
KIMI_TACHI_DIR = KIMI_CONFIG_DIR / "agents" / "kimi-tachi"
PACKAGE_DIR = Path(__file__).parent.parent.parent


def _get_kimi_path() -> str:
    """Find kimi executable."""
    kimi_path = shutil.which("kimi")
    if kimi_path:
        return kimi_path
    typer.echo("Error: 'kimi' not found in PATH. Please install Kimi CLI first.", err=True)
    sys.exit(1)


@app.command()
def install(
    force: Annotated[bool, typer.Option("--force", "-f", help="Overwrite existing files")] = False
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
    typer.echo(f"\nUsage:")
    typer.echo(f"  kimi-tachi run              # Start with sisyphus (default)")
    typer.echo(f"  kimi-tachi run --agent oracle   # Start with oracle")
    typer.echo(f"  kimi --agent {KIMI_TACHI_DIR / 'sisyphus.yaml'}")


@app.command()
def run(
    agent: Annotated[str, typer.Option("--agent", "-a", help="Agent to use")] = "sisyphus",
    yolo: Annotated[bool, typer.Option("--yolo", "-y", help="Auto-approve all actions")] = False,
    plan: Annotated[bool, typer.Option("--plan", "-p", help="Start in plan mode")] = False,
    work_dir: Annotated[str, typer.Option("--work-dir", "-w", help="Working directory")] = ".",
):
    """Run Kimi CLI with kimi-tachi agent."""
    
    agent_file = KIMI_TACHI_DIR / f"{agent}.yaml"
    if not agent_file.exists():
        typer.echo(f"Error: Agent '{agent}' not found at {agent_file}", err=True)
        typer.echo(f"Available agents: {', '.join(a.stem for a in KIMI_TACHI_DIR.glob('*.yaml'))}", err=True)
        sys.exit(1)
    
    kimi_path = _get_kimi_path()
    cmd = [kimi_path, "--agent", str(agent_file), "--work-dir", work_dir]
    
    if yolo:
        cmd.append("--yolo")
    if plan:
        # Note: Kimi CLI may not have --plan flag, use /plan command instead
        typer.echo("Note: Plan mode will be activated via /plan command after startup")
    
    typer.echo(f"🚀 Starting kimi-tachi with {agent}...")
    subprocess.run(cmd)


@app.command()
def do(
    prompt: str,
    agent: Annotated[str, typer.Option("--agent", "-a")] = "sisyphus",
    yolo: Annotated[bool, typer.Option("--yolo", "-y")] = True,
):
    """One-shot mode: execute a single prompt and exit."""
    
    agent_file = KIMI_TACHI_DIR / f"{agent}.yaml"
    if not agent_file.exists():
        typer.echo(f"Error: Agent '{agent}' not found", err=True)
        sys.exit(1)
    
    kimi_path = _get_kimi_path()
    cmd = [kimi_path, "--agent", str(agent_file)]
    
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
        "sisyphus": "Task Orchestrator - The commander who coordinates the squad",
        "oracle": "Architecture Consultant - For complex technical decisions",
        "hermes": "Code Explorer - Fast exploration and navigation",
        "hephaestus": "Implementation Expert - Deep coding and refactoring",
        "momus": "Code Reviewer - Quality assurance and audits",
        "prometheus": "Research Planner - Large-scale analysis and planning",
        "librarian": "Knowledge Manager - Documentation and information retrieval",
    }
    
    for agent_file in sorted(KIMI_TACHI_DIR.glob("*.yaml")):
        name = agent_file.stem
        desc = agents.get(name, "Specialized agent")
        typer.echo(f"  {name:15} - {desc}")


@app.command()
def status():
    """Check kimi-tachi installation status."""
    
    typer.echo("kimi-tachi Status:\n")
    
    # Check Kimi CLI
    kimi_path = shutil.which("kimi")
    if kimi_path:
        typer.echo(f"  ✓ Kimi CLI: {kimi_path}")
    else:
        typer.echo("  ✗ Kimi CLI: Not found")
    
    # Check installation
    if KIMI_TACHI_DIR.exists():
        agent_count = len(list(KIMI_TACHI_DIR.glob("*.yaml")))
        typer.echo(f"  ✓ Agents installed: {agent_count}")
    else:
        typer.echo(f"  ✗ Agents: Not installed")
        typer.echo(f"    Run: kimi-tachi install")
    
    # Check skills
    skills_dir = KIMI_CONFIG_DIR / "skills"
    if skills_dir.exists():
        skill_count = len([d for d in skills_dir.iterdir() if d.is_dir()])
        typer.echo(f"  ✓ Skills installed: {skill_count}")
    else:
        typer.echo(f"  ✗ Skills: Not installed")


def main():
    app()


if __name__ == "__main__":
    main()
