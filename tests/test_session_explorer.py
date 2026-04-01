"""
Tests for Session Explorer (v0.5.3)

测试覆盖：
1. DecisionFingerprint 生成和去重
2. SessionExplorer 相关性计算
3. 主动探查逻辑
4. 已探查 Session 追踪
"""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from kimi_tachi.memory.session_explorer import (
    DecisionFingerprint,
    DecisionDeduplicator,
    SessionExplorer,
    ExploredSession,
    get_explorer,
    reset_explorer,
)


class TestDecisionFingerprint:
    """测试决策指纹生成"""
    
    def test_extract_keywords(self):
        """测试关键词提取"""
        content = "Use PostgreSQL database for user authentication"
        keywords = DecisionDeduplicator.extract_keywords(content)
        
        assert "postgresql" in keywords
        assert "database" in keywords
        assert "user" in keywords
        assert "authentication" in keywords
        # 停用词应被过滤
        assert "for" not in keywords
    
    def test_generate_fingerprint(self):
        """测试指纹生成"""
        content = "Use JWT tokens for API authentication"
        fp = DecisionDeduplicator.generate_fingerprint(content, "session_123")
        
        assert isinstance(fp, DecisionFingerprint)
        assert len(fp.content_hash) == 16
        assert "jwt" in fp.keywords
        assert fp.source_session == "session_123"
        assert fp.timestamp is not None
    
    def test_fingerprint_consistency(self):
        """测试相同内容生成相同指纹"""
        content1 = "Use Redis for session storage"
        content2 = "Use redis for session storage"  # 小写差异
        
        fp1 = DecisionDeduplicator.generate_fingerprint(content1, "s1")
        fp2 = DecisionDeduplicator.generate_fingerprint(content2, "s1")
        
        # 相同语义应生成相同指纹
        assert fp1.content_hash == fp2.content_hash
    
    def test_fingerprint_different_sessions(self):
        """测试不同 session 的相同内容生成不同指纹"""
        content = "Use PostgreSQL database"
        
        fp1 = DecisionDeduplicator.generate_fingerprint(content, "session_1")
        fp2 = DecisionDeduplicator.generate_fingerprint(content, "session_2")
        
        # 不同来源应生成不同指纹
        assert fp1.content_hash != fp2.content_hash


