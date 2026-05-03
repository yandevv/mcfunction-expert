# Datapack architecture patterns

Distilled idioms from real, popular community datapacks. Reach for this file when the user is designing **mid-scale logic** — a minigame, a tracking system, a multi-version pack, a tick-heavy mechanic — not when answering a one-line command question.

Each entry is structured as: **what it is**, **snippet**, **when to reach for it**, **source**.

Patterns are organized by category so future entries from other datapacks slot in alongside related ones.

---

## State machines & global state

### Fake-player scoreboard globals

**What it is.** Datapacks have no native "global variable" — but a scoreboard objective with a fake-player name (`Temp`, `Starts:`, `#global`) gives you one. One objective per logical variable; the fake player holds the value.

**Snippet.**
```mcfunction
# load
scoreboard objectives add game_state dummy
scoreboard objectives add game_ticks dummy
scoreboard players set Temp game_state 0

# tick
execute if score Temp game_state matches 1.. run function mypack:active_tick
```

**When to reach for it.** Any time you need a global flag, counter, or mode that isn't tied to a specific player or entity. Prefer this over entity tags for state — scoreboards survive chunk unloads predictably.

**Source.** Manhunt (`manhunt_enabled`, `manhunt_ticks`, `manhunt_lead` on the `Temp` fake player).

### Sentinel values over multiple booleans

**What it is.** A single integer objective with meaningful values (0 = off, 1 = phase A, 2 = phase B) is cleaner than three boolean objectives. Branch with `matches X..Y` ranges.

**Snippet.**
```mcfunction
# 0 disabled, 1 lead phase, 2 hunt phase
execute if score Temp game_state matches 1 run function mypack:lead_tick
execute if score Temp game_state matches 2 run function mypack:hunt_tick
execute if score Temp game_state matches 1.. run function mypack:any_active_tick
```

**When to reach for it.** Whenever your "is X?" booleans are mutually exclusive or ordered phases. Saves objective slots and makes phase transitions a single `scoreboard players set`.

**Source.** Manhunt (`manhunt_enabled` 0/1/2 for off/lead/hunt).

### Decision-flag dummy register

**What it is.** When a decision depends on multiple conditions, write the boolean *result* into a throwaway dummy score (`reg_1`), then dispatch on it. Avoids deeply nested `execute if ... if ... unless ...` chains.

**Snippet.**
```mcfunction
scoreboard players set Temp reg_1 0
execute unless score Temp current_min matches -2147483647.. run scoreboard players set Temp reg_1 1
execute if score Temp current_min matches -2147483647.. if score Temp candidate >= Temp current_min run scoreboard players set Temp reg_1 1
execute if score Temp reg_1 matches 1 run function mypack:apply_update
execute if score Temp reg_1 matches 0 run function mypack:fallback
```

**When to reach for it.** Three or more conditions feeding a single decision, or when the same decision is consumed by multiple subsequent commands. Read once, branch many.

**Source.** Manhunt (`update_compass_overworld.mcfunction` uses `reg_1`).

---

## Tick budgeting

### "Second" throttle via tick counter

**What it is.** Heavy work (entity iteration, distance math, item modification) runs every 20 ticks instead of every tick by counting up and resetting.

**Snippet.**
```mcfunction
# tick.mcfunction
scoreboard players add Temp tick_counter 1
execute if score Temp tick_counter matches 20.. run function mypack:second

# second.mcfunction
scoreboard players set Temp tick_counter 0
# ... heavy work here ...
```

**When to reach for it.** Any per-second logic: pathfinding-style calculations, broadcasting compass updates, sidebar refreshes, scanning all players. Lighter than `schedule function … 20t` and easier to pause/resume — just stop incrementing the counter.

**Source.** Manhunt (`tick.mcfunction` → `second.mcfunction`).

### Gate the entire tick on an enabled flag

**What it is.** Every line in `tick.mcfunction` is prefixed with `execute if score Temp <enabled> matches 1.. run …` so the pack costs near-zero when its feature is off.

**Snippet.**
```mcfunction
execute if score Temp game_state matches 1.. run function mypack:active_tick_logic
execute if score Temp game_state matches 1.. as @e[type=item,nbt={Item:{components:{"minecraft:custom_data":{Tracker:1b}}}}] run kill @s
```

**When to reach for it.** Any pack with an opt-in/opt-out toggle (most minigames, many utility packs). Keep tick.mcfunction guarded so users who installed the pack but haven't started it pay no per-tick cost.

**Source.** Manhunt.

---

## Entity selection algorithms

### Find-minimum over entities (closest, lowest, weakest)

**What it is.** To pick the entity that minimizes some scoreboard value: seed a fake-player "running min" to max int, iterate candidates with `execute as`, and in the iteration function conditionally update min and tag the winner.

**Snippet.**
```mcfunction
# caller
scoreboard players set Temp current_min 2147483647
execute as @e[tag=candidate] run function mypack:check_candidate

# check_candidate.mcfunction (executes "as @s")
execute if score Temp current_min > @s my_score run tag @e remove winner
execute if score Temp current_min > @s my_score run tag @s add winner
execute if score Temp current_min > @s my_score run scoreboard players operation Temp current_min = @s my_score
```

**When to reach for it.** "Closest player to X", "lowest-health mob", "first to reach Y", "leader of a leaderboard". Anything where you'd write a min/argmin in normal code.

