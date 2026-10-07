#!/usr/bin/env python3
"""Scale the stat bonuses of Gears Tactics weapon mods, attachments, armour and grenades.

Reads the original CSVs (never modifies them) and writes modified copies.
Only the stat value column is changed; costs, ids and formatting are kept as-is.
Penalties (negative values) are flipped to positive before scaling.
Grenade damage/healing mods get their own, larger multiplier.
"""
import argparse
import sys
from decimal import Decimal
from pathlib import Path

VALUE_COLUMNS = ("ModificationValue", "MaxModificationValue")
STAT_COLUMN = "ModifiedStatName"
TYPE_COLUMN = "WeaponType"
# Grenade weapon types (frag and stim; the data does not say which is which) and the stats boosted further.
GRENADE_TYPES = {"7", "15"}
GRENADE_STATS = {"WeaponDamage", "WeaponHealing"}
# Fraction stats are capped at 90%.
FRACTION_CAPS = {"Evasion": Decimal("0.9"), "Resilience": Decimal("0.9")}


def unquote(token):
    return token[1:-1] if len(token) >= 2 and token[0] == token[-1] == '"' else token


def format_like(value, original):
    """Format `value` the way the game's export does (no trailing zeros, ".5" vs "0.5")."""
    text = format(value.normalize(), "f")
    if original.lstrip("-").startswith(".") and text.lstrip("-").startswith("0."):
        text = text.replace("0.", ".", 1)
    return text


def scale_file(src, dst, factor, cap, grenade_factor):
    raw = src.read_bytes().decode("utf-8")
    newline = "\r\n" if "\r\n" in raw else "\n"
    lines = raw.split(newline)
    header = [unquote(t) for t in lines[0].split(",")]
    stat_i = header.index(STAT_COLUMN)
    type_i = header.index(TYPE_COLUMN) if TYPE_COLUMN in header else None
    value_i = next(header.index(c) for c in VALUE_COLUMNS if c in header)

    stats = {}  # stat -> [scaled, kept (zero), capped, flipped]
    out = [lines[0]]
    for number, line in enumerate(lines[1:], start=2):
        if not line.strip():
            out.append(line)
            continue
        tokens = line.split(",")
        if len(tokens) != len(header):
            sys.exit(f"{src.name}:{number}: expected {len(header)} columns, got {len(tokens)}")
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
    dst.write_bytes(newline.join(out).encode("utf-8"))
    return stats


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="*", type=Path, help="CSV files (default: original/*.csv)")
    parser.add_argument("--out", type=Path, default=Path("mod"), help="output folder (default: mod)")
    parser.add_argument("--factor", type=Decimal, default=Decimal(3), help="multiplier (default: 3)")
    parser.add_argument("--grenade-factor", type=Decimal, default=Decimal(6),
                        help="multiplier for frag/stim grenade damage and healing (default: 6)")
    parser.add_argument("--no-cap", action="store_true", help="allow Evasion/Resilience above 90%%")
    args = parser.parse_args()

    inputs = args.inputs or sorted(Path("original").glob("*.csv"))
    if not inputs:
        sys.exit("No input CSVs found. Put the originals in original/ or pass them as arguments.")
    for src in inputs:
        stats = scale_file(src, args.out / src.name, args.factor, not args.no_cap, args.grenade_factor)
        print(f"{src.name}")
        for stat, (scaled, kept, capped, flipped) in sorted(stats.items()):
            notes = (f", {flipped} penalties flipped" if flipped else "") + (f", {capped} capped at 90%" if capped else "")
            mult = args.grenade_factor if "(grenade)" in stat else args.factor
            print(f"  {stat:28} x{mult}: {scaled:4} rows, {kept:3} zero{notes}")


if __name__ == "__main__":
    main()
