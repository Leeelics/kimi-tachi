# kimi-tachi v0.5.0 对 MemNexus 的需求清单

> 版本: v0.5.0-alpha  
> 日期: 2026-03-26  
> 优先级: P0 (阻塞), P1 (重要), P2 (优化)

---

## 需求概览

```
kimi-tachi v0.5.0 记忆架构
├── 项目级记忆 (MemNexus 现有) - 代码、Git、会话
├── 全局记忆层 (需要新增) - 跨项目知识、用户偏好
└── 实时索引层 (需要新增) - 文件监听、hooks 触发
```

---

## 🔴 P0: 跨项目全局记忆层

### 背景
kimi-tachi 的七人衆需要在不同项目间共享知识：
- "我在项目 A 用过这个模式，项目 B 也可以用"
- "用户的编码偏好在所有项目保持一致"
- "常见的架构决策可以复用"

### 需求详情

#### 1. 全局记忆存储

```python
# 新的 GlobalMemory 类
from memnexus import GlobalMemory

global_mem = await GlobalMemory.init()

# 存储跨项目知识
await global_mem.store(
    content="用户偏好使用 Pydantic 做数据验证",
    category="user_preference",
    tags=["python", "validation", "pattern"],
    scope="user",  # user | project | session
)

# 存储可复用的架构模式
await global_mem.store(
    content="JWT + Redis 的认证架构",
    category="architecture_pattern",
    tags=["auth", "jwt", "redis"],
    scope="user",
    related_projects=["project-a", "project-b"],  # 在哪些项目用过
)
```

#### 2. 全局搜索 API

```python
# 跨项目搜索
results = await global_mem.search(
    query="JWT 实现",
    filters={
        "category": "architecture_pattern",
        "tags": ["auth"],
        "used_in_projects": ["current-project-id"],  # 在当前项目用过的
    },
    limit=10,
)

# 获取用户的常用模式
patterns = await global_mem.get_user_patterns(
    category="code_style",
    limit=20,
)
```

#### 3. 数据结构建议

```python
@dataclass
class GlobalMemoryEntry:
    id: str
    content: str
    category: str  # user_preference | architecture_pattern | code_style | common_solution
    tags: List[str]
    scope: str  # user | project | session
    source_project: Optional[str]  # 来源项目
    related_projects: List[str]  # 相关项目
    usage_count: int  # 使用次数
    last_used: datetime
    created_at: datetime
    metadata: Dict[str, Any]
```

#### 4. 存储位置

```
~/.memnexus/
├── global/                    # 新增：全局记忆
│   ├── global_memory.db       # SQLite 或 LanceDB
│   └── index/                 # 向量索引
└── projects/                  # 现有：项目级记忆
    ├── project-a/
    └── project-b/
```

---

## 🔴 P0: 实时索引与 kimi-cli Hooks 集成

### 背景
kimi-cli 正在开发 hooks 系统，kimi-tachi 需要：
1. 监听文件变更，实时更新索引
2. 通过 hooks 主动触发记忆操作
3. 会话生命周期管理（开始、暂停、结束）

### 需求详情

#### 1. 文件系统监听 (File Watcher)

```python
from memnexus import FileWatcher

watcher = FileWatcher(
    project_path=".",
    on_change=handle_file_change,  # 回调函数
    ignore_patterns=[".git", "__pycache__", "*.pyc"],
)

async def handle_file_change(event):
    """文件变更回调"""
    # event.type: created | modified | deleted | renamed
    # event.file_path: 文件路径
    # event.content: 新内容（如果是文本文件）
    
    # 自动更新索引
    await memory.index_file(event.file_path)
    
    # 通知 kimi-tachi
    await tachi.notify_file_changed(event)

# 启动监听
await watcher.start()
```

#### 2. kimi-cli Hooks 支持

```python
# memnexus/hooks/kimi_hooks.py

class KimiHooks:
    """kimi-cli hooks 集成"""
    
    async def on_session_start(self, session_info: dict):
        """会话开始时触发"""
        # 恢复会话记忆
        context = await memory.recall_session(
            session_id=session_info["id"],
            project_path=session_info["work_dir"],
        )
        
        # 提供给 kimi-tachi
        return {
            "recalled_memories": context.recent_memories,
            "project_summary": context.project_summary,
            "user_preferences": context.user_preferences,
        }
    
    async def on_session_end(self, session_info: dict, summary: dict):
        """会话结束时触发"""
        # 保存会话记忆
        await memory.store_session(
            session_id=session_info["id"],
            summary=summary["conversation_summary"],
            decisions=summary["key_decisions"],
            code_changes=summary["files_changed"],
        )
        
        # 提取全局知识
        if summary["is_significant"]:
            await global_mem.extract_and_store(
                session_summary=summary,
                category="architecture_pattern",
            )
    
    async def on_tool_call(self, tool_name: str, result: dict):
        """工具调用后触发"""
        # 存储重要的工具调用结果
        if tool_name in ["WriteFile", "StrReplaceFile"]:
            await memory.store_file_change(
                file_path=result["file_path"],
                change_type="modified",
                content=result.get("content"),
            )
    
    async def on_agent_switch(self, from_agent: str, to_agent: str, context: dict):
        """切换 Agent 时触发"""
        # 保存当前 Agent 的上下文
        await memory.store_agent_context(
            agent=from_agent,
            context=context,
        )
        
        # 恢复目标 Agent 的上下文
        recalled = await memory.recall_agent_context(
            agent=to_agent,
        )
        
        return recalled
```

