"""
Phase 2.2 消息总线测试

测试消息总线的核心功能：
- 消息创建和序列化
- 点对点消息
- 广播
- 组播
- 发布订阅
- 持久化
- 追踪
"""

import asyncio

import pytest

from kimi_tachi.message_bus import (
    DeliveryStatus,
    Message,
    MessageBus,
    MessagePriority,
    MessageStore,
    MessageType,
    get_tracer,
)

# ==================== 模型测试 ====================


class TestMessageModel:
    """测试消息模型"""

    def test_create_direct_message(self):
        """测试创建点对点消息"""
        msg = Message.create(
            content={"task": "test"},
            source="kamaji",
            target="calcifer",
            priority=MessagePriority.HIGH,
        )

        assert msg.source == "kamaji"
        assert msg.header.target == "calcifer"
        assert msg.message_type == MessageType.DIRECT
        assert msg.header.priority == MessagePriority.HIGH
        assert msg.body.content == {"task": "test"}
        assert msg.delivery_status == DeliveryStatus.PENDING

    def test_create_broadcast(self):
        """测试创建广播消息"""
        msg = Message.create_broadcast(
            content="Hello all!",
            source="kamaji",
        )

        assert msg.message_type == MessageType.BROADCAST
        assert msg.source == "kamaji"
        assert msg.body.content == "Hello all!"

    def test_create_multicast(self):
        """测试创建组播消息"""
        msg = Message.create_multicast(
            content="Hello group!",
            source="kamaji",
            targets=["calcifer", "enma"],
        )

        assert msg.message_type == MessageType.MULTICAST
        assert msg.header.targets == ["calcifer", "enma"]

    def test_create_publish(self):
        """测试创建发布消息"""
        msg = Message.create_publish(
            content="New event!",
            source="kamaji",
            channel="events",
        )

        assert msg.message_type == MessageType.PUBLISH
        assert msg.header.channel == "events"

    def test_create_reply(self):
        """测试创建回复消息"""
        original = Message.create(
            content="Original",
            source="kamaji",
            target="calcifer",
        )

        reply = Message.create_reply(
            original_message=original,
            content="Reply",
            source="calcifer",
        )

        assert reply.message_type == MessageType.REPLY
        assert reply.header.correlation_id == original.message_id
        assert reply.header.target == original.source

    def test_message_status_transitions(self):
        """测试消息状态转换"""
        msg = Message.create("test", source="kamaji", target="calcifer")

        assert msg.delivery_status == DeliveryStatus.PENDING

        msg.mark_delivered()
        assert msg.delivery_status == DeliveryStatus.DELIVERED
        assert msg.delivered_at is not None

        msg.mark_acknowledged()
        assert msg.delivery_status == DeliveryStatus.ACKNOWLEDGED
        assert msg.acknowledged_at is not None

    def test_message_retry(self):
        """测试消息重试"""
        msg = Message.create("test", source="kamaji", target="calcifer")
        msg.header.max_retries = 3

        assert not msg.should_retry()  # 未失败时不重试

        msg.mark_failed("error")
        assert msg.should_retry()

        msg.increment_retry()
        assert msg.header.retry_count == 1
        assert msg.should_retry()

        # 达到最大重试次数
        msg.header.retry_count = 3
        assert not msg.should_retry()

    def test_message_expiration(self):
        """测试消息过期"""

        msg = Message.create("test", source="kamaji", target="calcifer")
        msg.header.ttl = 0  # 立即过期

        assert msg.header.is_expired()

    def test_message_serialization(self):
        """测试消息序列化"""
        msg = Message.create(
            content={"key": "value"},
            source="kamaji",
            target="calcifer",
            metadata={"extra": "data"},
        )

        storage_dict = msg.to_storage_dict()

        assert storage_dict["header"]["source"] == "kamaji"
        assert storage_dict["body"]["content"] == '{"key": "value"}'
        assert storage_dict["delivery_status"] == "pending"


# ==================== 消息总线测试 ====================


