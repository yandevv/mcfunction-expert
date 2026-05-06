---
name: mcfunction-expert
description: >
  Expert guide for creating Minecraft Java Edition datapacks using .mcfunction files,
  Beet (the Python-based pack development toolkit), and Bolt (Python-like scripting
  that compiles to .mcfunction). Use this skill whenever the user mentions datapacks,
  mcfunction, beet, bolt, Minecraft commands, scoreboard, NBT, function tags,
  pack.mcmeta, beet.json, .bolt files, bolt-expressions, loot tables, advancements,
  predicates, or any Minecraft Java Edition pack development — even if they say
  "I want to make a Minecraft mod", "help me with Minecraft commands", "how do I
  make a kill counter", or "I'm working on a datapack". Trigger proactively whenever
  the conversation is about authoring or modifying Minecraft data packs.
---

# mcfunction-expert

A guide for creating Minecraft Java Edition datapacks, covering three tiers of tooling.

## Step 1: Always establish the Minecraft version

Before writing any code, ask the user which Minecraft version they're targeting. The version determines:
- The correct `pack_format` number for `pack.mcmeta`
- Which commands and syntax are available
- Whether newer features (like macro functions `$()`) are available

If the user doesn't know or says "latest", default to **1.21.4** (pack_format 61). See `references/beet-reference.md` for the full pack_format table.

## Step 2: Choose the right approach

| Situation | Use | Why |
|-----------|-----|-----|
| Simple pack, no tooling, just writing commands | **Raw `.mcfunction`** | Zero dependencies, ships exactly what Minecraft loads — no build step to debug, no toolchain for the user to install. The right floor when the pack is small enough that a human can hold its file tree in their head. |
| Need to manage multiple files, merge packs, or write Python plugins | **Beet** | Adds a build pipeline (file merging, output linking to a world, plugin hooks) without changing the language you write in. Pick this when project structure — not the commands themselves — is what's getting unwieldy. |
| Need loops, variables, Python logic that generates commands | **Bolt** (requires Beet) | Real control flow at *author time*: `for`, `if`, function defs, f-strings expand into raw commands during build. Pick this when you'd otherwise be copy-pasting near-identical command lines or hand-unrolling loops. |

When in doubt, ask the user. The boundary cases — e.g. "three commands plus one small loop" or "two files but no real logic" — usually resolve by asking *which axis is the pain on*: file management → Beet, repetitive command generation → Bolt, neither → stay raw. Bolt is the most powerful but requires Python + uv/pip; raw mcfunction is zero-dependency.

---

## Scaffolding a new project

Don't hand-emit boilerplate (`pack.mcmeta`, `beet.json`, function tags, load/tick stubs) — the skill bundles a script that does it from canonical templates in `assets/templates/`:

```bash
python scripts/scaffold_pack.py \
  --name my-pack --namespace mypack \
  --mc-version 1.21.4 [--with-bolt] [--out ./my-pack]
```

This writes the full tree (raw or Beet+Bolt depending on `--with-bolt`) with the correct `pack_format` for the version. Use it whenever the user is starting a new pack; spend your tokens on the *feature* they're asking for, not on retyping scaffolding. The templates themselves live in `assets/templates/` if you need to inspect or override pieces.

---

## Raw `.mcfunction` approach

### Project structure
```
my-pack/
├── pack.mcmeta
└── data/
    └── <namespace>/
        ├── function/
        │   ├── load.mcfunction
        │   └── tick.mcfunction
        └── tags/
            └── function/
                ├── minecraft/load.json   ← or data/minecraft/tags/function/load.json
                └── minecraft/tick.json
```

### pack.mcmeta
```json
{
  "pack": {
    "pack_format": 61,
    "description": "My datapack"
  }
}
```

### Function tags (hooking into load/tick)
`data/minecraft/tags/function/load.json`:
```json
{ "values": ["mynamespace:load"] }
```

`data/minecraft/tags/function/tick.json`:
```json
{ "values": ["mynamespace:tick"] }
```

For full command reference and patterns, read `references/mcfunction-reference.md`.

---

## Beet approach

### Install
```bash
uv tool install beet        # recommended
# or: pip install beet
```

### Minimal beet.json
```json
{
  "name": "my-pack",
  "description": "My datapack",
  "output": "build",
  "data_pack": {
    "load": ["src"]
  }
}
```

Put your raw `.mcfunction` files under `src/data/<namespace>/function/` — beet copies and merges them into the output.

### Running beet
```bash
beet build       # one-time build
beet watch       # auto-rebuild on file changes
beet build --link "My World"   # build + link to Minecraft world
```

For the full beet config schema, Python plugin API, and pack_format table, read `references/beet-reference.md`.

---

## Bolt approach

Bolt lets you write Python-like syntax that compiles down to `.mcfunction`. It lives inside a beet project and is parsed by **mecha** (the compiler) with bolt's parser extensions layered on top.

### Install
```bash
uv tool install beet
uv add bolt mecha        # or: pip install bolt mecha
```

### beet.json with Bolt
```json
{
  "name": "my-pack",
  "output": "build",
  "require": ["bolt"],
  "pipeline": ["bolt", "mecha"],
  "data_pack": {
    "load": ["src"]
  }
}
```

`bolt` registers the parser; `mecha` runs the compile step that emits `.mcfunction`. **Without `mecha` in the pipeline the build succeeds silently but the output `.mcfunction` files contain unexpanded Python source — loops never unroll, f-strings never interpolate.**

