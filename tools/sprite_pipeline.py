"""Non-destructive art pipeline for The Last Skyfarer.

Reads the untouched source sheets in art_source/ (copies of the creative
director's originals) and writes processed, transparent game-ready PNGs into
assets/. Source files are opened read-only and never modified.

Run from the repository root:  python3 -I tools/sprite_pipeline.py
"""
import os
import sys
from collections import deque

import numpy as np
from PIL import Image, ImageFilter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "art_source")
OUT = os.path.join(ROOT, "assets")


def src(*p):
    return os.path.join(SRC, *p)


def out(*p):
    path = os.path.join(OUT, *p)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


# ---------------------------------------------------------------------------
# Background removal helpers
# ---------------------------------------------------------------------------

def paper_mask(rgb, min_bright=150, max_sat=48):
    """Pixels that look like sheet paper / grid lines (light, unsaturated)."""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx = np.maximum(np.maximum(r, g), b)
    mn = np.minimum(np.minimum(r, g), b)
    bright = (r + g + b) / 3.0
    return (bright > min_bright) & ((mx - mn) < max_sat)


def flood_from_edges(cand):
    """Flood fill candidate background pixels connected to the image border."""
    h, w = cand.shape
    bg = np.zeros_like(cand, dtype=bool)
    q = deque()
    for x in range(w):
        for y in (0, h - 1):
            if cand[y, x] and not bg[y, x]:
                bg[y, x] = True
                q.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if cand[y, x] and not bg[y, x]:
                bg[y, x] = True
                q.append((y, x))
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and cand[ny, nx] and not bg[ny, nx]:
                bg[ny, nx] = True
                q.append((ny, nx))
    return bg


def components(mask):
    """Label 4-connected components. Returns (labels, sizes, bboxes)."""
    h, w = mask.shape
    labels = np.zeros((h, w), dtype=np.int32)
    sizes = [0]
    boxes = [None]
    cur = 0
    for sy in range(h):
        row = mask[sy]
        for sx in np.nonzero(row)[0]:
            if labels[sy, sx]:
                continue
            cur += 1
            q = deque([(sy, sx)])
            labels[sy, sx] = cur
            n = 0
            x0, y0, x1, y1 = sx, sy, sx, sy
            while q:
                y, x = q.popleft()
                n += 1
                x0, x1, y0, y1 = min(x0, x), max(x1, x), min(y0, y), max(y1, y)
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not labels[ny, nx]:
                        labels[ny, nx] = cur
                        q.append((ny, nx))
            sizes.append(n)
            boxes.append((x0, y0, x1 + 1, y1 + 1))
    return labels, sizes, boxes


def cutout(img, keep="largest", min_bright=150, max_sat=48, keep_ratio=0.02,
           drop_boxes=(), paper_blob=500):
    """Remove the paper background from a PIL RGB image region.

    keep="largest" keeps the largest foreground blob plus any blob larger than
    keep_ratio * largest that overlaps its bounding box (scarf ends, etc.).
    drop_boxes: (x0,y0,x1,y1) regions whose pixels are cleared first
    (used to drop the companion who sits inside some of Kieran's cells).
    """
    rgb = np.asarray(img.convert("RGB")).astype(np.int32)
    cand = paper_mask(rgb, min_bright, max_sat)
    # Also accept anything close to this cell's own paper colour (aged,
    # yellowed paper near the sheet edges is more saturated than the centre).
    border = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]])
    paper = np.median(border, axis=0)
    cand |= np.abs(rgb - paper).max(axis=2) < 34
    bg = flood_from_edges(cand)
    # Paper regions sealed off by grid lines or labels are not edge-connected;
    # treat any large paper-coloured blob as background as well.
    plabels, psizes, _ = components(cand & ~bg)
    big_paper = [i for i in range(1, len(psizes)) if psizes[i] > paper_blob]
    if big_paper:
        bg |= np.isin(plabels, big_paper)
    fg = ~bg
    for (x0, y0, x1, y1) in drop_boxes:
        fg[y0:y1, x0:x1] = False
    # Drop the soft ground shadow: greyish-beige, mid brightness, low sat.
    labels, sizes, boxes = components(fg)
    if len(sizes) <= 1:
        return None
    if keep == "all":
        keep_ids = [i for i in range(1, len(sizes)) if sizes[i] > 40]
    else:
        big = int(np.argmax(sizes[1:])) + 1
        bx = boxes[big]
        keep_ids = [big]
        for i in range(1, len(sizes)):
            if i == big or sizes[i] < max(30, keep_ratio * sizes[big]):
                continue
            b = boxes[i]
            if b[0] < bx[2] and b[2] > bx[0] and b[1] < bx[3] and b[3] > bx[1]:
                keep_ids.append(i)
    alpha = np.isin(labels, keep_ids)
    a = Image.fromarray((alpha * 255).astype(np.uint8))
    # Soften the hard edge slightly so the sprite sits in painted scenes.
    a = a.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.6))
    rgba = img.convert("RGBA")
    rgba.putalpha(a)
    return rgba


