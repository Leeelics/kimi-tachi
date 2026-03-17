# kimi-tachi 文档索引

## 文档地图

```
kimi-tachi/
├── README.md              ← 开始 here（技术 + 使用）
├── VISION.md              ← 为什么做（愿景 + 动机）
├── QUICKSTART.md          ← 快速上手
├── DOCUMENTATION_INDEX.md ← 你在这里
└── docs/                  ← 详细文档（待建）
```

## 文档指南

### 1. 了解项目
**阅读顺序：** VISION.md → README.md

- **VISION.md**: 为什么要做 kimi-tachi？
  - 解决的问题
  - 设计哲学
  - 与 oh-my-opencode 的关系
  - 长期愿景

- **README.md**: kimi-tachi 是什么？
  - 技术架构
  - Agent 体系
  - 使用方式
  - 实施路线图

### 2. 开始使用
**阅读顺序：** QUICKSTART.md → README.md

- **QUICKSTART.md**: 5 分钟上手
  - 安装步骤
  - 基础命令
  - 注意事项

### 3. 深入理解
**按需阅读：**

| 你想了解 | 阅读 |
|---------|------|
| 为什么用原生 Task 不用 MCP | README.md #关键技术决策 |
| 7 个 Agent 的分工 | README.md #agent-体系 |
| 与 Kimi CLI 的关系 | VISION.md #与-kimi-cli-官方的关系 |
| 未来规划 | VISION.md #长期愿景 |
| 如何贡献 | （待建 Contributing.md）|

## 文档完整度检查

### ✅ 已完成

| 内容 | 文档 | 完整度 |
|------|------|--------|
| 项目愿景 | VISION.md | 90% |
| 技术架构 | README.md | 85% |
| Agent 定义 | README.md + agents/*.yaml | 70% (5/7) |
| 使用指南 | QUICKSTART.md | 80% |
| 路线图 | README.md #实施路线图 | 80% |
| 与 oh-my-opencode 对比 | VISION.md #与-oh-my-opencode-的关系 | 90% |

### 🚧 待补充

| 内容 | 优先级 | 计划位置 |
|------|--------|----------|
| prometheus.yaml | P0 | agents/ |
| librarian.yaml | P0 | agents/ |
| Contributing Guide | P1 | CONTRIBUTING.md |
| 详细 API 文档 | P2 | docs/api/ |
| 使用案例集 | P2 | docs/examples/ |
| ADR (架构决策记录) | P2 | docs/adr/ |
| 性能基准 | P3 | docs/benchmarks/ |

## 关键设想记录状态

### 1. 核心设想

| 设想 | 状态 | 位置 |
|------|------|------|
| 原生优先策略 | ✅ 已记录 | README.md #原生优先策略 |
| 七人衆 Agent 体系 | 🚧 部分 | README.md + agents/ (5/7) |
| Skills 系统 | ✅ 已记录 | README.md + skills/ |
| 工程化可靠性 | ✅ 已记录 | VISION.md #工程化可靠性 |
| 零侵入集成 | ✅ 已记录 | README.md #与-kimi-cli-的协作 |

### 2. 从 oh-my-opencode 继承

| 功能 | kimi-tachi 实现 | 记录位置 |
|------|----------------|----------|
| 多代理编排 | Task 工具 | README.md |
| Todo Enforcer | Skill | skills/todo-enforcer/ |
| Category Router | Skill | skills/category-router/ |
| Hashline Edit | 使用原生 StrReplaceFile | README.md #关键技术决策 |
| 分层记忆 | Phase 2 (Context 扩展) | README.md #记忆系统 |
| Ralph Loop | max_ralph_iterations 配置 | README.md #ralph-loop |
| Background Agent | 不支持 (架构差异) | VISION.md #与-oh-my-opencode-的关系 |
| Tmux 集成 | 不支持 | - |

### 3. 技术决策

| 决策 | 选择 | 理由 | 记录位置 |
|------|------|------|----------|
| 子代理机制 | Task 工具 | 原生支持，无需额外进程 | README.md |
| 配置管理 | config.toml | 统一配置源 | README.md |
| CLI 框架 | Typer | 简单，与 Kimi CLI 一致 | - |
| 包管理 | pip | 标准，易分发 | pyproject.toml |
| 命名风格 | 希腊神话 + 日语 | 文化趣味 | README.md |

### 4. 未记录的设想

以下设想**尚未明确记录**，需要补充：

#### 1. 错误处理策略
- Agent 执行失败时如何恢复？
- 重试机制？
- 降级策略？

**建议位置**: docs/adr/error-handling.md

#### 2. 可观测性
- 如何追踪多代理调用链？
- 性能监控？
- 日志记录？

**建议位置**: docs/observability.md

#### 3. 安全考虑
- Agent 执行代码的权限控制？
- 敏感信息处理？
- 沙箱机制？

**建议位置**: docs/security.md

#### 4. 版本兼容性
- 与 Kimi CLI 版本绑定策略？
- Agent YAML 版本管理？
- 迁移指南？

**建议位置**: docs/compatibility.md

## 下一步文档工作

### Phase 1 (MVP)
- [x] 核心文档（README, VISION, QUICKSTART）
- [ ] 补全 prometheus.yaml
- [ ] 补全 librarian.yaml
- [ ] 添加 CONTRIBUTING.md
- [ ] Git 仓库初始化

### Phase 2 (增强)
- [ ] 使用案例文档
- [ ] 故障排查指南
- [ ] 性能优化指南

### Phase 3 (完整)
- [ ] API 文档
- [ ] 架构决策记录 (ADR)
- [ ] 社区治理文档

## 快速参考

### 关键链接

```markdown
[README](README.md) - 项目主页
[VISION](VISION.md) - 愿景与动机
[QUICKSTART](QUICKSTART.md) - 快速开始
```

### 关键命令

```bash
# 安装
pip install -e .
kimi-tachi install

# 使用
kimi-tachi run
kimi-tachi run --agent oracle
kimi-tachi do "Implement feature"

# 开发
make format
make lint
make test
```

---

**最后更新**: 2024-03-17  
**文档版本**: 0.1.0
