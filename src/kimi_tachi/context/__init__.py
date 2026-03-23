"""
Context Cache Module

Phase 2.4: 上下文缓存优化

提供文件内容缓存、语义索引、分析结果缓存、上下文压缩等功能。

设计原则:
1. 隐私优先: 全部本地存储，不上传代码
2. 安全降级: 任何环节失败都回退到原始行为
3. 渐进增强: 默认轻量，高级功能可选开启
4. 可观测性: 所有指标可测量、可验证

使用示例:
    from kimi_tachi.context import ContextCacheManager

    cache = ContextCacheManager(
        cache_dir=Path("~/.kimi-tachi/cache"),
        enable_semantic_index=True,
    )

    # 文件读取（自动缓存）
    content = cache.get_file_content("src/main.py")

    # 符号查询
    symbols = cache.query_symbol("process_data")
"""

from __future__ import annotations

from .analysis_cache import AnalysisResultCache
from .compressor import ContextCompressor

# 核心组件
from .file_cache import FileContentCache

# 管理器
from .manager import ContextCacheManager
from .semantic_index import SemanticIndex

# 基础类型
from .types import (
    CacheEntry,
    CacheStatistics,
    FileMetadata,
    Symbol,
    SymbolType,
)

__all__ = [
    # 类型
    "CacheEntry",
    "CacheStatistics",
    "FileMetadata",
    "Symbol",
    "SymbolType",
    # 组件
    "FileContentCache",
    "SemanticIndex",
    "AnalysisResultCache",
    "ContextCompressor",
    # 管理器
    "ContextCacheManager",
]
