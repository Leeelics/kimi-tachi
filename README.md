# kimi-tachi (君たち)

> Multi-agent task orchestration for Kimi CLI

[![Version](https://img.shields.io/badge/version-0.6.2-blue.svg)](./CHANGELOG.md)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)

## 是什么

**kimi-tachi** 是 Kimi CLI 的多团队智能体编排系统。每个团队由一名 **Coordinator（队长）** 和若干专业 Agent 组成。

你始终只和当前团队的 **Coordinator** 对话，队长会在幕后自动调度团队成员完成任务。

### 内置团队

| 团队 | 主题 | Coordinator | 适用场景 |
|------|------|-------------|----------|
| **coding** | 七人衆（宫崎骏/吉卜力）| 釜爺 (kamaji) | 编程开发、架构设计、代码审查 |
| **content** | 三国·自媒体天团 | 荀彧 (xunyu) | 内容创作、选题写作、排版设计 |

### coding 团队角色示例

| Agent | 角色 | 职责 | Emoji |
|-------|------|------|-------|
| **kamaji** | 釜爺 | 总协调 | ◕‿◕ |
| **nekobasu** | 猫バス | 代码探索 | 🚌 |
| **shishigami** | シシ神 | 架构设计 | 🦌 |
| **calcifer** | カルシファー | 代码实现 | 🔥 |
| **enma** | 閻魔大王 | 代码审查 | 👹 |
| **tasogare** | 黄昏時 | 任务规划 | 🌆 |
| **phoenix** | 火の鳥 | 知识管理 | 🐦 |

## 怎么用

### 安装与升级

```bash
# 首次安装
pip install kimi-tachi
kimi-tachi install

# 升级到新版本后，重新 install 即可更新 agents/skills/plugins
kimi-tachi install
```

要求：kimi-cli >= 1.25.0，Python >= 3.12

### 启动

```bash
# 直接启动（默认使用 kamaji）
kimi-tachi
```

### 团队切换

```bash
# 查看可用团队
kimi-tachi teams list

# 切换团队
kimi-tachi teams switch <team-id>
```

### 查看状态

```bash
kimi-tachi status
```

## 有什么效果

### 自动任务编排

kamaji 会根据任务复杂度自动调度合适的角色：

- **简单任务** → kamaji 直接处理
- **中等任务** → 🚌 探索后执行
- **复杂任务** → 🌆 规划 → 🚌 探索 → 🦌 架构 → 🔥 实现 → 👹 审查

### 示例效果（coding 团队）

```
用户：实现用户登录功能
kamaji：🌆 复杂任务，开始协调团队...

[调用 tasogare 规划 JWT 方案]
[调用 nekobasu 探索现有代码]
[调用 calcifer 实现登录接口]
[调用 enma 审查通过]

结果：已实现 JWT 登录系统
---
◕‿◕ Workers Involved:
- 🌆 tasogare: 规划 JWT 方案
- 🚌 nekobasu: 找到现有用户模型
- 🔥 calcifer: 实现 4 个文件
- 👹 enma: 审查通过
```

### 测试分层

- `tests/unit/` — 单元测试
- `tests/integration/` — 集成测试

```bash
make test        # 运行全部测试
make check       # 运行代码检查
```

## 链接

- [Changelog](./CHANGELOG.md)
- [License](./LICENSE)
