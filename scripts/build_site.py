#!/usr/bin/env python3
"""Build the Glurp lore storybook site.

Renders the Markdown in this repository into static HTML under _site/
(or the directory given with --out). Standard library only.

    python3 scripts/build_site.py              # build into _site/
    python3 scripts/build_site.py --render-og  # also re-render site/og.png
                                               # with a local headless Chrome

The Markdown converter covers only the constructs the lore uses:
headings, paragraphs, emphasis, strong, inline code, links, images,
fenced code, block quotes, lists, tables, definition lists and rules.
"""

from __future__ import annotations

import argparse
import html
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
            out.append(f"<p{cls}>{inline(b.text)}</p>")
        elif b.kind == "img":
            place = b.items[1] if len(b.items) > 1 else ""
            out.append(figure(b, f"fig fig-{place}") if place else figure(b))
        elif b.kind == "pre":
            out.append(f"<pre><code>{html.escape(b.text)}</code></pre>")
        elif b.kind == "hr":
            out.append('<hr class="ornament">')
        elif b.kind == "quote":
            out.append(quote_html(b.items))
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


def quote_html(lines: list[str]) -> str:
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


def quotes_transform(blocks: list[Block]) -> str:
    """Each quote becomes a speech card; a paragraph after it is its caption."""
    cards = []
    i = 0
    while i < len(blocks):
        b = blocks[i]
        if b.kind == "quote":
            cap = ""
            if i + 1 < len(blocks) and blocks[i + 1].kind == "p":
                cap = f"<figcaption>{inline(blocks[i + 1].text)}</figcaption>"
                i += 1
            cards.append(f'<figure class="speech">{quote_html(b.items)}{cap}</figure>')
        else:
            cards.append(render([b]))
        i += 1
    return f'<div class="speech-grid">{"".join(cards)}</div>'


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
<meta property="og:image" content="{BASE_URL}og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Glurp, a green pixel-art ork in a purple hoodie, beside a three-ringed crystal ball, under the title The Lore and History of Glurp.">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<link rel="preload" href="fonts/pixelify-sans-700.woff2" as="font" type="font/woff2" crossorigin>
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
    <p class="legal">Text © 2026 EDOS LLC, licensed <a href="{REPO_URL}/blob/main/LICENSE" rel="noopener">CC BY 4.0</a>. Ork Meter, Ork Meter Plus, Ork Bot, Orkestera, EDOS, the three-ring mark and the Glurp character are trademarks of EDOS LLC.</p>
  </div>
</footer>
</body>
</html>
"""


# --------------------------------------------------------------------------
# Open Graph image
# --------------------------------------------------------------------------

OG_HTML = """<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{{font-family:Pixelify;font-weight:700;src:url({fonts}/pixelify-sans-700.woff2) format("woff2")}}
@font-face{{font-family:JBM;font-weight:500;src:url({fonts}/jetbrains-mono-500.woff2) format("woff2")}}
html,body{{margin:0;width:1200px;height:630px;overflow:hidden;background:#101412}}
.card{{position:absolute;inset:28px;background:#171d19;border:6px solid #0d120e;box-shadow:10px 10px 0 #0d120e;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:18px}}
img{{width:896px;height:384px;image-rendering:pixelated;border:6px solid #0d120e}}
h1{{margin:0;font:700 52px Pixelify,monospace;color:#edf3e9;letter-spacing:1px}} h1 span{{color:#c4f58a}}
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


def render_og() -> None:
    chrome = find_chrome()
    if not chrome:
        sys.exit("render-og: no Chrome found (set CHROME=/path/to/chrome)")
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
            transform=quotes_transform,
        )
    )
    pages.append(
        simple_page(
            "tooltip.md", "tooltip.html", "From orkmeter.com", "page-tooltip",
            ("quotes.html", "Glurp-isms"), ("index.html", "Back to the cover"),
            transform=tooltip_transform,
        )
    )

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    for page in pages:
        (out / page.path).write_text(layout(page), encoding="utf-8")
    shutil.copytree(ROOT / "images", out / "images")
    for item in SITE_ASSETS.iterdir():
        dest = out / item.name
        if item.is_dir():
            shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)
    (out / "CNAME").write_text("lore.orkmeter.com\n", encoding="utf-8")
    (out / ".nojekyll").write_text("", encoding="utf-8")
    print(f"built {len(pages)} pages into {out}")


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