**Source.** Manhunt (`find_closest.mcfunction` for the closest runner per hunter).

### Classify entities once on discovery

**What it is.** When iterating entities of a team or type, you don't want to re-categorize every tick. Tag them on first sighting (player vs non-player, valid vs invalid), then iterate with `tag=manhunt_true_runner` filters thereafter.

**Snippet.**
```mcfunction
# every second, find unclassified team members
execute as @e[team=runners,tag=!classified_player,tag=!classified_other] run function mypack:classify

# classify.mcfunction
execute as @s[type=player] run tag @s add classified_player
execute as @s[type=!player] run tag @s add classified_other
```

**When to reach for it.** Any team or selector that might pick up tamed animals, allay companions, or other unintended entities. Also useful for "first time we've seen this player" hooks.

**Source.** Manhunt (`handle_fake_runner.mcfunction` separates real runner players from tamed mobs on the runners team).

---

## Cross-version compatibility

### Dual `function/` + `functions/` directories

**What it is.** Minecraft renamed pack-data subfolders in 1.21 (`functions` → `function`, `tags/functions` → `tags/function`, etc.). Minecraft loads whichever exists. To support 1.17 through 1.21+ in one pack, ship **both** spellings of every directory and tag JSON.

**Layout.**
```
data/<ns>/function/foo.mcfunction      ← 1.21+ reads this
data/<ns>/functions/foo.mcfunction     ← ≤1.20 reads this
data/minecraft/tags/function/load.json
data/minecraft/tags/functions/load.json
```

Same trick for `predicate/` ↔ `predicates/`, `item_modifier/` ↔ `item_modifiers/`, etc.

**When to reach for it.** Distributing a pack publicly across many MC versions. Skip if the user is on a single known version — the duplication isn't worth it.

**Source.** Manhunt ships both spellings everywhere.

### `_new` / `_old` function variants for the NBT↔components break

**What it is.** MC 1.20.5 replaced item NBT (`item.tag.foo`) with components (`item.components.minecraft:foo`). The break is too deep to handle inline, so ship two versions of any function that touches item data and dispatch from a version-detect flag set at load.

**Snippet.**
```mcfunction
# load.mcfunction — detect once
# (a feature only present in 1.20.5+ flips the flag)
execute if items entity @s container.* minecraft:stick run scoreboard players set Temp version_new 1

# caller dispatches
execute if score Temp version_new matches 1 run function mypack:set_compass_new
execute if score Temp version_new matches 0 run function mypack:set_compass_old
```

```
function/set_compass_new.mcfunction  ← uses "minecraft:set_components"
function/set_compass_old.mcfunction  ← uses "minecraft:set_nbt"
item_modifiers/foo_components.json   ← components-format modifier
item_modifiers/foo_nbt.json          ← NBT-format modifier
```

**When to reach for it.** Whenever code has to read or write item data on packs that span the 1.20.5 boundary. The fault line is real and can't be papered over with conditionals — branch at the function level.

**Source.** Manhunt (`go_mad_new`/`go_mad_old`, `set_compass_*_new`/`_old`, `go_mad_components.json` vs `go_mad_nbt.json`).

---

## Item identity & lifecycle

### `custom_data` tag for item identity

**What it is.** Mark a special item with a `minecraft:custom_data` component (1.20.5+) or `tag` NBT (older), then identify it later by that field rather than by item type alone.

**Snippet.**
```mcfunction
# give with the marker
give @s minecraft:compass[minecraft:custom_data={Tracker:1b}]

# detect it later
execute as @a if items entity @s hotbar.* minecraft:compass[minecraft:custom_data~{Tracker:1b}] run say has tracker
```

**When to reach for it.** Any "special version of a vanilla item": tracker compasses, quest items, custom tools, currency. Don't rely on display name or lore — `custom_data` is the durable identifier.

**Source.** Manhunt (`Manhunt_tracker:1b` on the hunter compass).

### Tick-time cleanup of dropped custom items

**What it is.** Players drop or die with custom items, leaving them on the ground. Sweep them every tick with a cheap selector that filters on the same `custom_data` tag.

**Snippet.**
```mcfunction
# tick.mcfunction
execute as @e[type=item] if data entity @s Item.components."minecraft:custom_data".Tracker run kill @s
```

**When to reach for it.** Any pack where re-acquiring the item is the expected flow (per-life compass, per-round weapon). Prevents inventory duplication and item-entity buildup.

**Source.** Manhunt (`tick.mcfunction` line 7).

---

## Macros & storage

### Computed coordinates → storage → macro function

**What it is.** Need to bake runtime values into a command (e.g., set 38 inventory slots' lodestone targets to a runner's position)? Store the values in a data-storage path, then call a macro function `with storage`. Inside, prefix commands with `$` and use `$(VAR)` placeholders.

**Snippet.**
```mcfunction
# caller
execute store result storage mypack:compass_data X int 1 run scoreboard players get @e[tag=target,limit=1] pos_x
execute store result storage mypack:compass_data Y int 1 run scoreboard players get @e[tag=target,limit=1] pos_y
execute store result storage mypack:compass_data Z int 1 run scoreboard players get @e[tag=target,limit=1] pos_z
function mypack:set_compass with storage mypack:compass_data
```

