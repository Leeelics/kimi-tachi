#!/usr/bin/env python3
"""
MCP 进程监控测试

实时监控运行 kimi-tachi 时的 MCP 进程数量
"""

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, '/home/lee/ship/kimi-tachi/src')
sys.path.insert(0, '/home/lee/kit/eval-explorer/src')


def count_mcp_processes():
    """统计 MCP 进程数量"""
    try:
        result = subprocess.run(
            ["ps", "aux"],
            capture_output=True,
            text=True
        )
        
        mcp_count = 0
        kimi_count = 0
        node_count = 0
        
        for line in result.stdout.split('\n'):
            # MCP 相关进程
            if 'mcp' in line.lower() and 'grep' not in line:
                mcp_count += 1
            # kimi 进程
            if 'kimi' in line and 'grep' not in line:
                kimi_count += 1
            # node 进程（MCP 服务器常用）
            if 'node' in line and 'grep' not in line:
                node_count += 1
        
        return {
            'mcp': mcp_count,
            'kimi': kimi_count,
            'node': node_count,
            'total': mcp_count + kimi_count + node_count
        }
    except Exception as e:
        return {'error': str(e)}


async def test_with_monitoring():
    """带监控的测试"""
    
    print("="*80)
    print("🎯 Phase 2.1 MCP 进程监控测试")
    print("="*80)
    print(f"\n时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n环境变量:")
    print(f"  KIMI_TACHI_DYNAMIC_AGENTS={os.environ.get('KIMI_TACHI_DYNAMIC_AGENTS', 'not set')}")
    
    # 基线测量
    print("\n" + "-"*80)
    print("📊 基线 MCP 进程统计")
    print("-"*80)
    baseline = count_mcp_processes()
    print(f"  MCP 进程: {baseline.get('mcp', 0)}")
    print(f"  Kimi 进程: {baseline.get('kimi', 0)}")
    print(f"  Node 进程: {baseline.get('node', 0)}")
    print(f"  总计: {baseline.get('total', 0)}")
    
    # 创建测试工作目录
    with tempfile.TemporaryDirectory() as tmpdir:
        print("\n" + "-"*80)
        print("🔧 初始化 HybridOrchestrator")
        print("-"*80)
        
        from kimi_tachi.orchestrator.hybrid_orchestrator import HybridOrchestrator
        
        orch = HybridOrchestrator(work_dir=tmpdir)
        print(f"  动态模式: {orch.dynamic_mode}")
        print(f"  工作目录: {tmpdir}")
        
        # 初始化后的 MCP 统计
        init_stats = count_mcp_processes()
        print("\n📊 初始化后 MCP 进程统计")
        print(f"  MCP 进程: {init_stats.get('mcp', 0)}")
        print(f"  Kimi 进程: {init_stats.get('kimi', 0)}")
        
        # 模拟创建动态 subagent
        print("\n" + "-"*80)
        print("🚀 模拟动态 Subagent 创建")
        print("-"*80)
        
        # 记录创建前后的进程变化
        before_create = count_mcp_processes()
        print(f"  创建前 MCP 进程: {before_create.get('mcp', 0)}")
        
        # 这里我们只是模拟，真正的创建会在实际运行时发生
        print("  (实际创建会在调用 delegate 时发生)")
        
        after_create = count_mcp_processes()
        print(f"  创建后 MCP 进程: {after_create.get('mcp', 0)}")
        
        # 清理
        print("\n" + "-"*80)
        print("🧹 清理资源")
        print("-"*80)
        orch.cleanup()
        
        # 最终统计
        final_stats = count_mcp_processes()
        print(f"  清理后 MCP 进程: {final_stats.get('mcp', 0)}")
    
    # 总结
    print("\n" + "="*80)
    print("📋 测试总结")
    print("="*80)
    print(f"\n基线 MCP 进程: {baseline.get('mcp', 0)}")
    print(f"初始化后 MCP 进程: {init_stats.get('mcp', 0)}")
    print(f"最终 MCP 进程: {final_stats.get('mcp', 0)}")
    
    print("\n✅ 监控测试完成！")
    print("\n注意：实际的 MCP 进程减少效果需要在完整运行 kimi-tachi 时验证。")
    print("当前测试仅验证了组件初始化和配置正确性。")
    
    # 保存结果
    result = {
        'timestamp': datetime.now().isoformat(),
        'phase': '2.1',
        'test': 'mcp_monitor',
        'baseline': baseline,
        'init': init_stats,
        'final': final_stats,
        'dynamic_mode': orch.dynamic_mode
    }
    
    result_path = Path('/home/lee/ship/kimi-tachi/results/phase2_1_mcp_monitor.json')
    result_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(result_path, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"\n📁 结果已保存: {result_path}")


def main():
    """主函数"""
    # 设置环境变量
    os.environ['KIMI_TACHI_DYNAMIC_AGENTS'] = 'true'
    os.environ['KIMI_TACHI_DEBUG_AGENTS'] = 'true'
    
    asyncio.run(test_with_monitoring())


if __name__ == '__main__':
    main()
