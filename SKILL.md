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

| Situation | Use |
|-----------|-----|
| Simple pack, no tooling, just writing commands | **Raw `.mcfunction`** |
| Need to manage multiple files, merge packs, or write Python plugins | **Beet** |
| Need loops, variables, Python logic that generates commands | **Bolt** (requires Beet) |

When in doubt, ask the user. Bolt is the most powerful but requires Python + uv/pip. Raw mcfunction is zero-dependency.

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

Bolt lets you write `.bolt` files using Python-like syntax that compiles down to `.mcfunction`. It lives inside a beet project.

### Install
```bash
uv tool install beet
uv add bolt              # or: pip install bolt
```

### beet.json with Bolt
```json
{
  "name": "my-pack",
  "output": "build",
  "require": ["bolt"],
  "pipeline": ["bolt"],
  "data_pack": {
    "load": ["src"]
  }
}
```

### Example .bolt file
`src/data/mynamespace/function/main.bolt`:
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

For mid-scale design questions — minigames, multi-version packs, tracking systems, tick-heavy logic, role-based games, custom-item lifecycles — read `references/datapack-patterns.md`. It distills idioms from popular community datapacks (currently: Manhunt) organized by category: state machines, tick budgeting, entity-selection algorithms, cross-version dispatch, item identity & lifecycle, macros & storage, dimension handling, state transitions, teams & roles, initialization, naming.

Reach for it whenever the user is *designing* something rather than asking about a single command.