```mcfunction
# set_compass.mcfunction (every line is a macro)
$item modify entity @s hotbar.0 mypack:compass_lodestone {X:$(X),Y:$(Y),Z:$(Z)}
$item modify entity @s hotbar.1 mypack:compass_lodestone {X:$(X),Y:$(Y),Z:$(Z)}
# ... slots 2..8, inventory.0..26, offhand ...
```

**When to reach for it.** Any time you'd otherwise hand-write 10+ near-identical commands that differ only in numeric/string values. Macros + storage are dramatically more maintainable than `execute store` chains into `data modify`.

**Source.** Manhunt (`update_compass_overworld.mcfunction` → `set_compass_overworld.mcfunction`).

### Item modifier referencing storage

**What it is.** An item modifier JSON can pull values from a data-storage source via `copy_nbt`, so the macro function only needs to call `item modify` once per slot — the JSON does the value injection.

**Snippet.** (`data/<ns>/item_modifiers/set_compass.json`)
```json
[
  { "function": "minecraft:copy_nbt",
    "source": { "type": "minecraft:storage", "source": "mypack:compass_data" },
    "ops": [{ "source": "X", "target": "LodestonePos.X", "op": "replace" }] },
  { "function": "minecraft:copy_nbt",
    "source": { "type": "minecraft:storage", "source": "mypack:compass_data" },
    "ops": [{ "source": "Y", "target": "LodestonePos.Y", "op": "replace" }] },
  { "function": "minecraft:copy_nbt",
    "source": { "type": "minecraft:storage", "source": "mypack:compass_data" },
    "ops": [{ "source": "Z", "target": "LodestonePos.Z", "op": "replace" }] },
  { "function": "minecraft:set_nbt", "tag": "{LodestoneTracked:0b}" }
]
```

**When to reach for it.** When values change at runtime but the *shape* of the modification is fixed. Combines well with the macro+storage pattern above.

**Source.** Manhunt (`item_modifiers/set_compass_nbt.json`).

---

## Dimension handling

### Predicate over `execute in`

**What it is.** To **test** the player's dimension, use a `location_check` predicate. To **change** execution context to another dimension, use `execute in <dim>`. They're not interchangeable — predicates are cheaper and don't switch the executor's frame of reference.

**Snippet.** (`predicates/in_nether.json`)
```json
{
  "condition": "minecraft:location_check",
  "predicate": { "dimension": "minecraft:the_nether" }
}
```

```mcfunction
execute as @a if predicate mypack:in_nether run function mypack:nether_only_logic
```

**When to reach for it.** Filtering players by dimension, gating commands by location, dimension-specific ticking. Reserve `execute in` for actually running commands inside a different dimension's coordinate space.

**Source.** Manhunt (`in_overworld.json`, `in_nether.json`, `in_end.json`).

### Parallel position storage per dimension

**What it is.** When you need to track an entity's last-known position separately per dimension (e.g., a tracker that points to where the runner was in *this* dimension last), keep parallel coordinate objectives suffixed by dimension.

**Snippet.**
```mcfunction
# objectives: pos_x_o pos_y_o pos_z_o (overworld), pos_x_n pos_y_n pos_z_n (nether)
execute as @a[team=runners] if predicate mypack:in_overworld run function mypack:store_pos_overworld
execute as @a[team=runners] if predicate mypack:in_nether     run function mypack:store_pos_nether
```

**When to reach for it.** Cross-dimension tracking, "return to last X" mechanics, dimension-aware leaderboards.

**Source.** Manhunt (`grab_position.mcfunction`).

### Sentinel pitfall: 0/0/0 means "never visited"

**What it is.** Position objectives default to 0. If you compute distance to a target that's never been to a dimension, you'll point at world-origin garbage. Detect the all-zero case explicitly and bail out.

**Snippet.**
```mcfunction
execute if score @e[tag=target,limit=1] pos_x_n matches 0 \
        if score @e[tag=target,limit=1] pos_y_n matches 0 \
        if score @e[tag=target,limit=1] pos_z_n matches 0 \
        run function mypack:target_never_visited_nether
```

**When to reach for it.** Whenever an integer "0" is a valid value but also the uninitialized default. Either pick a real sentinel (`-2147483648`) at init, or check explicitly. Combine with a `tag=informed_user` gate so the warning message doesn't spam every tick.

**Source.** Manhunt (`not_in_nether.mcfunction`).

### Composite predicates with `all_of` / `any_of`

**What it is.** Combine multiple predicate conditions with `all_of` (AND) or `any_of` (OR). Each term is a full predicate condition object. Use this when the desired behavior requires multiple independent checks that would be awkward to chain inline in a command.

**Snippet.** (`predicates/boss_shoots.json` — fires at players only, and only 3% of ticks)
```json
{
  "condition": "minecraft:all_of",
  "terms": [
    {
      "condition": "minecraft:random_chance",
      "chance": 0.03
    },
    {
      "condition": "minecraft:entity_properties",
      "entity": "this",
      "predicate": {
        "targeted_entity": { "type": "minecraft:player" }
      }
    }
  ]
}
```

```mcfunction
# tick.mcfunction
execute as @e[tag=boss_mob] at @s if predicate mypack:boss_shoots run function mypack:shoot_fireball
```

**When to reach for it.** When you have 2+ independent conditions (random chance + entity type check, location + health threshold, etc.) that you want applied cleanly rather than nested in `execute if … if …` chains. Predicates are reusable across functions and loot tables.

