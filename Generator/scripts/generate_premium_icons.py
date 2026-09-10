import os
import io
import re
import argparse
import hashlib
import requests
from PIL import Image, ImageDraw
import cv2
import numpy as np
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM

# Hook opcional: si rembg esta instalado, se usa para fondos fotorealistas.
try:
    from rembg import remove as rembg_remove
    HAS_REMBG = True
except ImportError:
    HAS_REMBG = False

# Rutas relativas al repo (Generator/scripts/ -> Generator/ -> raiz del repo).
_SCRIPTS = os.path.dirname(os.path.abspath(__file__))
_GENERATOR = os.path.dirname(_SCRIPTS)
BASE = os.path.dirname(_GENERATOR)
OUT_DIR = os.path.join(BASE, "Graphite_Elegance_Release", "Icons", "ICO")
PNG_DIR = os.path.join(BASE, "Graphite_Elegance_Release", "Icons", "PNG")
REVIEW_DIR = os.path.join(BASE, "Graphite_Elegance_Release", "Icons", "_Review")
RAW_DIR = os.path.join(_GENERATOR, "assets", "Raw_Silhouettes")
LOCK_PATH = os.path.join(_GENERATOR, "assets", "Raw_Silhouettes.lock.json")
DESKTOP_DIRS = [
    os.path.join(os.path.expanduser("~"), "Desktop"),
    os.path.join(os.environ.get("PUBLIC", r"C:\Users\Public"), "Desktop"),
]

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(PNG_DIR, exist_ok=True)
os.makedirs(REVIEW_DIR, exist_ok=True)

# Factor de supersampling: todo se compone a size*SS y se reduce una sola vez.
SS = 4

# Especificacion parametrica por tamano de ICO. A 32/16 px el borde de 1px y la
# sombra se convierten en ruido, y el 50% optico se percibe como un punto, asi
# que el logo crece y los adornos se omiten.
ICO_SPECS = {
    256: dict(logo_frac=0.50, border=True, shadow=True),
    128: dict(logo_frac=0.50, border=True, shadow=True),
    64: dict(logo_frac=0.52, border=True, shadow=True),
    48: dict(logo_frac=0.54, border=True, shadow=True),
    32: dict(logo_frac=0.62, border=False, shadow=False),
    16: dict(logo_frac=0.68, border=False, shadow=False),
}

# Umbrales de cuarentena: resultados de baja confianza van a _Review, no al set.
MIN_SOURCE_PX = 200
MIN_COVERAGE = 0.02
MAX_COVERAGE = 0.90
MAX_ISLANDS = 8