@pytest.mark.asyncio
class TestMessageBus:
    """测试消息总线"""

    async def test_start_stop(self):
        """测试启动和停止"""
        bus = MessageBus(enable_persistence=False, enable_tracing=False)

        await bus.start()
        assert bus._running

        await bus.stop()
        assert not bus._running

    async def test_register_unregister_agent(self):
        """测试注册和注销 agent"""
        bus = MessageBus(enable_persistence=False, enable_tracing=False)
        await bus.start()

        async def handler(msg):
            pass

        # 注册
        reg = await bus.register_agent(
            agent_id="test_agent",
            agent_type="tester",
            handler=handler,
            capabilities=["test"],
        )

        assert reg.agent_id == "test_agent"
        assert reg.agent_type == "tester"
        assert "test_agent" in bus.list_agents()

        # 注销
        success = await bus.unregister_agent("test_agent")
        assert success
        assert "test_agent" not in bus.list_agents()

        await bus.stop()

    async def test_send_message(self):
        """测试点对点消息"""
        bus = MessageBus(enable_persistence=False, enable_tracing=False)
        await bus.start()

        received = []

        async def handler(msg):
            received.append(msg)

        await bus.register_agent("receiver", handler=handler)

        msg = Message.create(
            content="Hello!",
            source="sender",
            target="receiver",
        )

        success = await bus.send(msg)
        assert success

        # 等待投递
        await asyncio.sleep(0.1)

        assert len(received) == 1
        assert received[0].body.content == "Hello!"

        await bus.stop()

    async def test_broadcast(self):
        """测试广播"""
        bus = MessageBus(enable_persistence=False, enable_tracing=False)
        await bus.start()

        received1 = []
        received2 = []

        async def handler1(msg):
            received1.append(msg)

        async def handler2(msg):
            received2.append(msg)

        await bus.register_agent("agent1", handler=handler1)
        await bus.register_agent("agent2", handler=handler2)

        msg = Message.create_broadcast(
            content="Broadcast!",
            source="sender",
        )

        count = await bus.broadcast(msg)
        assert count == 2

        # 等待投递
        await asyncio.sleep(0.1)

        assert len(received1) == 1
        assert len(received2) == 1

        await bus.stop()

    async def test_multicast(self):
        """测试组播"""
        bus = MessageBus(enable_persistence=False, enable_tracing=False)
        await bus.start()

        received1 = []
        received2 = []
        received3 = []

        async def handler1(msg):
            received1.append(msg)

        async def handler2(msg):
            received2.append(msg)

        async def handler3(msg):
            received3.append(msg)

        await bus.register_agent("agent1", handler=handler1)
        await bus.register_agent("agent2", handler=handler2)
        await bus.register_agent("agent3", handler=handler3)

        msg = Message.create_multicast(
            content="Multicast!",
            source="sender",
            targets=["agent1", "agent2"],  # 不包括 agent3
        )

        count = await bus.multicast(msg, ["agent1", "agent2"])
        assert count == 2

        # 等待投递
        await asyncio.sleep(0.1)

        assert len(received1) == 1
        assert len(received2) == 1
        assert len(received3) == 0

        await bus.stop()

    async def test_publish_subscribe(self):
        """测试发布订阅"""
        bus = MessageBus(enable_persistence=False, enable_tracing=False)
        await bus.start()

        received = []

        async def handler(msg):
            received.append(msg)

        await bus.register_agent("subscriber", handler=handler)
        await bus.subscribe("test_channel", "subscriber", handler)

        msg = Message.create_publish(
            content="Published!",
            source="publisher",
            channel="test_channel",
        )

        count = await bus.publish(msg)
        assert count == 1

        # 等待投递
        await asyncio.sleep(0.1)

        assert len(received) == 1
        assert received[0].body.content == "Published!"

        # 取消订阅
        success = await bus.unsubscribe("test_channel", "subscriber")
        assert success

        # 再次发布
        msg2 = Message.create_publish(
            content="After unsubscribe",
            source="publisher",
            channel="test_channel",
        )
        count = await bus.publish(msg2)
        assert count == 0

        await bus.stop()

    async def test_message_priority(self):
        """测试消息优先级"""
        bus = MessageBus(enable_persistence=False, enable_tracing=False)
        await bus.start()

        received = []

        async def handler(msg):
            received.append(msg.header.priority)

        await bus.register_agent("receiver", handler=handler)

        # 按低优先级顺序发送
        await bus.send(
            Message.create(
                content="low",
                source="sender",
                target="receiver",
                priority=MessagePriority.LOW,
            )
        )
        await bus.send(
            Message.create(
                content="high",
                source="sender",
                target="receiver",
                priority=MessagePriority.HIGH,
            )
        )
        await bus.send(
            Message.create(
                content="critical",
                source="sender",
                target="receiver",
                priority=MessagePriority.CRITICAL,
            )
        )

        # 等待投递
        await asyncio.sleep(0.2)

        # 验证按优先级顺序处理
        assert received[0] == MessagePriority.CRITICAL
        assert received[1] == MessagePriority.HIGH
        assert received[2] == MessagePriority.LOW

        await bus.stop()

    async def test_statistics(self):
        """测试统计信息"""
        bus = MessageBus(enable_persistence=False, enable_tracing=False)
        await bus.start()

        async def handler(msg):
            pass

        await bus.register_agent("agent", handler=handler)

        # 发送消息
        await bus.send(Message.create("test", source="s", target="agent"))
        await bus.broadcast(Message.create_broadcast("broadcast", source="s"))

        # 等待投递
        await asyncio.sleep(0.1)

        stats = bus.get_statistics()

        assert stats["messages"]["total"] >= 2
        assert stats["agents"]["registered"] == 1
        assert stats["delivery"]["delivered"] >= 2

        await bus.stop()


