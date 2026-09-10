"""
Shared composition for the Isoform icon factory.

Pure functions (Pillow + OpenCV + NumPy) used by ``build.py``. Kept separate
from the desktop applicator and from the legacy scripts.

Styles are described declaratively (vertical RGB gradient, logo colour, border,
shadow and an optional pixel-art mode) so new variants can be added without
touching the rendering code.
"""
from __future__ import annotations

import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw

_PIPELINE = os.path.dirname(os.path.abspath(__file__))
if _PIPELINE not in sys.path:
    sys.path.insert(0, _PIPELINE)
from styles import STYLES  # noqa: E402

SS = 4  # supersampling factor
ICON_SIZES = (16, 32, 48, 64, 128, 256)

# Parametric spec per output size. At 32/16 px the 1px border and the shadow
# become noise, so they are dropped and the logo grows.
ICO_SPECS = {
    256: dict(logo_frac=0.50, border=True, shadow=True),
    128: dict(logo_frac=0.50, border=True, shadow=True),
    64: dict(logo_frac=0.52, border=True, shadow=True),
    48: dict(logo_frac=0.54, border=True, shadow=True),
    32: dict(logo_frac=0.62, border=False, shadow=False),
    16: dict(logo_frac=0.68, border=False, shadow=False),
}

# Palette reference: see styles.py.


