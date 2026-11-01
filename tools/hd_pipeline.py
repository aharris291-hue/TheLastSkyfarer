"""High-definition sprite pass for The Last Skyfarer.

The source sheets are small (Kieran's animation frames are about 100 px
tall), so displaying them at game size blurred them. This pass:

1. Upscales the untouched sources 4x with Real-ESRGAN (tools/esrgan_upscale.py,
   cached in tools/cache/, never written over art_source/).
2. Finds each figure with the tuned 1x cut-out from sprite_pipeline.py and
   applies that mask, enlarged and cleaned, to the 4x image. The result has a
   fully opaque body with a thin anti-aliased edge instead of a soft,
   half-transparent fringe.
3. Writes game-ready PNGs into assets/ at the size they are displayed, so the
   engine draws them close to 1:1.

Run from the repository root:  python3 tools/hd_pipeline.py [step ...]
Steps: upscale, kieran, bodies, environment, ground, rotor (default: all)
"""
import os
import sys

import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, os.path.dirname(__file__))
import sprite_pipeline as sp  # noqa: E402

ROOT = sp.ROOT
CACHE = os.path.join(ROOT, "tools", "cache")

SOURCES = {
    # cache key: (source path under art_source, crop box at 1x or None)
    "atlas_brindle": (("environments", "Eight Realms_ Platformer Asset Atlas.png"), (0, 40, 384, 512)),
    "atlas_starfall": (("environments", "Eight Realms_ Platformer Asset Atlas.png"), (770, 560, 1150, 905)),
    "kieran_actions": (("characters", "Kieran Thorn Actions.jpeg"), None),
    "piko": (("characters", "Piko Turnaround.jpeg"), None),
    "tessa": (("characters", "Tessa Reed Turnaround.jpeg"), None),
    "bram": (("characters", "Bram Holloway Turnaround.jpeg"), None),
    "elara": (("characters", "Elara Greenborough Turnaround.jpeg"), None),
    "elias": (("characters", "Elias Thorn Final Years Turnaround.jpeg"), None),
}


def x4(key):
    path = os.path.join(CACHE, f"{key}_x4.png")
    if not os.path.exists(path):
        from esrgan_upscale import upscale
        parts, box = SOURCES[key]
        im = Image.open(sp.src(*parts)).convert("RGB")
        if box:
            im = im.crop(box)
        os.makedirs(CACHE, exist_ok=True)
        upscale(im).save(path)
    return Image.open(path).convert("RGB")


def build_upscale():
    for k in SOURCES:
        x4(k)
    return [f"cache/{k}_x4.png" for k in SOURCES]


# ---------------------------------------------------------------------------
# Mask helpers
# ---------------------------------------------------------------------------

def mask_of(rgba, thresh=110):
    return np.asarray(rgba.getchannel("A")) >= thresh


def apply_mask_4x(mask1, img4, clean_paper=True, feather=0.8):
    """Enlarge a 1x boolean mask to 4x, smooth its outline, strip paper
    coloured fringe pixels and return the 4x image as RGBA."""
    m = Image.fromarray((mask1 * 255).astype(np.uint8))
    m = m.resize((m.width * 4, m.height * 4), Image.BILINEAR).filter(ImageFilter.GaussianBlur(1.2))
    m4 = np.asarray(m) >= 128
    rgb = np.asarray(img4).astype(np.int32)
    if clean_paper:
        # Paper-coloured pixels near the outline are the old background.
        inner = np.asarray(Image.fromarray((m4 * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(9))) > 0
        band = m4 & ~inner
        bright = rgb.mean(axis=2)
        sat = rgb.max(axis=2) - rgb.min(axis=2)
        paperish = (bright > 196) & (sat < 52)
        m4 = m4 & ~(band & paperish)
        # Close the pinholes that removal can leave.
        m4 = np.asarray(Image.fromarray((m4 * 255).astype(np.uint8))
                        .filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3))) > 0
    a = Image.fromarray((m4 * 255).astype(np.uint8))
    if feather:
        a = a.filter(ImageFilter.GaussianBlur(feather))
    out = img4.convert("RGBA")
    out.putalpha(a)
    return out


