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
- Penalties (e.g. -2 magazine size, -40 damage, -15 crit chance, -1 movement) are flipped to positive and then tripled, so they become bonuses too (-2 magazine becomes +6).
- Evasion and Resilience are capped at 90%. Use `--no-cap` to disable.
- Frag/stim grenade mods (weapon types 7 and 15) get **6x** on damage and healing instead of 3x. The data doesn't say which of the two types is frag and which is stim, so both are boosted; the unused stat on each has no effect. The other grenade-slot item (type 6) stays at 3x. Change this with `--grenade-factor`.
- **Every weapon mod and armour piece now carries every stat for its type**, tiered by rarity (the stat's typical value at that rarity, then multiplied like everything else). Weapon mods get damage, accuracy, crit chance, crit multiplier, magazine size and movement; armour gets health, evasion, resilience and movement. Stats a mod already listed at 0 are filled in too.
  - Values come from the median of the game's existing values for that stat at each rarity (movement uses weapons and armour together), never dropping as rarity rises.
  - New rows are appended to the end of the two main CSVs (`WeaponModsAndArmour.csv` +2,364 rows, `WeaponModsAndArmour_Operation.csv` +2,462) and copy the costs of the mod they belong to. Grenade mods and the two Artifact files don't get extra stats.
  - Movement is the big one: top-rarity mods now give +6 movement each, and it stacks across a weapon's four mods plus armour.
- Research, equip and scrap costs are unchanged.

## Rebuild or change the multiplier

```
python3 scripts/scale_mods.py                 # original/*.csv -> mod/*.csv, 3x
python3 scripts/scale_mods.py --factor 2      # different multiplier
python3 scripts/scale_mods.py --grenade-factor 10   # different grenade damage/healing multiplier
python3 scripts/scale_mods.py --no-add-stats  # skip adding missing stats
python3 scripts/scale_mods.py --no-cap        # allow Evasion/Resilience above 90%
```

The script always reads from `original/`, so running it repeatedly never compounds the multiplier.

## Status

Untested in-game. The output was verified against the originals (original rows kept in place, only values changed, every mod has the full stat set, no duplicate keys, costs match). It is unknown whether the game's UI can display this many stats per mod. If the game misbehaves, try `--no-add-stats` or `--factor 2`.