**Source.** BattleTowers (`predicates/baller_test.json` — wither skeleton shoots at players with 3% chance).

---

## Game-state transitions

### Debounce major events with a countdown

**What it is.** "Boss died" or "structure destroyed" can flicker for a tick or two as entities unload. Wait a fixed delay before declaring the event final.

**Snippet.**
```mcfunction
# at the moment players enter the End:
scoreboard players set Temp dragon_check 10

# every second:
execute in minecraft:the_end as @a[predicate=mypack:in_end] \
        if score Temp dragon_check matches 1.. \
        run scoreboard players remove Temp dragon_check 1
execute if score Temp dragon_check matches 0 \
        unless entity @e[type=minecraft:ender_dragon] \
        run function mypack:dragon_dead
```

**When to reach for it.** Detecting boss kills, structure destruction, "all enemies cleared" — anything where the test for absence has a transient false positive.

**Source.** Manhunt (`hunt_second.mcfunction` dragon-death check).

### Idempotent end-state functions

**What it is.** Multiple win/lose conditions may fire on the same tick. Make `game_over` (and similar) safe to call repeatedly: clear state, broadcast once, set the disabled flag at the top.

**Snippet.**
```mcfunction
# game_over.mcfunction
execute if score Temp game_state matches 0 run return 0   # already over
scoreboard players set Temp game_state 0
# ... cleanup, announcement, reset ...
```

**When to reach for it.** Any function reachable from multiple guards (timer expired, all players dead, objective complete). Cheaper to make idempotent than to perfectly de-duplicate the callers.

**Source.** Manhunt's `game_over.mcfunction` is reachable from runner-death, hunter-death, and dragon-death paths.

---

## Teams & roles

### Minecraft teams + classification tags

**What it is.** Use `team add` for the *role* (visible color, friendly fire, name display) and tags for *classification within the role* (real player vs animal, alive vs dead).

**Snippet.**
```mcfunction
team add hunters
team modify hunters color blue
team add runners
team modify runners color red

# then use tags for sub-states
tag @s add died
execute as @e[team=runners,tag=!died,type=player] run function mypack:still_in_game
```

**When to reach for it.** Any role-based pack. Don't try to express the role *and* sub-states all in tags — teams give you visuals and selector ergonomics for free.

**Source.** Manhunt (`first_load.mcfunction` for team setup, `manhunt_died`/`manhunt_true_runner` tags layered on top).

### Live-counter pattern for win conditions

**What it is.** Maintain a fake-player counter (`players_left`) decremented on death. Combined with an "any live entity?" check, gives you robust win detection.

**Snippet.**
```mcfunction
# on death (called from a scoreboard-based death detector)
scoreboard players remove Temp players_left 1
gamemode spectator @s
tag @s add died

# every second
execute if score Temp players_left matches ..0 \
        unless entity @e[team=runners,tag=!died,type=player] \
        run function mypack:hunters_win
```

**When to reach for it.** Last-team-standing minigames, survival-style packs, anything with elimination.

**Source.** Manhunt (`runners_death.mcfunction` + `hunt_second.mcfunction`).

---

## Entity manipulation

### Projectile direction math via `execute store result entity`

**What it is.** Minecraft's `fireball` entity has a `power` array (`[X, Y, Z]` as doubles) that sets its direction and speed. You can compute a direction vector in fixed-point scoreboard math, then write it back to entity NBT via `execute store result entity`. This is how to make a fireball (or other projectile) aim at a specific point rather than flying in its default direction.

**Algorithm (5 steps):**
1. Summon the fireball at the caster's position (uses local `^ ^ ^` offsets).
2. Read caster's world position into `#casterX/Y/Z` scores (scaled × 1000 for integer precision).
3. Add height offset for the caster's eye level (wither skeleton is ~1.2 blocks → +1200).
4. Read the newly-spawned fireball's actual position into `#fireballX/Y/Z`.
5. Subtract caster from fireball → direction vector. Write each component back to `power[n]` scaled `double 0.0001` (converts ±1000 fixed-point back to ±0.1 double range).

**Snippet.**
```mcfunction
execute positioned as @s run summon minecraft:fireball ^ ^1 ^2 {Tags:["mypack_proj"]}

execute store result score #castX mypack_pos run data get entity @s Pos[0] 1000
execute store result score #castY mypack_pos run data get entity @s Pos[1] 1000
execute store result score #castZ mypack_pos run data get entity @s Pos[2] 1000
scoreboard players add #castY mypack_pos 1200   # eye-level offset for mob height

execute store result score #projX mypack_pos as @e[type=minecraft:fireball,tag=mypack_proj,limit=1] run data get entity @s Pos[0] 1000
execute store result score #projY mypack_pos as @e[type=minecraft:fireball,tag=mypack_proj,limit=1] run data get entity @s Pos[1] 1000
execute store result score #projZ mypack_pos as @e[type=minecraft:fireball,tag=mypack_proj,limit=1] run data get entity @s Pos[2] 1000

scoreboard players operation #projX mypack_pos -= #castX mypack_pos
scoreboard players operation #projY mypack_pos -= #castY mypack_pos
scoreboard players operation #projZ mypack_pos -= #castZ mypack_pos

execute store result entity @e[type=minecraft:fireball,tag=mypack_proj,limit=1] power[0] double 0.0001 run scoreboard players get #projX mypack_pos
execute store result entity @e[type=minecraft:fireball,tag=mypack_proj,limit=1] power[1] double 0.0001 run scoreboard players get #projY mypack_pos
execute store result entity @e[type=minecraft:fireball,tag=mypack_proj,limit=1] power[2] double 0.0001 run scoreboard players get #projZ mypack_pos

tag @e[tag=mypack_proj] remove mypack_proj
```