def outline_cutout(img, line_thresh=212, gap=2, keep="all", min_blob=60, drop_boxes=()):
    """Cut out Piko: his fur is nearly the same cream as the paper, so we rely
    on his drawn outline. Dark line pixels are thickened to close sketchy gaps,
    the paper outside them is flood-filled from the border, and the result is
    the region enclosed by the outline."""
    rgb = np.asarray(img.convert("RGB")).astype(np.int32)
    bright = rgb.mean(axis=2)
    lines = Image.fromarray(((bright < line_thresh) * 255).astype(np.uint8))
    lines = np.asarray(lines.filter(ImageFilter.MaxFilter(gap * 2 + 1))) > 0
    bg = flood_from_edges(~lines)
    fg = ~bg
    for (x0, y0, x1, y1) in drop_boxes:
        fg[y0:y1, x0:x1] = False
    labels, sizes, boxes = components(fg)
    if keep == "all":
        ids = [i for i in range(1, len(sizes)) if sizes[i] > min_blob]
    else:
        ids = [int(np.argmax(sizes[1:])) + 1]
    alpha = np.isin(labels, ids)
    a = Image.fromarray((alpha * 255).astype(np.uint8))
    a = a.filter(ImageFilter.MinFilter(gap * 2 - 1)).filter(ImageFilter.GaussianBlur(0.7))
    rgba = img.convert("RGBA")
    rgba.putalpha(a)
    return rgba


def trim(img, pad=2):
    bbox = img.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
    if not bbox:
        return img
    x0, y0, x1, y1 = bbox
    return img.crop((max(0, x0 - pad), max(0, y0 - pad),
                     min(img.width, x1 + pad), min(img.height, y1 + pad)))


def white_cutout(img, thresh=238):
    """For clean white-background sheets (emotion sheet, asset atlas)."""
    rgb = np.asarray(img.convert("RGB")).astype(np.int32)
    cand = (rgb.min(axis=2) > thresh)
    bg = flood_from_edges(cand)
    a = Image.fromarray(((~bg) * 255).astype(np.uint8))
    a = a.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.5))
    rgba = img.convert("RGBA")
    rgba.putalpha(a)
    return rgba


# ---------------------------------------------------------------------------
# Kieran animation frames (from "Kieran Thorn Actions.jpeg", a gridded sheet)
# ---------------------------------------------------------------------------

KIERAN_ROWS = {
    # name: (y0, y1, x0, x1, count)
    "idle": (34, 142, 44, 553, 5),
    "walk": (155, 265, 44, 658, 6),
    "run": (291, 403, 44, 656, 6),
    "jump": (155, 265, 748, 1155, 4),
}

FRAME_H = 128  # every Kieran frame is placed on a shared canvas


