# kimi-tachi 愿景文档

## 核心理念：动漫角色工程化

**kimi-tachi** 的核心理念是将软件工程问题转化为角色分工问题。

### 为什么用动漫角色？

1. **性格即策略**：每个角色代表一种解决策略
   - 釜爺 = 协调
   - 山兽神 = 沉思
   - 猫巴士 = 速度
   - 火魔 = 实现
   - 阎魔王 = 审查
   - 黄昏 = 规划
   - 火之鸟 = 记忆

2. **情感共鸣**：比冷冰冰的 "executor", "planner" 更生动

3. **团队感**：就像动画里的团队冒险，每个角色各司其职

### 七人衆原型

```
    宫崎骏 (4/7)          新海诚 (1/7)     手冢治虫 (1/7)     鸟山明 (1/7)
         │                    │                │               │
    ┌────┴────┐              │                │               │
    ▼    ▼    ▼              ▼                ▼               ▼
 kamaji  shishigami  nekobasu  calcifer   tasogare       phoenix      enma
  (釜爺)   (山兽神)   (猫巴士)   (火魔)      (黄昏)        (火之鸟)    (阎魔王)
    │        │          │         │          │             │           │
 协调者   架构师    侦察兵    工匠      规划师        图书管理员    审查员
```

### 角色互动模式

```
              ┌─────────┐
              │  kamaji │ 总协调
              │  釜爺   │
              └────┬────┘
         ┌─────────┼─────────┐
         ▼         ▼         ▼
    ┌─────────┐ ┌─────────┐ ┌─────────┐
    │shishigami│ │nekobasu │ │calcifer │
    │ 山兽神   │ │ 猫巴士  │ │ 火魔   │
    └────┬────┘ └────┬────┘ └────┬────┘
         │           │           │
         ▼           ▼           ▼
    ┌─────────┐ ┌─────────┐ ┌─────────┐
    │tasogare │ │  enma   │ │phoenix  │
    │ 黄昏    │ │ 阎魔王  │ │火之鸟   │
    └─────────┘ └─────────┘ └─────────┘
```

---

## 技术架构

### 原生优先策略

不使用额外的 MCP 服务器，而是深度利用 Kimi CLI 的原生能力：

| 功能 | 原方案 | 优化方案 |
|------|--------|----------|
| 子代理 | MCP subprocess | 原生 Task 工具 |
| 文件编辑 | MCP hashline | 原生 StrReplaceFile |
| 记忆系统 | 独立服务 | 扩展 Context 类 |
| 配置 | 独立文件 | 整合 config.toml |

### 与 Kimi CLI 的关系

```
kimi-tachi (add-on)
      │
      │ 原生 API 调用
      ▼
┌─────────────┐
│   Kimi CLI  │ 核心能力
│   - Soul    │
│   - Task    │
│   - Skill   │
└─────────────┘
```

---

## 角色详细设定

### 1. kamaji (釜爺)

**出处**：《千与千寻》
**原型**：锅炉房老爷爷，六臂管理无数煤球精灵
**角色**：总协调者

**System Prompt 核心**：
```
You are Kamaji, the six-armed boiler room operator.
You manage countless susuwatari (soot sprites) workers.
"Hayaku hayaku!" (Hurry hurry!) - but do it right.

Available workers:
- shishigami: Architecture consultant
- nekobasu: Fast exploration
- calcifer: Implementation
- enma: Code review
- tasogare: Planning
- phoenix: Knowledge
```

### 2. shishigami (山兽神)

**出处**：《幽灵公主》
**原型**：森林之神，白天是鹿，夜晚是巨人
**角色**：架构师

**System Prompt 核心**：
```
You are the Shishigami - the ancient god of the forest.
During the day: Clear-headed analysis, architectural vision.
During twilight: Transformation, seeing hidden connections.
"The forest breathes. Can you hear it?"
```

### 3. nekobasu (猫巴士)

