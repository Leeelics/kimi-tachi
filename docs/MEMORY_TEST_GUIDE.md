# Kimi-Tachi Memory 测试指南

> 测试 feature/memory-integration 分支的完整流程

## 前置条件

- Python >= 3.12
- Git 仓库（用于测试 Git 记忆）
- kimi-cli >= 1.25.0

---

## 第一阶段：环境准备

### 1.1 切换到测试分支

```bash
cd /home/lee/ship/kimi-tachi
git checkout feature/memory-integration
git pull origin feature/memory-integration  # 确保最新
```

### 1.2 安装依赖

```bash
# 安装 kimi-tachi
pip install -e "."

# 确保 memnexus 已安装
pip install memnexus

# 验证安装
kimi-tachi --version
# 应显示 0.4.2

memnexus --version
# 应显示 0.3.0+
```

### 1.3 准备测试项目

```bash
# 创建一个测试项目（有 Git 历史）
mkdir -p /tmp/test-memory-project
cd /tmp/test-memory-project

# 初始化 Git
git init

# 创建一些测试代码文件
cat > auth.py << 'EOF'
\"\"\"Authentication module.\"\"\"
from typing import Optional

class AuthManager:
    \"\"\"Manages user authentication.\"\"\"
    
    def authenticate_user(self, username: str, password: str) -> Optional[dict]:
        \"\"\"Authenticate user with credentials.\"\"\"
        # TODO: Implement authentication
        pass
    
    def generate_token(self, user_id: str) -> str:
        \"\"\"Generate JWT token for user.\"\"\"
        return f"token_{user_id}"
EOF

cat > models.py << 'EOF'
\"\"\"Data models.\"\"\"
from pydantic import BaseModel

class User(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool = True
EOF

# 提交到 Git
git add .
git commit -m "Initial commit: Add auth and models"

# 再添加一些代码
cat > api.py << 'EOF'
\"\"\"API endpoints.\"\"\"
from fastapi import FastAPI

app = FastAPI()

@app.post("/login")
def login(username: str, password: str):
    \"\"\"User login endpoint.\"\"\"
    return {"message": "Login endpoint"}
EOF

git add .
git commit -m "Add API endpoints"
```

---

## 第二阶段：CLI 命令测试

### 2.1 初始化记忆

```bash
cd /tmp/test-memory-project

# 测试初始化
kimi-tachi memory init
```

**预期输出：**
```
🧠 Initializing memory...
✅ Memory initialized: /tmp/test-memory-project
   Session ID: tachi_20260326_xxxxxx
   Global memory available
```

**检查点：**
- [ ] 无错误
- [ ] 显示 Session ID
- [ ] 提示 Global memory available

### 2.2 索引项目

```bash
# 测试增量索引（第一次，应该索引所有）
kimi-tachi memory index
```

**预期输出：**
```
📚 Indexing project (incremental)...
✅ Indexed X Git commits
✅ Indexed Y code symbols
```

**检查点：**
- [ ] Git commits 数量 > 0
- [ ] Code symbols 数量 > 0

```bash
# 再次索引（应该跳过已索引的）
kimi-tachi memory index
```

**预期输出：**
```
📚 Indexing project (incremental)...
✅ Indexed 0 Git commits
   (X skipped - already indexed)
✅ Indexed 0 code symbols
   (Y files skipped - unchanged)
```

**检查点：**
- [ ] 显示 skipped，证明增量索引有效

```bash
# 测试全量索引
kimi-tachi memory index --full
```

**检查点：**
- [ ] 重新索引所有内容

### 2.3 搜索测试

```bash
# 搜索代码
kimi-tachi memory search "authentication"
```

**预期输出：**
```
🔍 Searching: authentication
┌─────────┬──────────────────────────────────────────┐
│ Type    │ Source                                   │
├─────────┼──────────────────────────────────────────┤
│ code    │ auth.py                                  │
│ code    │ api.py                                   │
│ general │ git:commit:xxx                           │
└─────────┴──────────────────────────────────────────┘
```

**检查点：**
- [ ] 找到 auth.py
- [ ] 找到 api.py
- [ ] 显示代码片段

