"""
文件内容缓存

提供基于文件 hash 的内容缓存，支持:
1. 自动检测文件修改
2. LRU 淘汰策略
3. 内存 + 磁盘两级缓存
"""

from __future__ import annotations

import sqlite3
import threading
import time
from collections import OrderedDict
from pathlib import Path

from .types import CacheEntry, CacheStatistics, FileMetadata


class FileContentCache:
    """
    文件内容缓存

    设计:
    - L1: 内存缓存 (LRU, 有大小限制)
    - L2: SQLite 磁盘缓存 (持久化)
    - 自动检测文件修改 (mtime + hash)

    使用:
        cache = FileContentCache(
            memory_limit=50*1024*1024,  # 50MB
            disk_cache_dir=Path("~/.kimi-tachi/cache/files"),
        )

        # 读取文件（自动缓存）
        content = cache.get("/path/to/file.py")

        # 手动添加缓存
        cache.put("/path/to/file.py", content)

        # 使缓存失效
        cache.invalidate("/path/to/file.py")
    """

    def __init__(
        self,
        memory_limit: int = 50 * 1024 * 1024,  # 50MB
        disk_cache_dir: Path | None = None,
        ttl_seconds: int | None = None,  # 默认不过期
    ):
        self.memory_limit = memory_limit
        self.disk_cache_dir = disk_cache_dir
        self.ttl_seconds = ttl_seconds

        # 内存缓存: OrderedDict 用于 LRU
        self._memory_cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._current_memory_size: int = 0
        self._lock = threading.RLock()

        # 统计
        self._stats = CacheStatistics()

        # 初始化磁盘缓存
        self._db_path: Path | None = None
        if disk_cache_dir:
            self._init_disk_cache()

    def _init_disk_cache(self) -> None:
        """初始化磁盘缓存数据库"""
        if not self.disk_cache_dir:
            return

        self.disk_cache_dir.mkdir(parents=True, exist_ok=True)
        self._db_path = self.disk_cache_dir / "file_cache.db"

        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS file_cache (
                    path TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    mtime REAL NOT NULL,
                    size INTEGER NOT NULL,
                    created_at REAL NOT NULL,
                    accessed_at REAL NOT NULL,
                    access_count INTEGER DEFAULT 0
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_accessed
                ON file_cache(accessed_at)
            """)

            conn.commit()

    def get(self, file_path: str | Path) -> str | None:
        """
        获取文件内容（带缓存）

        Args:
            file_path: 文件路径

        Returns:
            文件内容，如果文件不存在或读取失败返回 None
        """
        path = Path(file_path)
        path_str = str(path.resolve())

        # 获取当前文件元数据
        current_meta = FileMetadata.from_path(path)
        if not current_meta:
            return None

        with self._lock:
            # 1. 检查内存缓存
            if path_str in self._memory_cache:
                entry = self._memory_cache[path_str]

                # 检查是否过期
                if entry.is_expired():
                    self._remove_from_memory(path_str)
                else:
                    # 验证文件是否修改
                    cached_meta = entry.value.get("metadata")
                    if cached_meta and not current_meta.is_modified(cached_meta):
                        # 缓存命中
                        entry.touch()
                        self._memory_cache.move_to_end(path_str)
                        self._stats.file_cache_hits += 1
                        return entry.value["content"]
                    else:
                        # 文件已修改，移除缓存
                        self._remove_from_memory(path_str)

            # 2. 检查磁盘缓存
            if self._db_path:
                content = self._get_from_disk(path_str, current_meta)
                if content is not None:
                    # 加载到内存缓存
                    self._add_to_memory(path_str, {
                        "content": content,
                        "metadata": current_meta,
                    })
                    self._stats.file_cache_hits += 1
                    return content

            # 缓存未命中
            self._stats.file_cache_misses += 1
            return None

    def get_or_read(self, file_path: str | Path) -> str | None:
        """
        获取文件内容，缓存未命中则读取文件

        Args:
            file_path: 文件路径

        Returns:
            文件内容，失败返回 None
        """
        # 先尝试缓存
        content = self.get(file_path)
        if content is not None:
            return content

        # 缓存未命中，读取文件
        try:
            path = Path(file_path)
            content = path.read_text(encoding="utf-8")

            # 添加到缓存
            self.put(file_path, content)

            return content
        except (OSError, UnicodeDecodeError):
            return None

    def put(self, file_path: str | Path, content: str) -> None:
        """
        添加文件内容到缓存

        Args:
            file_path: 文件路径
            content: 文件内容
        """
        path = Path(file_path)
        path_str = str(path.resolve())

        # 获取文件元数据
        metadata = FileMetadata.from_path(path)
        if not metadata:
            # 文件可能不存在，创建临时元数据
            metadata = FileMetadata(
                path=path_str,
                size=len(content.encode("utf-8")),
                mtime=time.time(),
                content_hash="",
            )

        value = {
            "content": content,
            "metadata": metadata,
        }

        with self._lock:
            # 添加到内存缓存
            self._add_to_memory(path_str, value)

            # 添加到磁盘缓存
            if self._db_path:
                self._add_to_disk(path_str, content, metadata)

    def _add_to_memory(self, path_str: str, value: dict) -> None:
        """添加到内存缓存（带 LRU 淘汰）"""
        content = value["content"]
        content_size = len(content.encode("utf-8"))

        # 如果单文件超过限制，不缓存
        if content_size > self.memory_limit // 10:  # 单文件不超过 10%
            return

        # 淘汰旧缓存直到有足够空间
        while (self._current_memory_size + content_size > self.memory_limit
               and self._memory_cache):
            self._evict_oldest()

        # 添加新缓存
        entry = CacheEntry(
            key=path_str,
            value=value,
            ttl_seconds=self.ttl_seconds,
        )

        self._memory_cache[path_str] = entry
        self._memory_cache.move_to_end(path_str)
        self._current_memory_size += content_size

        self._stats.file_cache_entries = len(self._memory_cache)
        self._stats.file_cache_size = self._current_memory_size

    def _remove_from_memory(self, path_str: str) -> None:
        """从内存缓存移除"""
        if path_str in self._memory_cache:
            entry = self._memory_cache.pop(path_str)
            content_size = len(entry.value["content"].encode("utf-8"))
            self._current_memory_size -= content_size

    def _evict_oldest(self) -> None:
        """淘汰最旧的缓存"""
        if not self._memory_cache:
            return

        # 移除最旧的
        path_str, entry = self._memory_cache.popitem(last=False)
        content_size = len(entry.value["content"].encode("utf-8"))
        self._current_memory_size -= content_size

    def _get_from_disk(self, path_str: str, current_meta: FileMetadata) -> str | None:
        """从磁盘缓存获取"""
        if not self._db_path:
            return None

        try:
            with sqlite3.connect(self._db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT content, content_hash, mtime
                    FROM file_cache
                    WHERE path = ?
                    """,
                    (path_str,),
                )
                row = cursor.fetchone()

                if not row:
                    return None

                content, content_hash, mtime = row

                # 验证文件是否修改
                if mtime != current_meta.mtime:
                    # 文件已修改，删除缓存
                    conn.execute(
                        "DELETE FROM file_cache WHERE path = ?",
                        (path_str,),
                    )
                    conn.commit()
                    return None

                # 更新访问统计
                conn.execute(
                    """
                    UPDATE file_cache
                    SET accessed_at = ?, access_count = access_count + 1
                    WHERE path = ?
                    """,
                    (time.time(), path_str),
                )
                conn.commit()

                return content

        except sqlite3.Error:
            return None

    def _add_to_disk(self, path_str: str, content: str, metadata: FileMetadata) -> None:
        """添加到磁盘缓存"""
        if not self._db_path:
            return

        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO file_cache
                    (path, content, content_hash, mtime, size, created_at, accessed_at, access_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        path_str,
                        content,
                        metadata.content_hash,
                        metadata.mtime,
                        metadata.size,
                        time.time(),
                        time.time(),
                        1,
                    ),
                )
                conn.commit()
        except sqlite3.Error:
            pass  # 磁盘缓存失败不影响主流程

    def invalidate(self, file_path: str | Path) -> None:
        """使缓存失效"""
        path = Path(file_path)
        path_str = str(path.resolve())

        with self._lock:
            self._remove_from_memory(path_str)

            if self._db_path:
                try:
                    with sqlite3.connect(self._db_path) as conn:
                        conn.execute(
                            "DELETE FROM file_cache WHERE path = ?",
                            (path_str,),
                        )
                        conn.commit()
                except sqlite3.Error:
                    pass

    def clear(self) -> None:
        """清空所有缓存"""
        with self._lock:
            self._memory_cache.clear()
            self._current_memory_size = 0

            if self._db_path:
                try:
                    with sqlite3.connect(self._db_path) as conn:
                        conn.execute("DELETE FROM file_cache")
                        conn.commit()
                except sqlite3.Error:
                    pass

    def get_statistics(self) -> CacheStatistics:
        """获取统计信息"""
        with self._lock:
            self._stats.file_cache_entries = len(self._memory_cache)
            self._stats.file_cache_size = self._current_memory_size
            return self._stats

    def cleanup_expired(self) -> int:
        """清理过期缓存，返回清理数量"""
        cleaned = 0

        with self._lock:
            expired = [
                key for key, entry in self._memory_cache.items()
                if entry.is_expired()
            ]
            for key in expired:
                self._remove_from_memory(key)
                cleaned += 1

        return cleaned
