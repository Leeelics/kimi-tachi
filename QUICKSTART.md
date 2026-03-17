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

### 1. 使用总协调启动

```bash
# 默认使用 kamaji (釜爺)
kimi-tachi run

# 等同于
kimi-tachi run --agent kamaji
```

### 2. 使用特定角色

```bash
# 架构咨询 - 山兽神
kimi-tachi run --agent shishigami

# 快速探索 - 猫巴士
kimi-tachi run --agent nekobasu

# 代码实现 - 火魔
kimi-tachi run --agent calcifer

# 代码审查 - 阎魔王
kimi-tachi run --agent enma

# Plan Mode - 黄昏
kimi-tachi run --agent tasogare --plan

# 知识查询 - 火之鸟
kimi-tachi run --agent phoenix
```

### 3. One-shot 模式

```bash
# 单次任务，无需交互
kimi-tachi do "实现用户登录功能"

# 指定角色
kimi-tachi do --agent calcifer "重构这个函数"
```

## 使用示例

### 新功能开发流程

```bash
# 启动总协调
kimi-tachi run

# 在对话中：
> 帮我实现一个用户认证系统

# kamaji 会自动：
# 1. 调用 tasogare 制定计划
# 2. 调用 nekobasu 探索代码
# 3. 调用 calcifer 实现
# 4. 调用 enma 审查
```

### 直接调用 Kimi CLI

```bash
# 安装后，Agent 已复制到 ~/.kimi/agents/kimi-tachi/
kimi --agent ~/.kimi/agents/kimi-tachi/calcifer.yaml
```

## 查看可用角色

```bash
kimi-tachi list-agents
```

输出：
```
Available Agents:
  - kamaji     (釜爺)    - 总协调
  - shishigami (山兽神)  - 架构师
  - nekobasu   (猫巴士)  - 侦察兵
  - calcifer   (火魔)    - 工匠
  - enma       (阎魔王)  - 审查员
  - tasogare   (黄昏)    - 规划师
  - phoenix    (火之鸟)  - 记忆
```

## 配置

编辑 `~/.kimi/config.toml`：

```toml
[kimi_tachi]
default_agent = "kamaji"

[kimi_tachi.agents]
kamaji.model = "kimi-k2.5"
calcifer.yolo = false
```

## 故障排查

### 检查安装

```bash
kimi-tachi status
```

### 重新安装

```bash
# 删除旧配置
rm -rf ~/.kimi/agents/kimi-tachi
rm -rf ~/.kimi/skills/todo-enforcer
rm -rf ~/.kimi/skills/category-router

# 重新安装
kimi-tachi install
```

## 下一步

- 阅读 [VISION.md](VISION.md) 了解设计理念
- 阅读 [README.md](README.md) 查看完整文档
- 尝试不同的角色，找到最适合你的工作流
