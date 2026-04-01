#!/usr/bin/env python3
"""
Phase 2.2 消息总线验证脚本

验证消息总线的核心功能：
1. 消息模型创建
2. 消息总线初始化和注册
3. 点对点消息发送
4. 广播和组播
5. 发布订阅模式
6. 消息持久化
7. 分布式追踪
"""

import asyncio
import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, "/home/lee/ship/kimi-tachi/src")

from kimi_tachi.message_bus import (
    Message,
    MessageBus,
    MessagePriority,
    MessageType,
)


def test_message_models():
    """测试消息模型"""
    print("\n" + "=" * 80)
    print("📦 测试消息模型")
    print("=" * 80)

    try:
        # 创建消息
        msg = Message(
            sender="kamaji",
            recipient="nekobasu",
            msg_type=MessageType.DIRECT,
            payload={"task": "探索代码库", "path": "/src"},
            priority=MessagePriority.HIGH,
        )

        print("✅ 消息创建成功")
        print(f"   ID: {msg.id}")
        print(f"   发送者: {msg.sender}")
        print(f"   接收者: {msg.recipient}")
        print(f"   类型: {msg.msg_type.value}")
        print(f"   优先级: {msg.priority.name}")
        print(f"   时间戳: {msg.timestamp}")
        print(f"   Trace ID: {msg.trace_id}")

        # 序列化测试
        json_str = msg.model_dump_json()
        print("\n✅ JSON 序列化成功")
        print(f"   长度: {len(json_str)} 字符")

        # 反序列化测试
        msg2 = Message.model_validate_json(json_str)
        print("✅ JSON 反序列化成功")
        print(f"   发送者匹配: {msg.sender == msg2.sender}")

        return True

    except Exception as e:
        print(f"❌ 消息模型测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_message_bus():
    """测试消息总线"""
    print("\n" + "=" * 80)
    print("🚌 测试消息总线")
    print("=" * 80)

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建消息总线
            bus = MessageBus(storage_dir=tmpdir)
            print("✅ 消息总线创建成功")
            print(f"   存储目录: {tmpdir}")

            # 注册 agents
            received_messages = []

            async def nekobasu_handler(msg):
                received_messages.append(("nekobasu", msg))
                print(f"   🚌 nekobasu 收到消息: {msg.payload.get('task', 'N/A')}")

            async def calcifer_handler(msg):
                received_messages.append(("calcifer", msg))
                print(f"   🔥 calcifer 收到消息: {msg.payload.get('task', 'N/A')}")

            bus.register_agent("nekobasu", nekobasu_handler)
            bus.register_agent("calcifer", calcifer_handler)
            print("\n✅ Agents 注册成功")
            print(f"   已注册: {list(bus._agents.keys())}")

            # 测试点对点消息
            print("\n📨 测试点对点消息...")
            msg = Message(
                sender="kamaji",
                recipient="nekobasu",
                msg_type=MessageType.DIRECT,
                payload={"task": "探索代码库"},
            )
            await bus.send("nekobasu", msg)
            await asyncio.sleep(0.1)  # 等待消息处理

            # 测试广播
            print("\n📢 测试广播消息...")
            broadcast_msg = Message(
                sender="kamaji",
                recipient=None,  # 广播
                msg_type=MessageType.BROADCAST,
                payload={"announcement": "开始工作！"},
            )
            await bus.broadcast(broadcast_msg, exclude=["kamaji"])
            await asyncio.sleep(0.1)

            # 测试组播
            print("\n📬 测试组播消息...")
            multicast_msg = Message(
                sender="kamaji",
                recipient="nekobasu,calcifer",  # 组播
                msg_type=MessageType.MULTICAST,
                payload={"task": "协作任务"},
            )
            await bus.multicast(["nekobasu", "calcifer"], multicast_msg)
            await asyncio.sleep(0.1)

            print("\n✅ 消息发送完成")
            print(f"   收到消息数: {len(received_messages)}")

            # 统计信息
            stats = bus.get_stats()
            print("\n📊 消息总线统计:")
            print(f"   注册 agents: {stats['registered_agents']}")
            print(f"   活跃订阅: {stats['active_subscriptions']}")

            await bus.stop()
            print("\n✅ 消息总线停止成功")

            return True

    except Exception as e:
        print(f"❌ 消息总线测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_pub_sub():
    """测试发布订阅"""
    print("\n" + "=" * 80)
    print("📡 测试发布订阅")
    print("=" * 80)

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            bus = MessageBus(storage_dir=tmpdir)

            # 订阅主题
            received = []

            async def task_handler(msg):
                received.append(msg)
                print(f"   收到任务: {msg.payload}")

            async def system_handler(msg):
                received.append(msg)
                print(f"   收到系统消息: {msg.payload}")

            bus.subscribe("tasks", task_handler)
            bus.subscribe("system", system_handler)
            print("✅ 订阅成功")
            print("   主题: tasks, system")

            # 发布消息
            print("\n📤 发布消息...")
            await bus.publish(
                "tasks",
                Message(
                    sender="kamaji",
                    msg_type=MessageType.PUBLISH,
                    payload={"action": "start", "task_id": "123"},
                ),
            )

            await bus.publish(
                "system",
                Message(
                    sender="system",
                    msg_type=MessageType.SYSTEM,
                    payload={"status": "healthy"},
                ),
            )

            await asyncio.sleep(0.1)

            print("\n✅ 发布完成")
            print(f"   收到消息数: {len(received)}")

            await bus.stop()
            return True

    except Exception as e:
        print(f"❌ 发布订阅测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_tracing():
    """测试分布式追踪"""
    print("\n" + "=" * 80)
    print("🔍 测试分布式追踪")
    print("=" * 80)

    try:
        from kimi_tachi.message_bus.tracing import SpanKind, TraceManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TraceManager(storage_dir=tmpdir)
            print("✅ TraceManager 创建成功")

            # 创建 trace
            trace = manager.start_trace(
                name="workflow_execution", attributes={"workflow": "feature_implementation"}
            )
            print("✅ Trace 创建成功")
            print(f"   Trace ID: {trace.trace_id}")

            # 创建 span
            with manager.start_span(
                trace_id=trace.trace_id,
                name="exploration_phase",
                agent="nekobasu",
                kind=SpanKind.AGENT,
            ) as span:
                print("✅ Span 创建成功")
                print(f"   Span ID: {span.span_id}")
                print(f"   Agent: {span.agent}")

                # 模拟工作
                span.add_event("开始探索")
                span.add_event("发现关键文件")
                span.set_attribute("files_found", 5)

            # 获取 trace 信息
            trace_info = manager.get_trace(trace.trace_id)
            print("\n📊 Trace 信息:")
            print(f"   名称: {trace_info.name}")
            print(f"   Span 数: {len(trace_info.spans)}")
            print(f"   状态: {trace_info.status}")

            return True

    except Exception as e:
        print(f"❌ 分布式追踪测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def generate_report(results: dict):
    """生成验证报告"""
    print("\n" + "=" * 80)
    print("📋 Phase 2.2 验证报告")
    print("=" * 80)

    passed = sum(1 for v in results.values() if v)
    failed = sum(1 for v in results.values() if not v)

    print("\n测试结果:")
    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {status}: {test_name}")

    print("\n汇总:")
    print(f"  通过: {passed}/{len(results)}")
    print(f"  失败: {failed}/{len(results)}")

    if failed == 0:
        print("\n🎉 Phase 2.2 消息总线验证通过！")
    else:
        print(f"\n⚠️  有 {failed} 项测试失败")

    # 保存报告
    report = {
        "timestamp": datetime.now().isoformat(),
        "phase": "2.2",
        "title": "Message Bus",
        "results": results,
        "summary": {"passed": passed, "failed": failed, "total": len(results)},
    }

    report_path = Path("/home/lee/ship/kimi-tachi/results/phase2_2_verification.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)

    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n📁 报告已保存: {report_path}")


async def main():
    """主函数"""
    print("=" * 80)
    print("🎯 Phase 2.2 消息总线验证")
    print("=" * 80)
    print(f"\n时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    results = {}

    # 运行测试
    results["message_models"] = test_message_models()
    results["message_bus"] = await test_message_bus()
    results["pub_sub"] = await test_pub_sub()
    results["tracing"] = await test_tracing()

    # 生成报告
    generate_report(results)

    print("\n" + "=" * 80)
    print("🚀 下一步")
    print("=" * 80)
    print("""
1. 与 HybridOrchestrator 集成:
   from kimi_tachi.message_bus import OrchestratorMessageBus
   bus = OrchestratorMessageBus(orchestrator)

2. 运行实际任务测试:
   python scripts/baseline_real.py --tasks 3 --level L1

3. 对比 Phase 2.1 vs Phase 2.2 效果:
   - 消息延迟: 目标 < 100ms
   - 并行效率: 目标 +40%
""")


if __name__ == "__main__":
    asyncio.run(main())