```bash
# 搜索特定函数
kimi-tachi memory search "authenticate_user"
```

**检查点：**
- [ ] 找到 authenticate_user 函数
- [ ] 显示函数签名

### 2.4 状态检查

```bash
kimi-tachi memory status
```

**预期输出：**
```
🧠 Memory Status:
   Project: /tmp/test-memory-project
   Session: tachi_20260326_xxxxxx

📊 Statistics:
   Git commits indexed: X
   Code symbols indexed: Y
   Total memories: Z
```

**检查点：**
- [ ] 显示正确的项目路径
- [ ] 显示统计数据

---

## 第三阶段：全局记忆测试

### 3.1 注册到全局记忆

```bash
cd /tmp/test-memory-project

kimi-tachi memory register-global --project test-auth
```

**预期输出：**
```
🌍 Registering project in global memory: test-auth
✅ Project registered. Run 'kimi-tachi memory sync-global' to sync.
```

### 3.2 同步到全局

```bash
kimi-tachi memory sync-global --project test-auth
```

**预期输出：**
```
🌍 Syncing to global memory (incremental): test-auth
✅ Sync complete: {'indexed': X, 'projects': 1}
```

### 3.3 跨项目搜索

```bash
kimi-tachi memory global-search "JWT"
```

**预期输出：**
```
🌍 Global search: JWT
┌───────────┬──────────────────────────────────────────┐
│ Project   │ Source                                   │
├───────────┼──────────────────────────────────────────┤
│ test-auth │ auth.py                                  │
└───────────┴──────────────────────────────────────────┘
Found 1 results from 1 projects
```

**检查点：**
- [ ] 显示项目名
- [ ] 显示来源文件

---

## 第四阶段：Agent 记忆测试（关键）

### 4.1 测试 Agent 召回

```bash
cd /tmp/test-memory-project

# 召回 kamaji 的上下文
kimi-tachi memory recall --agent kamaji
```

**预期输出：**
```
🧠 Recalling context for kamaji...

◕‿◕ kamaji's Memory Profile:
[显示记忆配置]

📋 Recalled Context:
   Session: tachi_20260326_xxxxxx
   Recent memories: 0
   Relevant code: 0
   Cross-project knowledge: 0
```

**检查点：**
- [ ] 显示 Agent profile
- [ ] 显示上下文信息

### 4.2 模拟 Agent 工作并存储

创建一个测试脚本来模拟：

```bash
cat > /tmp/test_agent_memory.py << 'EOF'
import asyncio
import sys
sys.path.insert(0, '/home/lee/ship/kimi-tachi/src')

from kimi_tachi.memory import TachiMemory

async def test():
    # 初始化
    memory = await TachiMemory.init("/tmp/test-memory-project")
    
    # 1. 召回 Agent 上下文
    print("=== 1. 召回 kamaji 上下文 ===")
    context = await memory.recall_agent_context("kamaji")
    print(f"Session: {context.session_id}")
    print(f"Recent memories: {len(context.recent_memories)}")
    
    # 2. 搜索相关代码
    print("\n=== 2. 搜索代码 ===")
    results = await memory.search("authentication", limit=3)
    for r in results:
        print(f"  - {r.get('source', 'unknown')}: {r.get('content', '')[:50]}...")
    
    # 3. 存储决策
    print("\n=== 3. 存储决策 ===")
    memory_id = await memory.store_agent_output(
        agent="kamaji",
        output="决定使用 JWT 认证方案",
        task="选择认证方案",
        metadata={"decision": "JWT", "reason": "stateless"}
    )
    print(f"Stored: {memory_id}")
    
    # 4. 再次召回（应该有新记忆）
    print("\n=== 4. 再次召回 ===")
    context = await memory.recall_agent_context("kamaji")
    print(f"Recent memories: {len(context.recent_memories)}")
    if context.recent_memories:
        print(f"Latest: {context.recent_memories[0].get('content', '')[:100]}")

asyncio.run(test())
EOF

python3 /tmp/test_agent_memory.py
```