**When to reach for it.** Boss AI that shoots targeted projectiles, arrow-launching mechanics, any custom trajectory. The `double 0.0001` scale factor converts the 1000× fixed-point integers to appropriate double magnitudes for `power`. Remove the tag immediately after writing so the `limit=1` selectors don't accidentally target a lingering entity if the function is called again.

**Source.** BattleTowers (`fireball.mcfunction`).

---

## Initialization

### `load` vs `first_load` idempotence

**What it is.** `minecraft:load` runs every world reload — your `load.mcfunction` should only do things that are safe to repeat (creating objectives is, since Minecraft no-ops on existing ones). True first-time setup (initial team creation, default values, intro message) goes in a separate `first_load.mcfunction` gated by a "have I run before?" flag.

**Snippet.**
```mcfunction
# load.mcfunction
scoreboard objectives add init_flag dummy
scoreboard objectives add game_state dummy
# ... all other objective creation ...

# the dummy objective returns -2147483648..2147483647 if the score exists.
# matches -2147483647.. is a clean "score exists" test.
execute unless score Temp init_flag matches -2147483647.. run function mypack:first_load
```

```mcfunction
# first_load.mcfunction
team add hunters
team add runners
scoreboard players set Temp game_state 0
scoreboard players set Temp init_flag 1
tellraw @a {"text":"Pack installed!","color":"gold"}
```

**When to reach for it.** Any pack whose `load` function might do something unsafe to repeat (announcements, resetting game state, re-creating teams). The `matches -2147483647..` trick is the canonical "does this score exist?" test.

**Source.** Manhunt (`load.mcfunction` line 39, `first_load.mcfunction`).

### Data storage as a setup flag (alternative to scoreboard sentinel)

**What it is.** Instead of a scoreboard sentinel score, use a data storage compound to track whether first-time setup has run. Check with `execute unless data storage`, set with `data merge storage`.

**Snippet.**
```mcfunction
# load.mcfunction — runs every reload, safe to repeat
execute unless data storage mypack {Setup:1} run function mypack:setup

# setup.mcfunction — runs once
scoreboard objectives add mypack_pos dummy
# ... one-time initialization ...
data merge storage mypack {Setup:1}
```

**When to reach for it.** Packs with minimal scoreboard use where you don't want to create an objective just for a flag. Slightly cleaner than the `-2147483647..` sentinel trick. Both approaches are correct — the storage version requires no objective creation.

**Source.** BattleTowers (`load.mcfunction` + `setup.mcfunction`).

---

## Naming conventions

### Namespaced objectives & function-name prefixes

**What it is.** Prefix every objective with the pack namespace (`manhunt_dst`, not `dst`) — objectives are global across all datapacks and collisions silently corrupt other packs' state. Group functions by lifecycle prefix: `start_*`, `update_*`, `set_*`, `*_second`.

**When to reach for it.** Always for objectives. For functions, once the pack has more than ~5 functions — prefix discipline is the difference between a navigable pack and a mess at 30 files.

**Source.** Manhunt (every objective is `manhunt_*`; functions follow `start_game`, `update_compass_*`, `set_compass_*`, `hunt_second`, `lead_second`).

### `#`-prefixed fake player names for internal scores

**What it is.** A widely-used convention (not enforced by the engine) to signal "private/internal" fake player scores: `#casterX`, `#fireballX`, `#temp`. The `#` prefix means these won't be shown by `scoreboard players list` output in the same visual cluster as real player scores and makes their internal purpose immediately obvious to readers.

**When to reach for it.** Scratch-space scores used within a single function call that have no user-facing meaning. Keeps internal math visually separate from per-player state and global flags. Use regular fake-player names (no `#`) for globals intended to persist or be read by other functions.

**Source.** BattleTowers (`fireball.mcfunction` uses `#casterX`, `#casterY`, `#casterZ`, `#fireballX`, `#fireballY`, `#fireballZ`).

---

## Structure worldgen (Jigsaw)

Custom structures are built from five layers of JSON files plus binary `.nbt` structure templates. Each layer has a distinct role — getting one wrong breaks the whole pipeline silently.

### The Jigsaw pipeline overview

```
data/<ns>/worldgen/structure/<name>.json       ← declares the structure feature
data/<ns>/worldgen/structure_set/<name>.json   ← controls placement frequency
data/<ns>/worldgen/template_pool/<pool>.json   ← lists which .nbt pieces assemble
data/<ns>/structures/<name>.nbt                ← the actual block data
data/<ns>/worldgen/processor_list/<name>.json  ← block transforms applied at spawn
```

All five layers must be present and consistent for structures to appear.

### `worldgen/structure/` — the Jigsaw feature definition

**What it is.** Declares a jigsaw-type structure: which biomes it can appear in, which template pool starts it, how large it can grow, and how it adapts to terrain.

