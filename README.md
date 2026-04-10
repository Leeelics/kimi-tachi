# kimi-tachi (君たち)

> Multi-agent task orchestration for Kimi CLI

[![Version](https://img.shields.io/badge/version-0.6.2-blue.svg)](./CHANGELOG.md)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)

## 是什么

**kimi-tachi** 是 Kimi CLI 的多智能体编排层。灵感来自宫崎骏、新海诚、手冢治虫、鸟山明的作品角色。

你只需要和 **釜爺 (kamaji)** 对话，其他六位角色会在幕后自动协作——探索代码、设计架构、实现功能、审查质量，共同完成任务。

| Agent | 角色 | 职责 | Emoji |
|-------|------|------|-------|
| **kamaji** | 釜爺 | 总协调（唯一接口） | ◕‿◕ |
| **nekobasu** | 猫バス | 代码探索 | 🚌 |
| **shishigami** | シシ神 | 架构设计 | 🦌 |
| **calcifer** | カルシファー | 代码实现 | 🔥 |
| **enma** | 閻魔大王 | 代码审查 | 👹 |
| **tasogare** | 黄昏時 | 任务规划 | 🌆 |
| **phoenix** | 火の鳥 | 知识管理 | 🐦 |

## 怎么用

### 安装

```bash
pip install kimi-tachi
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

### 示例效果

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
