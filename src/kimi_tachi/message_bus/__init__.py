"""
Phase 2.2 消息总线架构 (Message Bus)

提供异步消息传递基础设施，支持多种通信模式：
- 点对点 (send)
- 广播 (broadcast)
- 组播 (multicast)
- 发布订阅 (publish/subscribe)

核心组件：
- MessageBus: 消息总线核心
- Message: 消息模型
- MessageStore: 消息持久化
- Tracer: 分布式追踪

与 HybridOrchestrator 集成：
- OrchestratorMessageBus: 适配器类

向后兼容：
- 可通过环境变量 KIMI_TACHI_MESSAGE_BUS_ENABLED 控制是否启用
- 默认启用，设置 false 可回退到直接委托模式

Author: kimi-tachi Team
Phase: 2.2
"""

from __future__ import annotations

import os

# 核心
from .hub import (
    AgentNotFoundError,
    ChannelNotFoundError,
    MessageBus,
    MessageBusError,
    OrchestratorMessageBus,
)

# 模型
from .models import (
    AgentRegistration,
    BusStatistics,
    DeliveryStatus,
    Message,
    MessageBody,
    MessageHeader,
    MessagePriority,
    MessageType,
    Subscription,
)

# 持久化
from .persistence import MessageStore

# 追踪
from .tracing import (
    Span,
    Trace,
    Tracer,
    create_message_span,
    get_current_span_id,
    get_current_trace_id,
    get_tracer,
    set_tracer,
    trace_message_deliver,
    trace_message_receive,
    trace_message_send,
)

__all__ = [
    # 模型
    "Message",
    "MessageHeader",
    "MessageBody",
    "MessageType",
    "MessagePriority",
    "DeliveryStatus",
    "Subscription",
    "AgentRegistration",
    "BusStatistics",
    # 核心
    "MessageBus",
    "OrchestratorMessageBus",
    "MessageBusError",
    "AgentNotFoundError",
    "ChannelNotFoundError",
    # 持久化
    "MessageStore",
    # 追踪
    "Tracer",
    "Trace",
    "Span",
    "get_tracer",
    "set_tracer",
    "get_current_trace_id",
    "get_current_span_id",
    "trace_message_send",
    "trace_message_receive",
    "trace_message_deliver",
    "create_message_span",
]


def is_message_bus_enabled() -> bool:
    """
    检查消息总线是否启用

    可通过环境变量 KIMI_TACHI_MESSAGE_BUS_ENABLED 控制。
    默认启用（true）。
    """
    return os.environ.get("KIMI_TACHI_MESSAGE_BUS_ENABLED", "true").lower() not in (
        "0",
        "false",
        "no",
        "disabled",
    )


__version__ = "2.2.0"
