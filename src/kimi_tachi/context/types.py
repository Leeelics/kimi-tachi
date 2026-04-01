"""
Context Cache 基础类型定义
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class SymbolType(Enum):
    """符号类型"""

    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"
    VARIABLE = "variable"
    CONSTANT = "constant"
    IMPORT = "import"
    MODULE = "module"


@dataclass(frozen=True)
class FileMetadata:
    """文件元数据"""

    path: str
    size: int
    mtime: float  # 修改时间
    content_hash: str  # SHA256

    @classmethod
    def from_path(cls, path: Path) -> FileMetadata | None:
        """从文件路径创建元数据"""
        try:
            stat = path.stat()
            content = path.read_bytes()
            content_hash = hashlib.sha256(content).hexdigest()[:16]

            return cls(
                path=str(path.resolve()),
                size=stat.st_size,
                mtime=stat.st_mtime,
                content_hash=content_hash,
            )
        except OSError:
            return None

    def is_modified(self, other: FileMetadata) -> bool:
        """检查文件是否修改"""
        return self.mtime != other.mtime or self.content_hash != other.content_hash


@dataclass
class Symbol:
    """代码符号"""

    name: str
    type: SymbolType
    file_path: str
    line_start: int
    line_end: int = 0
    docstring: str | None = None
    signature: str | None = None  # 函数签名
    parent: str | None = None  # 父类/父函数

    # 关系
    calls: list[str] = field(default_factory=list)  # 调用的函数
    references: list[str] = field(default_factory=list)  # 被引用处

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "type": self.type.value,
            "file_path": self.file_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "docstring": self.docstring,
            "signature": self.signature,
            "parent": self.parent,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Symbol:
        """从字典创建"""
        return cls(
            name=data["name"],
            type=SymbolType(data["type"]),
            file_path=data["file_path"],
            line_start=data["line_start"],
            line_end=data.get("line_end", 0),
            docstring=data.get("docstring"),
            signature=data.get("signature"),
            parent=data.get("parent"),
        )


@dataclass
class CacheEntry:
    """缓存条目"""

    key: str
    value: Any
    created_at: datetime = field(default_factory=datetime.now)
    accessed_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    ttl_seconds: int | None = None  # None 表示永久

    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl_seconds is None:
            return False
        elapsed = (datetime.now() - self.created_at).total_seconds()
        return elapsed > self.ttl_seconds

    def touch(self) -> None:
        """更新访问时间"""
        self.accessed_at = datetime.now()
        self.access_count += 1


@dataclass
class CacheStatistics:
    """缓存统计信息"""

    # 文件缓存
    file_cache_hits: int = 0
    file_cache_misses: int = 0
    file_cache_size: int = 0  # bytes
    file_cache_entries: int = 0

    # 分析缓存
    analysis_cache_hits: int = 0
    analysis_cache_misses: int = 0

    # 索引
    index_symbol_count: int = 0
    index_file_count: int = 0
    index_build_time_ms: float = 0.0

    # 压缩
    compression_ratio: float = 0.0  # 压缩率
    tokens_saved: int = 0

    @property
    def file_cache_hit_rate(self) -> float:
        """文件缓存命中率"""
        total = self.file_cache_hits + self.file_cache_misses
        if total == 0:
            return 0.0
        return self.file_cache_hits / total * 100

    @property
    def analysis_cache_hit_rate(self) -> float:
        """分析缓存命中率"""
        total = self.analysis_cache_hits + self.analysis_cache_misses
        if total == 0:
            return 0.0
        return self.analysis_cache_hits / total * 100

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "file_cache": {
                "hits": self.file_cache_hits,
                "misses": self.file_cache_misses,
                "hit_rate": round(self.file_cache_hit_rate, 2),
                "size_mb": round(self.file_cache_size / 1024 / 1024, 2),
                "entries": self.file_cache_entries,
            },
            "analysis_cache": {
                "hits": self.analysis_cache_hits,
                "misses": self.analysis_cache_misses,
                "hit_rate": round(self.analysis_cache_hit_rate, 2),
            },
            "index": {
                "symbols": self.index_symbol_count,
                "files": self.index_file_count,
                "build_time_ms": round(self.index_build_time_ms, 2),
            },
            "compression": {
                "ratio": round(self.compression_ratio, 2),
                "tokens_saved": self.tokens_saved,
            },
        }
