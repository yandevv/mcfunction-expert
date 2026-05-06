#!/usr/bin/env python3
"""
Scaffold a canonical Minecraft datapack project tree.

Writes the same boilerplate the model would otherwise hand-emit on every
scaffolding task (pack.mcmeta, beet.json, load/tick functions + tags, optional
Bolt entry point) so the model can spend its tokens on the actual feature.

Templates live in assets/templates/ next to the skill. The script copies them
and substitutes {{NAME}}, {{NAMESPACE}}, {{DESCRIPTION}}, {{PACK_FORMAT}},
{{MC_VERSION}}.

The pack.mcmeta is written into `src/` (not the project root) so beet's
file-copy pipeline picks it up. The beet.json templates intentionally OMIT
the `"minecraft"` field — when that field is present, beet auto-generates
its own pack.mcmeta on every build and silently overwrites the hand-written
one. If you want beet to manage versioning instead, add `"minecraft"` back
and delete src/pack.mcmeta.

Usage:
    python scripts/scaffold_pack.py \\
        --name my-pack --namespace mypack \\
        --mc-version 1.21.4 [--with-bolt] [--out ./my-pack] \\
        [--pack-format N]   # override the version-table lookup
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# pack_format per https://minecraft.wiki/w/Pack_format, stored as
# (major, minor) tuples. Pre-1.21.9 versions used a flat integer; 1.21.9+
# introduced minor versions (e.g. 88.0, 94.1, 101.2). The pack.mcmeta
# `pack_format` field always takes only the major; min_format/max_format
# carry the minor in tuple form. Newer entries ship rapidly — if a target
# version isn't in the table, pass --pack-format MAJOR[.MINOR] to override.
PACK_FORMATS: dict[str, tuple[int, int]] = {
    "1.20.5": (41, 0), "1.20.6": (41, 0),
    "1.21":   (48, 0), "1.21.1": (48, 0),
    "1.21.2": (57, 0), "1.21.3": (57, 0),
    "1.21.4": (61, 0),
    "1.21.5": (71, 0),
    "1.21.6": (80, 0),
    "1.21.7": (81, 0), "1.21.8": (81, 0),
    "1.21.9": (88, 0), "1.21.10": (88, 0),
    "1.21.11": (94, 1),
    "26.1": (101, 1), "26.1.1": (101, 1), "26.1.2": (101, 1),
}


def parse_pack_format(spec: str) -> tuple[int, int]:
    """Parse a --pack-format override like '94' or '94.1' → (94, 0) or (94, 1)."""
    if "." in spec:
        major, minor = spec.split(".", 1)
        return (int(major), int(minor))
    return (int(spec), 0)

SKILL_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = SKILL_ROOT / "assets" / "templates"


def render(template_name: str, subs: dict[str, str]) -> str:
    text = (TEMPLATES / template_name).read_text(encoding="utf-8")
    for key, value in subs.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold a Minecraft datapack project.")
    parser.add_argument("--name", required=True, help="Project name (used in beet.json, pack.mcmeta).")
    parser.add_argument("--namespace", required=True, help="Datapack namespace (lowercase, no spaces).")
    parser.add_argument("--mc-version", required=True, help="Target Minecraft version, e.g. 1.21.4.")
    parser.add_argument("--description", default=None, help="Pack description (defaults to name).")
    parser.add_argument("--with-bolt", action="store_true", help="Include Bolt setup (require + pipeline + Bolt-syntax main.mcfunction).")
    parser.add_argument("--pack-format", default=None, help="Override the pack_format from the version table. Accepts MAJOR or MAJOR.MINOR (e.g. 94 or 94.1).")
    parser.add_argument("--out", default=None, help="Output directory (defaults to ./<name>).")
    args = parser.parse_args()

    if args.pack_format is not None:
        pf = parse_pack_format(args.pack_format)
    else:
        pf = PACK_FORMATS.get(args.mc_version)
        if pf is None:
            sys.stderr.write(
                f"error: unknown Minecraft version {args.mc_version!r}. "
                f"Known: {', '.join(sorted(PACK_FORMATS))}. "
                f"Pass --pack-format MAJOR[.MINOR] to bypass the table.\n"
            )
            return 2
    pack_format_major, pack_format_minor = pf

    out = Path(args.out or args.name).resolve()
    if out.exists() and any(out.iterdir()):
        sys.stderr.write(f"error: output directory {out} exists and is not empty\n")
        return 2

    description = args.description or args.name
    subs = {
        "NAME": args.name,
        "NAMESPACE": args.namespace,
        "DESCRIPTION": description,
        "PACK_FORMAT": str(pack_format_major),
        "PACK_FORMAT_MINOR": str(pack_format_minor),
        "MC_VERSION": args.mc_version,
    }

    # pack.mcmeta lives in src/ so beet's load:["src"] picks it up. Putting it
    # at the project root would mean beet ignores it and either auto-generates
    # one (if "minecraft" is in beet.json) or omits it entirely.
    write(out / "src" / "pack.mcmeta", render("pack.mcmeta", subs))

    beet_template = "beet.bolt.json" if args.with_bolt else "beet.raw.json"
    write(out / "beet.json", render(beet_template, subs))

    fn_dir = out / "src" / "data" / args.namespace / "function"
    write(fn_dir / "load.mcfunction", render("load.mcfunction", subs))
    write(fn_dir / "tick.mcfunction", render("tick.mcfunction", subs))

    tag_dir = out / "src" / "data" / "minecraft" / "tags" / "function"
    write(tag_dir / "load.json", render("load.json", subs))
    write(tag_dir / "tick.json", render("tick.json", subs))

    if args.with_bolt:
        # Bolt-syntax functions go in function/ with .mcfunction extension.
        # The mecha+bolt pipeline parses Bolt syntax inside .mcfunction.
        # Files with .bolt extension under function/ are silently ignored —
        # those belong in module/ as importable Python modules.
        write(fn_dir / "main.mcfunction", render("main.mcfunction", subs))

    pf_display = f"{pack_format_major}.{pack_format_minor}" if pack_format_minor else str(pack_format_major)
    print(f"Scaffolded {args.name} ({args.mc_version}, pack_format {pf_display}) at {out}")
    print("Next steps:")
    if args.with_bolt:
        print("  uv tool install beet && uv add bolt mecha")
    else:
        print("  uv tool install beet   # optional, for `beet build`")
    print(f"  cd {out} && beet build")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
