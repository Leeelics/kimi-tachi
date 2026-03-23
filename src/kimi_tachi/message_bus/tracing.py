"""
Phase 2.2 分布式追踪模块

实现消息执行的分布式追踪，支持：
- Trace ID 生成和传播
- Span 创建和管理
- 调用链追踪
- 性能分析

Author: kimi-tachi Team
Phase: 2.2
"""

from __future__ import annotations

import time
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any

from .models import Message

# 当前追踪上下文
_current_trace_id: ContextVar[str | None] = ContextVar("trace_id", default=None)
_current_span_id: ContextVar[str | None] = ContextVar("span_id", default=None)


@dataclass
class Span:
    """
    追踪 Span

    表示一个操作的时间跨度。
    """

    name: str
    span_id: str = field(default_factory=lambda: str(uuid.uuid4())[:16])
    trace_id: str | None = None
    parent_span_id: str | None = None

    # 时间戳
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None

    # 元数据
    attributes: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)

    # 状态
    status: str = "ok"  # ok, error
    error_message: str | None = None

    def __post_init__(self):
        """初始化 trace_id"""
        if self.trace_id is None:
            self.trace_id = _current_trace_id.get() or str(uuid.uuid4())
        if self.parent_span_id is None:
            self.parent_span_id = _current_span_id.get()

    def end(self, status: str = "ok", error_message: str | None = None) -> None:
        """结束 Span"""
        self.end_time = time.time()
        self.status = status
        self.error_message = error_message

    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        """添加事件"""
        self.events.append(
            {
                "name": name,
                "timestamp": time.time(),
                "attributes": attributes or {},
            }
        )

    def set_attribute(self, key: str, value: Any) -> None:
        """设置属性"""
        self.attributes[key] = value

    @property
    def duration_ms(self) -> float:
        """Span 持续时间（毫秒）"""
        end = self.end_time or time.time()
        return (end - self.start_time) * 1000

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "parent_span_id": self.parent_span_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": round(self.duration_ms, 2),
            "attributes": self.attributes,
            "events": self.events,
            "status": self.status,
            "error_message": self.error_message,
        }


@dataclass
class Trace:
    """
    追踪链路

    包含一组相关的 Span，表示一个完整的请求链路。
    """

    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    spans: list[Span] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None

    # 元数据
    root_span_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def create_span(
        self,
        name: str,
        parent_span_id: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> Span:
        """
        创建新 Span

        Args:
            name: Span 名称
            parent_span_id: 父 Span ID
            attributes: 初始属性

        Returns:
            Span 实例
        """
        span = Span(
            name=name,
            trace_id=self.trace_id,
            parent_span_id=parent_span_id or self.root_span_id,
        )

        if attributes:
            span.attributes.update(attributes)

        self.spans.append(span)

        # 设置根 Span
        if self.root_span_id is None:
            self.root_span_id = span.span_id

        return span

    def end(self) -> None:
        """结束追踪"""
        self.end_time = time.time()

    @property
    def duration_ms(self) -> float:
        """追踪持续时间（毫秒）"""
        end = self.end_time or time.time()
        return (end - self.start_time) * 1000

    @property
    def span_count(self) -> int:
        """Span 数量"""
        return len(self.spans)

    def get_span(self, span_id: str) -> Span | None:
        """获取指定 Span"""
        for span in self.spans:
            if span.span_id == span_id:
                return span
        return None

    def get_root_span(self) -> Span | None:
        """获取根 Span"""
        if self.root_span_id:
            return self.get_span(self.root_span_id)
        return None

    def get_children(self, span_id: str) -> list[Span]:
        """获取子 Span 列表"""
        return [s for s in self.spans if s.parent_span_id == span_id]

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "trace_id": self.trace_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": round(self.duration_ms, 2),
            "span_count": self.span_count,
            "root_span_id": self.root_span_id,
            "spans": [s.to_dict() for s in self.spans],
            "metadata": self.metadata,
        }


