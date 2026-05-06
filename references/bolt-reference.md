# Bolt Reference

Bolt is a Python-like scripting language for Minecraft datapacks that compiles to `.mcfunction`.
It is part of the beet monorepo. Install: `pip install bolt` or `uv add bolt`.
Repo: https://github.com/mcbeet/beet (bolt lives in `packages/bolt/`)

---

## Setup

### beet.json
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

`bolt` registers parser extensions for Python-like syntax; `mecha` runs the actual compile step (`mc.compile(...)`) that emits `.mcfunction`. **If `mecha` is omitted from the pipeline, the build succeeds with no warning but the output `.mcfunction` files still contain raw Python source** — loops are not unrolled, f-strings are not interpolated. Both must be present.

The `"minecraft"` field is intentionally absent here. When it is set, beet auto-generates a `pack.mcmeta` on every build that overwrites any hand-written one in `src/`. Either let beet manage the metadata (set `"minecraft"`, do not write your own `pack.mcmeta`) or manage `pack.mcmeta` yourself (omit `"minecraft"`, place the file at `src/pack.mcmeta`). See `references/beet-reference.md` for the 1.21+ `pack.mcmeta` template.

### File placement — Bolt has two file types, not one

This is the most common failure mode for first-time Bolt users.

**Function with Bolt syntax** lives in `function/` with the **`.mcfunction`** extension:
```
src/data/mynamespace/function/main.mcfunction
```
With `bolt` + `mecha` in the pipeline, Bolt syntax (Python `for`/`def`/f-strings) is accepted inside `.mcfunction` files. This is what compiles to a callable `/function ns:main`.