**Snippet.**
```json
{
  "type": "minecraft:jigsaw",
  "biomes": "#minecraft:is_overworld",
  "step": "surface_structures",
  "spawn_overrides": {},
  "terrain_adaptation": "beard_box",
  "start_pool": "battle_towers:overworld/start",
  "size": 7,
  "start_height": { "absolute": -1 },
  "project_start_to_heightmap": "WORLD_SURFACE",
  "max_distance_from_center": 116,
  "use_expansion_hack": false
}
```

Key fields:
- `biomes` — a biome tag (`#minecraft:is_overworld`, `#minecraft:is_nether`) or a specific biome. Controls which chunks can contain this structure.
- `size` — max number of jigsaw pieces assembled. More = taller/larger structures.
- `terrain_adaptation` — `beard_box` (smooth box carve below, good for overworld towers), `beard_thin` (lighter, for nether), `bury` (underground), `none`.
- `project_start_to_heightmap` — `WORLD_SURFACE` to snap the start height to terrain, `OCEAN_FLOOR`, etc.
- `start_height` — vertical offset from the heightmap reference. `{"absolute": -1}` plants the base 1 block below surface.

**When to reach for it.** Any datapack that adds structures to world generation. Create one `.json` per dimension variant (overworld.json, nether.json) to use dimension-specific biomes and terrain_adaptation.

**Source.** BattleTowers (`worldgen/structure/overworld.json`, `worldgen/structure/nether.json`).

### `worldgen/structure_set/` — placement frequency and distribution

**What it is.** Controls how often and where the structure appears in the world. `random_spread` is the most common type: it divides the world into cells (`spacing` × `spacing` chunks each) and places at most one structure per cell, with a minimum gap (`separation`) between them.

**Snippet.**
```json
{
  "structures": [{ "structure": "battle_towers:overworld", "weight": 1 }],
  "placement": {
    "type": "minecraft:random_spread",
    "salt": 56756869,
    "spacing": 24,
    "separation": 18
  }
}
```

Key points:
- `salt` — a unique integer per structure type. Different salts prevent all structure types from aligning in grid patterns across the world. Pick any large distinct integer.
- `spacing` — cell size in chunks. Larger = rarer.
- `separation` — minimum chunk distance between structures (must be < spacing).

**When to reach for it.** Every custom jigsaw structure needs a structure_set. Tune `spacing` for density: 6–12 for common, 20–30 for rare, 60+ for very rare. Always use a unique `salt` per pack — two packs with the same salt create overlapping grid patterns.

**Source.** BattleTowers (`worldgen/structure_set/overworld.json` — spacing 24, separation 18).

### Template pools — chaining pieces (start → floor → top)

**What it is.** Template pools define which `.nbt` pieces can appear at each stage of jigsaw assembly. Each pool has a `fallback` pool used when the assembler runs out of `size` budget. This creates a natural `start → floor (repeated) → top` tower pattern.

**Snippet.**
```
start pool:   one piece (the tower base)
floor pool:   weight 9 → floor.nbt, weight 1 → top.nbt  ← rarely caps early
              fallback → fallback pool
fallback pool: top.nbt  ← forces cap if size runs out
```

```json
{
  "name": "battle_towers:overworld/floor",
  "fallback": "battle_towers:overworld/fallback",
  "elements": [
    { "weight": 9, "element": { "location": "battle_towers:overworld/floor", "processors": "battle_towers:tower_flavor", "projection": "rigid", "element_type": "minecraft:single_pool_element" } },
    { "weight": 1, "element": { "location": "battle_towers:overworld/top",   "processors": "battle_towers:tower_flavor", "projection": "rigid", "element_type": "minecraft:single_pool_element" } }
  ]
}
```

Key fields:
- `fallback` — pool used when no more size budget remains. Always set this to a "terminator" pool (a cap/top piece) to prevent open-ended structures.
- `weight` — relative probability of picking each element. Total weight is the denominator.
- `processors` — which processor list transforms the blocks (use `"minecraft:empty"` for no transform).
- `projection` — `rigid` (absolute position, no terrain matching) vs `terrain_matching`.
- `element_type` — `minecraft:single_pool_element` for `.nbt` files.

**When to reach for it.** Any procedurally assembled structure: towers, dungeons, villages. The start → floor → cap pattern generalizes to "entry room → hallway → boss room" dungeon designs.

**Source.** BattleTowers (`worldgen/template_pool/overworld/{start,floor,fallback}.json`).

### `additions` pool — optional child pieces overlaid on parents

**What it is.** A separate `additions` pool adds extra child pieces *on top of* a parent piece (placed at the same jigsaw connection point). BattleTowers uses this to randomly attach a spawner structure to each floor from a weighted list.

**Snippet.** (excerpt from `additions.json`)
```json
{
  "name": "battle_towers:overworld/additions",
  "fallback": "minecraft:empty",
  "elements": [
    { "weight": 2, "element": { "location": "battle_towers:spawners/spawner_zombie",  "processors": "minecraft:empty", "projection": "rigid", "element_type": "minecraft:single_pool_element" } },
    { "weight": 2, "element": { "location": "battle_towers:spawners/spawner_spider",  "processors": "minecraft:empty", "projection": "rigid", "element_type": "minecraft:single_pool_element" } },
    { "weight": 1, "element": { "location": "battle_towers:spawners/spawner_cave_spider", "processors": "minecraft:empty", "projection": "rigid", "element_type": "minecraft:single_pool_element" } }
  ]
}
```

