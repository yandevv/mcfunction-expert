#!/usr/bin/env python3
"""
Scaffold a canonical Minecraft datapack project tree.

Writes the same boilerplate the model would otherwise hand-emit on every
scaffolding task (pack.mcmeta, beet.json, load/tick functions + tags, optional
Bolt entry point) so the model can spend its tokens on the actual feature.

Templates live in assets/templates/ next to the skill. The script copies them
and substitutes {{NAME}}, {{NAMESPACE}}, {{DESCRIPTION}}, {{PACK_FORMAT}},
{{MC_VERSION}}.

Usage:
    python scripts/scaffold_pack.py \\
        --name my-pack --namespace mypack \\
        --mc-version 1.21.4 [--with-bolt] [--out ./my-pack]
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

PACK_FORMATS = {
    "1.20.5": 41, "1.20.6": 41,
    "1.21": 48, "1.21.1": 48,
    "1.21.2": 57, "1.21.3": 57,
    "1.21.4": 61,
    "1.21.5": 71,
}

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
    parser.add_argument("--with-bolt", action="store_true", help="Include Bolt setup (require + pipeline + .bolt entry).")
    parser.add_argument("--out", default=None, help="Output directory (defaults to ./<name>).")
    args = parser.parse_args()

    pack_format = PACK_FORMATS.get(args.mc_version)
    if pack_format is None:
        sys.stderr.write(
            f"error: unknown Minecraft version {args.mc_version!r}. "
            f"Known: {', '.join(sorted(PACK_FORMATS))}\n"
        )
        return 2

    out = Path(args.out or args.name).resolve()
    if out.exists() and any(out.iterdir()):
        sys.stderr.write(f"error: output directory {out} exists and is not empty\n")
        return 2

    description = args.description or args.name
    subs = {
        "NAME": args.name,
        "NAMESPACE": args.namespace,
        "DESCRIPTION": description,
        "PACK_FORMAT": str(pack_format),
        "MC_VERSION": args.mc_version,
    }

    write(out / "pack.mcmeta", render("pack.mcmeta", subs))

    beet_template = "beet.bolt.json" if args.with_bolt else "beet.raw.json"
    write(out / "beet.json", render(beet_template, subs))

    fn_dir = out / "src" / "data" / args.namespace / "function"
    write(fn_dir / "load.mcfunction", render("load.mcfunction", subs))
    write(fn_dir / "tick.mcfunction", render("tick.mcfunction", subs))

    tag_dir = out / "src" / "data" / "minecraft" / "tags" / "function"
    write(tag_dir / "load.json", render("load.json", subs))
    write(tag_dir / "tick.json", render("tick.json", subs))

    if args.with_bolt:
        write(fn_dir / "main.bolt", render("main.bolt", subs))

    print(f"Scaffolded {args.name} ({args.mc_version}, pack_format {pack_format}) at {out}")
    print("Next steps:")
    if args.with_bolt:
        print("  uv tool install beet && uv add bolt")
    else:
        print("  uv tool install beet   # optional, for `beet build`")
    print(f"  cd {out} && beet build")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
