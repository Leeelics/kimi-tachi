"""
Adapters for integrating kimi-tachi with kimi-cli internals.

v0.4.0: Added WireAdapter for Message Bus integration
"""

from .wire_adapter import WireAdapter, get_wire_adapter

__all__ = ["WireAdapter", "get_wire_adapter"]
