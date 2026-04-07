# kimi-tachi Memory System

> 智能 Session 探查与记忆管理

## 概述

记忆系统提供跨会话的决策保持和知识积累能力。

### 核心能力

| 功能 | 说明 |
|------|------|
| **决策去重** | 自动识别和避免重复存储相同决策 |
| **Session 探查** | 主动发现历史会话中的相关决策 |
| **跨会话记忆** | 新会话自动继承相关历史决策 |

---

## 架构

```
┌─────────────────────────────────────────────────────────────┐
│                    kimi-tachi Memory                         │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: TachiMemory (Orchestration)                       │
│           - 提供高层 API                                     │
│           - 格式化输出给 kimi-cli                           │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: MemoryAdapter (Abstraction)                       │
│           - 统一接口封装                                     │
│           - 支持 memnexus 和 fallback                       │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: Storage Backend                                   │
│           - memnexus (主要)                                 │
│           - JSON files (fallback)                           │
└─────────────────────────────────────────────────────────────┘
```

### MemNexus 集成

memnexus 是主要的存储后端（v0.4.0+）：

```python
from memnexus.session import SessionExplorer, DecisionDeduplicator

# Session 探查
explorer = SessionExplorer()
result = explorer.explore_related(
    current_session_id="session_123",
    query="database design",
    limit=5
)

# 决策去重
dedup = DecisionDeduplicator()
check = dedup.check_duplicate("Use Redis for caching")
if not check.is_duplicate:
    dedup.record_decision("Use Redis for caching", session_id)
```

---

## 使用方式

### 基础 API

```python
from kimi_tachi.memory import TachiMemory, get_memory

# 获取记忆实例
memory = await get_memory(".")

# 为任务回忆相关上下文
context = await memory.recall_for_task("implement auth")

# 存储决策
await memory.store_decision("Use JWT for authentication")
```

### Session 探查

```python
from kimi_tachi.memory.session_explorer import SessionExplorer

explorer = SessionExplorer().load()

# 查找相关历史决策
decisions = explorer.find_relevant_sessions(
    current_session_id="current",
    query="database authentication",
    limit=5
)
```

### 决策去重

```python
from kimi_tachi.memory.session_explorer import DecisionDeduplicator

dedup = DecisionDeduplicator().load()

# 检查是否已存在相同决策
if not dedup.is_duplicate("Use Redis for caching"):
    dedup.add("Use Redis for caching", session_id)
    dedup.save()
```

---

## 存储结构

```
~/.kimi-tachi/memory/
├── hooks/
│   ├── session_<id>.json       # 活跃会话
│   └── history/                # 归档会话
├── code/                       # 代码记忆 (MemNexus)
└── global/                     # 全局记忆
```

---

## 集成

### Hooks 自动触发

```yaml
# hooks/kimi-tachi_hooks.yml
hooks:
  SessionStart:
    tools:
      - kimi_tachi.hooks.tools:recall_session_context
  
  BeforeContextCompact:
    tools:
      - kimi_tachi.hooks.tools:store_key_decisions
```

### CLI 命令

```bash
# 初始化记忆
kimi-tachi memory init

# 索引项目
kimi-tachi memory index

# 搜索记忆
kimi-tachi memory search "auth"

# 查看当前会话上下文
kimi-tachi memory recall
```

---

## 测试

### 环境准备

```bash
# 安装依赖
pip install -e "."
pip install memnexus

# 验证安装
kimi-tachi --version
memnexus --version
```

### 功能测试

```bash
# 1. 初始化记忆
kimi-tachi memory init

# 2. 在项目中索引代码
kimi-tachi memory index

# 3. 搜索记忆
kimi-tachi memory search "authentication"

# 4. 开始会话测试自动回忆
kimi-tachi start
# 然后询问："实现用户认证"
# 系统应该自动回忆之前的相关决策
```

---

## 迁移指南

当 memnexus 0.4.0+ 可用时，更新 `MemoryAdapter`：

```python
# _memory_adapter.py
from memnexus.session import SessionExplorer, DecisionDeduplicator

class MemoryAdapter:
    def __init__(self):
        self._explorer = SessionExplorer()
        self._deduplicator = DecisionDeduplicator()
```

---

*API 映射: `SessionExplorer.find_relevant_sessions()` → `SessionExplorer.explore_related()`*
