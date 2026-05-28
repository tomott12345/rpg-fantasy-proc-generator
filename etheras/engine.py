"""
Etheras World Generator — Core Engine
Procedural generation for the Etheras RPG setting.
"""

from __future__ import annotations

import re
import random
import math
import os
import glob
import time
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from functools import reduce

import yaml

# ── Constants ─────────────────────────────────────────────────────────────────
PROCGEN_TABLES     = "procgen.tables"
PROCGEN_GENERATORS = "procgen.generators"
PROCGEN_WEIGHTS    = "procgen.weights"
PROCGEN_DICE       = "procgen.dice"

# Compiled regex patterns
DICE_PAT = re.compile(r"(?:(\d+)[dD](\d+))|([()\+\-\*/])|(\d+)")
CURLY_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_.\-]+)(\|[a-zA-Z]+)?\s*\}\}")

# ── Module-level globals (set by WorldContext on init) ─────────────────────────
CURRENT_ROOT: Optional[Dict[str, Any]] = None
CURRENT_RNG:  Optional[random.Random]  = None
_TABLE_CACHE: Dict[str, Any]           = {}


# ══════════════════════════════════════════════════════════════════════════════
# LOADERS
# ══════════════════════════════════════════════════════════════════════════════

def make_rng(seed: Optional[int]) -> random.Random:
    rng = random.Random()
    rng.seed(seed)
    return rng


def deep_merge(a: dict, b: dict) -> dict:
    out = a.copy()
    for k, v in b.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = deepcopy(v)
    return out