def build_kieran():
    sheet = Image.open(src("characters", "Kieran Thorn Actions.jpeg"))
    report = []
    for name, (y0, y1, x0, x1, n) in KIERAN_ROWS.items():
        cw = (x1 - x0) / n
        frames = []
        for i in range(n):
            cx0 = int(round(x0 + i * cw)) + 4
            cx1 = int(round(x0 + (i + 1) * cw)) - 3
            cell = sheet.crop((cx0, y0 + 4, cx1, y1 - 3))
            drop = ()
            if name == "idle":
                # Piko sits low on the right of each idle cell
                drop = ((int(cell.width * 0.62), int(cell.height * 0.70), cell.width, cell.height),)
            res = cutout(cell, drop_boxes=drop)
            frames.append(res)
        # Shared canvas so feet stay planted: align bottoms, center horizontally
        w = max(f.width for f in frames)
        h = max(f.height for f in frames)
        strip = Image.new("RGBA", (w * n, h), (0, 0, 0, 0))
        for i, f in enumerate(frames):
            strip.paste(f, (i * w, 0), f)
        strip.save(out("characters", "kieran", f"kieran_{name}.png"))
        report.append(f"kieran_{name}.png  frames={n} frame_size={w}x{h}")
    # The gliding row's poses straddle the drawn cell borders, so detect the
    # figures across the whole row instead of slicing fixed cells.
    row = cutout(sheet.crop((48, 604, 576, 716)), keep="all")
    a = np.asarray(row.getchannel("A")) > 40
    _, sizes, boxes = components(a)
    figs = sorted([boxes[i] for i in range(1, len(sizes))
                   if sizes[i] > 3000 and boxes[i][0] > 10], key=lambda b: b[0])
    frames = [row.crop((b[0], 0, b[2], row.height)) for b in figs]
    w = max(f.width for f in frames)
    strip = Image.new("RGBA", (w * len(frames), row.height), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        strip.paste(f, (i * w + (w - f.width), 0), f)
    strip.save(out("characters", "kieran", "kieran_glide.png"))
    report.append(f"kieran_glide.png  frames={len(frames)} frame_size={w}x{row.height}")
    return report


# ---------------------------------------------------------------------------
# Portraits
# ---------------------------------------------------------------------------

def build_portraits():
    rep = []
    emo = Image.open(src("characters", "Kieran Thorn Emotions Sheet.png"))
    # 5 columns x 2 rows of busts on top, 4 larger busts beneath
    cols = 5
    names = {
        (0, 0): "neutral", (1, 0): "smile", (2, 0): "laugh", (3, 0): "doubt",
        (4, 0): "angry", (0, 1): "surprised", (1, 1): "worried",
        (2, 1): "bored", (3, 1): "skeptical", (4, 1): "content",
    }
    cw = emo.width / cols
    for (c, r), nm in names.items():
        box = (int(c * cw), int(r * 305), int((c + 1) * cw), int(r * 305 + 310))
        p = white_cutout(emo.crop(box))
        p = trim(p)
        p.thumbnail((256, 256), Image.LANCZOS)
        p.save(out("portraits", f"kieran_{nm}.png"))
        rep.append(f"portraits/kieran_{nm}.png")
    # bottom-right "looking up / hopeful"
    p = trim(white_cutout(emo.crop((1190, 610, 1536, 1024))))
    p.thumbnail((256, 256), Image.LANCZOS)
    p.save(out("portraits", "kieran_hopeful.png"))
    rep.append("portraits/kieran_hopeful.png")

    piko = Image.open(src("characters", "Piko Turnaround.jpeg"))
    faces = {"curious": (360, 50, 510, 215), "happy": (515, 50, 680, 215),
             "surprised": (690, 50, 850, 215), "sleepy": (815, 70, 1010, 215),
             "determined": (1010, 50, 1180, 215)}
    for nm, box in faces.items():
        p = outline_cutout(piko.crop(box), keep="largest")
        p = trim(p)
        p.thumbnail((256, 256), Image.LANCZOS)
        p.save(out("portraits", f"piko_{nm}.png"))
        rep.append(f"portraits/piko_{nm}.png")

    tessa = Image.open(src("characters", "Tessa Reed Turnaround.jpeg"))
    p = cutout(tessa.crop((60, 60, 290, 330)), min_bright=150, max_sat=40)
    p = trim(p)
    p.thumbnail((256, 256), Image.LANCZOS)
    p.save(out("portraits", "tessa_neutral.png"))
    rep.append("portraits/tessa_neutral.png")

    elias = Image.open(src("characters", "Elias Thorn Final Years Turnaround.jpeg"))
    p = cutout(elias.crop((40, 40, 330, 360)), min_bright=150, max_sat=40)
    p = trim(p)
    p.thumbnail((256, 256), Image.LANCZOS)
    p.save(out("portraits", "elias_portrait.png"))
    rep.append("portraits/elias_portrait.png")
    return rep


# ---------------------------------------------------------------------------
# Full-body NPC / companion sprites
# ---------------------------------------------------------------------------

def build_bodies():
    rep = []
    piko = Image.open(src("characters", "Piko Turnaround.jpeg"))
    # Side view (facing left) including the floating tail
    p = outline_cutout(piko.crop((70, 300, 545, 800)), min_blob=400,
                       drop_boxes=((0, 0, 262, 262), (0, 0, 349, 140), (0, 0, 316, 192)))
    p = trim(p)
    p.save(out("characters", "piko", "piko_side.png"))
    rep.append(f"piko_side.png {p.size}")
    # Front view (for close-ups / journal)
    p = trim(outline_cutout(piko.crop((80, 70, 436, 495)), min_blob=400,
                              drop_boxes=((345, 230, 356, 425), (250, 0, 356, 165), (290, 360, 356, 425))))
    p.save(out("characters", "piko", "piko_front.png"))
    rep.append(f"piko_front.png {p.size}")

    tessa = Image.open(src("characters", "Tessa Reed Turnaround.jpeg"))
    p = trim(cutout(tessa.crop((620, 60, 800, 720)), min_bright=150, max_sat=40))
    p.save(out("characters", "tessa", "tessa_side.png"))
    rep.append(f"tessa_side.png {p.size}")
    p = trim(cutout(tessa.crop((60, 60, 290, 720)), min_bright=150, max_sat=40))
    p.save(out("characters", "tessa", "tessa_front.png"))
    rep.append(f"tessa_front.png {p.size}")
    return rep


# ---------------------------------------------------------------------------
# Environment props from the "Eight Realms" Brindle Isle panel
# ---------------------------------------------------------------------------

def build_environment():
    rep = []
    atlas = Image.open(src("environments", "Eight Realms_ Platformer Asset Atlas.png")).convert("RGB")
    panel = atlas.crop((0, 48, 384, 412))
    cut = white_cutout(panel, thresh=232)
    a = np.asarray(cut.getchannel("A")) > 40
    labels, sizes, boxes = components(a)
    items = [(boxes[i], sizes[i]) for i in range(1, len(sizes)) if sizes[i] > 250]
    items.sort(key=lambda t: (t[0][1] // 40, t[0][0]))
    for idx, (b, s) in enumerate(items):
        piece = cut.crop(b)
        piece.save(out("environments", "brindle", f"brindle_{idx:02d}.png"))
        rep.append(f"brindle_{idx:02d}.png box={b} px={s}")
    # Panorama strip for the far parallax layer
    pano = atlas.crop((12, 418, 376, 506))
    pano = pano.resize((pano.width * 4, pano.height * 4), Image.LANCZOS).filter(ImageFilter.GaussianBlur(1.6))
    pano.save(out("environments", "brindle", "brindle_panorama.png"))
    rep.append("brindle_panorama.png")
    return rep


def build_maps():
    m = Image.open(os.path.join(SRC, "maps", "Windrest Village_ Brindle Isle Map.png"))
    m.convert("RGB").save(out("ui", "windrest_map.jpg"), quality=90)
    a = Image.open(os.path.join(SRC, "maps", "Brindle Isle_ A Skybound Explorer\u2019s Atlas Elias's Journal.png"))
    a.convert("RGB").save(out("ui", "brindle_atlas.jpg"), quality=88)
    k = Image.open(src("characters", "Gemini_Generated_Image_clpuvvclpuvvclpu.jpeg"))
    k.convert("RGB").save(out("ui", "title_keyart.jpg"), quality=90)
    return ["ui/windrest_map.jpg", "ui/brindle_atlas.jpg", "ui/title_keyart.jpg"]


def build_ground():
    """Split the long Brindle platform into caps + a tileable middle so the
    village ground can be any length (used with a horizontal NinePatchRect)."""
    g = Image.open(out("environments", "brindle", "brindle_00.png"))
    top = g.crop((0, 7, g.width, 58))
    top = top.resize((top.width * 3, top.height * 3), Image.LANCZOS)
    top.save(out("environments", "brindle", "ground_strip.png"))
    # Seamless tile from the middle of the strip: cross-fade the ends so the
    # village ground can repeat without visible seams.
    mid = top.crop((150, 0, top.width - 150, top.height))
    blend = 60
    tile = mid.crop((0, 0, mid.width - blend, mid.height)).copy()
    right = mid.crop((mid.width - blend, 0, mid.width, mid.height))
    for x in range(blend):
        a = x / (blend - 1)
        col_r = right.crop((x, 0, x + 1, mid.height))
        col_l = tile.crop((x, 0, x + 1, mid.height))
        tile.paste(Image.blend(col_r, col_l, a), (x, 0))
    tile.save(out("environments", "brindle", "ground_tile.png"))
    top.crop((0, 0, 150, top.height)).save(out("environments", "brindle", "ground_cap_left.png"))
    top.crop((top.width - 150, 0, top.width, top.height)).save(out("environments", "brindle", "ground_cap_right.png"))
    g.crop((0, 66, 106, g.height)).save(out("environments", "brindle", "platform_small_a.png"))
    g.crop((114, 66, g.width, g.height)).save(out("environments", "brindle", "platform_small_b.png"))
    return ["ground_strip.png", "platform_small_a.png", "platform_small_b.png"]


def turnaround_views(path, min_bright=150, max_sat=40):
    """Return the full-body figures of a 5-view turnaround sheet, left->right."""
    sheet = Image.open(path).convert("RGB")
    body = sheet.crop((0, 40, sheet.width, sheet.height - 70))
    cut = cutout(body, keep="all", min_bright=min_bright, max_sat=max_sat)
    a = np.asarray(cut.getchannel("A")) > 40
    _, sizes, boxes = components(a)
    figs = sorted([boxes[i] for i in range(1, len(sizes)) if sizes[i] > 8000], key=lambda b: b[0])
    return [trim(cut.crop(b)) for b in figs]


def build_standins():
    """Stand-in villagers (pending the creative director's casting approval)."""
    rep = []
    for key, fname in (("bram", "Bram Holloway Turnaround.jpeg"),
                       ("elara", "Elara Greenborough Turnaround.jpeg")):
        views = turnaround_views(src("characters", fname))
        front, side = views[0], views[2]
        side.save(out("characters", key, f"{key}_side.png"))
        front.save(out("characters", key, f"{key}_front.png"))
        head = front.crop((0, 0, front.width, int(front.height * 0.36)))
        head = trim(head)
        head.thumbnail((256, 256), Image.LANCZOS)
        head.save(out("portraits", f"{key}_neutral.png"))
        rep.append(f"{key}: {len(views)} views, side={side.size}")
    return rep


WORKSHOP_PIECES = {  # index in the Starfall Basin panel -> name
    17: "bookshelf", 8: "armillary", 9: "armillary_large", 19: "chest",
    14: "lantern", 18: "lantern_b", 3: "desk",
}


def build_workshop_props():
    """Brass instruments, shelves and lanterns for Elias's workshop, taken from
    the Starfall Basin panel of the asset atlas."""
    atlas = Image.open(src("environments", "Eight Realms_ Platformer Asset Atlas.png")).convert("RGB")
    panel = atlas.crop((770, 560, 1150, 905))
    cut = white_cutout(panel, thresh=232)
    a = np.asarray(cut.getchannel("A")) > 40
    _, sizes, boxes = components(a)
    items = sorted([(boxes[i], sizes[i]) for i in range(1, len(sizes)) if sizes[i] > 250],
                   key=lambda t: (t[0][1] // 40, t[0][0]))
    rep = []
    for idx, name in WORKSHOP_PIECES.items():
        b = items[idx][0]
        cut.crop(b).save(out("environments", "workshop", f"{name}.png"))
        rep.append(f"workshop/{name}.png")
    return rep


def build_upscaled():
    """Pre-upscale the small atlas props 4x with Lanczos + light sharpening so
    they hold up at 1080p better than runtime bilinear scaling."""
    rep = []
    for folder in ("brindle", "workshop"):
        d = os.path.join(OUT, "environments", folder)
        for f in sorted(os.listdir(d)):
            if not f.endswith(".png") or f.startswith("ground_strip") or f.endswith("_4x.png") \
                    or f.startswith("brindle_panorama"):
                continue
            im = Image.open(os.path.join(d, f)).convert("RGBA")
            big = im.resize((im.width * 4, im.height * 4), Image.LANCZOS)
            rgb = big.convert("RGB").filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=2))
            rgb.putalpha(big.getchannel("A"))
            rgb.save(os.path.join(d, f.replace(".png", "_4x.png")))
            rep.append(f"{folder}/{f} -> 4x {big.size}")
    return rep


if __name__ == "__main__":
    # Afterwards run tools/hd_pipeline.py, which replaces the game-size sprites
    # (Kieran, NPCs, Piko, props, ground) with high-definition versions. The
    # old Lanczos "upscale" step is kept for reference but no longer default.
    steps = sys.argv[1:] or ["kieran", "portraits", "bodies", "environment", "ground", "standins", "workshop", "maps"]
    fn = {"kieran": build_kieran, "portraits": build_portraits, "bodies": build_bodies,
          "environment": build_environment, "maps": build_maps, "ground": build_ground, "standins": build_standins, "workshop": build_workshop_props, "upscale": build_upscaled}
    for s in steps:
        for line in fn[s]():
            print(line)