def resize_rgba(img, size):
    """Premultiplied resize so edges never pick up a light or dark halo."""
    arr = np.asarray(img.convert("RGBA")).astype(np.float32) / 255.0
    a = arr[..., 3:4]
    pm = np.concatenate([arr[..., :3] * a, a], axis=2)
    chans = [Image.fromarray(pm[..., i]).resize(size, Image.LANCZOS) for i in range(4)]
    pm2 = np.stack([np.asarray(c) for c in chans], axis=2).clip(0, 1)
    a2 = pm2[..., 3:4]
    rgb = np.where(a2 > 1e-4, pm2[..., :3] / np.maximum(a2, 1e-4), 0)
    # Snap nearly opaque pixels to fully opaque so bodies never look faded.
    a2 = np.where(a2 > 0.92, 1.0, a2)
    return Image.fromarray((np.concatenate([rgb, a2], axis=2) * 255 + 0.5).astype(np.uint8), "RGBA")


def erase_grid_lines(cell, dark=150, frac=0.45, off=3):
    """Paint over the sheet's cell border lines (long dark rows/columns),
    keeping pixels where the figure is drawn over the line."""
    rgb = np.asarray(cell.convert("RGB")).astype(np.int32).copy()
    br = rgb.mean(axis=2)
    paper = np.median(np.concatenate([rgb[0], rgb[-1]]), axis=0)
    h, w = br.shape

    def paperlike(y, x):
        return 0 <= y < h and 0 <= x < w and br[y, x] > 175

    for y in range(h):
        if (br[y] < dark).mean() > frac:
            for x in np.nonzero(br[y] < dark + 30)[0]:
                if paperlike(y - off, x) or paperlike(y + off, x):
                    rgb[y, x] = paper
    br = rgb.mean(axis=2)
    for x in range(w):
        if (br[:, x] < dark).mean() > frac:
            for y in np.nonzero(br[:, x] < dark + 30)[0]:
                if paperlike(y, x - off) or paperlike(y, x + off):
                    rgb[y, x] = paper
    return Image.fromarray(rgb.astype(np.uint8))


# ---------------------------------------------------------------------------
# Kieran
# ---------------------------------------------------------------------------

KIERAN_ROWS = {
    # name: (y0, y1, x0, x1, count) on the 1x sheet. The jump row runs past
    # its cell border: the boots hang below it, so the crop goes to y=294.
    "idle": (34, 146, 44, 553, 5),
    "walk": (155, 270, 44, 658, 6),
    "run": (291, 408, 44, 656, 6),
    "jump": (155, 294, 748, 1155, 4),
}
KIERAN_OUT = 0.5     # 4x frames are written at 2x the sheet size
KIERAN_PAD = 6       # transparent margin under the feet (output px)


def cutout_4x(img4, drop=(), keep_all=False, line_br=125, gap=2, pocket=300):
    """Cut a figure out of an upscaled sheet using its dark ink outline.

    The upscaler draws a continuous dark outline around each figure, so the
    paper is flood-filled from the border and stops at that line. Paper
    pockets sealed inside (between an arm and the body) are removed when
    their colour matches this cell's paper. Light parts of the figure, like
    Kieran's shirt or trousers, stay because they are inside the outline."""
    clean = erase_grid_lines(img4, off=10)
    rgb = np.asarray(clean).astype(np.int32)
    br = rgb.mean(axis=2)
    lines = Image.fromarray(((br < line_br) * 255).astype(np.uint8))
    lines = np.asarray(lines.filter(ImageFilter.MaxFilter(gap * 2 + 1))) > 0
    bg = sp.flood_from_edges(~lines)
    border = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]])
    paper = np.median(border, axis=0)
    lab, sizes, _ = sp.components(~lines & ~bg)
    for i in range(1, len(sizes)):
        if sizes[i] < pocket:
            continue
        sel = lab == i
        mean = rgb[sel].mean(axis=0)
        if np.abs(mean - paper).max() < 16:
            bg |= sel
    fg = ~bg
    fg = np.asarray(Image.fromarray((fg * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(gap * 2 + 1))) > 0
    for (x0, y0, x1, y1) in drop:
        fg[y0:y1, x0:x1] = False
    lab, sizes, boxes = sp.components(fg)
    if len(sizes) <= 1:
        return img4.convert("RGBA")
    big = int(np.argmax(sizes[1:])) + 1
    bx = boxes[big]
    keep = [big]
    for i in range(1, len(sizes)):
        if i == big or sizes[i] < (200 if keep_all else max(120, 0.01 * sizes[big])):
            continue
        b = boxes[i]
        if keep_all or (b[0] < bx[2] and b[2] > bx[0] and b[1] < bx[3] and b[3] > bx[1]):
            keep.append(i)
    m = np.isin(lab, keep)
    a = Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8))
    out = img4.convert("RGBA")
    out.putalpha(a)
    return out