### Where Bolt code lives — important

There are two distinct file types:

- **Function with Bolt syntax** → `src/data/<ns>/function/<name>.mcfunction`. Yes, `.mcfunction` extension. With `bolt` + `mecha` in the pipeline, Bolt syntax (Python `for`/`def`/f-strings) is parsed inside `.mcfunction` files. This is what becomes callable as `/function ns:name` in-game.
- **Reusable Python module imported by other Bolt code** → `src/data/<ns>/module/<name>.bolt`. The `.bolt` extension is scoped to `module/` (or `modules/` pre-pack-format-48), not `function/`. A `.bolt` file under `function/` is loaded as a Python library and silently dropped from the data pack — you'll see no `.mcfunction` output for it and `/function ns:name` returns "Unknown function".

### Example function with Bolt syntax
`src/data/mynamespace/function/main.mcfunction`:
```python
# Variables and loops compile to commands
for i in range(5):
    summon minecraft:zombie ~{i} ~ ~ {Tags: [f"zombie_{i}"]}

# Define reusable functions
def heal_player(amount):
    effect give @s minecraft:instant_health 1 {amount}

heal_player(2)
```

### Key bolt syntax
```python
# Direct Minecraft commands pass through
say Hello world
tp @s 0 64 0

# Python variables
count = 10
message = "hello"

# F-string interpolation
tellraw @a f"Count is {count}"
tag @s add f"player_{count}"

# Loops
for i in range(count):
    give @s minecraft:apple {i}

# Functions
def spawn_mobs(n, mob):
    for i in range(n):
        summon {mob} ~{i} ~ ~

spawn_mobs(5, "minecraft:zombie")

# Conditionals
if score @s kills matches 10..:
    title @s title "10 Kills!"
```

### bolt-expressions (scoreboard math)
```python
from bolt_expressions import Scoreboard

kills = Scoreboard.objective("kills")

# Read and write scoreboards like Python variables
kills["@s"] += 1
kills["@s"] = kills["@s"] * 2

# Comparison triggers an execute if block
if kills["@s"] >= 10:
    say You reached 10 kills!
```

For the complete bolt syntax guide and bolt-expressions patterns, read `references/bolt-reference.md`.

---

## Common patterns quick reference

### Scoreboard (raw mcfunction)
```mcfunction
# In load.mcfunction
scoreboard objectives add kills minecraft.player_killed_entity:minecraft.player

# In tick.mcfunction
execute as @a[scores={kills=10..}] run function mynamespace:reward
```

### Execute chain pattern
```mcfunction
execute as @a at @s if block ~ ~-1 ~ minecraft:grass_block run say Standing on grass!
```

### Calling functions from load/tick
Never put heavy logic in tick directly — call a named function:
```mcfunction
# tick.mcfunction
function mynamespace:loop/main
```

### Storage and NBT
```mcfunction
data modify storage mynamespace:db counter set value 0
execute store result storage mynamespace:db counter int 1 run scoreboard players get @s kills
```

---

## Architectural patterns from real datapacks

For mid-scale design questions — minigames, multi-version packs, tracking systems, tick-heavy logic, role-based games, custom-item lifecycles, procedural structures, loot tables — read `references/datapack-patterns.md`. It distills idioms from popular community datapacks (Manhunt, BattleTowers, Vanilla-Refresh) organized by category:

- State machines & global state, tick budgeting (including multi-speed scheduled clock loops), entity-selection algorithms (including locating just-mined blocks via fresh-item locator)
- **Runtime configuration** (storage-based feature toggles, optional addon handshake via shared init score)
- Cross-version dispatch (including pack.mcmeta overlays for 1.21.4+), item identity & lifecycle (including custom enchantments with `minecraft:tick` run_function effects), macros & storage (including stack-pop iteration over storage lists, dynamic per-key objectives, NBT↔scoreboard bidirectional sync)
- **Vanilla event hooks** (statistic-criteria scoreboards as block/item event hooks)
- Dimension handling, game-state transitions (advancement revocation triggers, trigger-based player menus, OP-side `tellraw` admin chat menus), teams & roles, entity manipulation
- **Marker entities & block tracking** (pseudo-block state, per-block logic ownership)
- **Raycasting & spatial recursion** (recursive local-Z forward raycast, 6-neighbor 3D flood fill for vein-style propagation)
- **Predicates & player input** (equipment slot checks, player jump/sneak/sprint detection — 1.21.3+, probability stacking via repeated predicate calls for Fortune-style multipliers)
- Initialization (load vs first_load, per-player tick sub-function, first-join detection), naming conventions (math constants, public API + `internal/` directory layout)
- **Worldgen terrain & biomes** (custom biome anatomy with positional features-by-step array, configured/placed feature split, noise parameter files, density function composition with `cache_once`/`min`/`max`/`range_choice`, `multi_noise` 6-axis dimension dispatch, tag-based `has_structure` decoupling, hierarchical folder conventions for large packs)
- **Structure worldgen** (Jigsaw pipeline, structure_set, template pools, additions pools, `terrain_adaptation` modes)
- **Processor lists** (block substitution, barrier-as-editor-marker removal)
- **Loot tables** (vanilla table reuse, quality/luck scaling, nesting, location-conditional items, random_sequence, enchantment functions, mob drop tables, count distributions)

Reach for it whenever the user is *designing* something rather than asking about a single command.
