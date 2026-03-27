"""
Agent Memory Profiles - Seven Samurai (七人衆)

Defines memory preferences and behaviors for each agent type.

This allows each character to have unique "memory personality":
- Kamaji remembers user preferences and architecture decisions
- Nekobasu caches code structure to avoid re-exploring
- Phoenix maintains knowledge base of patterns
- etc.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class MemoryProfile:
    """Memory profile for an agent."""
    
    # What to remember
    remember_categories: List[str] = field(default_factory=list)
    
    # When to recall
    recall_on_start: List[str] = field(default_factory=list)
    recall_triggers: List[str] = field(default_factory=list)
    
    # When to store
    store_on_end: List[str] = field(default_factory=list)
    store_triggers: List[str] = field(default_factory=list)
    
    # Search preferences
    search_queries: List[str] = field(default_factory=list)
    search_limit: int = 5
    
    # Description for the agent
    memory_description: str = ""


# Seven Samurai Memory Profiles
AGENT_MEMORY_PROFILES = {
    "kamaji": MemoryProfile(
        remember_categories=[
            "user_preferences",      # 用户偏好
            "architecture_decisions", # 架构决策
            "project_goals",         # 项目目标
            "team_conventions",      # 团队约定
        ],
        recall_on_start=[
            "last_session_summary",  # 上次会话总结
            "pending_tasks",         # 待办任务
            "user_preferences",      # 用户偏好
        ],
        recall_triggers=[
            "new_project",           # 新项目时
            "architecture_question", # 架构问题时
        ],
        store_on_end=[
            "session_summary",       # 会话总结
            "key_decisions",         # 关键决策
            "architecture_changes",  # 架构变更
        ],
        store_triggers=[
            "user_preference_stated", # 用户明确表达偏好
            "architecture_decision",  # 做出架构决策
        ],
        search_queries=[
            "architecture",
            "design decision",
            "project structure",
        ],
        search_limit=10,
        memory_description="""
        Kamaji (釜爺) - The Coordinator's Memory
        
        As the boiler room chief, I remember:
        - User's coding preferences and style
        - Architecture decisions and their rationale
        - Project goals and constraints
        - Team conventions and standards
        
        When starting a task, I recall:
        - What we were working on last time
        - Any pending tasks or open questions
        - User's specific requirements
        
        I store at the end of each session:
        - Summary of what was accomplished
        - Key decisions made and why
        - Any architecture changes
        """,
    ),
    
    "nekobasu": MemoryProfile(
        remember_categories=[
            "code_structure",        # 代码结构
            "file_relationships",    # 文件关系
            "explored_paths",        # 已探索路径
            "common_patterns",       # 常见模式
        ],
        recall_on_start=[
            "code_map",              # 代码地图
            "recent_changes",        # 最近变更
            "explored_directories",  # 已探索目录
        ],
        recall_triggers=[
            "explore_task",          # 探索任务时
            "find_code",             # 查找代码时
        ],
        store_on_end=[
            "exploration_results",   # 探索结果
            "new_findings",          # 新发现
            "code_structure_update", # 代码结构更新
        ],
        store_triggers=[
            "new_file_discovered",   # 发现新文件
            "pattern_identified",    # 识别模式
        ],
        search_queries=[
            "file structure",
            "module organization",
            "import relationships",
        ],
        search_limit=8,
        memory_description="""
        Nekobasu (猫バス) - The Explorer's Memory
        
        As the cat bus with twelve legs, I remember:
        - Code structure and organization
        - Which files are related to each other
        - Paths I've already explored (to avoid repetition)
        - Common patterns in the codebase
        
        When starting an exploration:
        - I recall the current code map
        - Recent changes that might affect exploration
        - Directories I've already explored
        
        I store after exploration:
        - What I found (file structure, relationships)
        - New discoveries
        - Updated code structure information
        """,
    ),
    
    "calcifer": MemoryProfile(
        remember_categories=[
            "implementation_patterns",  # 实现模式
            "testing_strategies",       # 测试策略
            "common_bugs",              # 常见 bug
            "library_usage",            # 库使用
        ],
        recall_on_start=[
            "similar_implementations",  # 类似实现
            "project_patterns",         # 项目模式
            "library_conventions",      # 库约定
        ],
        recall_triggers=[
            "implementation_task",      # 实现任务时
            "bug_fix",                  # 修复 bug 时
        ],
        store_on_end=[
            "code_changes",             # 代码变更
            "implementation_notes",     # 实现笔记
            "testing_approach",         # 测试方法
        ],
        store_triggers=[
            "pattern_used",             # 使用模式时
            "bug_fixed",                # 修复 bug 时
        ],
        search_queries=[
            "implementation",
            "how to implement",
            "best practice",
        ],
        search_limit=6,
        memory_description="""
        Calcifer (カルシファー) - The Builder's Memory
        
        As the fire demon powering the castle, I remember:
        - Implementation patterns and best practices
        - Testing strategies that work
        - Common bugs and how to avoid them
        - How libraries are used in this project
        
        When starting to build:
        - I look for similar implementations
        - Project-specific patterns
        - Library conventions
        
        I store after building:
        - What I built and how
        - Implementation notes
        - Testing approach used
        """,
    ),
    
    "enma": MemoryProfile(
        remember_categories=[
            "code_quality_issues",      # 代码质量问题
            "review_patterns",          # 审查模式
            "standards_violations",     # 规范违反
            "security_concerns",        # 安全问题
        ],
        recall_on_start=[
            "common_issues",            # 常见问题
            "project_standards",        # 项目规范
            "past_reviews",             # 过往审查
        ],
        recall_triggers=[
            "review_task",              # 审查任务时
            "quality_check",            # 质量检查时
        ],
        store_on_end=[
            "review_results",           # 审查结果
            "issues_found",             # 发现的问题
            "recommendations",          # 建议
        ],
        store_triggers=[
            "issue_identified",         # 识别问题时
            "standard_violated",        # 违反规范时
        ],
        search_queries=[
            "code quality",
            "security",
            "best practices",
        ],
        search_limit=5,
        memory_description="""
        Enma (閻魔大王) - The Reviewer's Memory
        
        As the strict judge of code quality, I remember:
        - Code quality issues found in the past
        - Common review patterns
        - Standards violations
        - Security concerns
        
        When starting a review:
        - Common issues in this codebase
        - Project standards
        - Past reviews of similar code
        
        I store after reviewing:
        - What I found
        - Issues identified
        - Recommendations made
        """,
    ),
    
    "tasogare": MemoryProfile(
        remember_categories=[
            "research_findings",        # 研究结果
            "solution_approaches",      # 解决方案
            "trade_off_analysis",       # 权衡分析
            "planning_history",         # 规划历史
        ],
        recall_on_start=[
            "similar_tasks",            # 类似任务
            "past_approaches",          # 过往方法
            "research_context",         # 研究背景
        ],
        recall_triggers=[
            "planning_task",            # 规划任务时
            "research_needed",          # 需要研究时
        ],
        store_on_end=[
            "planning_results",         # 规划结果
            "research_summary",         # 研究总结
            "approach_chosen",          # 选择的方法
        ],
        store_triggers=[
            "decision_made",            # 做出决策时
            "research_completed",       # 研究完成时
        ],
        search_queries=[
            "solution",
            "approach",
            "comparison",
        ],
        search_limit=7,
        memory_description="""
        Tasogare (黄昏時) - The Planner's Memory
        
        As the twilight hour connecting problem and solution, I remember:
        - Research findings
        - Different solution approaches
        - Trade-off analyses
        - Planning history
        
        When starting to plan:
        - Similar tasks from the past
        - Approaches that worked
        - Research context
        
        I store after planning:
        - The plan created
        - Research summary
        - Why certain approaches were chosen
        """,
    ),
    
    "shishigami": MemoryProfile(
        remember_categories=[
            "system_designs",           # 系统设计
            "technology_choices",       # 技术选型
            "scalability_patterns",     # 可扩展性模式
            "integration_patterns",     # 集成模式
        ],
        recall_on_start=[
            "current_architecture",     # 当前架构
            "design_principles",        # 设计原则
            "technology_stack",         # 技术栈
        ],
        recall_triggers=[
            "design_task",              # 设计任务时
            "architecture_review",      # 架构审查时
        ],
        store_on_end=[
            "design_decisions",         # 设计决策
            "architecture_updates",     # 架构更新
            "technology_rationale",     # 技术选型理由
        ],
        store_triggers=[
            "design_pattern_chosen",    # 选择设计模式时
            "technology_selected",      # 选择技术时
        ],
        search_queries=[
            "architecture",
            "design pattern",
            "system design",
        ],
        search_limit=8,
        memory_description="""
        Shishigami (シシ神) - The Architect's Memory
        
        As the forest deity of ancient wisdom, I remember:
        - System designs and their evolution
        - Technology choices and why they were made
        - Scalability patterns
        - Integration patterns
        
        When starting architectural work:
        - Current architecture
        - Design principles of the project
        - Technology stack
        
        I store after designing:
        - Design decisions made
        - Architecture updates
        - Rationale for technology choices
        """,
    ),
    
    "phoenix": MemoryProfile(
        remember_categories=[
            "knowledge_base",           # 知识库
            "documentation_patterns",   # 文档模式
            "common_questions",         # 常见问题
            "best_practices",           # 最佳实践
        ],
        recall_on_start=[
            "relevant_knowledge",       # 相关知识
            "documentation_context",    # 文档背景
            "similar_questions",        # 类似问题
        ],
        recall_triggers=[
            "documentation_task",       # 文档任务时
            "question_asked",           # 被问到问题时
        ],
        store_on_end=[
            "knowledge_added",          # 新增知识
            "documentation_updates",    # 文档更新
            "qa_pairs",                 # 问答对
        ],
        store_triggers=[
            "new_knowledge",            # 新知识时
            "question_answered",        # 回答问题时
        ],
        search_queries=[
            "documentation",
            "how to",
            "what is",
            "explain",
        ],
        search_limit=10,
        memory_description="""
        Phoenix (火の鳥) - The Librarian's Memory
        
        As the eternal observer across time, I remember:
        - Knowledge base of the project
        - Documentation patterns
        - Common questions and their answers
        - Best practices
        
        When starting documentation:
        - Relevant existing knowledge
        - Documentation context
        - Similar questions from the past
        
        I store after documenting:
        - New knowledge added
        - Documentation updates
        - Q&A pairs
        """,
    ),
}


def get_agent_profile(agent_type: str) -> MemoryProfile:
    """
    Get memory profile for an agent type.
    
    Args:
        agent_type: Agent type (kamaji, nekobasu, etc.)
        
    Returns:
        MemoryProfile for the agent
    """
    return AGENT_MEMORY_PROFILES.get(
        agent_type,
        MemoryProfile(remember_categories=["general"])  # Default
    )


def list_agent_profiles() -> Dict[str, str]:
    """List all available agent profiles with descriptions."""
    return {
        name: profile.memory_description.split('\n')[0].strip()
        for name, profile in AGENT_MEMORY_PROFILES.items()
    }