def _kieran_frame(sheet1, sheet4, box, drop=()):
    x0, y0, x1, y1 = box
    img4 = sheet4.crop((x0 * 4, y0 * 4, x1 * 4, y1 * 4))
    drop4 = tuple(tuple(v * 4 for v in d) for d in drop)
    rgba = cutout_4x(img4, drop4)
    return rgba, None


def build_kieran():
    sheet1 = Image.open(sp.src("characters", "Kieran Thorn Actions.jpeg")).convert("RGB")
    sheet4 = x4("kieran_actions")
    anims = {}
    for name, (y0, y1, x0, x1, n) in KIERAN_ROWS.items():
        cw = (x1 - x0) / n
        frames = []
        for i in range(n):
            cx0 = int(round(x0 + i * cw)) + 4
            cx1 = int(round(x0 + (i + 1) * cw)) - 3
            ch = y1 - y0
            drop = ()
            if name == "idle":
                # Piko sits low on the right of each idle cell
                drop = ((int((cx1 - cx0) * 0.62), int(ch * 0.66), cx1 - cx0, ch),)
            if name in ("idle", "walk") and i == 0:
                # Row label ("Idle", "Walk") in the first cell's corner
                drop = drop + ((0, 0, 48, 24),)
            if name == "jump" and i == 0:
                # The row's "Junpare Filel" label sits in the first cell
                drop = ((0, 0, cx1 - cx0, 18),)
            frames.append(_kieran_frame(sheet1, sheet4, (cx0, y0 + 4, cx1, y1), drop))
        anims[name] = frames
    # Gliding row: the poses straddle the cell borders, so find figures across
    # the whole row.
    gy0, gy1 = 600, 720
    row1 = erase_grid_lines(sheet1.crop((48, gy0, 576, gy1)))
    cut = sp.cutout(row1, keep="all")
    a = mask_of(cut, 40)
    labels, sizes, boxes = sp.components(a)
    figs = sorted([i for i in range(1, len(sizes)) if sizes[i] > 3000 and boxes[i][0] > 10],
                  key=lambda i: boxes[i][0])
    glide = []
    for i in figs:
        b = boxes[i]
        bx0, bx1 = max(b[0] - 6, 0), min(b[2] + 6, row1.width)
        img4 = sheet4.crop(((48 + bx0) * 4, gy0 * 4, (48 + bx1) * 4, gy1 * 4))
        glide.append((cutout_4x(img4), None))
    anims["glide"] = glide

    # One shared canvas height so the feet sit on the same line in every
    # animation; frames are anchored horizontally on the torso.
    def bbox(img):
        return img.getchannel("A").point(lambda v: 255 if v > 24 else 0).getbbox()

    out_frames = {}
    max_h = 0
    max_half_w = 0
    for name, frames in anims.items():
        lst = []
        for rgba, _ in frames:
            b = bbox(rgba)
            fig = rgba.crop(b)
            fig = resize_rgba(fig, (max(1, round(fig.width * KIERAN_OUT)), max(1, round(fig.height * KIERAN_OUT))))
            al = np.asarray(fig.getchannel("A")) > 128
            top = al[: max(1, int(al.shape[0] * 0.55))]
            cols = np.nonzero(top.any(axis=0))[0]
            ys, xs = np.nonzero(top)
            cx = xs.mean() if len(xs) else fig.width / 2
            lst.append((fig, cx))
            max_h = max(max_h, fig.height)
            max_half_w = max(max_half_w, cx, fig.width - cx)
        out_frames[name] = lst
    H = max_h + KIERAN_PAD + 4
    W = int(max_half_w * 2 + 8)
    report = []
    for name, lst in out_frames.items():
        strip = Image.new("RGBA", (W * len(lst), H), (0, 0, 0, 0))
        for i, (fig, cx) in enumerate(lst):
            x = int(round(i * W + W / 2 - cx))
            y = H - KIERAN_PAD - fig.height
            strip.alpha_composite(fig, (x, y))
        strip.save(sp.out("characters", "kieran", f"kieran_{name}.png"))
        report.append(f"kieran_{name}.png frames={len(lst)} frame={W}x{H}")
    report.append(f"feet baseline = {H - KIERAN_PAD}px from top of a {H}px frame")
    return report