**预期输出：**
```
=== 1. 召回 kamaji 上下文 ===
Session: tachi_20260326_xxxxxx
Recent memories: 0

=== 2. 搜索代码 ===
  - auth.py: ...
  - api.py: ...

=== 3. 存储决策 ===
Stored: abc123...

=== 4. 再次召回 ===
Recent memories: 1
Latest: Task: 选择认证方案 Output: 决定使用 JWT 认证方案
```

**检查点：**
- [ ] 搜索返回结果
- [ ] 存储成功
- [ ] 再次召回能看到新记忆

---

## 第五阶段：集成到 Kimi CLI 测试

### 5.1 安装 Plugin

```bash
cd /home/lee/ship/kimi-tachi

# 确保 plugin 安装
kimi plugin uninstall kimi-tachi 2>/dev/null || true
kimi plugin install ./plugins/kimi-tachi

# 验证安装
kimi plugin list
```

**检查点：**
- [ ] kimi-tachi v0.4.2 显示为 installed

### 5.2 测试记忆工具

创建一个测试对话：

```bash
cd /tmp/test-memory-project

# 启动 kimi（会加载 kamaji，自动使用记忆）
kimi --agent-file ~/.kimi/agents/kimi-tachi/kamaji.yaml
```

在对话中测试：

```
你: 搜索一下认证相关的代码

[观察 kamaji 是否自动调用 memory_search]

你: 记住我们要用 JWT 方案

[观察 kamaji 是否自动调用 memory_store_decision]

你: 我之前说过用什么认证方案？

[观察 kamaji 是否能回忆起之前的决策]
```

### 5.3 检查记忆调用

由于工具调用是自动的，可以通过以下方式验证：

1. **查看 kimi 的日志输出**（如果开启了 verbose 模式）
2. **检查 memnexus 数据库**：
   ```bash
   # 查看存储的记忆
   ls -la ~/.memnexus/
   ls -la ~/.memnexus/global/
   ```

3. **再次搜索验证**：
   ```bash
   kimi-tachi memory search "JWT"
   # 应该能找到之前存储的决策
   ```

---

## 第六阶段：回归测试

### 6.1 确保原有功能正常

```bash
# 测试基础命令
kimi-tachi --version
kimi-tachi list-agents
kimi-tachi status

# 测试 workflow（不涉及记忆）
kimi-tachi workflow "test task" --type quick
```

### 6.2 确保无记忆时正常工作

```bash
# 在没有初始化的目录
mkdir -p /tmp/no-memory
cd /tmp/no-memory

# 这些命令应该仍然工作（只是报告无记忆）
kimi-tachi memory status
# 预期：提示未初始化

kimi-tachi start
# 预期：正常启动，只是没有记忆功能
```

---

## 问题排查

### 问题 1: ImportError: memnexus not found

```bash
pip install memnexus
# 或
pip install -e "/home/lee/ship/memnexus"
```

### 问题 2: Memory 初始化失败

```bash
# 检查权限
ls -la ~/.memnexus/

# 手动清理后重试
rm -rf ~/.memnexus/projects/test-memory-project
kimi-tachi memory init
```

### 问题 3: Agent 没有调用记忆工具

检查 agent YAML 文件：
```bash
grep "memory_" ~/.kimi/agents/kimi-tachi/kamaji.yaml
# 应该显示 memory_search, memory_store_decision 等
```

### 问题 4: 全局记忆搜索无结果

```bash
# 确保已注册和同步
kimi-tachi memory register-global --project test-auth
kimi-tachi memory sync-global --project test-auth

# 检查全局存储
ls -la ~/.memnexus/global/
```

---

## 测试通过标准

- [ ] 所有 CLI 命令正常工作
- [ ] 增量索引有效（第二次索引跳过已索引内容）
- [ ] 搜索返回相关结果
- [ ] Agent 能存储和召回记忆
- [ ] 全局记忆跨项目有效
- [ ] 原有功能不受影响
- [ ] 无记忆时优雅降级

---

## 测试完成后的操作

```bash
# 1. 提交测试结果（如果有修改）
git add -A
git commit -m "test: verify memory integration"

# 2. 切换回 main 分支（如果需要）
git checkout main

# 3. 清理测试项目
rm -rf /tmp/test-memory-project
rm -f /tmp/test_agent_memory.py
```
