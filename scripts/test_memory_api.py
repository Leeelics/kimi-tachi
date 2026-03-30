#!/usr/bin/env python3
"""
Test TachiMemory API integration

Run: python3 scripts/test_memory_api.py
"""

import asyncio
import sys
import tempfile
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


def print_section(title):
    """Print a section header."""
    console.print(f"\n[bold cyan]{'=' * 60}[/bold cyan]")
    console.print(f"[bold cyan]{title}[/bold cyan]")
    console.print(f"[bold cyan]{'=' * 60}[/bold cyan]\n")


def print_success(msg):
    console.print(f"[green]✓[/green] {msg}")


def print_error(msg):
    console.print(f"[red]✗[/red] {msg}")


def print_info(msg):
    console.print(f"[dim]ℹ {msg}[/dim]")


async def setup_test_project():
    """Create a temporary test project with Git history."""
    import subprocess
    
    test_dir = tempfile.mkdtemp(prefix="kimi-tachi-test-")
    os.chdir(test_dir)
    
    # Init git
    subprocess.run(["git", "init"], capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], capture_output=True)
    
    # Create test files
    Path("auth.py").write_text('''
"""Authentication module."""
class AuthManager:
    def authenticate(self, username: str, password: str):
        """Authenticate user with credentials."""
        pass
    
    def generate_token(self, user_id: str) -> str:
        """Generate JWT token."""
        return f"token_{user_id}"
''')
    
    Path("models.py").write_text('''
"""Data models."""
class User:
    def __init__(self, id: int, name: str):
        self.id = id
        self.name = name
''')
    
    # Commit
    subprocess.run(["git", "add", "."], capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], capture_output=True)
    
    # Add more files
    Path("api.py").write_text('''
"""API endpoints."""
def login(username: str, password: str):
    """Login endpoint."""
    pass
''')
    
    subprocess.run(["git", "add", "."], capture_output=True)
    subprocess.run(["git", "commit", "-m", "Add API"], capture_output=True)
    
    return test_dir


async def test_memory_init():
    """Test memory initialization."""
    print_section("Test 1: Memory Initialization")
    
    try:
        from kimi_tachi.memory import TachiMemory
        
        memory = await TachiMemory.init(".")
        print_success(f"Memory initialized: {memory.project_path}")
        print_info(f"Session ID: {memory._current_session_id}")
        return memory
    except Exception as e:
        print_error(f"Failed to initialize memory: {e}")
        return None


async def test_indexing(memory):
    """Test project indexing."""
    print_section("Test 2: Project Indexing")
    
    try:
        # First index
        print_info("First index (should index all)...")
        stats = await memory.index_project(git=True, code=True, incremental=True)
        print_success(f"Indexed: {stats.get('git_commits', 0)} commits, {stats.get('code_symbols', 0)} symbols")
        
        # Second index (should skip)
        print_info("Second index (should skip)...")
        stats2 = await memory.index_project(git=True, code=True, incremental=True)
        skipped = stats2.get('skipped', 0)
        if skipped > 0:
            print_success(f"Incremental indexing works ({skipped} items skipped)")
        else:
            print_info("Incremental indexing may not be working (0 skipped)")
        
        return True
    except Exception as e:
        print_error(f"Indexing failed: {e}")
        return False


async def test_search(memory):
    """Test memory search."""
    print_section("Test 3: Memory Search")
    
    try:
        results = await memory.search("authentication", limit=5)
        
        if results:
            print_success(f"Found {len(results)} results")
            
            table = Table(title="Search Results")
            table.add_column("Type", style="cyan")
            table.add_column("Source", style="green")
            table.add_column("Preview", style="white")
            
            for r in results[:3]:
                result_type = r.get("type", "unknown")
                source = r.get("source", r.get("file", "unknown"))[:30]
                content = r.get("content", "")[:50] or r.get("name", "")
                table.add_row(result_type, source, content)
            
            console.print(table)
        else:
            print_info("No results found (this may be OK)")
        
        return True
    except Exception as e:
        print_error(f"Search failed: {e}")
        return False


