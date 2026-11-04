#!/usr/bin/env python3
"""Insert the chapter illustrations listed in docs/art-placement.md.

    python3 scripts/place_art.py          # insert any figure not yet in its chapter
    python3 scripts/place_art.py --check  # only report; exit 1 if an anchor is missing

Each table row names a chapter, an image, the opening words of the block the
figure follows, and a placement. A figure already present in its chapter is
left alone, so the script is safe to re-run. Alt text comes from the SVG's
<title>. Standard library only.
"""
from __future__ import annotations

import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "docs" / "art-placement.md"
ROW = re.compile(r'^\|\s*(\S+\.md)\s*\|\s*(images/\S+\.svg)\s*\|\s*"(.+)"\s*\|\s*([\w-]+)\s*\|')


def norm(s: str) -> str:
    s = re.sub(r"[*_`\"“”‘’']", "", s)
    return re.sub(r"\s+", " ", s).strip().lower()


def title_of(svg: Path) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", svg.read_text(encoding="utf-8"), re.S)
    return html.unescape(m.group(1)).strip() if m else ""


def place(lines: list[str], anchor: str) -> int | None:
    """Index after the block whose first line starts with anchor."""
    want = norm(anchor)
    for i, line in enumerate(lines):
        starts_block = i == 0 or not lines[i - 1].strip() or lines[i - 1].startswith("#")
        if starts_block and line.strip() and norm(line).startswith(want):
            j = i + 1
            if not line.startswith("#"):
                while j < len(lines) and lines[j].strip():
                    j += 1
            return j
    return None


def main() -> None:
    check = "--check" in sys.argv
    rows = [m.groups() for m in map(ROW.match, MANIFEST.read_text(encoding="utf-8").splitlines()) if m]
    missing = 0
    for chapter, image, anchor, where in rows:
        path = ROOT / "chapters" / chapter
        lines = path.read_text(encoding="utf-8").split("\n")
        if any(f"../{image}" in ln for ln in lines):
            continue
        at = place(lines, anchor)
        if at is None:
            missing += 1
            print(f"MISSING anchor in {chapter}: {anchor!r} (for {image})")
            continue
        if check:
            print(f"would place {image} in {chapter} after {anchor!r}")
            continue
        alt = title_of(ROOT / image).replace("]", ")")
        fig = f'![{alt}](../{image} "{where}")'
        lines[at:at] = ["", fig] if at < len(lines) and not lines[at].strip() else ["", fig, ""]
        path.write_text("\n".join(lines), encoding="utf-8")
        print(f"placed {image} in {chapter}")
    sys.exit(1 if missing else 0)


if __name__ == "__main__":
    main()