**Reusable Python module** imported by other Bolt code lives in `module/` (or `modules/` for pre-pack-format-48 packs) with the **`.bolt`** extension:
```
src/data/mynamespace/module/utils.bolt
```
This is what `.bolt` is actually scoped to (see Bolt's `Module.scope` in `bolt/module.py`). A `.bolt` file is **not** a Minecraft function and is not callable as `/function ns:name` — it's a library imported via `from mynamespace:utils import ...`.

> **Pitfall.** A `.bolt` file placed under `function/` is loaded as a Python module and silently dropped from the data pack output. The build prints no warning. In-game, `/function ns:name` returns "Unknown function". If you see this symptom, check the file extension first.

---

## Core syntax

### Commands pass through unchanged
```python
say Hello world
tp @s 0 64 0
give @s minecraft:diamond 1
```

### Variables
```python
# Python variables — used for interpolation only, not compiled to NBT
count = 10
name = "zombie"
damage = 2.5
```

### F-string interpolation
Use `f"..."` to embed Python values in commands:
```python
n = 5
tag = "wave_1"
summon minecraft:zombie ~{n} ~ ~ {Tags: [f"{tag}"]}
tellraw @a f"Spawning {n} zombies"
```

### Loops
```python
for i in range(5):
    summon minecraft:zombie ~{i} ~ ~ {Tags: [f"zombie_{i}"]}

# Nested
for x in range(3):
    for z in range(3):
        setblock ~{x} ~ ~{z} minecraft:stone
```

### Conditionals
```python
# execute if/unless wrapping
if score @s kills matches 10..:
    title @s title "10 Kills!"
    function mynamespace:reward

if entity @s[type=minecraft:player]:
    say I am a player

unless entity @s[tag=initialized]:
    tag @s add initialized
    function mynamespace:setup
```

### Functions
```python
def spawn_wave(n, mob):
    for i in range(n):
        summon {mob} ~{i} ~ ~

spawn_wave(5, "minecraft:zombie")
spawn_wave(3, "minecraft:skeleton")
```

Functions defined with `def` compile to inline commands at the call site (not separate .mcfunction files unless you use the `@function` decorator).

### Named mcfunction via decorator
```python
@function mynamespace:helpers/spawn_zombie
def spawn_zombie():
    summon minecraft:zombie ~ ~ ~
    say Zombie spawned!
```

This creates a separate `helpers/spawn_zombie.mcfunction` callable with `function mynamespace:helpers/spawn_zombie`.

### NBT dictionary literals
```python
invisibility_effect = {
    id: "minecraft:invisibility",
    duration: 999999,
    amplifier: 1,
    show_particles: false,
}

summon minecraft:zombie ~ ~ ~ {
    ActiveEffects: [invisibility_effect],
    IsBaby: true,
}
```

### Macros (1.20.2+)
```python
# Macro functions receive $variable from storage
function mynamespace:with_name with storage mynamespace:args {name: "Steve"}

# In the macro function file:
$say Hello $(name)!
```

---

## Module system

### Importing from other bolt modules
```python
# In src/data/mynamespace/module/utils.bolt   (NOTE: module/, not function/)
def heal(amount):
    effect give @s minecraft:instant_health 1 {amount}

# In another file (function/<name>.mcfunction or module/<name>.bolt):
from mynamespace:utils import heal
heal(2)
```

The import path uses the `<namespace>:<module-name>` form (no `module/` prefix in the path string — Bolt's resolver knows where modules live).

### Importing Python modules
```python
import math
radius = math.floor(5.7)
```

---

## bolt-expressions (scoreboard & NBT math)

Install: `pip install bolt-expressions` or `uv add bolt-expressions`

Add to beet.json:
```json
{ "require": ["bolt", "bolt_expressions"] }
```

### Scoreboard operations
```python
from bolt_expressions import Scoreboard

kills = Scoreboard.objective("kills")
temp = Scoreboard.objective("temp")

# Read/write like Python variables — compiles to scoreboard commands
kills["@s"] += 1
kills["@s"] -= 1
kills["@s"] *= 2
kills["@s"] /= 2
kills["@s"] %= 10

# Copy between players
kills["target"] = kills["@s"]

# Set to a literal value
kills["@s"] = 0
temp["@s"] = kills["@s"]
```

### Comparisons / conditionals
```python
from bolt_expressions import Scoreboard

kills = Scoreboard.objective("kills")

if kills["@s"] >= 10:
    title @s title "10 Kills!"

if kills["@s"] == kills["other_player"]:
    say Tied!

if kills["@s"] in 5..15:
    say Between 5 and 15 kills
```

### Data / NBT
```python
from bolt_expressions import Data

# Read from entity NBT
hp = Data.entity("@s")["Health"]

# Read from storage
counter = Data.storage("mynamespace:db")["counter"]

# Operations between scoreboard and storage
kills = Scoreboard.objective("kills")
kills["@s"] = counter  # copies storage value to scoreboard
counter = kills["@s"]  # copies scoreboard to storage
```

### Auto-initialization
bolt-expressions creates the scoreboard objectives automatically at load time in a generated `init_expressions.mcfunction` (registered to `minecraft:load`).

---

## Generated output structure

Given `src/data/mynamespace/function/main.mcfunction` (Bolt-syntax inside `.mcfunction`):
```python
from bolt_expressions import Scoreboard
kills = Scoreboard.objective("kills")
kills["@s"] += 1
```

Output in `build/`:
```
data/mynamespace/function/main.mcfunction
    → scoreboard players add @s kills 1

data/mynamespace/function/init_expressions.mcfunction
    → scoreboard objectives add kills dummy
data/minecraft/tags/function/load.json
    → { "values": ["mynamespace:init_expressions"] }
```

---

## Tips

- Bolt runs at build time — Python logic is fully evaluated; the output is plain `.mcfunction`
- You can mix `.bolt` (modules) and `.mcfunction` (functions, with or without Bolt syntax) in the same project. Remember: `.bolt` ↔ `module/`, `.mcfunction` ↔ `function/`. Cross those wires and the file silently disappears from the output.
- F-string interpolation works inside `tellraw` JSON arguments and at selector/objective token positions, not just in plain command text — e.g. `tellraw @a {"text":f"Score: {n}"}` and `scoreboard players set @s f"obj_{i}" 0` both compile correctly.
- Use `beet watch` during development for instant feedback
- The compiled output in `build/` is valid, readable mcfunction — useful for debugging
- Full bolt docs: https://mcbeet.dev (search "bolt" in the docs)
- Full bolt-expressions docs: https://rx-modules.github.io/bolt-expressions/
