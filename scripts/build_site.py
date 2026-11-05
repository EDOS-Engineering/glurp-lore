#!/usr/bin/env python3
"""Build the Glurp lore storybook site.

Renders the Markdown in this repository into static HTML under _site/
(or the directory given with --out). Standard library only.

    python3 scripts/build_site.py              # build into _site/
    python3 scripts/build_site.py --render-og  # also re-render the share cards
                                               # (site/og.png, site/og/*.png) and
                                               # PNG icons with a local headless
                                               # Chrome; commit the results

The Markdown converter covers only the constructs the lore uses:
headings, paragraphs, emphasis, strong, inline code, links, images,
fenced code, block quotes, lists, tables, definition lists and rules.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE_ASSETS = ROOT / "site"
BASE_URL = "https://lore.orkmeter.com/"
REPO_URL = "https://github.com/EDOS-Engineering/glurp-lore"
ORKMETER_URL = "https://orkmeter.com/"
PLUS_URL = "https://orkmeter.com/billing"
BOOK_TITLE = "The Lore and History of Glurp"
PUBLISHER = {"@type": "Organization", "name": "EDOS Engineering", "legalName": "EDOS LLC",
             "url": "https://github.com/EDOS-Engineering"}
COVER_ALT = (
    "Glurp, a green pixel-art ork in a purple hoodie, beside a three-ringed crystal ball, "
    "under the title The Lore and History of Glurp."
)

MARK_SVG = (
    '<svg viewBox="0 0 28 28" fill="none"><g class="r1"><path d="M24 14A10 10 0 1 1 14 4" '
    'stroke="#c4f58a" stroke-width="2.5" stroke-linecap="round"/></g><g class="r2"><path '
    'd="M21 14A7 7 0 1 1 14 7" stroke="#99cc70" stroke-width="2" stroke-linecap="round"/></g>'
    '<g class="r3"><path d="M18 14A4 4 0 1 1 14 10" stroke="#72a653" stroke-width="1.75" '
    'stroke-linecap="round"/></g></svg>'
)


# --------------------------------------------------------------------------
# Markdown: blocks
# --------------------------------------------------------------------------

@dataclass
class Block:
    kind: str  # h, p, img, pre, hr, quote, ul, ol, table, dl
    text: str = ""
    level: int = 0
    items: list = field(default_factory=list)
    # Glurp-isms said here: (anchor id, href of the entry on quotes.html).
    # Set by link_isms(); rendered as ids on the paragraph or block quote.
    isms: list = field(default_factory=list)


# An image on a line of its own is a figure. Its placement is the image title,
#   ![alt](../images/x.svg "spot-right")      (invisible on GitHub)
# or a pandoc-style class after it,
#   ![alt](../images/x.svg){.spot-right}
# One of PLACEMENTS; no placement means a full-width plate.
IMAGE_LINE = re.compile(
    r'^!\[([^\]]*)\]\(([^)\s]+)(?:\s+"([^"]*)")?\)(?:\{\.([\w-]+)\})?$'
)
PLACEMENTS = ("spot-right", "spot-left", "wide", "vignette")


def _starts_block(line: str) -> bool:
    return bool(
        line.startswith("```")
        or re.match(r"#{1,6}\s", line)
        or line.strip() == "---"
        or line.startswith(">")
        or re.match(r"[-*] ", line)
        or re.match(r"\d+\. ", line)
        or line.startswith("|")
    )


def parse(md: str) -> list[Block]:
    lines = md.replace("\r\n", "\n").split("\n")
    out: list[Block] = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line.startswith("```"):
            i += 1
            buf = []
            while i < n and not lines[i].startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            out.append(Block("pre", "\n".join(buf)))
            continue
        m = re.match(r"(#{1,6})\s+(.*)", line)
        if m:
            out.append(Block("h", m.group(2).strip(), level=len(m.group(1))))
            i += 1
            continue
        if line.strip() == "---":
            out.append(Block("hr"))
            i += 1
            continue
        if line.startswith("|") and i + 1 < n and re.match(r"^\|[\s\-:|]+\|$", lines[i + 1]):
            rows = []
            while i < n and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            out.append(Block("table", items=[rows[0]] + rows[2:]))
            continue
        if line.startswith(">"):
            buf = []
            while i < n and lines[i].startswith(">"):
                buf.append(re.sub(r"^>\s?", "", lines[i]))
                i += 1
            out.append(Block("quote", items=buf))
            continue
        if re.match(r"[-*] ", line) or re.match(r"\d+\. ", line):
            ordered = bool(re.match(r"\d+\. ", line))
            pat = r"\d+\. " if ordered else r"[-*] "
            items = []
            while i < n and re.match(pat, lines[i]):
                items.append(re.sub("^" + pat, "", lines[i]))
                i += 1
            out.append(Block("ol" if ordered else "ul", items=items))
            continue
        if i + 1 < n and lines[i + 1].startswith(": "):
            pairs = []
            while i + 1 < n and lines[i].strip() and lines[i + 1].startswith(": "):
                term = lines[i]
                defs = []
                i += 1
                while i < n and lines[i].startswith(": "):
                    defs.append(lines[i][2:])
                    i += 1
                pairs.append((term, defs))
                while i < n and not lines[i].strip():
                    i += 1
            out.append(Block("dl", items=pairs))
            continue
        img = IMAGE_LINE.match(line.strip())
        if img:
            place = img.group(4) or (img.group(3) or "").strip()
            if place and place not in PLACEMENTS:
                sys.exit(f"unknown image placement {place!r} in: {line.strip()}")
            out.append(Block("img", img.group(1), items=[img.group(2), place]))
            i += 1
            continue
        buf = [line]
        i += 1
        while i < n and lines[i].strip() and not _starts_block(lines[i]):
            buf.append(lines[i])
            i += 1
        out.append(Block("p", " ".join(s.strip() for s in buf)))
    return out


# --------------------------------------------------------------------------
# Markdown: inline
# --------------------------------------------------------------------------

LINK_MAP: dict[str, str] = {}


def map_href(href: str) -> str:
    if re.match(r"https?://", href):
        return href
    name = href.split("/")[-1]
    if "images/" in href:
        return "images/" + name
    if name in LINK_MAP:
        return LINK_MAP[name]
    if name == "LICENSE":
        return f"{REPO_URL}/blob/main/LICENSE"
    if name.endswith(".md"):
        return f"{REPO_URL}/blob/main/{href.lstrip('./')}"
    return href


def attr(value: str) -> str:
    return html.escape(value, quote=True)


def inline(text: str) -> str:
    codes: list[str] = []

    def keep_code(m: re.Match) -> str:
        codes.append(m.group(1))
        return f"\x00{len(codes) - 1}\x00"

    text = re.sub(r"`([^`]+)`", keep_code, text)
    text = html.escape(text, quote=False)
    text = re.sub(
        r"!\[([^\]]*)\]\(([^)]+)\)",
        lambda m: f'<img src="{attr(map_href(m.group(2)))}" alt="{attr(m.group(1))}">',
        text,
    )

    def link(m: re.Match) -> str:
        href = map_href(m.group(2))
        ext = ' rel="noopener"' if href.startswith("http") else ""
        return f'<a href="{attr(href)}"{ext}>{m.group(1)}</a>'

    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\w*])\*(?=\S)(.+?)(?<=\S)\*(?![\w*])", r"<em>\1</em>", text)
    text = re.sub(
        r"\x00(\d+)\x00", lambda m: f"<code>{html.escape(codes[int(m.group(1))])}</code>", text
    )
    return text


def plain(text: str) -> str:
    """Inline Markdown to plain text (for meta descriptions)."""
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"[*`]", "", text)
    return text


def describe(text: str, limit: int = 158) -> str:
    text = plain(text).strip()
    if len(text) <= limit:
        return text
    cut = text[: limit - 1].rsplit(" ", 1)[0].rstrip(",;:.")
    return cut + "…"


def render(blocks: list[Block], first_para_class: str | None = None) -> str:
    out = []
    lead_done = first_para_class is None
    for b in blocks:
        if b.kind == "h":
            out.append(f"<h{b.level}>{inline(b.text)}</h{b.level}>")
        elif b.kind == "p":
            cls = ""
            if not lead_done:
                cls = f' class="{first_para_class}"'
                lead_done = True
            out.append(f"<p{ism_id(b)}{cls}>{ism_extra(b)}{inline(b.text)}{ism_back(b)}</p>")
        elif b.kind == "img":
            place = b.items[1] if len(b.items) > 1 else ""
            out.append(figure(b, f"fig fig-{place}") if place else figure(b))
        elif b.kind == "pre":
            out.append(f"<pre><code>{html.escape(b.text)}</code></pre>")
        elif b.kind == "hr":
            out.append('<hr class="ornament">')
        elif b.kind == "quote":
            out.append(quote_html(b.items, b))
        elif b.kind in ("ul", "ol"):
            lis = "".join(f"<li>{inline(t)}</li>" for t in b.items)
            out.append(f"<{b.kind}>{lis}</{b.kind}>")
        elif b.kind == "table":
            head, *rows = b.items
            th = "".join(f'<th scope="col">{inline(c)}</th>' for c in head)
            body = "".join(
                "<tr>"
                + "".join(
                    (f'<th scope="row">{inline(c)}</th>' if j == 0 else f"<td>{inline(c)}</td>")
                    for j, c in enumerate(r)
                )
                + "</tr>"
                for r in rows
            )
            out.append(
                f'<div class="table-wrap"><table><thead><tr>{th}</tr></thead>'
                f"<tbody>{body}</tbody></table></div>"
            )
        elif b.kind == "dl":
            parts = []
            for term, defs in b.items:
                tid = "term-" + re.sub(r"[^a-z0-9]+", "-", plain(term).lower()).strip("-")
                parts.append(f'<div class="entry" id="{tid}"><dt>{inline(term)}</dt>')
                parts.extend(f"<dd>{inline(d)}</dd>" for d in defs)
                parts.append("</div>")
            out.append(f'<dl class="glossary">{"".join(parts)}</dl>')
    return "\n".join(out)


def ism_id(b: Block) -> str:
    return f' id="{b.isms[0][0]}"' if b.isms else ""


def ism_extra(b: Block) -> str:
    """A second Glurp-ism in the same block gets an empty anchor of its own."""
    return "".join(f'<span class="ism-anchor" id="{i}"></span>' for i, _ in b.isms[1:])


def ism_back(b: Block) -> str:
    """Back to the index; shown only on the passage the reader arrived at."""
    if not b.isms:
        return ""
    return (
        f' <a class="ism-back" href="{attr(b.isms[0][1])}">'
        f'<span aria-hidden="true">↩</span> Glurp-isms</a>'
    )


def quote_html(lines: list[str], b: Block | None = None) -> str:
    """Block quote; line breaks inside a quote are kept, as in verse."""
    paras, cur = [], []
    for ln in lines:
        if ln.strip():
            cur.append(ln.strip())
        elif cur:
            paras.append(cur)
            cur = []
    if cur:
        paras.append(cur)
    body = ""
    for p in paras:
        cite = None
        if len(p) > 1 and p[-1].startswith("—"):
            cite = p.pop()
        body += "<p>" + "<br>".join(inline(x) for x in p) + "</p>"
        if cite:
            body += f'<p class="attribution">{inline(cite)}</p>'
    if b is not None and b.isms:
        body = ism_extra(b) + body + f'<p class="ism-back-line">{ism_back(b).strip()}</p>'
        return f"<blockquote{ism_id(b)}>{body}</blockquote>"
    return f"<blockquote>{body}</blockquote>"


def figure(b: Block, cls: str = "plate", eager: bool = False) -> str:
    src = map_href(b.items[0])
    w, h = svg_size(src)
    loading = "" if eager else ' loading="lazy"'
    return (
        f'<figure class="{cls}"><img src="{attr(src)}" alt="{attr(b.text)}" '
        f'width="{w}" height="{h}"{loading} decoding="async"></figure>'
    )


def svg_size(src: str) -> tuple[int, int]:
    p = ROOT / src
    if p.exists():
        head = p.read_text(encoding="utf-8")[:400]
        m = re.search(r'width="(\d+)"\s+height="(\d+)"', head)
        if m:
            return int(m.group(1)), int(m.group(2))
    return 640, 384


# --------------------------------------------------------------------------
# Pages
# --------------------------------------------------------------------------

@dataclass
class Chapter:
    num: int
    slug: str
    title: str
    image: Block
    body: list[Block]
    description: str

    @property
    def href(self) -> str:
        return f"{self.slug}.html"


@dataclass
class Page:
    path: str  # output file name, e.g. "glossary.html"
    title: str  # <title>
    description: str
    main: str
    body_class: str = ""
    prev: tuple[str, str] | None = None  # (href, label)
    next: tuple[str, str] | None = None
    og_type: str = "article"
    sources: list[str] = field(default_factory=list)  # files whose history dates the page
    image: str = "og.png"  # share card under the site root
    image_alt: str = COVER_ALT
    image_url: str = ""  # absolute, versioned; set by attach_cards()
    jsonld: list[dict] = field(default_factory=list)


def load_chapters() -> list[Chapter]:
    chapters = []
    for path in sorted((ROOT / "chapters").glob("*.md")):
        blocks = parse(path.read_text(encoding="utf-8"))
        h1 = blocks.pop(0)
        assert h1.kind == "h" and h1.level == 1, path
        m = re.match(r"Chapter (\d+):\s*(.*)", h1.text)
        assert m, h1.text
        num, title = int(m.group(1)), m.group(2)
        image = blocks.pop(0)
        assert image.kind == "img", path
        # Drop the trailing rule + previous/next links; the site has its own.
        if blocks and blocks[-1].kind == "p" and re.fullmatch(
            r"(\s*·?\s*\[[^\]]+\]\([^)]+\))+", blocks[-1].text
        ):
            blocks.pop()
            if blocks and blocks[-1].kind == "hr":
                blocks.pop()
        first = next(b for b in blocks if b.kind == "p")
        chapters.append(
            Chapter(num, path.stem, title, image, blocks, describe(first.text))
        )
    return chapters


def pixel_num(n: int) -> str:
    return f'<span class="pixel-num" aria-hidden="true">{n:02d}</span>'


def chapter_page(ch: Chapter, chapters: list[Chapter], prev, nxt) -> Page:
    total = len(chapters)
    dots = "".join(
        f'<span class="{"on" if c.num <= ch.num else ""}"></span>' for c in chapters
    )
    main = f"""