async def test_code_search(memory):
    """Test code-specific search."""
    print_section("Test 4: Code Search")
    
    try:
        results = await memory.search_code("authenticate", limit=5)
        
        if results:
            print_success(f"Found {len(results)} code symbols")
            for r in results[:3]:
                print_info(f"  - {r.get('name')} ({r.get('file')})")
        else:
            print_info("No code results found (this may be OK)")
        
        return True
    except Exception as e:
        print_error(f"Code search failed: {e}")
        return False


async def test_agent_context(memory):
    """Test agent context management."""
    print_section("Test 5: Agent Context Management")
    
    try:
        # Recall initial context
        print_info("Recalling kamaji context...")
        context = await memory.recall_agent_context("kamaji")
        print_success(f"Recalled: {len(context.recent_memories)} memories")
        
        # Store something
        print_info("Storing agent output...")
        memory_id = await memory.store_agent_output(
            agent="kamaji",
            output="Test decision: Use JWT authentication",
            task="Choose auth method",
            metadata={"decision": "JWT"}
        )
        print_success(f"Stored: {memory_id[:8] if memory_id else 'N/A'}...")
        
        # Recall again (should see new memory)
        print_info("Recalling again...")
        context2 = await memory.recall_agent_context("kamaji")
        print_success(f"Now has: {len(context2.recent_memories)} memories")
        
        return True
    except Exception as e:
        print_error(f"Agent context test failed: {e}")
        return False


async def test_global_memory(memory):
    """Test global memory features."""
    print_section("Test 6: Global Memory")
    
    try:
        # Register project
        print_info("Registering project in global memory...")
        success = await memory.register_in_global_memory("test-project")
        if success:
            print_success("Project registered")
        
        # Sync
        print_info("Syncing to global memory...")
        result = await memory.sync_to_global_memory("test-project", incremental=True)
        print_success(f"Synced: {result}")
        
        # Global search
        print_info("Searching global memory...")
        global_results = await memory.search_global_memory("auth", limit=5)
        print_success(f"Found {len(global_results)} global results")
        
        return True
    except Exception as e:
        print_error(f"Global memory test failed: {e}")
        return False


async def main():
    """Run all tests."""
    console.print(Panel.fit(
        "[bold blue]Kimi-Tachi Memory API Test[/bold blue]\n"
        "Testing memory integration with MemNexus",
        title="🧠 Memory Test",
        border_style="blue"
    ))
    
    # Setup
    original_dir = os.getcwd()
    test_dir = None
    
    try:
        test_dir = await setup_test_project()
        print_info(f"Test project: {test_dir}")
        
        # Run tests
        tests = [
            ("Init", test_memory_init),
            ("Indexing", test_indexing),
            ("Search", test_search),
            ("Code Search", test_code_search),
            ("Agent Context", test_agent_context),
            ("Global Memory", test_global_memory),
        ]
        
        results = {}
        memory = None
        
        for name, test_func in tests:
            if name == "Init":
                memory = await test_func()
                results[name] = memory is not None
            elif memory:
                results[name] = await test_func(memory)
            else:
                print_error(f"Skipping {name} (no memory)")
                results[name] = False
        
        # Summary
        print_section("Test Summary")
        
        passed = sum(1 for v in results.values() if v)
        total = len(results)
        
        table = Table(title="Results")
        table.add_column("Test", style="cyan")
        table.add_column("Status", style="bold")
        
        for name, result in results.items():
            status = "[green]PASS[/green]" if result else "[red]FAIL[/red]"
            table.add_row(name, status)
        
        console.print(table)
        console.print(f"\n[bold]{'=' * 60}[/bold]")
        
        if passed == total:
            console.print(f"[bold green]All {passed}/{total} tests passed! ✓[/bold green]")
        else:
            console.print(f"[bold yellow]{passed}/{total} tests passed[/bold yellow]")
        
    finally:
        # Cleanup
        os.chdir(original_dir)
        if test_dir and os.path.exists(test_dir):
            import shutil
            shutil.rmtree(test_dir)
            print_info(f"Cleaned up: {test_dir}")


if __name__ == "__main__":
    asyncio.run(main())
