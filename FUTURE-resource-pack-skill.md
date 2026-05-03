# TODO: Resource Pack Skill

Create a `resourcepack-expert` skill covering Minecraft Java Edition resource packs.

## What it should cover

- `assets/` directory structure (textures, sounds, models, lang, shaders, blockstates)
- `pack.mcmeta` with `filter` and `overlays` (modern format)
- Custom block/item models using the vanilla model format
- Custom textures and texture animation (`.mcmeta` per texture)
- Custom sounds and `sounds.json`
- Language files (`lang/en_us.json`) and custom translations
- Custom fonts and `font/default.json`
- Beet integration for resource packs: `ctx.assets`, `ResourcePack`, `Texture`, `SoundConfig`
- Merging resource packs with beet

## Why deferred

The current `mcfunction-expert` skill focuses on data packs only to keep scope tight.
Resource packs are a parallel concern — same `beet` toolchain but different file types.

## Suggested eval cases

1. "Add a custom texture for dirt blocks"
2. "Create a resource pack that makes swords glow"
3. "Add a custom sound that plays when a player levels up"
