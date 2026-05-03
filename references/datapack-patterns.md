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

---

## Naming conventions

### Namespaced objectives & function-name prefixes

**What it is.** Prefix every objective with the pack namespace (`manhunt_dst`, not `dst`) — objectives are global across all datapacks and collisions silently corrupt other packs' state. Group functions by lifecycle prefix: `start_*`, `update_*`, `set_*`, `*_second`.

**When to reach for it.** Always for objectives. For functions, once the pack has more than ~5 functions — prefix discipline is the difference between a navigable pack and a mess at 30 files.

**Source.** Manhunt (every objective is `manhunt_*`; functions follow `start_game`, `update_compass_*`, `set_compass_*`, `hunt_second`, `lead_second`).