#### 3. Hook 配置文件

```json
// .kimi/hooks/memnexus-hooks.json
{
  "hooks": {
    "session_start": "memnexus.hooks.kimi_hooks:on_session_start",
    "session_end": "memnexus.hooks.kimi_hooks:on_session_end",
    "tool_call": "memnexus.hooks.kimi_hooks:on_tool_call",
    "agent_switch": "memnexus.hooks.kimi_hooks:on_agent_switch"
  },
  "config": {
    "auto_index": true,
    "auto_store_decisions": true,
    "cross_project_recall": true
  }
}
```

---

## 🟡 P1: 七人衆个性化记忆

### 背景
每个 Agent 应该有自己独特的"记忆性格"

### 需求

```python
# Agent 类型的记忆偏好配置
AGENT_MEMORY_PROFILES = {
    "kamaji": {
        "remember": ["user_preferences", "architecture_decisions", "project_goals"],
        "recall_on_start": ["last_session_summary", "pending_tasks"],
        "store_on_end": ["session_summary", "key_decisions"],
    },
    "nekobasu": {
        "remember": ["code_structure", "file_relationships", "explored_paths"],
        "recall_on_start": ["code_map", "recent_changes"],
        "store_on_end": ["exploration_results", "new_findings"],
    },
    "calcifer": {
        "remember": ["implementation_patterns", "testing_strategies", "common_bugs"],
        "recall_on_start": ["similar_implementations", "project_patterns"],
        "store_on_end": ["code_changes", "implementation_notes"],
    },
    # ... 其他角色
}
```

---

## 🟡 P1: 记忆置信度和衰减

### 背景
旧记忆应该逐渐淡化，常用记忆应该强化

### 需求

```python
@dataclass
class MemoryRelevance:
    """记忆的相关性评分"""
    score: float  # 0-1
    factors: {
        "recency": float,      # 越近越高
        "frequency": float,    # 使用越频繁越高
        "similarity": float,   # 与当前查询越像越高
        "success_rate": float, # 成功率越高越高
    }

# 搜索时按相关性排序
results = await memory.search(
    query="authentication",
    sort_by="relevance",  # 综合评分
    min_score=0.5,        # 过滤低质量记忆
)

# 记忆衰减（可选）
await memory.apply_decay(
    half_life_days=30,  # 30天后相关性减半
)
```

---

## 🟢 P2: 记忆可视化（可选）

### 需求
```python
# 生成记忆图谱
await memory.visualize(
    output_path="memory-graph.html",
    include_global=True,
    include_projects=["current"],
)

# 记忆统计报告
report = await memory.generate_report(
    project_id="my-project",
    time_range="30d",
)
```

---

## 📅 实施建议

### Phase 1: 基础集成 (Week 1-2)
- [ ] kimi-tachi 使用现有 MemNexus 功能
- [ ] 封装 TachiMemory 适配层
- [ ] 测试基础场景

### Phase 2: 全局记忆 (Week 3-4)
- [ ] MemNexus 实现 GlobalMemory
- [ ] kimi-tachi 集成全局记忆
- [ ] 测试跨项目场景

### Phase 3: Hooks 集成 (Week 5-6)
- [ ] MemNexus 实现 FileWatcher
- [ ] MemNexus 实现 KimiHooks
- [ ] kimi-cli hooks 发布后进行集成测试

### Phase 4: 优化迭代 (Week 7-8)
- [ ] 七人衆个性化记忆
- [ ] 记忆置信度和衰减
- [ ] 性能优化

---

## 🤝 协作方式

1. **Issue 驱动**: 每个需求在 MemNexus  repo 提一个 Issue
2. **优先级标记**: 标记 `kimi-tachi-p0`, `kimi-tachi-p1`
3. **每周同步**: 周五同步进度，调整优先级
4. **联合测试**: 功能完成后在 kimi-tachi 测试验证

---

## ❓ 需要确认的问题

1. **全局记忆存储**: SQLite 够吗？还是需要 LanceDB 向量存储？
2. **文件监听**: 用 watchdog (Python) 还是 native 实现？
3. **Hooks 协议**: kimi-cli hooks 是什么格式？需要提前了解
4. **隐私**: 全局记忆是否涉及敏感信息？需要加密吗？

---

**准备好后，我可以帮你在 MemNexus repo 提这些 Issue。**
