"""
Aplica el estilo Graphite Elegance a imágenes fuente en Raw_Silhouettes.
Salida: ICO multi-resolución + PNG 256px en la carpeta Release.
"""
import os, sys
import cv2
import numpy as np
from PIL import Image, ImageDraw

# ── Rutas (relativas al repo: Generator/scripts/ -> Generator/ -> raiz) ───────
_SCRIPTS   = os.path.dirname(os.path.abspath(__file__))
_GENERATOR = os.path.dirname(_SCRIPTS)
ROOT       = os.path.dirname(_GENERATOR)
RAW = os.path.join(_GENERATOR, "assets", "Raw_Silhouettes")
ICO = os.path.join(ROOT, "Graphite_Elegance_Release", "Icons", "ICO")
PNG = os.path.join(ROOT, "Graphite_Elegance_Release", "Icons", "PNG")
os.makedirs(ICO, exist_ok=True)
os.makedirs(PNG, exist_ok=True)

# ── Especificación por tamaño ────────────────────────────────────────────────
SS = 4   # supersampling
ICO_SPECS = {
    256: dict(logo_frac=0.50, border=True,  shadow=True),
    128: dict(logo_frac=0.50, border=True,  shadow=True),
    64:  dict(logo_frac=0.52, border=True,  shadow=True),
    48:  dict(logo_frac=0.54, border=True,  shadow=True),
    32:  dict(logo_frac=0.62, border=False, shadow=False),
    16:  dict(logo_frac=0.68, border=False, shadow=False),
}