**When to reach for it.** When you want variation within a base piece — random spawner types, optional decoration rooms, loot-table variants on a floor — without duplicating the base `.nbt`. The additions pool is referenced via jigsaw block connections inside the parent `.nbt` file.

**Source.** BattleTowers (`worldgen/template_pool/overworld/additions.json`).

---

## Processor lists

Processor lists transform blocks in a structure `.nbt` at worldgen time — before the structure appears in the world. Live in `worldgen/processor_list/<name>.json`.

### Random block substitution for natural weathering

**What it is.** Use `minecraft:rule` processor with `random_block_match` as the input predicate to randomly replace a fraction of blocks with a weathered variant. Produces natural-looking aging without needing to manually paint variants in the structure editor.

**Snippet.** (`worldgen/processor_list/tower_flavor.json`)
```json
{
  "processors": [{
    "processor_type": "minecraft:rule",
    "rules": [
      {
        "location_predicate": { "predicate_type": "minecraft:always_true" },
        "input_predicate": {
          "predicate_type": "minecraft:random_block_match",
          "block": "minecraft:cobblestone",
          "probability": 0.2
        },
        "output_state": { "Name": "minecraft:mossy_cobblestone" }
      },
      {
        "location_predicate": {
          "predicate_type": "minecraft:random_block_match",
          "block": "minecraft:stone_slab",
          "probability": 0.1
        },
        "input_predicate": { "predicate_type": "minecraft:block_match", "block": "minecraft:stone_slab" },
        "output_state": { "Name": "minecraft:air" }
      }
    ]
  }]
}
```

Key points:
- Each `rule` has two predicates: `location_predicate` (where in the structure) and `input_predicate` (which block type). Both must match.
- `always_true` for `location_predicate` means "anywhere in the structure".
- Multiple rules in one processor list are applied in order.
- `probability` in `random_block_match` is per-block, not per-structure — 0.2 = 20% chance each qualifying block is replaced.

**When to reach for it.** Making ruins, aged buildings, overgrown structures. Keeps the source `.nbt` clean while producing varied outputs at worldgen. Also good for randomly removing decorative blocks (slabs → air) to create "damage".

**Source.** BattleTowers (`worldgen/processor_list/tower_flavor.json`).

### Barrier removal — editor markers cleared at worldgen

**What it is.** `minecraft:barrier` blocks are invisible to players in survival but visible in creative mode. Place them in a structure `.nbt` to mark regions, guide building, or fill void space during editing. Then remove them with a processor list so they don't appear in the actual world.

**Snippet.** (`worldgen/processor_list/remove_barriers.json`)
```json
{
  "processors": [{
    "processor_type": "minecraft:rule",
    "rules": [{
      "location_predicate": { "predicate_type": "minecraft:always_true" },
      "input_predicate": { "predicate_type": "minecraft:block_match", "block": "minecraft:barrier" },
      "output_state": { "Name": "minecraft:air" }
    }]
  }]
}
```

**When to reach for it.** During structure building in creative: place barriers to see bounding box extents, mark connection points, or fill awkward corners. Always pair with a `remove_barriers` processor on any pool that uses those structures. A common workflow: edit with barriers visible, save `.nbt`, assign remove_barriers processor, test in worldgen.

**Source.** BattleTowers (`worldgen/processor_list/remove_barriers.json`).

---

## Loot tables

### Referencing vanilla loot tables as entries

**What it is.** A loot table entry of `"type": "minecraft:loot_table"` with a vanilla `"name"` delegates to an existing loot table instead of defining items inline. Composes multiple vanilla tables with weights to produce varied chest contents without duplicating Mojang's data.

**Snippet.**
```json
{
  "pools": [{
    "rolls": 1,
    "entries": [
      { "type": "minecraft:loot_table", "name": "minecraft:chests/simple_dungeon",          "weight": 12 },
      { "type": "minecraft:loot_table", "name": "minecraft:chests/village/village_armorer",  "weight": 12 },
      { "type": "minecraft:loot_table", "name": "minecraft:chests/igloo_chest",              "weight": 10 },
      { "type": "minecraft:loot_table", "name": "battle_towers:treasure",                   "weight": 1  }
    ]
  }]
}
```

**When to reach for it.** Any chest that should feel like "varied loot from different sources". Far easier to maintain than copying individual items. Weights let you tune how often each source appears. Include your own custom table at low weight for the rare, signature drops.

**Source.** BattleTowers (`loot_tables/floor_chest.json`).

### Loot table nesting — reusable loot modules

**What it is.** Reference your own custom loot tables as entries inside other loot tables. Lets you define a loot module once (`stone_tools`) and include it in multiple contexts (`start_chest`) without duplicating the entries.

**Snippet.**
```json
{ "type": "minecraft:loot_table", "name": "battle_towers:stone_tools", "weight": 2, "quality": 3 }
```