APP_MAPPINGS = {
    'canva': ('simpleicons', 'canva'),
    'excel': ('simpleicons', 'microsoftexcel'),
    'reddit': ('simpleicons', 'reddit'),
    'github': ('simpleicons', 'github'),
    'gmail': ('simpleicons', 'gmail'),
    'go': ('simpleicons', 'go'),
    'linkedin': ('simpleicons', 'linkedin'),
    'outlook': ('simpleicons', 'microsoftoutlook'),
    'perplexity': ('simpleicons', 'perplexity'),
    'pinterest': ('simpleicons', 'pinterest'),
    'powerpoint': ('simpleicons', 'microsoftpowerpoint'),
    'roblox': ('simpleicons', 'roblox'),
    'spotify': ('simpleicons', 'spotify'),
    'to-do list': ('simpleicons', 'microsofttodo'),
    'todolist': ('simpleicons', 'microsofttodo'),
    'visual studio code': ('simpleicons', 'visualstudiocode'),
    'vscode': ('simpleicons', 'visualstudiocode'),
    'word': ('simpleicons', 'microsoftword'),

    # New Mappings
    'nordvpn': ('simpleicons', 'nordvpn'),
    'obs studio': ('simpleicons', 'obsstudio'),
    'obs': ('simpleicons', 'obsstudio'),
    'vlc media player': ('simpleicons', 'vlcmediaplayer'),
    'vlc': ('simpleicons', 'vlcmediaplayer'),
    'overwatch 2': ('simpleicons', 'overwatch'),
    'overwatch': ('simpleicons', 'overwatch'),
    'discord': ('simpleicons', 'discord'),
    'ccleaner': ('simpleicons', 'ccleaner'),
    'steam': ('simpleicons', 'steam'),
    'valorant': ('simpleicons', 'valorant'),
    'riot client': ('simpleicons', 'riotgames'),
    'cliente de riot': ('simpleicons', 'riotgames'),
    'riot-client': ('simpleicons', 'riotgames'),

    # Clearbit Fallbacks
    'aimlabs': ('clearbit', 'aimlabs.com'),
    'process lasso': ('clearbit', 'bitsum.com'),
    'processlassolauncher': ('clearbit', 'bitsum.com'),
    'terabox': ('clearbit', 'terabox.com'),
    'labymod launcher': ('clearbit', 'labymod.net'),
    'flow launcher': ('clearbit', 'flowlauncher.com'),
    'atlauncher': ('clearbit', 'atlauncher.com'),
    'msi afterburner': ('clearbit', 'msi.com'),
    'helium': ('clearbit', 'helium.com'),

    # Aplicaciones de escritorio: NVIDIA y Medal
    'nvidia app': ('simpleicons', 'nvidia'),
    'medal': ('clearbit', 'medal.tv'),

    # Steam grid/Clearbit fallback for games/tools without simpleicons
    'blatmoferus': ('clearbit', 'thegamekitchen.com'),
    'blasphemous': ('clearbit', 'thegamekitchen.com'),
    'g-cuninstaller': ('clearbit', 'geekuninstaller.com'),
    'geek-uninstaller': ('clearbit', 'geekuninstaller.com'),
    'hytel': ('clearbit', 'hytale.com'),
    'hytale': ('clearbit', 'hytale.com'),
    'the lostless': ('clearbit', 'store.steampowered.com'),
    'lossless-scaling': ('clearbit', 'store.steampowered.com'),
    'scalin': ('clearbit', 'store.steampowered.com'),
    'notebooklm': ('clearbit', 'google.com'),
    'optimizer': ('clearbit', 'github.com')
}

NAME_FIXES = {
    'msi afterburner': 'MSI Afterburner',
    'opendesing': 'OpenDesign',
    'process lasso': 'Process Lasso',
    'wallpaper engine': 'Wallpaper Engine',
    'valorant tracker': 'Valorant Tracker',
    'mini cozy room': 'Mini Cozy Room',
    'atlauncher': 'ATLauncher',
    'lossless scaling': 'Lossless Scaling',
    'blasphemous': 'Blasphemous',
    'ai studio': 'AI Studio',
    'antigravity': 'Antigravity',
    'epic games launcher': 'Epic Games',
    'epicgames': 'Epic Games',
    'notebooklm': 'NotebookLM',
    'tmodloader': 'tModLoader',
    'claude ai icon.svg': 'Claude AI',
    'cliente de riot': 'Riot Client',
    'riot client': 'Riot Client',
    'microsoft edge': 'Edge',
    'nvidia app': 'Nvidia App',
    'medal': 'Medal',
}


# ---------------------------------------------------------------------------
# Extraccion de silueta
# ---------------------------------------------------------------------------

def extract_silhouette(img_rgba):
    """Silueta binaria robusta a partir de HxWx4 uint8.

    - Con canal alfa real, el alfa es la verdad absoluta.
    - Sin alfa, se umbraliza la distancia perceptual (CIELab) al color de
      fondo muestreado en las esquinas: sobrevive a logos claros o saturados
      que un OTSU sobre gris hace desaparecer.
    - Agujeros: se rellena solo el ruido (<0.5% del logo); las contraformas
      grandes (Spotify, GitHub) se preservan porque son la identidad del logo.

    Devuelve (mask, stats) o (None, stats) si no hay nada utilizable.
    """
    rgb, alpha = img_rgba[:, :, :3], img_rgba[:, :, 3]
    h, w = rgb.shape[:2]

    if not np.all(alpha == 255):
        binmask = np.where(alpha >= 64, 255, 0).astype(np.uint8)
        # El alfa da el contorno, pero los detalles internos claros (el play de
        # YouTube, la M de Gmail) no son transparentes: se tallan como
        # contraforma si hay contraste interior significativo.
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


