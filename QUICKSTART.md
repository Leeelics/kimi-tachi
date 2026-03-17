# Quick Start

快速开始使用 kimi-tachi 七人众

## 安装

```bash
# 安装 kimi-tachi
pip install kimi-tachi

# 安装到 Kimi CLI（复制 agents 和 skills）
kimi-tachi install

# 配置默认角色（可选）
kimi-tachi setup
```

## 基础使用

### 1. 启动 kimi-tachi

```bash
# 使用 kamaji (釜爺) 启动 - 总协调角色
kimi --agent-file ~/.kimi/agents/kimi-tachi/kamaji.yaml

# 或者使用其他角色直接启动
kimi --agent-file ~/.kimi/agents/kimi-tachi/shishigami.yaml  # 架构师
kimi --agent-file ~/.kimi/agents/kimi-tachi/calcifer.yaml    # 实现专家
```

### 2. 在对话中切换角色

启动 kimi 后，使用 `/agent:<name>` 切换角色：

```
# 架构咨询 - 山兽神
> /agent:shishigami 如何设计这个缓存系统？

# 快速探索 - 猫巴士  
> /agent:nekobasu 找出所有 API 端点

# 代码实现 - 火魔
> /agent:calcifer 实现用户认证功能

# 代码审查 - 阎魔王
> /agent:enma 审查这段代码

# 规划研究 - 黄昏
> /agent:tasogare 帮我规划这个项目

# 知识查询 - 火之鸟
> /agent:phoenix 找一下相关文档

# 返回总协调
> /agent:kamaji 总结一下
```

## 使用示例

### 新功能开发流程

```bash
# 1. 启动总协调
kimi --agent-file ~/.kimi/agents/kimi-tachi/kamaji.yaml
```

在对话中：
```
> 帮我实现一个用户认证系统

[kamaji 分析任务并协调]

> /agent:shishigami 设计架构
[shishigami 提供架构建议]

> /agent:calcifer 按照架构实现
[calcifer 编写代码]

> /agent:enma 审查代码
[enma 审查并提供反馈]

> /agent:calcifer 修复问题
[calcifer 修复代码]
```

## 查看可用角色

```bash
kimi-tachi list-agents
```

输出：
```
Available agents (七人衆):

  calcifer        - Fire Demon - Powers the castle with code (カルシファー)
  enma            - King of Afterlife - Judges code quality strictly (閻魔大王)
  kamaji          - Boiler Room Chief - The six-armed coordinator (釜爺)
  nekobasu        - Cat Bus Express - Fast exploration with twelve legs (猫バス)
  phoenix         - Eternal Observer - Knowledge across time (火の鳥)
  shishigami      - Forest Deity - Architecture and ancient wisdom (シシ神)
  tasogare        - Twilight Hour - Connects problem and solution (黄昏時)
```

## CLI 命令

```bash
# 查看状态
kimi-tachi status

# 重新配置默认角色
kimi-tachi setup

# 重置安装
kimi-tachi reset

# 完全卸载
kimi-tachi uninstall
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

## 下一步

- 阅读 [VISION.md](VISION.md) 了解设计理念
- 阅读 [README.md](README.md) 查看完整文档
- 尝试不同的角色，找到最适合你的工作流
