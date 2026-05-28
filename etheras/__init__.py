"""
Etheras World Generator — Python package.

Quick start::

    from etheras import WorldContext, render_markdown

    world     = WorldContext("mnt/data/world_mod", seed=42)
    adventure = world.generate_one_shot(party_level=3)
    print(render_markdown(adventure))
"""

from .engine   import WorldContext
from .renderer import render_markdown

__all__ = ["WorldContext", "render_markdown"]
