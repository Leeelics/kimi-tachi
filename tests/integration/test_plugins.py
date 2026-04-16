"""
Tests for kimi-tachi plugins.

Author: kimi-tachi Team
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

PLUGINS_DIR = Path(__file__).parent.parent.parent / "plugins"


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
        assert result["agent"]["name"] == "猫バス"
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

    def test_workflow_plan(self):
        """Test workflow tool returns a plan (not executes agents)"""
        result = self.run_tool(
            "workflow",
            {"task": "implement user authentication", "workflow_type": "feature"},
        )

        assert result["success"] is True
        assert "phases" in result
        assert "recommendations" in result
        assert len(result["phases"]) > 0
        assert result["workflow_type"] == "feature"

        # Verify phases have required fields
        for phase in result["phases"]:
            assert "agent" in phase
            assert "description" in phase
            assert "prompt" in phase
            assert "subagent_type" in phase
            assert "resume" in phase
            assert phase["resume"] is None or isinstance(phase["resume"], str)
            # model is optional; when present it should be a string
            if "model" in phase:
                assert isinstance(phase["model"], str)

        # Verify recommendations
        rec = result["recommendations"]
        assert "use_plan_mode" in rec
        assert "plan_mode_reason" in rec
        assert "use_todo_list" in rec
        assert "parallel_steps" in rec

        # Verify todo_items and plan_file_path for multi-phase plans
        assert "todo_items" in result
        assert len(result["todo_items"]) == len(result["phases"])
        for item in result["todo_items"]:
            assert "title" in item
            assert item["status"] == "pending"
        assert "plan_file_path" in result
        assert isinstance(result["plan_file_path"], str)

    def test_workflow_plan_simple_task(self):
        """Test workflow plan for simple tasks skips plan mode."""
        result = self.run_tool(
            "workflow",
            {"task": "fix typo in readme", "workflow_type": "auto"},
        )

        assert result["success"] is True
        assert result["workflow_type"] == "quick"
        rec = result["recommendations"]
        assert rec["use_plan_mode"] is False
        assert (
            "simple" in rec["plan_mode_reason"].lower()
            or "directly" in rec["plan_mode_reason"].lower()
        )
        # Single-phase plans should not emit todo_items or plan_file_path
        assert result.get("todo_items") is None
        assert result.get("plan_file_path") is None

    def test_workflow_plan_model_override(self):
        """Test that shishigami phase recommends a stronger model."""
        result = self.run_tool(
            "workflow",
            {"task": "design microservices architecture", "workflow_type": "feature"},
        )

        assert result["success"] is True
        shishigami_phases = [p for p in result["phases"] if p["agent"] == "shishigami"]
        assert len(shishigami_phases) >= 1
        for phase in shishigami_phases:
            assert phase.get("model") == "kimi-k2.5"

    def test_workflow_plan_content_team(self):
        """Test workflow for content team maps agents to their own subagent types."""
        result = self.run_tool(
            "workflow",
            {
                "task": "write an article about AI trends",
                "workflow_type": "article",
                "team": "content",
            },
        )

        assert result["success"] is True
        assert result["team"] == "content"
        assert len(result["phases"]) >= 1
        for phase in result["phases"]:
            # Content team agents should map to themselves as subagent types
            assert phase["subagent_type"] == phase["agent"]

    def test_list_tasks_no_data_dir(self):
        """Test list_tasks gracefully handles missing kimi data directory."""
        result = self.run_tool("list_tasks", {})

        # In CI/test environments there may be no kimi data dir
        if result["success"]:
            assert "tasks" in result
        else:
            assert "error" in result
            assert (
                "not found" in result["error"].lower()
                or "data directory" in result["error"].lower()
            )

    def test_session_status_missing_session(self):
        """Test session_status returns error for unknown session."""
        result = self.run_tool("session_status", {"session_id": "nonexistent_session_xyz"})

        assert result["success"] is False
        assert "error" in result
        assert "not found" in result["error"].lower()

    def test_execute_workflow_spawn(self):
        """Test execute_workflow returns spawn for pending phases."""
        plan = {
            "success": True,
            "workflow_type": "feature",
            "team": "coding",
            "task": "implement auth",
            "work_dir": ".",
            "complexity": "medium",
            "phases": [
                {
                    "agent": "calcifer",
                    "description": "Implement auth",
                    "prompt": "Write the auth code",
                    "subagent_type": "coder",
                    "can_background": False,
                    "recommended_timeout": 300,
                }
            ],
            "parallel_batches": [[0]],
            "recommendations": {},
            "output": "plan output",
            "todo_items": [{"title": "calcifer: Implement auth", "status": "pending"}],
        }
        result = self.run_tool("execute_workflow", {"plan": plan, "state": {}})

        assert result["action"] == "spawn"
        assert len(result["spawn"]) == 1
        assert result["spawn"][0]["agent"] == "calcifer"
        assert result["todo_updates"][0]["status"] == "in_progress"

    def test_execute_workflow_complete(self):
        """Test execute_workflow returns complete when all phases done."""
        plan = {
            "success": True,
            "workflow_type": "quick",
            "team": "coding",
            "task": "fix typo",
            "work_dir": ".",
            "complexity": "simple",
            "phases": [
                {
                    "agent": "calcifer",
                    "description": "Fix typo",
                    "prompt": "Fix the typo",
                    "subagent_type": "coder",
                    "can_background": False,
                    "recommended_timeout": 120,
                }
            ],
            "parallel_batches": [[0]],
            "recommendations": {},
            "output": "plan output",
            "todo_items": [{"title": "calcifer: Fix typo", "status": "pending"}],
        }
        result = self.run_tool(
            "execute_workflow",
            {"plan": plan, "state": {"completed_phase_indices": [0], "current_batch_index": 1}},
        )

        assert result["action"] == "complete"
        assert result["todo_updates"][0]["status"] == "done"

    def test_execute_workflow_wait_for_background(self):
        """Test execute_workflow returns wait when background tasks pending."""
        plan = {
            "success": True,
            "workflow_type": "feature",
            "team": "coding",
            "task": "plan architecture",
            "work_dir": ".",
            "complexity": "complex",
            "phases": [
                {
                    "agent": "tasogare",
                    "description": "Plan",
                    "prompt": "Plan it",
                    "subagent_type": "plan",
                    "can_background": True,
                    "recommended_timeout": 300,
                }
            ],
            "parallel_batches": [[0]],
            "recommendations": {},
            "output": "plan output",
            "todo_items": [{"title": "tasogare: Plan", "status": "pending"}],
        }
        result = self.run_tool(
            "execute_workflow",
            {
                "plan": plan,
                "state": {
                    "completed_phase_indices": [],
                    "background_tasks": ["bg_123"],
                    "current_batch_index": 1,
                },
            },
        )

        assert result["action"] == "wait"
        assert result["wait_tasks"] == ["bg_123"]


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

        tool_names = {t["name"] for t in plugin["tools"]}
        expected_tools = {
            "workflow",
            "execute_workflow",
            "list_agents",
            "get_agent_info",
            "check_compatibility",
            "list_tasks",
            "session_status",
            "memory_search",
            "memory_global_search",
            "memory_recall_agent",
            "memory_store_decision",
        }
        assert expected_tools <= tool_names, f"Missing tools: {expected_tools - tool_names}"

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
