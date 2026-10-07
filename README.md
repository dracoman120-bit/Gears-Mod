# Gears Tactics: 3x Mod Stats

Triples the stat bonuses of every weapon mod, attachment, armour piece and grenade mod in Gears Tactics (Steam).
It works by editing the game's stat tables (CSV files); no game code is touched.

## Install

1. In your Gears Tactics Steam folder, find the four files below. Search the install folder for the filenames.
2. **Back up the originals** (copies of them are also in `original/`).
3. Copy the files from `mod/` over the ones in the game folder:
   - `WeaponModsAndArmour.csv` (campaign)
   - `WeaponModsAndArmour_Operation.csv` (operations)
   - `ArtifactWeaponMods.csv`
   - `ArtifactArmours.csv`
4. Launch the game. To uninstall, put the originals back (or use Steam > Verify integrity of game files).

Game updates may overwrite the files; re-copy them afterwards. Keep it to single-player/co-op with friends who run the same files.

## What changes

- Every positive stat value is multiplied by 3 (damage, accuracy, crit chance, crit multiplier, range, magazine size, healing, health, evasion, resilience, defence, movement).
- Penalties (e.g. -2 magazine size, -40 damage) and zero values are left alone, so drawbacks don't get tripled.
- Evasion and Resilience are capped at 100%. Without the cap, some values would exceed 1.0, which the game may not handle well. Use `--no-cap` to disable.
- Research, equip and scrap costs are unchanged.

## Rebuild or change the multiplier

```
python3 scripts/scale_mods.py                 # original/*.csv -> mod/*.csv, 3x
python3 scripts/scale_mods.py --factor 2      # different multiplier
python3 scripts/scale_mods.py --no-cap        # allow Evasion/Resilience above 100%
```

The script always reads from `original/`, so running it repeatedly never compounds the multiplier.

## Status

Untested in-game. The output was verified against the originals (row counts, line endings, and that only the value column changed). If the game misbehaves, try `--factor 2`.
