"""
Tests for kimi-tachi plugins.

Author: kimi-tachi Team
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

PLUGINS_DIR = Path(__file__).parent.parent / "plugins"


class TestKimiTachiPlugin:
    """Test kimi-tachi plugin tools."""

    def run_tool(self, tool_name: str, input_data: dict) -> dict:
        """Helper to run a plugin tool"""
        tool_path = PLUGINS_DIR / "kimi-tachi" / "scripts" / f"{tool_name}.py"
        result = subprocess.run(
            [sys.executable, str(tool_path)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
        )
        return json.loads(result.stdout)

    def test_list_agents(self):
        """Test list_agents tool"""
        result = self.run_tool("list_agents", {})

        assert result["success"] is True
        assert "agents" in result
        assert len(result["agents"]) == 7

        # Check kamaji
        kamaji = next(a for a in result["agents"] if a["id"] == "kamaji")
        assert kamaji["icon"] == "◕‿◕"
        assert kamaji["role"] == "coordinator"

    def test_agent_info_valid(self):
        """Test agent_info with valid agent"""
        result = self.run_tool("agent_info", {"agent": "nekobasu"})

        assert result["success"] is True
        assert result["agent"]["name"] == "猫バス (Nekobasu)"
        assert result["agent"]["icon"] == "🚌"
        assert "abilities" in result["agent"]

    def test_agent_info_invalid(self):
        """Test agent_info with invalid agent"""
        result = self.run_tool("agent_info", {"agent": "invalid"})

        assert result["success"] is False
        assert "error" in result

    def test_check_compatibility(self):
        """Test check_compatibility tool"""
        result = self.run_tool("check_compatibility", {})

        assert result["success"] is True
        assert "cli_version" in result
        assert "compatible" in result


class TestTodoEnforcerPlugin:
    """Test todo-enforcer plugin tools."""

    def run_tool(self, tool_name: str, input_data: dict) -> dict:
        """Helper to run a plugin tool"""
        tool_path = PLUGINS_DIR / "todo-enforcer" / "scripts" / f"{tool_name}.py"
        result = subprocess.run(
            [sys.executable, str(tool_path)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
        )
        return json.loads(result.stdout)

    def test_validate_todos_all_completed(self):
        """Test validate_todos with all completed"""
        todos = [
            {"title": "Task 1", "status": "completed"},
            {"title": "Task 2", "status": "completed"},
        ]
        result = self.run_tool("validate_todos", {"todos": todos})

        assert result["success"] is True
        assert result["valid"] is True
        assert result["stats"]["completed"] == 2

    def test_validate_todos_with_pending(self):
        """Test validate_todos with pending items"""
        todos = [
            {"title": "Task 1", "status": "completed"},
            {"title": "Task 2", "status": "pending"},
        ]
        result = self.run_tool("validate_todos", {"todos": todos})

        assert result["success"] is True
        assert result["valid"] is False
        assert result["stats"]["pending"] == 1

    def test_validate_todos_empty(self):
        """Test validate_todos with empty list"""
        result = self.run_tool("validate_todos", {"todos": []})

        assert result["success"] is True
        assert result["valid"] is True

    def test_check_format_valid(self):
        """Test check_format with valid todos"""
        todos = [
            {"title": "Implement feature X", "status": "pending"},
            {"title": "Write tests", "status": "in_progress"},
        ]
        result = self.run_tool("check_format", {"todos": todos})

        assert result["success"] is True
        assert result["valid"] is True

    def test_generate_template(self):
        """Test generate_template tool"""
        result = self.run_tool("generate_template", {"task_type": "feature"})

        assert result["success"] is True
        assert "template" in result
        assert len(result["template"]) > 0


class TestCategoryRouterPlugin:
    """Test category-router plugin tools."""

    def run_tool(self, tool_name: str, input_data: dict) -> dict:
        """Helper to run a plugin tool"""
        tool_path = PLUGINS_DIR / "category-router" / "scripts" / f"{tool_name}.py"
        result = subprocess.run(
            [sys.executable, str(tool_path)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
        )
        return json.loads(result.stdout)

    def test_route_task_implement(self):
        """Test route_task for implementation task"""
        result = self.run_tool("route_task", {"task": "implement user auth"})

        assert result["success"] is True
        assert result["category"] == "implement"
        assert result["agent"] == "calcifer"

    def test_route_task_explore(self):
        """Test route_task for exploration task"""
        result = self.run_tool("route_task", {"task": "find all API endpoints"})

        assert result["success"] is True
        assert result["category"] == "explore"
        assert result["agent"] == "nekobasu"

    def test_detect_category(self):
        """Test detect_category tool"""
        result = self.run_tool("detect_category", {"text": "design the database schema"})

        assert result["success"] is True
        assert "detected_category" in result
        assert "confidence" in result

    def test_list_categories(self):
        """Test list_categories tool"""
        result = self.run_tool("list_categories", {})

        assert result["success"] is True
        assert "categories" in result
        assert len(result["categories"]) == 6


class TestPluginJson:
    """Test plugin.json files are valid."""

    def test_kimi_tachi_plugin_json(self):
        """Test kimi-tachi plugin.json is valid"""
        plugin_path = PLUGINS_DIR / "kimi-tachi" / "plugin.json"
        with open(plugin_path) as f:
            plugin = json.load(f)

        assert plugin["name"] == "kimi-tachi"
        assert "tools" in plugin
        assert len(plugin["tools"]) >= 1

        # Check tool structure
        for tool in plugin["tools"]:
            assert "name" in tool
            assert "command" in tool
            assert "description" in tool

    def test_todo_enforcer_plugin_json(self):
        """Test todo-enforcer plugin.json is valid"""
        plugin_path = PLUGINS_DIR / "todo-enforcer" / "plugin.json"
        with open(plugin_path) as f:
            plugin = json.load(f)

        assert plugin["name"] == "todo-enforcer"
        assert "tools" in plugin

    def test_category_router_plugin_json(self):
        """Test category-router plugin.json is valid"""
        plugin_path = PLUGINS_DIR / "category-router" / "plugin.json"
        with open(plugin_path) as f:
            plugin = json.load(f)

        assert plugin["name"] == "category-router"
        assert "tools" in plugin


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
