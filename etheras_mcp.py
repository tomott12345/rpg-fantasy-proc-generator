"""
Etheras World Generator — MCP Server

Exposes the procedural generator as Claude Desktop tools via the
Model Context Protocol (FastMCP).

Claude Desktop config (add to mcpServers in claude_desktop_config.json):
  "etheras": {
    "command": "/path/to/repo/.venv/bin/python",
    "args":    ["/path/to/repo/etheras_mcp.py"]
  }

Tools exposed:
  generate_adventure    — full one-shot adventure (Markdown)
  generate_session_zero — player-facing pitch
  roll_table            — single roll on any procgen table
  get_live_events       — mid-session drama events for a region
  list_tables           — enumerate available table IDs
  list_generators       — enumerate available generator IDs
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

# ── Locate world data relative to this file ───────────────────────────────────
REPO_DIR  = Path(__file__).parent.resolve()
WORLD_DIR = str(REPO_DIR / "mnt" / "data" / "world_mod")

# ── Import the package from the same repo ────────────────────────────────────
sys.path.insert(0, str(REPO_DIR))
from etheras.engine   import WorldContext
from etheras.renderer import render_markdown

# ── FastMCP setup ─────────────────────────────────────────────────────────────
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    name="etheras-world-generator",
    instructions=(
        "Tools for the Etheras procedural RPG adventure generator. "
        "Use generate_adventure to create a full one-shot, then expand "
        "the Markdown with your own narrative prose."
    ),
)


# ══════════════════════════════════════════════════════════════════════════════
# TOOLS
# ══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def generate_adventure(
    party_level: int = 3,
    seed: Optional[int] = None,
) -> str:
    """
    Generate a complete one-shot adventure and return it as Markdown.

    Args:
        party_level: Average party level (1–20). Affects CR targets and
                     treasure tier. Default 3.
        seed:        Integer seed for reproducible output. If omitted a
                     random seed is chosen and printed in the output so
                     you can replay the same adventure later.

    Returns:
        Formatted Markdown ready to paste into a campaign doc or Claude
        Desktop for narrative expansion.
    """
    world     = WorldContext(WORLD_DIR, seed=seed, verbose=False)
    adventure = world.generate_one_shot(party_level=party_level)
    return render_markdown(adventure)


@mcp.tool()
def generate_session_zero(seed: Optional[int] = None) -> str:
    """
    Generate a brief player-facing session-zero pitch.

    Returns a short premise paragraph suitable for sharing with players
    before the first session — no GM spoilers included.

    Args:
        seed: Optional integer seed for a reproducible pitch.

    Returns:
        Plain-text session-zero blurb.
    """
    world = WorldContext(WORLD_DIR, seed=seed, verbose=False)
    result = world.generate_session_zero()
    sz = result.get("session_zero") or {}
    output = sz.get("output", "")
    if not output:
        # Fallback: format the raw context
        lines = [f"**Seed:** {result['seed']}"]
        for k, v in sz.items():
            if k not in ("now", "output") and v:
                label = k.replace("_", " ").title()
                val   = v if isinstance(v, str) else json.dumps(v)
                lines.append(f"**{label}:** {val}")
        output = "\n".join(lines)
    return f"**Seed:** `{result['seed']}`\n\n{output}"


@mcp.tool()
def roll_table(
    table_id: str,
    seed: Optional[int] = None,
) -> str:
    """
    Roll once on a named procgen table and return the result as JSON.

    Use list_tables() to discover valid table IDs.

    Args:
        table_id: ID of the table to roll on (e.g. "region", "dungeon_theme",
                  "npc_personality", "rumor", "weather_event").
        seed:     Optional integer seed.

    Returns:
        JSON string of the rolled entry dict (or the raw value if a string).
    """
    world  = WorldContext(WORLD_DIR, seed=seed, verbose=False)
    result = world.roll_table(table_id)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
def get_live_events(
    region_id: str = "",
    count: int = 6,
    seed: Optional[int] = None,
) -> str:
    """
    Return a numbered list of mid-session drama events for a region.

    These are random "live event" prompts you can drop into a slow moment
    to inject energy. Roll a d{count} at the table to pick one.

    Args:
        region_id: Etheras region key — one of: ackdon, sadri_desert,
                   iuned, dagger_depths, glitterhold_forest, wraith_fortress.
                   Leave blank to draw from the full cross-region pool.
        count:     How many events to return (1–20). Default 6.
        seed:      Optional integer seed.

    Returns:
        Numbered Markdown list of events.
    """
    count = max(1, min(count, 20))
    world  = WorldContext(WORLD_DIR, seed=seed, verbose=False)
    events = world._get_live_events(region_id.strip(), count=count)
    if not events:
        return f"No live events found for region '{region_id}'."
    header = f"**Live Events — {region_id or 'All Regions'} (d{len(events)})**\n"
    body   = "\n".join(f"{i}. {e}" for i, e in enumerate(events, 1))
    return header + "\n" + body


@mcp.tool()
def list_tables() -> str:
    """
    List all available procgen table IDs.

    Returns:
        Comma-separated string of table IDs you can pass to roll_table().
    """
    world = WorldContext(WORLD_DIR, verbose=False)
    return ", ".join(world.list_tables())


@mcp.tool()
def list_generators() -> str:
    """
    List all available generator IDs.

    Returns:
        Comma-separated string of generator IDs (for advanced use with
        WorldContext.generate() directly).
    """
    world = WorldContext(WORLD_DIR, verbose=False)
    return ", ".join(world.list_generators())


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    mcp.run()