<article class="book-page panel">
  {figure(ch.image, "plate plate-hero", eager=True)}
  <header class="chapter-head">
    <div class="chapter-badge">{pixel_num(ch.num)}<span class="badge-label">Chapter</span></div>
    <div>
      <p class="kicker">Chapter {ch.num} of {total}</p>
      <h1><span class="visually-hidden">Chapter {ch.num}: </span>{inline(ch.title)}</h1>
    </div>
  </header>
  <div class="prose">
{render(ch.body, first_para_class="lead")}
  </div>
  <div class="fin" aria-hidden="true"><span></span><span></span><span></span></div>
  <div class="progress" role="img" aria-label="Chapter {ch.num} of {total}">{dots}</div>
</article>"""
    return Page(
        path=ch.href,
        title=f"Chapter {ch.num}: {plain(ch.title)} · {BOOK_TITLE}",
        description=ch.description,
        main=main,
        body_class="page-chapter",
        prev=prev,
        next=nxt,
    )


def readme_sections(blocks: list[Block]) -> dict[str, list[Block]]:
    """Split README blocks into {heading: blocks}; '' holds the preamble."""
    sections: dict[str, list[Block]] = {"": []}
    cur = ""
    for b in blocks:
        if b.kind == "h" and b.level == 2:
            cur = b.text
            sections[cur] = []
        elif not (b.kind == "h" and b.level == 1):
            sections[cur].append(b)
    return sections


def cover_page(readme: dict[str, list[Block]], chapters: list[Chapter], tagline: str) -> Page:
    pre = readme[""]
    art = next(b for b in pre if b.kind == "img")
    subtitle = next(b for b in pre if b.kind == "p")
    quote = next(b for b in pre if b.kind == "quote")
    title_html = BOOK_TITLE.replace("Glurp", '<span class="glurp">Glurp</span>')
    first = chapters[0]
    main = f"""