# ---------------------------------------------------------------------------
# NPCs and Piko
# ---------------------------------------------------------------------------

def _hd_cut(key, box, height, method="paper", **kw):
    """Cut a figure from a turnaround sheet at 4x and size it for the game."""
    sheet1 = Image.open(sp.src(*SOURCES[key][0])).convert("RGB")
    sheet4 = x4(key)
    crop1 = sheet1.crop(box)
    if method == "outline":
        cut = sp.outline_cutout(crop1, **kw)
        m = mask_of(cut)
    else:
        cut = sp.cutout(crop1, min_bright=150, max_sat=40, **kw)
        m = mask_of(cut)
    rgba = apply_mask_4x(m, sheet4.crop(tuple(v * 4 for v in box)), clean_paper=(method != "outline"))
    b = rgba.getchannel("A").point(lambda v: 255 if v > 24 else 0).getbbox()
    rgba = rgba.crop(b)
    w = round(rgba.width * height / rgba.height)
    return resize_rgba(rgba, (w, height))


def build_bodies():
    rep = []
    # In-game display heights (px at 1080p): adults ~190, Piko ~120 long.
    jobs = [
        ("tessa", (620, 60, 800, 720), "tessa", "tessa_side", 210, {}),
        ("tessa", (60, 60, 290, 720), "tessa", "tessa_front", 210, {}),
    ]
    for key, box, folder, name, h, kw in jobs:
        img = _hd_cut(key, box, h, **kw)
        img.save(sp.out("characters", folder, f"{name}.png"))
        rep.append(f"{name}.png {img.size}")
    for key in ("bram", "elara"):
        sheet = Image.open(sp.src("characters", f"{'Bram Holloway' if key == 'bram' else 'Elara Greenborough'} Turnaround.jpeg")).convert("RGB")
        body = sheet.crop((0, 40, sheet.width, sheet.height - 70))
        cut = sp.cutout(body, keep="all", min_bright=150, max_sat=40)
        a = mask_of(cut, 40)
        _, sizes, boxes = sp.components(a)
        figs = sorted([boxes[i] for i in range(1, len(sizes)) if sizes[i] > 8000], key=lambda b: b[0])
        for idx, name in ((0, "front"), (2, "side")):
            b = figs[idx]
            box = (max(b[0] - 6, 0), 40 + max(b[1] - 6, 0), min(b[2] + 6, sheet.width), 40 + min(b[3] + 6, body.height))
            img = _hd_cut(key, box, 216)
            img.save(sp.out("characters", key, f"{key}_{name}.png"))
            rep.append(f"{key}_{name}.png {img.size}")
    # Piko side view including the floating tail, outline-based cut.
    img = _hd_cut("piko", (70, 300, 545, 800), 160, method="outline", min_blob=400,
                  drop_boxes=((0, 0, 262, 262), (0, 0, 349, 140), (0, 0, 316, 192)))
    img.save(sp.out("characters", "piko", "piko_side.png"))
    rep.append(f"piko_side.png {img.size}")
    # Maren's placeholder silhouette, pre-sized so it is not shrunk 3x in-game.
    src_m = os.path.join(CACHE, "maren_placeholder_src.png")
    if not os.path.exists(src_m):
        Image.open(sp.out("characters", "maren", "maren_placeholder.png")).save(src_m)
    m = Image.open(src_m).convert("RGBA")
    m = resize_rgba(m, (round(m.width * 216 / m.height), 216))
    m.save(sp.out("characters", "maren", "maren_placeholder.png"))
    rep.append(f"maren_placeholder.png {m.size}")
    return rep


