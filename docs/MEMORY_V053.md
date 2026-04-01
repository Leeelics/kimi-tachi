# kimi-tachi Memory v0.5.3 - 智能 Session 探查

> 主动探查与去重机制

## 概述

v0.5.3 引入了 **智能 Session 探查** 功能，解决了之前版本无法发现跨 Session 关联决策的问题。

### 问题背景

在 v0.5.2 中：
- SessionStart 只加载 **同一个 session** 的历史
- 无法自动发现 **其他 session** 的相关决策
- 没有机制防止重复存储相同决策

**场景示例：**
```
昨天 Session A:
  - 决策："Use PostgreSQL for user data"
  
今天 Session B (新会话):
  用户："Add user profile feature"
  系统：❌ 不知道昨天的数据库决策！
```

### v0.5.3 解决方案

```
今天 Session B (新会话):
  系统：🔍 主动探查历史 session...
  系统：✅ 发现相关决策："Use PostgreSQL for user data"
  用户："Add user profile feature"
  系统：基于之前的 PostgreSQL 决策，建议...
```

## 新功能

### 1. 决策指纹去重 (`DecisionDeduplicator`)

```python
from kimi_tachi.memory.session_explorer import DecisionDeduplicator

# 创建去重器
dedup = DecisionDeduplicator().load()

# 检查是否重复
if not dedup.is_duplicate("Use Redis for caching"):
    # 添加指纹
    fp = dedup.add("Use Redis for caching", "session_123")
    print(f"Fingerprint: {fp.content_hash}")
    
# 保存状态
dedup.save()
```

**指纹生成算法：**
1. 提取关键词（过滤停用词）
2. 排序去重
3. 生成 MD5 hash
4. 存储关键词和时间戳

### 2. Session 探查器 (`SessionExplorer`)

```python
from kimi_tachi.memory.session_explorer import SessionExplorer

# 创建探查器
explorer = SessionExplorer().load()

# 查找相关决策
decisions = explorer.find_relevant_sessions(
    current_session_id="current_session",
    query="database authentication",
    current_cwd="/home/user/myproject",
    limit=5,
    min_relevance=0.2
)

for d in decisions:
    print(f"[{d['source_session']}] {d['content']}")
```

**相关性算法：**
```
score = (关键词匹配数 × 0.3) 
      + (同一项目 ? 1.0 : 0) 
      + (相关路径 ? 0.5 : 0)
      × 时间衰减(7天半衰期)
```

### 3. 已探查 Session 追踪

```python
# 检查是否已探查
if not explorer.is_explored("session_abc", by_session="current"):
    # 探查并标记
    success, decisions, relevance = explorer.explore_session(
        session_file=Path("..."),
        current_session_id="current",
        query="...",
        current_cwd="..."
    )
    # 自动标记为已探查
```

### 4. Hook 集成

`recall_on_session_start` Hook 已增强：

```python
def recall_on_session_start(session_id, source, cwd, **kwargs):
    if source == "startup" and EXPLORER_AVAILABLE:
        # 主动探查相关 session
        relevant_decisions = explorer.find_relevant_sessions(
            current_session_id=session_id,
            query=cwd,  # 使用工作目录作为查询
            current_cwd=cwd,
            limit=5,
            min_relevance=0.3
        )
        # 输出到 stdout，被 kimi-cli 捕获
```

## 存储结构

```
~/.kimi-tachi/memory/
├── hooks/                      # Session 数据 (JSON)
│   ├── session_<id>.json
│   └── history/
├── session_explorer/           # v0.5.3 新增
│   ├── decision_fingerprints.json
│   └── explored_sessions.json
└── code/                       # MemNexus 存储
```

### 指纹存储格式

```json
{
  "a1b2c3d4e5f67890": {
    "content_hash": "a1b2c3d4e5f67890",
    "keywords": ["postgresql", "database", "user"],
    "timestamp": "2026-04-01T10:30:00",
    "source_session": "session_abc123",
    "content_preview": "Use PostgreSQL for user data..."
  }
}
```