def resize_silhouette_aa(mask, target_long):
    """Recorta al bbox y reescala con rampa de alfa limpia (sin ringing).

    Pre-blur gaussiano proporcional al factor de reduccion (filtro paso-bajo
    correcto), resize INTER_AREA y curva smoothstep para recuperar nitidez.
    Devuelve un RGBA blanco listo para componer.
    """
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
    a8 = (a * 255).astype(np.uint8)
    logo = np.dstack([np.full_like(a8, 255)] * 3 + [a8])
    return Image.fromarray(logo, "RGBA")


# ---------------------------------------------------------------------------
# Composicion
# ---------------------------------------------------------------------------

def compose_icon(mask, size, logo_frac, border=True, shadow=True):
    """Compone un icono completo a size x size, renderizando a size*SS y
    reduciendo una sola vez con LANCZOS."""
    S = size * SS
    radius = (60 / 256) * S

    # Gradiente vertical en float + dithering de +-0.5 para eliminar banding.
    grad = np.linspace(45.0, 10.0, S, dtype=np.float32)[:, None]
    noise = np.random.default_rng(0).uniform(-0.5, 0.5, (S, S)).astype(np.float32)
    g = np.clip(np.broadcast_to(grad, (S, S)) + noise, 0, 255).astype(np.uint8)
    canvas = Image.fromarray(np.dstack([g, g, g, np.full((S, S), 255, np.uint8)]), "RGBA")

    sq = Image.new("L", (S, S), 0)
    ImageDraw.Draw(sq).rounded_rectangle((0, 0, S - 1, S - 1), radius, fill=255)
    canvas.putalpha(sq)

    if border:
        b = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        ImageDraw.Draw(b).rounded_rectangle(
            (SS // 2, SS // 2, S - 1 - SS // 2, S - 1 - SS // 2),
            radius, outline=(255, 255, 255, 30), width=SS)
        canvas.alpha_composite(b)

    logo = resize_silhouette_aa(mask, max(1, int(S * logo_frac)))
    off = ((S - logo.width) // 2, (S - logo.height) // 2)

    if shadow:
        # Sombra dual: ambient (difusa, sin offset) + key (definida, caida +4y).
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
        sh *= np.asarray(sq, np.float32) / 255  # la sombra no sale del squircle
        sh_rgba = np.zeros((S, S, 4), np.uint8)
        sh_rgba[:, :, 3] = (sh * 255).astype(np.uint8)
        canvas.alpha_composite(Image.fromarray(sh_rgba, "RGBA"))

    canvas.alpha_composite(logo, off)
    return canvas.resize((size, size), Image.Resampling.LANCZOS)


def nice_name_for(base_name):
    nice = base_name.replace('-', ' ').replace('_', ' ').title()
    return NAME_FIXES.get(nice.lower(), nice)


def apply_premium_style(mask, base_name, review_reasons=None):
    """Compone PNG maestro + ICO con cada resolucion renderizada a medida.
    Si hay motivos de revision, el resultado va a _Review en vez del set."""
    if mask is None or not np.any(mask):
        return False

    renders = {sz: compose_icon(mask, sz, **spec) for sz, spec in ICO_SPECS.items()}
    master = renders[256]
    nice_name = nice_name_for(base_name)

    if review_reasons:
        png_dir = ico_dir = REVIEW_DIR
        print(f"[REVIEW] {nice_name}: {'; '.join(review_reasons)}")
    else:
        png_dir, ico_dir = PNG_DIR, OUT_DIR

    master.save(os.path.join(png_dir, f"{nice_name}.png"), format="PNG")
    sizes = sorted(ICO_SPECS, reverse=True)
    master.save(
        os.path.join(ico_dir, f"{nice_name}.ico"), format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=[renders[s] for s in sizes if s != 256])
    return True


# ---------------------------------------------------------------------------
# Fuentes: SVG y raster
# ---------------------------------------------------------------------------

def generate_from_svg(svg_img_bytes, base_name):
    try:
        drawing = svg2rlg(io.BytesIO(svg_img_bytes))
        if not drawing:
            return False

        # dpi calculado para que el lado largo mida ~1024 px reales.
        scale = 1024 / max(drawing.width, drawing.height)
        png_data = renderPM.drawToString(drawing, fmt="PNG", dpi=int(72 * scale))

        img = Image.open(io.BytesIO(png_data)).convert("RGBA")
        gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGBA2GRAY)
        # Cairo rasteriza negro sobre blanco con AA; luminancia invertida = alfa.
        mask = np.where((255 - gray) >= 128, 255, 0).astype(np.uint8)
        if not np.any(mask):
            return False
        return apply_premium_style(mask, base_name)
    except Exception as e:
        print(f"SVG error for {base_name}: {e}")
        return False


def generate_from_png(png_bytes, base_name):
    try:
        img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
        reasons = []
        if max(img.size) < MIN_SOURCE_PX:
            reasons.append(f"fuente de baja resolucion ({img.width}x{img.height})")

        img_np = np.array(img)
        if HAS_REMBG and np.all(img_np[:, :, 3] == 255):
            try:
                img_np = np.array(rembg_remove(img).convert("RGBA"))
            except Exception:
                pass

        mask, stats = extract_silhouette(img_np)
        if mask is None:
            return False
        if stats['coverage'] < MIN_COVERAGE:
            reasons.append(f"cobertura sospechosamente baja ({stats['coverage']:.1%})")
        if stats['coverage'] > MAX_COVERAGE:
            reasons.append(f"cobertura sospechosamente alta ({stats['coverage']:.1%})")
        if stats['islands'] > MAX_ISLANDS:
            reasons.append(f"demasiados fragmentos ({stats['islands']})")

        return apply_premium_style(mask, base_name, reasons)
    except Exception as e:
        print(f"PNG error for {base_name}: {e}")
        return False


# ---------------------------------------------------------------------------
# Orquestacion
# ---------------------------------------------------------------------------

def process_app(app_name):
    headers = {'User-Agent': 'Mozilla/5.0'}
    clean_name = app_name.lower().replace('.lnk', '').replace('.ico', '')
    clean_name = re.sub(r' release-stable-win', '', clean_name)
    clean_name = re.sub(r' \d+$', '', clean_name)
    clean_name = clean_name.strip()

    print(f"Processing {clean_name}...")

    mapped_domain = None
    if clean_name in APP_MAPPINGS:
        source, target = APP_MAPPINGS[clean_name]
        if source == 'clearbit':
            mapped_domain = target
        if source == 'simpleicons':
            svg_url = f"https://cdn.jsdelivr.net/npm/simple-icons@v11/icons/{target}.svg"
            try:
                resp = requests.get(svg_url, headers=headers, timeout=5)
                if resp.status_code == 200:
                    if generate_from_svg(resp.content, clean_name):
                        print(f"[OK] SimpleIcons (Mapped) -> {clean_name}")
                        return
            except requests.RequestException:
                pass
        elif source == 'clearbit':
            png_url = f"https://logo.clearbit.com/{target}?size=512&format=png"
            try:
                resp = requests.get(png_url, headers=headers, timeout=5)
                if resp.status_code == 200:
                    if generate_from_png(resp.content, clean_name):
                        print(f"[OK] Clearbit (Mapped) -> {clean_name}")
                        return
            except requests.RequestException:
                pass

    slug = re.sub(r'[^a-z0-9]', '', clean_name)
    svg_url = f"https://cdn.jsdelivr.net/npm/simple-icons@v11/icons/{slug}.svg"
    try:
        resp = requests.get(svg_url, headers=headers, timeout=5)
        if resp.status_code == 200:
            if generate_from_svg(resp.content, clean_name):
                print(f"[OK] SimpleIcons -> {clean_name}")
                return
    except requests.RequestException:
        pass

    # Nota: logo.clearbit.com fue clausurado por HubSpot; se mantiene el intento
    # por si reviviera, pero el rescate real es el favicon del dominio mapeado.
    domain = mapped_domain or f"{slug}.com"
    png_url = f"https://logo.clearbit.com/{domain}?size=512&format=png"
    try:
        resp = requests.get(png_url, headers=headers, timeout=5)
        if resp.status_code == 200:
            if generate_from_png(resp.content, clean_name):
                print(f"[OK] Clearbit -> {clean_name}")
                return
    except requests.RequestException:
        pass

    # Google Favicons Fallback (suele venir reescalado: candidato a _Review)
    favicon_url = f"https://www.google.com/s2/favicons?sz=256&domain={domain}"
    try:
        resp = requests.get(favicon_url, headers=headers, timeout=5)
        if resp.status_code == 200:
            if generate_from_png(resp.content, clean_name):
                print(f"[OK] Google Favicons -> {clean_name}")
                return
    except requests.RequestException:
        pass

    print(f"[FAIL] Could not generate icon for {clean_name}")


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_sources(raw_dir=RAW_DIR, lock_path=LOCK_PATH):
    """Verify local source assets against their pinned SHA-256 lock."""
    if not os.path.isfile(lock_path):
        print(f"[WARN] Sin lock de fuentes ({lock_path}); genéralo con hash_assets.py")
        return True
    import json
    with open(lock_path, "r", encoding="utf-8") as fh:
        lock = json.load(fh)
    problems = []
    for name, digest in sorted(lock.items()):
        path = os.path.join(raw_dir, name)
        if not os.path.isfile(path):
            problems.append(f"falta {name}")
        elif _sha256(path) != digest:
            problems.append(f"hash distinto {name}")
    for problem in problems:
        print(f"  [FUENTE] {problem}")
    if problems:
        return False
    print(f"[INFO] {len(lock)} fuentes locales verificadas")
    return True


def process_raw_images():
    if os.path.exists(RAW_DIR):
        print("Processing RAW directory for local icons...")
        valid_exts = ('.png', '.jpg', '.jpeg', '.webp', '.ico')
        for f in sorted(os.listdir(RAW_DIR)):  # stable order
            if f.lower().endswith(valid_exts):
                base_name = os.path.splitext(f)[0].strip()
                path = os.path.join(RAW_DIR, f)
                with open(path, 'rb') as fp:
                    if generate_from_png(fp.read(), base_name):
                        print(f"[OK] Local Raw -> {base_name}")


DEFAULT_APPS = (
    'canva', 'excel', 'reddit', 'github', 'gmail', 'go', 'linkedin',
    'outlook', 'perplexity', 'pinterest', 'powerpoint', 'roblox',
    'spotify', 'to-do list', 'vscode', 'word', 'blasphemous',
    'geek-uninstaller', 'hytale', 'lossless-scaling', 'notebooklm',
    'optimizer', 'discord', 'ccleaner', 'steam', 'valorant',
    'riot-client', 'obs', 'terraria', 'minecraft', 'chatgpt',
    'nvidia app', 'medal',
)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Generador Graphite Elegance. Por defecto es REPRODUCIBLE: "
                    "solo usa las fuentes locales y en orden estable.")
    parser.add_argument("--online", action="store_true",
                        help="Permitir descargas mutables (SimpleIcons/Clearbit).")
    parser.add_argument("--from-desktop", action="store_true",
                        help="Incluir los accesos del escritorio del operador (no reproducible).")
    parser.add_argument("--verify-sources", action="store_true",
                        help="Verificar hashes de Raw_Silhouettes.lock.json antes de generar.")
    args = parser.parse_args(argv)

    if args.verify_sources and not verify_sources():
        print("[FAIL] Fuentes locales alteradas; abortando.")
        return 1

    if args.online or args.from_desktop:
        apps = set()
        if args.online:
            apps.update(DEFAULT_APPS)
        if args.from_desktop:
            for d in DESKTOP_DIRS:
                if os.path.exists(d):
                    for f in sorted(os.listdir(d)):
                        if f.endswith('.lnk'):
                            name = re.sub(r' release-stable-win', '', f.replace('.lnk', '').strip())
                            apps.add(re.sub(r' \d+$', '', name))
        for app in sorted(apps):
            process_app(app)

    # Local, versioned assets -> deterministic output.
    process_raw_images()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
