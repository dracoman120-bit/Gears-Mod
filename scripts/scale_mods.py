#!/usr/bin/env python3
"""Scale the stat bonuses of Gears Tactics weapon mods, attachments, armour and grenades.

Reads the original CSVs (never modifies them) and writes modified copies.
Costs, ids and formatting are kept as-is. Changes made:
  * Weapon mods and armour get every stat they were missing, one row per rarity the mod
    already has, valued from that stat's typical rarity curve (see build_new_rows).
    Stats a mod lists but at 0 are filled from the same curve.
  * Penalties (negative values) are flipped to positive.
  * All stat values are multiplied (default 3x); grenade damage/healing get their own multiplier.
  * Evasion and Resilience are capped at 90%.
"""
import argparse
import sys
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from statistics import median

VALUE_COLUMNS = ("ModificationValue", "MaxModificationValue")
STAT_COLUMN = "ModifiedStatName"
TYPE_COLUMN = "WeaponType"
# Grenade weapon types (frag and stim; the data does not say which is which) and the stats boosted further.
GRENADE_TYPES = {"7", "15"}
GRENADE_STATS = {"WeaponDamage", "WeaponHealing"}
# All grenade-slot weapon types (the two above plus type 6); these never receive the added stats.
GRENADE_SLOT_TYPES = GRENADE_TYPES | {"6"}
# Fraction stats are capped at 90%.
FRACTION_CAPS = {"Evasion": Decimal("0.9"), "Resilience": Decimal("0.9")}
# Full stat set every mod should carry.
WEAPON_STATS = ("WeaponDamage", "WeaponAccuracy", "WeaponCritChance", "WeaponCritDamageMultiplier",
                "WeaponMagazineSize", "MovementAllowance")
ARMOUR_STATS = ("Health", "Evasion", "Resilience", "MovementAllowance")
MOD_COLUMNS = ("ArmourClass", "ArmourSet", "WeaponType", "ModSlot", "Variant", "Rarity")


def unquote(token):
    return token[1:-1] if len(token) >= 2 and token[0] == token[-1] == '"' else token


def format_like(value, original):
    """Format `value` the way the game's export does (no trailing zeros, ".5" vs "0.5")."""
    text = format(value.normalize(), "f")
    if original.lstrip("-").startswith(".") and text.lstrip("-").startswith("0."):
        text = text.replace("0.", ".", 1)
    return text


def build_new_rows(rows, header, like):
    """Return (new rows, zero rows filled) giving each weapon mod / armour piece every stat it lacks.

    A mod is (weapon type, slot, variant) or (armour class, set). For each missing stat we add a row
    per rarity the mod already has, copying the mod's costs and taking the value from the stat's
    median positive value at that rarity across the file (movement pools weapons and armour, since
    weapon mods alone have no low-rarity movement data). Gaps are filled from the nearest known
    rarity and the curve is never allowed to drop as rarity rises. Values are unscaled here.
    Rows the mod already lists at 0 are updated in place to the curve value.
    """
    col = {name: header.index(name) for name in MOD_COLUMNS}
    stat_i = header.index(STAT_COLUMN)
    value_i = next(header.index(c) for c in VALUE_COLUMNS if c in header)

    def classify(tokens):
        """-> (category, mod key), or (None, None) for grenade-slot rows."""
        if tokens[col["ArmourClass"]] != "-1":
            return "armour", ("armour", tokens[col["ArmourClass"]], tokens[col["ArmourSet"]])
        weapon_type = unquote(tokens[col["WeaponType"]])
        if weapon_type in GRENADE_SLOT_TYPES:
            return None, None
        return "weapon", ("weapon", weapon_type, unquote(tokens[col["ModSlot"]]), unquote(tokens[col["Variant"]]))

    def pool(category, stat):
        return "any" if stat == "MovementAllowance" else category

    rarities = sorted({int(unquote(t[col["Rarity"]])) for t in rows})
    samples = defaultdict(list)  # (pool, stat, rarity) -> positive values
    mods = {}  # mod key -> (category, {stat}, {rarity: first row})
    for tokens in rows:
        category, key = classify(tokens)
        if category is None:
            continue
        stat = unquote(tokens[stat_i])
        rarity = int(unquote(tokens[col["Rarity"]]))
        value = Decimal(unquote(tokens[value_i]))
        if value > 0:
            samples[(pool(category, stat), stat, rarity)].append(value)
        _, stats, by_rarity = mods.setdefault(key, (category, set(), {}))
        stats.add(stat)
        by_rarity.setdefault(rarity, tokens)

    def curve(pool_name, stat):
        raw = [median(samples[(pool_name, stat, r)]) if samples.get((pool_name, stat, r)) else None for r in rarities]
        known = [v for v in raw if v is not None]
        if not known:
            return None
        filled, previous = [], known[0]
        for v in raw:
            previous = v if v is not None else previous
            filled.append(previous)
        top = Decimal(0)
        for i, v in enumerate(filled):
            top = max(top, v)
            filled[i] = top
        return dict(zip(rarities, filled))

    filled = defaultdict(int)
    for tokens in rows:
        category, _ = classify(tokens)
        stat = unquote(tokens[stat_i])
        if category is None or Decimal(unquote(tokens[value_i])) != 0:
            continue
        values = curve(pool(category, stat), stat)
        if values is not None:
            tokens[value_i] = format_like(values[int(unquote(tokens[col["Rarity"]]))], like)
            filled[stat] += 1

    new_rows = []
    # Row keys are numbers, except a few named rows (e.g. LancerS_Stock); continue after the highest number.
    next_id = max(int(unquote(t[0])) for t in rows if unquote(t[0]).isdigit()) + 1
    for key in sorted(mods, key=lambda k: tuple(int(x) if x.lstrip("-").isdigit() else x for x in k)):
        category, stats, by_rarity = mods[key]
        for stat in (WEAPON_STATS if category == "weapon" else ARMOUR_STATS):
            if stat in stats:
                continue
            values = curve(pool(category, stat), stat)
            if values is None:
                continue
            for rarity in sorted(by_rarity):
                tokens = list(by_rarity[rarity])
                quoted = tokens[stat_i].startswith('"')
                tokens[0] = str(next_id)
                tokens[stat_i] = f'"{stat}"' if quoted else stat
                tokens[value_i] = format_like(values[rarity], like)
                new_rows.append(tokens)
                next_id += 1
    return new_rows, filled


