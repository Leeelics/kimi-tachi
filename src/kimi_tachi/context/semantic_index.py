"""
语义索引

基于 tree-sitter 的代码语义索引，提供:
1. 快速符号查找
2. 代码结构分析
3. 引用关系追踪

设计原则:
- 轻量快速: 使用 tree-sitter，无需 LSP
- 增量更新: 只重新索引修改的文件
- 本地存储: SQLite 持久化
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any

from tree_sitter import Language, Parser, Tree

from .types import Symbol, SymbolType

# 初始化 Python 解析器
try:
    import tree_sitter_python as tspython
    PYTHON_LANGUAGE = Language(tspython.language())
    _PARSER_AVAILABLE = True
except ImportError:
    _PARSER_AVAILABLE = False


class SemanticIndex:
    """
    代码语义索引

    使用示例:
        index = SemanticIndex(
            index_path=Path("~/.kimi-tachi/cache/index.db"),
        )

        # 构建索引
        index.build_index(["src/**/*.py"])

        # 查询符号
        symbols = index.query_symbol("process_data")

        # 查找引用
        refs = index.find_references("process_data")
    """

    def __init__(
        self,
        index_path: Path | None = None,
        use_lsp: bool = False,  # 默认不使用 LSP
    ):
        self.index_path = index_path
        self.use_lsp = use_lsp

        # 初始化解析器
        self._parser: Parser | None = None
        if _PARSER_AVAILABLE:
            self._parser = Parser(PYTHON_LANGUAGE)

        # 初始化数据库
        if index_path:
            self._init_database()

    def _init_database(self) -> None:
        """初始化索引数据库"""
        if not self.index_path:
            return

        self.index_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.index_path) as conn:
            # 符号表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS symbols (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    line_start INTEGER NOT NULL,
                    line_end INTEGER,
                    docstring TEXT,
                    signature TEXT,
                    parent TEXT,
                    calls TEXT,  -- JSON list
                    references TEXT,  -- JSON list
                    created_at REAL NOT NULL
                )
            """)

            # 文件索引状态表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS file_index_status (
                    file_path TEXT PRIMARY KEY,
                    mtime REAL NOT NULL,
                    size INTEGER NOT NULL,
                    indexed_at REAL NOT NULL,
                    symbol_count INTEGER DEFAULT 0
                )
            """)

            # 创建索引
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_symbol_name
                ON symbols(name)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_symbol_type
                ON symbols(type)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_symbol_file
                ON symbols(file_path)
            """)

            conn.commit()

    def build_index(
        self,
        file_paths: list[str | Path],
        incremental: bool = True,
    ) -> dict[str, Any]:
        """
        构建代码索引

        Args:
            file_paths: 要索引的文件列表
            incremental: 是否增量更新（只索引修改的文件）

        Returns:
            统计信息
        """
        if not self._parser:
            return {"error": "Tree-sitter parser not available"}

        stats = {
            "total_files": len(file_paths),
            "indexed_files": 0,
            "skipped_files": 0,
            "symbol_count": 0,
            "time_ms": 0,
        }

        start_time = time.time()

        for file_path in file_paths:
            path = Path(file_path)

            if not path.exists() or path.suffix != ".py":
                continue

            # 检查是否需要重新索引
            if incremental and not self._needs_reindex(path):
                stats["skipped_files"] += 1
                continue

            # 索引文件
            try:
                symbols = self._index_file(path)
                stats["indexed_files"] += 1
                stats["symbol_count"] += len(symbols)
            except Exception:
                continue

        stats["time_ms"] = (time.time() - start_time) * 1000

        return stats

    def _needs_reindex(self, path: Path) -> bool:
        """检查文件是否需要重新索引"""
        if not self.index_path:
            return True

        try:
            stat = path.stat()

            with sqlite3.connect(self.index_path) as conn:
                cursor = conn.execute(
                    "SELECT mtime FROM file_index_status WHERE file_path = ?",
                    (str(path.resolve()),),
                )
                row = cursor.fetchone()

                if not row:
                    return True

                return stat.st_mtime > row[0]
        except (OSError, sqlite3.Error):
            return True

    def _index_file(self, path: Path) -> list[Symbol]:
        """索引单个文件"""
        content = path.read_text(encoding="utf-8")
        tree = self._parser.parse(content.encode())

        # 提取符号
        symbols = self._extract_symbols(tree, content, path)

        # 保存到数据库
        if self.index_path:
            self._save_symbols(symbols, path)

        return symbols

    def _extract_symbols(
        self,
        tree: Tree,
        content: str,
        path: Path,
    ) -> list[Symbol]:
        """从 AST 提取符号"""
        symbols = []
        root = tree.root_node
        lines = content.split("\n")

        def get_line_text(line_num: int) -> str:
            if 0 <= line_num - 1 < len(lines):
                return lines[line_num - 1].strip()
            return ""

        def extract_docstring(node) -> str | None:
            """提取文档字符串"""
            # 查找函数/类定义后的第一个字符串
            for child in node.children:
                if child.type == "expression_statement":
                    for subchild in child.children:
                        if subchild.type == "string":
                            doc = content[subchild.start_byte:subchild.end_byte]
                            return doc.strip('"\' ')
            return None

        def extract_signature(node) -> str | None:
            """提取函数签名"""
            if node.type != "function_definition":
                return None

            # 获取函数定义行
            line = get_line_text(node.start_point[0] + 1)

            # 提取到冒号前
            if ":" in line:
                return line[:line.index(":")].strip()
            return line.strip()

        def walk(node, parent_name: str | None = None):
            """遍历 AST"""
            if node.type == "function_definition":
                # 获取函数名
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = content[name_node.start_byte:name_node.end_byte]

                    symbol = Symbol(
                        name=name,
                        type=SymbolType.FUNCTION,
                        file_path=str(path.resolve()),
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                        docstring=extract_docstring(node),
                        signature=extract_signature(node),
                        parent=parent_name,
                    )
                    symbols.append(symbol)

                    # 递归处理函数内部
                    body = node.child_by_field_name("body")
                    if body:
                        for child in body.children:
                            walk(child, name)

            elif node.type == "class_definition":
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = content[name_node.start_byte:name_node.end_byte]

                    symbol = Symbol(
                        name=name,
                        type=SymbolType.CLASS,
                        file_path=str(path.resolve()),
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                        docstring=extract_docstring(node),
                        parent=parent_name,
                    )
                    symbols.append(symbol)

                    # 递归处理类内部
                    body = node.child_by_field_name("body")
                    if body:
                        for child in body.children:
                            walk(child, name)

            elif node.type == "method_definition":
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = content[name_node.start_byte:name_node.end_byte]

                    symbol = Symbol(
                        name=name,
                        type=SymbolType.METHOD,
                        file_path=str(path.resolve()),
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                        docstring=extract_docstring(node),
                        signature=extract_signature(node),
                        parent=parent_name,
                    )
                    symbols.append(symbol)

            # 递归处理其他节点
            for child in node.children:
                walk(child, parent_name)

        walk(root)
        return symbols

    def _save_symbols(self, symbols: list[Symbol], path: Path) -> None:
        """保存符号到数据库"""
        if not self.index_path:
            return

        import json

        try:
            with sqlite3.connect(self.index_path) as conn:
                # 删除旧符号
                conn.execute(
                    "DELETE FROM symbols WHERE file_path = ?",
                    (str(path.resolve()),),
                )

                # 插入新符号
                for symbol in symbols:
                    conn.execute(
                        """
                        INSERT INTO symbols
                        (name, type, file_path, line_start, line_end, docstring,
                         signature, parent, calls, references, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            symbol.name,
                            symbol.type.value,
                            symbol.file_path,
                            symbol.line_start,
                            symbol.line_end,
                            symbol.docstring,
                            symbol.signature,
                            symbol.parent,
                            json.dumps(symbol.calls),
                            json.dumps(symbol.references),
                            time.time(),
                        ),
                    )

                # 更新文件索引状态
                stat = path.stat()
                conn.execute(
                    """
                    INSERT OR REPLACE INTO file_index_status
                    (file_path, mtime, size, indexed_at, symbol_count)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        str(path.resolve()),
                        stat.st_mtime,
                        stat.st_size,
                        time.time(),
                        len(symbols),
                    ),
                )

                conn.commit()
        except sqlite3.Error:
            pass  # 索引失败不影响主流程

    def query_symbol(
        self,
        name: str,
        symbol_type: SymbolType | None = None,
        limit: int = 20,
    ) -> list[Symbol]:
        """
        查询符号

        Args:
            name: 符号名称（支持模糊匹配）
            symbol_type: 符号类型过滤
            limit: 最大返回数量

        Returns:
            符号列表
        """
        if not self.index_path:
            return []

        try:
            with sqlite3.connect(self.index_path) as conn:
                if symbol_type:
                    cursor = conn.execute(
                        """
                        SELECT name, type, file_path, line_start, line_end,
                               docstring, signature, parent
                        FROM symbols
                        WHERE name LIKE ? AND type = ?
                        ORDER BY name
                        LIMIT ?
                        """,
                        (f"%{name}%", symbol_type.value, limit),
                    )
                else:
                    cursor = conn.execute(
                        """
                        SELECT name, type, file_path, line_start, line_end,
                               docstring, signature, parent
                        FROM symbols
                        WHERE name LIKE ?
                        ORDER BY name
                        LIMIT ?
                        """,
                        (f"%{name}%", limit),
                    )

                rows = cursor.fetchall()

                return [
                    Symbol(
                        name=row[0],
                        type=SymbolType(row[1]),
                        file_path=row[2],
                        line_start=row[3],
                        line_end=row[4] or row[3],
                        docstring=row[5],
                        signature=row[6],
                        parent=row[7],
                    )
                    for row in rows
                ]
        except sqlite3.Error:
            return []

    def get_file_symbols(self, file_path: str | Path) -> list[Symbol]:
        """获取文件中的所有符号"""
        if not self.index_path:
            return []

        path = Path(file_path)

        try:
            with sqlite3.connect(self.index_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT name, type, file_path, line_start, line_end,
                           docstring, signature, parent
                    FROM symbols
                    WHERE file_path = ?
                    ORDER BY line_start
                    """,
                    (str(path.resolve()),),
                )

                rows = cursor.fetchall()

                return [
                    Symbol(
                        name=row[0],
                        type=SymbolType(row[1]),
                        file_path=row[2],
                        line_start=row[3],
                        line_end=row[4] or row[3],
                        docstring=row[5],
                        signature=row[6],
                        parent=row[7],
                    )
                    for row in rows
                ]
        except sqlite3.Error:
            return []

    def get_statistics(self) -> dict[str, Any]:
        """获取索引统计信息"""
        if not self.index_path:
            return {"error": "No index path configured"}

        try:
            with sqlite3.connect(self.index_path) as conn:
                # 符号统计
                cursor = conn.execute("SELECT COUNT(*) FROM symbols")
                symbol_count = cursor.fetchone()[0]

                # 文件统计
                cursor = conn.execute("SELECT COUNT(*) FROM file_index_status")
                file_count = cursor.fetchone()[0]

                # 类型分布
                cursor = conn.execute(
                    "SELECT type, COUNT(*) FROM symbols GROUP BY type"
                )
                type_distribution = {row[0]: row[1] for row in cursor.fetchall()}

                return {
                    "symbol_count": symbol_count,
                    "file_count": file_count,
                    "type_distribution": type_distribution,
                }
        except sqlite3.Error as e:
            return {"error": str(e)}

    def clear(self) -> None:
        """清空索引"""
        if not self.index_path:
            return

        try:
            with sqlite3.connect(self.index_path) as conn:
                conn.execute("DELETE FROM symbols")
                conn.execute("DELETE FROM file_index_status")
                conn.commit()
        except sqlite3.Error:
            pass
