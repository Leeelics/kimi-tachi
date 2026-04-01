"""
Task Dependency Analyzer

分析 Workflow Phase 之间的依赖关系，支持：
1. 基于文件输入输出的依赖分析
2. 基于语义的任务描述分析
3. 基于历史执行记录的分析
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


@dataclass
class DependencyEdge:
    """依赖边"""

    from_phase: str
    to_phase: str
    reason: str  # 依赖原因: "file", "semantic", "explicit"
    strength: float = 1.0  # 依赖强度 0-1


@dataclass
class DependencyGraph:
    """依赖关系图"""

    phases: list[str] = field(default_factory=list)
    edges: list[DependencyEdge] = field(default_factory=list)

    # 邻接表表示
    dependencies: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    dependents: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))

    def add_edge(self, edge: DependencyEdge) -> None:
        """添加依赖边"""
        self.edges.append(edge)
        self.dependencies[edge.to_phase].append(edge.from_phase)
        self.dependents[edge.from_phase].append(edge.to_phase)

    def get_dependencies(self, phase: str) -> list[str]:
        """获取 phase 的所有依赖"""
        return self.dependencies.get(phase, [])

    def get_dependents(self, phase: str) -> list[str]:
        """获取依赖于 phase 的所有 phases"""
        return self.dependents.get(phase, [])

    def has_dependency(self, from_phase: str, to_phase: str) -> bool:
        """检查 from_phase 是否依赖 to_phase"""
        return to_phase in self.dependencies.get(from_phase, [])

    def topological_sort(self) -> list[str]:
        """拓扑排序，返回执行顺序"""
        visited = set()
        temp_mark = set()
        result = []

        def visit(phase: str) -> None:
            if phase in temp_mark:
                raise ValueError(f"Circular dependency detected involving {phase}")
            if phase in visited:
                return

            temp_mark.add(phase)
            for dep in self.dependencies.get(phase, []):
                visit(dep)
            temp_mark.remove(phase)
            visited.add(phase)
            result.append(phase)

        for phase in self.phases:
            if phase not in visited:
                visit(phase)

        return result

    def find_parallel_groups(self) -> list[list[str]]:
        """
        找出可以并行执行的 phase 组

        Returns:
            每组内的 phases 可以并行执行，组间有依赖关系
        """
        # 计算每个 phase 的层级（最长依赖链长度）
        levels: dict[str, int] = {}

        def get_level(phase: str) -> int:
            if phase in levels:
                return levels[phase]

            deps = self.dependencies.get(phase, [])
            if not deps:
                levels[phase] = 0
            else:
                levels[phase] = max(get_level(dep) for dep in deps) + 1
            return levels[phase]

        for phase in self.phases:
            get_level(phase)

        # 按层级分组
        groups: dict[int, list[str]] = defaultdict(list)
        for phase, level in levels.items():
            groups[level].append(phase)

        # 按层级排序返回
        return [groups[i] for i in sorted(groups.keys())]


@dataclass
class FileAccessPattern:
    """文件访问模式"""

    reads: set[str] = field(default_factory=set)
    writes: set[str] = field(default_factory=set)


class TaskDependencyAnalyzer:
    """
    任务依赖分析器

    分析 phase 之间的依赖关系，支持多种分析策略
    """

    # 语义关键词映射
    SEMANTIC_PATTERNS = {
        "planning": ["plan", "design", "architecture", "structure"],
        "exploration": ["explore", "analyze", "investigate", "research", "survey"],
        "implementation": ["implement", "code", "write", "create", "build", "develop"],
        "review": ["review", "check", "verify", "validate", "audit"],
        "documentation": ["document", "readme", "comment", "explain"],
    }

    # 隐式依赖规则
    IMPLICIT_DEPENDENCIES = [
        ("implementation", "planning"),  # 实现依赖规划
        ("implementation", "exploration"),  # 实现依赖探索
        ("review", "implementation"),  # 审查依赖实现
        ("documentation", "implementation"),  # 文档依赖实现
    ]

    def __init__(self) -> None:
        self.file_patterns: dict[str, FileAccessPattern] = {}
        self.semantic_cache: dict[str, str] = {}  # phase name -> category

    def analyze(
        self,
        phases: list[Any],  # Phase
        explicit_dependencies: dict[str, list[str]] | None = None,
    ) -> DependencyGraph:
        """
        综合分析 phases 的依赖关系

        Args:
            phases: Workflow phases
            explicit_dependencies: 显式指定的依赖关系 {phase_name: [dep_names]}

        Returns:
            依赖关系图
        """
        graph = DependencyGraph(phases=[p.name for p in phases])

        # 从 phases 提取显式依赖
        phase_deps: dict[str, list[str]] = {}
        for p in phases:
            if hasattr(p, "dependencies") and p.dependencies:
                phase_deps[p.name] = p.dependencies

        # 合并外部传入的依赖
        if explicit_dependencies:
            phase_deps.update(explicit_dependencies)

        # 1. 分析显式依赖
        if phase_deps:
            for phase_name, deps in phase_deps.items():
                for dep in deps:
                    graph.add_edge(
                        DependencyEdge(
                            from_phase=dep,
                            to_phase=phase_name,
                            reason="explicit",
                            strength=1.0,
                        )
                    )

        # 2. 分析基于 task_template 的语义依赖
        for phase in phases:
            category = self._categorize_semantically(phase.task_template)
            self.semantic_cache[phase.name] = category

        # 应用隐式依赖规则
        for phase_name, category in self.semantic_cache.items():
            for impl_cat, dep_cat in self.IMPLICIT_DEPENDENCIES:
                if category == impl_cat:
                    # 找到同类别或之前的依赖
                    for other_name, other_cat in self.semantic_cache.items():
                        if (
                            other_name != phase_name
                            and other_cat == dep_cat
                            and not graph.has_dependency(phase_name, other_name)
                        ):
                            graph.add_edge(
                                DependencyEdge(
                                    from_phase=other_name,
                                    to_phase=phase_name,
                                    reason="semantic",
                                    strength=0.7,
                                )
                            )

        # 3. 分析 task_template 中的文件引用
        for phase in phases:
            pattern = self._extract_file_pattern(phase.task_template)
            self.file_patterns[phase.name] = pattern

        # 基于文件读写检测依赖
        for phase1 in phases:
            for phase2 in phases:
                if phase1.name == phase2.name:
                    continue

                pattern1 = self.file_patterns[phase1.name]
                pattern2 = self.file_patterns[phase2.name]

                # 如果 phase2 读取的文件被 phase1 写入
                common_files = pattern2.reads & pattern1.writes
                if common_files:
                    graph.add_edge(
                        DependencyEdge(
                            from_phase=phase1.name,
                            to_phase=phase2.name,
                            reason="file",
                            strength=0.9,
                        )
                    )

        return graph

    def _categorize_semantically(self, task_template: str) -> str:
        """
        基于语义对任务进行分类

        Returns:
            类别: planning, exploration, implementation, review, documentation, unknown
        """
        text = task_template.lower()

        scores: dict[str, int] = {}
        for category, keywords in self.SEMANTIC_PATTERNS.items():
            score = sum(1 for keyword in keywords if keyword in text)
            if score > 0:
                scores[category] = score

        if not scores:
            return "unknown"

        return max(scores, key=scores.get)

    def _extract_file_pattern(self, task_template: str) -> FileAccessPattern:
        """
        从任务模板中提取文件访问模式

        检测:
        - 读取: "read", "analyze", "explore", "check"
        - 写入: "write", "create", "modify", "update", "implement"
        """
        pattern = FileAccessPattern()

        # 文件路径模式
        file_patterns = [
            r"[\w\-./]+\.py",
            r"[\w\-./]+\.md",
            r"[\w\-./]+\.yaml",
            r"[\w\-./]+\.json",
            r"[\w\-./]+\.toml",
        ]

        # 读取关键词
        read_keywords = [
            "read",
            "analyze",
            "explore",
            "check",
            "investigate",
            "survey",
            "understand",
            "review",
            "examine",
        ]

        # 写入关键词
        write_keywords = [
            "write",
            "create",
            "modify",
            "update",
            "implement",
            "build",
            "develop",
            "change",
            "edit",
            "add",
        ]

        text = task_template.lower()

        # 检测文件引用
        for fp in file_patterns:
            matches = re.findall(fp, text)

            # 根据上下文判断是读还是写
            for match in matches:
                # 获取匹配位置周围的上下文
                idx = text.find(match)
                context = text[max(0, idx - 50) : min(len(text), idx + 50)]

                # 判断操作类型（优先检查写入，因为写入更具体）
                is_read = any(kw in context for kw in read_keywords)
                is_write = any(kw in context for kw in write_keywords)

                # 如果同时有读写关键词，根据距离判断
                if is_read and is_write:
                    # 计算关键词到文件路径的距离
                    read_dist = min(
                        abs(context.find(kw) - 50) for kw in read_keywords if kw in context
                    )
                    write_dist = min(
                        abs(context.find(kw) - 50) for kw in write_keywords if kw in context
                    )
                    if write_dist < read_dist:
                        pattern.writes.add(match)
                    else:
                        pattern.reads.add(match)
                elif is_write:
                    pattern.writes.add(match)
                else:
                    pattern.reads.add(match)

        return pattern

    def suggest_parallelization(
        self,
        graph: DependencyGraph,
        min_parallel_ratio: float = 0.4,
    ) -> dict[str, Any]:
        """
        建议并行化方案

        Returns:
            {
                "parallel_groups": [[phase1, phase2], [phase3]],
                "parallel_ratio": 0.5,
                "estimated_time_reduction": "30%",
                "recommendations": ["..."],
            }
        """
        groups = graph.find_parallel_groups()

        # 计算并行比例
        total_phases = len(graph.phases)
        parallel_phases = sum(len(g) for g in groups if len(g) > 1)
        parallel_ratio = parallel_phases / total_phases if total_phases > 0 else 0

        # 生成建议
        recommendations: list[str] = []

        if parallel_ratio < min_parallel_ratio:
            recommendations.append(
                f"Current parallel ratio ({parallel_ratio:.1%}) is below target "
                f"({min_parallel_ratio:.1%})"
            )

            # 找出可以解耦的依赖
            for edge in graph.edges:
                if edge.strength < 0.8 and edge.reason == "semantic":
                    recommendations.append(
                        f"Consider removing weak dependency: {edge.from_phase} -> {edge.to_phase} "
                        f"(strength: {edge.strength:.2f})"
                    )

        # 估算时间节省（简化模型）
        # 假设每个 phase 平均耗时相同
        sequential_time = total_phases
        parallel_time = len(groups)
        time_reduction = (sequential_time - parallel_time) / sequential_time

        return {
            "parallel_groups": groups,
            "parallel_ratio": parallel_ratio,
            "estimated_time_reduction": f"{time_reduction:.1%}",
            "recommendations": recommendations,
        }