def scale_file(src, dst, factor, cap, grenade_factor, add_stats):
    raw = src.read_bytes().decode("utf-8")
    newline = "\r\n" if "\r\n" in raw else "\n"
    lines = raw.split(newline)
    tail = [lines.pop()] if lines[-1] == "" else []
    header = [unquote(t) for t in lines[0].split(",")]
    stat_i = header.index(STAT_COLUMN)
    type_i = header.index(TYPE_COLUMN) if TYPE_COLUMN in header else None
    value_i = next(header.index(c) for c in VALUE_COLUMNS if c in header)

    rows = []
    for number, line in enumerate(lines[1:], start=2):
        tokens = line.split(",")
        if len(tokens) != len(header):
            sys.exit(f"{src.name}:{number}: expected {len(header)} columns, got {len(tokens)}")
        rows.append(tokens)

    added, filled = defaultdict(int), {}
    if add_stats and all(c in header for c in MOD_COLUMNS):
        dotted = any(unquote(t[value_i]).startswith(".") for t in rows)
        new_rows, filled = build_new_rows(rows, header, ".5" if dotted else "0.5")
        for tokens in new_rows:
            added[unquote(tokens[stat_i])] += 1
        rows += new_rows

    stats = {}  # stat -> [scaled, kept (zero), capped, flipped]
    out = [lines[0]]
    for tokens in rows:
        stat = unquote(tokens[stat_i])
        original = unquote(tokens[value_i])
        value = Decimal(original)
        is_grenade = type_i is not None and unquote(tokens[type_i]) in GRENADE_TYPES and stat in GRENADE_STATS
        counts = stats.setdefault(stat + (" (grenade)" if is_grenade else ""), [0, 0, 0, 0])
        if value == 0:
            counts[1] += 1
        else:
            if value < 0:  # penalty (e.g. -2 magazine) becomes a bonus
                counts[3] += 1
            scaled = abs(value) * (grenade_factor if is_grenade else factor)
            if cap and stat in FRACTION_CAPS:
                limit = max(FRACTION_CAPS[stat], abs(value))
                if scaled > limit:
                    scaled = limit
                    counts[2] += 1
            counts[0] += 1
            tokens[value_i] = format_like(scaled, original)
        out.append(",".join(tokens))

    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(newline.join(out + tail).encode("utf-8"))
    return stats, added, filled


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("inputs", nargs="*", type=Path, help="CSV files (default: original/*.csv)")
    parser.add_argument("--out", type=Path, default=Path("mod"), help="output folder (default: mod)")
    parser.add_argument("--factor", type=Decimal, default=Decimal(3), help="multiplier (default: 3)")
    parser.add_argument("--grenade-factor", type=Decimal, default=Decimal(6),
                        help="multiplier for frag/stim grenade damage and healing (default: 6)")
    parser.add_argument("--no-cap", action="store_true", help="allow Evasion/Resilience above 90%%")
    parser.add_argument("--no-add-stats", action="store_true", help="don't add missing stats to mods")
    args = parser.parse_args()

    inputs = args.inputs or sorted(Path("original").glob("*.csv"))
    if not inputs:
        sys.exit("No input CSVs found. Put the originals in original/ or pass them as arguments.")
    for src in inputs:
        stats, added, filled = scale_file(src, args.out / src.name, args.factor, not args.no_cap,
                                  args.grenade_factor, not args.no_add_stats)
        print(f"{src.name}" + (f"  (+{sum(added.values())} rows, {sum(filled.values())} zero rows filled)" if added else ""))
        for stat, (scaled, kept, capped, flipped) in sorted(stats.items()):
            notes = (f", {flipped} penalties flipped" if flipped else "") + (f", {capped} capped at 90%" if capped else "")
            notes += f", {added[stat]} added" if added.get(stat) else ""
            notes += f", {filled[stat]} zeros filled" if filled.get(stat) else ""
            mult = args.grenade_factor if "(grenade)" in stat else args.factor
            print(f"  {stat:28} x{mult}: {scaled:4} rows, {kept:3} zero{notes}")


if __name__ == "__main__":
    main()
