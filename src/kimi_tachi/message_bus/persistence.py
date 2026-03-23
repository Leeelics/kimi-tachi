"""
Phase 2.2 消息持久化模块

使用 SQLite 实现消息持久化，支持：
- 消息存储和查询
- 投递状态追踪
- 历史消息检索
- 消息重放

Author: kimi-tachi Team
Phase: 2.2
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
import time
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .models import DeliveryStatus, Message, MessagePriority, MessageType


class MessageStore:
    """
    消息存储

    使用 SQLite 持久化消息，支持异步操作。
    """

    def __init__(
        self,
        db_path: Path | str | None = None,
        max_retention_days: int = 7,
        cleanup_interval: int = 3600,
    ):
        """
        初始化消息存储

        Args:
            db_path: 数据库文件路径，默认为 ~/.kimi-tachi/message_bus.db
            max_retention_days: 消息最大保留天数
            cleanup_interval: 清理间隔（秒）
        """
        if db_path is None:
            db_path = Path.home() / ".kimi-tachi" / "message_bus.db"

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.max_retention_days = max_retention_days
        self.cleanup_interval = cleanup_interval

        self._lock = asyncio.Lock()
        self._last_cleanup = 0

        # 初始化数据库
        self._init_db()

    def _init_db(self) -> None:
        """初始化数据库表"""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    message_id TEXT PRIMARY KEY,
                    correlation_id TEXT,
                    trace_id TEXT,
                    span_id TEXT,
                    source TEXT NOT NULL,
                    message_type TEXT NOT NULL,
                    target TEXT,
                    channel TEXT,
                    priority INTEGER NOT NULL DEFAULT 2,
                    content TEXT,
                    content_type TEXT,
                    metadata TEXT,
                    delivery_status TEXT NOT NULL DEFAULT 'pending',
                    created_at REAL NOT NULL,
                    delivered_at REAL,
                    acknowledged_at REAL,
                    error_info TEXT,
                    ttl INTEGER DEFAULT 300
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_source
                ON messages(source)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_target
                ON messages(target)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_channel
                ON messages(channel)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_trace
                ON messages(trace_id)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_created
                ON messages(created_at)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_status
                ON messages(delivery_status)
            """)

            # 投递日志表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS delivery_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    error_info TEXT,
                    FOREIGN KEY (message_id) REFERENCES messages(message_id)
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_delivery_message
                ON delivery_log(message_id)
            """)

            conn.commit()

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """获取数据库连接"""
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.row_factory = sqlite3.Row
            yield conn
        finally:
            conn.close()

    async def save_message(self, message: Message) -> bool:
        """
        保存消息

        Args:
            message: 要保存的消息

        Returns:
            是否保存成功
        """
        async with self._lock:
            try:
                await asyncio.to_thread(self._save_message_sync, message)
                await self._maybe_cleanup()
                return True
            except Exception as e:
                # 记录错误但不抛出，避免影响主流程
                print(f"[MessageStore] Failed to save message: {e}")
                return False

    def _save_message_sync(self, message: Message) -> None:
        """同步保存消息"""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO messages (
                    message_id, correlation_id, trace_id, span_id,
                    source, message_type, target, channel, priority,
                    content, content_type, metadata,
                    delivery_status, created_at, delivered_at,
                    acknowledged_at, error_info, ttl
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message.header.message_id,
                    message.header.correlation_id,
                    message.header.trace_id,
                    message.header.span_id,
                    message.header.source,
                    message.header.message_type.value,
                    message.header.target,
                    message.header.channel,
                    message.header.priority.value,
                    json.dumps(message.body.content, ensure_ascii=False, default=str),
                    message.body.content_type,
                    json.dumps(message.header.metadata, ensure_ascii=False),
                    message.delivery_status.value,
                    message.header.timestamp,
                    message.delivered_at,
                    message.acknowledged_at,
                    message.error_info,
                    message.header.ttl,
                ),
            )
            conn.commit()

    async def update_status(
        self,
        message_id: str,
        status: DeliveryStatus,
        error_info: str | None = None,
    ) -> bool:
        """
        更新消息状态

        Args:
            message_id: 消息ID
            status: 新状态
            error_info: 错误信息（可选）

        Returns:
            是否更新成功
        """
        async with self._lock:
            try:
                await asyncio.to_thread(self._update_status_sync, message_id, status, error_info)
                return True
            except Exception as e:
                print(f"[MessageStore] Failed to update status: {e}")
                return False

    def _update_status_sync(
        self,
        message_id: str,
        status: DeliveryStatus,
        error_info: str | None = None,
    ) -> None:
        """同步更新状态"""
        with self._get_connection() as conn:
            # 根据状态更新相应的时间戳
            if status == DeliveryStatus.DELIVERED:
                conn.execute(
                    """
                    UPDATE messages
                    SET delivery_status = ?, delivered_at = ?, error_info = ?
                    WHERE message_id = ?
                    """,
                    (status.value, time.time(), error_info, message_id),
                )
            elif status == DeliveryStatus.ACKNOWLEDGED:
                conn.execute(
                    """
                    UPDATE messages
                    SET delivery_status = ?, acknowledged_at = ?, error_info = ?
                    WHERE message_id = ?
                    """,
                    (status.value, time.time(), error_info, message_id),
                )
            else:
                conn.execute(
                    """
                    UPDATE messages
                    SET delivery_status = ?, error_info = ?
                    WHERE message_id = ?
                    """,
                    (status.value, error_info, message_id),
                )
            conn.commit()

    async def get_message(self, message_id: str) -> Message | None:
        """
        获取消息

        Args:
            message_id: 消息ID

        Returns:
            Message 对象或 None
        """
        async with self._lock:
            return await asyncio.to_thread(self._get_message_sync, message_id)

    def _get_message_sync(self, message_id: str) -> Message | None:
        """同步获取消息"""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM messages WHERE message_id = ?",
                (message_id,),
            ).fetchone()

            if row is None:
                return None

            return self._row_to_message(row)

    async def get_messages_for_target(
        self,
        target: str,
        status: DeliveryStatus | None = None,
        limit: int = 100,
    ) -> list[Message]:
        """
        获取目标 agent 的消息

        Args:
            target: 目标 agent ID
            status: 过滤状态（可选）
            limit: 返回数量限制

        Returns:
            Message 列表
        """
        async with self._lock:
            return await asyncio.to_thread(
                self._get_messages_for_target_sync, target, status, limit
            )

    def _get_messages_for_target_sync(
        self,
        target: str,
        status: DeliveryStatus | None,
        limit: int,
    ) -> list[Message]:
        """同步获取目标消息"""
        with self._get_connection() as conn:
            if status:
                rows = conn.execute(
                    """
                    SELECT * FROM messages
                    WHERE target = ? AND delivery_status = ?
                    ORDER BY priority ASC, created_at DESC
                    LIMIT ?
                    """,
                    (target, status.value, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM messages
                    WHERE target = ?
                    ORDER BY priority ASC, created_at DESC
                    LIMIT ?
                    """,
                    (target, limit),
                ).fetchall()

            return [self._row_to_message(row) for row in rows]

    async def get_messages_by_trace(
        self,
        trace_id: str,
        limit: int = 100,
    ) -> list[Message]:
        """
        获取追踪链上的所有消息

        Args:
            trace_id: 追踪ID
            limit: 返回数量限制

        Returns:
            Message 列表（按时间排序）
        """
        async with self._lock:
            return await asyncio.to_thread(self._get_messages_by_trace_sync, trace_id, limit)

    def _get_messages_by_trace_sync(
        self,
        trace_id: str,
        limit: int,
    ) -> list[Message]:
        """同步获取追踪消息"""
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM messages
                WHERE trace_id = ?
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (trace_id, limit),
            ).fetchall()

            return [self._row_to_message(row) for row in rows]

    async def get_pending_messages(
        self,
        limit: int = 100,
        max_age_seconds: float = 300,
    ) -> list[Message]:
        """
        获取待处理消息（用于重试）

        Args:
            limit: 返回数量限制
            max_age_seconds: 最大消息年龄

        Returns:
            Message 列表
        """
        async with self._lock:
            return await asyncio.to_thread(self._get_pending_messages_sync, limit, max_age_seconds)

    def _get_pending_messages_sync(
        self,
        limit: int,
        max_age_seconds: float,
    ) -> list[Message]:
        """同步获取待处理消息"""
        min_time = time.time() - max_age_seconds

        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM messages
                WHERE delivery_status = 'pending' AND created_at > ?
                ORDER BY priority ASC, created_at ASC
                LIMIT ?
                """,
                (min_time, limit),
            ).fetchall()

            return [self._row_to_message(row) for row in rows]

    async def get_channel_messages(
        self,
        channel: str,
        since: float | None = None,
        limit: int = 100,
    ) -> list[Message]:
        """
        获取频道消息

        Args:
            channel: 频道名称
            since: 起始时间戳（可选）
            limit: 返回数量限制

        Returns:
            Message 列表
        """
        async with self._lock:
            return await asyncio.to_thread(self._get_channel_messages_sync, channel, since, limit)

    def _get_channel_messages_sync(
        self,
        channel: str,
        since: float | None,
        limit: int,
    ) -> list[Message]:
        """同步获取频道消息"""
        with self._get_connection() as conn:
            if since:
                rows = conn.execute(
                    """
                    SELECT * FROM messages
                    WHERE channel = ? AND created_at > ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (channel, since, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM messages
                    WHERE channel = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (channel, limit),
                ).fetchall()

            return [self._row_to_message(row) for row in rows]

    async def log_delivery(
        self,
        message_id: str,
        agent_id: str,
        status: str,
        error_info: str | None = None,
    ) -> bool:
        """
        记录投递日志

        Args:
            message_id: 消息ID
            agent_id: Agent ID
            status: 投递状态
            error_info: 错误信息（可选）

        Returns:
            是否记录成功
        """
        async with self._lock:
            try:
                await asyncio.to_thread(
                    self._log_delivery_sync, message_id, agent_id, status, error_info
                )
                return True
            except Exception as e:
                print(f"[MessageStore] Failed to log delivery: {e}")
                return False

    def _log_delivery_sync(
        self,
        message_id: str,
        agent_id: str,
        status: str,
        error_info: str | None,
    ) -> None:
        """同步记录投递日志"""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO delivery_log (message_id, agent_id, status, timestamp, error_info)
                VALUES (?, ?, ?, ?, ?)
                """,
                (message_id, agent_id, status, time.time(), error_info),
            )
            conn.commit()

    async def get_delivery_log(self, message_id: str) -> list[dict[str, Any]]:
        """
        获取消息投递日志

        Args:
            message_id: 消息ID

        Returns:
            投递日志列表
        """
        async with self._lock:
            return await asyncio.to_thread(self._get_delivery_log_sync, message_id)

    def _get_delivery_log_sync(self, message_id: str) -> list[dict[str, Any]]:
        """同步获取投递日志"""
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM delivery_log
                WHERE message_id = ?
                ORDER BY timestamp ASC
                """,
                (message_id,),
            ).fetchall()

            return [
                {
                    "id": row["id"],
                    "message_id": row["message_id"],
                    "agent_id": row["agent_id"],
                    "status": row["status"],
                    "timestamp": row["timestamp"],
                    "error_info": row["error_info"],
                }
                for row in rows
            ]

    async def cleanup_old_messages(self) -> int:
        """
        清理过期消息

        Returns:
            清理的消息数量
        """
        async with self._lock:
            return await asyncio.to_thread(self._cleanup_old_messages_sync)

    def _cleanup_old_messages_sync(self) -> int:
        """同步清理过期消息"""
        cutoff_time = time.time() - (self.max_retention_days * 24 * 3600)

        with self._get_connection() as conn:
            # 先获取要删除的消息ID
            rows = conn.execute(
                "SELECT message_id FROM messages WHERE created_at < ?",
                (cutoff_time,),
            ).fetchall()

            message_ids = [row["message_id"] for row in rows]

            if not message_ids:
                return 0

            # 删除投递日志
            placeholders = ",".join(["?"] * len(message_ids))
            conn.execute(
                f"DELETE FROM delivery_log WHERE message_id IN ({placeholders})",
                message_ids,
            )

            # 删除消息
            conn.execute(
                f"DELETE FROM messages WHERE message_id IN ({placeholders})",
                message_ids,
            )

            conn.commit()
            return len(message_ids)

    async def _maybe_cleanup(self) -> None:
        """按需执行清理"""
        now = time.time()
        if now - self._last_cleanup > self.cleanup_interval:
            count = await self.cleanup_old_messages()
            if count > 0:
                print(f"[MessageStore] Cleaned up {count} old messages")
            self._last_cleanup = now

    def _row_to_message(self, row: sqlite3.Row) -> Message:
        """将数据库行转换为 Message 对象"""
        from .models import MessageBody, MessageHeader

        # 解析内容
        try:
            content = json.loads(row["content"])
        except json.JSONDecodeError:
            content = row["content"]

        # 解析元数据
        try:
            metadata = json.loads(row["metadata"]) if row["metadata"] else {}
        except json.JSONDecodeError:
            metadata = {}

        header = MessageHeader(
            message_id=row["message_id"],
            correlation_id=row["correlation_id"],
            trace_id=row["trace_id"],
            span_id=row["span_id"] or "",
            source=row["source"],
            timestamp=row["created_at"],
            ttl=row["ttl"] or 300,
            priority=MessagePriority(row["priority"]),
            message_type=MessageType(row["message_type"]),
            target=row["target"],
            channel=row["channel"],
            metadata=metadata,
        )

        body = MessageBody(
            content=content,
            content_type=row["content_type"] or "application/json",
        )

        message = Message(
            header=header,
            body=body,
            delivery_status=DeliveryStatus(row["delivery_status"]),
            delivered_at=row["delivered_at"],
            acknowledged_at=row["acknowledged_at"],
            error_info=row["error_info"],
        )

        return message

    async def get_statistics(self) -> dict[str, Any]:
        """
        获取存储统计信息

        Returns:
            统计信息字典
        """
        async with self._lock:
            return await asyncio.to_thread(self._get_statistics_sync)

    def _get_statistics_sync(self) -> dict[str, Any]:
        """同步获取统计信息"""
        with self._get_connection() as conn:
            # 消息总数
            total = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]

            # 按状态统计
            status_counts = conn.execute(
                "SELECT delivery_status, COUNT(*) FROM messages GROUP BY delivery_status"
            ).fetchall()

            # 按类型统计
            type_counts = conn.execute(
                "SELECT message_type, COUNT(*) FROM messages GROUP BY message_type"
            ).fetchall()

            # 数据库大小
            db_size = self.db_path.stat().st_size if self.db_path.exists() else 0

            return {
                "total_messages": total,
                "by_status": {row[0]: row[1] for row in status_counts},
                "by_type": {row[0]: row[1] for row in type_counts},
                "db_size_bytes": db_size,
                "db_size_mb": round(db_size / (1024 * 1024), 2),
            }

    async def close(self) -> None:
        """关闭存储（清理资源）"""
        await self.cleanup_old_messages()
