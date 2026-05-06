# Beet Reference

Beet is the Minecraft pack development toolkit. Install with `uv tool install beet` or `pip install beet`.
Docs: https://mcbeet.dev | Repo: https://github.com/mcbeet/beet

---

## pack_format table

| Minecraft version              | pack_format |
|--------------------------------|-------------|
| 1.13 – 1.14.4                  | 4           |
| 1.15 – 1.16.1                  | 5           |
| 1.16.2 – 1.16.5                | 6           |
| 1.17 – 1.17.1                  | 7           |
| 1.18 – 1.18.1                  | 8           |
| 1.18.2                         | 9           |
| 1.19 – 1.19.3                  | 10          |
| 1.19.4                         | 12          |
| 1.20 – 1.20.1                  | 15          |
| 1.20.2                         | 18          |
| 1.20.3 – 1.20.4                | 26          |
| 1.20.5 – 1.20.6                | 41          |
| 1.21 – 1.21.1                  | 48          |
| 1.21.2 – 1.21.3                | 57          |
| 1.21.4                         | 61          |
| 1.21.5                         | 71          |
| 1.21.6                         | 80          |
| 1.21.7 – 1.21.8                | 81          |
| 1.21.9 – 1.21.10               | 88.0        |
| 1.21.11 pre-release line       | 94.0        |
| 1.21.11                        | 94.1        |
| 26.1 – 26.1.2                  | 101.1       |
| 26.2 Snapshot 1 – Snapshot 2   | 101.2       |
| 26.2 Snapshot 3                | 102.0       |
| 26.2 Snapshot 4                | 103.0       |
| 26.2 Snapshot 5                | 104.0       |
| 26.2 Snapshot 6                | 105.0       |

> **Minor versions (1.21.9+).** Starting with 1.21.9, Mojang split `pack_format` into `<major>.<minor>` (e.g. `88.0`, `94.1`, `101.2`). In `pack.mcmeta`, the legacy `pack_format` field still takes the **major** integer only; the minor is carried in the tuple-form fields `min_format: [major, minor]` and `max_format: [major, minor]`. So for 1.21.11 (94.1) the file has `"pack_format": 94, "min_format": [94, 1], …`.

Beet can also auto-detect pack_format from a version string:
```json
{ "minecraft": "1.21.4" }
```

But see the warning in the next section before adding `"minecraft"` to a project that hand-writes its own `pack.mcmeta`.

---

## `pack.mcmeta` for 1.21+ compatibility

Starting in 1.20.2, Minecraft began rejecting `pack.mcmeta` files that declare an unsupported format range. By 1.21.6+, three separate fields are required if you want a single pack to load across the whole 1.21.x line:

```json
{
  "pack": {
    "pack_format": 61,
    "supported_formats": [61, 999],
    "min_format": [61, 0],
    "max_format": [999, 0],
    "description": "..."
  }
}
```

- `pack_format` — legacy single integer (the **major** only, even on 1.21.9+ where the format gained a minor). Satisfies pre-1.20.2 readers.
- `supported_formats` — **array** `[min, max]`. Required by 1.20.2+ when the declared format is in the 17–81 range. Some versions also accept the object form `{ "min_inclusive": …, "max_inclusive": … }`, but 1.21.11's error message instructs the array form, so prefer it.
- `min_format` / `max_format` — tuples `[major, minor]`. Required by 1.21.6+ whenever the supported range extends past format 81. From 1.21.9 onward this is the **only** field that carries the minor component (e.g. `[94, 1]` for 1.21.11). For pre-minor versions, set the minor to `0`.

Omitting any one of these on 1.21.6+ will register the pack in `/datapack list` but silently fail to load functions, advancements, or scoreboards. The metadata-rejection error appears in `latest.log` but never in chat — which is what makes it confusing.

### Beet silently overwrites hand-written `pack.mcmeta`

Compounding the above: if `beet.json` contains a `"minecraft"` field, **beet auto-generates its own `pack.mcmeta` on every build and overwrites whatever you placed at the project root or in `src/`**. The auto-generated file uses fields like `min_format: [88, 0], max_format: [88, 0]` pinned to a single sub-version, which excludes most other 1.21.x sub-versions.

Two safe configurations:

