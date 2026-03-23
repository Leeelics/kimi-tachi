"""
Phase 2.2 消息总线核心 (MsgHub)

实现异步消息总线，支持：
- 点对点消息 (send)
- 广播 (broadcast)
- 组播 (multicast)
- 发布订阅 (publish/subscribe)
- 消息持久化
- 执行追踪
- 与 HybridOrchestrator 集成

Author: kimi-tachi Team
Phase: 2.2
"""

from __future__ import annotations

import asyncio
import contextlib
import time
from collections import defaultdict
from collections.abc import Callable, Coroutine
from typing import Any

from .models import (
    AgentRegistration,
    BusStatistics,
    DeliveryStatus,
    Message,
    MessagePriority,
    MessageType,
    Subscription,
)
from .persistence import MessageStore
from .tracing import (
    get_tracer,
    trace_message_deliver,
    trace_message_receive,
    trace_message_send,
)

# 处理器类型别名
MessageHandler = Callable[[Message], Coroutine[Any, Any, None]]


class MessageBusError(Exception):
    """消息总线错误"""

    pass


class AgentNotFoundError(MessageBusError):
    """Agent 未找到错误"""

    pass


class ChannelNotFoundError(MessageBusError):
    """频道未找到错误"""

    pass


class MessageBus:
    """
    消息总线

    实现异步消息传递的核心组件，支持多种通信模式：
    - 点对点 (send): 直接发送给特定 agent
    - 广播 (broadcast): 发送给所有注册的 agent
    - 组播 (multicast): 发送给指定的一组 agent
    - 发布订阅 (publish/subscribe): 基于频道的消息分发

    特性：
    - 异步非阻塞
    - 消息持久化（可选）
    - 分布式追踪
    - 优先级队列
    - 自动重试

    Example:
        >>> bus = MessageBus()
        >>> await bus.start()
        >>>
        >>> # 注册 agent
        >>> await bus.register_agent("calcifer", handler=message_handler)
        >>>
        >>> # 发送消息
        >>> msg = Message.create("Hello!", source="kamaji", target="calcifer")
        >>> await bus.send(msg)
        >>>
        >>> # 发布订阅
        >>> await bus.subscribe("tasks", "calcifer", task_handler)
        >>> await bus.publish(Message.create_publish("New task", "kamaji", "tasks"))
        >>>
        >>> await bus.stop()
    """

    def __init__(
        self,
        enable_persistence: bool = True,
        enable_tracing: bool = True,
        max_queue_size: int = 10000,
        delivery_timeout: float = 30.0,
        retry_interval: float = 5.0,
    ):
        """
        初始化消息总线

        Args:
            enable_persistence: 是否启用消息持久化
            enable_tracing: 是否启用分布式追踪
            max_queue_size: 最大队列大小
            delivery_timeout: 投递超时（秒）
            retry_interval: 重试间隔（秒）
        """
        self.enable_persistence = enable_persistence
        self.enable_tracing = enable_tracing
        self.max_queue_size = max_queue_size
        self.delivery_timeout = delivery_timeout
        self.retry_interval = retry_interval

        # Agent 注册表
        self._agents: dict[str, AgentRegistration] = {}
        self._handlers: dict[str, MessageHandler] = {}

        # 消息队列（按优先级）
        self._queues: dict[MessagePriority, asyncio.Queue[Message]] = {
            priority: asyncio.Queue(maxsize=max_queue_size) for priority in MessagePriority
        }

        # 发布订阅
        self._subscriptions: dict[str, list[Subscription]] = defaultdict(list)

        # 持久化存储
        self._store: MessageStore | None = None
        if enable_persistence:
            self._store = MessageStore()

        # 追踪器
        self._tracer = get_tracer() if enable_tracing else None

        # 统计
        self._stats = BusStatistics()

        # 运行状态
        self._running = False
        self._delivery_task: asyncio.Task | None = None
        self._retry_task: asyncio.Task | None = None
        self._cleanup_task: asyncio.Task | None = None

        # 锁
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        """启动消息总线"""
        if self._running:
            return

        self._running = True

        # 启动投递任务
        self._delivery_task = asyncio.create_task(self._delivery_loop())

        # 启动重试任务
        if self.enable_persistence:
            self._retry_task = asyncio.create_task(self._retry_loop())

        # 启动清理任务
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        print("[MessageBus] Started")

    async def stop(self) -> None:
        """停止消息总线"""
        if not self._running:
            return

        self._running = False

        # 取消任务
        if self._delivery_task:
            self._delivery_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._delivery_task

        if self._retry_task:
            self._retry_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._retry_task

        if self._cleanup_task:
            self._cleanup_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._cleanup_task

        # 关闭存储
        if self._store:
            await self._store.close()

        print("[MessageBus] Stopped")

    # ==================== Agent 管理 ====================

    async def register_agent(
        self,
        agent_id: str,
        agent_type: str = "worker",
        handler: MessageHandler | None = None,
        capabilities: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AgentRegistration:
        """
        注册 agent

        Args:
            agent_id: Agent 唯一标识
            agent_type: Agent 类型
            handler: 消息处理函数
            capabilities: 能力列表
            metadata: 元数据

        Returns:
            AgentRegistration 实例
        """
        async with self._lock:
            registration = AgentRegistration(
                agent_id=agent_id,
                agent_type=agent_type,
                capabilities=capabilities or [],
                metadata=metadata or {},
            )

            self._agents[agent_id] = registration

            if handler:
                self._handlers[agent_id] = handler

            self._stats.registered_agents = len(self._agents)

            print(f"[MessageBus] Agent registered: {agent_id} ({agent_type})")
            return registration

    async def unregister_agent(self, agent_id: str) -> bool:
        """
        注销 agent

        Args:
            agent_id: Agent ID

        Returns:
            是否成功注销
        """
        async with self._lock:
            if agent_id not in self._agents:
                return False

            del self._agents[agent_id]
            self._handlers.pop(agent_id, None)

            # 清理订阅
            for channel, subs in list(self._subscriptions.items()):
                self._subscriptions[channel] = [s for s in subs if s.subscriber_id != agent_id]

            self._stats.registered_agents = len(self._agents)

            print(f"[MessageBus] Agent unregistered: {agent_id}")
            return True

    def get_agent(self, agent_id: str) -> AgentRegistration | None:
        """获取 agent 信息"""
        return self._agents.get(agent_id)

    def list_agents(self) -> list[str]:
        """列出所有已注册 agent"""
        return list(self._agents.keys())

    async def update_heartbeat(self, agent_id: str) -> bool:
        """更新 agent 心跳"""
        if agent_id not in self._agents:
            return False

        self._agents[agent_id].update_heartbeat()
        return True

    # ==================== 消息发送 ====================

    async def send(self, message: Message) -> bool:
        """
        发送点对点消息

        Args:
            message: 消息对象

        Returns:
            是否成功入队
        """
        if not self._running:
            raise MessageBusError("Message bus is not running")

        # 设置消息类型
        message.header.message_type = MessageType.DIRECT

        # 验证目标
        if not message.header.target:
            raise MessageBusError("Direct message requires target")

        # 追踪
        if self.enable_tracing:
            trace_message_send(message)

        # 持久化
        if self._store:
            await self._store.save_message(message)

        # 入队
        success = await self._enqueue(message)

        if success:
            self._stats.record_message(message)

        return success

    async def broadcast(self, message: Message) -> int:
        """
        广播消息给所有 agent

        Args:
            message: 消息对象

        Returns:
            成功投递的 agent 数量
        """
        if not self._running:
            raise MessageBusError("Message bus is not running")

        message.header.message_type = MessageType.BROADCAST

        # 追踪
        if self.enable_tracing:
            trace_message_send(message)

        count = 0
        for agent_id in self._agents:
            if agent_id == message.source:
                continue  # 不发送给自己

            # 创建副本
            msg_copy = message.model_copy(deep=True)
            msg_copy.header.target = agent_id

            # 持久化
            if self._store:
                await self._store.save_message(msg_copy)

            # 入队
            if await self._enqueue(msg_copy):
                count += 1

        self._stats.record_message(message)
        self._stats.messages_by_type["broadcast"] = count

        return count

    async def multicast(self, message: Message, targets: list[str]) -> int:
        """
        组播消息给指定 agent 列表

        Args:
            message: 消息对象
            targets: 目标 agent ID 列表

        Returns:
            成功投递的 agent 数量
        """
        if not self._running:
            raise MessageBusError("Message bus is not running")

        message.header.message_type = MessageType.MULTICAST
        message.header.targets = targets

        # 追踪
        if self.enable_tracing:
            trace_message_send(message)

        count = 0
        for agent_id in targets:
            if agent_id not in self._agents:
                continue

            # 创建副本
            msg_copy = message.model_copy(deep=True)
            msg_copy.header.target = agent_id

            # 持久化
            if self._store:
                await self._store.save_message(msg_copy)

            # 入队
            if await self._enqueue(msg_copy):
                count += 1

        self._stats.record_message(message)
        self._stats.messages_by_type["multicast"] = count

        return count

    # ==================== 发布订阅 ====================

    async def subscribe(
        self,
        channel: str,
        subscriber_id: str,
        callback: MessageHandler,
        filter_pattern: str | None = None,
    ) -> Subscription:
        """
        订阅频道

        Args:
            channel: 频道名称
            subscriber_id: 订阅者 agent ID
            callback: 消息回调函数
            filter_pattern: 过滤模式（可选）

        Returns:
            Subscription 实例
        """
        async with self._lock:
            subscription = Subscription(
                channel=channel,
                subscriber_id=subscriber_id,
                callback=callback,
                filter_pattern=filter_pattern,
            )

            self._subscriptions[channel].append(subscription)
            self._stats.active_subscriptions = sum(
                len(subs) for subs in self._subscriptions.values()
            )

            print(f"[MessageBus] {subscriber_id} subscribed to {channel}")
            return subscription

    async def unsubscribe(self, channel: str, subscriber_id: str) -> bool:
        """
        取消订阅

        Args:
            channel: 频道名称
            subscriber_id: 订阅者 agent ID

        Returns:
            是否成功取消
        """
        async with self._lock:
            if channel not in self._subscriptions:
                return False

            original_len = len(self._subscriptions[channel])
            self._subscriptions[channel] = [
                s for s in self._subscriptions[channel] if s.subscriber_id != subscriber_id
            ]

            if len(self._subscriptions[channel]) < original_len:
                self._stats.active_subscriptions = sum(
                    len(subs) for subs in self._subscriptions.values()
                )
                print(f"[MessageBus] {subscriber_id} unsubscribed from {channel}")
                return True

            return False

    async def publish(self, message: Message) -> int:
        """
        发布消息到频道

        Args:
            message: 消息对象（需设置 channel）

        Returns:
            成功投递的订阅者数量
        """
        if not self._running:
            raise MessageBusError("Message bus is not running")

        if not message.header.channel:
            raise MessageBusError("Publish message requires channel")

        channel = message.header.channel
        message.header.message_type = MessageType.PUBLISH

        # 追踪
        if self.enable_tracing:
            trace_message_send(message)

        # 持久化
        if self._store:
            await self._store.save_message(message)

        # 分发给订阅者
        count = 0
        async with self._lock:
            subscriptions = list(self._subscriptions.get(channel, []))

        for sub in subscriptions:
            if not sub.matches(message):
                continue

            # 创建副本
            msg_copy = message.model_copy(deep=True)
            msg_copy.header.target = sub.subscriber_id

            # 入队
            if await self._enqueue(msg_copy):
                count += 1
                sub.messages_received += 1

        self._stats.record_message(message)
        self._stats.messages_by_type["publish"] = count

        return count

    # ==================== 内部方法 ====================

    async def _enqueue(self, message: Message) -> bool:
        """将消息入队"""
        queue = self._queues[message.header.priority]

        try:
            queue.put_nowait(message)
            return True
        except asyncio.QueueFull:
            print(f"[MessageBus] Queue full for priority {message.header.priority}")
            return False

    async def _delivery_loop(self) -> None:
        """消息投递主循环"""
        while self._running:
            message = None

            # 按优先级从高到低处理
            for priority in MessagePriority:
                try:
                    message = self._queues[priority].get_nowait()
                    break
                except asyncio.QueueEmpty:
                    continue

            if message is None:
                # 所有队列都空，等待一下
                await asyncio.sleep(0.01)
                continue

            # 投递消息
            await self._deliver_message(message)

    async def _deliver_message(self, message: Message) -> bool:
        """投递单个消息"""
        start_time = time.time()

        # 检查过期
        if message.header.is_expired():
            message.mark_expired()
            if self._store:
                await self._store.update_status(message.message_id, DeliveryStatus.EXPIRED)
            self._stats.record_expired()
            return False

        target = message.header.target

        # 检查目标
        if target and target not in self._agents:
            # 目标不存在
            message.mark_failed(f"Agent not found: {target}")
            if self._store:
                await self._store.update_status(
                    message.message_id, DeliveryStatus.FAILED, message.error_info
                )

            latency = (time.time() - start_time) * 1000
            self._stats.record_delivery(latency, success=False)
            return False

        # 获取处理器
        handler = self._handlers.get(target) if target else None

        success = False
        error_info = None

        if handler:
            # 追踪
            span = None
            if self.enable_tracing:
                span = trace_message_receive(message, target)

            try:
                # 设置超时
                await asyncio.wait_for(
                    handler(message),
                    timeout=self.delivery_timeout,
                )
                success = True
                message.mark_acknowledged()

                if self._agents.get(target):
                    self._agents[target].messages_received += 1

            except TimeoutError:
                error_info = f"Delivery timeout after {self.delivery_timeout}s"
                message.mark_failed(error_info)

                # 检查是否需要重试
                if message.should_retry():
                    message.increment_retry()
                    await self._enqueue(message)
                    return False

            except Exception as e:
                error_info = str(e)
                message.mark_failed(error_info)

            finally:
                if span:
                    status = "ok" if success else "error"
                    self._tracer.end_span(span.span_id, status, error_info)

        else:
            # 没有处理器，只是标记为已投递
            message.mark_delivered()
            success = True

        # 更新状态
        if self._store:
            if success:
                await self._store.update_status(
                    message.message_id,
                    DeliveryStatus.ACKNOWLEDGED
                    if message.acknowledged_at
                    else DeliveryStatus.DELIVERED,
                )
            else:
                await self._store.update_status(
                    message.message_id, DeliveryStatus.FAILED, error_info
                )

        # 追踪
        if self.enable_tracing:
            trace_message_deliver(message, target or "unknown", success)

        # 统计
        latency = (time.time() - start_time) * 1000
        self._stats.record_delivery(latency, success)

        return success

    async def _retry_loop(self) -> None:
        """重试循环"""
        while self._running:
            await asyncio.sleep(self.retry_interval)

            if not self._store:
                continue

            # 获取待处理消息
            pending = await self._store.get_pending_messages(
                limit=100,
                max_age_seconds=300,
            )

            for message in pending:
                if message.should_retry():
                    message.increment_retry()
                    await self._enqueue(message)

    async def _cleanup_loop(self) -> None:
        """清理循环"""
        while self._running:
            await asyncio.sleep(60)  # 每分钟检查一次

            # 清理不活跃的 agent
            inactive = []
            for agent_id, agent in self._agents.items():
                if not agent.is_alive(timeout=120):
                    inactive.append(agent_id)

            for agent_id in inactive:
                await self.unregister_agent(agent_id)
                print(f"[MessageBus] Removed inactive agent: {agent_id}")

    # ==================== 查询方法 ====================

    async def get_message(self, message_id: str) -> Message | None:
        """获取消息"""
        if self._store:
            return await self._store.get_message(message_id)
        return None

    async def get_pending_messages(self, agent_id: str) -> list[Message]:
        """获取 agent 的待处理消息"""
        if self._store:
            return await self._store.get_messages_for_target(agent_id, DeliveryStatus.PENDING)
        return []

    async def get_message_history(
        self,
        trace_id: str,
        limit: int = 100,
    ) -> list[Message]:
        """获取追踪链上的消息历史"""
        if self._store:
            return await self._store.get_messages_by_trace(trace_id, limit)
        return []

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息"""
        return self._stats.to_dict()

    async def get_storage_statistics(self) -> dict[str, Any] | None:
        """获取存储统计信息"""
        if self._store:
            return await self._store.get_statistics()
        return None


# ==================== HybridOrchestrator 集成 ====================


class OrchestratorMessageBus:
    """
    与 HybridOrchestrator 集成的消息总线适配器

    提供与现有 orchestrator 兼容的接口。
    """

    def __init__(
        self,
        orchestrator: Any,
        enable_persistence: bool = True,
        enable_tracing: bool = True,
    ):
        """
        初始化适配器

        Args:
            orchestrator: HybridOrchestrator 实例
            enable_persistence: 是否启用持久化
            enable_tracing: 是否启用追踪
        """
        self.orchestrator = orchestrator
        self.bus = MessageBus(
            enable_persistence=enable_persistence,
            enable_tracing=enable_tracing,
        )

        self._agent_map: dict[str, str] = {
            "kamaji": "coordinator",
            "shishigami": "architect",
            "nekobasu": "explorer",
            "calcifer": "builder",
            "enma": "reviewer",
            "tasogare": "planner",
            "phoenix": "librarian",
        }

    async def start(self) -> None:
        """启动总线并注册所有 agent"""
        await self.bus.start()

        # 注册所有已知 agent
        for agent_id, agent_type in self._agent_map.items():
            await self.bus.register_agent(
                agent_id=agent_id,
                agent_type=agent_type,
                handler=self._create_handler(agent_id),
            )

    async def stop(self) -> None:
        """停止总线"""
        await self.bus.stop()

    def _create_handler(self, agent_id: str) -> MessageHandler:
        """创建 agent 消息处理器"""

        async def handler(message: Message) -> None:
            """处理消息并委托给 agent"""
            content = message.body.content

            # 构建上下文
            context = ""
            if message.header.correlation_id:
                context += f"Related to: {message.header.correlation_id}\n"
            if message.header.metadata:
                context += f"Metadata: {message.header.metadata}\n"

            # 使用 orchestrator 委托任务
            # 注意：这里假设 orchestrator 有 delegate 方法
            if hasattr(self.orchestrator, "delegate"):
                await self.orchestrator.delegate(
                    agent=agent_id,
                    task=str(content),
                    context=context,
                )

        return handler

    async def send_to_agent(
        self,
        agent_id: str,
        content: Any,
        source: str = "kamaji",
        **kwargs: Any,
    ) -> bool:
        """
        发送消息给指定 agent

        Args:
            agent_id: 目标 agent ID
            content: 消息内容
            source: 来源 agent ID
            **kwargs: 额外参数

        Returns:
            是否发送成功
        """
        message = Message.create(
            content=content,
            source=source,
            target=agent_id,
            **kwargs,
        )
        return await self.bus.send(message)

    async def broadcast_to_all(
        self,
        content: Any,
        source: str = "kamaji",
        **kwargs: Any,
    ) -> int:
        """
        广播给所有 agent

        Args:
            content: 消息内容
            source: 来源 agent ID
            **kwargs: 额外参数

        Returns:
            成功投递的数量
        """
        message = Message.create_broadcast(
            content=content,
            source=source,
            **kwargs,
        )
        return await self.bus.broadcast(message)

    async def multicast_to_agents(
        self,
        content: Any,
        targets: list[str],
        source: str = "kamaji",
        **kwargs: Any,
    ) -> int:
        """
        组播给指定 agents

        Args:
            content: 消息内容
            targets: 目标 agent ID 列表
            source: 来源 agent ID
            **kwargs: 额外参数

        Returns:
            成功投递的数量
        """
        message = Message.create_multicast(
            content=content,
            source=source,
            targets=targets,
            **kwargs,
        )
        return await self.bus.multicast(message, targets)

    async def publish_event(
        self,
        channel: str,
        content: Any,
        source: str = "kamaji",
        **kwargs: Any,
    ) -> int:
        """
        发布事件到频道

        Args:
            channel: 频道名称
            content: 消息内容
            source: 来源 agent ID
            **kwargs: 额外参数

        Returns:
            成功投递的订阅者数量
        """
        message = Message.create_publish(
            content=content,
            source=source,
            channel=channel,
            **kwargs,
        )
        return await self.bus.publish(message)

    async def subscribe_to_channel(
        self,
        channel: str,
        agent_id: str,
        callback: MessageHandler | None = None,
    ) -> Subscription:
        """
        订阅频道

        Args:
            channel: 频道名称
            agent_id: 订阅者 agent ID
            callback: 回调函数（可选，默认使用 agent 处理器）

        Returns:
            Subscription 实例
        """
        if callback is None:
            callback = self._create_handler(agent_id)

        return await self.bus.subscribe(channel, agent_id, callback)

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息"""
        return self.bus.get_statistics()