# ==================== 持久化测试 ====================


@pytest.mark.asyncio
class TestMessageStore:
    """测试消息存储"""

    async def test_save_and_get(self, tmp_path):
        """测试保存和获取消息"""
        db_path = tmp_path / "test.db"
        store = MessageStore(db_path=db_path)

        msg = Message.create(
            content={"test": "data"},
            source="sender",
            target="receiver",
        )

        # 保存
        success = await store.save_message(msg)
        assert success

        # 获取
        retrieved = await store.get_message(msg.message_id)
        assert retrieved is not None
        assert retrieved.body.content == {"test": "data"}
        assert retrieved.source == "sender"

        await store.close()

    async def test_update_status(self, tmp_path):
        """测试更新状态"""
        db_path = tmp_path / "test.db"
        store = MessageStore(db_path=db_path)

        msg = Message.create("test", source="s", target="r")
        await store.save_message(msg)

        # 更新为已投递
        success = await store.update_status(msg.message_id, DeliveryStatus.DELIVERED)
        assert success

        retrieved = await store.get_message(msg.message_id)
        assert retrieved.delivery_status == DeliveryStatus.DELIVERED
        assert retrieved.delivered_at is not None

        await store.close()

    async def test_get_by_trace(self, tmp_path):
        """测试按追踪ID获取"""
        db_path = tmp_path / "test.db"
        store = MessageStore(db_path=db_path)

        trace_id = "test-trace-123"

        msg1 = Message.create("msg1", source="s", target="r1", trace_id=trace_id)
        msg2 = Message.create("msg2", source="s", target="r2", trace_id=trace_id)
        msg3 = Message.create("msg3", source="s", target="r3")  # 不同 trace

        await store.save_message(msg1)
        await store.save_message(msg2)
        await store.save_message(msg3)

        messages = await store.get_messages_by_trace(trace_id)
        assert len(messages) == 2

        await store.close()

    async def test_delivery_log(self, tmp_path):
        """测试投递日志"""
        db_path = tmp_path / "test.db"
        store = MessageStore(db_path=db_path)

        msg = Message.create("test", source="s", target="r")
        await store.save_message(msg)

        # 记录投递
        await store.log_delivery(msg.message_id, "agent1", "delivered")
        await store.log_delivery(msg.message_id, "agent1", "acknowledged")

        log = await store.get_delivery_log(msg.message_id)
        assert len(log) == 2
        assert log[0]["status"] == "delivered"
        assert log[1]["status"] == "acknowledged"

        await store.close()

    async def test_statistics(self, tmp_path):
        """测试存储统计"""
        db_path = tmp_path / "test.db"
        store = MessageStore(db_path=db_path)

        # 保存不同类型的消息
        await store.save_message(Message.create("d1", source="s", target="r"))
        await store.save_message(Message.create_broadcast("b1", source="s"))
        await store.save_message(Message.create_publish("p1", source="s", channel="c"))

        stats = await store.get_statistics()

        assert stats["total_messages"] == 3
        assert "direct" in stats["by_type"]
        assert "broadcast" in stats["by_type"]
        assert "publish" in stats["by_type"]

        await store.close()


# ==================== 追踪测试 ====================