1. **Let beet manage metadata** — set `"minecraft": "1.21.4"` in `beet.json`, do not write a `pack.mcmeta` yourself. Accept that beet's pinning may not be 1.21.x-cross-compatible.
2. **Manage metadata yourself** — omit `"minecraft"` from `beet.json` entirely and place the file at `src/pack.mcmeta` (so beet's file-copy pipeline picks it up). The scaffolder (`scripts/scaffold_pack.py`) does this by default.

### Troubleshooting: `/function ns:load` returns "Unknown function" but the pack is enabled

A pack that registers in `/datapack list` but whose functions are unreachable in-game almost always means Minecraft rejected something at load time and only logged it. Check, in order:

1. **`pack.mcmeta` format fields.** Tail the log:
   ```bash
   grep -i -E "<your-namespace>|metadata|format" \
     "$HOME/Library/Application Support/minecraft/logs/latest.log" | tail -30
   ```
   If you see "missing mandatory fields min_format and max_format" or "requires a supported_formats field", apply the three-field template above.
2. **Invalid statistic-criterion objective names.** A single bad `scoreboard objectives add` line invalidates the entire function file at load time, with "Unknown function" as the only in-game symptom. The bare statistic IDs (`minecraft.fish_caught`, `minecraft.player_killed_entity`) are not valid criteria — the correct form is `minecraft.custom:minecraft.fish_caught`, `minecraft.killed:<entity_id>`, etc. Grep `latest.log` for "objective" or "criterion" to confirm.
3. **A `.bolt` file under `function/`.** Bolt scopes `.bolt` to `module/`; files with that extension under `function/` are loaded as Python modules and never written to the output. Rename to `.mcfunction` or move to `module/`. See `references/bolt-reference.md`.

---

## beet.json / beet.yaml full schema

```json
{
  "name": "my-pack",
  "description": "Pack description",
  "version": "1.0.0",
  "minecraft": "1.21.4",
  "output": "build",
  "require": [],
  "pipeline": ["my_plugin.my_function"],
  "meta": {
    "my_key": "my_value"
  },
  "data_pack": {
    "load": ["src"],
    "render": { "functions": "**" }
  },
  "resource_pack": {
    "load": ["assets"]
  }
}
```

YAML equivalent (often cleaner):
```yaml
name: my-pack
description: Pack description
minecraft: "1.21.4"
output: build

require:
  - bolt

pipeline:
  - bolt

data_pack:
  load:
    - src
```

Key fields:
- `require` — Python packages to import before pipeline runs (e.g. `"bolt"`)
- `pipeline` — list of plugin dotpaths to run (e.g. `"my_plugins.add_functions"`)
- `meta` — arbitrary key/value data accessible in plugins via `ctx.meta`
- `data_pack.load` — directories containing raw datapack files to merge in
- `minecraft` — version string; beet resolves pack_format automatically

---

## Beet Python API

### DataPack and Function

```python
from beet import DataPack, Function, FunctionTag

# Create a data pack and add a function
pack = DataPack()
pack["demo:hello"] = Function(["say hello", "say world"])

# Function with automatic tag registration
pack["demo:on_load"] = Function(["say loaded"], tags=["minecraft:load"])

# Access a function's lines
pack.functions["demo:hello"].lines.append("say bye")

# Merge two packs (tags are merged, not overwritten)
pack.merge(other_pack)

# Save to disk
with DataPack(path="build/my_datapack") as pack:
    pack["demo:hello"] = Function(["say hello"])
```

### Context (plugins)

```python
from beet import Context, Function, FunctionTag

def my_plugin(ctx: Context):
    # Access the data pack being built
    ctx.data["demo:hello"] = Function(["say hello"], tags=["minecraft:load"])

    # Access metadata from beet.json
    count = ctx.meta.get("greeting_count", 3)

    # Access the resource pack
    ctx.assets["minecraft:en_us"] = Language({"key": "value"})

    # Require another plugin (runs it if not already run)
    ctx.require(other_plugin)

    # Inject a service object
    service = ctx.inject(MyService)

    # Generator plugin: yield to run code after inner plugins finish
    yield
    # code here runs after all required plugins complete
```

### Common file types

```python
from beet import (
    Function,          # .mcfunction
    FunctionTag,       # tags/function/*.json
    Advancement,       # advancement/*.json
    LootTable,         # loot_table/*.json
    Predicate,         # predicate/*.json
    Recipe,            # recipe/*.json
    Structure,         # structure/*.nbt
    DimensionType,     # dimension_type/*.json
)
```

### FunctionTag merging

```python
from beet import FunctionTag

pack["minecraft:load"] = FunctionTag({"values": ["demo:load"]})
# Adding a second tag to the same key merges the values arrays
pack["minecraft:load"] = FunctionTag({"values": ["demo:other_load"]})
# Result: {"values": ["demo:load", "demo:other_load"]}
```

### Pattern matching

```python
# Match functions by glob pattern
matching = pack.functions.match("demo:*")
matching = pack.functions.match("demo:*", "!demo:internal/*")
```

---

## Writing plugins

### Simple plugin (no yield)

```python
# my_plugins.py
from beet import Context, Function

def add_greeting(ctx: Context):
    count = ctx.meta.get("count", 5)
    ctx.data["greeting:hello"] = Function(
        [f"say hello {i}" for i in range(count)],
        tags=["minecraft:load"]
    )
```

Add to `beet.json`:
```json
{
  "pipeline": ["my_plugins.add_greeting"],
  "meta": { "count": 3 }
}
```

### Generator plugin (with yield)

```python
def my_generator(ctx: Context):
    # Entry phase: runs before inner plugins
    ctx.meta["my_data"] = []

    yield  # wait for inner plugins to finish

    # Exit phase: runs after all required plugins complete
    for item in ctx.meta["my_data"]:
        ctx.data[f"ns:{item}"] = Function([f"say {item}"])
```

### Service injection

```python
from dataclasses import dataclass, field
from beet import Context

@dataclass
class Registry:
    ctx: Context
    entries: list = field(default_factory=list)

    def __post_init__(self):
        self.ctx.require(self._flush)

    def register(self, name: str):
        self.entries.append(name)

    def _flush(self, ctx: Context):
        yield
        for name in self.entries:
            ctx.data[f"ns:{name}"] = Function([f"say {name}"])

def my_plugin(ctx: Context):
    reg = ctx.inject(Registry)
    reg.register("foo")
    reg.register("bar")
```

---

## CLI commands

```bash
beet build                    # build once
beet watch                    # watch + rebuild on change
beet build --link "My World"  # build + symlink into Minecraft saves
beet cache --clear            # clear build cache
beet -p path/to/beet.json build  # specify project file
```

---

## Project layout (recommended)

```
my-pack/
├── beet.json          # or beet.yaml
├── src/               # raw datapack files (beet merges these)
│   └── data/
│       └── mynamespace/
│           └── function/
│               └── load.mcfunction
├── my_plugins.py      # Python plugins (if any)
└── build/             # output (gitignore this)
```
