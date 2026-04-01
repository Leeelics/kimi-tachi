"""
上下文压缩器

压缩长文本内容，减少 Token 使用。

策略:
1. 提取关键部分（函数签名、类定义、注释）
2. 移除实现细节
3. 保留结构信息
4. 智能截断
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class CompressionResult:
    """压缩结果"""
    original_tokens: int
    compressed_tokens: int
    content: str
    strategy: str  # 使用的压缩策略

    @property
    def reduction_ratio(self) -> float:
        """压缩率"""
        if self.original_tokens == 0:
            return 0.0
        return (self.original_tokens - self.compressed_tokens) / self.original_tokens

    @property
    def reduction_percent(self) -> float:
        """压缩百分比"""
        return self.reduction_ratio * 100


class ContextCompressor:
    """
    上下文压缩器

    使用示例:
        compressor = ContextCompressor()

        # 压缩文件内容
        result = compressor.compress_file_content(
            long_code_content,
            max_tokens=500
        )

        print(f"压缩率: {result.reduction_percent:.1f}%")
        print(f"结果: {result.content}")
    """

    # 估算：平均每个 token 约 4 个字符
    CHARS_PER_TOKEN = 4

    def __init__(
        self,
        chars_per_token: int = 4,
        preserve_docstrings: bool = True,
        preserve_signatures: bool = True,
    ):
        self.chars_per_token = chars_per_token
        self.preserve_docstrings = preserve_docstrings
        self.preserve_signatures = preserve_signatures

    def estimate_tokens(self, text: str) -> int:
        """估算 token 数量"""
        return len(text) // self.chars_per_token

    def compress_file_content(
        self,
        content: str,
        max_tokens: int = 500,
        file_path: str | None = None,
    ) -> CompressionResult:
        """
        压缩文件内容

        Args:
            content: 原始文件内容
            max_tokens: 最大 token 数
            file_path: 文件路径（用于选择压缩策略）

        Returns:
            压缩结果
        """
        original_tokens = self.estimate_tokens(content)
        max_chars = max_tokens * self.chars_per_token

        # 如果内容已经很短，直接返回
        if len(content) <= max_chars:
            return CompressionResult(
                original_tokens=original_tokens,
                compressed_tokens=original_tokens,
                content=content,
                strategy="none",
            )

        # 根据文件类型选择策略
        if file_path:
            if file_path.endswith(".py"):
                return self._compress_python(content, max_chars, original_tokens)
            elif file_path.endswith((".md", ".rst")):
                return self._compress_markdown(content, max_chars, original_tokens)
            elif file_path.endswith((".json", ".yaml", ".yml")):
                return self._compress_config(content, max_chars, original_tokens)

        # 通用压缩
        return self._compress_generic(content, max_chars, original_tokens)

    def _compress_python(
        self,
        content: str,
        max_chars: int,
        original_tokens: int,
    ) -> CompressionResult:
        """压缩 Python 代码"""
        lines = content.split("\n")

        # 提取关键部分
        preserved_lines = []

        for i, line in enumerate(lines):
            stripped = line.strip()
            current_indent = len(line) - len(line.lstrip())

            # 保留导入语句
            if stripped.startswith(("import ", "from ")):
                preserved_lines.append(line)
                continue

            # 保留类定义
            if stripped.startswith("class "):
                preserved_lines.append(line)
                continue

            # 保留函数定义
            if stripped.startswith("def "):
                preserved_lines.append(line)

                # 保留文档字符串
                if self.preserve_docstrings:
                    j = i + 1
                    while j < len(lines):
                        next_line = lines[j].strip()
                        if next_line.startswith('"""') or next_line.startswith("'''"):
                            # 找到文档字符串结束
                            docstring_lines = []
                            while j < len(lines):
                                docstring_lines.append(lines[j])
                                if lines[j].strip().endswith(('"""', "'''")) and len(lines[j].strip()) > 3:
                                    break
                                j += 1
                            preserved_lines.extend(docstring_lines[:3])  # 最多 3 行
                            break
                        elif next_line and not next_line.startswith("#"):
                            break
                        j += 1

                # 添加省略标记
                preserved_lines.append(line[:current_indent] + "    ...")
                continue

            # 保留装饰器
            if stripped.startswith("@"):
                preserved_lines.append(line)
                continue

            # 保留全局变量/常量定义
            if (stripped and not stripped.startswith("#") and
                "=" in stripped and not stripped.startswith("def ") and
                current_indent == 0):
                # 可能是变量定义
                preserved_lines.append(line)

        compressed = "\n".join(preserved_lines)

        # 如果还是太长，截断
        if len(compressed) > max_chars:
            compressed = self._smart_truncate(compressed, max_chars)

        compressed_tokens = self.estimate_tokens(compressed)

        return CompressionResult(
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            content=compressed,
            strategy="python_structure",
        )

    def _compress_markdown(
        self,
        content: str,
        max_chars: int,
        original_tokens: int,
    ) -> CompressionResult:
        """压缩 Markdown 文档"""
        lines = content.split("\n")

        preserved_lines = []
        in_code_block = False

        for line in lines:
            stripped = line.strip()

            # 代码块标记
            if stripped.startswith("```"):
                in_code_block = not in_code_block
                preserved_lines.append(line)
                continue

            # 保留代码块内的内容（但可能截断）
            if in_code_block:
                preserved_lines.append(line)
                continue

            # 保留标题
            if stripped.startswith("#"):
                preserved_lines.append(line)
                continue

            # 保留列表项（但限制数量）
            if stripped.startswith(("- ", "* ", "1. ")):
                preserved_lines.append(line)
                continue

            # 保留重要段落（第一段、包含关键字的段落）
            if stripped and len(preserved_lines) < 50:  # 限制段落数量
                # 检查是否包含关键字
                keywords = ["summary", "overview", "introduction", "usage", "example"]
                if any(kw in stripped.lower() for kw in keywords):
                    preserved_lines.append(line)

        compressed = "\n".join(preserved_lines)

        if len(compressed) > max_chars:
            compressed = self._smart_truncate(compressed, max_chars)

        compressed_tokens = self.estimate_tokens(compressed)

        return CompressionResult(
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            content=compressed,
            strategy="markdown_summary",
        )

    def _compress_config(
        self,
        content: str,
        max_chars: int,
        original_tokens: int,
    ) -> CompressionResult:
        """压缩配置文件"""
        lines = content.split("\n")

        preserved_lines = []

        for line in lines:
            stripped = line.strip()

            # 跳过注释（但保留前 10 行）
            if stripped.startswith("#"):
                if len(preserved_lines) < 10:
                    preserved_lines.append(line)
                continue

            # 保留键值对（但截断长值）
            if "=" in stripped or ":" in stripped:
                # 截断长值
                if len(line) > 200:
                    line = line[:200] + "..."
                preserved_lines.append(line)
            else:
                preserved_lines.append(line)

        compressed = "\n".join(preserved_lines)

        if len(compressed) > max_chars:
            compressed = self._smart_truncate(compressed, max_chars)

        compressed_tokens = self.estimate_tokens(compressed)

        return CompressionResult(
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            content=compressed,
            strategy="config_keys",
        )

    def _compress_generic(
        self,
        content: str,
        max_chars: int,
        original_tokens: int,
    ) -> CompressionResult:
        """通用压缩策略"""
        # 保留前 30% 和后 20%，中间用省略号
        prefix_len = int(max_chars * 0.3)
        suffix_len = int(max_chars * 0.2)

        prefix = content[:prefix_len]
        suffix = content[-suffix_len:] if len(content) > suffix_len else ""

        compressed = prefix + "\n\n... [content truncated] ...\n\n" + suffix

        compressed_tokens = self.estimate_tokens(compressed)

        return CompressionResult(
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            content=compressed,
            strategy="truncate",
        )

    def _smart_truncate(self, content: str, max_chars: int) -> str:
        """智能截断，尽量在完整句子/行处截断"""
        if len(content) <= max_chars:
            return content

        # 尝试在段落边界截断
        truncate_point = max_chars

        # 向前查找换行符
        for i in range(truncate_point, max(0, truncate_point - 200), -1):
            if content[i:i+2] == "\n\n":
                truncate_point = i
                break

        return content[:truncate_point] + "\n\n... [truncated] ..."

    def compress_conversation(
        self,
        messages: list[dict[str, Any]],
        max_tokens: int = 2000,
        preserve_recent: int = 3,  # 保留最近 N 条
    ) -> list[dict[str, Any]]:
        """
        压缩对话历史

        Args:
            messages: 消息列表
            max_tokens: 最大 token 数
            preserve_recent: 保留最近的 N 条完整消息

        Returns:
            压缩后的消息列表
        """
        if not messages:
            return messages

        # 保留最近的消息
        recent_messages = messages[-preserve_recent:]
        older_messages = messages[:-preserve_recent]

        # 压缩旧消息
        compressed_older = []
        current_tokens = sum(
            self.estimate_tokens(m.get("content", ""))
            for m in recent_messages
        )

        # 从旧到新处理，保留关键信息
        for msg in reversed(older_messages):
            content = msg.get("content", "")
            tokens = self.estimate_tokens(content)

            if current_tokens + tokens <= max_tokens * 0.7:  # 留 30% 余量
                compressed_older.insert(0, msg)
                current_tokens += tokens
            else:
                # 压缩这条消息
                compressed_content = self._compress_message(content)
                compressed_tokens = self.estimate_tokens(compressed_content)

                if current_tokens + compressed_tokens <= max_tokens * 0.7:
                    compressed_msg = msg.copy()
                    compressed_msg["content"] = compressed_content
                    compressed_msg["_compressed"] = True
                    compressed_older.insert(0, compressed_msg)
                    current_tokens += compressed_tokens
                else:
                    # 添加摘要标记
                    summary_msg = {
                        "role": "system",
                        "content": f"[Earlier conversation: {len(older_messages)} messages before this point]",
                        "_summary": True,
                    }
                    compressed_older.insert(0, summary_msg)
                    break

        return compressed_older + recent_messages

    def _compress_message(self, content: str) -> str:
        """压缩单条消息"""
        lines = content.split("\n")

        # 保留关键行
        key_lines = []
        for line in lines:
            stripped = line.strip()

            # 保留决策、结论、关键信息
            indicators = [
                "decision:", "conclusion:", "summary:", "key:",
                "important:", "note:", "warning:", "error:",
            ]
            if any(ind in stripped.lower() for ind in indicators) or stripped.startswith("```") or len(stripped) < 100 and stripped:
                key_lines.append(line)

        if not key_lines:
            # 没有关键行，返回前 3 行
            return "\n".join(lines[:3]) + "\n..."

        result = "\n".join(key_lines[:10])  # 最多 10 行
        if len(key_lines) > 10:
            result += "\n..."

        return result

    def get_compression_stats(
        self,
        results: list[CompressionResult],
    ) -> dict[str, Any]:
        """获取压缩统计信息"""
        if not results:
            return {}

        total_original = sum(r.original_tokens for r in results)
        total_compressed = sum(r.compressed_tokens for r in results)

        return {
            "files_processed": len(results),
            "total_original_tokens": total_original,
            "total_compressed_tokens": total_compressed,
            "tokens_saved": total_original - total_compressed,
            "average_reduction": sum(r.reduction_percent for r in results) / len(results),
            "strategies_used": list({r.strategy for r in results}),
        }
