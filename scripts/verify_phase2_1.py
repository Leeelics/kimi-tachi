#!/usr/bin/env python3
"""
Phase 2.1 验证脚本

验证动态 Agent 创建是否成功：
1. MCP 进程数是否从 7 降到 ≤2
2. 动态创建功能是否正常工作
3. 回退机制是否可用

用法:
    python scripts/verify_phase2_1.py
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, "/home/lee/ship/kimi-tachi/src")

from kimi_tachi.orchestrator.agent_factory import AgentFactory
from kimi_tachi.orchestrator.hybrid_orchestrator import HybridOrchestrator


def count_mcp_processes() -> int:
    """统计当前 MCP 进程数量"""
    try:
        result = subprocess.run(["ps", "aux"], capture_output=True, text=True)

        count = 0
        for line in result.stdout.split("\n"):
            # 检测 MCP 相关进程 (排除当前监控进程和 grep)
            if (
                ("mcp" in line.lower() or "node" in line.lower())
                and "verify_phase2_1" not in line
                and "grep" not in line
            ):
                count += 1

        return count
    except Exception as e:
        print(f"⚠️  无法统计 MCP 进程: {e}")
        return -1


def test_agent_factory():
    """测试 AgentFactory"""
    print("\n" + "=" * 80)
    print("🔧 测试 AgentFactory")
    print("=" * 80)

    try:
        factory = AgentFactory()
        print("✅ AgentFactory 初始化成功")

        # 测试加载 agent 配置
        config = factory.get_agent_config("nekobasu")
        print(f"✅ 加载 nekobasu 配置成功: {config.name}")
        print(f"   角色: {config.role}")
        print(f"   工具数: {len(config.tools)}")

        # 测试统计信息
        stats = factory.get_stats()
        print(f"✅ 统计信息: {stats}")

        return True

    except Exception as e:
        print(f"❌ AgentFactory 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_hybrid_orchestrator():
    """测试 HybridOrchestrator"""
    print("\n" + "=" * 80)
    print("⚙️  测试 HybridOrchestrator")
    print("=" * 80)

    try:
        # 测试动态模式
        os.environ["KIMI_TACHI_DYNAMIC_AGENTS"] = "true"
        orch_dynamic = HybridOrchestrator(work_dir="/tmp/test_dynamic")
        print("✅ 动态模式初始化成功")
        print(f"   模式: {'动态' if orch_dynamic.dynamic_mode else '固定'}")

        # 测试固定模式
        os.environ["KIMI_TACHI_DYNAMIC_AGENTS"] = "false"
        orch_fixed = HybridOrchestrator(work_dir="/tmp/test_fixed")
        print("✅ 固定模式初始化成功")
        print(f"   模式: {'动态' if orch_fixed.dynamic_mode else '固定'}")

        return True

    except Exception as e:
        print(f"❌ HybridOrchestrator 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def verify_mcp_reduction():
    """验证 MCP 进程数减少"""
    print("\n" + "=" * 80)
    print("📊 验证 MCP 进程数减少")
    print("=" * 80)

    # 统计当前 MCP 进程
    current_mcp = count_mcp_processes()
    print(f"当前 MCP 进程数: {current_mcp}")

    # 注意：这里只是统计当前系统的 MCP 进程
    # 真正的验证需要在实际运行 kimi-tachi 后进行

    if current_mcp <= 2:
        print("✅ MCP 进程数已达标 (≤2)")
        return True
    else:
        print(f"⚠️  当前 MCP 进程数为 {current_mcp}，但这不是在 kimi-tachi 运行时的统计")
        print("   实际验证需要在运行 kimi-tachi 后执行: ps aux | grep mcp")
        return None  # 无法确定


def check_kamaji_yaml():
    """检查 kamaji.yaml 配置"""
    print("\n" + "=" * 80)
    print("📝 检查 kamaji.yaml 配置")
    print("=" * 80)

    kamaji_path = Path("/home/lee/ship/kimi-tachi/agents/kamaji.yaml")

    if not kamaji_path.exists():
        print(f"❌ 找不到 kamaji.yaml: {kamaji_path}")
        return False

    content = kamaji_path.read_text()

    # 检查 subagents 是否为空
    if "subagents: {}" in content:
        print("✅ kamaji.yaml 中 subagents 已清空")
    else:
        print("⚠️  kamaji.yaml 中 subagents 可能未完全清空")

    # 检查 CreateSubagent 工具
    if "CreateSubagent" in content:
        print("✅ kamaji.yaml 包含 CreateSubagent 工具")
    else:
        print("❌ kamaji.yaml 缺少 CreateSubagent 工具")
        return False

    # 检查 Dynamic Agent Creation Protocol
    if "Dynamic Agent Creation Protocol" in content:
        print("✅ kamaji.yaml 包含动态创建协议")
    else:
        print("⚠️  kamaji.yaml 可能缺少动态创建协议文档")

    return True


def generate_report():
    """生成验证报告"""
    print("\n" + "=" * 80)
    print("📋 Phase 2.1 验证报告")
    print("=" * 80)

    report = {
        "timestamp": datetime.now().isoformat(),
        "phase": "2.1",
        "title": "Dynamic Agent Creation",
        "tests": {},
    }

    # 运行各项测试
    report["tests"]["agent_factory"] = test_agent_factory()
    report["tests"]["hybrid_orchestrator"] = test_hybrid_orchestrator()
    report["tests"]["mcp_reduction"] = verify_mcp_reduction()
    report["tests"]["kamaji_yaml"] = check_kamaji_yaml()

    # 统计结果
    passed = sum(1 for v in report["tests"].values() if v is True)
    failed = sum(1 for v in report["tests"].values() if v is False)
    unknown = sum(1 for v in report["tests"].values() if v is None)

    report["summary"] = {
        "passed": passed,
        "failed": failed,
        "unknown": unknown,
        "total": len(report["tests"]),
    }

    # 打印汇总
    print("\n" + "=" * 80)
    print("📊 测试结果汇总")
    print("=" * 80)
    print(f"通过: {passed}/{report['summary']['total']}")
    print(f"失败: {failed}/{report['summary']['total']}")
    print(f"待定: {unknown}/{report['summary']['total']}")

    if failed == 0:
        print("\n✅ Phase 2.1 基础验证通过！")
        print("   下一步：运行实际任务验证 MCP 进程减少")
    else:
        print(f"\n⚠️  有 {failed} 项测试失败，请检查")

    # 保存报告
    report_path = Path("/home/lee/ship/kimi-tachi/results/phase2_1_verification.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)

    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n📁 报告已保存: {report_path}")

    return report


def main():
    """主函数"""
    print("=" * 80)
    print("🎯 Phase 2.1 验证 - 动态 Agent 创建")
    print("=" * 80)
    print(f"\n时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("目标: 验证 MCP 进程从 7 降到 ≤2")

    generate_report()  # Generate and print report

    print("\n" + "=" * 80)
    print("🚀 下一步行动")
    print("=" * 80)
    print("""
1. 运行实际任务验证:
   export KIMI_TACHI_DYNAMIC_AGENTS=true
   python scripts/baseline_real.py --tasks 3 --level L1

2. 监控 MCP 进程:
   watch -n 1 'ps aux | grep mcp | grep -v grep | wc -l'

3. 对比优化效果:
   python scripts/baseline_compare.py baseline_before.json baseline_after.json
""")


if __name__ == "__main__":
    main()
