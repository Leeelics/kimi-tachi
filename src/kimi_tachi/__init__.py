"""
kimi-tachi (君たち) - Multi-agent task orchestration for Kimi CLI

A squad of specialized agents working together (七人衆):
- kamaji: Task coordinator (釜爺)
- shishigami: Architecture consultant (山兽神)
- nekobasu: Code explorer (猫巴士)
- calcifer: Implementation expert (火魔)
- enma: Code reviewer (阎魔王)
- tasogare: Research planner (黄昏)
- phoenix: Knowledge manager (火之鸟)

Phase 2.2: Message Bus Architecture
- Asynchronous message passing
- Point-to-point, broadcast, multicast, pub/sub
- Message persistence (SQLite)
- Distributed tracing
"""

__version__ = "0.2.2"
__all__ = ["cli", "message_bus", "orchestrator", "metrics"]
