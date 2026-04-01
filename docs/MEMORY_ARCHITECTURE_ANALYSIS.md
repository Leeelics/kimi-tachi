# kimi-tachi 记忆系统架构分析

> 关于主动探查 vs 被动提取的深度讨论

## 当前记忆系统架构

### 1. 存储层 (Storage Layer)

```
┌─────────────────────────────────────────────────────────────┐
│                     存储架构 (v0.5.2)                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ~/.kimi-tachi/memory/                                      │
│  ├── hooks/                                                 │
│  │   ├── session_<id>.json    # 活跃会话 (JSON 文件)         │
│  │   ├── history/             # 归档会话                     │
│  │   │   └── session_YYYYMMDD_<id>.json                     │
│  │   └── *.log                # 操作日志                     │
│  │                                                          │
│  ├── code/                    # MemNexus 代码记忆           │
│  │   ├── index.db             # 向量索引 (如果存在)          │
│  │   └── storage/             # 原始存储                    │
│  │                                                          │
│  └── global/                  # MemNexus 全局记忆           │
│      └── ...                                                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2. Session 数据格式

```json
{
  "session_id": "abc123",
  "started_at": "2026-04-01T10:00:00",
  "ended_at": "2026-04-01T14:30:00",
  "source": "startup",
  "cwd": "/path/to/project",
  "decisions": [
    {
      "type": "decision",
      "content": "Use JWT authentication",
      "timestamp": "2026-04-01T10:30:00",
      "session_id": "abc123"  // <-- 需要添加，用于追踪来源
    }
  ],
  "events": [...],
  "compactions": [...],
  "summary": "...",
  "end_reason": "user_exit"
}
```

### 3. 当前的 Recall 机制

```python
# 当前实现 (被动式)
async def recall_agent_context(agent_type: str, task: str = ""):
    # 1. 只搜索 MemNexus (代码记忆)
    recent = await self.memory.store.search(query=task, limit=10)
    
    # 2. 只恢复当前 session 的 hooks 数据
    session_data = load_session_data(current_session_id)
    
    # 问题：无法发现其他 session 的相关信息！
```

## 核心问题识别

### 问题 1: 无法主动探查历史 Session

**现状：**
- SessionStart hook 只加载 **同一个 session_id** 的历史
- 如果用户开启新会话，无法自动发现之前会话的相关决策

**示例场景：**
```
Session 1 (昨天):
  - 决策："Use PostgreSQL for user data"
  - 决策："Implement JWT auth"

Session 2 (今天，新会话):
  - 用户："Add user profile feature"
  - 系统：❌ 不知道昨天的数据库决策！
  - 结果：可能重复讨论技术选型
```

### 问题 2: 缺乏去重机制

**现状：**
- 没有 "已探查 session" 的追踪
- 没有 "已回忆决策" 的标记
- 可能导致同一决策被多次加载

### 问题 3: 存储方式割裂

| 数据类型 | 存储方式 | 索引方式 | 问题 |
|---------|---------|---------|------|
| Session 数据 | JSON 文件 | 无索引 | 无法全文搜索 |
| 代码记忆 | MemNexus | 向量索引 | 与 Session 数据割裂 |
| 全局记忆 | MemNexus | 项目索引 | 更新延迟 |

## 方案对比：主动探查 vs 被动提取

### 方案 A: 主动探查 (Proactive Exploration)

```
概念：系统主动扫描所有历史 session，找出相关信息

触发时机：
- SessionStart 时
- 用户输入新任务时
- 上下文切换时

实现方式：
1. 遍历所有历史 session 文件
2. 基于语义相似度筛选相关 session
3. 提取关键决策和模式
4. 合并到当前上下文
```

**优点：**
- ✅ 发现跨会话的隐性关联
- ✅ 不依赖用户触发记忆工具
- ✅ 可以建立长期知识图谱

**缺点：**
- ❌ 性能开销大（需要扫描所有文件）
- ❌ 可能加载过多无关信息
- ❌ 需要复杂的去重和相关性判断

### 方案 B: 被动提取 (Passive Retrieval)

```
概念：只在需要时，根据明确信号提取信息

触发时机：
- 用户显式调用 memory_search
- Agent 工具调用时记录
- 特定关键词触发

实现方式：
1. 维护一个统一的索引
2. 根据查询实时搜索
3. 只返回最相关的结果
```

**优点：**
- ✅ 性能可控
- ✅ 相关性高
- ✅ 实现简单

**缺点：**
- ❌ 可能遗漏重要上下文
- ❌ 依赖用户或 Agent 主动查询
- ❌ 无法建立全局知识图谱

### 方案 C: 混合策略 (推荐) ⭐

```
概念：被动为主 + 主动为辅

层级设计：
┌─────────────────────────────────────────┐
│  Layer 3: 主动背景知识 (低频更新)         │
│  - 项目架构模式                          │
│  - 技术栈决策                            │
│  - 更新频率：每次索引时                   │
├─────────────────────────────────────────┤
│  Layer 2: 被动语义搜索 (按需查询)         │
│  - 代码记忆                              │
│  - 历史决策                              │
│  - 触发：关键词匹配                      │
├─────────────────────────────────────────┤
│  Layer 1: 当前会话上下文 (实时)           │
│  - 当前 session 的 decisions/events      │
│  - Hook 自动维护                         │
└─────────────────────────────────────────┘
```

## 推荐实现方案

### 1. 统一索引层

```python
class SessionIndex:
    """
    统一的 Session 索引
    
    解决 JSON 文件无法全文搜索的问题
    """
    def __init__(self, storage_path: Path):
        self.index_path = storage_path / "session_index.db"
        # 使用 SQLite + FTS5 或向量数据库
        
    async def index_session(self, session_data: dict):
        """索引一个 session 到统一索引"""
        # 提取可搜索字段
        searchable_content = {
            "session_id": session_data["session_id"],
            "cwd": session_data.get("cwd", ""),
            "decisions": [d["content"] for d in session_data.get("decisions", [])],
            "summary": session_data.get("summary", ""),
            "timestamp": session_data.get("started_at"),
        }
        # 存入索引
        
    async def search_relevant_sessions(
        self, 
        query: str, 
        current_session: str,
        limit: int = 5
    ) -> list[dict]:
        """搜索相关 session（排除当前）"""
        # 返回相关 session_id 列表
