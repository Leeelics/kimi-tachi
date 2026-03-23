"""
Context Cache Manager

整合所有缓存组件的统一管理器。
"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any

from .analysis_cache import AnalysisQuery, AnalysisResultCache
from .compressor import ContextCompressor
from .file_cache import FileContentCache
from .semantic_index import SemanticIndex
from .types import CacheStatistics, Symbol


class ContextCacheManager:
    """
    上下文缓存管理器

    整合文件缓存、语义索引、分析缓存、上下文压缩的统一管理器。

    使用示例:
        manager = ContextCacheManager(
            cache_dir=Path("~/.kimi-tachi/cache"),
            enable_semantic_index=True,
        )

        # 读取文件（带缓存）
        content = manager.get_file_content("src/main.py")

        # 查询符号
        symbols = manager.query_symbol("process_data")

        # 获取分析结果（带缓存）
        result = manager.get_analysis_result(
            query_type="find_functions",
            params={"pattern": "process_*"},
            file_paths=["src/main.py"],
            analyzer=perform_analysis,
        )

        # 压缩上下文
        compressed = manager.compress_context(long_content)
    """

    def __init__(
        self,
        cache_dir: Path | str | None = None,
        enable_file_cache: bool = True,
        enable_semantic_index: bool = True,
        enable_analysis_cache: bool = True,
        enable_compression: bool = True,
        # 文件缓存配置
        file_cache_memory_limit: int = 50 * 1024 * 1024,  # 50MB
        file_cache_ttl: int | None = None,
        # 分析缓存配置
        analysis_cache_ttl: int = 3600,
        # 压缩配置
        compression_max_tokens: int = 500,
    ):
        """
        初始化上下文缓存管理器

        Args:
            cache_dir: 缓存目录，None 表示不使用磁盘缓存
            enable_file_cache: 启用文件内容缓存
            enable_semantic_index: 启用语义索引
            enable_analysis_cache: 启用分析结果缓存
            enable_compression: 启用上下文压缩
            file_cache_memory_limit: 文件缓存内存限制
            file_cache_ttl: 文件缓存过期时间
            analysis_cache_ttl: 分析缓存过期时间
            compression_max_tokens: 压缩后最大 token 数
        """
        self.cache_dir = Path(cache_dir).expanduser() if cache_dir else None

        # 初始化各组件
        self.file_cache: FileContentCache | None = None
        self.semantic_index: SemanticIndex | None = None
        self.analysis_cache: AnalysisResultCache | None = None
        self.compressor: ContextCompressor | None = None

        if enable_file_cache:
            disk_dir = self.cache_dir / "files" if self.cache_dir else None
            self.file_cache = FileContentCache(
                memory_limit=file_cache_memory_limit,
                disk_cache_dir=disk_dir,
                ttl_seconds=file_cache_ttl,
            )

        if enable_semantic_index:
            index_path = self.cache_dir / "index.db" if self.cache_dir else None
            self.semantic_index = SemanticIndex(index_path=index_path)

        if enable_analysis_cache:
            db_path = self.cache_dir / "analysis.db" if self.cache_dir else None
            self.analysis_cache = AnalysisResultCache(
                db_path=db_path,
                default_ttl=analysis_cache_ttl,
            )

        if enable_compression:
            self.compressor = ContextCompressor()

        # 统计
        self._stats = CacheStatistics()
        self._lock = threading.RLock()

        # 是否启用
        self._enabled = True

    @property
    def enabled(self) -> bool:
        """是否启用缓存"""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        """设置启用状态"""
        self._enabled = value

    def get_file_content(
        self,
        file_path: str | Path,
        use_cache: bool | None = None,
    ) -> str | None:
        """
        获取文件内容（带缓存）

        Args:
            file_path: 文件路径
            use_cache: 是否使用缓存，None 使用默认设置

        Returns:
            文件内容，失败返回 None
        """
        if use_cache is None:
            use_cache = self._enabled

        if not use_cache or not self.file_cache:
            # 直接读取文件
            try:
                return Path(file_path).read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                return None

        return self.file_cache.get_or_read(file_path)

    def invalidate_file_cache(self, file_path: str | Path) -> None:
        """使文件缓存失效"""
        if self.file_cache:
            self.file_cache.invalidate(file_path)

        # 同时使相关的分析缓存失效
        if self.analysis_cache:
            self.analysis_cache.invalidate_by_file(str(file_path))

    def build_semantic_index(
        self,
        file_paths: list[str | Path],
        incremental: bool = True,
    ) -> dict[str, Any]:
        """
        构建语义索引

        Args:
            file_paths: 要索引的文件列表
            incremental: 是否增量更新

        Returns:
            构建统计信息
        """
        if not self.semantic_index:
            return {"error": "Semantic index not enabled"}

        start_time = time.time()
        stats = self.semantic_index.build_index(file_paths, incremental)
        build_time = (time.time() - start_time) * 1000

        with self._lock:
            self._stats.index_build_time_ms = build_time
            self._stats.index_symbol_count = stats.get("symbol_count", 0)
            self._stats.index_file_count = stats.get("indexed_files", 0)

        return stats

    def query_symbol(
        self,
        name: str,
        symbol_type: str | None = None,
        limit: int = 20,
    ) -> list[Symbol]:
        """
        查询符号

        Args:
            name: 符号名称
            symbol_type: 符号类型过滤
            limit: 最大返回数量

        Returns:
            符号列表
        """
        if not self.semantic_index:
            return []

        from .types import SymbolType

        stype = SymbolType(symbol_type) if symbol_type else None
        return self.semantic_index.query_symbol(name, stype, limit)

    def get_analysis_result(
        self,
        query_type: str,
        params: dict[str, Any],
        file_paths: list[str | Path],
        analyzer: callable,
        use_cache: bool | None = None,
    ) -> Any:
        """
        获取分析结果（带缓存）

        Args:
            query_type: 查询类型
            params: 查询参数
            file_paths: 依赖的文件路径
            analyzer: 分析函数（缓存未命中时调用）
            use_cache: 是否使用缓存

        Returns:
            分析结果
        """
        if use_cache is None:
            use_cache = self._enabled

        if not use_cache or not self.analysis_cache:
            # 直接执行分析
            return analyzer(**params)

        # 计算文件 hashes
        file_hashes = {}
        for fp in file_paths:
            from .types import FileMetadata
            meta = FileMetadata.from_path(Path(fp))
            if meta:
                file_hashes[str(Path(fp).resolve())] = meta.content_hash

        # 构建查询
        query = AnalysisQuery(
            query_type=query_type,
            params=params,
            file_hashes=file_hashes,
        )

        # 尝试获取缓存
        result = self.analysis_cache.get(query)
        if result is not None:
            with self._lock:
                self._stats.analysis_cache_hits += 1
            return result

        # 缓存未命中，执行分析
        with self._lock:
            self._stats.analysis_cache_misses += 1

        result = analyzer(**params)

        # 缓存结果
        self.analysis_cache.put(query, result)

        return result

    def compress_context(
        self,
        content: str,
        max_tokens: int | None = None,
        file_path: str | None = None,
    ) -> str:
        """
        压缩上下文

        Args:
            content: 原始内容
            max_tokens: 最大 token 数
            file_path: 文件路径（用于选择压缩策略）

        Returns:
            压缩后的内容
        """
        if not self.compressor or not self._enabled:
            return content

        max_tokens = max_tokens or 500

        result = self.compressor.compress_file_content(
            content,
            max_tokens=max_tokens,
            file_path=file_path,
        )

        with self._lock:
            self._stats.compression_ratio = result.reduction_ratio
            self._stats.tokens_saved += result.original_tokens - result.compressed_tokens

        return result.content

    def compress_conversation(
        self,
        messages: list[dict[str, Any]],
        max_tokens: int = 2000,
    ) -> list[dict[str, Any]]:
        """
        压缩对话历史

        Args:
            messages: 消息列表
            max_tokens: 最大 token 数

        Returns:
            压缩后的消息列表
        """
        if not self.compressor or not self._enabled:
            return messages

        return self.compressor.compress_conversation(messages, max_tokens)

    def get_statistics(self) -> CacheStatistics:
        """获取统计信息"""
        with self._lock:
            stats = self._stats

            # 合并各组件统计
            if self.file_cache:
                fc_stats = self.file_cache.get_statistics()
                stats.file_cache_hits = fc_stats.file_cache_hits
                stats.file_cache_misses = fc_stats.file_cache_misses
                stats.file_cache_size = fc_stats.file_cache_size
                stats.file_cache_entries = fc_stats.file_cache_entries

            if self.analysis_cache:
                self.analysis_cache.get_statistics()
                # 分析缓存统计已直接更新

            return stats

    def clear_all_cache(self) -> None:
        """清空所有缓存"""
        if self.file_cache:
            self.file_cache.clear()

        if self.semantic_index:
            self.semantic_index.clear()

        if self.analysis_cache:
            self.analysis_cache.clear()

        with self._lock:
            self._stats = CacheStatistics()

    def cleanup(self) -> None:
        """清理过期缓存"""
        if self.file_cache:
            self.file_cache.cleanup_expired()

        # 分析缓存的清理在 put 时自动进行

    def get_cache_info(self) -> dict[str, Any]:
        """获取缓存信息摘要"""
        info = {
            "enabled": self._enabled,
            "cache_dir": str(self.cache_dir) if self.cache_dir else None,
            "components": {
                "file_cache": self.file_cache is not None,
                "semantic_index": self.semantic_index is not None,
                "analysis_cache": self.analysis_cache is not None,
                "compressor": self.compressor is not None,
            },
        }

        # 添加统计
        stats = self.get_statistics()
        info["statistics"] = stats.to_dict()

        return info