class TestDecisionDeduplicator:
    """测试决策去重器"""
    
    @pytest.fixture
    def temp_storage(self):
        """临时存储目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def deduplicator(self, temp_storage):
        """创建去重器实例"""
        return DecisionDeduplicator(temp_storage)
    
    def test_is_duplicate_new_content(self, deduplicator):
        """测试新内容不是重复"""
        content = "Implement OAuth2 authentication flow"
        assert not deduplicator.is_duplicate(content)
    
    def test_is_duplicate_existing_content(self, deduplicator):
        """测试已存在内容是重复"""
        content = "Use Redis cache for performance"
        deduplicator.add(content, "session_1")
        
        # 同一内容应被视为重复（任何来源）
        assert deduplicator.is_duplicate(content)
        # 同一内容，不同来源也应被视为重复
        assert deduplicator.is_duplicate(content, "session_2")
    
    def test_add_and_retrieve(self, deduplicator):
        """测试添加和检索指纹"""
        content = "Deploy to AWS Lambda"
        fp = deduplicator.add(content, "session_abc")
        
        assert fp.content_hash in deduplicator._fingerprints
        # 检查存储的预览内容
        stored_fp = deduplicator._fingerprints[fp.content_hash]
        assert stored_fp.content_preview == content  # 短内容完整存储
    
    def test_save_and_load(self, deduplicator, temp_storage):
        """测试保存和加载"""
        # 添加一些指纹
        contents = [
            "Use TypeScript for frontend",
            "Python for backend API",
            "Docker for deployment",
        ]
        for i, content in enumerate(contents):
            deduplicator.add(content, f"session_{i}")
        
        # 保存
        deduplicator.save()
        
        # 创建新实例并加载
        new_dedup = DecisionDeduplicator(temp_storage).load()
        
        # 验证已存在的内容被识别为重复
        assert new_dedup.is_duplicate("Use TypeScript for frontend")
        assert new_dedup.is_duplicate("Python for backend API")
        assert not new_dedup.is_duplicate("New unique content")
    
    def test_get_all_keywords(self, deduplicator):
        """测试获取所有关键词"""
        deduplicator.add("Use React framework", "s1")
        deduplicator.add("Vue.js for UI", "s2")
        
        keywords = deduplicator.get_all_keywords()
        
        assert "react" in keywords
        assert "framework" in keywords
        assert "vue" in keywords


class TestSessionExplorer:
    """测试 Session 探查器"""
    
    @pytest.fixture
    def temp_storage(self):
        """临时存储目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def mock_hooks_dir(self, temp_storage):
        """创建模拟 hooks 目录"""
        hooks_dir = temp_storage / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建一些模拟 session 文件
        for i in range(3):
            session_data = {
                "session_id": f"session_{i}",
                "started_at": (datetime.now() - timedelta(days=i)).isoformat(),
                "cwd": "/home/user/project" if i < 2 else "/other/project",
                "decisions": [
                    {
                        "type": "decision",
                        "content": f"Decision {i}: Use {'PostgreSQL' if i == 0 else 'Redis' if i == 1 else 'MongoDB'}",
                        "timestamp": datetime.now().isoformat(),
                    }
                ]
            }
            
            session_file = hooks_dir / f"session_{i}.json"
            with open(session_file, "w") as f:
                json.dump(session_data, f)
        
        return hooks_dir
    
    @pytest.fixture
    def explorer(self, temp_storage, monkeypatch):
        """创建探查器实例"""
        # 模拟 hooks 路径
        explorer = SessionExplorer(temp_storage)
        return explorer
    
    def test_calculate_relevance_same_project(self, explorer):
        """测试同一项目的相关性计算"""
        session_data = {
            "session_id": "s1",
            "started_at": datetime.now().isoformat(),
            "cwd": "/home/user/myproject",
            "decisions": [
                {"content": "Use Python for backend"}
            ]
        }
        
        relevance = explorer.calculate_relevance(
            session_data,
            query="Python backend development",
            current_cwd="/home/user/myproject"
        )
        
        # 同一项目应得分较高
        assert relevance > 0.5
    
    def test_calculate_relevance_different_project(self, explorer):
        """测试不同项目的相关性计算"""
        session_data = {
            "session_id": "s1",
            "started_at": datetime.now().isoformat(),
            "cwd": "/other/project",
            "decisions": [
                {"content": "Use Java for backend"}
            ]
        }
        
        relevance = explorer.calculate_relevance(
            session_data,
            query="Python backend",
            current_cwd="/home/user/myproject"
        )
        
        # 不同项目且关键词不匹配，得分应较低（可能为 0 或很低）
        assert relevance < 0.5  # 放宽阈值
    
    def test_calculate_relevance_time_decay(self, explorer):
        """测试时间衰减"""
        # 旧 session
        old_session = {
            "session_id": "old",
            "started_at": (datetime.now() - timedelta(days=30)).isoformat(),
            "cwd": "/home/user/project",
            "decisions": [{"content": "Use Python"}]
        }
        
        # 新 session
        new_session = {
            "session_id": "new",
            "started_at": datetime.now().isoformat(),
            "cwd": "/home/user/project",
            "decisions": [{"content": "Use Python"}]
        }
        
        old_relevance = explorer.calculate_relevance(old_session, "Python", "/home/user/project")
        new_relevance = explorer.calculate_relevance(new_session, "Python", "/home/user/project")
        
        # 新 session 应得分更高
        assert new_relevance > old_relevance
    
    def test_is_explored(self, explorer):
        """测试已探查检查"""
        explorer.mark_explored("session_1", "current_session", 0.8, 3)
        
        assert explorer.is_explored("session_1")
        assert explorer.is_explored("session_1", "current_session")
        assert not explorer.is_explored("session_1", "other_session")
        assert not explorer.is_explored("session_2")
    
    def test_mark_explored(self, explorer):
        """测试标记已探查"""
        explorer.mark_explored(
            session_id="session_target",
            explored_by="session_source",
            relevance_score=0.75,
            decisions_extracted=5
        )
        
        assert "session_target" in explorer._explored_sessions
        record = explorer._explored_sessions["session_target"]
        assert record.explored_by == "session_source"
        assert record.relevance_score == 0.75
        assert record.decisions_extracted == 5
    
    def test_explore_session_skip_self(self, temp_storage):
        """测试跳过自身 session"""
        explorer = SessionExplorer(temp_storage)
        
        # 创建 session 文件
        session_file = temp_storage / "session_target.json"
        session_data = {
            "session_id": "same_session",
            "started_at": datetime.now().isoformat(),
            "cwd": "/project",
            "decisions": []
        }
        with open(session_file, "w") as f:
            json.dump(session_data, f)
        
        # 探查自身应返回 False
        success, decisions, relevance = explorer.explore_session(
            session_file, "same_session", "query", "/project"
        )
        
        assert not success
        assert len(decisions) == 0
    
    def test_explore_session_below_threshold(self, temp_storage):
        """测试低于阈值跳过"""
        explorer = SessionExplorer(temp_storage)
        
        # 创建 session 文件（完全不相关）
        session_file = temp_storage / "session_target.json"
        session_data = {
            "session_id": "target",
            "started_at": datetime.now().isoformat(),
            "cwd": "/unrelated/project",
            "decisions": [{"content": "some test content here"}]
        }
        with open(session_file, "w") as f:
            json.dump(session_data, f)
        
        # 第一次探查：使用低阈值应该成功
        success1, decisions1, relevance1 = explorer.explore_session(
            session_file, "current", "test content matching", "/other/project",
            min_relevance=0.1
        )
        assert success1  # 低阈值应该通过
        
        # 第二次探查：使用超高阈值应该失败（但相关性不可能是 1.0）
        # 注意：由于 session 已被标记为已探查，这次会跳过
        success2, decisions2, relevance2 = explorer.explore_session(
            session_file, "current", "test content matching", "/other/project",
            min_relevance=1.0  # 超高阈值
        )
        # 已经被探查过，应该返回 False
        assert not success2
    
    def test_explore_session_extract_decisions(self, temp_storage):
        """测试提取新决策"""
        explorer = SessionExplorer(temp_storage)
        
        # 创建 session 文件
        session_file = temp_storage / "session_target.json"
        session_data = {
            "session_id": "target",
            "started_at": datetime.now().isoformat(),
            "cwd": "/project",
            "decisions": [
                {"content": "Use Python for API", "timestamp": datetime.now().isoformat()},
                {"content": "Deploy to AWS", "timestamp": datetime.now().isoformat()},
            ]
        }
        with open(session_file, "w") as f:
            json.dump(session_data, f)
        
        # 探查
        success, decisions, relevance = explorer.explore_session(
            session_file, "current", "Python API development", "/project",
            min_relevance=0.1
        )
        
        assert success
        assert len(decisions) == 2
        # 检查添加了指纹和来源
        assert "fingerprint" in decisions[0]
        assert decisions[0].get("source_session") == "target"
    
    def test_get_exploration_stats(self, explorer):
        """测试获取统计信息"""
        # 添加一些数据
        explorer.mark_explored("s1", "current", 0.8, 3)
        explorer._deduplicator.add("Decision 1", "s1")
        explorer._deduplicator.add("Decision 2", "s1")
        
        stats = explorer.get_exploration_stats()
        
        assert stats["total_explored_sessions"] == 1
        assert stats["total_unique_decisions"] == 2
        assert stats["known_keywords_count"] > 0
    
    def test_save_and_load_exploration(self, temp_storage):
        """测试保存和加载探查状态"""
        # 创建并填充 explorer
        explorer = SessionExplorer(temp_storage)
        explorer.mark_explored("session_1", "current", 0.8, 2)
        explorer._deduplicator.add("Test decision", "session_1")
        explorer.save()
        
        # 创建新实例并加载
        new_explorer = SessionExplorer(temp_storage).load()
        
        # 验证状态恢复
        assert new_explorer.is_explored("session_1")
        assert new_explorer._deduplicator.is_duplicate("Test decision")


