"""
分析结果缓存

缓存 LLM 分析结果，避免重复调用。

设计:
- 基于查询内容 hash 作为 key
- 关联文件 hash，文件修改自动失效
- 支持 TTL 过期
- 可配置的缓存策略
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class AnalysisQuery:
    """分析查询"""
    query_type: str  # "find_functions", "analyze_class", etc.
    params: dict[str, Any]
    file_hashes: dict[str, str]  # 依赖文件的路径 -> hash

    def to_key(self) -> str:
        """生成缓存 key"""
        # 序列化查询
        data = {
            "type": self.query_type,
            "params": self.params,
            "files": sorted(self.file_hashes.items()),  # 排序保证一致性
        }
        serialized = json.dumps(data, sort_keys=True)
        return hashlib.sha256(serialized.encode()).hexdigest()[:32]


class AnalysisResultCache:
    """
    分析结果缓存

    使用示例:
        cache = AnalysisResultCache(
            db_path=Path("~/.kimi-tachi/cache/analysis.db"),
            default_ttl=3600,  # 1小时
        )

        # 构建查询
        query = AnalysisQuery(
            query_type="find_functions",
            params={"pattern": "process_*"},
            file_hashes={"src/main.py": "abc123..."},
        )

        # 尝试获取缓存
        result = cache.get(query)
        if result is None:
            # 缓存未命中，执行分析
            result = perform_analysis(query)
            cache.put(query, result)
    """

    def __init__(
        self,
        db_path: Path | None = None,
        default_ttl: int = 3600,  # 默认 1 小时
        max_entries: int = 10000,
    ):
        self.db_path = db_path
        self.default_ttl = default_ttl
        self.max_entries = max_entries

        # 内存缓存（热数据）
        self._memory_cache: dict[str, dict] = {}

        if db_path:
            self._init_database()

    def _init_database(self) -> None:
        """初始化数据库"""
        if not self.db_path:
            return

        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS analysis_cache (
                    query_key TEXT PRIMARY KEY,
                    query_type TEXT NOT NULL,
                    result TEXT NOT NULL,  -- JSON
                    file_hashes TEXT NOT NULL,  -- JSON
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL,
                    access_count INTEGER DEFAULT 0,
                    hit_count INTEGER DEFAULT 0
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_expires
                ON analysis_cache(expires_at)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_query_type
                ON analysis_cache(query_type)
            """)

            conn.commit()

    def get(self, query: AnalysisQuery) -> Any | None:
        """
        获取缓存的分析结果

        Args:
            query: 分析查询

        Returns:
            缓存的结果，未命中或过期返回 None
        """
        key = query.to_key()

        # 1. 检查内存缓存
        if key in self._memory_cache:
            entry = self._memory_cache[key]
            if entry["expires_at"] > time.time():
                if self._validate_file_hashes(query.file_hashes, entry["file_hashes"]):
                    entry["hit_count"] += 1
                    return entry["result"]

        # 2. 检查磁盘缓存
        if not self.db_path:
            return None

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT result, file_hashes, expires_at
                    FROM analysis_cache
                    WHERE query_key = ?
                    """,
                    (key,),
                )
                row = cursor.fetchone()

                if not row:
                    return None

                result_json, file_hashes_json, expires_at = row

                # 检查是否过期
                if time.time() > expires_at:
                    # 删除过期缓存
                    conn.execute(
                        "DELETE FROM analysis_cache WHERE query_key = ?",
                        (key,),
                    )
                    conn.commit()
                    return None

                # 验证文件 hash
                cached_hashes = json.loads(file_hashes_json)
                if not self._validate_file_hashes(query.file_hashes, cached_hashes):
                    # 文件已修改，删除缓存
                    conn.execute(
                        "DELETE FROM analysis_cache WHERE query_key = ?",
                        (key,),
                    )
                    conn.commit()
                    return None

                # 缓存命中
                result = json.loads(result_json)

                # 更新访问统计
                conn.execute(
                    """
                    UPDATE analysis_cache
                    SET access_count = access_count + 1, hit_count = hit_count + 1
                    WHERE query_key = ?
                    """,
                    (key,),
                )
                conn.commit()

                # 加载到内存缓存
                self._memory_cache[key] = {
                    "result": result,
                    "file_hashes": cached_hashes,
                    "expires_at": expires_at,
                    "hit_count": 1,
                }

                return result

        except (sqlite3.Error, json.JSONDecodeError):
            return None

    def put(
        self,
        query: AnalysisQuery,
        result: Any,
        ttl: int | None = None,
    ) -> bool:
        """
        缓存分析结果

        Args:
            query: 分析查询
            result: 分析结果
            ttl: 过期时间（秒），None 使用默认值

        Returns:
            是否成功
        """
        key = query.to_key()
        ttl = ttl or self.default_ttl
        expires_at = time.time() + ttl

        # 序列化结果
        try:
            result_json = json.dumps(result, default=str)
            file_hashes_json = json.dumps(query.file_hashes)
        except (TypeError, ValueError):
            return False

        # 保存到内存
        self._memory_cache[key] = {
            "result": result,
            "file_hashes": query.file_hashes,
            "expires_at": expires_at,
            "hit_count": 0,
        }

        # 保存到磁盘
        if not self.db_path:
            return True

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO analysis_cache
                    (query_key, query_type, result, file_hashes, created_at, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        key,
                        query.query_type,
                        result_json,
                        file_hashes_json,
                        time.time(),
                        expires_at,
                    ),
                )
                conn.commit()

                # 清理旧缓存
                self._cleanup_old_entries()

                return True
        except sqlite3.Error:
            return False

    def _validate_file_hashes(
        self,
        current_hashes: dict[str, str],
        cached_hashes: dict[str, str],
    ) -> bool:
        """验证文件 hash 是否匹配"""
        # 检查所有依赖文件
        for path, current_hash in current_hashes.items():
            cached_hash = cached_hashes.get(path)
            if not cached_hash or cached_hash != current_hash:
                return False
        return True

    def _cleanup_old_entries(self) -> None:
        """清理旧缓存条目"""
        if not self.db_path:
            return

        try:
            with sqlite3.connect(self.db_path) as conn:
                # 删除过期条目
                conn.execute(
                    "DELETE FROM analysis_cache WHERE expires_at < ?",
                    (time.time(),),
                )

                # 如果条目过多，删除最旧的
                cursor = conn.execute("SELECT COUNT(*) FROM analysis_cache")
                count = cursor.fetchone()[0]

                if count > self.max_entries:
                    # 删除访问最少的旧条目
                    conn.execute(
                        """
                        DELETE FROM analysis_cache
                        WHERE query_key IN (
                            SELECT query_key FROM analysis_cache
                            ORDER BY hit_count ASC, created_at ASC
                            LIMIT ?
                        )
                        """,
                        (count - self.max_entries + 1000,),  # 多删一些留出空间
                    )

                conn.commit()
        except sqlite3.Error:
            pass

    def invalidate_by_file(self, file_path: str) -> int:
        """
        使涉及特定文件的所有缓存失效

        Returns:
            失效的缓存数量
        """
        if not self.db_path:
            return 0

        try:
            with sqlite3.connect(self.db_path) as conn:
                # 查找包含该文件的缓存
                cursor = conn.execute(
                    "SELECT query_key, file_hashes FROM analysis_cache",
                )

                to_delete = []
                for row in cursor.fetchall():
                    query_key, file_hashes_json = row
                    try:
                        file_hashes = json.loads(file_hashes_json)
                        if file_path in file_hashes:
                            to_delete.append(query_key)
                    except json.JSONDecodeError:
                        continue

                # 删除
                for key in to_delete:
                    conn.execute(
                        "DELETE FROM analysis_cache WHERE query_key = ?",
                        (key,),
                    )
                    # 从内存缓存也删除
                    self._memory_cache.pop(key, None)

                conn.commit()
                return len(to_delete)
        except sqlite3.Error:
            return 0

    def clear(self) -> None:
        """清空所有缓存"""
        self._memory_cache.clear()

        if not self.db_path:
            return

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM analysis_cache")
                conn.commit()
        except sqlite3.Error:
            pass

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息"""
        if not self.db_path:
            return {
                "memory_entries": len(self._memory_cache),
                "disk_entries": 0,
            }

        try:
            with sqlite3.connect(self.db_path) as conn:
                # 总条目
                cursor = conn.execute("SELECT COUNT(*) FROM analysis_cache")
                total = cursor.fetchone()[0]

                # 过期条目
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM analysis_cache WHERE expires_at < ?",
                    (time.time(),),
                )
                expired = cursor.fetchone()[0]

                # 总命中次数
                cursor = conn.execute(
                    "SELECT SUM(hit_count) FROM analysis_cache"
                )
                total_hits = cursor.fetchone()[0] or 0

                # 按类型统计
                cursor = conn.execute(
                    "SELECT query_type, COUNT(*) FROM analysis_cache GROUP BY query_type"
                )
                by_type = {row[0]: row[1] for row in cursor.fetchall()}

                return {
                    "memory_entries": len(self._memory_cache),
                    "disk_entries": total,
                    "expired_entries": expired,
                    "total_hits": total_hits,
                    "by_type": by_type,
                }
        except sqlite3.Error as e:
            return {"error": str(e)}