<section class="cover panel" aria-labelledby="cover-title">
  <div class="cover-sky" aria-hidden="true"></div>
  {figure(art, "cover-art", eager=True)}
  <div class="cover-text">
    <p class="kicker">A storybook from the Ork Meter workshop</p>
    <h1 id="cover-title">{title_html}</h1>
    <p class="subtitle">{inline(subtitle.text)}</p>
    {quote_html(quote.items)}
    <div class="cover-actions">
      <a class="btn btn-primary" href="{first.href}" rel="next">Begin the tale <span aria-hidden="true">→</span></a>
      <a class="btn btn-quiet" href="contents.html">Table of contents</a>
    </div>
    <p class="cover-meta">{len(chapters)} chapters · a glossary · a book of quotes</p>
  </div>
</section>"""
    return Page(
        path="index.html",
        title=BOOK_TITLE,
        description=tagline,
        main=main,
        body_class="page-cover",
        next=(first.href, f"Chapter 1: {first.title}"),
        og_type="book",
    )


def contents_page(readme: dict[str, list[Block]], chapters: list[Chapter]) -> Page:
    cards = []
    for ch in chapters:
        # Each card has its own tableau (images/toc/, painted by make_art.py);
        # a chapter without one falls back to its opening plate.
        art = f"images/toc/{ch.slug}.svg"
        if not (ROOT / art).exists():
            art = map_href(ch.image.items[0])
        w, h = svg_size(art)
        cards.append(
            f"""<li><a class="toc-card panel" href="{ch.href}">
  <img src="{attr(art)}" alt="" width="{w}" height="{h}" decoding="async">
  <span class="toc-text">{pixel_num(ch.num)}<span class="toc-title"><span class="visually-hidden">Chapter {ch.num}: </span>{inline(ch.title)}</span></span>
</a></li>"""
        )
    also = readme.get("Contents", [])
    also_blocks = [b for b in also if b.kind != "ol"]
    sections = []
    for heading in ("Who is Glurp?", "The canonical summary", "The world, briefly"):
        if heading in readme:
            sections.append(
                f'<section class="panel aside-panel"><h2>{inline(heading)}</h2>'
                f'<div class="prose">{render(readme[heading])}</div></section>'
            )
    main = f"""
<header class="page-head">
  <p class="kicker">Table of contents</p>
  <h1>Contents</h1>
</header>
<ol class="toc">
{"".join(cards)}
</ol>
<section class="panel aside-panel also">
  <h2>Beyond the chapters</h2>
  <div class="prose">{render(also_blocks)}</div>
