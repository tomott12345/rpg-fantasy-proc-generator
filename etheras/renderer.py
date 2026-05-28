"""
Etheras World Generator — Markdown Renderer
Converts a WorldContext adventure dict into game-ready Markdown.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _g(d: Any, *keys: str, fallback: str = "") -> Any:
    """Safe nested dict getter — returns fallback on any miss or None."""
    cur = d
    for k in keys:
        if isinstance(cur, dict):
            cur = cur.get(k, fallback)
        else:
            return fallback
    return cur if cur is not None else fallback


def _table(rows: List[Dict], headers: List[str]) -> str:
    """Render a list of dicts as a Markdown table."""
    if not rows:
        return ""
    head = "|" + "|".join(h.replace("_", " ").title() for h in headers) + "|"
    sep  = "|" + "|".join("---" for _ in headers) + "|"
    body = "\n".join(
        "|" + "|".join(str(r.get(h, "")) for h in headers) + "|"
        for r in rows
    )
    return "\n".join([head, sep, body])


# ══════════════════════════════════════════════════════════════════════════════
# MAIN RENDERER
# ══════════════════════════════════════════════════════════════════════════════

def render_markdown(data: dict) -> str:
    """
    Render a WorldContext adventure dict to game-ready Markdown.

    The ``seed`` field at the top level enables full reproducibility —
    pass it back to ``WorldContext(world_dir, seed=<seed>)`` to replay.
    """
    seed        = data.get("seed", "?")
    party_level = data.get("party_level", "?")
    adv         = data.get("adventure") or data

    title  = _g(adv, "title",  fallback="Untitled Adventure")
    region = _g(adv, "region", fallback="Unknown")

    qs       = adv.get("quest_summary") or {}
    q_type   = _g(qs, "type")
    q_twist  = _g(qs, "twist")
    q_comp   = _g(qs, "complication")
    q_reward = _g(qs, "reward")
    q_cr     = _g(qs, "cr_range")

    enc        = adv.get("encounter_structure") or {}
    hooks      = adv.get("hooks") or []
    qg         = adv.get("quest_giver") or {}
    locs       = adv.get("locations") or {}
    settlement = locs.get("settlement") or {}
    dungeon    = locs.get("dungeon") or {}
    weather    = adv.get("weather") or {}
    rumors     = adv.get("rumors") or []
    clues      = adv.get("clues") or []
    quirk      = adv.get("magic_item_quirk") or {}
    monsters   = adv.get("monster_encounters") or []
    randoms    = adv.get("random_encounters") or []
    treasure   = adv.get("treasure") or []
    live_ev    = adv.get("live_events") or []
    faction    = adv.get("faction") or {}
    resolution = adv.get("resolution") or {}

    lines: List[str] = []
    A = lines.append

    # ── Header ────────────────────────────────────────────────────────────────
    A(f"# 🗺️ {title}")
    A(f"> 🎲 **Seed:** `{seed}` | **Party Level:** {party_level}")
    A(f"> *Regenerate: `world = WorldContext(WORLD_DIR, seed={seed})`*")
    A("")

    # ── Quest summary ─────────────────────────────────────────────────────────
    A("## 📜 Quest Summary")
    A("| | |")
    A("|---|---|")
    A(f"| **Region** | {region} |")
    if q_type:   A(f"| **Type** | {q_type} |")
    if q_twist:  A(f"| **Twist** | {q_twist} |")
    if q_comp:   A(f"| **Complication** | {q_comp} |")
    if q_reward: A(f"| **Reward Tier** | {q_reward} |")
    if q_cr:     A(f"| **CR Range** | {q_cr} |")
    A("")

    # ── Encounter structure ───────────────────────────────────────────────────
    if enc:
        A("## ⚔️ Encounter Structure")
        enc_type = _g(enc, "type")
        enc_note = _g(enc, "note")
        if enc_type: A(f"**Style:** {enc_type}  ")
        if enc_note: A(f"*{enc_note}*  ")
        parts = []
        for k in ("combat", "social", "puzzle", "trap"):
            v = enc.get(k)
            if v:
                parts.append(f"{v}× {k}")
        if parts:
            A("**Recommended mix:** " + ", ".join(parts))
        A("")

    # ── Adventure hooks ───────────────────────────────────────────────────────
    if hooks:
        A("## 🎣 Adventure Hooks")
        for i, h in enumerate(hooks, 1):
            t = h.get("title", f"Hook {i}")
            d = h.get("description", "")
            A(f"{i}. **{t}** — {d}")
        A("")

    # ── Quest giver ───────────────────────────────────────────────────────────
    if qg:
        A("## 🧑 Quest Giver")
        if _g(qg, "known_npc"):
            A(f"**Known NPC:** {_g(qg, 'known_npc')} ({_g(qg, 'known_npc_traits')})  ")
        if _g(qg, "archetype"):
            A(f"**Archetype:** {_g(qg, 'archetype')}  ")
        if _g(qg, "motivation"):
            A(f"**Motivation:** {_g(qg, 'motivation')}  ")
        if _g(qg, "speech_quirk"):
            A(f"**Speech Quirk:** {_g(qg, 'speech_quirk')}  ")
        if _g(qg, "secret"):
            A(f"**Secret (GM only):** _{_g(qg, 'secret')}_  ")
        A("")

    # ── Settlement ────────────────────────────────────────────────────────────
    if settlement:
        A("## 🏙️ Settlement")
        if _g(settlement, "name"):
            A(f"**Name:** {_g(settlement, 'name')}  ")
        if _g(settlement, "type"):
            A(f"**Type:** {_g(settlement, 'type')}  ")
        if _g(settlement, "current_problem"):
            A(f"**Current Problem:** {_g(settlement, 'current_problem')}  ")
        A("")

    # ── Dungeon ───────────────────────────────────────────────────────────────
    if dungeon:
        A("## 🏚️ Dungeon")
        if _g(dungeon, "name"):
            A(f"**Name:** {_g(dungeon, 'name')}  ")
        if _g(dungeon, "themes"):
            A(f"**Themes:** {_g(dungeon, 'themes')}  ")
        depth    = dungeon.get("depth")
        cr_guess = dungeon.get("cr_guess")
        if depth:    A(f"**Depth:** {depth} levels  ")
        if cr_guess: A(f"**CR Baseline:** {cr_guess}  ")
        A("")

    # ── Weather ───────────────────────────────────────────────────────────────
    if weather and _g(weather, "name"):
        A("## 🌩️ Weather Condition")
        A(f"**{_g(weather, 'name')}** — {_g(weather, 'description')}  ")
        if _g(weather, "mechanical_effect"):
            A(f"*Effect:* {_g(weather, 'mechanical_effect')}")
        A("")

    # ── Rumors ────────────────────────────────────────────────────────────────
    if rumors:
        A("## 💬 Rumors at the Tavern")
        A("*Share with players. Items marked ✓ are true; items marked ✗ are false.*")
        A("")
        for r in rumors:
            mark = "✓" if r.get("true") else "✗"
            A(f"- [{mark}] {r.get('text', '')}")
        A("")

    # ── Investigation clues ───────────────────────────────────────────────────
    if clues:
        A("## 🔍 Investigation Clues")
        for c in clues:
            ctype = c.get("type", "").title()
            ctext = c.get("clue", "")
            impl  = c.get("implication", "")
            if ctext:
                A(f"**[{ctype}]** {ctext}")
                if impl:
                    A(f"   → *{impl}*")
        A("")

    # ── Active faction ────────────────────────────────────────────────────────
    if faction and _g(faction, "name"):
        A("## 🏛️ Active Faction")
        A(f"**{_g(faction, 'name')}**  ")
        if _g(faction, "goals"):
            A(f"*Goals:* {_g(faction, 'goals')}")
        A("")

    # ── Key monsters ──────────────────────────────────────────────────────────
    if monsters:
        A("## 👹 Key Monsters")
        A(_table(monsters, ["name", "type", "cr", "notes"]))
        A("")

    # ── Random encounter table ────────────────────────────────────────────────
    if randoms:
        A("## 🎲 Random Encounter Table")
        A(_table(randoms, ["roll", "encounter"]))
        A("")

    # ── Treasure ──────────────────────────────────────────────────────────────
    if treasure:
        A("## 💰 Treasure")
        A(_table(treasure, ["roll", "treasure"]))
        A("")

    # ── Magic item quirk ──────────────────────────────────────────────────────
    if quirk and _g(quirk, "quirk"):
        A("## ✨ Magic Item Quirk")
        A(f"**{_g(quirk, 'quirk')}** — {_g(quirk, 'effect')}")
        A("")

    # ── Live events ───────────────────────────────────────────────────────────
    if live_ev:
        A("## ⚡ Live Events (Roll d6 Mid-Session)")
        A("*Drop one into a slow moment to inject energy.*")
        A("")
        for i, ev in enumerate(live_ev, 1):
            text = ev if isinstance(ev, str) else ev.get("event", str(ev))
            A(f"{i}. {text}")
        A("")

    # ── Resolution paths ──────────────────────────────────────────────────────
    if resolution:
        A("## 🎯 Resolution Paths")
        for c in resolution.get("choices") or []:
            A(f"- {c}")
        outcome = resolution.get("outcome", "")
        if outcome:
            A(f"\n**Outcome:** {outcome}")
        A("")

    # ── Footer ────────────────────────────────────────────────────────────────
    A("---")
    A(
        f"*Generated by Etheras World Generator v12 "
        f"| Seed `{seed}` "
        f"| {datetime.now().strftime('%Y-%m-%d')}*"
    )

    return "\n".join(lines)