### 已探查 Session 存储格式

```json
{
  "session_abc123": {
    "session_id": "session_abc123",
    "explored_at": "2026-04-01T14:00:00",
    "explored_by": "session_xyz789",
    "relevance_score": 0.85,
    "decisions_extracted": 3
  }
}
```

## 使用场景

### 场景 1: Agent 启动时主动探查

```python
from kimi_tachi.memory.tachi_memory import TachiMemory

memory = await TachiMemory.init(".")
memory.start_session(
    session_id="my_session",
    proactive_explore=True,
    task="Implement user authentication"
)
# 自动探查相关历史决策
```

### 场景 2: 手动探查

```python
# 获取探查统计
stats = memory.get_exploration_stats()
print(f"Explored {stats['total_explored_sessions']} sessions")

# 手动搜索相关决策
decisions = memory.explore_related_sessions(
    query="database migration",
    limit=10
)
```

### 场景 3: 去重检查

```python
from kimi_tachi.memory.session_explorer import get_explorer

explorer = get_explorer()

# 在存储决策前检查
content = "Use Docker for deployment"
if not explorer._deduplicator.is_duplicate(content):
    # 真正存储
    store_decision(content)
```

## 配置选项

### 相关性阈值

```python
# 高阈值：只返回非常相关的结果
decisions = explorer.find_relevant_sessions(
    ..., min_relevance=0.7
)

# 低阈值：返回更多可能相关的结果
decisions = explorer.find_relevant_sessions(
    ..., min_relevance=0.1
)
```

### 限制数量

```python
# 限制返回的决策数量
decisions = explorer.find_relevant_sessions(
    ..., limit=3  # 最多返回 3 个
)
```

## 性能考虑

### 存储开销

- 每个决策指纹：~200 bytes
- 每个已探查记录：~150 bytes
- 1000 个决策：~200 KB

### 计算开销

- 指纹生成：O(n)，n 为内容长度
- 相关性计算：O(m×k)，m 为 session 数，k 为平均决策数
- 首次探查可能较慢（需要扫描所有 session）
- 后续探查很快（跳过已探查的 session）

### 优化建议

1. **定期归档**：旧 session 移动到 `history/` 目录
2. **增量索引**：只扫描新 session
3. **异步探查**：在后台进行探查，不阻塞主流程

## 故障排除

### 问题：探查没有找到相关 session

**可能原因：**
1. 相关性阈值太高
2. 历史 session 不存在或已删除
3. 查询词与历史决策不匹配

**解决：**
```python
# 降低阈值
decisions = explorer.find_relevant_sessions(..., min_relevance=0.1)

# 检查可用 session
print(f"Available sessions: {len(explorer.get_all_session_files())}")

# 查看统计
print(explorer.get_exploration_stats())
```

### 问题：重复决策仍然出现

**可能原因：**
1. 指纹存储未加载
2. 内容略有差异（大小写、标点等）

**解决：**
```python
# 确保加载状态
explorer = SessionExplorer().load()

# 检查指纹
dedup = explorer._deduplicator
print(f"Known fingerprints: {len(dedup._fingerprints)}")
```

### 问题：存储文件损坏

**解决：**
```python
# 重置所有状态（会丢失去重历史）
explorer.reset()
```

## 未来改进

### v0.6.0 计划

- [ ] 统一索引（SQLite + FTS5）
- [ ] 语义相似度（向量搜索）
- [ ] 决策依赖图

### v0.7.0 计划

- [ ] 项目架构知识图谱
- [ ] 长期模式学习
- [ ] 智能建议生成

---

## 参考

- 源码：`src/kimi_tachi/memory/session_explorer.py`
- 测试：`tests/test_session_explorer.py`
- 架构分析：`docs/MEMORY_ARCHITECTURE_ANALYSIS.md`