# ---------------------------------------------------------------------------
# Environment props
# ---------------------------------------------------------------------------

def white_mask_4x(img4, thresh=218, hole=30):
    """Background of the atlas panel at 4x: near-white connected to the edge,
    plus enclosed white pockets (between windmill sails, inside the well)."""
    rgb = np.asarray(img4).astype(np.int32)
    mn = rgb.min(axis=2)
    sat = rgb.max(axis=2) - mn
    cand = (mn > thresh) & (sat < 34)
    bg = sp.flood_from_edges(cand)
    lab, sizes, _ = sp.components(cand & ~bg)
    pockets = [i for i in range(1, len(sizes)) if sizes[i] > hole]
    if pockets:
        bg |= np.isin(lab, pockets)
    return ~bg


# Which pieces to keep from each old 1x component box: "largest" drops the
# neighbours that touched it in the atlas (the bush beside the windmill).
PIECE_KEEP = {7: "largest"}


def build_environment():
    rep = []
    atlas = Image.open(sp.src("environments", "Eight Realms_ Platformer Asset Atlas.png")).convert("RGB")
    # Same detection as the original pass so piece numbers stay the same.
    panel = atlas.crop((0, 48, 384, 412))
    cut1 = sp.white_cutout(panel, thresh=232)
    a1 = np.asarray(cut1.getchannel("A")) > 40
    _, sizes1, boxes1 = sp.components(a1)
    items = [(boxes1[i], sizes1[i]) for i in range(1, len(sizes1)) if sizes1[i] > 250]
    items.sort(key=lambda t: (t[0][1] // 40, t[0][0]))

    img4 = x4("atlas_brindle")         # crop starts at y=40, the panel at y=48
    fg = white_mask_4x(img4)
    fg = np.asarray(Image.fromarray((fg * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(3))) > 0
    lab, sizes, boxes = sp.components(fg)
    for idx, (b, _) in enumerate(items):
        x0, y0, x1, y1 = b[0] * 4, (b[1] + 8) * 4, b[2] * 4, (b[3] + 8) * 4
        pad = 6
        x0, y0, x1, y1 = max(x0 - pad, 0), max(y0 - pad, 0), min(x1 + pad, img4.width), min(y1 + pad, img4.height)
        sub = lab[y0:y1, x0:x1]
        ids, counts = np.unique(sub[sub > 0], return_counts=True)
        if len(ids) == 0:
            continue
        if PIECE_KEEP.get(idx) == "largest":
            keep = [ids[np.argmax(counts)]]
        else:
            # Components mostly inside this box (not neighbours poking in).
            keep = [i for i, c in zip(ids, counts) if c > 0.6 * sizes[i] and c > 150]
        m = np.isin(sub, keep)
        piece = img4.crop((x0, y0, x1, y1)).convert("RGBA")
        al = Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.7))
        piece.putalpha(al)
        bb = piece.getchannel("A").point(lambda v: 255 if v > 24 else 0).getbbox()
        piece = piece.crop(bb)
        piece.save(sp.out("environments", "brindle", f"brindle_{idx:02d}_4x.png"))
        rep.append(f"brindle_{idx:02d}_4x.png {piece.size}")
    return rep


def build_ground():
    """Grass-topped ground: seamless tile + caps from the long Brindle
    platform, plus a tileable rock texture for the island's underside."""
    g = Image.open(sp.out("environments", "brindle", "brindle_00_4x.png"))
    H = 153
    # Grass and the first course of stones.
    top = g.crop((0, 0, g.width, 236))
    top = resize_rgba(top, (round(top.width * H / top.height), H))
    top.save(sp.out("environments", "brindle", "ground_strip.png"))
    capw = 150
    mid = top.crop((capw, 0, top.width - capw, H))
    blend = 90
    tile = mid.crop((0, 0, mid.width - blend, H)).copy()
    right = np.asarray(mid.crop((mid.width - blend, 0, mid.width, H))).astype(np.float32)
    t = np.asarray(tile).astype(np.float32)
    for x in range(blend):
        w = x / (blend - 1)
        t[:, x] = right[:, x] * (1 - w) + t[:, x] * w
    tile = Image.fromarray(t.clip(0, 255).astype(np.uint8), "RGBA")
    # The tile's bottom edge is where the rock fill continues; make the lower
    # rows fully opaque so no sky shows through between them.
    arr = np.asarray(tile).copy()
    arr[int(H * 0.45):, :, 3] = 255
    tile = Image.fromarray(arr, "RGBA")
    tile.save(sp.out("environments", "brindle", "ground_tile.png"))
    top.crop((0, 0, capw, H)).save(sp.out("environments", "brindle", "ground_cap_left.png"))
    top.crop((top.width - capw, 0, top.width, H)).save(sp.out("environments", "brindle", "ground_cap_right.png"))
    # Rock texture for the underside: the stone wall of the big platform,
    # made seamless in both directions.
    rock = g.crop((40, 110, 700, 232)).convert("RGB")
    rock = _seamless(rock, 36)
    rock.save(sp.out("environments", "brindle", "rock_fill.png"))
    rep = ["ground_strip.png", "ground_tile.png", "rock_fill.png"]
    # Small floating platforms.
    for name, idx in (("platform_small_a", 2), ("platform_small_b", 3)):
        p = Image.open(sp.out("environments", "brindle", f"brindle_{idx:02d}_4x.png"))
        p = resize_rgba(p, (p.width // 2, p.height // 2))
        p.save(sp.out("environments", "brindle", f"{name}.png"))
        rep.append(f"{name}.png {p.size}")
    return rep


def _seamless(img, blend):
    a = np.asarray(img).astype(np.float32)
    h, w = a.shape[:2]
    out = a[:, : w - blend].copy()
    for x in range(blend):
        t = x / (blend - 1)
        out[:, x] = a[:, w - blend + x] * (1 - t) + out[:, x] * t
    a = out
    h, w = a.shape[:2]
    out = a[: h - blend].copy()
    for y in range(blend):
        t = y / (blend - 1)
        out[y] = a[h - blend + y] * (1 - t) + out[y] * t
    return Image.fromarray(out.clip(0, 255).astype(np.uint8))


# ---------------------------------------------------------------------------
# Windmill rotor (so the sails can turn)
# ---------------------------------------------------------------------------

def build_rotor():
    """Split the windmill into a static tower and a rotor of four sails.

    The rotor is assembled from one clean sail from the original art, copied
    at 90 degree steps around the hub. The tower keeps only the pixels inside
    the tower and cap outline, so the original painted sails disappear."""
    wm = Image.open(sp.out("environments", "brindle", "brindle_07_4x.png")).convert("RGBA")
    a = np.asarray(wm).copy()
    h, w = a.shape[:2]
    # Hub position and tower outline, measured on the 4x windmill piece.
    hub = (int(w * 0.555), int(h * 0.36))
    yy, xx = np.mgrid[0:h, 0:w]
    # Tower: a trapezoid from just under the cap to the base, plus the cap.
    t_top, t_bot = int(h * 0.30), h
    half_top, half_bot = w * 0.13, w * 0.30
    frac = np.clip((yy - t_top) / max(t_bot - t_top, 1), 0, 1)
    half = half_top + (half_bot - half_top) * frac
    tower = (yy >= t_top) & (np.abs(xx - w * 0.6) <= half)
    cap = ((xx - w * 0.6) ** 2 / (w * 0.17) ** 2 + (yy - h * 0.33) ** 2 / (h * 0.085) ** 2) <= 1
    base = yy > h * 0.80
    keep = tower | cap | base
    ta = a.copy()
    ta[~keep, 3] = 0
    Image.fromarray(ta).save(sp.out("environments", "brindle", "windmill_tower.png"))
    # One sail: the upper-right one in the source art, from hub outwards.
    sail_box = (int(w * 0.56), 0, int(w * 0.80), int(h * 0.33))
    sail = wm.crop(sail_box)
    # Rotate so the sail points straight up from the hub.
    import math
    sx, sy = sail_box[0], sail_box[1]
    tip = None
    sa = np.asarray(sail)[..., 3] > 128
    ys, xs = np.nonzero(sa)
    if len(ys):
        i = np.argmin(ys)
        tip = (xs[i] + sx, ys[i] + sy)
    ang = math.degrees(math.atan2(tip[0] - hub[0], hub[1] - tip[1])) if tip else 0.0
    R = int(max(h * 0.40, w * 0.5))
    canvas = Image.new("RGBA", (2 * R, 2 * R), (0, 0, 0, 0))
    layer = Image.new("RGBA", (2 * R, 2 * R), (0, 0, 0, 0))
    layer.alpha_composite(sail, (R - hub[0] + sx, R - hub[1] + sy))
    up = layer.rotate(ang, resample=Image.BICUBIC, center=(R, R))
    for k in range(4):
        canvas.alpha_composite(up.rotate(90 * k, resample=Image.BICUBIC, center=(R, R)))
    # Wooden stocks (the arms the sails hang on) under the sails, and a hub.
    from PIL import ImageDraw
    arms = Image.new("RGBA", (2 * R, 2 * R), (0, 0, 0, 0))
    d = ImageDraw.Draw(arms)
    reach = int(R * 0.86)
    for k in range(4):
        th = math.radians(90 * k + ang * 0)
        ex, ey = R + math.sin(th) * reach, R - math.cos(th) * reach
        d.line([(R, R), (ex, ey)], fill=(52, 33, 22, 255), width=17)
        d.line([(R, R), (ex, ey)], fill=(132, 86, 50, 255), width=10)
    arms.alpha_composite(canvas)
    canvas = arms
    d = ImageDraw.Draw(canvas)
    hr = int(w * 0.05)
    d.ellipse([R - hr, R - hr, R + hr, R + hr], fill=(110, 72, 42, 255), outline=(45, 28, 18, 255), width=5)
    d.ellipse([R - hr // 3, R - hr // 3, R + hr // 3, R + hr // 3], fill=(196, 160, 90, 255))
    # Keep the hub at the exact centre of the saved image.
    bb = canvas.getbbox()
    half = max(R - bb[0], bb[2] - R, R - bb[1], bb[3] - R)
    canvas = canvas.crop((R - half, R - half, R + half, R + half))
    canvas.save(sp.out("environments", "brindle", "windmill_rotor.png"))
    return [f"windmill_tower.png {w}x{h} hub={hub}", f"windmill_rotor.png {canvas.size} sail_angle={ang:.1f}"]


def build_fx():
    """Procedural ambient textures (project-owned): cloud puffs and a leaf."""
    from PIL import ImageDraw
    rng = np.random.default_rng(7)
    rep = []
    for n in range(3):
        W, H = 720, 300
        a = Image.new("L", (W, H), 0)
        d = ImageDraw.Draw(a)
        for _ in range(16):
            r = rng.uniform(50, 110)
            cx = rng.uniform(r + 40, W - r - 40)
            cy = rng.uniform(max(H * 0.45, r * 0.8 + 40), H - r * 0.8 - 40)
            d.ellipse([cx - r, cy - r * 0.8, cx + r, cy + r * 0.8], fill=255)
        a = a.filter(ImageFilter.GaussianBlur(14))
        al = np.asarray(a).astype(np.float32) / 255.0
        yy = np.linspace(0, 1, H)[:, None]
        shade = 1.0 - 0.22 * np.clip((yy - 0.45) / 0.55, 0, 1)
        rgb = np.stack([250 * shade, 251 * shade, 255 * shade + 0 * yy], axis=2) * np.ones((H, W, 1))
        img = np.concatenate([rgb, (al * 235)[..., None]], axis=2).clip(0, 255).astype(np.uint8)
        Image.fromarray(img, "RGBA").save(sp.out("environments", "fx", f"cloud_{n}.png"))
        rep.append(f"fx/cloud_{n}.png")
    leaf = Image.new("RGBA", (28, 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(leaf)
    d.ellipse([1, 2, 26, 14], fill=(126, 168, 72, 255), outline=(64, 96, 40, 255), width=2)
    d.line([(3, 8), (24, 8)], fill=(80, 116, 48, 255), width=1)
    leaf.save(sp.out("environments", "fx", "leaf.png"))
    petal = Image.new("RGBA", (18, 12), (0, 0, 0, 0))
    ImageDraw.Draw(petal).ellipse([1, 1, 16, 10], fill=(248, 206, 220, 255), outline=(200, 140, 160, 255))
    petal.save(sp.out("environments", "fx", "petal.png"))
    rep += ["fx/leaf.png", "fx/petal.png"]
    return rep


def build_workshop():
    """Workshop props (Starfall Basin panel) at 4x, same names as before."""
    atlas = Image.open(sp.src("environments", "Eight Realms_ Platformer Asset Atlas.png")).convert("RGB")
    panel = atlas.crop((770, 560, 1150, 905))
    cut1 = sp.white_cutout(panel, thresh=232)
    a1 = np.asarray(cut1.getchannel("A")) > 40
    _, sizes1, boxes1 = sp.components(a1)
    items = sorted([(boxes1[i], sizes1[i]) for i in range(1, len(sizes1)) if sizes1[i] > 250],
                   key=lambda t: (t[0][1] // 40, t[0][0]))
    img4 = x4("atlas_starfall")
    fg = white_mask_4x(img4)
    fg = np.asarray(Image.fromarray((fg * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(3))) > 0
    lab, sizes, _ = sp.components(fg)
    rep = []
    for idx, name in sp.WORKSHOP_PIECES.items():
        b = items[idx][0]
        x0, y0, x1, y1 = max(b[0] * 4 - 6, 0), max(b[1] * 4 - 6, 0), min(b[2] * 4 + 6, img4.width), min(b[3] * 4 + 6, img4.height)
        sub = lab[y0:y1, x0:x1]
        ids, counts = np.unique(sub[sub > 0], return_counts=True)
        keep = [i for i, c in zip(ids, counts) if c > 0.6 * sizes[i] and c > 150]
        m = np.isin(sub, keep)
        piece = img4.crop((x0, y0, x1, y1)).convert("RGBA")
        piece.putalpha(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.7)))
        piece = piece.crop(piece.getchannel("A").point(lambda v: 255 if v > 24 else 0).getbbox())
        piece.save(sp.out("environments", "workshop", f"{name}_4x.png"))
        rep.append(f"workshop/{name}_4x.png {piece.size}")
    return rep


STEPS = {
    "workshop": build_workshop,
    "fx": build_fx,
    "upscale": build_upscale,
    "kieran": build_kieran,
    "bodies": build_bodies,
    "environment": build_environment,
    "ground": build_ground,
    "rotor": build_rotor,
}

if __name__ == "__main__":
    steps = sys.argv[1:] or list(STEPS)
    for s in steps:
        for line in STEPS[s]():
            print(s, line)