def load_yaml_file(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_world_folder(folder: str) -> dict:
    files = sorted(glob.glob(os.path.join(folder, "*.yaml")))
    if not files:
        return {}
    return reduce(deep_merge, [load_yaml_file(p) for p in files], {})


# ══════════════════════════════════════════════════════════════════════════════
# DICE ENGINE
# ══════════════════════════════════════════════════════════════════════════════

def _roll_single(rng: random.Random, ndice: int, sides: int) -> int:
    return sum(rng.randint(1, sides) for _ in range(ndice))


def roll(expr: str, rng: Optional[random.Random] = None) -> int:
    if not expr:
        raise ValueError("Empty dice expression")
    if rng is None:
        rng = CURRENT_RNG
    tokens: List[str] = []
    for m in DICE_PAT.finditer(str(expr)):
        if m.group(1) and m.group(2):
            tokens.append(str(_roll_single(rng, int(m.group(1)), int(m.group(2)))))
        elif m.group(3):
            tokens.append(m.group(3))
        elif m.group(4):
            tokens.append(m.group(4))
    safe = "".join(tokens)
    try:
        return int(eval(safe, {"__builtins__": {}}, {}))
    except Exception as e:
        raise ValueError(f"Bad dice expr '{expr}' -> '{safe}': {e}")


def weighted_choice(weights: Dict[str, int], rng: random.Random) -> str:
    if not weights:
        raise ValueError("Empty weights dict")
    items = list(weights.keys())
    wts   = [max(int(w), 0) for w in weights.values()]
    if sum(wts) <= 0:
        raise ValueError("Weights sum to zero")
    return rng.choices(items, weights=wts, k=1)[0]


# ══════════════════════════════════════════════════════════════════════════════
# DATA NAVIGATION
# ══════════════════════════════════════════════════════════════════════════════

def deep_get(d: Dict[str, Any], path: str) -> Any:
    cur = d
    for part in path.split("."):
        if not part:
            continue
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            raise KeyError(f"Path '{path}' not found (stuck at '{part}')")
    return cur


def interpolate(s: str, ctx: Dict[str, Any]) -> str:
    def repl(m: re.Match) -> str:
        key  = m.group(1)
        filt = (m.group(2) or "").lstrip("|")
        val: Any = ctx
        for p in key.split("."):
            if isinstance(val, dict) and p in val:
                val = val[p]
            else:
                return m.group(0)
        sval = str(val)
        if   filt == "title": sval = sval.title()
        elif filt == "upper": sval = sval.upper()
        elif filt == "lower": sval = sval.lower()
        return sval
    return CURLY_RE.sub(repl, s)


def resolve_at(ref: str, root: Dict[str, Any], runtime: Dict[str, Any]) -> Any:
    if not ref.startswith("@"):
        return ref
    path = ref[1:]
    if path.startswith("weights."):
        path = f"{PROCGEN_WEIGHTS}.{path[8:]}"
    elif path.startswith("dice."):
        path = f"{PROCGEN_DICE}.{path[5:]}"
    if "{{" in path:
        path = interpolate(path, runtime)
    if "[" in path and path.endswith("]"):
        head, key = path.split("[", 1)
        return deep_get(root, head)[key[:-1]]
    return deep_get(root, path)


# ══════════════════════════════════════════════════════════════════════════════
# EXPRESSION EVALUATOR
# ══════════════════════════════════════════════════════════════════════════════

def case(key: Any, mapping: Dict[str, Any], default: Any = None) -> Any:
    return mapping.get(str(key), default)


def treasure_tier_by_cr(cr_val: Any) -> Any:
    if CURRENT_ROOT is None:
        raise RuntimeError("CURRENT_ROOT not set — create a WorldContext first")
    try:
        cr = float(cr_val)
    except Exception:
        cr = 0.0
    table = deep_get(CURRENT_ROOT, f"{PROCGEN_DICE}.treasure_tier_by_cr")
    exact = range_m = plus_m = None
    for k, v in table.items():
        k_str = str(k).strip()
        try:
            if float(k_str) == cr:
                exact = v
                break
        except ValueError:
            pass
        if "-" in k_str:
            try:
                a, b = k_str.split("-", 1)
                if float(a) <= cr <= float(b):
                    range_m = v
            except ValueError:
                pass
        if k_str.endswith("+"):
            try:
                if cr >= float(k_str[:-1]):
                    plus_m = v
            except ValueError:
                pass
    return exact or range_m or plus_m or next(iter(table.values()))


def lookup(path: str) -> Any:
    if CURRENT_ROOT is None:
        raise RuntimeError("CURRENT_ROOT not set — create a WorldContext first")
    return deep_get(CURRENT_ROOT, path)


class SafeLocals(dict):
    RESERVED = {
        "treasure_tier_by_cr", "lookup", "roll", "case", "math",
        "max", "min", "abs", "round", "int", "float", "len", "sum",
    }

    def __init__(self, base_ctx: Dict[str, Any]) -> None:
        super().__init__()
        self._ctx = base_ctx

    def __contains__(self, key: object) -> bool:
        return dict.__contains__(self, key) or (
            key in self._ctx and key not in self.RESERVED
        )

    def __getitem__(self, key: str) -> Any:
        if dict.__contains__(self, key):
            return dict.__getitem__(self, key)
        if key in self._ctx and key not in self.RESERVED:
            return self._ctx[key]
        raise KeyError(key)

    def get(self, key: str, default: Any = None) -> Any:  # type: ignore[override]
        try:
            return self[key]
        except KeyError:
            return default


def eval_expr(expr: str, ctx: Dict[str, Any]) -> Any:
    sl = SafeLocals(ctx)
    sl.update({
        "case":                case,
        "math":                math,
        "treasure_tier_by_cr": treasure_tier_by_cr,
        "lookup":              lookup,
        "roll":                lambda s: roll(s, CURRENT_RNG),
        "max": max, "min": min, "abs": abs, "round": round,
        "int": int, "float": float, "len": len, "sum": sum,
    })
    try:
        return eval(expr, {"__builtins__": {}}, sl)
    except Exception as e:
        raise ValueError(f"Bad expr '{expr}': {e}")


# ══════════════════════════════════════════════════════════════════════════════
# TABLE ENGINE
# ══════════════════════════════════════════════════════════════════════════════

def build_table_cache(root: Dict[str, Any]) -> None:
    global _TABLE_CACHE
    try:
        tables = deep_get(root, PROCGEN_TABLES)
        _TABLE_CACHE = {t["id"]: t for t in tables if "id" in t}
    except KeyError:
        _TABLE_CACHE = {}


def get_proc_table(root: Dict[str, Any], table_id: str) -> Dict[str, Any]:
    if not _TABLE_CACHE:
        build_table_cache(root)
    if table_id not in _TABLE_CACHE:
        available = sorted(_TABLE_CACHE.keys())
        raise KeyError(
            f"Table '{table_id}' not found. Available: {', '.join(available)}"
        )
    return _TABLE_CACHE[table_id]


def roll_table(table: Dict[str, Any], rng: random.Random) -> Any:
    entries = table.get("entries", [])
    if not entries:
        return None
    total = sum(int(e.get("weight", 1)) for e in entries)
    r = rng.uniform(0, total)
    acc = 0.0
    for e in entries:
        acc += int(e.get("weight", 1))
        if r <= acc:
            return e.get("result", e)
    return entries[-1].get("result", entries[-1])


def run_generator(
    root: Dict[str, Any],
    gen_name: str,
    rng: random.Random,
    base_ctx: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    gens = deep_get(root, PROCGEN_GENERATORS)
    if gen_name not in gens:
        available = sorted(gens.keys())
        raise KeyError(
            f"Generator '{gen_name}' not found. Available: {', '.join(available)}"
        )
    steps = gens[gen_name].get("steps", [])
    ctx: Dict[str, Any] = {} if base_ctx is None else deepcopy(base_ctx)
    ctx["now"] = datetime.now(timezone.utc).isoformat()

    for step in steps:
        if "choose" in step:
            for k, v in step["choose"].items():
                resolved = (
                    resolve_at(v, root, ctx)
                    if isinstance(v, str) and v.startswith("@")
                    else v
                )
                ctx[k] = (
                    weighted_choice(resolved, rng)
                    if isinstance(resolved, dict)
                    else resolved
                )

        elif "roll" in step:
            for k, v in step["roll"].items():
                expr = (
                    resolve_at(v, root, ctx)
                    if isinstance(v, str) and v.startswith("@")
                    else v
                )
                ctx[k] = roll(str(expr), rng)

        elif "pick_n" in step:
            spec    = step["pick_n"]
            out_key = spec.get("into", "problems")
            src     = spec.get("from", [])
            n_raw   = spec.get("n", 1)
            n       = roll(str(n_raw), rng) if isinstance(n_raw, str) else int(n_raw)
            pool    = list(src)
            rng.shuffle(pool)
            ctx[out_key] = pool[:n]

        elif "derive" in step:
            for k, expr in step["derive"].items():
                ctx[k] = eval_expr(str(expr), ctx)

        elif "table" in step:
            table_id = step["table"]
            t   = get_proc_table(root, table_id)
            res = roll_table(t, rng)
            ctx[table_id] = res
            alias = table_id.split("_")[0]
            if alias and alias not in ctx:
                ctx[alias] = res

        elif "bind" in step:
            for k, expr in step["bind"].items():
                ctx[k] = eval_expr(str(expr), ctx) if isinstance(expr, str) else expr

        elif "output_template" in step:
            ctx["output"] = interpolate(step["output_template"], ctx)

    return ctx


# ══════════════════════════════════════════════════════════════════════════════
# WORLD CONTEXT
# ══════════════════════════════════════════════════════════════════════════════

class WorldContext:
    """
    Entry point for all generation.  Create once per request.

    Example::

        world = WorldContext("mnt/data/world_mod", seed=42)
        adventure = world.generate_one_shot(party_level=3)
        md = render_markdown(adventure)
    """

    def __init__(
        self,
        world_dir: str,
        seed: Optional[int] = None,
        verbose: bool = True,
    ) -> None:
        global CURRENT_ROOT, CURRENT_RNG, _TABLE_CACHE

        self.world_dir = world_dir
        self.seed      = seed if seed is not None else int(time.time()) % 999_983
        self.root      = load_world_folder(world_dir)
        self.rng       = make_rng(self.seed)

        build_table_cache(self.root)
        CURRENT_ROOT = self.root
        CURRENT_RNG  = self.rng

        if verbose:
            gens = list(deep_get(self.root, PROCGEN_GENERATORS).keys())
            print(f"🌍 World loaded | seed: {self.seed} | tables: {len(_TABLE_CACHE)}")
            print(f"   generators : {gens}")

    # ── Public helpers ────────────────────────────────────────────────────────

    def roll_table(self, table_id: str) -> Any:
        """Roll once on a named procgen table."""
        return roll_table(get_proc_table(self.root, table_id), self.rng)

    def generate(
        self,
        gen_name: str,
        base_ctx: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Run a named generator and return the full context dict."""
        return run_generator(self.root, gen_name, self.rng, base_ctx)

    def list_tables(self) -> List[str]:
        return sorted(_TABLE_CACHE.keys())

    def list_generators(self) -> List[str]:
        return sorted(deep_get(self.root, PROCGEN_GENERATORS).keys())

    # ── One-shot adventure ────────────────────────────────────────────────────

    def generate_one_shot(self, party_level: int = 3) -> Dict[str, Any]:
        """Generate a complete one-shot adventure dict."""
        cr_guess = max(1, party_level - 1)
        ctx = self.generate(
            "one_shot",
            base_ctx={"cr_guess": cr_guess, "party_level": party_level},
        )
        rumor2 = self.roll_table("rumor")
        clue2  = self.roll_table("mystery_clue")
        region_id = (
            (ctx.get("region") or {}).get("id", "")
            if isinstance(ctx.get("region"), dict)
            else ""
        )
        live_events = self._get_live_events(region_id)
        return self._assemble(ctx, party_level, rumor2, clue2, live_events)

    # ── Session zero ──────────────────────────────────────────────────────────

    def generate_session_zero(self) -> Dict[str, Any]:
        """Generate a brief player-facing session-zero pitch."""
        ctx = self.generate("session_zero")
        return {"seed": self.seed, "session_zero": ctx}

    # ── Save ──────────────────────────────────────────────────────────────────

    def save(
        self,
        adventure: Dict[str, Any],
        prefix: str = "adventure",
        export_dir: str = "mnt/data/exports",
    ) -> str:
        """Render an adventure dict to Markdown and write to disk."""
        from .renderer import render_markdown
        md = render_markdown(adventure)
        os.makedirs(export_dir, exist_ok=True)
        ts   = datetime.now().strftime("%Y%m%d-%H%M%S")
        path = os.path.join(export_dir, f"{prefix}-{self.seed}-{ts}.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"✅ Saved: {path}")
        return path

    # ── Internal ──────────────────────────────────────────────────────────────

    def _get_live_events(self, region_id: str, count: int = 6) -> List[str]:
        all_events = (
            (self.root.get("encounters") or {}).get("live_events") or {}
        )
        pool = list(all_events.get(region_id) or [])
        if not pool:
            pool = [e for events in all_events.values() for e in events]
        self.rng.shuffle(pool)
        return pool[:count]

    @staticmethod
    def _s(val: Any, fallback: str = "") -> str:
        return str(val) if val is not None else fallback

    @staticmethod
    def _dg(d: Any, key: str, fallback: str = "") -> str:
        return str(d.get(key, fallback)) if isinstance(d, dict) else fallback

    def _assemble(
        self,
        ctx:         Dict[str, Any],
        party_level: int,
        rumor2:      Any,
        clue2:       Any,
        live_events: List[str],
    ) -> Dict[str, Any]:
        dg = self._dg
        s  = self._s

        region       = ctx.get("region") or {}
        region_label = dg(region, "label", "Unknown Region")
        region_id    = dg(region, "id", "")

        hook      = ctx.get("hook_types") or {}
        hook_type = dg(hook, "type", "adventure").replace("_", " ").title()
        hook_twist= dg(hook, "twist", "")

        dungeon      = ctx.get("dungeon_theme") or {}
        dungeon_name = dg(dungeon, "name", "Ancient Site")
        dungeon_tags = dungeon.get("tags", []) if isinstance(dungeon, dict) else []

        stype       = ctx.get("settlement_type") or {}
        stype_label = dg(stype, "label", "settlement")
        sprob       = s(ctx.get("settlement_problem"), "none obvious yet")

        npc       = ctx.get("npc_personality") or {}
        npc_arch  = dg(npc, "archetype", "stranger").replace("_", " ").title()
        npc_motiv = dg(npc, "motivation", "")
        npc_speech= dg(npc, "speech_quirk", "")
        npc_secret= dg(npc, "secret", "")

        rumor1   = ctx.get("rumor") or {}
        r1_text  = dg(rumor1, "text", "")
        r1_true  = rumor1.get("accurate", False) if isinstance(rumor1, dict) else False
        r2_text  = dg(rumor2, "text", "") if isinstance(rumor2, dict) else s(rumor2)
        r2_true  = rumor2.get("accurate", False) if isinstance(rumor2, dict) else False

        clue1   = ctx.get("mystery_clue") or {}
        c1_text = dg(clue1, "clue", "")
        c1_impl = dg(clue1, "implication", "")
        c1_type = dg(clue1, "type", "")
        c2_text = dg(clue2, "clue", "") if isinstance(clue2, dict) else s(clue2)
        c2_impl = dg(clue2, "implication", "") if isinstance(clue2, dict) else ""
        c2_type = dg(clue2, "type", "") if isinstance(clue2, dict) else ""

        weather  = ctx.get("weather_event") or {}
        wx_name  = dg(weather, "name", "")
        wx_desc  = dg(weather, "description", "")
        wx_fx    = dg(weather, "mechanical_effect", "")

        enc        = ctx.get("encounter_mix") or {}
        enc_type   = dg(enc, "type", "").replace("_", " ").title()
        enc_note   = dg(enc, "note", "")
        enc_combat = enc.get("combat", 2) if isinstance(enc, dict) else 2
        enc_social = enc.get("social", 1) if isinstance(enc, dict) else 1
        enc_puzzle = enc.get("puzzle", 1) if isinstance(enc, dict) else 1
        enc_trap   = enc.get("trap",   1) if isinstance(enc, dict) else 1

        quirk    = ctx.get("magic_item_quirk") or {}
        q_text   = dg(quirk, "quirk",  "")
        q_effect = dg(quirk, "effect", "")

        complication = s(ctx.get("complication"), "")
        reward       = s(ctx.get("reward"),       "standard")
        cr_guess     = ctx.get("cr_guess", max(1, party_level - 1))

        # Bestiary — prefer regional monsters, fall back by CR proximity
        bestiary = self.root.get("bestiary") or []
        regional = [b for b in bestiary if region_id in (b.get("habitats") or [])]
        if not regional:
            regional = [
                b for b in bestiary
                if abs(float(b.get("cr", 0)) - cr_guess) <= 2
            ]
        if not regional:
            regional = bestiary[:4]
        sampled = self.rng.sample(regional, min(3, len(regional)))
        monster_encounters = [
            {
                "name":  b.get("id", "unknown").replace("_", " ").title(),
                "type":  ", ".join(b.get("tags") or []),
                "cr":    b.get("cr", "?"),
                "notes": "Habitats: " + ", ".join(b.get("habitats") or []),
            }
            for b in sampled
        ]

        # Random encounter table from spawn data
        spawn_tables = (
            (self.root.get("encounters") or {}).get("spawn_tables") or []
        )
        region_spawn = next(
            (t for t in spawn_tables if t.get("region") == region_id), None
        )
        random_encounters = []
        if region_spawn:
            for i, e in enumerate(region_spawn.get("entries", [])[:8], 1):
                random_encounters.append({
                    "roll":      str(i),
                    "encounter": (
                        e.get("creature", "?").replace("_", " ").title()
                        + f" (CR {e.get('cr', '?')})"
                    ),
                })

        # Treasure from loot tables
        loot         = self.root.get("loot") or {}
        bundles      = loot.get("bundles") or {}
        relics       = loot.get("cataclysm_relics") or {}
        bundle       = bundles.get(reward) or bundles.get("standard") or {}
        minor_relics = relics.get("minor") or ["lumenshard"]
        major_relics = relics.get("major") or ["hourglass_of_ages"]
        treasure = [
            {"roll": "1-2", "treasure": f"{bundle.get('dice', '2d10')} {bundle.get('unit', 'gold')}"},
            {"roll": "3-4", "treasure": f"Minor relic: {self.rng.choice(minor_relics).replace('_', ' ')}"},
            {"roll": "5-6", "treasure": f"Major relic: {self.rng.choice(major_relics).replace('_', ' ')}"},
        ]

        # Faction
        factions      = self.root.get("factions") or []
        faction       = next(
            (f for f in factions if f.get("base_region") == region_id), None
        )
        if not faction and factions:
            faction = self.rng.choice(factions)
        faction_name  = (faction or {}).get("name", "")
        faction_goals = (faction or {}).get("goals") or []

        # Known NPC
        npcs_yaml = self.root.get("npcs") or []
        reg_npcs  = [n for n in npcs_yaml if n.get("location") == region_id] or npcs_yaml
        known_npc = self.rng.choice(reg_npcs) if reg_npcs else {}

        return {
            "seed":        self.seed,
            "party_level": party_level,
            "adventure": {
                "title":  f"{hook_type} in {region_label}",
                "region": region_label,
                "theme":  hook_type.lower().replace(" ", "_"),
                "quest_summary": {
                    "type":         hook_type,
                    "twist":        hook_twist,
                    "complication": complication,
                    "reward":       reward,
                    "cr_range":     f"CR {max(1, cr_guess - 1)}-{cr_guess + 2}",
                },
                "encounter_structure": {
                    "type":   enc_type,
                    "note":   enc_note,
                    "combat": enc_combat,
                    "social": enc_social,
                    "puzzle": enc_puzzle,
                    "trap":   enc_trap,
                },
                "hooks": [
                    {"title": "Quest Giver",  "description": f"A {npc_arch} needs help: {npc_motiv}"},
                    {"title": "Tavern Rumor", "description": r1_text},
                    {"title": "Strange Clue", "description": c1_text},
                ],
                "quest_giver": {
                    "archetype":        npc_arch,
                    "motivation":       npc_motiv,
                    "speech_quirk":     npc_speech,
                    "secret":           npc_secret,
                    "known_npc":        known_npc.get("name", ""),
                    "known_npc_traits": ", ".join(known_npc.get("traits") or []),
                },
                "locations": {
                    "settlement": {
                        "name":            f"{region_label} {stype_label.title()}",
                        "type":            stype_label,
                        "current_problem": sprob,
                    },
                    "dungeon": {
                        "name":     dungeon_name,
                        "themes":   ", ".join(str(t) for t in dungeon_tags),
                        "depth":    self.rng.randint(2, 5),
                        "cr_guess": cr_guess,
                    },
                },
                "weather": {
                    "name":              wx_name,
                    "description":       wx_desc,
                    "mechanical_effect": wx_fx,
                },
                "rumors": [
                    {"text": r1_text, "true": r1_true},
                    {"text": r2_text, "true": r2_true},
                ],
                "clues": [
                    {"type": c1_type, "clue": c1_text, "implication": c1_impl},
                    {"type": c2_type, "clue": c2_text, "implication": c2_impl},
                ],
                "magic_item_quirk":  {"quirk": q_text, "effect": q_effect},
                "monster_encounters": monster_encounters,
                "random_encounters":  random_encounters,
                "treasure":           treasure,
                "live_events":        live_events,
                "faction": {
                    "name":  faction_name,
                    "goals": ", ".join(str(g) for g in faction_goals),
                },
                "resolution": {
                    "choices": [
                        (
                            f"Side with {faction_name} to resolve the crisis."
                            if faction_name
                            else "Confront the threat directly."
                        ),
                        "Exploit the situation for personal gain.",
                        "Forge an unexpected alliance with the antagonist.",
                    ],
                    "outcome": (
                        f"The fate of {region_label} shifts based on the party's choices."
                    ),
                },
            },
        }