</section>
{"".join(sections)}"""
    return Page(
        path="contents.html",
        title=f"Contents · {BOOK_TITLE}",
        description="The table of contents: eight chapters of Glurp's story, plus a glossary of Orkish developer terms and a book of Glurp-isms.",
        main=main,
        body_class="page-contents",
        prev=("index.html", "Cover"),
        next=(chapters[0].href, f"Chapter 1: {chapters[0].title}"),
    )


def simple_page(src: str, out: str, kicker: str, body_class: str, prev, nxt, transform=None) -> Page:
    blocks = parse((ROOT / src).read_text(encoding="utf-8"))
    h1 = blocks.pop(0)
    intro = blocks.pop(0) if blocks and blocks[0].kind == "p" else None
    body = transform(blocks) if transform else render(blocks)
    intro_html = f'<p class="intro">{inline(intro.text)}</p>' if intro else ""
    main = f"""
<header class="page-head">
  <p class="kicker">{kicker}</p>
  <h1>{inline(h1.text)}</h1>
  {intro_html}
</header>
<div class="panel sheet">
{body}
</div>"""
    return Page(
        path=out,
        title=f"{plain(h1.text)} · {BOOK_TITLE}",
        description=describe(intro.text) if intro else plain(h1.text),
        main=main,
        body_class=body_class,
        prev=prev,
        next=nxt,
    )


# --------------------------------------------------------------------------
# Glurp-isms: the linked index
# --------------------------------------------------------------------------
#
# quotes.md is an index into the chapters. Each Glurp-ism is found in the
# prose and linked to the paragraph (or verse) where it is said. The anchor
# id comes from the words of the quote, so it survives prose edits around it.
#
# Finding a quote, in order of preference:
#   1. said: the quote, ignoring case, punctuation and emphasis, is in the
#      words a block puts in quotation marks, or in the block's plain text.
#      The earliest chapter wins (where it was first said).
#   2. near: the block sharing the longest run of words with the quote
#      (at least NEAR_MIN_WORDS) - the passage the saying grew out of.
#   3. unrecorded: no passage; listed unlinked at the end of the index.

NEAR_MIN_WORDS = 4


@dataclass
class Ism:
    quote: Block
    caption: Block | None
    anchor: str
    chapter: "Chapter | None" = None
    block: Block | None = None
    how: str = ""  # "said", "near" or "" (unrecorded)
    order: int = 0  # block position in the chapter


def words(text: str) -> list[str]:
    text = plain(text).lower().replace("\u2019", "'").replace("\u2018", "'")
    return re.findall(r"[a-z0-9]+(?:'[a-z0-9]+)*", text)


def spoken(text: str) -> str:
    """The words inside quotation marks or italics, joined in order."""
    parts = re.findall(r'"([^"]*)"|\u201c([^\u201d]*)\u201d|(?<![\w*])\*([^*]+)\*(?![\w*])', text)
    return " ".join(next(g for g in m if g) for m in parts if any(m))


def block_text(b: Block) -> str:
    return b.text if b.kind == "p" else " ".join(b.items)


def ism_anchor(text: str) -> str:
    return "said-" + "-".join(words(text)[:8]).replace("'", "")


def contains(hay: list[str], needle: list[str]) -> bool:
    n = len(needle)
    return any(hay[i : i + n] == needle for i in range(len(hay) - n + 1))


def longest_run(a: list[str], b: list[str]) -> int:
    best = 0
    prev = [0] * (len(b) + 1)
    for x in a:
        cur = [0] * (len(b) + 1)
        for j, y in enumerate(b):
            if x == y:
                cur[j + 1] = prev[j] + 1
                best = max(best, cur[j + 1])
        prev = cur
    return best


def load_isms(chapters: list[Chapter]) -> tuple[list[Block], list[Ism]]:
    """Parse quotes.md and find where each Glurp-ism is said in the chapters."""
    blocks = parse((ROOT / "quotes.md").read_text(encoding="utf-8"))
    isms: list[Ism] = []
    for i, b in enumerate(blocks):
        if b.kind == "quote":
            cap = blocks[i + 1] if i + 1 < len(blocks) and blocks[i + 1].kind == "p" else None
            isms.append(Ism(b, cap, ism_anchor(" ".join(b.items))))
    seen = [x.anchor for x in isms]
    dupes = {a for a in seen if seen.count(a) > 1}
    if dupes:
        sys.exit(f"two Glurp-isms share an anchor: {sorted(dupes)}")

    passages = [
        (ch, pos, b)
        for ch in chapters
        for pos, b in enumerate(ch.body)
        if b.kind in ("p", "quote")
    ]
    for ism in isms:
        q = words(" ".join(ism.quote.items))
        for ch, pos, b in passages:
            text = block_text(b)
            if contains(words(spoken(text)), q) or contains(words(text), q):
                ism.chapter, ism.block, ism.order, ism.how = ch, b, pos, "said"
                break
        else:
            best, hit = 0, None
            for ch, pos, b in passages:
                run = longest_run(q, words(block_text(b)))
                if run > best:
                    best, hit = run, (ch, pos, b)
            if hit and best >= min(NEAR_MIN_WORDS, len(q)):
                ism.chapter, ism.order, ism.block = hit
                ism.how = "near"
        if ism.block is not None:
            ism.block.isms.append((ism.anchor, f"quotes.html#{ism.anchor}"))
    return blocks, isms


def isms_transform(isms: list[Ism]):
    """The Glurp-isms page: an index by chapter, each entry linked to its passage."""

    def card(ism: Ism) -> str:
        cap = f"<figcaption>{inline(ism.caption.text)}</figcaption>" if ism.caption else ""
        where = ""
        if ism.chapter:
            ch = ism.chapter
            near = ' <span class="ism-near">· near enough</span>' if ism.how == "near" else ""
            where = (
                f'<a class="ism-where" href="{ch.href}#{ism.anchor}">'
                f"Ch. {ch.num} · {inline(ch.title)}{near}"
                f' <span aria-hidden="true">→</span></a>'
            )
        return (
            f'<figure class="speech" id="{ism.anchor}">{quote_html(ism.quote.items)}'
            f"{cap}{where}</figure>"
        )

    def transform(_blocks: list[Block]) -> str:
        groups = []
        found = sorted((x for x in isms if x.chapter), key=lambda x: (x.chapter.num, x.order))
        for ch in sorted({x.chapter.num: x.chapter for x in found}.values(), key=lambda c: c.num):
            cards = "".join(card(x) for x in found if x.chapter is ch)
            groups.append(
                f'<section class="ism-group" aria-labelledby="isms-{ch.slug}">'
                f'<h2 id="isms-{ch.slug}"><a href="{ch.href}">{pixel_num(ch.num)}'
                f'<span><span class="visually-hidden">Chapter {ch.num}: </span>{inline(ch.title)}</span></a></h2>'
                f'<div class="speech-grid">{cards}</div></section>'
            )
        lost = [x for x in isms if not x.chapter]
        if lost:
            groups.append(
                '<section class="ism-group ism-unrecorded" aria-labelledby="isms-unrecorded">'
                '<h2 id="isms-unrecorded"><span>Not yet in the book</span></h2>'
                '<p class="ism-note">Said somewhere, by someone, probably Glurp. '
                "The chapters have not caught up.</p>"
                f'<div class="speech-grid">{"".join(card(x) for x in lost)}</div></section>'
            )
        return "\n".join(groups)

    return transform


def tooltip_transform(blocks: list[Block]) -> str:
    out = []
    for b in blocks:
        if b.kind == "pre":
            out.append(f'<p class="tooltip-line">{html.escape(b.text)}</p>')
        else:
            out.append(render([b]))
    return '<div class="prose">' + "\n".join(out) + "</div>"


# --------------------------------------------------------------------------
# Layout
# --------------------------------------------------------------------------

def layout(page: Page) -> str:
    canonical = BASE_URL + ("" if page.path == "index.html" else page.path)
    head_links = ""
    if page.prev:
        head_links += f'<link rel="prev" href="{attr(page.prev[0])}">\n'
    if page.next:
        head_links += f'<link rel="next" href="{attr(page.next[0])}">\n'
    turn = ""
    if page.prev or page.next:
        prev = (
            f'<a class="turn turn-prev panel" href="{attr(page.prev[0])}" rel="prev">'
            f'<span class="turn-dir"><span aria-hidden="true">←</span> Previous page</span>'
            f'<span class="turn-title">{inline(page.prev[1])}</span></a>'
            if page.prev
            else "<span></span>"
        )
        nxt = (
            f'<a class="turn turn-next panel" href="{attr(page.next[0])}" rel="next">'
            f'<span class="turn-dir">Next page <span aria-hidden="true">→</span></span>'
            f'<span class="turn-title">{inline(page.next[1])}</span></a>'
            if page.next
            else "<span></span>"
        )
        hint = '<p class="turn-hint">Tip: use the ← and → arrow keys to turn the page.</p>'
        if page.body_class != "page-cover":
            turn = f'<nav class="page-turn" aria-label="Turn the page">{prev}{nxt}</nav>{hint}'

    def nav_link(href: str, label: str) -> str:
        cur = ' aria-current="page"' if href == page.path else ""
        return f'<a href="{href}"{cur}>{label}</a>'

    title = html.escape(page.title)
    desc = attr(page.description)
    jsonld = "".join(
        '<script type="application/ld+json">'
        + json.dumps(d, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
        + "</script>\n"
        for d in page.jsonld
    )
    return f"""<!doctype html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{canonical}">