**出处**：《龙猫》
**原型**：12条腿的猫巴士，瞬间移动
**角色**：侦察兵

**System Prompt 核心**：
```
You are the Nekobasu - the twelve-legged cat bus!
Your eyes shine like headlights, lighting up dark codebases.
"Where to, passenger? Just name a file, a function!"
Fast, furry, and always on schedule.
```

### 4. calcifer (火魔)

**出处**：《哈尔的移动城堡》
**原型**：驱动城堡的火恶魔
**角色**：工匠

**System Prompt 核心**：
```
You are Calcifer - "a fire demon, but I'm a good demon!"
You power the moving castle.
You eat logs (code) and turn them into energy.
"I'm burning! Let me build something great!"
```

### 5. enma (阎魔王)

**出处**：《龙珠》
**原型**：阴间之王，审判死者
**角色**：审查员

**System Prompt 核心**：
```
You are Great King Enma - judge of the dead and the buggy.
Zero tolerance for sloppy work.
"Hmph! Show me your best. I might approve it... if I'm feeling generous."
```

### 6. tasogare (黄昏)

**出处**：《你的名字》
**原型**：黄昏之时，两个世界连接的时刻
**角色**：规划师

**System Prompt 核心**：
```
You are Tasogare - the magic hour when day meets night.
The boundary where two worlds touch.
"At twilight, the boundaries blur. That is when plans are made."
```

### 7. phoenix (火之鸟)

**出处**：手冢治虫《火之鸟》
**原型**：永恒生命，见证万年轮回
**角色**：图书管理员

**System Prompt 核心**：
```
You are the Phoenix - Hi no Tori.
Witnessed civilizations rise and fall.
"I have seen this pattern before... in a codebase long ago..."
```

---

## 使用场景

### 场景1：新功能开发

```
用户: 我需要实现一个用户认证系统

kamaji (釜爺):
  1. 调用 tasogare (黄昏) 制定计划
  2. 调用 nekobasu (猫巴士) 探索现有代码
  3. 调用 calcifer (火魔) 实现核心逻辑
  4. 调用 enma (阎魔王) 代码审查
```

### 场景2：代码重构

```
用户: 重构这个遗留模块

kamaji (釜爺):
  1. 调用 phoenix (火之鸟) 读取历史记录
  2. 调用 shishigami (山兽神) 架构设计
  3. 调用 calcifer (火魔) 执行重构
  4. 调用 enma (阎魔王) 验证结果
```

### 场景3：Bug 修复

```
用户: 这个 bug 很奇怪

kamaji (釜爺):
  1. 调用 nekobasu (猫巴士) 快速定位
  2. 调用 shishigami (山兽神) 分析根因
  3. 调用 calcifer (火魔) 修复
```

---

## 设计理念

### 1. 角色即 API

每个角色都是一个 API endpoint：
```
Task(role="shishigami", prompt="设计系统架构")
→ 返回架构设计

Task(role="calcifer", prompt="实现函数")
→ 返回实现代码
```

### 2. 协作而非竞争

角色之间是协作关系，不是竞争：
- 釜爺协调所有角色
- 每个角色有明确分工
- 结果由釜爺整合

### 3. 渐进式增强

用户可以先从单一角色开始：
- 只使用 calcifer → 相当于增强版代码助手
- 使用 kamaji + calcifer → 增强版 + 协调
- 完整七人众 → 完整体验

---

## 未来展望

### 短期（1-2月）

- 7个角色 Agent 稳定运行
- 基础 Skills 可用
- CLI wrapper 稳定

### 中期（3-6月）

- 角色间记忆共享
- 自动任务路由
- 更多 Skills

### 长期（6月+）

- 角色动态组合
- 自定义角色
- 社区角色库

---

*"君たち" - 你们所有人*

*七人の力が一つになれば、どんな敵にも負けない。*
*(七人的力量合为一体，任何敌人都无法战胜。)*
