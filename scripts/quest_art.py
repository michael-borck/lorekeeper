#!/usr/bin/env python3
"""Generate and process Quest-mode art with limn.

Follows the SwipeVerse pixel recipe: juggernautXL + the pixel-art-xl LoRA,
style front-loaded, a strong anti-photo negative and fixed seeds so runs are
reproducible.

  python3 scripts/quest_art.py generate            # all jobs, 2 candidates each
  python3 scripts/quest_art.py generate --name keeper --candidates 4
  python3 scripts/quest_art.py pick keeper 2       # choose candidate 2
  python3 scripts/quest_art.py process             # picked PNG -> player/art/quest/*.webp

Candidates and picks live in art/ (gitignored). Only processed WebP ships.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DROPS = ROOT / "art" / "drops"
CANDIDATES = ROOT / "art" / "candidates"
OUT = ROOT / "player" / "art" / "quest"

MODEL = "juggernautXL_v9"
LORA = "<lora:pixel-art-xl:1> "
SCENE_SIZE = "1216x832"
PORTRAIT_SIZE = "1024x1024"
NEGATIVE = (
    "photo, photorealistic, 3d render, bokeh, depth of field, film grain, "
    "cinematic lighting, blurry, soft focus, text, letters, watermark, "
    "signature, border, frame, UI elements"
)
PALETTE = "warm torchlight gold and parchment with deep indigo shadows"
PORTRAIT = (
    "16-bit pixel art RPG dialogue portrait, chunky pixels, limited color "
    "palette: head and shoulders of {desc}, facing the viewer, plain dark "
    "indigo background, " + PALETTE + ", game art"
)
SCENE = (
    "16-bit pixel art game scene, chunky pixels, limited color palette: "
    "{desc}, " + PALETTE + ", game art"
)

JOBS = {
    # Narrators, one per pack category. Width shipped: 384px.
    "keeper": (PORTRAIT, "an old bearded archivist sage in a hooded robe holding a glowing lantern, round spectacles, a large leather book", PORTRAIT_SIZE),
    "sentinel": (PORTRAIT, "a stern young guard captain in a hooded cloak and light armour holding a round shield and a ring of iron keys", PORTRAIT_SIZE),
    "oracle": (PORTRAIT, "a friendly brass clockwork automaton scholar with glowing cyan eyes holding a small open book", PORTRAIT_SIZE),
    "courier": (PORTRAIT, "a cheerful messenger with a feathered cap and a leather satchel, a carrier pigeon perched on her shoulder", PORTRAIT_SIZE),
    "artificer": (PORTRAIT, "a young tinkerer with brass goggles pushed up on her forehead holding a small wrench, tiny sparks", PORTRAIT_SIZE),
    "architect": (PORTRAIT, "a calm architect in a dark coat holding a rolled blueprint and a brass compass", PORTRAIT_SIZE),
    "mentor": (PORTRAIT, "a kind middle-aged teacher with a long scarf holding a scroll and a piece of chalk", PORTRAIT_SIZE),
    "cartographer": (PORTRAIT, "an adventurous cartographer in a wide-brimmed hat with a rolled map under one arm and a quill", PORTRAIT_SIZE),
    # Scenes.
    "hero": (SCENE, "a cozy tall stone library tower at dusk with glowing windows, a winding dirt path with lanterns leading from its door across green hills toward distant mountains and a small castle", SCENE_SIZE),
    "map": (SCENE, "a top-down parchment fantasy world map, a dotted winding trail connecting small villages, forests, rivers, mountains and a castle, compass rose in one corner", SCENE_SIZE),
}
WIDTHS = {"hero": 1216, "map": 1216}
BASE_SEED = 7300


def run_limn(prompt: str, size: str, seed: int, out: Path) -> bool:
    cmd = [
        "limn", "generate", LORA + prompt,
        "-m", MODEL, "-s", size, "--seed", str(seed),
        "--negative", NEGATIVE, "-o", str(out),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired:
        print("    FAILED: timed out")
        return False
    if result.returncode != 0 or not out.exists():
        print(f"    FAILED: {result.stderr.strip() or result.stdout.strip()}")
        return False
    return True


def cmd_generate(args: argparse.Namespace) -> int:
    names = [args.name] if args.name else list(JOBS)
    failures = 0
    for index, name in enumerate(names):
        template, desc, size = JOBS[name]
        prompt = template.format(desc=desc)
        seed_base = BASE_SEED + list(JOBS).index(name) * 10
        for k in range(1, args.candidates + 1):
            out = CANDIDATES / f"{name}-{k}.png"
            out.parent.mkdir(parents=True, exist_ok=True)
            if out.exists() and not args.force:
                print(f"  {name}-{k} exists, skipped")
                continue
            print(f"  {name}-{k} seed={seed_base + k} ...", flush=True)
            if not run_limn(prompt, size, seed_base + k, out):
                failures += 1
    return 1 if failures else 0


def cmd_pick(args: argparse.Namespace) -> int:
    src = CANDIDATES / f"{args.name}-{args.candidate}.png"
    if not src.exists():
        sys.exit(f"missing candidate: {src}")
    DROPS.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, DROPS / f"{args.name}.png")
    print(f"picked {src.name}")
    return 0


def cmd_process(args: argparse.Namespace) -> int:
    from PIL import Image

    OUT.mkdir(parents=True, exist_ok=True)
    count = 0
    for name in JOBS:
        src = DROPS / f"{name}.png"
        if not src.exists():
            print(f"  {name}: not picked yet")
            continue
        image = Image.open(src).convert("RGB")
        width = WIDTHS.get(name, 384)
        if image.width > width:
            height = round(image.height * width / image.width)
            image = image.resize((width, height), Image.LANCZOS)
        dest = OUT / f"{name}.webp"
        image.save(dest, "WEBP", quality=args.quality, method=6)
        count += 1
        print(f"  {dest.relative_to(ROOT)}  {dest.stat().st_size // 1024} KB")
    print(f"{count} image(s) processed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate")
    gen.add_argument("--name", choices=list(JOBS))
    gen.add_argument("--candidates", type=int, default=2)
    gen.add_argument("--force", action="store_true")
    gen.set_defaults(func=cmd_generate)
    pick = sub.add_parser("pick")
    pick.add_argument("name", choices=list(JOBS))
    pick.add_argument("candidate", type=int)
    pick.set_defaults(func=cmd_pick)
    process = sub.add_parser("process")
    process.add_argument("--quality", type=int, default=82)
    process.set_defaults(func=cmd_process)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