```

### 2. 智能 Recall 机制

```python
class SmartRecallManager:
    """
    智能回忆管理器
    
    实现 "探查一次，标记已读" 的机制
    """
    def __init__(self):
        # 已探查的 session 集合
        self._explored_sessions: set[str] = set()
        # 已加载的决策指纹（用于去重）
        self._loaded_decision_hashes: set[str] = set()
        
    async def recall_for_task(
        self, 
        task: str,
        current_session_id: str
    ) -> dict:
        """
        为当前任务智能回忆
        
        策略：
        1. 首先搜索统一索引，找到相关 session
        2. 排除已探查的 session
        3. 提取新决策（去重）
        4. 标记为已探查
        """
        # 1. 搜索相关 session
        relevant = await session_index.search_relevant_sessions(
            query=task,
            current_session=current_session_id,
            limit=5
        )
        
        new_contexts = []
        for session in relevant:
            if session["session_id"] in self._explored_sessions:
                continue
                
            # 提取新决策
            for decision in session.get("decisions", []):
                decision_hash = hash(decision["content"])
                if decision_hash not in self._loaded_decision_hashes:
                    new_contexts.append(decision)
                    self._loaded_decision_hashes.add(decision_hash)
            
            # 标记为已探查
            self._explored_sessions.add(session["session_id"])
        
        return {
            "new_decisions": new_contexts,
            "explored_sessions": list(self._explored_sessions),
        }
```

### 3. 增量索引策略

```python
class IncrementalSessionIndexer:
    """
    增量 Session 索引器
    
    避免重复扫描所有文件
    """
    def __init__(self):
        self._last_index_time: datetime = None
        self._indexed_sessions: set[str] = set()
        
    async def index_new_sessions(self):
        """只索引新创建或修改的 session"""
        history_dir = Path("~/.kimi-tachi/memory/hooks/history")
        
        for session_file in history_dir.glob("session_*.json"):
            mtime = session_file.stat().st_mtime
            session_id = session_file.stem
            
            # 只处理新的或修改过的
            if session_id not in self._indexed_sessions:
                data = json.loads(session_file.read_text())
                await session_index.index_session(data)
                self._indexed_sessions.add(session_id)
```

## 实施路线图

### Phase 1: 去重和追踪 (v0.5.3)

- [ ] 为决策添加唯一指纹（hash）
- [ ] 添加 "已探查 session" 追踪
- [ ] Session 数据添加相关性标签

### Phase 2: 统一索引 (v0.6.0)

- [ ] 实现 SQLite + FTS5 索引
- [ ] 增量索引机制
- [ ] 跨 session 搜索 API

### Phase 3: 智能 Recall (v0.6.5)

- [ ] 实现 SmartRecallManager
- [ ] 语义相似度匹配
- [ ] 自动相关性评分

### Phase 4: 知识图谱 (v0.7.0)

- [ ] 决策依赖图
- [ ] 项目架构知识图谱
- [ ] 长期模式学习

## 当前建议

### 立即可做的改进

1. **添加决策指纹去重**
```python
def get_decision_fingerprint(decision: dict) -> str:
    """生成决策指纹用于去重"""
    content = decision.get("content", "").lower().strip()
    # 归一化：去除标点、保留关键词
    import re
    keywords = re.findall(r'\b\w+\b', content)
    return hashlib.md5(" ".join(sorted(keywords)).encode()).hexdigest()[:16]
```

2. **标记已探查 Session**
```python
# 在 session 数据中标记
{
  "session_id": "abc123",
  "explored_by": ["session_xyz789"],  # 被哪些 session 探查过
  "explored_at": "2026-04-01T15:00:00"
}
```

3. **相关性评分**
```python
def calculate_relevance(session_data: dict, query: str) -> float:
    """计算 session 与查询的相关性"""
    score = 0.0
    
    # 决策内容匹配
    for decision in session_data.get("decisions", []):
        if any(word in decision["content"].lower() for word in query.lower().split()):
            score += 1.0
    
    # 时间衰减（越新的越相关）
    age_hours = (now - parse_time(session_data["started_at"])).hours
    time_decay = 1.0 / (1.0 + age_hours / 24)  # 24小时后衰减一半
    
    return score * time_decay
```

## 总结

**当前状态：**
- ✅ 有基础的记忆存储（Hooks + MemNexus）
- ⚠️ Session 数据孤立，无法跨会话搜索
- ❌ 没有去重机制
- ❌ 缺乏统一索引

**建议方向：**
1. **短期**：在现有架构上添加去重和追踪
2. **中期**：建立统一索引，实现被动搜索
3. **长期**：混合策略，智能主动探查

**关键决策点：**
- 是否值得引入额外的数据库（SQLite/向量库）来统一索引？
- 主动探查的性能开销是否可接受？
- 如何平衡相关性和信息过载？

---

*这是一个需要仔细权衡的架构决策。*
