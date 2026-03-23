"""
Tests for parallel workflow execution
"""

from __future__ import annotations

import pytest

from kimi_tachi.orchestrator.dependency_analyzer import (
    DependencyGraph,
    TaskDependencyAnalyzer,
)
from kimi_tachi.orchestrator.workflow_engine import Phase, Workflow


class TestDependencyAnalyzer:
    """测试依赖分析器"""

    def test_empty_dependency_graph(self):
        """测试空依赖图"""
        graph = DependencyGraph(phases=[])
        assert graph.topological_sort() == []
        assert graph.find_parallel_groups() == []

    def test_single_phase(self):
        """测试单个 phase"""
        graph = DependencyGraph(phases=["phase1"])
        assert graph.topological_sort() == ["phase1"]
        assert graph.find_parallel_groups() == [["phase1"]]

    def test_linear_dependencies(self):
        """测试线性依赖"""
        graph = DependencyGraph(phases=["a", "b", "c"])
        graph.add_edge(
            type("Edge", (), {"from_phase": "a", "to_phase": "b", "reason": "test", "strength": 1.0})()
        )
        graph.add_edge(
            type("Edge", (), {"from_phase": "b", "to_phase": "c", "reason": "test", "strength": 1.0})()
        )

        # 拓扑排序
        sorted_phases = graph.topological_sort()
        assert sorted_phases.index("a") < sorted_phases.index("b")
        assert sorted_phases.index("b") < sorted_phases.index("c")

        # 并行组（线性依赖没有并行）
        groups = graph.find_parallel_groups()
        assert len(groups) == 3
        assert all(len(g) == 1 for g in groups)

    def test_parallel_dependencies(self):
        """测试并行依赖"""
        graph = DependencyGraph(phases=["a", "b", "c", "d"])
        # a -> b, a -> c (b 和 c 可以并行)
        graph.add_edge(
            type("Edge", (), {"from_phase": "a", "to_phase": "b", "reason": "test", "strength": 1.0})()
        )
        graph.add_edge(
            type("Edge", (), {"from_phase": "a", "to_phase": "c", "reason": "test", "strength": 1.0})()
        )
        # b -> d, c -> d
        graph.add_edge(
            type("Edge", (), {"from_phase": "b", "to_phase": "d", "reason": "test", "strength": 1.0})()
        )
        graph.add_edge(
            type("Edge", (), {"from_phase": "c", "to_phase": "d", "reason": "test", "strength": 1.0})()
        )

        groups = graph.find_parallel_groups()
        # 应该有 3 层: [a], [b, c], [d]
        assert len(groups) == 3
        assert groups[0] == ["a"]
        assert set(groups[1]) == {"b", "c"}
        assert groups[2] == ["d"]

    def test_circular_dependency_detection(self):
        """测试循环依赖检测"""
        graph = DependencyGraph(phases=["a", "b"])
        graph.add_edge(
            type("Edge", (), {"from_phase": "a", "to_phase": "b", "reason": "test", "strength": 1.0})()
        )
        graph.add_edge(
            type("Edge", (), {"from_phase": "b", "to_phase": "a", "reason": "test", "strength": 1.0})()
        )

        with pytest.raises(ValueError, match="Circular dependency"):
            graph.topological_sort()


class TestTaskDependencyAnalyzer:
    """测试任务依赖分析器"""

    def test_semantic_categorization(self):
        """测试语义分类"""
        analyzer = TaskDependencyAnalyzer()

        # 规划类
        assert analyzer._categorize_semantically("Create a plan for the project") == "planning"
        assert analyzer._categorize_semantically("Design the architecture") == "planning"

        # 探索类
        assert analyzer._categorize_semantically("Explore the codebase") == "exploration"
        assert analyzer._categorize_semantically("Analyze the patterns") == "exploration"

        # 实现类
        assert analyzer._categorize_semantically("Implement the feature") == "implementation"
        assert analyzer._categorize_semantically("Write the code") == "implementation"

        # 审查类
        assert analyzer._categorize_semantically("Review the changes") == "review"

        # 文档类
        assert analyzer._categorize_semantically("Document the API") == "documentation"

        # 未知
        assert analyzer._categorize_semantically("Something random") == "unknown"

    def test_implicit_dependencies(self):
        """测试隐式依赖检测"""
        analyzer = TaskDependencyAnalyzer()

        phases = [
            Phase(name="plan", agent="tasogare", task_template="Create a plan"),
            Phase(name="implement", agent="calcifer", task_template="Implement the feature"),
        ]

        graph = analyzer.analyze(phases)

        # implementation 应该依赖 planning
        assert "plan" in graph.get_dependencies("implement")

    def test_explicit_dependencies(self):
        """测试显式依赖"""
        analyzer = TaskDependencyAnalyzer()

        phases = [
            Phase(name="a", agent="calcifer", task_template="Task A"),
            Phase(name="b", agent="calcifer", task_template="Task B", dependencies=["a"]),
            Phase(name="c", agent="calcifer", task_template="Task C", dependencies=["a", "b"]),
        ]

        graph = analyzer.analyze(phases)

        assert "a" in graph.get_dependencies("b")
        assert "a" in graph.get_dependencies("c")
        assert "b" in graph.get_dependencies("c")

    def test_parallelization_suggestions(self):
        """测试并行化建议"""
        analyzer = TaskDependencyAnalyzer()

        # 完全并行的 phases
        phases = [
            Phase(name="a", agent="calcifer", task_template="Task A"),
            Phase(name="b", agent="calcifer", task_template="Task B"),
            Phase(name="c", agent="calcifer", task_template="Task C"),
        ]

        graph = analyzer.analyze(phases)
        suggestions = analyzer.suggest_parallelization(graph, min_parallel_ratio=0.4)

        assert suggestions["parallel_ratio"] == 1.0  # 全部可以并行
        assert len(suggestions["parallel_groups"]) == 1
        assert len(suggestions["parallel_groups"][0]) == 3

    def test_file_pattern_extraction(self):
        """测试文件模式提取"""
        analyzer = TaskDependencyAnalyzer()

        # 测试读取模式
        read_pattern = analyzer._extract_file_pattern(
            "Read and analyze src/main.py to understand the code"
        )
        assert "src/main.py" in read_pattern.reads

        # 测试写入模式
        write_pattern = analyzer._extract_file_pattern(
            "Create tests/test_main.py with test cases"
        )
        assert "tests/test_main.py" in write_pattern.writes


class TestWorkflowIntegration:
    """测试 Workflow 集成"""

    def test_workflow_creation(self):
        """测试 Workflow 创建"""
        phases = [
            Phase(name="explore", agent="nekobasu", task_template="Explore {task}"),
            Phase(name="implement", agent="calcifer", task_template="Implement {task}"),
        ]

        workflow = Workflow(
            name="test_workflow",
            description="Test workflow",
            phases=phases,
        )

        assert workflow.name == "test_workflow"
        assert len(workflow.phases) == 2

    def test_phase_with_dependencies(self):
        """测试带依赖的 Phase"""
        phase = Phase(
            name="review",
            agent="enma",
            task_template="Review {task}",
            dependencies=["implement"],
        )

        assert phase.dependencies == ["implement"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