def extract_silhouette(img_rgba):
    """Binary silhouette from an HxWx4 uint8 array. Returns (mask, stats)."""
    rgb, alpha = img_rgba[:, :, :3], img_rgba[:, :, 3]
    h, w = rgb.shape[:2]

    if not np.all(alpha == 255):
        binmask = np.where(alpha >= 64, 255, 0).astype(np.uint8)
        inside = binmask > 0
        if np.any(inside):
            gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
            vals = gray[inside]
            if vals.std() > 25:
                t, _ = cv2.threshold(vals.reshape(-1, 1), 0, 255,
                                     cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                dark = inside & (gray <= t)
                light = inside & (gray > t)
                minor = dark if np.count_nonzero(dark) < np.count_nonzero(light) else light
                frac = np.count_nonzero(minor) / np.count_nonzero(inside)
                if 0.02 < frac < 0.45:
                    binmask[minor] = 0
    else:
        lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
        corners = [lab[2, 2], lab[2, w - 3], lab[h - 3, 2], lab[h - 3, w - 3]]
        bg = np.median(corners, axis=0)
        dist = np.linalg.norm(lab - bg, axis=2)
        dist8 = cv2.normalize(dist, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        _, binmask = cv2.threshold(dist8, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    cnts, hier = cv2.findContours(binmask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    if hier is None:
        return None, dict(coverage=0.0, islands=0)
    hier = hier[0]

    outers = [(c, cv2.contourArea(c)) for c, hr in zip(cnts, hier) if hr[3] == -1]
    if not outers:
        return None, dict(coverage=0.0, islands=0)
    largest = max(a for _, a in outers)
    if largest <= 0:
        return None, dict(coverage=0.0, islands=0)

    keep = [c for c, a in outers if a > largest * 0.01]
    logo_area = sum(cv2.contourArea(c) for c in keep)

    out = np.zeros_like(binmask)
    cv2.drawContours(out, keep, -1, 255, cv2.FILLED)
    for c, hr in zip(cnts, hier):
        if hr[3] != -1 and cv2.contourArea(c) >= logo_area * 0.005:
            cv2.drawContours(out, [c], -1, 0, cv2.FILLED)

    coverage = float(np.count_nonzero(out)) / out.size
    return out, dict(coverage=coverage, islands=len(keep))


def _logo_rgba(alpha8, color):
    r, g, b = color
    return np.dstack([np.full_like(alpha8, r), np.full_like(alpha8, g),
                      np.full_like(alpha8, b), alpha8])


def _resize_silhouette_aa(mask, target_long, color):
    x, y, bw, bh = cv2.boundingRect(mask)
    mask = mask[y:y + bh, x:x + bw]
    scale = target_long / max(bw, bh)
    if scale < 1.0:
        mask = cv2.GaussianBlur(mask, (0, 0), 0.5 / scale)
        interp = cv2.INTER_AREA
    else:
        interp = cv2.INTER_CUBIC
    new_wh = (max(1, round(bw * scale)), max(1, round(bh * scale)))
    a = cv2.resize(mask, new_wh, interpolation=interp).astype(np.float32) / 255
    a = np.clip((a - 0.30) / 0.40, 0, 1)
    a = a * a * (3 - 2 * a)
    return Image.fromarray(_logo_rgba((a * 255).astype(np.uint8), color), "RGBA")


def _resize_silhouette_pixel(mask, target_long, color, grid=32):
    """Blocky logo: quantise to a coarse grid then upscale with NEAREST."""
    x, y, bw, bh = cv2.boundingRect(mask)
    mask = mask[y:y + bh, x:x + bw]
    scale = target_long / max(bw, bh)
    new_wh = (max(1, round(bw * scale)), max(1, round(bh * scale)))
    cell = max(1, round(target_long / grid))
    small = (max(1, round(new_wh[0] / cell)), max(1, round(new_wh[1] / cell)))
    q = cv2.resize(mask, small, interpolation=cv2.INTER_AREA)
    q = np.where(q >= 128, 255, 0).astype(np.uint8)
    a = cv2.resize(q, new_wh, interpolation=cv2.INTER_NEAREST)
    return Image.fromarray(_logo_rgba(a, color), "RGBA")


def _gradient(S, top, bottom):
    rows = np.linspace(0.0, 1.0, S, dtype=np.float32)[:, None]
    noise = np.random.default_rng(0).uniform(-0.5, 0.5, (S, S)).astype(np.float32)
    rgb = np.zeros((S, S, 3), np.uint8)
    for c in range(3):
        g = top[c] + (bottom[c] - top[c]) * rows
        rgb[:, :, c] = np.clip(np.broadcast_to(g, (S, S)) + noise, 0, 255).astype(np.uint8)
    return rgb


def compose_icon(mask, size, style):
    """Compose one size x size icon in the given style."""
    st = STYLES[style]
    spec = ICO_SPECS[size]
    S = size if st.get("pixelated") else size * SS
    border = st.get("border", False) and spec["border"]
    shadow = st.get("shadow", False) and spec["shadow"]
    square = st.get("square", False)

    rgb = _gradient(S, st["grad_top"], st["grad_bottom"])
    canvas = Image.fromarray(np.dstack([rgb, np.full((S, S), 255, np.uint8)]), "RGBA")

    radius = 0 if square else (st.get("radius", 60) / 256) * S
    if not square:
        sq = Image.new("L", (S, S), 0)
        ImageDraw.Draw(sq).rounded_rectangle((0, 0, S - 1, S - 1), radius, fill=255)
        canvas.putalpha(sq)

    if border:
        color = st.get("border_color", (255, 255, 255, 30))
        width = max(1, int(round(st.get("border_width", 1) * S / 256)))
        inset = width / 2
        b = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        ImageDraw.Draw(b).rounded_rectangle(
            (inset, inset, S - 1 - inset, S - 1 - inset),
            max(0, radius - inset), outline=color, width=width)
        canvas.alpha_composite(b)

    if st.get("pixelated"):
        logo = _resize_silhouette_pixel(
            mask, max(1, int(S * st.get("logo_frac", spec["logo_frac"]))), st["logo"],
            grid=st.get("pixel_grid", 32))
    else:
        logo = _resize_silhouette_aa(
            mask, max(1, int(S * st.get("logo_frac", spec["logo_frac"]))), st["logo"])
    off = ((S - logo.width) // 2, (S - logo.height) // 2)

    if shadow:
        la = np.zeros((S, S), np.float32)
        la[off[1]:off[1] + logo.height, off[0]:off[0] + logo.width] = \
            np.asarray(logo)[:, :, 3] / 255.0
        u = S / 256.0
        ambient = cv2.GaussianBlur(la, (0, 0), 8 * u) * 0.30
        key = cv2.GaussianBlur(la, (0, 0), 3 * u) * 0.50
        dy = max(1, int(4 * u))
        key_shifted = np.zeros_like(key)
        key_shifted[dy:, :] = key[:-dy, :]
        sh = np.clip(ambient + key_shifted, 0, 1)
        sh *= np.asarray(canvas.getchannel("A"), np.float32) / 255
        sh_rgba = np.zeros((S, S, 4), np.uint8)
        sh_rgba[:, :, 3] = (sh * 255).astype(np.uint8)
        canvas.alpha_composite(Image.fromarray(sh_rgba, "RGBA"))

    canvas.alpha_composite(logo, off)
    return canvas.resize((size, size), Image.Resampling.LANCZOS)


def compose_from_file(source_path, style, sizes=ICON_SIZES):
    """Return a dict {size: PIL.Image} for a source image and style."""
    img = Image.open(source_path).convert("RGBA")
    mask, _stats = extract_silhouette(np.array(img))
    if mask is None or not np.any(mask):
        raise ValueError(f"No se pudo extraer silueta: {source_path}")
    return {s: compose_icon(mask, s, style) for s in sorted(sizes)}


def save_ico(renders, ico_path):
    ordered = sorted(renders)
    master = renders[ordered[-1]]
    master.save(ico_path, format="ICO", sizes=[(s, s) for s in ordered])


def save_png(renders, png_path):
    renders[max(renders)].save(png_path, format="PNG")
