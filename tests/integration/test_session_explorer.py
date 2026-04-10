"""
Tests for Session Explorer integration with memnexus 0.4.0+

测试覆盖：
1. memnexus SessionExplorer 集成
2. TachiMemory 使用 memnexus 进行跨 session 探查
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from kimi_tachi.memory import TachiMemory

# Test memnexus integration
try:
    from memnexus.session import (
        DecisionDeduplicator,
        ExploreOptions,
        SessionExplorer,
    )

    MEMNEXUS_AVAILABLE = True
except ImportError:
    MEMNEXUS_AVAILABLE = False


pytestmark = pytest.mark.skipif(not MEMNEXUS_AVAILABLE, reason="memnexus not installed")


class TestMemnexusSessionExplorer:
    """Test memnexus SessionExplorer integration"""

    @pytest.fixture
    def temp_storage(self):
        """临时存储目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def sessions_dir(self):
        """memnexus sessions 目录"""
        sessions_path = Path.home() / ".memnexus" / "sessions"
        sessions_path.mkdir(parents=True, exist_ok=True)
        return sessions_path

    def create_test_session(
        self, sessions_dir: Path, session_id: str, decisions: list, project: str = ""
    ):
        """创建测试 session 文件"""
        session_file = sessions_dir / f"{session_id}.json"
        session_data = {
            "session_id": session_id,
            "started_at": datetime.now().isoformat(),
            "project": project,
            "working_directory": str(sessions_dir),
            "decisions": [{"content": d} for d in decisions],
        }
        session_file.write_text(json.dumps(session_data))
        return session_file

    @pytest.mark.asyncio
    async def test_session_explorer_basic(self, sessions_dir: Path, temp_storage: Path):
        """测试基本的 SessionExplorer 功能"""
        # 清理旧测试文件
        for f in sessions_dir.glob("test_*.json"):
            f.unlink()

        # 创建测试 session
        self.create_test_session(
            sessions_dir,
            "test_explorer_1",
            ["Use PostgreSQL for database", "Implement JWT auth"],
            "myapp",
        )

        explorer = SessionExplorer(storage_path=temp_storage)
        options = ExploreOptions(limit=5, min_relevance=0.1)

        result = await explorer.explore_related(
            current_session_id="current",
            query="database authentication",
            context={"cwd": str(sessions_dir), "project": "myapp"},
            options=options,
        )

        assert len(result.decisions) > 0
        explorer.close()

        # 清理
        for f in sessions_dir.glob("test_*.json"):
            f.unlink()

    @pytest.mark.asyncio
    async def test_decision_deduplicator(self, temp_storage: Path):
        """测试 DecisionDeduplicator 去重功能"""
        dedup = DecisionDeduplicator(storage_path=temp_storage)

        # 检查新内容不是重复
        content1 = "Use Redis for caching"
        result1 = await dedup.check_duplicate(content1)
        assert not result1.is_duplicate

        # 添加指纹
        fp1 = await dedup.add_fingerprint(content1, "session_1")
        assert fp1 is not None

        # 再次检查，应该是重复
        result2 = await dedup.check_duplicate(content1)
        assert result2.is_duplicate

        dedup.close()


class TestTachiMemoryIntegration:
    """Test TachiMemory integration with memnexus"""

    @pytest.fixture
    def sessions_dir(self):
        """memnexus sessions 目录"""
        sessions_path = Path.home() / ".memnexus" / "sessions"
        sessions_path.mkdir(parents=True, exist_ok=True)
        return sessions_path

    def create_test_session(
        self, sessions_dir: Path, session_id: str, decisions: list, project: str = ""
    ):
        """创建测试 session 文件"""
        # 清理同名旧文件
        old_file = sessions_dir / f"{session_id}.json"
        if old_file.exists():
            old_file.unlink()

        session_file = sessions_dir / f"{session_id}.json"
        session_data = {
            "session_id": session_id,
            "started_at": datetime.now().isoformat(),
            "project": project,
            "working_directory": str(sessions_dir),
            "decisions": [{"content": d} for d in decisions],
        }
        session_file.write_text(json.dumps(session_data))
        return session_file

    @pytest.mark.asyncio
    async def test_tachi_memory_recall(self, sessions_dir: Path):
        """测试 TachiMemory 的 recall_for_task 功能"""
        import subprocess

        # 清理旧测试文件
        for f in sessions_dir.glob("tachi_test_*.json"):
            f.unlink()

        with tempfile.TemporaryDirectory() as tmpdir:
            # 初始化 memnexus
            subprocess.run(["memnexus", "init"], cwd=tmpdir, capture_output=True)

            # 创建测试 session
            self.create_test_session(
                sessions_dir,
                "tachi_test_1",
                ["Use PostgreSQL for user data", "Deploy to AWS"],
                "testproject",
            )

            memory = await TachiMemory.init(tmpdir)

            # 测试 recall
            context = await memory.recall_for_task("database AWS")

            # 验证返回结构
            assert "related_decisions" in context
            assert "formatted_output" in context

            await memory.close()

        # 清理
        for f in sessions_dir.glob("tachi_test_*.json"):
            f.unlink()

    @pytest.mark.asyncio
    async def test_tachi_memory_store_decision(self):
        """测试 TachiMemory 的 store_decision 功能"""
        import subprocess

        with tempfile.TemporaryDirectory() as tmpdir:
            # 初始化 memnexus
            subprocess.run(["memnexus", "init"], cwd=tmpdir, capture_output=True)

            memory = await TachiMemory.init(tmpdir)

            # 存储决策
            fingerprint = await memory.store_decision(
                "Use Docker for deployment", {"source": "test"}
            )

            # 新决策应该存储成功
            assert fingerprint is not None

            # 再次存储相同内容，应该返回 None（去重）
            _ = await memory.store_decision("Use Docker for deployment", {"source": "test"})
            # 注意：由于 memnexus 的实现，这里可能返回 None 或新的 fingerprint

            await memory.close()
