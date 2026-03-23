"""
Phase 2.2 消息总线数据模型

消息模型使用 Pydantic 实现，提供强类型验证和序列化支持。
支持多种消息类型：点对点、广播、组播、发布订阅。

Author: kimi-tachi Team
Phase: 2.2
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable, Coroutine
from enum import Enum, StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class MessageType(StrEnum):
    """消息类型枚举"""

    DIRECT = "direct"  # 点对点消息
    BROADCAST = "broadcast"  # 广播消息
    MULTICAST = "multicast"  # 组播消息
    PUBLISH = "publish"  # 发布订阅
    REPLY = "reply"  # 回复消息
    SYSTEM = "system"  # 系统消息
    ERROR = "error"  # 错误消息


class MessagePriority(int, Enum):
    """消息优先级"""

    CRITICAL = 0  # 关键 - 立即处理
    HIGH = 1  # 高优先级
    NORMAL = 2  # 普通
    LOW = 3  # 低优先级
    BACKGROUND = 4  # 后台任务


class DeliveryStatus(StrEnum):
    """消息投递状态"""

    PENDING = "pending"  # 待投递
    DELIVERED = "delivered"  # 已投递
    ACKNOWLEDGED = "acknowledged"  # 已确认
    FAILED = "failed"  # 投递失败
    EXPIRED = "expired"  # 已过期


class MessageHeader(BaseModel):
    """消息头部信息"""

    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: str | None = None  # 关联消息ID（用于追踪请求-响应链）
    trace_id: str | None = None  # 分布式追踪ID
    parent_span_id: str | None = None  # 父 span ID
    span_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:16])

    source: str = "unknown"  # 消息来源（agent ID）
    timestamp: float = Field(default_factory=time.time)
    ttl: int = 300  # 消息生存时间（秒）

    # 优先级和重试
    priority: MessagePriority = MessagePriority.NORMAL
    retry_count: int = 0
    max_retries: int = 3

    # 路由信息
    message_type: MessageType = MessageType.DIRECT
    target: str | None = None  # 目标 agent（点对点）
    targets: list[str] | None = None  # 目标列表（组播）
    channel: str | None = None  # 频道（发布订阅）

    # 元数据
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: float) -> float:
        """确保时间戳有效"""
        if v <= 0:
            return time.time()
        return v

    def is_expired(self) -> bool:
        """检查消息是否过期"""
        return time.time() - self.timestamp > self.ttl

    def to_log_dict(self) -> dict[str, Any]:
        """转换为日志友好的字典"""
        return {
            "message_id": self.message_id[:8],
            "trace_id": self.trace_id[:8] if self.trace_id else None,
            "span_id": self.span_id[:8],
            "source": self.source,
            "type": self.message_type.value,
            "priority": self.priority.name,
        }


class MessageBody(BaseModel):
    """消息体"""

    # 主要内容
    content: Any = None
    content_type: str = "application/json"
    encoding: str = "utf-8"

    # 序列化后的内容（用于持久化）
    serialized: str | None = None

    # 附件/引用
    attachments: list[dict[str, Any]] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)  # 引用的文件/资源

    def model_dump_for_storage(self) -> dict[str, Any]:
        """序列化为存储格式"""
        return {
            "content": self._serialize_content(),
            "content_type": self.content_type,
            "encoding": self.encoding,
            "attachments": self.attachments,
            "references": self.references,
        }

    def _serialize_content(self) -> str:
        """序列化内容"""
        import json

        if self.serialized:
            return self.serialized

        if isinstance(self.content, str):
            return self.content

        try:
            return json.dumps(self.content, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            return str(self.content)


class Message(BaseModel):
    """
    完整消息对象

    包含头部和消息体，支持序列化和反序列化。
    """

    header: MessageHeader = Field(default_factory=MessageHeader)
    body: MessageBody = Field(default_factory=MessageBody)

    # 投递状态（运行时）
    delivery_status: DeliveryStatus = DeliveryStatus.PENDING
    delivered_at: float | None = None
    acknowledged_at: float | None = None
    error_info: str | None = None

    class Config:
        arbitrary_types_allowed = True

    @classmethod
    def create(
        cls,
        content: Any,
        source: str,
        message_type: MessageType = MessageType.DIRECT,
        target: str | None = None,
        priority: MessagePriority = MessagePriority.NORMAL,
        correlation_id: str | None = None,
        trace_id: str | None = None,
        channel: str | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Message:
        """
        创建新消息的便捷方法

        Args:
            content: 消息内容
            source: 消息来源 agent ID
            message_type: 消息类型
            target: 目标 agent ID（点对点）
            priority: 优先级
            correlation_id: 关联消息ID
            trace_id: 追踪ID
            channel: 发布订阅频道
            metadata: 额外元数据
            **kwargs: 其他头部参数

        Returns:
            Message 实例
        """
        header = MessageHeader(
            source=source,
            message_type=message_type,
            target=target,
            priority=priority,
            correlation_id=correlation_id,
            trace_id=trace_id,
            channel=channel,
            metadata=metadata or {},
            **kwargs,
        )

        body = MessageBody(content=content)

        return cls(header=header, body=body)

    @classmethod
    def create_reply(
        cls,
        original_message: Message,
        content: Any,
        source: str,
        **kwargs: Any,
    ) -> Message:
        """
        创建回复消息

        Args:
            original_message: 原始消息
            content: 回复内容
            source: 回复者 agent ID
            **kwargs: 其他参数

        Returns:
            Message 实例
        """
        return cls.create(
            content=content,
            source=source,
            message_type=MessageType.REPLY,
            target=original_message.header.source,
            correlation_id=original_message.header.message_id,
            trace_id=original_message.header.trace_id,
            priority=original_message.header.priority,
            **kwargs,
        )

    @classmethod
    def create_broadcast(
        cls,
        content: Any,
        source: str,
        priority: MessagePriority = MessagePriority.NORMAL,
        **kwargs: Any,
    ) -> Message:
        """创建广播消息"""
        return cls.create(
            content=content,
            source=source,
            message_type=MessageType.BROADCAST,
            priority=priority,
            **kwargs,
        )

    @classmethod
    def create_multicast(
        cls,
        content: Any,
        source: str,
        targets: list[str],
        priority: MessagePriority = MessagePriority.NORMAL,
        **kwargs: Any,
    ) -> Message:
        """创建组播消息"""
        return cls.create(
            content=content,
            source=source,
            message_type=MessageType.MULTICAST,
            priority=priority,
            targets=targets,
            **kwargs,
        )

    @classmethod
    def create_publish(
        cls,
        content: Any,
        source: str,
        channel: str,
        priority: MessagePriority = MessagePriority.NORMAL,
        **kwargs: Any,
    ) -> Message:
        """创建发布订阅消息"""
        return cls.create(
            content=content,
            source=source,
            message_type=MessageType.PUBLISH,
            channel=channel,
            priority=priority,
            **kwargs,
        )

    @property
    def message_id(self) -> str:
        """获取消息ID"""
        return self.header.message_id

    @property
    def source(self) -> str:
        """获取消息来源"""
        return self.header.source

    @property
    def message_type(self) -> MessageType:
        """获取消息类型"""
        return self.header.message_type

    def mark_delivered(self) -> None:
        """标记为已投递"""
        self.delivery_status = DeliveryStatus.DELIVERED
        self.delivered_at = time.time()

    def mark_acknowledged(self) -> None:
        """标记为已确认"""
        self.delivery_status = DeliveryStatus.ACKNOWLEDGED
        self.acknowledged_at = time.time()

    def mark_failed(self, error: str) -> None:
        """标记为投递失败"""
        self.delivery_status = DeliveryStatus.FAILED
        self.error_info = error

    def mark_expired(self) -> None:
        """标记为已过期"""
        self.delivery_status = DeliveryStatus.EXPIRED

    def should_retry(self) -> bool:
        """检查是否应该重试"""
        return (
            self.delivery_status == DeliveryStatus.FAILED
            and self.header.retry_count < self.header.max_retries
        )

    def increment_retry(self) -> None:
        """增加重试计数"""
        self.header.retry_count += 1

    def to_storage_dict(self) -> dict[str, Any]:
        """转换为存储字典"""
        return {
            "header": self.header.model_dump(),
            "body": self.body.model_dump_for_storage(),
            "delivery_status": self.delivery_status.value,
            "delivered_at": self.delivered_at,
            "acknowledged_at": self.acknowledged_at,
            "error_info": self.error_info,
        }

    def to_log_line(self) -> str:
        """转换为日志行"""
        header_info = self.header.to_log_dict()
        return (
            f"[{header_info['type']}] {header_info['message_id']} "
            f"from:{header_info['source']} "
            f"status:{self.delivery_status.value}"
        )


class Subscription(BaseModel):
    """
    订阅信息

    用于发布订阅模式的消息订阅。
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    channel: str
    subscriber_id: str  # 订阅者 agent ID
    callback: Callable[[Message], Coroutine[Any, Any, None]] | None = None

    # 订阅选项
    filter_pattern: str | None = None  # 消息过滤模式（可选）
    max_concurrent: int = 10  # 最大并发处理数

    # 统计
    messages_received: int = 0
    messages_processed: int = 0
    messages_failed: int = 0
    created_at: float = Field(default_factory=time.time)

    class Config:
        arbitrary_types_allowed = True

    def matches(self, message: Message) -> bool:
        """检查消息是否匹配此订阅"""
        # 频道匹配
        if message.header.channel != self.channel:
            return False

        # 过滤模式匹配（简单实现，可扩展为正则）
        if self.filter_pattern:
            content_str = str(message.body.content)
            if self.filter_pattern not in content_str:
                return False

        return True

    async def handle(self, message: Message) -> bool:
        """
        处理消息

        Returns:
            是否成功处理
        """
        self.messages_received += 1

        if self.callback is None:
            return False

        try:
            await self.callback(message)
            self.messages_processed += 1
            return True
        except Exception:
            self.messages_failed += 1
            return False

    def to_dict(self) -> dict[str, Any]:
        """转换为字典（不包含 callback）"""
        return {
            "id": self.id,
            "channel": self.channel,
            "subscriber_id": self.subscriber_id,
            "filter_pattern": self.filter_pattern,
            "max_concurrent": self.max_concurrent,
            "messages_received": self.messages_received,
            "messages_processed": self.messages_processed,
            "messages_failed": self.messages_failed,
            "created_at": self.created_at,
        }