**When to reach for it.** Any time the same set of items (a tool set, a food bundle, a currency set) could appear in multiple chests. Also useful for applying loot functions to a sub-table (enchant the whole module's contents).

**Source.** BattleTowers (`loot_tables/start_chest.json` referencing `battle_towers:stone_tools`).

### `quality` field — luck-scaling entry weights

**What it is.** The `quality` field on a loot table entry scales its effective weight by the player's luck: `effective_weight = weight + quality * luck`. Higher-quality entries become relatively more common when a player has good luck (e.g., from Luck of the Sea, Hero of the Village, or commands).

**Snippet.**
```json
{ "type": "minecraft:loot_table", "name": "battle_towers:treasure", "weight": 1, "quality": 8 }
```

**When to reach for it.** Rare premium items in chests. Set high `quality` (6–10) on rare items so luck genuinely improves the odds of finding good loot. Leave `quality` at 0 (or omit it) for common filler items.

**Source.** BattleTowers (`loot_tables/top_chest.json` — treasure has quality 8, dungeon loot has quality 2).

### Location-conditional items in a shared loot table

**What it is.** A single loot table can serve multiple contexts by adding `"conditions"` to individual entries that filter by dimension. Items with failing conditions are skipped entirely, not replaced — effectively making the entry dimension-exclusive.

**Snippet.** (from `treasure.json` — one table serves both overworld and nether towers)
```json
{
  "type": "minecraft:item",
  "name": "minecraft:emerald",
  "weight": 3,
  "conditions": [{ "condition": "minecraft:location_check", "predicate": { "dimension": "minecraft:overworld" } }]
},
{
  "type": "minecraft:item",
  "name": "minecraft:blaze_rod",
  "weight": 3,
  "conditions": [{ "condition": "minecraft:location_check", "predicate": { "dimension": "minecraft:the_nether" } }]
}
```

**When to reach for it.** When structure variants in different dimensions share most of their loot but need a few dimension-appropriate unique items. Keeps you from maintaining two near-identical loot tables.

**Source.** BattleTowers (`loot_tables/treasure.json`).

### `random_sequence` — deterministic chest loot per seed

**What it is.** Adding `"random_sequence": "mypack:name"` to a loot table makes it use a seeded RNG tied to the world seed and the chest's position. The same chest will always have the same loot on a given seed — making the pack seed-discoverable and reproducible.

**Snippet.**
```json
{
  "pools": [{ ... }],
  "random_sequence": "battle_towers:treasure"
}
```

**When to reach for it.** Loot tables that should feel "baked into the world" rather than random. Omit for loot that should vary on every chest open. Seed-dependent loot is expected by speedrunners and seed explorers — include it in treasure chests, omit it from renewable loot.

**Source.** BattleTowers (`loot_tables/treasure.json`).

### `enchant_with_levels` with a conditional

**What it is.** The `minecraft:enchant_with_levels` loot function applies a random enchantment at a level range. Wrap it in a `conditions` array with `minecraft:random_chance` to make enchantment probabilistic — items are sometimes enchanted, sometimes plain.

**Snippet.**
```json
{
  "function": "minecraft:enchant_with_levels",
  "levels": { "min": 10, "max": 20 },
  "treasure": true,
  "conditions": [{ "condition": "minecraft:random_chance", "chance": 0.8 }]
}
```

- `levels` — enchantment power range (higher = better enchants, not just higher level).
- `treasure` — `true` allows treasure enchantments (Mending, Infinity, etc.).
- `chance` 0.8 = 80% of items get enchanted, 20% remain plain.

**When to reach for it.** Weapon/tool drops that should feel like dungeon loot — sometimes enchanted, sometimes not. The `levels` range controls quality; the `chance` condition controls frequency.

**Source.** BattleTowers (`loot_tables/stone_tools.json`).

### Mob drop tables as loot entries

**What it is.** Use `"type": "minecraft:loot_table"` with a path like `"minecraft:entities/zombie"` to include a mob's actual drop table in a chest. The chest will contain whatever that mob would drop (rotten flesh, carrots, etc.), respecting looting enchantment level from functions.

**Snippet.**
```json
{
  "type": "minecraft:loot_table",
  "name": "minecraft:entities/zombie",
  "weight": 5,
  "quality": 1,
  "functions": [{ "function": "minecraft:set_count", "count": { "min": 1, "max": 5 } }]
}
```

**When to reach for it.** "Creature cache" chests in dungeons — a chest that contains what the local monsters would have dropped. Also useful for modding mob drop tables by creating a wrapper loot table that references the vanilla one plus extra entries.

**Source.** BattleTowers (`loot_tables/start_chest.json`).

### Count distributions — uniform, binomial, min/max

**What it is.** Three ways to express item count ranges in loot tables, each with different statistical shapes.

**Snippet.**
```json
{ "function": "minecraft:set_count", "count": { "min": 1, "max": 10 } }          // uniform (flat)
{ "function": "minecraft:set_count", "count": { "type": "minecraft:uniform", "min": 1, "max": 8 } }   // explicit uniform
{ "function": "minecraft:set_count", "count": { "type": "minecraft:binomial", "n": 10, "p": 0.5 } }   // bell curve
```

- **Uniform** (`min`/`max` shorthand or `type: uniform`): equal probability across the range. Standard, boring, predictable.
- **Binomial** (`n` trials, `p` probability per trial): bell-curve distribution centered around `n*p`. Feels more natural — usually gives mid-range counts, rarely max or min.

**When to reach for it.** Use uniform for resources where any amount is equally fine (arrows, sticks). Use binomial when the "typical" count matters — e.g., 10 trials at 0.5 probability gives a peak around 5, making 5 cobblestone the most common outcome with rare high/low outliers.

**Source.** BattleTowers (`loot_tables/treasure.json` uses `minecraft:uniform`; `loot_tables/start_chest.json` uses `minecraft:binomial`).