@pytest.mark.asyncio
class TestTracing:
    """测试分布式追踪"""

    async def test_trace_creation(self):
        """测试追踪创建"""
        tracer = get_tracer()

        trace = tracer.start_trace("test-operation")

        assert trace.trace_id is not None
        assert trace.root_span_id is not None
        assert len(trace.spans) == 1

        tracer.end_trace(trace.trace_id)

    async def test_span_hierarchy(self):
        """测试 Span 层级"""
        tracer = get_tracer()

        trace = tracer.start_trace("root-operation")
        root_span = trace.get_root_span()

        # 创建子 Span
        child1 = tracer.start_span("child1")
        child2 = tracer.start_span("child2", parent_span_id=root_span.span_id)

        assert child1.parent_span_id == root_span.span_id
        assert child2.parent_span_id == root_span.span_id

        tracer.end_span(child1.span_id)
        tracer.end_span(child2.span_id)
        tracer.end_trace(trace.trace_id)

    async def test_span_context_manager(self):
        """测试 Span 上下文管理器"""
        tracer = get_tracer()

        async with tracer.trace("test-trace") as trace:
            async with tracer.span("operation1") as span1:
                span1.set_attribute("key", "value")

            async with tracer.span("operation2") as span2:
                span2.add_event("event1", {"data": "test"})

        # 验证追踪已结束
        assert trace.end_time is not None
        assert len(trace.spans) == 3  # root + 2 children

    async def test_message_tracing(self):
        """测试消息追踪"""
        from kimi_tachi.message_bus.tracing import (
            trace_message_receive,
            trace_message_send,
        )

        msg = Message.create("test", source="sender", target="receiver")

        # 发送追踪
        trace_message_send(msg)
        assert msg.header.trace_id is not None

        # 接收追踪
        span = trace_message_receive(msg, "receiver")
        assert span is not None
        assert span.name == "message.receive"


# ==================== 集成测试 ====================


@pytest.mark.asyncio
class TestIntegration:
    """集成测试"""

    async def test_full_workflow(self, tmp_path):
        """测试完整工作流"""
        db_path = tmp_path / "workflow.db"

        # 创建带持久化的总线
        bus = MessageBus(
            enable_persistence=True,
            enable_tracing=True,
        )
        bus._store = MessageStore(db_path=db_path)
        bus._store._init_db()

        await bus.start()

        # 记录接收的消息
        received_messages = []

        async def handler(msg):
            received_messages.append(
                {
                    "id": msg.message_id,
                    "content": msg.body.content,
                    "type": msg.message_type.value,
                }
            )

        # 注册 agents
        await bus.register_agent("coordinator", handler=handler)
        await bus.register_agent("worker1", handler=handler)
        await bus.register_agent("worker2", handler=handler)

        # 订阅频道
        await bus.subscribe("tasks", "worker1", handler)
        await bus.subscribe("tasks", "worker2", handler)

        # 1. 点对点
        await bus.send(
            Message.create(
                content="Direct task",
                source="coordinator",
                target="worker1",
            )
        )

        # 2. 广播
        await bus.broadcast(
            Message.create_broadcast(
                content="Broadcast message",
                source="coordinator",
            )
        )

        # 3. 组播
        await bus.multicast(
            Message.create_multicast(
                content="Multicast message",
                source="coordinator",
                targets=["worker1", "worker2"],
            ),
            targets=["worker1", "worker2"],
        )

        # 4. 发布订阅
        await bus.publish(
            Message.create_publish(
                content="Task published",
                source="coordinator",
                channel="tasks",
            )
        )

        # 等待所有消息处理
        await asyncio.sleep(0.5)

        # 验证结果
        # coordinator 收到广播 (1)
        # worker1 收到 direct (1) + 广播 (1) + 组播 (1) + 订阅 (1) = 4
        # worker2 收到广播 (1) + 组播 (1) + 订阅 (1) = 3

        coordinator_msgs = [m for m in received_messages if m["content"] == "Broadcast message"]
        worker1_direct = [m for m in received_messages if m["content"] == "Direct task"]
        task_msgs = [m for m in received_messages if m["content"] == "Task published"]

        assert len(coordinator_msgs) == 1  # 广播（不包括自己）
        assert len(worker1_direct) == 1
        assert len(task_msgs) == 2  # 两个订阅者

        # 验证持久化
        stats = await bus.get_storage_statistics()
        assert stats is not None
        assert stats["total_messages"] >= 7

        await bus.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