class Tracer:
    """
    分布式追踪器

    管理追踪链路和 Span 的生命周期。
    """

    def __init__(self, max_traces: int = 1000):
        """
        初始化追踪器

        Args:
            max_traces: 最大保留的追踪数量
        """
        self.max_traces = max_traces
        self._traces: dict[str, Trace] = {}
        self._active_spans: dict[str, Span] = {}

    def start_trace(
        self,
        name: str,
        trace_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Trace:
        """
        开始新的追踪

        Args:
            name: 追踪名称（根 Span 名称）
            trace_id: 指定追踪ID（可选）
            metadata: 元数据

        Returns:
            Trace 实例
        """
        trace = Trace(
            trace_id=trace_id or str(uuid.uuid4()),
            metadata=metadata or {},
        )

        # 创建根 Span
        root_span = trace.create_span(name)
        self._active_spans[root_span.span_id] = root_span

        # 设置上下文
        _current_trace_id.set(trace.trace_id)
        _current_span_id.set(root_span.span_id)

        # 保存追踪
        self._traces[trace.trace_id] = trace

        # 清理旧追踪
        self._cleanup_old_traces()

        return trace

    def start_span(
        self,
        name: str,
        parent_span_id: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> Span:
        """
        开始新的 Span

        Args:
            name: Span 名称
            parent_span_id: 父 Span ID（默认使用当前上下文）
            attributes: 初始属性

        Returns:
            Span 实例
        """
        trace_id = _current_trace_id.get()

        if trace_id is None or trace_id not in self._traces:
            # 没有活动追踪，创建新的
            trace = self.start_trace(name)
            return trace.get_root_span()  # type: ignore

        trace = self._traces[trace_id]

        # 确定父 Span
        if parent_span_id is None:
            parent_span_id = _current_span_id.get()

        span = trace.create_span(name, parent_span_id, attributes)
        self._active_spans[span.span_id] = span

        # 更新当前 Span
        _current_span_id.set(span.span_id)

        return span

    def end_span(
        self,
        span_id: str | None = None,
        status: str = "ok",
        error_message: str | None = None,
    ) -> None:
        """
        结束 Span

        Args:
            span_id: Span ID（默认结束当前 Span）
            status: 状态
            error_message: 错误信息
        """
        if span_id is None:
            span_id = _current_span_id.get()

        if span_id is None or span_id not in self._active_spans:
            return

        span = self._active_spans.pop(span_id)
        span.end(status, error_message)

        # 恢复父 Span 为当前 Span
        if span.parent_span_id:
            _current_span_id.set(span.parent_span_id)
        else:
            # 没有父 Span，结束追踪
            self.end_trace(span.trace_id)

    def end_trace(self, trace_id: str | None = None) -> None:
        """
        结束追踪

        Args:
            trace_id: 追踪ID（默认结束当前追踪）
        """
        if trace_id is None:
            trace_id = _current_trace_id.get()

        if trace_id and trace_id in self._traces:
            trace = self._traces[trace_id]
            trace.end()

            # 清理活动 Span
            for span in trace.spans:
                self._active_spans.pop(span.span_id, None)

        # 清除上下文
        _current_trace_id.set(None)
        _current_span_id.set(None)

    def get_trace(self, trace_id: str) -> Trace | None:
        """获取追踪"""
        return self._traces.get(trace_id)

    def get_current_trace(self) -> Trace | None:
        """获取当前追踪"""
        trace_id = _current_trace_id.get()
        if trace_id:
            return self._traces.get(trace_id)
        return None

    def get_current_span(self) -> Span | None:
        """获取当前 Span"""
        span_id = _current_span_id.get()
        if span_id:
            return self._active_spans.get(span_id)
        return None

    def inject_context(self, message: Message) -> None:
        """
        注入追踪上下文到消息

        Args:
            message: 要注入的消息
        """
        trace_id = _current_trace_id.get()
        span_id = _current_span_id.get()

        if trace_id:
            message.header.trace_id = trace_id
        if span_id:
            message.header.parent_span_id = span_id

    def extract_context(self, message: Message) -> None:
        """
        从消息提取追踪上下文

        Args:
            message: 要提取的消息
        """
        if message.header.trace_id:
            _current_trace_id.set(message.header.trace_id)
        if message.header.span_id:
            _current_span_id.set(message.header.span_id)

    @asynccontextmanager
    async def span(
        self,
        name: str,
        parent_span_id: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> AsyncGenerator[Span, None]:
        """
        Span 上下文管理器

        Args:
            name: Span 名称
            parent_span_id: 父 Span ID
            attributes: 初始属性

        Yields:
            Span 实例
        """
        span = self.start_span(name, parent_span_id, attributes)
        try:
            yield span
            self.end_span(span.span_id, status="ok")
        except Exception as e:
            self.end_span(span.span_id, status="error", error_message=str(e))
            raise

    @asynccontextmanager
    async def trace(
        self,
        name: str,
        trace_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AsyncGenerator[Trace, None]:
        """
        追踪上下文管理器

        Args:
            name: 追踪名称
            trace_id: 追踪ID
            metadata: 元数据

        Yields:
            Trace 实例
        """
        t = self.start_trace(name, trace_id, metadata)
        try:
            yield t
            self.end_trace(t.trace_id)
        except Exception:
            self.end_trace(t.trace_id)
            raise

    def _cleanup_old_traces(self) -> None:
        """清理旧追踪"""
        if len(self._traces) > self.max_traces:
            # 按开始时间排序，删除最旧的
            sorted_traces = sorted(
                self._traces.items(),
                key=lambda x: x[1].start_time,
            )
            to_remove = len(self._traces) - self.max_traces
            for trace_id, _ in sorted_traces[:to_remove]:
                del self._traces[trace_id]

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息"""
        total_spans = sum(len(t.spans) for t in self._traces.values())
        active_traces = sum(1 for t in self._traces.values() if t.end_time is None)

        return {
            "total_traces": len(self._traces),
            "active_traces": active_traces,
            "completed_traces": len(self._traces) - active_traces,
            "total_spans": total_spans,
            "active_spans": len(self._active_spans),
            "max_traces": self.max_traces,
        }

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "traces": [t.to_dict() for t in self._traces.values()],
            "statistics": self.get_statistics(),
        }


# 全局追踪器实例
_global_tracer: Tracer | None = None


def get_tracer() -> Tracer:
    """获取全局追踪器实例"""
    global _global_tracer
    if _global_tracer is None:
        _global_tracer = Tracer()
    return _global_tracer


def set_tracer(tracer: Tracer) -> None:
    """设置全局追踪器实例"""
    global _global_tracer
    _global_tracer = tracer


def create_message_span(
    message: Message,
    operation: str,
    attributes: dict[str, Any] | None = None,
) -> Span:
    """
    为消息操作创建 Span

    Args:
        message: 消息
        operation: 操作名称
        attributes: 额外属性

    Returns:
        Span 实例
    """
    tracer = get_tracer()

    # 提取消息的追踪上下文
    tracer.extract_context(message)

    attrs = {
        "message_id": message.message_id,
        "message_type": message.message_type.value,
        "source": message.source,
    }

    if message.header.target:
        attrs["target"] = message.header.target
    if message.header.channel:
        attrs["channel"] = message.header.channel

    if attributes:
        attrs.update(attributes)

    return tracer.start_span(f"message.{operation}", attributes=attrs)


def trace_message_send(message: Message) -> None:
    """追踪消息发送"""
    tracer = get_tracer()
    tracer.inject_context(message)

    span = create_message_span(
        message,
        "send",
        {
            "priority": message.header.priority.name,
        },
    )
    span.add_event("message_sent", {"timestamp": time.time()})


def trace_message_receive(message: Message, handler: str) -> Span:
    """追踪消息接收"""
    span = create_message_span(
        message,
        "receive",
        {
            "handler": handler,
        },
    )
    span.add_event("message_received", {"timestamp": time.time()})
    return span


def trace_message_deliver(message: Message, target: str, success: bool) -> None:
    """追踪消息投递"""
    span = create_message_span(
        message,
        "deliver",
        {
            "target": target,
            "success": success,
        },
    )
    span.add_event(
        "message_delivered",
        {
            "timestamp": time.time(),
            "success": success,
        },
    )
    if not success:
        span.status = "error"


def get_current_trace_id() -> str | None:
    """获取当前追踪ID"""
    return _current_trace_id.get()


def get_current_span_id() -> str | None:
    """获取当前 Span ID"""
    return _current_span_id.get()