<meta name="theme-color" content="#101412">
<meta name="color-scheme" content="dark">
<meta property="og:site_name" content="{BOOK_TITLE}">
<meta property="og:type" content="{page.og_type}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{canonical}">
<meta property="og:locale" content="en_GB">
<meta property="og:image" content="{attr(page.image_url)}">
<meta property="og:image:type" content="image/png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{attr(page.image_alt)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{desc}">
<meta name="twitter:image" content="{attr(page.image_url)}">
<meta name="twitter:image:alt" content="{attr(page.image_alt)}">
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<link rel="icon" href="icon-512.png" type="image/png" sizes="512x512">
<link rel="apple-touch-icon" href="apple-touch-icon.png" sizes="180x180">
{jsonld}<link rel="preload" href="fonts/silkscreen-400.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="fonts/inter-400.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="style.css">
{head_links}<script src="site.js" defer></script>
</head>
<body class="{page.body_class}">
<a class="skip" href="#main">Skip to the story</a>
<header class="site-header">
  <div class="bar">
    <a class="brand" href="index.html" aria-label="{BOOK_TITLE}, cover">
      <span class="mark" aria-hidden="true">{MARK_SVG}</span>
      <span class="brand-text"><span class="brand-name">Glurp Lore</span><span class="brand-sub">from Ork Meter</span></span>
    </a>
    <nav class="site-nav" aria-label="Book">
      {nav_link("contents.html", "Contents")}
      {nav_link("glossary.html", "Glossary")}
      {nav_link("quotes.html", "Quotes")}
    </nav>
    <a class="btn btn-primary btn-small header-cta" href="{ORKMETER_URL}">Count every token at Ork Meter</a>
  </div>
</header>
<main id="main" class="wrap">
{page.main}
{turn}
</main>
<footer class="site-footer">
  <div class="wrap footer-grid">
    <div class="footer-brand">
      <span class="mark mark-lg" aria-hidden="true">{MARK_SVG}</span>
      <p class="footer-pitch">Count every token, make every token count.</p>
    </div>
    <div class="footer-cta">
      <a class="btn btn-primary" href="{ORKMETER_URL}">Count every token at Ork Meter</a>
      <a class="btn btn-gold" href="{PLUS_URL}">Try Ork Meter Plus</a>
    </div>
    <nav class="footer-links" aria-label="More">
      <a href="contents.html">Contents</a>
      <a href="glossary.html">Glossary</a>
      <a href="quotes.html">Quotes</a>
      <a href="tooltip.html">Tooltip</a>
      <a href="{REPO_URL}" rel="noopener">Source on GitHub</a>
    </nav>
    <p class="legal">Text © 2026 EDOS LLC, licensed <a href="{REPO_URL}/blob/main/LICENSE" rel="noopener">CC BY 4.0</a>. Artwork, the three-ring mark and the Glurp character design © 2026 EDOS LLC, all rights reserved.</p>
  </div>
