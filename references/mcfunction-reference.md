# Raw mcfunction Reference

For pure datapack work without Python tooling.

---

## Pack structure

```
my-pack/
├── pack.mcmeta
└── data/
    ├── minecraft/
    │   └── tags/
    │       └── function/
    │           ├── load.json
    │           └── tick.json
    └── <namespace>/
        ├── function/
        │   ├── load.mcfunction
        │   ├── tick.mcfunction
        │   └── helpers/
        │       └── util.mcfunction
        ├── loot_table/
        ├── advancement/
        ├── predicate/
        ├── recipe/
        └── tags/
            └── function/
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

Use a pack_format range for compatibility across versions:
```json
{
  "pack": {
    "pack_format": 61,
    "supported_formats": [48, 61],
    "description": "Works on 1.21–1.21.4"
  }
}
```

---

## Function tags

### minecraft:load — runs once on world load / /reload
`data/minecraft/tags/function/load.json`:
```json
{ "values": ["mynamespace:load"] }
```

### minecraft:tick — runs every game tick (20/sec)
`data/minecraft/tags/function/tick.json`:
```json
{ "values": ["mynamespace:tick"] }
```

Keep tick functions lightweight — call sub-functions rather than putting all logic in tick.

---

## Core commands

### execute
The most powerful command — chains context modifiers before a run clause.
```mcfunction
# as <selector> — change execution entity
execute as @a run say I am a player

# at <selector> — change position to entity
execute at @p run summon minecraft:zombie ~ ~ ~

# if/unless entity
execute if entity @s[tag=initialized] run function ns:already_setup
execute unless entity @s[tag=initialized] run function ns:first_setup

# if/unless block
execute if block ~ ~-1 ~ minecraft:grass_block run say On grass!

# if/unless score
execute if score @s kills matches 10.. run function ns:reward

# store result — write command output to score or storage
execute store result score @s temp run data get entity @s Health

# positioned / in — change coordinates or dimension
execute in minecraft:the_nether positioned 0 64 0 run summon minecraft:blaze

# Chain multiple
execute as @a at @s if block ~ ~-1 ~ minecraft:water run say In water!
```

### scoreboard
```mcfunction
# Create objective (in load)
scoreboard objectives add kills minecraft.player_killed_entity:minecraft.player
scoreboard objectives add points dummy "Points"

# Modify scores
scoreboard players add @s kills 1
scoreboard players remove @s kills 1
scoreboard players set @s kills 0
scoreboard players operation @s points = @s kills

# Arithmetic operations (=, +=, -=, *=, /=, %=, <, >, ><)
scoreboard players operation @s temp *= @s multiplier

# Read in selector
@a[scores={kills=10..}]
@a[scores={kills=..5}]
@a[scores={kills=3..7}]
```

### data (NBT)
```mcfunction
# Get entity data
data get entity @s Health
data get entity @s Inventory[0]

# Set entity data
data modify entity @s CustomName set value '"Bob"'
data modify entity @s Tags append value "my_tag"

# Storage (key-value store not tied to an entity)
data modify storage mynamespace:db counter set value 0
data get storage mynamespace:db counter

# Execute store with data
execute store result storage mynamespace:db counter int 1 run scoreboard players get @s points
```

### tag
```mcfunction
tag @s add initialized
tag @s remove initialized
execute if entity @s[tag=initialized] run say already set up
```

### team
```mcfunction
team add red "Red Team"
team join red @s
execute if entity @s[team=red] run say I am on red team
```

### tellraw / title
```mcfunction
# tellraw uses JSON text components
tellraw @a {"text":"Hello!","color":"gold","bold":true}
tellraw @a ["Text ",{"score":{"name":"@s","objective":"kills"}}," kills"]

# title
title @a title {"text":"Round Start!","color":"yellow"}
title @a subtitle {"text":"Good luck","color":"white"}
title @a times 10 40 10
title @a clear
```

### summon
```mcfunction
summon minecraft:zombie ~ ~ ~ {CustomName:'"Bob"',IsInvincible:true}
summon minecraft:armor_stand ~ ~ ~ {Invisible:true,Marker:true,Tags:["my_marker"]}
```

### give / clear
```mcfunction
give @s minecraft:diamond_sword{Enchantments:[{id:"sharpness",lvl:5}]} 1
clear @s minecraft:dirt
```

### effect
```mcfunction
effect give @s minecraft:speed 30 2 true
effect give @a minecraft:night_vision 99999 0 true
effect clear @s minecraft:speed
```

### tp / teleport
```mcfunction
tp @s 0 64 0
tp @s ~ ~10 ~
tp @s @p
```

---

## Selectors

```mcfunction
@p    # nearest player
@a    # all players
@e    # all entities
@s    # executing entity
@r    # random player
@e[type=minecraft:zombie]
@a[gamemode=survival]
@a[distance=..10]           # within 10 blocks
@a[nbt={SelectedItem:{id:"minecraft:stick"}}]
@e[tag=my_tag]
@e[scores={kills=1..}]
@e[limit=1,sort=nearest,type=minecraft:zombie]
```

---

## Macros (1.20.2+ / pack_format 18+)

Macros let you pass arguments into functions at runtime via storage.

```mcfunction
# caller
data modify storage ns:args {} set value {name: "Steve", count: 5}
function ns:greet with storage ns:args {}

# ns:greet.mcfunction
$say Hello $(name), you have $(count) items!
```

The `$` prefix marks a macro line. The function must be called with `function ... with storage/entity/block`.

---

## Useful patterns

### One-time setup guard
```mcfunction
# load.mcfunction
execute unless score #setup ns_flags matches 1 run function ns:setup

# setup.mcfunction
scoreboard objectives add ns_flags dummy
scoreboard players set #setup ns_flags 1
# ... rest of setup
```

### Recursive countdown (using schedule)
```mcfunction
# ns:countdown
execute if score #timer ns matches 1.. run schedule function ns:countdown 1t
scoreboard players remove #timer ns 1
```

### Conditional chain (function per branch)
```mcfunction
# main dispatch
execute if score @s state matches 0 run function ns:state/idle
execute if score @s state matches 1 run function ns:state/walking
execute if score @s state matches 2 run function ns:state/attacking
```

### Fake player constants
```mcfunction
# In load — set constants using fake player names
scoreboard players set #CONST_20 ns_math 20
scoreboard players set #CONST_100 ns_math 100
```

---

## Common mistakes

- `execute run function` — don't nest execute/run for simple function calls, just use `function`
- Empty tick function — even an empty tick.mcfunction called 20/sec wastes performance; use `schedule` or `execute if` guards
- Tag JSON arrays overwrite by default in vanilla — use beet if you need safe merging across multiple files