# ── Extracción de silueta ────────────────────────────────────────────────────
def extract_silhouette(img_rgba):
    rgb, alpha = img_rgba[:, :, :3], img_rgba[:, :, 3]
    h, w = rgb.shape[:2]

    if not np.all(alpha == 255):
        # Imagen con canal alfa real
        binmask = np.where(alpha >= 64, 255, 0).astype(np.uint8)
        inside = binmask > 0
        if np.any(inside):
            gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
            vals = gray[inside]
            if vals.std() > 25:
                t, _ = cv2.threshold(vals.reshape(-1,1), 0, 255,
                                     cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                dark  = inside & (gray <= t)
                light = inside & (gray > t)
                minor = dark if np.count_nonzero(dark) < np.count_nonzero(light) else light
                frac  = np.count_nonzero(minor) / np.count_nonzero(inside)
                if 0.02 < frac < 0.45:
                    binmask[minor] = 0
    else:
        # Sin canal alfa: distancia Lab al fondo
        lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
        corners = [lab[2,2], lab[2,w-3], lab[h-3,2], lab[h-3,w-3]]
        bg = np.median(corners, axis=0)
        dist = np.linalg.norm(lab - bg, axis=2)
        dist8 = cv2.normalize(dist, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        _, binmask = cv2.threshold(dist8, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    cnts, hier = cv2.findContours(binmask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    if hier is None:
        return None
    hier = hier[0]

    outers = [(c, cv2.contourArea(c)) for c, hr in zip(cnts, hier) if hr[3] == -1]
    if not outers:
        return None
    largest = max(a for _, a in outers)
    if largest <= 0:
        return None

    keep = [c for c, a in outers if a > largest * 0.01]
    logo_area = sum(cv2.contourArea(c) for c in keep)

    out = np.zeros_like(binmask)
    cv2.drawContours(out, keep, -1, 255, cv2.FILLED)
    for c, hr in zip(cnts, hier):
        if hr[3] != -1 and cv2.contourArea(c) >= logo_area * 0.005:
            cv2.drawContours(out, [c], -1, 0, cv2.FILLED)
    return out


def resize_silhouette_aa(mask, target_long):
    x, y, bw, bh = cv2.boundingRect(mask)
    mask = mask[y:y+bh, x:x+bw]
    scale = target_long / max(bw, bh)
    if scale < 1.0:
        mask = cv2.GaussianBlur(mask, (0,0), 0.5 / scale)
        interp = cv2.INTER_AREA
    else:
        interp = cv2.INTER_CUBIC
    new_wh = (max(1, round(bw*scale)), max(1, round(bh*scale)))
    a = cv2.resize(mask, new_wh, interpolation=interp).astype(np.float32) / 255
    a = np.clip((a - 0.30) / 0.40, 0, 1)
    a = a * a * (3 - 2 * a)
    a8 = (a * 255).astype(np.uint8)
    logo = np.dstack([np.full_like(a8, 255)] * 3 + [a8])
    return Image.fromarray(logo, "RGBA")


def compose_icon(mask, size, logo_frac, border=True, shadow=True):
    S = size * SS
    radius = (60 / 256) * S

    grad  = np.linspace(45.0, 10.0, S, dtype=np.float32)[:, None]
    noise = np.random.default_rng(0).uniform(-0.5, 0.5, (S, S)).astype(np.float32)
    g     = np.clip(np.broadcast_to(grad, (S, S)) + noise, 0, 255).astype(np.uint8)
    canvas = Image.fromarray(np.dstack([g, g, g, np.full((S,S), 255, np.uint8)]), "RGBA")

    sq = Image.new("L", (S, S), 0)
    ImageDraw.Draw(sq).rounded_rectangle((0, 0, S-1, S-1), radius, fill=255)
    canvas.putalpha(sq)

    if border:
        b = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        ImageDraw.Draw(b).rounded_rectangle(
            (SS//2, SS//2, S-1-SS//2, S-1-SS//2),
            radius, outline=(255, 255, 255, 30), width=SS)
        canvas.alpha_composite(b)

    logo = resize_silhouette_aa(mask, max(1, int(S * logo_frac)))
    off  = ((S - logo.width) // 2, (S - logo.height) // 2)

    if shadow:
        la = np.zeros((S, S), np.float32)
        la[off[1]:off[1]+logo.height, off[0]:off[0]+logo.width] = \
            np.asarray(logo)[:, :, 3] / 255.0
        u = S / 256.0
        ambient     = cv2.GaussianBlur(la, (0,0), 8*u) * 0.30
        key         = cv2.GaussianBlur(la, (0,0), 3*u) * 0.50
        dy          = max(1, int(4*u))
        key_shifted = np.zeros_like(key)
        key_shifted[dy:, :] = key[:-dy, :]
        sh = np.clip(ambient + key_shifted, 0, 1)
        sh *= np.asarray(sq, np.float32) / 255
        sh_rgba = np.zeros((S, S, 4), np.uint8)
        sh_rgba[:, :, 3] = (sh * 255).astype(np.uint8)
        canvas.alpha_composite(Image.fromarray(sh_rgba, "RGBA"))

    canvas.alpha_composite(logo, off)
    return canvas.resize((size, size), Image.Resampling.LANCZOS)


# ── Proceso ──────────────────────────────────────────────────────────────────
TARGETS = [
    ("Labymod.png",         "Labymod"),
    ("Outlook.png",         "Outlook"),
    ("ATLauncher.png",      "ATLauncher"),
    ("Classroom.png",       "Classroom"),
    ("Youtube.png",         "Youtube"),
    ("Mini Cozy Room.jpg",  "Mini Cozy Room"),
]

sizes = sorted(ICO_SPECS, reverse=True)

for src_file, out_name in TARGETS:
    src_path = os.path.join(RAW, src_file)
    if not os.path.exists(src_path):
        print(f"[SKIP] No encontrado: {src_path}")
        continue

    img = Image.open(src_path).convert("RGBA")
    img_np = np.array(img)

    mask = extract_silhouette(img_np)
    if mask is None or not np.any(mask):
        print(f"[FAIL] No se pudo extraer silueta: {out_name}")
        continue

    renders = {sz: compose_icon(mask, sz, **ICO_SPECS[sz]) for sz in sizes}
    master  = renders[256]

    png_path = os.path.join(PNG, f"{out_name}.png")
    ico_path = os.path.join(ICO, f"{out_name}.ico")

    master.save(png_path, format="PNG")
    master.save(
        ico_path, format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=[renders[s] for s in sizes if s != 256]
    )
    print(f"[OK] {out_name}")

print("\nFinalizado.")
