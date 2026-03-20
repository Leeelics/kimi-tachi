# Quick Start

快速开始使用 kimi-tachi 七人众

## 安装

```bash
# 安装 kimi-tachi
pip install kimi-tachi

# 安装到 Kimi CLI（复制 agents 和 skills）
kimi-tachi install
```

## 基础使用

### 1. 启动 kimi-tachi

```bash
# 直接启动（默认使用 kamaji 釜爺）
kimi-tachi

# 或显式启动
kimi-tachi start
```

启动后，你会进入 Kimi CLI 交互界面，状态栏显示 `agent (kimi-for-coding)`。

### 2. 和 kamaji 对话

**你只需要和 kamaji 对话**，其他角色会自动在幕后工作。

#### 简单任务

```
> 读取 pyproject.toml 的内容

[kamaji 直接读取并展示文件内容]
```

#### 需要探索的任务

```
> 找到项目中所有和 database 相关的代码

🚌 让我派猫巴士去找找...

找到 8 个相关文件：
- src/db/connection.py
- src/models/user.py
- src/migrations/001_initial.sql
...

---
**◕‿◕ Workers Involved:**
- 🚌 nekobasu: 探索了项目结构，找到 8 个文件
```

#### 实现功能

```
> 帮我实现一个用户登录功能

🌆 这是一个复杂任务，让我协调团队...

[🌆 tasogare 正在分析需求...]
[🚌 nekobasu 正在探索现有代码...]
[🔥 calcifer 正在实现代码...]
[👹 enma 正在审查...]

已完成！实现了 JWT 认证系统：
- POST /api/auth/login - 用户登录
- POST /api/auth/register - 用户注册
- AuthMiddleware - 路由保护
- User 模型更新

---
**◕‿◕ Workers Involved:**
- 🌆 tasogare: 分析了需求，选择 JWT 方案
- 🚌 nekobasu: 找到现有 User 模型
- 🔥 calcifer: 实现了 4 个文件，包含完整测试
- 👹 enma: 代码审查通过，修复了 2 处风格问题

「さあ、働け！働け！」团队完成！
```

## 工作原理

kimi-tachi 使用 **自动编排**：

```
用户请求
    ↓
kamaji 分析任务复杂度
    ↓
┌─────────────────┬─────────────────┐
│   简单任务      │   复杂任务       │
│   kamaji 直接   │   调用 workers   │
│   处理          │   幕后协作       │
└─────────────────┴─────────────────┘
    ↓
统一回复给用户
    ↓
显示 Workers Involved（参与的角色）
```

## 角色介绍

| 角色 | Emoji | 来源 | 职责 |
|------|-------|------|------|
| kamaji | ◕‿◕ | 《千与千寻》| 总协调，你的唯一接口 |
| shishigami | 🦌 | 《幽灵公主》| 架构设计 |
| nekobasu | 🚌 | 《龙猫》| 代码探索 |
| calcifer | 🔥 | 《哈尔的移动城堡》| 代码实现 |
| enma | 👹 | 《龙珠》| 代码审查 |
| tasogare | 🌆 | 《你的名字》| 规划研究 |
| phoenix | 🐦 | 《火之鸟》| 知识管理 |

**注意**：除了 kamaji，其他角色都在幕后工作，不会直接与你对话。

## CLI 命令

除了 `kimi-tachi` 启动交互式会话，还有一些辅助命令：

```bash
# 查看所有角色
kimi-tachi list-agents

# 查看安装状态
kimi-tachi status

# 工作流模式（非交互式，自动执行完整流程）
kimi-tachi workflow "实现用户认证" --type feature

# 会话管理
kimi-tachi sessions              # 查看会话历史
kimi-tachi sessions --clear      # 清除会话

# 维护
kimi-tachi setup      # 重新配置
kimi-tachi reset      # 重置安装
kimi-tachi uninstall  # 完全卸载
```

## 使用示例

### 示例 1：Bug 修复

```
> 修复登录时的空指针异常

🚌 让我先找找相关代码...

找到问题在 src/auth.py:42，当用户不存在时没有正确处理。

🔥 已修复！添加了空值检查：
```python
if user is None:
    raise AuthenticationError("User not found")
```

---
**◕‿◕ Workers Involved:**
- 🚌 nekobasu: 定位到问题代码
- 🔥 calcifer: 实现修复
- 👹 enma: 审查通过
```

### 示例 2：架构咨询

```
> 我应该用 Redis 还是内存缓存？

🌆 让我分析一下需求...

🦌 基于分析，建议如下：

| 方案 | 适用场景 | 建议 |
|------|----------|------|
| Redis | 多实例部署、持久化 | ✅ 推荐 |
| 内存 | 单实例、简单场景 | ⚠️ 有限制 |

对于你的项目（看起来是微服务），建议使用 Redis：
- 支持分布式缓存
- 数据持久化
- 丰富的数据结构

---
**◕‿◕ Workers Involved:**
- 🌆 tasogare: 分析了项目规模和需求
- 🦌 shishigami: 设计了缓存架构方案
```

### 示例 3：代码重构

```
> 重构 utils.py，把它拆分成多个模块

🚌 先探索一下 utils.py 的内容...
🌆 规划重构方案...
🔥 执行重构...
👹 审查重构结果...

已完成重构！将 utils.py 拆分为：
- utils/datetime.py - 时间相关
- utils/string.py - 字符串处理
- utils/validation.py - 验证逻辑
- utils/http.py - HTTP 工具

所有原有导入保持兼容（添加了 re-export）。

---
**◕‿◕ Workers Involved:**
- 🚌 nekobasu: 分析了 utils.py 的结构
- 🌆 tasogare: 制定了重构计划
- 🔥 calcifer: 执行了重构，保持向后兼容
- 👹 enma: 审查通过，无功能回退
```

## 故障排查

### 检查安装

```bash
kimi-tachi status
```

### 重新安装

```bash
# 重置到干净状态
kimi-tachi reset

# 或者手动删除后重装
kimi-tachi uninstall
kimi-tachi install
```

### 手动启动

如果 `kimi-tachi` 命令有问题，可以直接用 Kimi CLI：

```bash
kimi --agent-file ~/.kimi/agents/kimi-tachi/kamaji.yaml
```

## 下一步

- 阅读 [VISION.md](./VISION.md) 了解设计理念
- 阅读 [README.md](../README.md) 查看完整文档
- 尝试不同的任务类型，观察 kamaji 如何自动编排

---

**💡 提示**：不需要记住复杂的命令或角色分工，像平常一样描述你的需求，kamaji 会自动协调最适合的团队来完成任务。
