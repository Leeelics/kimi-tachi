"""
MCP 进程监控器

用于监控 MCP 进程数量，帮助验证 Phase 2 的优化效果。
"""

from __future__ import annotations

import contextlib
import subprocess
import threading
import time
from collections.abc import Callable

from .collector import collector


class MCPProcessMonitor:
    """MCP 进程监控器"""

    def __init__(self, check_interval: float = 1.0):
        """
        初始化监控器

        Args:
            check_interval: 检查间隔（秒）
        """
        self.check_interval = check_interval
        self._running = False
        self._thread: threading.Thread | None = None
        self._callbacks: list[Callable[[int], None]] = []
        self._peak_count = 0
        self._current_count = 0

    def start(self):
        """启动监控"""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """停止监控"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def _monitor_loop(self):
        """监控循环"""
        while self._running:
            count = self._count_mcp_processes()
            self._current_count = count
            self._peak_count = max(self._peak_count, count)

            # 记录到收集器
            collector.record_mcp_process(count)

            # 调用回调
            for callback in self._callbacks:
                with contextlib.suppress(Exception):
                    callback(count)

            time.sleep(self.check_interval)

    def _count_mcp_processes(self) -> int:
        """统计 MCP 进程数量"""
        try:
            # 使用 ps 命令查找 MCP 相关进程
            # MCP 进程通常包含 "mcp" 或特定服务器名称
            result = subprocess.run(["ps", "aux"], capture_output=True, text=True)

            count = 0
            for line in result.stdout.split("\n"):
                # 查找 MCP 相关进程
                # 注意：这里需要根据实际的 MCP 进程特征来调整
                if (
                    any(keyword in line.lower() for keyword in ["mcp", "node", "python"])
                    and "mcp_monitor" not in line
                    and "grep" not in line
                ):
                    count += 1

            return count

        except Exception:
            return 0

    @property
    def current_count(self) -> int:
        """当前 MCP 进程数量"""
        return self._current_count

    @property
    def peak_count(self) -> int:
        """峰值 MCP 进程数量"""
        return self._peak_count

    def on_change(self, callback: Callable[[int], None]):
        """
        注册变化回调

        Args:
            callback: 回调函数，接收新的进程数量
        """
        self._callbacks.append(callback)

    def get_report(self) -> dict:
        """获取监控报告"""
        return {
            "current": self._current_count,
            "peak": self._peak_count,
            "target": "≤2",
            "status": "✅" if self._peak_count <= 2 else "❌",
        }


class SimpleMCPMonitor:
    """简单的 MCP 监控器（非线程版）"""

    @staticmethod
    def count_now() -> int:
        """立即统计 MCP 进程数量"""
        try:
            result = subprocess.run(["ps", "aux"], capture_output=True, text=True)

            count = 0
            for line in result.stdout.split("\n"):
                # 简化的检测逻辑
                if "mcp" in line.lower() or "node" in line.lower():
                    count += 1

            return count

        except Exception:
            return 0

    @staticmethod
    def check_and_record():
        """检查并记录到收集器"""
        count = SimpleMCPMonitor.count_now()
        collector.record_mcp_process(count)
        return count


# 便捷函数
def start_mcp_monitoring(interval: float = 1.0) -> MCPProcessMonitor:
    """
    启动 MCP 进程监控

    用法:
        monitor = start_mcp_monitoring()

        # 执行一些操作...

        monitor.stop()
        print(f"峰值 MCP 进程数: {monitor.peak_count}")
    """
    monitor = MCPProcessMonitor(interval)
    monitor.start()
    return monitor


def check_mcp_count() -> int:
    """检查当前 MCP 进程数量"""
    return SimpleMCPMonitor.check_and_record()
