"""
Aplica el estilo Lumina Frost a imágenes fuente en Raw_Silhouettes.
Salida: ICO multi-resolución + PNG 256px en la carpeta Release.
"""
import os, sys
import cv2
import numpy as np
from PIL import Image, ImageDraw

_SCRIPTS   = os.path.dirname(os.path.abspath(__file__))
_GENERATOR = os.path.dirname(_SCRIPTS)
ROOT       = os.path.dirname(_GENERATOR)
RAW      = os.path.join(_GENERATOR, "assets", "Raw_Silhouettes")
ICO_BASE = os.path.join(ROOT, "Lumina_Frost_Release", "Icons", "ICO")
os.makedirs(ICO_BASE, exist_ok=True)

SS = 4
ICO_SPECS = {
    256: dict(logo_frac=0.50, border=False, shadow=False),
    128: dict(logo_frac=0.50, border=False, shadow=False),
    64:  dict(logo_frac=0.52, border=False, shadow=False),
    48:  dict(logo_frac=0.54, border=False, shadow=False),
    32:  dict(logo_frac=0.62, border=False, shadow=False),
    16:  dict(logo_frac=0.68, border=False, shadow=False),
}

def extract_silhouette(img_rgba):
    rgb, alpha = img_rgba[:, :, :3], img_rgba[:, :, 3]
    h, w = rgb.shape[:2]

    if not np.all(alpha == 255):
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
    
    # INVERTIDO: Color oscuro para el logo (#191919) para máximo contraste
    logo = np.dstack([np.full_like(a8, 25)] * 3 + [a8])
    return Image.fromarray(logo, "RGBA")

def compose_icon(mask, size, logo_frac, border=False, shadow=False):
    S = size * SS
    radius = (60 / 256) * S

    # INVERTIDO: Squircle blanco brillante
    grad  = np.linspace(255.0, 245.0, S, dtype=np.float32)[:, None]
    noise = np.random.default_rng(0).uniform(-0.5, 0.5, (S, S)).astype(np.float32)
    g     = np.clip(np.broadcast_to(grad, (S, S)) + noise, 0, 255).astype(np.uint8)
    canvas = Image.fromarray(np.dstack([g, g, g, np.full((S,S), 255, np.uint8)]), "RGBA")

    sq = Image.new("L", (S, S), 0)
    ImageDraw.Draw(sq).rounded_rectangle((0, 0, S-1, S-1), radius, fill=255)
    canvas.putalpha(sq)

    logo = resize_silhouette_aa(mask, max(1, int(S * logo_frac)))
    off  = ((S - logo.width) // 2, (S - logo.height) // 2)

    canvas.alpha_composite(logo, off)
    return canvas.resize((size, size), Image.Resampling.LANCZOS)

# Solo procesar categoría: Videojuegos
TARGETS = {
    "Videojuegos": [
        ("ATLauncher.png", "ATLauncher"),
        ("Aimlabs.ico", "Aimlabs"),
        ("Blasphemous.png", "Blasphemous"),
        ("Blitz.jpg", "Blitz"),
        ("Epic Games.png", "Epic Games"),
        ("Hytale.png", "Hytale"),
        ("Kovacks.jpg", "Kovacks"),
        ("Labymod.png", "Labymod"),
        ("Minecraft.ico", "Minecraft"),
        ("Mini Cozy Room.png", "Mini Cozy Room"),
        ("Terraria.ico", "Terraria"),
        ("Valorant Tracker.png", "Valorant Tracker"),
        ("tModLoader.png", "tModLoader")
    ]
}

sizes = sorted(ICO_SPECS, reverse=True)

for category, items in TARGETS.items():
    cat_dir = os.path.join(ICO_BASE, category)
    os.makedirs(cat_dir, exist_ok=True)
    
    for src_file, out_name in items:
        src_path = os.path.join(RAW, src_file)
        if not os.path.exists(src_path):
            # Try alternate extension
            base, ext = os.path.splitext(src_path)
            alt_path = None
            for alt_ext in ['.png', '.jpg', '.ico']:
                if os.path.exists(base + alt_ext):
                    alt_path = base + alt_ext
                    break
            if alt_path:
                src_path = alt_path
            else:
                print(f"[SKIP] No encontrado: {src_path}")
                continue

        try:
            img = Image.open(src_path).convert("RGBA")
        except Exception as e:
            print(f"[ERROR] No se pudo abrir {src_path}: {e}")
            continue

        img_np = np.array(img)

        mask = extract_silhouette(img_np)
        if mask is None or not np.any(mask):
            print(f"[FAIL] No se pudo extraer silueta: {out_name}")
            continue

        renders = {sz: compose_icon(mask, sz, **ICO_SPECS[sz]) for sz in sizes}
        master  = renders[256]

        ico_path = os.path.join(cat_dir, f"{out_name}.ico")

        master.save(
            ico_path, format="ICO",
            sizes=[(s, s) for s in sizes],
            append_images=[renders[s] for s in sizes if s != 256]
        )
        print(f"[OK] {category} -> {out_name}.ico")

print("\nFinalizado.")
