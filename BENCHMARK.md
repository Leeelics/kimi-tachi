# Kimi-Tachi Efficiency Benchmark

> 项目健康度与效率基线看板  
> 最后更新：`2026-04-10`

---

## 一、代码健康指标

| 指标 | 当前值 | 基线 (清理前) | 变化 |
|------|--------|---------------|------|
| `src/kimi_tachi/` 总代码行数 | **2,207** | ~14,500 | **-84.8%** |
| Python 源文件数 | **16** | ~40 | **-60%** |
| 测试用例数 | **70 passed** | 170 passed | 聚焦有效测试 |
| ruff lint 错误 | **0** | 0 | 持平 |
| pytest 执行时间 | **~1.9s** | ~4.5s | **-58%** |

---

## 二、功能验证指标

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 单元测试 | ✅ 67 passed | CLI、Team、Compatibility、Memory |
| 集成测试 | ✅ 18 passed | Plugins (workflow、router、todo-enforcer) |
| E2E 测试 | ✅ 3 passed | install → status → uninstall 完整链路 |
| 构建检查 | ✅ pass | sdist + wheel 构建成功 |
| 死代码残留 | ✅ 0 | orchestrator / context / session / background 已清空 |
| Workflow Plan 有效性 | ✅ pass | 任务复杂度分析 → phase 生成正确 |
| Subagent Type 映射 | ✅ pass | anime 名字已映射为 `coder`/`explore`/`plan` |

---

## 三、Workflow 引擎能力基线

| 能力 | 当前支持 | 备注 |
|------|----------|------|
| 单任务多阶段编排 | ✅ | `tasogare → nekobasu → calcifer → enma` |
| `research`/`plan` 并行执行 | ✅ | 同类别 phase 可合并为一个 batch |
| `create`/`review` 串行执行 | ✅ | 默认安全策略，避免并行写冲突 |
| **多分身（同类型 Agent 拆分任务）** | ❌ | 不支持把一个大任务拆成 N 个子任务并行处理 |
| **Map-Explore（多文件并行探查）** | ❌ | 不支持一次性起多个 `explore` 分别查不同目录 |
| **Map-Create（多文件并行创建）** | ❌ | 不支持多个 `coder` 同时写不同文件 |
| **Reduce（多结果聚合后分发）** | ❌ | 没有 explore 结果 → 多个 create 的分发机制 |
| `background` 执行 | ⚠️ 部分 | 仅 `research`/`plan` 可标记 `can_background=true` |
| `model` override | ❌ | workflow plan 未输出 `model` 字段 |
| `resume` 续跑 | ❌ | workflow plan 未输出 `resume` 字段 |

> **评估结论**：当前 kimi-tachi 是一个**轻量 Plan Generator**，能够生成标准的线性/轻度并行 workflow。但尚不具备 "Map-Reduce" 式的多分身能力。

---

## 四、效率得分 (KT-Score)

一种简化的内部评分，用来衡量 "用更少的代码做更对的事"。

```
KT-Score = (有效测试数 / 代码行数 × 1000) × (1 + 构建成功率)
         = (70 / 2207 × 1000) × 2
         = 31.7 × 2
         = 63.4
```

- **清理前**：(170 / 14500 × 1000) × 2 ≈ **23.4**
- **清理后**：**63.4**（↑ 171%）

这代表每 1000 行代码支撑的「有效测试密度」大幅提升，维护成本显著降低。

---

## 五、下一步优化方向

1. **增强 Workflow 并行能力**
   - 支持任务拆分（Split）→ 多 `explore` 并行 → 结果聚合 → 多 `coder` 并行
   - 这对 "重构 10 个文件"、"给整个项目补文档" 类任务至关重要

2. **补齐 kimi-cli v1.30.0  capability gap**
   - 在 workflow plan 中支持 `model` override
   - 支持 `resume` 续跑已有 agent 实例
   - 支持 `include_ignored` 等 grep 高级参数透传

3. **引入真实性能基准**
   - 测量 "生成一个 feature workflow plan" 的耗时（目标 < 50ms）
   - 测量 `kimi-tachi install` 的端到端耗时

---

*Maintained by the boiler room chief. 🔥*