class AgentRegistration(BaseModel):
    """
    Agent 注册信息

    用于消息总线中的 agent 管理。
    """

    agent_id: str
    agent_type: str
    capabilities: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    # 连接信息
    registered_at: float = Field(default_factory=time.time)
    last_heartbeat: float = Field(default_factory=time.time)

    # 消息队列配置
    max_queue_size: int = 1000
    priority_filter: list[MessagePriority] | None = None

    # 统计
    messages_sent: int = 0
    messages_received: int = 0

    def is_alive(self, timeout: float = 60.0) -> bool:
        """检查 agent 是否活跃"""
        return time.time() - self.last_heartbeat < timeout

    def update_heartbeat(self) -> None:
        """更新心跳时间"""
        self.last_heartbeat = time.time()

    def accepts_priority(self, priority: MessagePriority) -> bool:
        """检查是否接受指定优先级的消息"""
        if self.priority_filter is None:
            return True
        return priority in self.priority_filter

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "capabilities": self.capabilities,
            "metadata": self.metadata,
            "registered_at": self.registered_at,
            "last_heartbeat": self.last_heartbeat,
            "is_alive": self.is_alive(),
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
        }


class BusStatistics(BaseModel):
    """消息总线统计信息"""

    # 消息统计
    total_messages: int = 0
    messages_by_type: dict[str, int] = Field(default_factory=dict)
    messages_by_priority: dict[str, int] = Field(default_factory=dict)

    # 投递统计
    delivered_count: int = 0
    failed_count: int = 0
    expired_count: int = 0
    pending_count: int = 0

    # 性能统计
    total_latency_ms: float = 0.0
    message_count_for_latency: int = 0
    max_latency_ms: float = 0.0

    # Agent 统计
    registered_agents: int = 0
    active_subscriptions: int = 0

    # 时间戳
    started_at: float = Field(default_factory=time.time)
    last_updated: float = Field(default_factory=time.time)

    def record_message(self, message: Message) -> None:
        """记录消息统计"""
        self.total_messages += 1

        msg_type = message.message_type.value
        self.messages_by_type[msg_type] = self.messages_by_type.get(msg_type, 0) + 1

        priority = message.header.priority.name
        self.messages_by_priority[priority] = self.messages_by_priority.get(priority, 0) + 1

        self.last_updated = time.time()

    def record_delivery(self, latency_ms: float, success: bool = True) -> None:
        """记录投递结果"""
        if success:
            self.delivered_count += 1
        else:
            self.failed_count += 1

        self.total_latency_ms += latency_ms
        self.message_count_for_latency += 1
        self.max_latency_ms = max(self.max_latency_ms, latency_ms)
        self.last_updated = time.time()

    def record_expired(self) -> None:
        """记录过期消息"""
        self.expired_count += 1
        self.last_updated = time.time()

    @property
    def avg_latency_ms(self) -> float:
        """平均延迟"""
        if self.message_count_for_latency == 0:
            return 0.0
        return self.total_latency_ms / self.message_count_for_latency

    @property
    def delivery_rate(self) -> float:
        """投递成功率"""
        total = self.delivered_count + self.failed_count
        if total == 0:
            return 0.0
        return self.delivered_count / total * 100

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "messages": {
                "total": self.total_messages,
                "by_type": self.messages_by_type,
                "by_priority": self.messages_by_priority,
            },
            "delivery": {
                "delivered": self.delivered_count,
                "failed": self.failed_count,
                "expired": self.expired_count,
                "pending": self.pending_count,
                "success_rate": round(self.delivery_rate, 2),
            },
            "performance": {
                "avg_latency_ms": round(self.avg_latency_ms, 2),
                "max_latency_ms": round(self.max_latency_ms, 2),
            },
            "agents": {
                "registered": self.registered_agents,
                "subscriptions": self.active_subscriptions,
            },
            "uptime_seconds": round(time.time() - self.started_at, 2),
        }
