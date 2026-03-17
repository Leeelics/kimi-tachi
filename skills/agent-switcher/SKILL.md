---
name: agent-switcher
description: Switch between kimi-tachi anime agents using /agent command
triggers:
  - "/agent:"
---

# Agent Switcher (エージェント切替)

Switch to a specialized kimi-tachi anime agent.

## Usage

### Starting kimi-tachi

```bash
# Start with kamaji (coordinator)
kimi --agent-file ~/.kimi/agents/kimi-tachi/kamaji.yaml

# Or start with a specific agent directly
kimi --agent-file ~/.kimi/agents/kimi-tachi/shishigami.yaml
```

### Switching Agents in Conversation

Once inside kimi, type `/agent:<name>` followed by your request:

```
/agent:shishigami 如何设计这个缓存系统？
/agent:nekobasu 找出所有 API 端点定义
/agent:calcifer 实现用户认证功能
/agent:enma 审查这段代码的质量
/agent:tasogare 帮我规划这个项目
/agent:phoenix 找一下相关文档
/agent:kamaji 回到总协调
```

## Available Agents

| Command | Character | Origin | Role |
|---------|-----------|--------|------|
| `/agent:kamaji` | 釜爺 | Spirited Away | Coordinator - manages all workers |
| `/agent:shishigami` | シシ神 | Princess Mononoke | Architect - ancient wisdom, system design |
| `/agent:nekobasu` | 猫バス | My Neighbor Totoro | Explorer - fast code navigation |
| `/agent:calcifer` | カルシファー | Howl's Moving Castle | Builder - implementation, coding |
| `/agent:enma` | 閻魔大王 | Dragon Ball | Reviewer - strict code quality judge |
| `/agent:tasogare` | 黄昏時 | Your Name | Planner - research and planning |
| `/agent:phoenix` | 火の鳥 | Phoenix (Tezuka) | Librarian - knowledge and documentation |

## Context Handling

When switching agents:
1. **Current context is preserved** - The new agent receives relevant background
2. **Task continuity** - Work continues seamlessly
3. **No repetition needed** - Don't re-explain what you already discussed

## Examples

### Architecture Discussion
```
User: /agent:shishigami 我想设计一个微服务架构
shishigami: [provides architecture advice]
User: /agent:calcifer 按照这个架构实现服务发现模块
calcifer: [implements based on shishigami's design]
```

### Code Review Flow
```
User: /agent:calcifer 实现用户登录功能
calcifer: [implements code]
User: /agent:enma 审查一下这段代码
enma: [reviews and provides feedback]
User: /agent:calcifer 按照enma的建议修复
calcifer: [fixes the issues]
```

### Exploration to Implementation
```
User: /agent:nekobasu 找一下认证相关的代码在哪里
ekobasu: [finds the files]
User: /agent:calcifer 在这些文件基础上添加 OAuth 支持
calcifer: [implements OAuth]
```

## Tips

- You can switch agents as many times as needed
- Each agent specializes in their domain - use the right tool for the job
- Kamaji (coordinator) can delegate automatically, but explicit `/agent` gives you control
- When in doubt, start with kamaji and let him coordinate
