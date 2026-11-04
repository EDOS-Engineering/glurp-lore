#!/usr/bin/env python3
"""Paint every illustration in images/ from pixel grids.

    python3 scripts/make_art.py            # rewrite images/
    python3 scripts/make_art.py OUT_DIR    # write somewhere else

Standard library only. Each picture is a grid of palette keys painted as
horizontal <rect> runs with crisp edges; the one exception is the Ork Meter
mark (three rings), which is laid over the crystal ball exactly as the brand
draws it and is never altered. No scripts, no text, no foreignObject.

Glurp's pose grids and palette are copied verbatim from the Ork Meter app's
scripts/render_glurp.py; the conductor recolour, baton and notes for cousin
Glorp come from the brand's Ork.dc.html (notes always float above the head).
New poses are built from the same base grid: hands removed, sleeves drawn as
outlined limbs, props stamped on top.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# --------------------------------------------------------------------------
# Glurp: palette and grids (verbatim from render_glurp.py)
# --------------------------------------------------------------------------

PALETTE = {
    "K": "#0d120e", "P": "#0d120e",
    "G": "#6fae3f", "L": "#9fd66a", "D": "#4a7d2a", "Z": "#355a20",
    "W": "#f1ecd8", "V": "#cfc6a8", "E": "#ffd84a", "X": "#3a1414",
    "H": "#4b3f86", "J": "#7d6dcc", "Q": "#362c66",
    "N": "#2a2f3a", "U": "#3c4352", "B": "#5a3d27",
    "T": "#f2c14e", "F": "#ffe08a", "O": "#b8862b", "M": "#c9d4c6", "S": "#c4f58a", "R": "#e5533d",
}

BASE = [
    "........KKKKKKKK........",
    "......KKGLLLGGGGKK......",
    ".....KGLLLGGGGGGGDK.....",
    "....KGLGGGGGGGGGGGDK....",
    "....KGKKKKKGGKKKKKGK....",
    "KK..KGWEPGGGGGGPEWDK..KK",
    "KZK.KGGGGGGDDGGGGGDK.KZK",
    "KZGKKGGGGGXGGXGGGGDKKGZK",
    ".KGDKGGGGGGGGGGGGGDKDGK.",
    "..KKKGWGGGGGGGGGGWDKKK..",
    "....KGWVKKKKKKKKWVDK....",
    "....KGGVKXXXXXXKVGDK....",
    ".....KDGGKKKKKKGGDK.....",
    "......KKDGGGGGGDKK......",
    "....KKJHHHHHHHHHHQKK....",
    "...KJHHHHHHWWHHHHHHQK...",
    "..KJHHHHHHHWWHHHHHHHQK..",
    "..KHJHHHHHHTTHHHHHHQQK..",
    ".KGKHHHHQJJJJJJQHHHQKGK.",
    ".KGKHHHHQQQQQQQQHHHQKGK.",
    "..KKHHHHHHHHHHHHHHQQKK..",
    "...KQQQQQQQQQQQQQQQQK...",
    "...KUNNNNNK..KUNNNNNK...",
    "...KBBBBBBK..KBBBBBBK...",
    "...KKKKKKKK..KKKKKKKK...",
]

ASK = [
    ".......KKKKKKKK.......",
    ".....KKGGGGGLLGKK.....",
    "....KGGGGGGGLLGGGK....",
    "...KGGGGGGGGGLLGGDK...",
    "..KKKKKKGKKKKKGGGGGK..",
    "..KPEGGGPEWGGGGGGDKKK.",
    ".KGGGGGGGGGGGGGGDKZGK.",
    "KGXGGGGGGGGGGGGGDKZZGK",
    "KGGGGGGGGGGGGGGGDKZGK.",
    ".KWGGGGGWGGGGGGGGDKK..",
    ".KVKKKKKWVGGGGGGGDK...",
    "..KGXXXXKVGGGGGGGDK...",
    "...KDKKKKGGGGGGGDK....",
    "....KKDGGGGGGGDKK.....",
    "....KKJHHHHHHHHQKK....",
    "...KJHHWWHHHHHHHHQK...",
    "..KJHHHWWHHHHHHHHHQK..",
    "..KHHHHTTHHHHHHHHQQK..",
    ".KGKHHHQJJJJJQHHHQKGK.",
    ".KGKHHHQQQQQQQHHHQKGK.",
    "..KKHHHHHHHHHHHHQQKK..",
    "...KQQQQQQQQQQQQQQK...",
    "...KUNNNNK..KUNNNNK...",
    "..KBBBBBBK..KBBBBBBK..",
    "..KKKKKKKK..KKKKKKKK..",
]

GAUGE = ["..KKKKK..", ".KSSMRRK.", "KSMMMMMRK", "KMMMMMKMK", "KMMMMKMMK", "KMMMKMMMK", ".KMMMMMK.", "..KKKKK.."]
COIN = [".TT.", "TFFO", "TFFO", ".OO."]
DRIP = ["T", "T", ".", "T"]

# --------------------------------------------------------------------------
# Scene palette: Glurp's colours plus props, Glorp, and the valley folk
# --------------------------------------------------------------------------

PAL = dict(PALETTE)
PAL.update({
    # scene colours
    "a": "#171d19",  # panel
    "b": "#101412",  # floor / bg
    "c": "#303a32",  # line
    "o": "#131915",  # orb fill
    "r": "#1d2a1c",  # orb rim
    "t": "#0b0f0c",  # terminal screen
    "Y": "#a08ff0",  # note (Ork.dc.html default)
    # conductor recolour (Ork.dc.html, pose === 'conductor')
    "1": "#7C89DB", "2": "#9DA8E6", "3": "#5F6CD0", "4": "#4C58BC", "5": "#272D5E",
    "6": "#1E9587", "7": "#33B0A0", "8": "#17796E", "9": "#5FC9BA",
    # props
    "wood": "#7a5434", "wood_hi": "#8f6640", "wood_dk": "#45301f",
    "stone": "#232b26", "stone_hi": "#2b352e",
    "glass": "#1f2a24", "ring2": "#99cc70", "ring3": "#72a653",
    "night": "#0e1320", "moon": "#f1ecd8",
    "slate0": "#1f232b",
    # Pib, the young ork with the confident haircut
    "pib1": "#8fcf55", "pib2": "#b9e889", "pib3": "#629a37", "pib4": "#46722a",
    # valley orks
    "va1": "#5d9a3c", "va2": "#86c25a", "va3": "#3f7026", "va4": "#2c501b",
    "vb1": "#8f9f3e", "vb2": "#b4c45e", "vb3": "#6b7a2c", "vb4": "#4d581f",
    "vc1": "#4f9d6c", "vc2": "#77c48f", "vc3": "#357550", "vc4": "#25543a",
    # Grandmother Orgle
    "gm1": "#8fa46b", "gm2": "#b0c48c", "gm3": "#6c8150", "gm4": "#4d5d38",
    # the elf, the dwarf, the troll
    "el1": "#e6cfae", "el2": "#f4e4c8", "el3": "#c4a47e", "el4": "#a6855f", "elx": "#7a3b3b",
    "dw1": "#d39b70", "dw2": "#e8b78f", "dw3": "#a8714f", "dw4": "#8a5a3d",
    "dwr": "#b8432f", "dwr2": "#8c3123",
    "tr1": "#8ea3b5", "tr2": "#b3c4d3", "tr3": "#6c8196", "tr4": "#53667a",
    # the bee-keeping goblin
    "gb1": "#a7b24a", "gb2": "#c6d06a", "gb3": "#7d8734",
})
GLOW = {"g": ("#c4f58a", 0.28), "h": ("#c4f58a", 0.13)}

CONDUCT = {"G": "1", "L": "2", "D": "3", "Z": "4", "X": "5", "H": "6", "J": "7", "Q": "8", "Y": "9"}


def skin(prefix):
    return {"G": f"{prefix}1", "L": f"{prefix}2", "D": f"{prefix}3", "Z": f"{prefix}4"}


PIB = {**skin("pib"), "H": "U", "J": "M", "Q": "N"}
VALLEY_A = {**skin("va"), "H": "B", "J": "wood_hi", "Q": "wood_dk"}
VALLEY_B = {**skin("vb"), "H": "U", "J": "M", "Q": "N"}
VALLEY_C = {**skin("vc"), "H": "O", "J": "T", "Q": "wood_dk"}
GRANNY = {**skin("gm"), "H": "J", "J": "Y", "Q": "H", "T": "W"}
ELF = {"G": "el1", "L": "el2", "D": "el3", "Z": "el4", "X": "elx", "H": "ring3", "J": "S", "Q": "D", "T": "T"}
DWARF = {"G": "dw1", "L": "dw2", "D": "dw3", "Z": "dw4", "H": "dwr", "J": "R", "Q": "dwr2", "T": "M"}
TROLL = {"G": "tr1", "L": "tr2", "D": "tr3", "Z": "tr4", "X": "N", "H": "O", "J": "T", "Q": "wood_dk", "T": "F"}

BATON = [".......W", "......W.", ".....W..", "....W...", "...W....", "..W.....", ".B......", "B......."]
NOTE = ["..YYY", "..Y.Y", "..Y..", "YYY..", "YYY.."]

MARK = ('<g fill="none" stroke-linecap="round" shape-rendering="geometricPrecision" transform="translate({x} {y}) scale({s})">'
        '<path d="M24 14A10 10 0 1 1 14 4" stroke="#c4f58a" stroke-width="2.5"/>'
        '<path d="M21 14A7 7 0 1 1 14 7" stroke="#99cc70" stroke-width="2"/>'
        '<path d="M18 14A4 4 0 1 1 14 10" stroke="#72a653" stroke-width="1.75"/></g>')

FLOOR = 40  # first floor row of a 48-row plate; feet stand on FLOOR - 1


# --------------------------------------------------------------------------
# Pixel grids
# --------------------------------------------------------------------------

def line_cells(a, b):
    """Bresenham cells from a to b inclusive."""
    (x0, y0), (x1, y1) = a, b
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err = dx + dy
    out = []
    while True:
        out.append((x0, y0))
        if (x0, y0) == (x1, y1):
            return out
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


class Grid:
    """A grid of palette keys; '.' (or the scene's empty key) is unpainted."""

    empty = "."

    def __init__(self, w, h, fill="."):
        self.w, self.h = w, h
        self.g = [[fill] * w for _ in range(h)]

    def get(self, x, y):
        return self.g[y][x] if 0 <= x < self.w and 0 <= y < self.h else None

    def put(self, x, y, ch):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.g[y][x] = ch

    def stamp(self, x, y, rows, remap=None):
        for j, row in enumerate(rows):
            for i, ch in enumerate(row if isinstance(row, (list, tuple)) else list(row)):
                if ch != ".":
                    self.put(x + i, y + j, (remap or {}).get(ch, ch))

    def box(self, x, y, w, h, ch):
        for j in range(h):
            for i in range(w):
                self.put(x + i, y + j, ch)

    def frame(self, x, y, w, h, fill, edge="K"):
        self.box(x, y, w, h, edge)
        self.box(x + 1, y + 1, w - 2, h - 2, fill)

    def cells(self):
        return [list(r) for r in self.g]

    def limb(self, pts, fill="H", hand="G", over=False, width=2):
        """A sleeve along pts, a 2x2 hand at the last point, outlined in K."""
        body = set()
        for a, b in zip(pts, pts[1:]):
            for x, y in line_cells(a, b):
                for dx in range(width):
                    for dy in range(width):
                        body.add((x + dx, y + dy))
        hx, hy = pts[-1]
        hand_cells = {(hx + dx, hy + dy) for dx in (0, 1) for dy in (0, 1)} if hand else set()
        for x, y in body - hand_cells:
            self.put(x, y, fill)
        for x, y in hand_cells:
            self.put(x, y, hand)
        every = body | hand_cells
        for x, y in every:
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if (nx, ny) in every:
                    continue
                cur = self.get(nx, ny)
                if cur == self.empty or (over and cur not in (None, "K")):
                    self.put(nx, ny, "K")

    def outline(self, keys=None):
        """Ring every painted run with K where it touches empty space."""
        add = []
        for y in range(self.h):
            for x in range(self.w):
                if self.g[y][x] == self.empty:
                    for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                        v = self.get(nx, ny)
                        if v not in (None, self.empty, "K") and (keys is None or v in keys):
                            add.append((x, y))
                            break
        for x, y in add:
            self.put(x, y, "K")


def sprite(w, h):
    return Grid(w, h)


# --------------------------------------------------------------------------
# Poses (all built from BASE; a pose returns grid rows, feet on the last row)
# --------------------------------------------------------------------------

def no_hands(rows=BASE):
    s = sprite(24, 25)
    s.stamp(0, 0, rows)
    for y in (18, 19):
        s.put(1, y, ".")
        s.put(2, y, "K")
        s.put(3, y, "H")
        s.put(20, y, "Q")
        s.put(21, y, "K")
        s.put(22, y, ".")
    return s.cells()


def mirror_pts(pts):
    return [(22 - x, y) for x, y in pts]


def pose(w, h, ox, oy, body, arms=(), over=False):
    s = sprite(w, h)
    s.stamp(ox, oy, body)
    for pts in arms:
        s.limb([(x + ox, y + oy) for x, y in pts], over=over)
    return s


def close_eyes(rows):
    g = [list(r) for r in rows]
    for x in (6, 7, 8, 15, 16, 17):
        g[5][x] = "G"
        g[6][x] = "K"
    g[6][8] = g[6][15] = "G"
    return g


def raise_brow(rows):
    g = [list(r) for r in rows]
    for x in range(13, 18):
        g[4][x] = "G"
        g[3][x] = "K"
    return g


def grin(rows):
    g = [list(r) for r in rows]
    # wider, open grin: tusks stay, the mouth drops a row in the middle
    for x in range(9, 15):
        g[12][x] = "X"
    g[12][9] = g[12][14] = "K"
    g[13][9:15] = list("KKKKKK")
    return g


LEFT_UP = [(2, 16), (-2, 11), (-3, 6), (-3, 3)]
LEFT_SHRUG = [(3, 16), (-1, 19), (-3, 15)]
LEFT_WAVE = LEFT_UP


def glurp_celebrate():
    body = grin(no_hands())
    s = pose(34, 30, 5, 5, body, [LEFT_UP, mirror_pts(LEFT_UP)])
    for x, y, ch in [(3, 1, "T"), (9, 0, "S"), (15, 2, "Y"), (24, 0, "T"), (29, 2, "S"), (31, 0, "Y"),
                     (1, 4, "Y"), (32, 5, "T"), (12, 3, "S"), (20, 3, "T")]:
        s.put(x, y, ch)
    return s.cells()


def glurp_shrug(rows=None):
    body = raise_brow(no_hands(rows or BASE))
    s = pose(34, 30, 5, 5, body, [LEFT_SHRUG, mirror_pts(LEFT_SHRUG)])
    return s.cells()


def glurp_wave():
    body = no_hands()
    b = [list(r) for r in body]
    # keep the left hand, raise the right
    for y in (18, 19):
        b[y][1], b[y][2], b[y][3] = "K", "G", "K"
    s = pose(30, 29, 2, 4, b, [mirror_pts(LEFT_UP)])
    return s.cells()


def glurp_wand():
    b = [list(r) for r in no_hands()]
    for y in (18, 19):
        b[y][1], b[y][2], b[y][3] = "K", "G", "K"
    s = pose(38, 33, 3, 8, b, [[(19, 16), (23, 13), (26, 9)]])
    # the wand: light wood, tipped with a lime star
    hx, hy = 26 + 3, 9 + 8
    for i in range(1, 7):
        s.put(hx + 1 + i // 2 + i - 1 - i // 2, hy - i, "wood_hi")
    tip = (hx + 7, hy - 8)
    star = [(0, 0, "W"), (-1, 0, "S"), (1, 0, "S"), (0, -1, "S"), (0, 1, "S"), (-2, 0, "ring3"), (2, 0, "ring3"),
            (0, -2, "ring3"), (0, 2, "ring3")]
    for dx, dy, ch in star:
        s.put(tip[0] + dx, tip[1] + dy, ch)
    for x, y, ch in [(29, 3, "S"), (26, 6, "T"), (36, 4, "Y"), (31, 0, "T"), (24, 2, "S"), (33, 12, "S")]:
        s.put(x, y, ch)
    return s.cells()


def glurp_read(candle=False):
    s = sprite(28, 28)
    body = no_hands()
    s.stamp(2, 3, body)
    # the Book of Wounds held open as a scroll across the chest
    x0, y0 = 2, 3
    s.frame(x0 + 1, y0 + 15, 3, 8, "V")
    s.frame(x0 + 20, y0 + 15, 3, 8, "V")
    s.box(x0 + 4, y0 + 16, 16, 6, "W")
    s.box(x0 + 4, y0 + 15, 16, 1, "K")
    s.box(x0 + 4, y0 + 22, 16, 1, "K")
    for k in range(3):
        s.put(x0 + 6, y0 + 17 + 2 * k, "R")
        s.box(x0 + 8, y0 + 17 + 2 * k, 9 - (k % 2) * 3, 1, "V")
    for hx in (x0 - 1, x0 + 22):
        s.frame(hx, y0 + 17, 4, 4, "G")
        s.put(hx + 1, y0 + 18, "L")
    return s.cells()


def glurp_walk():
    b = [list(r) for r in no_hands()]
    for y in (18, 19):  # the right hand stays; the left arm holds the ball (drawn by the scene)
        b[y][20], b[y][21], b[y][22] = "K", "G", "K"
    # stride: the left boot planted, the right one lifted
    b[22] = list("...KUNNNNNK..KBBBBBBK...")
    b[23] = list("...KBBBBBBK..KKKKKKKK...")
    b[24] = list("...KKKKKKKK.............")[:24]
    return b


def glurp_seated_rows(rows=BASE, cut=19):
    """Head and shoulders only, for sitting behind a desk."""
    return [list(r) for r in rows[:cut]]


def glorp_baton_up():
    body = no_hands()
    s = pose(38, 36, 7, 11, body, [LEFT_UP, mirror_pts(LEFT_UP)])
    # baton from the raised right hand, pointing up and out
    hx, hy = 25 + 7, 3 + 11
    for i in range(1, 6):
        s.put(hx + 1 + i // 2, hy - i, "W")
    s.put(hx + 1, hy + 1, "B")
    s.stamp(12, 1, NOTE)
    s.stamp(21, 3, NOTE)
    s.stamp(16, 6, ["..YY", "..Y.", "YYY.", "YYY."])
    return s.cells()


def glorp_shrug():
    s = sprite(34, 37)
    s.stamp(0, 7, glurp_shrug())
    s.stamp(11, 0, NOTE)
    s.stamp(20, 2, NOTE)
    # a tiny baton held in the right palm
    for i in range(4):
        s.put(31 + i // 2, 20 - i, "W")
    return s.cells()


def glurp_point(rows=BASE):
    b = [list(r) for r in no_hands(rows)]
    for y in (18, 19):
        b[y][1], b[y][2], b[y][3] = "K", "G", "K"
    s = pose(36, 25, 0, 0, b, [[(19, 15), (25, 14), (31, 14)]])
    s.put(34, 14, "G")
    s.put(35, 14, "K")
    s.put(34, 13, "K")
    s.put(34, 15, "K")
    return s.cells()


def goblin():
    return [
        "....KKKKKKKK....",
        "...KgggggggqK...",
        "KK.KgKKKKKKgK.KK",
        "KgKKgEPggPEgKKgK",
        ".KgKggggggggKgK.",
        "..KKggXggXggKK..",
        "...KgKKKKKKgK...",
        "....KggWWggK....",
        "...KKUUUUUUKK...",
        "..KgKUUMMUUKgK..",
        "..KgKUUUUUUKgK..",
        "...KKUUUUUUKK...",
        "....KNNK.KNNK...",
        "....KBBK.KBBK...",
        "....KKKK.KKKK...",
    ]


GOBLIN = {"g": "gb1", "q": "gb2"}

BEE = ["KT", "TK"]

AGENT = [
    "...T....",
    "...K....",
    ".KKKKKK.",
    ".KttttK.",
    ".KStStK.",
    ".KttttK.",
    ".KKKKKK.",
    "KUUUUUUK",
    "KUMSSMUK",
    "KUUUUUUK",
]

ORK_BOT = [
    "..K......K..",
    ".KJK....KJK.",
    ".KJJKKKKJJK.",
    "..KJJJJJJK..",
    ".KJSKJJKSJK.",
    ".KJJJJJJJJK.",
    "..KJKKKKJK..",
    "...KJJJJK...",
    "..KHK..KHK..",
    "..KK....KK..",
]

DUCK = [
    "...KKK.....",
    "..KTTTK....",
    "KKKKTTK..K.",
    "KOOKTTKKKTK",
    ".KKTTTTTTTK",
    ".KTTTTFTTTK",
    "..KOTTTTOK.",
    "...KKKKKK..",
]

PANCAKES = [
    "....KK....",
    "...KTTK...",
    ".KKKKKKKK.",
    "KTTTTTTTTK",
    "KOOOOOOOOK",
    "KTTTTTTTTK",
    "KOOOOOOOOK",
    "KTTTTTTTTK",
    ".KKKKKKKK.",
]

MUG = [".KKKK..", "KWWWWKK", "KVVVVK.K", "KVVVVKK", "KVVVVK.", ".KKKK.."]
CANDLE = ["..T..", ".TFT.", "..F..", ".KKK.", ".KWK.", ".KWK.", ".KVK.", "KKKKK"]
FILE = ["KKKKKK.", "KWWWWKK", "KWVVWWK", "KWWWWWK", "KWVVVWK", "KWWWWWK", "KWVVWWK", "KKKKKKK"]
TURNIP = [".S.S.", "..S..", ".KWK.", "KWWJK", "KJJJK", ".KJK.", "..K.."]
ROCK = [".KKK.", "KMUUK", "KUUNK", ".KKK."]
LOCK = [".KKK.", "K...K", "K...K", "KKKKK", "KTTTK", "KTKTK", "KTTTK", "KKKKK"]
BIG_ROCK = ["..KKKK..", ".KMMUUK.", "KMUUUUNK", "KUUUUNNK", "KUUNNNNK", ".KKKKKK."]
BIG_LOCK = ["..KKKK..", ".K....K.", ".K....K.", "KKKKKKKK", "KTTTTTTK", "KTFTKTTK", "KTTTKTTK", "KTTTTTOK", "KKKKKKKK"]
ZZZ = ["YYY", "..Y", ".Y.", "YYY"]


# --------------------------------------------------------------------------
# Scenes
# --------------------------------------------------------------------------

class Scene(Grid):
    """A picture: a framed plate (default) or a transparent spot."""

    def __init__(self, w=80, h=48, cell=8, framed=True, transparent=False, floor=None):
        self.transparent = transparent
        self.empty = "." if transparent else "a"
        super().__init__(w, h, self.empty)
        self.C = cell
        self.framed = framed
        self.floor = FLOOR if floor is None and h == 48 else (h - 8 if floor is None else floor)
        if not transparent:
            for y in range(self.floor, h):
                for x in range(w):
                    self.g[y][x] = "c" if y == self.floor else "b"
        self.overlay = []

    # --- characters ---
    def glurp(self, pose, x, remap=None):
        y = self.floor - 25
        C = remap or {}
        if pose == "ask":
            self.stamp(x, y, ASK, remap)
            return
        if pose == "conductor":
            self.stamp(x, y, BASE, CONDUCT)
            self.stamp(x + 21, y + 11, BATON, CONDUCT)
            self.stamp(x + 5, y - 8, NOTE, CONDUCT)
            self.stamp(x + 18, y - 7, NOTE, CONDUCT)
            return
        self.stamp(x, y, BASE, C)
        if pose == "meter":
            self.stamp(x + 17, y + 12, GAUGE)
        if pose == "bleed":  # offsets from render_glurp.POSES["bleed"], relative to BASE
            self.stamp(x + 11, y + 22, DRIP)
            self.stamp(x + 21, y + 16, COIN)
            self.stamp(x + 25, y + 20, COIN)
            self.stamp(x - 4, y + 18, COIN)
            self.stamp(x + 20, y + 22, COIN)

    def stand(self, rows, x, remap=None, floor=None):
        """Stamp a sprite so its last row rests on the floor."""
        f = self.floor if floor is None else floor
        self.stamp(x, f - len(rows), rows, remap)

    # --- Ork Meter crystal ball on its pixel stand (as in Hero.dc.html) ---
    def ball(self, cx, r, inner_glow=False, base=None):
        base = self.floor if base is None else base
        sw = r + r // 4  # stand half-widths
        top_w, bot_w = 2 * (sw - 2), 2 * sw + 2
        stand_h = 7
        cy = base - stand_h - r + 1  # orb centre (cell edge coordinates)
        self.orb(cx, cy, r)
        sy = base - stand_h
        self.frame(int(cx - top_w / 2), sy, top_w, 4, "H")
        self.frame(int(cx - bot_w / 2), sy + 3, bot_w, 4, "N")

    def orb(self, cx, cy, r, glow=True):
        layers = [(r + 3, "h"), (r + 2, "g"), (r + 1, "r"), (r, "K"), (r - 1, "o")]
        if not glow:
            layers = layers[2:]
        for rad, ch in layers:
            for j in range(self.h):
                for i in range(self.w):
                    if (i + 0.5 - cx) ** 2 + (j + 0.5 - cy) ** 2 <= rad * rad:
                        if ch in GLOW and self.g[j][i] != self.empty:
                            continue  # glow only over empty panel
                        self.put(i, j, ch)
        self.mark(cx, cy, 0.77 * 2 * (r - 1))

    def mark(self, cx, cy, cells):
        size = cells * self.C
        self.overlay.append(MARK.format(x=round(cx * self.C - size / 2, 2), y=round(cy * self.C - size / 2, 2),
                                        s=round(size / 28, 4)))

    # --- terminal on a small foot ---
    def terminal(self, x, y, w, h, lines, base=None):
        base = self.floor if base is None else base
        self.frame(x, y, w, h, "t")
        self.box(x + 1, y + 1, w - 2, 2, "c")
        for k, ch in enumerate("RTS"):
            self.put(x + 2 + 2 * k, y + 1, ch)
        foot_w = 6
        fx = x + w // 2 - foot_w // 2
        self.frame(fx + 1, y + h - 1, foot_w - 2, base - 3 - (y + h) + 3, "U")
        self.frame(fx - 2, base - 3, foot_w + 4, 3, "N")
        for k, (indent, length, ch) in enumerate(lines):
            ly = y + 4 + 2 * k
            if ly >= y + h - 2:
                break
            self.box(x + 3 + indent, ly, length, 1, ch)

    def screen(self, x, y, w, h, lines, step=2):
        """A bare monitor face (no foot), for desks."""
        self.frame(x, y, w, h, "t")
        self.box(x + 1, y + 1, w - 2, 1, "c")
        for k, (indent, length, ch) in enumerate(lines):
            ly = y + 3 + step * k
            if ly >= y + h - 1:
                break
            self.box(x + 2 + indent, ly, min(length, w - 3 - indent), 1, ch)

    def desk(self, x, y, w, h, legs=True):
        """Desk: a light top edge and a darker front; y is the top surface row."""
        self.box(x, y, w, 1, "K")
        self.box(x, y + 1, w, 2, "wood_hi")
        self.box(x, y + 3, w, 1, "K")
        if legs:
            self.box(x + 1, y + 4, w - 2, 1, "wood_dk")
            for lx in (x + 1, x + w - 4):
                self.frame(lx, y + 3, 3, h - 3, "wood")
        else:
            self.frame(x, y + 3, w, h - 3, "wood")
        self.put(x, y, "K")

    def keyboard(self, x, y, w):
        self.frame(x, y, w, 3, "U")
        for i in range(x + 1, x + w - 1, 2):
            self.put(i, y + 1, "M")

    def shadow(self, x, y, w):
        self.box(x, y, w, 1, "c")

    def window(self, x, y, w, h, stars=()):
        self.frame(x, y, w, h, "night")
        self.box(x + w // 2, y + 1, 1, h - 2, "K")
        self.box(x + 1, y + h // 2, w - 2, 1, "K")
        for sx, sy in stars:
            self.put(x + sx, y + sy, "M")

    def moon(self, x, y):
        self.stamp(x, y, [".WW.", "WWVW", "WWWW", ".WW."], {"W": "moon"})

    def svg(self, title):
        C = self.C
        rects = []
        for y, row in enumerate(self.g):
            x = 0
            while x < self.w:
                ch = row[x]
                end = x
                while end < self.w and row[end] == ch:
                    end += 1
                if ch in GLOW:
                    col, op = GLOW[ch]
                    rects.append(f'<rect x="{x * C}" y="{y * C}" width="{(end - x) * C}" height="{C}" fill="{col}" fill-opacity="{op}"/>')
                elif ch not in ("a", "."):
                    rects.append(f'<rect x="{x * C}" y="{y * C}" width="{(end - x) * C}" height="{C}" fill="{PAL[ch]}"/>')
                x = end
        W, H = self.w * C, self.h * C
        border = ""
        if self.framed:
            border = (f'<rect x="0" y="0" width="{W}" height="4" fill="#0d120e"/>'
                      f'<rect x="0" y="{H - 4}" width="{W}" height="4" fill="#0d120e"/>'
                      f'<rect x="0" y="0" width="4" height="{H}" fill="#0d120e"/>'
                      f'<rect x="{W - 4}" y="0" width="4" height="{H}" fill="#0d120e"/>')
        bg = "" if self.transparent else f'<rect x="0" y="0" width="{W}" height="{H}" fill="#171d19"/>'
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
                f'shape-rendering="crispEdges" role="img" aria-labelledby="t">'
                f'<title id="t">{title}</title>'
                + bg + "\n".join(rects) + "\n" + "".join(self.overlay) + border + "</svg>\n")


S, M, P = "S", "M", "c"  # lime, muted, dim line colours


def code_lines():
    return [(0, 2, S), (3, 10, M), (3, 14, M), (5, 8, "T"), (3, 12, M), (0, 2, S), (3, 6, M), (0, 1, "J")]


# --------------------------------------------------------------------------
# The chapter plates (one per chapter, plus the cover)
# --------------------------------------------------------------------------

def plates():
    out = {}

    s = Scene(112, 48)
    s.ball(30, 9)
    s.glurp("bleed", 56)
    out["glurp-header"] = (s, "Glurp, a green pixel-art ork in a purple hoodie, stands beside their three-ringed crystal ball while gold tokens drip from their hoodie pocket.")

    s = Scene()
    s.terminal(6, 13, 30, 22, code_lines())
    s.glurp("idle", 46)
    out["01-hand-forged-code"] = (s, "Glurp stands beside their terminal, its screen full of hand-forged code, as they work late in the tower.")

    s = Scene()
    s.ball(22, 9)
    s.glurp("ask", 42)
    out["02-crystal-ball"] = (s, "Glurp looks up at their crystal ball on its stand, its three rings glowing, and asks where it all goes.")

    s = Scene()
    waterfall = [(0, 2, S), (2, 20, M), (2, 17, M), (2, 21, M), (2, 19, M), (2, 20, M), (2, 15, M), (2, 21, M)]
    s.terminal(6, 13, 30, 22, waterfall)
    s.glurp("bleed", 48)
    out["03-coming-of-the-agents"] = (s, "Glurp watches agent output pour down their terminal while gold tokens drip from their hoodie pocket.")

    s = Scene()
    # Book of Wounds: a parchment scroll pinned to the wall, five entries, each with a red mark
    sx, sy, sw, sh = 12, 7, 20, 27
    s.frame(sx - 1, sy, sw + 2, 3, "V")
    s.frame(sx, sy + 2, sw, sh - 4, "W")
    s.frame(sx - 1, sy + sh - 3, sw + 2, 3, "V")
    s.put(sx + sw // 2, sy - 1, "K")
    for k in range(5):
        ly = sy + 5 + 4 * k
        s.box(sx + 3, ly, 2, 2, "R")
        s.box(sx + 7, ly, 10 - (k % 2) * 3, 1, "V")
        s.box(sx + 7, ly + 1, 7 + (k % 3), 1, "V")
    s.glurp("idle", 46)
    out["04-five-wounds"] = (s, "Glurp stands beside the Book of Wounds, a scroll pinned to the wall with five entries, each marked in red.")

    s = Scene()
    s.ball(20, 8)
    s.glurp("meter", 42)
    out["05-finding-the-meter"] = (s, "Glurp holds up a token gauge beside their glowing crystal ball, finally able to see where their tokens go.")

    s = Scene()
    s.ball(40, 5)
    s.glurp("idle", 6)
    s.glurp("conductor", 49)
    out["06-cousin-conducts-the-horde"] = (s, "Glurp and their cousin Glorp, an indigo ork in teal with a baton and music notes, stand on either side of the crystal ball.")

    s = Scene()
    chat = [(0, 12, M), (8, 10, S), (0, 16, "J"), (0, 9, M), (10, 8, S), (0, 14, "J")]
    s.terminal(6, 11, 30, 24, chat)
    s.glurp("idle", 48)
    out["07-glurp-joins-discord"] = (s, "Glurp stands beside a chat window where their lime messages and Ork Bot's purple replies take turns.")

    s = Scene()
    s.ball(14, 6)
    s.glurp("idle", 29)
    s.terminal(59, 17, 16, 16, [(0, 2, S)])
    s.box(59 + 3 + 3, 17 + 4, 1, 1, S)  # cursor after the prompt
    out["08-epilogue"] = (s, "Late at night, Glurp stands between their glowing crystal ball and a terminal with a fresh prompt, ready to open a new session.")
    return out


# --------------------------------------------------------------------------
# Tableaus: wide scenes from the story (110 x 48 cells at 8 px = 880 x 384)
# --------------------------------------------------------------------------

def seat(s, rows, x, desk_y, remap=None, cut=19):
    """Sit a character behind a desk whose top surface row is desk_y."""
    head = [r for r in rows[:cut]]
    s.stamp(x, desk_y - cut + 1, head, remap)


def typing_hands(s, x, desk_y, remap=None, hand="G"):
    """Forearms from the shoulders of a seated BASE at x down to a keyboard."""
    r = remap or {}
    top = desk_y - 18
    s.limb([(x + 4, top + 15), (x + 7, top + 18)], fill=r.get("H", "H"), hand=r.get(hand, hand), over=True)
    s.limb([(x + 18, top + 15), (x + 15, top + 18)], fill=r.get("H", "H"), hand=r.get(hand, hand), over=True)


def tower_wall(s, x0=0, x1=None, top=1, rows=None, step=6):
    """Faint stone courses on the back wall."""
    x1 = s.w if x1 is None else x1
    rows = rows or range(top + 3, s.floor - 2, step)
    for k, y in enumerate(rows):
        for x in range(x0 + (k % 2) * 5, x1, 10):
            if s.get(x, y) == s.empty:
                s.put(x, y, "stone_hi")
            if s.get(x + 1, y) == s.empty:
                s.put(x + 1, y, "stone_hi")


def build_tableaus():
    out = {}

    # ---- Chapter 1: the queue at the tower door
    s = Scene(110, 48)
    tower_wall(s)
    s.window(50, 5, 12, 14, stars=[(2, 2), (8, 3), (3, 9), (9, 10)])
    s.moon(52, 7)
    # notched doorframe on the left; the queue comes through it
    s.frame(1, 4, 4, s.floor - 4, "wood")
    for y in range(8, s.floor - 2, 3):
        s.put(4, y, "K")
        s.put(3, y, "wood_dk")
    s.stand(hold_front(BIG_ROCK), 5, VALLEY_C)
    s.stamp(28, s.floor - 4, BIG_ROCK[2:])
    s.stand(hold_front(BIG_LOCK), 24, VALLEY_B)
    s.stand(hold_front(TURNIP), 43, VALLEY_A)
    # the turnip cart
    cx = 62
    cart_y = s.floor - 9
    s.frame(cx, cart_y, 13, 6, "wood")
    s.box(cx + 1, cart_y + 2, 11, 1, "wood_dk")
    for k, tx in enumerate((cx + 1, cx + 4, cx + 8)):
        s.stamp(tx, cart_y - 6 + (k % 2), TURNIP)
    for wx in (cx + 1, cx + 7):
        s.stamp(wx, s.floor - 5, [".KKK.", "KUMUK", "KMKMK", "KUMUK", ".KKK."])
    # Glurp at the anvil-desk, spectacles on, ready to fix it by hand
    desk_y = s.floor - 9
    seat(s, BASE, 78, desk_y)
    spectacles(s, 78, desk_y - 18)
    s.desk(76, desk_y, 33, 9)
    s.keyboard(83, desk_y - 1, 14)
    typing_hands(s, 78, desk_y)
    s.screen(99, desk_y - 13, 10, 12, [(0, 2, S), (1, 5, M), (1, 4, M), (0, 2, S)])
    out["01-the-valley-queue"] = (s, (
        "Orks from the valley queue at Glurp's tower with their problems: one holds a rock that works on their rock "
        "but not their brother's, one a padlock, one a turnip from a cart that will not sort. Glurp sits at their "
        "anvil-desk in decorative spectacles, ready to fix it all by hand."))

    # ---- Chapter 2: asleep on the space bar while the ball keeps watch
    s = Scene(110, 48)
    tower_wall(s)
    s.window(8, 5, 14, 16, stars=[(2, 2), (10, 3), (3, 11), (11, 12), (6, 6)])
    s.moon(14, 8)
    desk_y = s.floor - 10
    s.ball(84, 7, base=desk_y)
    sleepy = close_eyes(BASE)
    s.stamp(42, desk_y - 13, sleepy[:14])
    # folded arms on the desk, cheek on the space bar
    s.limb([(40, desk_y - 3), (52, desk_y - 2)], hand=None, over=True)
    s.limb([(64, desk_y - 3), (54, desk_y - 2)], hand=None, over=True)
    s.desk(26, desk_y, 72, 10)
    s.keyboard(44, desk_y - 1, 22)
    s.screen(28, desk_y - 15, 12, 14, [(0, 2, S), (1, 7, M), (1, 5, M), (1, 8, M), (0, 2, S)])
    for k, (zx, zy) in enumerate(((66, 16), (70, 11), (75, 6))):
        s.stamp(zx, zy, ZZZ)
    out["02-asleep-on-the-space-bar"] = (s, (
        "Late at night Glurp has fallen asleep at their desk, cheek on the space bar, while the crystal ball "
        "glows beside them and keeps watch."))

    # ---- Chapter 3: the rumour at the tavern
    s = Scene(110, 48)
    # shelves of bottles and a hanging lantern
    for sy in (8, 16):
        s.box(30, sy, 50, 1, "wood_hi")
        s.box(30, sy + 1, 50, 1, "K")
        for k, bx in enumerate(range(32, 78, 5)):
            col = ("ring3", "J", "T", "R", "M")[k % 5]
            h = 3 + (k % 2)
            s.frame(bx, sy - h - 1, 3, h + 1, col)
            s.put(bx + 1, sy - h - 2, "K")
    s.stamp(53, 20, ["..K..", "..K..", ".KKK.", "KTFTK", "KFFFK", "KTFTK", ".KKK."])
    s.box(55, 0, 1, 20, "K")
    # Pib, confident haircut, showing off a sticker-covered laptop
    pib = [list(r) for r in no_hands()]
    s.stand(pib, 8, PIB, floor=s.floor)
    s.stamp(14, s.floor - 28, ["...KKKK...", "..KZZZZK..", ".KZDDDZZK.", "KZDZZZDZK."], PIB | {"Z": "pib4", "D": "pib3"})
    lx, ly = 22, s.floor - 15
    s.frame(lx, ly, 14, 9, "U")
    for k, (px, py, col) in enumerate(((2, 2, "S"), (6, 1, "R"), (9, 3, "T"), (3, 5, "J"), (8, 6, "Y"), (11, 5, "ring3"))):
        s.box(lx + px, ly + py, 2, 2, col)
    s.frame(lx - 2, ly + 5, 3, 3, "pib1")
    s.frame(lx + 13, ly + 5, 3, 3, "pib1")
    # Glurp, brow down like a portcullis, mug lowered
    gl = [list(r) for r in no_hands()]
    for x in range(6, 18):
        gl[5][x] = "K" if gl[5][x] in ("W", "E", "P") or x in (6, 17) else gl[5][x]
    s.stand(gl, 78)
    s.frame(77, s.floor - 7, 3, 3, "G")
    s.frame(100, s.floor - 7, 3, 3, "G")
    # the bar counter in front
    bar_y = s.floor - 5
    s.box(0, bar_y, 110, 1, "K")
    s.box(0, bar_y + 1, 110, 1, "wood_hi")
    s.box(0, bar_y + 2, 110, 1, "K")
    s.box(0, bar_y + 3, 110, s.h - bar_y - 3, "wood")
    for x in range(6, 110, 12):
        s.box(x, bar_y + 3, 1, s.h - bar_y - 3, "wood_dk")
    s.stamp(60, bar_y - 6, MUG)
    out["03-the-tavern-rumour"] = (s, (
        "At the tavern, Pib, a young ork with a confident haircut, holds up a sticker-covered laptop and talks about "
        "the new magic, while Glurp listens over their mug with their brow lowered like a portcullis."))

    # ---- Chapter 4: the five wounds
    s = Scene(110, 34, floor=34)
    for k in range(5):
        px = 2 + k * 22
        s.frame(px, 2, 20, 30, "b")
        s.box(px + 1, 3, 18, 2, "c")
        s.box(px + 2, 3, 2, 2, "R")
    # 1 the Flood: log lines pour down into a pool, one red line, one wet sock
    px = 2
    s.frame(px + 3, 7, 14, 4, "t")
    for k in range(6):
        y = 11 + k * 3
        s.box(px + 4 + (k % 2), y, 10 - (k % 3), 1, "M")
        s.box(px + 5, y + 1, 7 + (k % 2), 1, "c")
    s.box(px + 4, 17, 11, 1, "R")
    s.box(px + 1, 28, 18, 3, "c")
    s.box(px + 2, 28, 15, 1, "M")
    s.stamp(px + 12, 25, ["KK.", "KWK", "KRK", "KWWK", ".KKK"])
    # 2 the Circle: a lime loop chasing its own tail
    px = 24
    cx, cy, rad = px + 10, 18, 7
    for j in range(8, 30):
        for i in range(px + 1, px + 19):
            d = ((i + 0.5 - cx) ** 2 + (j + 0.5 - cy) ** 2) ** 0.5
            if rad - 1.2 <= d <= rad + 0.3 and not (i > cx and j < cy - 2 and i < cx + 4):
                s.put(i, j, "S")
    s.stamp(cx + 1, cy - rad - 1, ["K.", "SK", "SSK", "SK", "K."])
    s.stamp(cx - 2, cy - 2, AGENT[2:7])
    # 3 the Forgetful Read: the same file, five times
    px = 46
    for k in range(5):
        s.stamp(px + 3 + k * 2, 9 + k * 4, FILE)
    # 4 the Avalanche: an enormous answer tumbling down
    px = 68
    blocks = [(3, 8), (9, 7), (6, 12), (12, 11), (2, 16), (9, 16), (14, 17), (5, 21), (11, 22), (1, 25), (7, 26), (13, 26)]
    for k, (bx, by) in enumerate(blocks):
        s.frame(px + bx, by, 5, 4, ("U", "M", "N")[k % 3])
    s.box(px + 1, 30, 18, 1, "c")
    # 5 the Cold Hearth: a stone fireplace gone grey, frost creeping in
    px = 90
    s.frame(px + 2, 9, 16, 21, "U")
    s.frame(px + 5, 14, 10, 16, "t")
    for x, y in ((px + 6, 27), (px + 8, 26), (px + 10, 27), (px + 12, 26)):
        s.box(x, y, 2, 2, "N")
    s.box(px + 6, 28, 8, 1, "U")
    s.box(px + 1, 8, 18, 2, "wood")
    for x, y in ((px + 3, 12), (px + 15, 11), (px + 4, 22), (px + 16, 20), (px + 9, 6), (px + 13, 5), (px + 5, 5)):
        s.put(x, y, "M")
    s.put(px + 9, 17, "M")
    s.put(px + 11, 19, "M")
    out["04-the-five-wounds-strip"] = (s, (
        "The Five Wounds in five panels: the Flood of log lines with one red failure and a wet sock, the Circle "
        "of an agent chasing its own loop, the Forgetful Read of one file read five times, the Avalanche of "
        "giant output tumbling down, and the Cold Hearth, a fireplace gone grey and frosty."))

    # ---- Chapter 5: the sign in the glass
    s = Scene(110, 48)
    tower_wall(s)
    s.terminal(6, 10, 32, 24, [])
    s.box(9, 14, 26, 18, "t")
    s.orb(22, 22, 7, glow=False)
    s.ball(88, 9)
    s.stand(raise_brow(BASE), 44)
    for x, y in ((40, 12), (41, 10), (70, 12), (69, 10)):
        s.put(x, y, "T")
    s.stamp(55, 6, [".TT.", "T..T", "..T.", ".T..", "....", ".T.."])
    out["05-the-sign-in-the-glass"] = (s, (
        "Glurp looks from the three-ringed logo on their screen to the three rings in their crystal ball, "
        "and back again, eyebrow raised: that is not a coincidence."))

    # ---- Chapter 6: the hall of the horde
    s = Scene(110, 48)
    for x in range(8, 104, 16):  # pillars
        s.frame(x, 1, 4, s.floor - 1, "stone")
    s.frame(39, 2, 32, 8, "6")  # Orkestera banner over the door, teal
    for k, nx in enumerate(range(42, 68, 6)):
        s.stamp(nx, 3 + (k % 2), ["..99", "..9.", "999.", "99.."])
    # two tiers of desks, an agent busy at each
    for row, (desk_y, xs) in enumerate(((24, (2, 18, 74, 90)), (34, (6, 22, 70, 86)))):
        for x in xs:
            s.stamp(x + 2, desk_y - 10, AGENT)
            s.screen(x + 9, desk_y - 8, 7, 8, [(0, 2, "S"), (0, 3, "M"), (0, 2, "9")], step=1)
            s.desk(x, desk_y, 17, 6 if row == 0 else 6)
    # Glorp on the platform, baton high, notes above the head
    s.frame(38, s.floor - 4, 34, 4, "8")
    s.box(39, s.floor - 3, 32, 1, "6")
    s.stamp(36, s.floor - 4 - 36, glorp_baton_up(), CONDUCT)
    out["06-the-hall-of-the-horde"] = (s, (
        "In a long hall, agents work at desk after desk while Glorp, an indigo ork in a teal coat, stands on a raised "
        "platform with baton held high, conducting the horde, music notes floating above his head."))

    # ---- Chapter 6: the argument at family dinner
    s = Scene(110, 48)
    tower_wall(s)
    table_y = s.floor - 10
    # Grandmother Orgle at the head of the table, keeping score
    gx = 43
    s.stamp(gx, table_y - 22, [r for r in BASE[:18]], GRANNY)
    s.stamp(gx + 6, table_y - 25, ["..KKKKK..", ".KWWWWWK.", "KWWMWWWMK", ".KKKKKKK."], {"M": "M"})
    spectacles(s, gx, table_y - 22)
    s.frame(gx + 1, table_y - 9, 22, 9, "wood")
    s.box(gx + 2, table_y - 8, 20, 7, "t")
    for k in range(3):  # Glurp's tally on the left of the board
        s.box(gx + 3 + k * 2, table_y - 7, 1, 5, "S")
    s.box(gx + 2, table_y - 5, 7, 1, "S")
    for k in range(3):  # Glorp's tally on the right
        s.box(gx + 14 + k * 2, table_y - 7, 1, 5, "9")
    s.box(gx + 13, table_y - 5, 7, 1, "9")
    s.box(gx + 11, table_y - 8, 1, 7, "c")
    # Glurp points across the table; Glorp shrugs, notes above the head
    s.stamp(4, table_y - 18, glurp_point()[:19])
    s.stamp(72, 1, glorp_shrug(), CONDUCT)
    s.desk(0, table_y, 110, 10)
    s.box(1, table_y + 1, 108, 1, "W")
    s.stamp(30, table_y - 8, PANCAKES)
    s.stamp(18, table_y - 5, MUG)
    s.stamp(100, table_y - 5, MUG)
    s.stamp(64, table_y - 7, CANDLE)
    out["06-the-family-dinner"] = (s, (
        "At family dinner Glurp points across the table at Glorp, who shrugs with a baton in hand, while "
        "Grandmother Orgle sits between them behind a stack of pancakes and keeps score on a tally board."))

    # ---- Chapter 7: the great hall of chatter
    s = Scene(110, 48)
    s.box(0, 1, 110, 2, "wood")
    s.box(0, 3, 110, 1, "K")
    s.stamp(20, 4, ORK_BOT)
    table_y = s.floor - 8
    cast = [
        (2, elf(), None, "S"),
        (24, dwarf(), None, "M"),
        (46, troll(), None, "Y"),
        (68, pib_rows(), PIB, "S"),
        (88, BASE, None, "J"),
    ]
    for k, (x, rows, remap, bubble) in enumerate(cast):
        s.stamp(x, table_y - len(rows[:19]) + 0, rows[:19], remap)
    for k, (x, rows, remap, bubble) in enumerate(cast):
        bx, by = x + 6 + (k % 2) * 2, 8 + (k % 2) * 1
        s.frame(bx, by - 2, 12, 5, "t")
        s.box(bx + 2, by, 7 - (k % 3), 1, bubble)
        s.put(bx + 2, by + 3, "K")
    s.desk(0, table_y, 110, 8)
    for k, (x, rows, remap, bubble) in enumerate(cast):
        s.frame(x + 5, table_y - 6, 14, 7, "U")
        s.box(x + 6, table_y - 5, 12, 5, "t")
        s.box(x + 8, table_y - 3, 6, 1, bubble)
    out["07-the-hall-of-chatter"] = (s, (
        "The Discord regulars at their laptops along one long table: an elf, a dwarf, a gentle troll, Pib and Glurp, "
        "each with a chat bubble overhead, while Ork Bot sits in the rafters like a helpful gremlin."))

    # ---- Chapter 8: curtain call
    s = Scene(110, 48)
    tower_wall(s)
    back = s.floor - 8
    s.box(0, back, 110, 1, "c")
    s.stamp(4, back - 25, glorp_side(), CONDUCT)
    s.stamp(30, back - 25, BASE, GRANNY)
    s.stamp(30 + 6, back - 28, ["..KKKKK..", ".KWWWWWK.", "KWWMWWWMK", ".KKKKKKK."])
    s.stamp(56, back - 27, troll())
    s.stamp(82, back - 25, elf())
    s.stamp(4, 2, NOTE, CONDUCT)
    s.stamp(17, 1, NOTE, CONDUCT)
    s.stand(goblin(), 2, GOBLIN)
    for bx, by in ((1, 21), (17, 19), (6, 17)):
        s.stamp(bx, by, BEE)
    s.stand(pib_rows(), 18, PIB)
    s.glurp("meter", 44)
    s.stand(dwarf(), 70)
    s.stand(DUCK, 94)
    s.stamp(96, 2, ORK_BOT)
    out["08-curtain-call"] = (s, (
        "The whole cast together in the tower: Glorp, Grandmother Orgle, the troll and the elf at the back; the "
        "bee-keeping goblin, Pib, Glurp with their token gauge, the dwarf and Sir Quackington in front; Ork Bot "
        "peeking down from above."))
    return out


def hold_front(prop):
    """BASE holding a prop in front of the belly with both hands."""
    s = sprite(24, 25)
    s.stamp(0, 0, no_hands())
    w, h = len(prop[0]), len(prop)
    px, py = 12 - w // 2, 21 - h
    s.stamp(px, py, prop)
    for hx in (px - 2, px + w - 1):
        s.frame(hx, py + h - 4, 3, 3, "G")
    return s.cells()


def spectacles(s, x, y):
    """Round rims over Glurp's eyes (row 5 of BASE); decorative, as the lore insists."""
    for ex in (x + 5, x + 14):
        s.put(ex, y + 5, "M")
        s.put(ex + 4, y + 5, "M")
        s.box(ex + 1, y + 4, 3, 1, "M")
        s.box(ex + 1, y + 6, 3, 1, "M")
    s.box(x + 10, y + 5, 4, 1, "M")


def pib_rows():
    s = sprite(24, 28)
    s.stamp(0, 3, BASE)
    s.stamp(6, 0, ["...KKKK...", "..KZZZZK..", ".KZDDDZZK.", "KZDZZZDZK."])
    return s.cells()


def elf():
    s = sprite(24, 25)
    b = [list(r) for r in BASE]
    for y, x in ((9, 6), (9, 17), (10, 6), (10, 7), (10, 16), (10, 17), (11, 7), (11, 16)):
        b[y][x] = "G"
    s.stamp(0, 0, b)
    s.stamp(0, 0, [
        "........KKKKKKKK........",
        "......KKTTFFTTTTKK......",
        ".....KTTFFTTTTTTTOK.....",
        "....KTTTTTTTTTTTTTOK....",
        "....KTO..........OTK....",
        "....KTO..........OTK....",
        "....KTK..........KTK....",
        "....KTK..........KTK....",
        "....KTK..........KTK....",
        "....KTK..........KTK....",
        "....KOK..........KOK....",
        "....KK............KK....",
    ])
    rows = s.cells()
    return [[ELF.get(c, c) if c not in ("T", "F", "O") else c for c in r] for r in rows]


def dwarf():
    s = sprite(24, 26)
    s.stamp(0, 1, BASE)
    s.stamp(4, 0, ["....KKKKKKKK....", "..KKUMMMMMMUKK..", ".KUMMMMMMMMMMUK.", "KWKUUUUUUUUUUKWK", "KWK..........KWK"])
    s.stamp(5, 10, [
        ".KBBK......KBBK.",
        ".KBBBKKKKKKBBBK.",
        "KBBkBBBBBBBBkBBK",
        "KBkBBBBkBBBBBkBK",
        "KBBBBkBBBBkBBBBK",
        ".KBBBBBBkBBBBBK.",
        "..KBBkBBBBBkBK..",
        "...KBBBBkBBBK...",
        "....KBBBBBBK....",
        ".....KKBBKK.....",
    ], {"k": "wood_hi"})
    rows = s.cells()
    return [[DWARF.get(c, c) for c in r] for r in rows]


def troll():
    b = [list(r) for r in BASE]
    tall = b[:16] + [b[15], b[16]] + b[16:]
    rows = [[TROLL.get(c, c) for c in r] for r in tall]
    return rows


def glorp_side():
    s = sprite(30, 25)
    s.stamp(0, 0, BASE)
    s.stamp(21, 11, BATON)
    return s.cells()


# --------------------------------------------------------------------------
# Spots and vignettes (transparent, 6 px cells)
# --------------------------------------------------------------------------

def build_spots():
    out = {}

    # ch1: Glurp typing at the anvil-desk
    s = Scene(40, 34, cell=6, framed=False, transparent=True, floor=34)
    desk_y = 22
    seat(s, BASE, 3, desk_y)
    s.desk(0, desk_y, 40, 12)
    s.keyboard(7, desk_y - 1, 14)
    typing_hands(s, 3, desk_y)
    s.screen(27, desk_y - 15, 13, 15, code_like())
    out["spot-glurp-typing"] = (s, "Glurp sits at their anvil-desk, typing by hand, a screen of code beside them.")

    # ch1: the jar of friendly bugs and Sir Quackington
    s = Scene(36, 26, cell=6, framed=False, transparent=True, floor=26)
    s.frame(3, 3, 14, 3, "U")
    s.frame(2, 5, 16, 20, "glass")
    s.box(3, 6, 1, 18, "c")
    s.frame(5, 12, 10, 5, "V")
    s.box(7, 14, 6, 1, "K")
    for bx, by, col in ((5, 8, "S"), (11, 9, "J"), (9, 19, "S"), (13, 21, "T"), (6, 21, "J")):
        s.stamp(bx, by, ["K.K", ".X.", "KXK"], {"X": col})
    s.stand(DUCK, 22, floor=25)
    s.shadow(0, 25, 34)
    out["spot-bug-jar-and-duck"] = (s, "A jar of friendly bugs with a blank label stands beside Sir Quackington, the rubber duck.")

    # ch2: a box of old cables, a crystal ball glowing inside
    s = Scene(40, 32, cell=6, framed=False, transparent=True, floor=32)
    s.orb(20, 12, 7)
    for pts, col in ((((6, 18), (2, 10), (5, 4)), "U"), (((32, 18), (37, 11), (33, 6)), "N"), (((12, 17), (10, 9)), "S")):
        s.limb(list(pts), fill=col, hand=None, width=1)
    s.frame(4, 17, 32, 14, "wood")
    s.box(5, 18, 30, 2, "wood_dk")
    s.box(2, 16, 9, 2, "wood_hi")
    s.box(29, 16, 9, 2, "wood_hi")
    s.box(1, 16, 1, 2, "K")
    s.box(38, 16, 1, 2, "K")
    s.box(19, 22, 3, 6, "wood_hi")
    out["spot-cable-box"] = (s, "A crystal ball with three glowing rings rises from an old cardboard box of tangled cables.")

    # ch2: the grumpy bee-keeping goblin
    s = Scene(34, 26, cell=6, framed=False, transparent=True, floor=25)
    s.stand(goblin(), 4, GOBLIN)
    s.frame(22, 10, 9, 15, "wood")
    for y in range(12, 24, 3):
        s.box(23, y, 7, 1, "wood_dk")
    s.box(21, 9, 11, 2, "wood_hi")
    for bx, by in ((22, 3), (28, 6), (19, 1), (2, 3), (25, 0)):
        s.stamp(bx, by, BEE)
    s.shadow(1, 25, 32)
    out["spot-goblin-and-bees"] = (s, "Glurp's neighbour, a grumpy goblin with a heavy frown, stands beside their beehive while bees buzz about.")

    # ch3: Glurp shrugs, bewildered
    s = Scene(34, 32, cell=6, framed=False, transparent=True, floor=31)
    s.stand(glurp_shrug(), 0, floor=31)
    s.stamp(2, 1, [".YY.", "Y..Y", "..Y.", ".Y..", "....", ".Y.."])
    s.stamp(28, 2, [".SS.", "S..S", "..S.", ".S..", "....", ".S.."])
    s.shadow(4, 31, 26)
    out["spot-glurp-shrugs"] = (s, "Glurp shrugs, palms up and one eyebrow raised, bewildered by how fast the agents work.")

    # ch4: Glurp reads the Book of Wounds by candlelight
    s = Scene(40, 30, cell=6, framed=False, transparent=True, floor=29)
    s.stand(glurp_read(), 0, floor=29)
    s.stamp(32, 16, CANDLE)
    s.frame(30, 24, 9, 5, "wood")
    s.shadow(1, 29, 38)
    out["spot-glurp-reading"] = (s, "Glurp reads the Book of Wounds, a scroll of five red-marked entries, by candlelight.")

    # ch5: Glurp casts healing with a wand
    s = Scene(38, 34, cell=6, framed=False, transparent=True, floor=33)
    s.stand(glurp_wand(), 0, floor=33)
    s.shadow(4, 33, 24)
    out["spot-glurp-wand"] = (s, "Glurp raises a wand tipped with a lime star, casting a small healing spell over their wounds.")

    # ch6: Glurp walks across the valley with the ball under one arm
    s = Scene(40, 32, cell=6, framed=False, transparent=True, floor=31)
    s.box(0, 31, 40, 1, "c")
    s.box(10, 30, 14, 1, "c")
    s.stand(glurp_walk(), 10, floor=31)
    s.orb(9, 21, 5)
    s.frame(8, 23, 3, 3, "G")
    s.stamp(33, 22, [".D.", "DSD", ".D.", ".D."])
    s.stamp(2, 27, [".S.", "SDS", ".D."])
    for x in (36, 38):
        s.put(x, 30, "c")
    out["spot-glurp-walking"] = (s, "Glurp walks across the valley with their crystal ball tucked under one arm, rings glowing.")

    # ch7: Ork Bot perched on the chat window, under the rafters
    s = Scene(36, 34, cell=6, framed=False, transparent=True, floor=34)
    s.box(0, 1, 36, 3, "wood")
    s.box(0, 0, 36, 1, "K")
    s.box(0, 4, 36, 1, "K")
    for x in (6, 28):
        s.box(x, 5, 1, 6, "c")
    s.frame(2, 13, 32, 20, "t")
    s.box(3, 14, 30, 2, "c")
    for k, ch in enumerate("RTS"):
        s.put(4 + 2 * k, 14, ch)
    msgs = [(4, 18, 14, "S"), (14, 21, 16, "J"), (4, 24, 10, "S"), (12, 27, 18, "J"), (12, 29, 12, "J")]
    for x, y, w, col in msgs:
        s.box(x, y, w, 1, col)
    s.stamp(20, 3, ORK_BOT)
    out["spot-ork-bot"] = (s, "Ork Bot, a small purple gremlin with lime eyes, perches on a chat window under the rafters, where Glurp's lime messages and its purple answers take turns.")

    # ch8: the desk at night
    s = Scene(40, 32, cell=6, framed=False, transparent=True, floor=32)
    s.screen(4, 7, 20, 15, [(0, 2, S), (3, 9, M), (0, 2, S)])
    s.box(13, 22, 3, 2, "U")
    s.stand(DUCK, 9, floor=7)
    s.desk(0, 24, 40, 8)
    s.frame(27, 13, 8, 11, "glass")
    s.box(27, 12, 8, 2, "U")
    s.box(26, 12, 1, 2, "K")
    s.box(35, 12, 1, 2, "K")
    s.stamp(29, 17, ["K.K", ".X.", "KXK"], {"X": "S"})
    s.stamp(30, 20, ["K.K", ".X.", "KXK"], {"X": "J"})
    s.stamp(1, 18, MUG)
    out["spot-desk-at-night"] = (s, "Glurp's desk at night: Sir Quackington keeps watch from the top of the monitor, beside the jar of friendly bugs and a cold mug of tea.")

    # ---- vignettes
    s = Scene(36, 14, cell=6, framed=False, transparent=True, floor=13)
    s.desk(2, 2, 18, 11)
    s.box(0, 13, 36, 1, "c")
    s.stamp(24, 9, COIN)
    for x, y in ((29, 12), (31, 11), (33, 12)):
        s.put(x, y, "M")
    out["vignette-last-token"] = (s, "A single gold token rolls away under the desk.")

    s = Scene(34, 22, cell=6, framed=False, transparent=True, floor=22)
    s.ball(17, 6)
    for pts in (((4, 6), (2, 9), (2, 12)), ((30, 6), (32, 9), (32, 12))):
        for x, y in line_cells(pts[0], pts[1]) + line_cells(pts[1], pts[2]):
            s.put(x, y, "S")
    out["vignette-humming-ball"] = (s, "The crystal ball hums on its stand, its inner ring spinning fast.")

    s = Scene(48, 32, cell=6, framed=False, transparent=True, floor=31)
    s.frame(2, 2, 5, 29, "wood")
    for y in range(5, 29, 2):
        s.put(6, y, "K")
        s.put(5, y, "wood_dk")
    s.mark(4.5 + 4.5, 12, 4)
    s.stand(glurp_celebrate(), 12, floor=31)
    s.shadow(10, 31, 36)
    out["vignette-new-notch"] = (s, "Glurp celebrates beside the notched doorframe, where a tiny three-ringed circle is carved beside the newest notch.")

    s = Scene(44, 30, cell=6, framed=False, transparent=True, floor=29)
    s.stand(glurp_wave(), 0, floor=29)
    s.stamp(30, 14, [
        "KKKKKKKKKKK",
        "KwwwwwwwwwK",
        "KKKKKKKKKKK",
        ".KdK...KdK.",
        ".KdK...KdK.",
        ".KdKKKKKdK.",
        ".KdddddddK.",
        ".KdKKKKKdK.",
        ".KdK...KdK.",
        ".KdK...KdK.",
        ".KKK...KKK.",
        "...........",
        "...........",
        "...........",
        "...........",
    ], {"w": "wood_hi", "d": "wood"})
    s.shadow(2, 29, 42)
    out["vignette-pull-up-a-stool"] = (s, "Glurp waves a newcomer over to an empty stool.")

    s = Scene(30, 22, cell=6, framed=False, transparent=True, floor=22)
    s.ball(15, 6)
    for x, y, ch in ((3, 6, "T"), (26, 4, "S"), (5, 16, "Y"), (25, 15, "T"), (2, 11, "S"), (28, 10, "Y")):
        s.put(x, y, ch)
    out["vignette-the-end"] = (s, "The crystal ball glows on its stand, three rings turning.")
    return out


def code_like():
    return [(0, 2, S), (2, 6, M), (2, 8, M), (3, 4, "T"), (2, 7, M), (0, 2, S)]


# --------------------------------------------------------------------------
# Standalone pose sheet entries (transparent, 8 px cells), for reuse
# --------------------------------------------------------------------------

def build_poses():
    out = {}

    def one(name, rows, alt, remap=None):
        h, w = len(rows), max(len(r) for r in rows)
        s = Scene(w, h, cell=8, framed=False, transparent=True, floor=h)
        s.stamp(0, 0, rows, remap)
        out[f"poses/{name}"] = (s, alt)

    one("glurp-celebrate", glurp_celebrate(), "Glurp celebrates, both arms up, grinning, confetti in the air.")
    one("glurp-shrug", glurp_shrug(), "Glurp shrugs, palms up, one eyebrow raised.")
    one("glurp-wave", glurp_wave(), "Glurp waves hello with one hand.")
    one("glurp-wand", glurp_wand(), "Glurp raises a wand tipped with a lime star.")
    one("glurp-read", glurp_read(), "Glurp reads an open scroll held in both hands.")
    one("glurp-walk", glurp_walk(), "Glurp walks, one boot lifted mid-stride.")
    one("glurp-point", glurp_point(), "Glurp points to the right, making a point.")
    one("glorp-baton-up", glorp_baton_up(), "Glorp, indigo in a teal coat, raises both arms and a baton, music notes above the head.", CONDUCT)
    one("glorp-shrug", glorp_shrug(), "Glorp, indigo in a teal coat, shrugs with a small baton in one palm, music notes above the head.", CONDUCT)

    s = Scene(32, 26, cell=8, framed=False, transparent=True, floor=26)
    seat(s, BASE, 4, 20)
    s.desk(0, 20, 32, 6)
    s.keyboard(9, 19, 14)
    typing_hands(s, 4, 20)
    out["poses/glurp-typing"] = (s, "Glurp sits at a desk, typing.")

    s = Scene(34, 22, cell=8, framed=False, transparent=True, floor=22)
    s.stamp(5, 2, close_eyes(BASE)[:14])
    s.limb([(3, 13), (15, 14)], hand=None, over=True)
    s.limb([(27, 13), (17, 14)], hand=None, over=True)
    s.desk(0, 16, 34, 6)
    s.stamp(28, 0, ZZZ)
    out["poses/glurp-sleep"] = (s, "Glurp sleeps slumped over a desk, eyes closed.")
    return out


def main(dest=None):
    dest = pathlib.Path(dest) if dest else ROOT / "images"
    (dest / "poses").mkdir(parents=True, exist_ok=True)
    every = {**plates(), **build_tableaus(), **build_spots(), **build_poses()}
    for name, (scene, alt) in every.items():
        (dest / f"{name}.svg").write_text(scene.svg(alt))
        print(name, "|", alt)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
