# v0.5.3 架构重构总结

## 背景

用户反馈：记忆相关的能力应该放到 **memnexus** 来实现，**kimi-tachi** 主要是组织和调用，提供便利的 kimi-cli harness。

## 问题

v0.5.3 初始实现把 Session Explorer 直接放在 kimi-tachi 里，违背了分层原则：

```
❌ Before (v0.5.3 initial):
kimi-tachi/
├── memory/
│   ├── session_explorer.py    # 实现了存储逻辑（应该在 memnexus）
│   └── tachi_memory.py        # 直接操作 JSON 文件
```

## 重构方案

### 架构分层

```
✅ After (v0.5.3 refactored):

┌─────────────────────────────────────────────────────────┐
│  Layer 3: kimi-tachi (Orchestration + CLI Harness)      │
│  ─────────────────────────────────────────────────────  │
│  • Orchestrate memory operations                        │
│  • Format output for kimi-cli                           │
│  • Provide convenient APIs                              │
│  • Hooks integration                                    │
├─────────────────────────────────────────────────────────┤
│  Layer 2: MemoryAdapter (Abstraction Layer)             │
│  ─────────────────────────────────────────────────────  │
│  • Abstract memnexus interface                          │
│  • Fallback to temporary implementations                │
│  • Hide implementation details                          │
├─────────────────────────────────────────────────────────┤
│  Layer 1: memnexus / Fallback                           │
│  ─────────────────────────────────────────────────────  │
│  • memnexus: Official storage backend (when available)  │
│  • Fallback: Temporary implementations (marked TODO)    │
│  • Storage: JSON files, vector index, etc.              │
└─────────────────────────────────────────────────────────┘
```

### 文件重组

```
kimi_tachi/memory/
├── __init__.py                    # 重新导出
├── tachi_memory.py                # 现在只是导入转发
├── tachi_memory_v2.py             # 重构后的实现 (orchestration only)
├── tachi_memory_legacy.py         # 保留旧版本
├── _memory_adapter.py             # 新增：适配层
├── session_explorer.py            # 标记为 TEMPORARY
├── agent_profiles.py              # 未改动
└── ...
```

## 关键变化

### 1. TachiMemoryV2 (Orchestration Layer)

```python
class TachiMemoryV2:
    """
    Responsibilities:
    ✅ ORCHESTRATION: Coordinate memory operations
    ✅ CLI INTEGRATION: Format output for kimi-cli  
    ✅ WORKFLOW: Provide high-level APIs
    
    NOT Responsible:
    ❌ Storage implementation (delegated to adapter)
    ❌ Vector indexing (memnexus)
    ❌ Deduplication algorithm (memnexus)
    """
    
    async def recall_for_task(self, task: str) -> dict:
        # 1. Call adapter.explore_sessions() -> delegates to memnexus
        # 2. Call mn_memory.store.search() -> memnexus
        # 3. Format results for kimi-cli
        pass
```

### 2. MemoryAdapter (Abstraction Layer)

```python
class MemoryAdapter:
    """
    Unified interface that:
    - Uses memnexus when available
    - Falls back to temporary implementations
    - Hides implementation details from TachiMemory
    """
    
    async def explore_sessions(...) -> ExplorationResult:
        # TODO v0.6.0: Call memnexus.SessionExplorer
        # Current: Fall back to temporary SessionExplorer
        pass
```

### 3. Protocol Definitions (API Contracts)

```python
class ISessionExplorer(Protocol):
    """What memnexus should provide"""
    async def explore_related(...) -> ExplorationResult: ...
    
class IDeduplicator(Protocol):
    """What memnexus should provide"""
    async def check_duplicate(...) -> DuplicateCheckResult: ...
```

## Migration Path

### Phase 1: v0.5.3 (Current)
- ✅ 重构完成，添加适配层
- ✅ 标记临时实现 (TODO v0.6.0)
- ✅ 保持功能不变
- ✅ 向后兼容

### Phase 2: v0.6.0 (When memnexus ready)
```python
# In _memory_adapter.py:
async def _init_from_memnexus(self):
    from memnexus import SessionExplorer, DecisionDeduplicator  # Enable this
    self._explorer = SessionExplorer()  # Use memnexus version
    self._deduplicator = DecisionDeduplicator()
    
# Remove fallback implementations
# Remove session_explorer.py
```

### Phase 3: v0.7.0 (Cleanup)
- Remove `_memory_adapter.py` (if memnexus API is stable)
- Call memnexus directly from TachiMemory
- Remove temporary implementations

## API 变化

### 对用户代码：无变化

```python
from kimi_tachi.memory import TachiMemory, get_memory

# 使用方式完全不变
memory = await get_memory(".")
context = await memory.recall_for_task("implement auth")
```

### 对内部实现：清晰分层

```python
# Before: Direct implementation
from .session_explorer import SessionExplorer
explorer = SessionExplorer()
results = explorer.find_relevant_sessions(...)

# After: Via adapter (hides implementation)
from ._memory_adapter import get_memory_adapter
adapter = get_memory_adapter()
results = await adapter.explore_sessions(...)
```

## 文件变更详情

| 文件 | 变化 | 说明 |
|------|------|------|
| `tachi_memory.py` | 📝 重写 | 现在是导入转发 |
| `tachi_memory_v2.py` | ➕ 新增 | 重构后的 orchestration 层 |
| `tachi_memory_legacy.py` | ➕ 保留 | 旧版本备份 |
| `_memory_adapter.py` | ➕ 新增 | 适配层和协议定义 |
| `session_explorer.py` | 🏷️ 标记 | 添加 TEMPORARY 注释 |
| `hooks/tools.py` | 🔧 更新 | 使用新的适配 API |

## 测试

- ✅ 所有 21 个 Session Explorer 测试通过
- ✅ 导入测试通过
- ✅ 向后兼容

## 总结

这次重构明确了架构边界：

1. **kimi-tachi** = Orchestration + CLI Harness
2. **MemoryAdapter** = Abstraction layer
3. **memnexus** = Storage backend (target)
4. **Fallback** = Temporary (marked for migration)

当 memnexus 实现了 Session Explorer 功能后，只需修改 `_memory_adapter.py` 中的几行代码即可切换，无需改动 kimi-tachi 的上层逻辑。