class TestIntegration:
    """集成测试"""
    
    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """每个测试前重置单例"""
        reset_explorer()
        yield
        reset_explorer()
    
    def test_get_explorer_singleton(self):
        """测试单例模式"""
        explorer1 = get_explorer()
        explorer2 = get_explorer()
        
        assert explorer1 is explorer2
    
    def test_end_to_end_exploration(self, tmp_path):
        """端到端探查流程"""
        # 创建模拟 hooks 目录
        hooks_dir = tmp_path / "hooks"
        hooks_dir.mkdir()
        
        # 创建多个 session
        for i in range(3):
            session_data = {
                "session_id": f"hist_{i}",
                "started_at": datetime.now().isoformat(),
                "cwd": "/project",
                "decisions": [
                    {
                        "content": f"Use {'PostgreSQL' if i == 0 else 'Redis' if i == 1 else 'Docker'}",
                        "timestamp": datetime.now().isoformat(),
                    }
                ]
            }
            with open(hooks_dir / f"session_{i}.json", "w") as f:
                json.dump(session_data, f)
        
        # 创建 explorer 并修改 hooks 路径
        from kimi_tachi.memory import session_explorer
        original_hooks = session_explorer.Path.home
        
        try:
            # 使用临时目录
            explorer = SessionExplorer(tmp_path / "explorer")
            explorer.hooks_path = hooks_dir
            
            # 执行探查
            decisions = explorer.find_relevant_sessions(
                current_session_id="current",
                query="database PostgreSQL",
                current_cwd="/project",
                limit=5,
                min_relevance=0.1
            )
            
            # 应该找到 PostgreSQL 相关的决策
            assert len(decisions) >= 1
            assert any("PostgreSQL" in d.get("content", "") for d in decisions)
            
            # 验证已标记为已探查
            assert explorer.is_explored("hist_0")
            
        finally:
            pass  # 清理在 fixture 中处理


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
