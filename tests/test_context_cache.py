"""
Tests for context cache module
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from kimi_tachi.context import (
    CacheStatistics,
    ContextCacheManager,
    FileContentCache,
    FileMetadata,
    Symbol,
    SymbolType,
)


class TestFileMetadata:
    """测试文件元数据"""

    def test_from_existing_file(self, tmp_path: Path):
        """测试从存在的文件创建元数据"""
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")
        
        meta = FileMetadata.from_path(test_file)
        
        assert meta is not None
        assert meta.path == str(test_file.resolve())
        assert meta.size == len("print('hello')")
        assert meta.content_hash is not None
    
    def test_from_nonexistent_file(self, tmp_path: Path):
        """测试从不存在的文件创建元数据"""
        test_file = tmp_path / "nonexistent.py"
        
        meta = FileMetadata.from_path(test_file)
        
        assert meta is None
    
    def test_is_modified(self, tmp_path: Path):
        """测试文件修改检测"""
        test_file = tmp_path / "test.py"
        test_file.write_text("version 1")
        
        meta1 = FileMetadata.from_path(test_file)
        
        # 修改文件
        test_file.write_text("version 2")
        meta2 = FileMetadata.from_path(test_file)
        
        assert meta1.is_modified(meta2)


class TestFileContentCache:
    """测试文件内容缓存"""

    def test_basic_cache_operations(self, tmp_path: Path):
        """测试基本缓存操作"""
        cache = FileContentCache(memory_limit=1024 * 1024)
        
        test_file = tmp_path / "test.py"
        test_content = "def hello():\n    print('world')"
        test_file.write_text(test_content)
        
        # 首次读取（缓存未命中）
        content1 = cache.get_or_read(test_file)
        assert content1 == test_content
        
        stats1 = cache.get_statistics()
        assert stats1.file_cache_misses == 1
        assert stats1.file_cache_hits == 0
        
        # 第二次读取（缓存命中）
        content2 = cache.get_or_read(test_file)
        assert content2 == test_content
        
        stats2 = cache.get_statistics()
        assert stats2.file_cache_hits == 1
    
    def test_cache_invalidation_on_modify(self, tmp_path: Path):
        """测试文件修改后缓存失效"""
        cache = FileContentCache(memory_limit=1024 * 1024)
        
        test_file = tmp_path / "test.py"
        test_file.write_text("version 1")
        
        # 首次读取
        cache.get_or_read(test_file)
        
        # 修改文件
        test_file.write_text("version 2")
        
        # 再次读取（应该重新读取文件）
        content = cache.get_or_read(test_file)
        assert content == "version 2"
    
    def test_disk_cache_persistence(self, tmp_path: Path):
        """测试磁盘缓存持久化"""
        cache_dir = tmp_path / "cache"
        
        # 第一个缓存实例
        cache1 = FileContentCache(
            memory_limit=1024 * 1024,
            disk_cache_dir=cache_dir,
        )
        
        test_file = tmp_path / "test.py"
        test_file.write_text("persistent content")
        
        cache1.get_or_read(test_file)
        
        # 创建新的缓存实例（模拟重启）
        cache2 = FileContentCache(
            memory_limit=1024 * 1024,
            disk_cache_dir=cache_dir,
        )
        
        # 应该从磁盘缓存读取
        content = cache2.get_or_read(test_file)
        assert content == "persistent content"
        
        stats = cache2.get_statistics()
        assert stats.file_cache_hits >= 1


class TestContextCacheManager:
    """测试上下文缓存管理器"""

    def test_manager_initialization(self, tmp_path: Path):
        """测试管理器初始化"""
        manager = ContextCacheManager(
            cache_dir=tmp_path / "cache",
            enable_file_cache=True,
            enable_semantic_index=True,
            enable_analysis_cache=True,
            enable_compression=True,
        )
        
        info = manager.get_cache_info()
        
        assert info["enabled"] is True
        assert info["components"]["file_cache"] is True
        assert info["components"]["semantic_index"] is True
        assert info["components"]["analysis_cache"] is True
        assert info["components"]["compressor"] is True
    
    def test_file_content_caching(self, tmp_path: Path):
        """测试文件内容缓存功能"""
        manager = ContextCacheManager(cache_dir=tmp_path / "cache")
        
        test_file = tmp_path / "test.py"
        test_file.write_text("def test(): pass")
        
        # 首次读取
        content1 = manager.get_file_content(test_file)
        assert content1 == "def test(): pass"
        
        # 第二次读取（应该命中缓存）
        content2 = manager.get_file_content(test_file)
        assert content2 == "def test(): pass"
        
        stats = manager.get_statistics()
        assert stats.file_cache_hits >= 1
    
    def test_context_compression(self, tmp_path: Path):
        """测试上下文压缩"""
        manager = ContextCacheManager(cache_dir=tmp_path / "cache")
        
        # 长内容
        long_content = "def function():\n    pass\n" * 100
        
        compressed = manager.compress_context(
            long_content,
            max_tokens=100,
            file_path="test.py",
        )
        
        # 压缩后应该更短
        assert len(compressed) < len(long_content)
        
        stats = manager.get_statistics()
        assert stats.compression_ratio > 0
    
    def test_disabled_cache(self, tmp_path: Path):
        """测试禁用缓存"""
        manager = ContextCacheManager(
            cache_dir=tmp_path / "cache",
            enable_file_cache=False,
        )
        
        manager.enabled = False
        
        test_file = tmp_path / "test.py"
        test_file.write_text("content")
        
        # 禁用缓存后应该直接读取文件
        content = manager.get_file_content(test_file)
        assert content == "content"


class TestCacheStatistics:
    """测试缓存统计"""

    def test_hit_rate_calculation(self):
        """测试命中率计算"""
        stats = CacheStatistics()
        stats.file_cache_hits = 80
        stats.file_cache_misses = 20
        
        assert stats.file_cache_hit_rate == 80.0
    
    def test_zero_hit_rate(self):
        """测试零命中率"""
        stats = CacheStatistics()
        
        assert stats.file_cache_hit_rate == 0.0
        assert stats.analysis_cache_hit_rate == 0.0
    
    def test_to_dict(self):
        """测试转换为字典"""
        stats = CacheStatistics()
        stats.file_cache_hits = 80
        stats.file_cache_misses = 20
        stats.file_cache_size = 1024 * 1024
        
        data = stats.to_dict()
        
        assert "file_cache" in data
        assert data["file_cache"]["hits"] == 80
        assert data["file_cache"]["hit_rate"] == 80.0


class TestSymbol:
    """测试符号类型"""

    def test_symbol_creation(self):
        """测试符号创建"""
        symbol = Symbol(
            name="process_data",
            type=SymbolType.FUNCTION,
            file_path="/path/to/file.py",
            line_start=10,
            line_end=20,
            docstring="Process the data.",
            signature="def process_data(data: dict) -> dict",
        )
        
        assert symbol.name == "process_data"
        assert symbol.type == SymbolType.FUNCTION
        assert symbol.line_start == 10
    
    def test_symbol_to_dict(self):
        """测试符号序列化"""
        symbol = Symbol(
            name="MyClass",
            type=SymbolType.CLASS,
            file_path="/path/to/file.py",
            line_start=1,
            line_end=50,
        )
        
        data = symbol.to_dict()
        
        assert data["name"] == "MyClass"
        assert data["type"] == "class"
        assert data["line_start"] == 1
    
    def test_symbol_from_dict(self):
        """测试符号反序列化"""
        data = {
            "name": "helper_function",
            "type": "function",
            "file_path": "/path/to/file.py",
            "line_start": 5,
            "line_end": 15,
            "docstring": "A helper function.",
            "signature": None,
            "parent": None,
        }
        
        symbol = Symbol.from_dict(data)
        
        assert symbol.name == "helper_function"
        assert symbol.type == SymbolType.FUNCTION
        assert symbol.docstring == "A helper function."


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
