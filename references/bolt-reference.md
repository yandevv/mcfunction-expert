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
  "minecraft": "1.21.4",
  "output": "build",
  "require": ["bolt"],
  "pipeline": ["bolt"],
  "data_pack": {
    "load": ["src"]
  }
}
```

### File placement

`.bolt` files go in the same location as `.mcfunction` files:
```
src/data/mynamespace/function/main.bolt
```

This compiles to `data/mynamespace/function/main.mcfunction` in the output.

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

### Importing from other bolt files
```python
# In src/data/mynamespace/function/utils.bolt
def heal(amount):
    effect give @s minecraft:instant_health 1 {amount}

# In another .bolt file
from mynamespace:utils import heal
heal(2)
```

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

Given `src/data/mynamespace/function/main.bolt`:
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
- You can mix `.bolt` and `.mcfunction` files in the same project
- Use `beet watch` during development for instant feedback
- The compiled output in `build/` is valid, readable mcfunction — useful for debugging
- Full bolt docs: https://mcbeet.dev (search "bolt" in the docs)
- Full bolt-expressions docs: https://rx-modules.github.io/bolt-expressions/