</footer>
</body>
</html>
"""


# --------------------------------------------------------------------------
# Open Graph image
# --------------------------------------------------------------------------

OG_HTML = """<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{{font-family:Silkscreen;font-weight:400;src:url({fonts}/silkscreen-400.woff2) format("woff2")}}
@font-face{{font-family:JBM;font-weight:500;src:url({fonts}/jetbrains-mono-500.woff2) format("woff2")}}
html,body{{margin:0;width:1200px;height:630px;overflow:hidden;background:#101412}}
.card{{position:absolute;inset:28px;background:#171d19;border:6px solid #0d120e;box-shadow:10px 10px 0 #0d120e;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:18px}}
img{{width:896px;height:384px;image-rendering:pixelated;border:6px solid #0d120e}}
h1{{margin:0;font:400 44px Silkscreen,monospace;color:#edf3e9;letter-spacing:-.04em}} h1 span{{color:#c4f58a}}
p{{position:absolute;right:30px;bottom:18px;margin:0;font:500 18px JBM,monospace;color:#a2afa4}}
</style></head><body><div class="card"><img src="{art}" alt=""><h1>The Lore and History of <span>Glurp</span></h1><p>lore.orkmeter.com</p></div></body></html>"""


def find_chrome() -> str | None:
    for c in (
        os.environ.get("CHROME"),
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
    ):
        if c and Path(c).exists():
            return c
    return None


def screenshot(chrome: str, page: Path, target: Path, width: int, height: int) -> None:
    subprocess.run(
        [
            chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
            "--force-device-scale-factor=1", f"--window-size={width},{height}",
            "--default-background-color=00000000",
            f"--screenshot={target}", page.as_uri(),
        ],
        check=True,
        capture_output=True,
    )


def render_og() -> None:
    chrome = find_chrome()
    if not chrome:
        sys.exit("render-og: no Chrome found (set CHROME=/path/to/chrome)")
    render_cards(chrome)
    render_icons(chrome)
    with tempfile.TemporaryDirectory() as tmp:
        card = Path(tmp) / "og.html"
        card.write_text(
            OG_HTML.format(
                fonts=(SITE_ASSETS / "fonts").as_uri(),
                art=(ROOT / "images" / "glurp-header.svg").as_uri(),
            ),
            encoding="utf-8",
        )
        target = SITE_ASSETS / "og.png"
        subprocess.run(
            [
                chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                "--force-device-scale-factor=1", "--window-size=1200,630",
                f"--screenshot={target}", card.as_uri(),
            ],
            check=True,
            capture_output=True,
        )
    print(f"wrote {target.relative_to(ROOT)}")


# --------------------------------------------------------------------------
# Share cards: one 1200x630 PNG per page
# --------------------------------------------------------------------------
#
# Link unfurlers (Discord, Slack, X, LinkedIn) only show raster og:images, so
# each page's card is painted from the existing pixel art with headless
# Chrome (--render-og) and committed under site/og/. The build only reads the
# PNGs: it versions their URLs with a content hash, and warns when a card's
# inputs (title, art, template) changed since it was last rendered.
# The cover keeps site/og.png.

OG_DIR = SITE_ASSETS / "og"
CARDS_JSON = OG_DIR / "cards.json"

CARD_HTML = """<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{{font-family:Silkscreen;font-weight:400;src:url({fonts}/silkscreen-400.woff2) format("woff2")}}
@font-face{{font-family:JBM;font-weight:500;src:url({fonts}/jetbrains-mono-500.woff2) format("woff2")}}
html,body{{margin:0;width:1200px;height:630px;overflow:hidden;background:#101412}}
.card{{position:absolute;inset:28px;background:#171d19;border:6px solid #0d120e;box-shadow:10px 10px 0 #0d120e;display:flex;align-items:center;gap:36px;padding:0 36px 12px}}
.frame{{flex:none;box-sizing:content-box;width:640px;height:384px;border:6px solid #0d120e;background:#1c241f;display:grid;place-items:center;overflow:hidden}}
.frame img{{display:block;image-rendering:pixelated}}
.text{{display:flex;flex-direction:column;gap:18px;min-width:0}}
.kicker{{margin:0;font:500 19px JBM,monospace;color:#c4f58a;letter-spacing:.06em;text-transform:uppercase}}
.num{{margin:0;font:400 88px/.8 Silkscreen,monospace;color:#c4f58a}}
h1{{margin:0;font:400 {size}px/1.12 Silkscreen,monospace;color:#edf3e9;letter-spacing:-.04em;overflow-wrap:break-word}}
h1 span{{color:#c4f58a}}
.line{{margin:0;font:500 19px/1.4 JBM,monospace;color:#c9d4c6}}
.grid{{display:grid;grid-template-columns:repeat(4,240px);gap:14px}}
.grid img{{display:block;width:240px;height:144px;image-rendering:pixelated;border:5px solid #0d120e}}
.stack{{flex-direction:column;justify-content:center;gap:22px;padding-bottom:44px}}
.stack .text{{align-items:center;text-align:center;gap:10px}}
.foot{{position:absolute;left:36px;right:30px;bottom:16px;display:flex;justify-content:space-between;font:500 17px JBM,monospace;color:#a2afa4}}
.foot b{{font:400 17px Silkscreen,monospace;color:#a2afa4;letter-spacing:-.02em}}
</style></head><body><div class="card{cls}">{art}<div class="text">{text}</div>
<div class="foot"><b>The Lore and History of Glurp</b><span>lore.orkmeter.com</span></div></div></body></html>"""

ICON_HTML = """<!doctype html><html><head><meta charset="utf-8"><style>
html,body{{margin:0;width:{s}px;height:{s}px;overflow:hidden;background:#101412}}
img{{position:absolute;inset:{pad}px;width:{inner}px;height:{inner}px}}
</style></head><body><img src="{mark}" alt=""></body></html>"""
ICONS = {"apple-touch-icon.png": 180, "icon-512.png": 512}


@dataclass
class Card:
    file: str  # under site/, e.g. "og/glossary.png"
    page: str  # the page it is for, e.g. "glossary.html"
    kicker: str
    title: str
    alt: str
    art: list[str]  # image paths under the repository root
    scale: float = 1.0  # for a single picture inside the frame
    num: int | None = None
    line: str = ""


def svg_title(src: str) -> str:
    m = re.search(r"<title[^>]*>([^<]*)</title>", (ROOT / src).read_text(encoding="utf-8"))
    return html.unescape(m.group(1)).strip() if m else ""


def md_title(src: str) -> str:
    return plain(parse((ROOT / src).read_text(encoding="utf-8"))[0].text)


def share_cards(chapters: list[Chapter]) -> list[Card]:
    cards = []
    for ch in chapters:
        art = f"images/toc/{ch.slug}.svg"
        if not (ROOT / art).exists():
            art = map_href(ch.image.items[0]).lstrip("./")
        cards.append(
            Card(
                f"og/{ch.slug}.png", ch.href, f"Chapter {ch.num} of {len(chapters)}",
                plain(ch.title),
                f"{svg_title(art)} Beside it: Chapter {ch.num}, {plain(ch.title)}.",
                [art], num=ch.num,
            )
        )
    toc = [f"images/toc/{ch.slug}.svg" for ch in chapters]
    cards.append(
        Card(
            "og/contents.png", "contents.html", "Table of contents", "Contents",
            "The eight chapter tableaus of Glurp's story in two rows, over the title Contents.",
            [t for t in toc if (ROOT / t).exists()][:8],
            line=f"{len(chapters)} chapters · a glossary · a book of quotes",
        )
    )
    for page, src, kicker, art, line in (
        ("glossary.html", "glossary.md", "Glossary", "images/poses/glurp-read.svg", ""),
        ("quotes.html", "quotes.md", "Quotes", "images/poses/glurp-shrug.svg",
         "“Oi, where'd all me tokens go?”"),
        ("tooltip.html", "tooltip.md", "From orkmeter.com", "images/poses/glurp-point.svg", ""),
    ):
        title = md_title(src)
        cards.append(
            Card(
                f"og/{Path(page).stem}.png", page, kicker, title,
                f"{svg_title(art)} Beside them: {title}.", [art], scale=1.5, line=line,
            )
        )
    return cards


def card_html(card: Card) -> str:
    def img(src: str, w: int, h: int, cls: str = "") -> str:
        return f'<img src="{(ROOT / src).as_uri()}" width="{w}" height="{h}" alt=""{cls}>'

    text = f'<p class="kicker">{html.escape(card.kicker)}</p>'
    if len(card.art) > 1:
        art = '<div class="grid">' + "".join(img(a, 240, 144) for a in card.art) + "</div>"
        cls, size = " stack", 64
    else:
        w, h = svg_size(card.art[0])
        art = f'<div class="frame">{img(card.art[0], round(w * card.scale), round(h * card.scale))}</div>'
        cls = ""
        longest = max(len(w) for w in card.title.split())
        size = 40 if longest <= 9 and len(card.title) <= 40 else 34
        if card.num is not None:
            text = f'<p class="num">{card.num:02d}</p>' + text
    title = html.escape(card.title).replace("Glurp", "<span>Glurp</span>")
    text += f"<h1 style=\"font-size:{size}px\">{title}</h1>"
    if card.line:
        text += f'<p class="line">{html.escape(card.line)}</p>'
    return CARD_HTML.format(fonts=(SITE_ASSETS / "fonts").as_uri(), cls=cls, art=art, text=text, size=size)


def card_inputs(card: Card) -> str:
    """A fingerprint of everything a card is painted from."""
    h = hashlib.sha256(CARD_HTML.encode())
    for part in (card.kicker, card.title, card.line, str(card.scale), str(card.num)):
        h.update(part.encode() + b"\0")
    for a in card.art:
        h.update((ROOT / a).read_bytes())
    return h.hexdigest()[:16]


def render_cards(chrome: str) -> None:
    cards = share_cards(load_chapters())
    OG_DIR.mkdir(exist_ok=True)
    record = {}
    with tempfile.TemporaryDirectory() as tmp:
        for card in cards:
            page = Path(tmp) / "card.html"
            page.write_text(card_html(card), encoding="utf-8")
            screenshot(chrome, page, SITE_ASSETS / card.file, 1200, 630)
            record[card.file] = {"page": card.page, "alt": card.alt, "inputs": card_inputs(card)}
            print(f"wrote site/{card.file}")
    for stale in set(p.name for p in OG_DIR.glob("*.png")) - {Path(c.file).name for c in cards}:
        (OG_DIR / stale).unlink()
    CARDS_JSON.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


def render_icons(chrome: str) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        for name, size in ICONS.items():
            pad = round(size * 0.14)
            page = Path(tmp) / "icon.html"
            page.write_text(
                ICON_HTML.format(s=size, pad=pad, inner=size - 2 * pad,
                                 mark=(SITE_ASSETS / "favicon.svg").as_uri()),
                encoding="utf-8",
            )
            screenshot(chrome, page, SITE_ASSETS / name, size, size)
            print(f"wrote site/{name}")


# --------------------------------------------------------------------------
# Build
# --------------------------------------------------------------------------

def build(out: Path) -> None:
    chapters = load_chapters()
    for ch in chapters:
        LINK_MAP[f"{ch.slug}.md"] = ch.href
    LINK_MAP.update(
        {
            "README.md": "contents.html",
            "glossary.md": "glossary.html",
            "quotes.md": "quotes.html",
            "tooltip.md": "tooltip.html",
        }
    )

    _, isms = load_isms(chapters)
    readme = readme_sections(parse((ROOT / "README.md").read_text(encoding="utf-8")))
    tooltip_blocks = parse((ROOT / "tooltip.md").read_text(encoding="utf-8"))
    canonical_tip = next(b.text for b in tooltip_blocks if b.kind == "pre")

    last = chapters[-1]
    pages = [
        cover_page(readme, chapters, canonical_tip),
        contents_page(readme, chapters),
    ]
    for idx, ch in enumerate(chapters):
        prev = (
            (chapters[idx - 1].href, f"Chapter {ch.num - 1}: {chapters[idx - 1].title}")
            if idx
            else ("contents.html", "Contents")
        )
        nxt = (
            (chapters[idx + 1].href, f"Chapter {ch.num + 1}: {chapters[idx + 1].title}")
            if idx + 1 < len(chapters)
            else ("glossary.html", "Glossary of Orkish Developer Terms")
        )
        pages.append(chapter_page(ch, chapters, prev, nxt))
    pages.append(
        simple_page(
            "glossary.md", "glossary.html", "Glossary", "page-glossary",
            (last.href, f"Chapter {last.num}: {last.title}"), ("quotes.html", "Glurp-isms"),
        )
    )
    pages.append(
        simple_page(
            "quotes.md", "quotes.html", "Quotes", "page-quotes",
            ("glossary.html", "Glossary of Orkish Developer Terms"), ("tooltip.html", "Tooltip"),
            transform=isms_transform(isms),
        )
    )
    pages.append(
        simple_page(
            "tooltip.md", "tooltip.html", "From orkmeter.com", "page-tooltip",
            ("quotes.html", "Glurp-isms"), ("index.html", "Back to the cover"),
            transform=tooltip_transform,
        )
    )

    for page, srcs in zip(pages, [["README.md", "tooltip.md"], ["README.md"]]):
        page.sources = srcs
    for page in pages:
        if not page.sources:
            src = f"chapters/{page.path[:-5]}.md"
            page.sources = [src if (ROOT / src).exists() else page.path[:-5] + ".md"]
    attach_cards(pages, chapters)
    add_structured_data(pages, chapters)

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    for page in pages:
        (out / page.path).write_text(layout(page), encoding="utf-8")
    shutil.copytree(ROOT / "images", out / "images")
    for item in SITE_ASSETS.iterdir():
        dest = out / item.name
        if item.is_dir():
            shutil.copytree(item, dest, ignore=shutil.ignore_patterns("cards.json"))
        else:
            shutil.copy2(item, dest)
    (out / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\n\nSitemap: {BASE_URL}sitemap.xml\n", encoding="utf-8"
    )
    (out / "sitemap.xml").write_text(sitemap(pages), encoding="utf-8")
    (out / "CNAME").write_text("lore.orkmeter.com\n", encoding="utf-8")
    (out / ".nojekyll").write_text("", encoding="utf-8")
    print(f"built {len(pages)} pages into {out}")
    linked = [x for x in isms if x.chapter]
    near = [x for x in linked if x.how == "near"]
    print(f"glurp-isms: {len(linked)} of {len(isms)} linked ({len(near)} near enough)")
    for x in near:
        print(f"  near enough, ch. {x.chapter.num}: {plain(' '.join(x.quote.items))}")
    for x in isms:
        if not x.chapter:
            print(f"  unrecorded: {plain(' '.join(x.quote.items))}")


def page_url(path: str) -> str:
    return BASE_URL + ("" if path == "index.html" else path)


def asset_url(name: str) -> str:
    """Absolute URL with a content-hash query, so unfurlers refetch on change."""
    digest = hashlib.sha256((SITE_ASSETS / name).read_bytes()).hexdigest()[:8]
    return f"{BASE_URL}{name}?v={digest}"


def attach_cards(pages: list[Page], chapters: list[Chapter]) -> None:
    record = json.loads(CARDS_JSON.read_text(encoding="utf-8")) if CARDS_JSON.exists() else {}
    cards = {c.page: c for c in share_cards(chapters)}
    for page in pages:
        card = cards.get(page.path)
        if card and (SITE_ASSETS / card.file).exists():
            page.image, page.image_alt = card.file, card.alt
            if record.get(card.file, {}).get("inputs") != card_inputs(card):
                print(f"warning: site/{card.file} is stale; run build_site.py --render-og")
        elif card:
            print(f"warning: no share card for {page.path}; run build_site.py --render-og")
        page.image_url = asset_url(page.image)


def add_structured_data(pages: list[Page], chapters: list[Chapter]) -> None:
    book_id = BASE_URL + "#book"
    by_path = {p.path: p for p in pages}
    cover = by_path["index.html"]

    def name(page: Page) -> str:
        return page.title.removesuffix(f" · {BOOK_TITLE}")

    def chapter_ld(ch: Chapter, full: bool) -> dict:
        page = by_path[ch.href]
        d = {"@context": "https://schema.org"} if full else {}
        d |= {"@type": "Chapter", "@id": page_url(ch.href) + "#chapter", "name": plain(ch.title),
             "position": ch.num, "url": page_url(ch.href)}
        if full:
            d.update({
                "headline": f"Chapter {ch.num}: {plain(ch.title)}",
                "description": page.description,
                "image": page.image_url,
                "inLanguage": "en-GB",
                "author": PUBLISHER,
                "isPartOf": {"@type": "Book", "@id": book_id, "name": BOOK_TITLE, "url": BASE_URL},
            })
        return d

    cover.jsonld.append({
        "@context": "https://schema.org",
        "@type": "Book",
        "@id": book_id,
        "name": BOOK_TITLE,
        "description": cover.description,
        "url": BASE_URL,
        "image": cover.image_url,
        "inLanguage": "en-GB",
        "bookFormat": "https://schema.org/EBook",
        "genre": "Fantasy",
        "author": PUBLISHER,
        "publisher": PUBLISHER,
        "copyrightHolder": {"@type": "Organization", "name": "EDOS LLC"},
        "copyrightYear": 2026,
        "license": "https://creativecommons.org/licenses/by/4.0/",
        "character": {"@type": "Person", "name": "Glurp"},
        "hasPart": [chapter_ld(ch, False) for ch in chapters],
    })
    for ch in chapters:
        by_path[ch.href].jsonld.append(chapter_ld(ch, True))
    for page in pages:
        if page.path == "index.html":
            continue
        trail = [("Cover", "index.html")]
        if page.path in {ch.href for ch in chapters}:
            trail.append(("Contents", "contents.html"))
        trail.append((name(page), page.path))
        page.jsonld.append({
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": i, "name": n, "item": page_url(p)}
                for i, (n, p) in enumerate(trail, 1)
            ],
        })


def git_lastmod(paths: list[str]) -> str | None:
    """Date of the last commit touching any of paths, or None outside git.

    A shallow clone only knows its tip, so every page gets the tip's date there.
    """
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%cs", "--", *paths],
            cwd=ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    return out or None


def sitemap(pages: list[Page]) -> str:
    rows = []
    for page in pages:
        lastmod = git_lastmod(page.sources)
        rows.append(
            f"  <url><loc>{html.escape(page_url(page.path))}</loc>"
            + (f"<lastmod>{lastmod}</lastmod>" if lastmod else "")
            + "</url>"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(rows)
        + "\n</urlset>\n"
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(ROOT / "_site"), help="output directory")
    ap.add_argument("--render-og", action="store_true", help="re-render site/og.png with Chrome first")
    args = ap.parse_args()
    if args.render_og:
        render_og()
    build(Path(args.out))


if __name__ == "__main__":
    main()
