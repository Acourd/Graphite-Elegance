"""
Phase 1: Copia Premium backups → release (ICO directo + PNG extraído del frame 256px).
Phase 2: Regenera Classroom desde SimpleIcons SVG con el pipeline Graphite.
"""
import os, shutil, io, requests
import cv2, numpy as np
from PIL import Image, ImageDraw

# ── Rutas (relativas al repo). PREM es una entrada opcional/legacy. ──────────
_SCRIPTS   = os.path.dirname(os.path.abspath(__file__))
_GENERATOR = os.path.dirname(_SCRIPTS)
_ROOT      = os.path.dirname(_GENERATOR)
PREM    = os.path.join(_GENERATOR, "_premium_in")
REL_ICO = os.path.join(_ROOT, "Graphite_Elegance_Release", "Icons", "ICO")
REL_PNG = os.path.join(_ROOT, "Graphite_Elegance_Release", "Icons", "PNG")
os.makedirs(REL_ICO, exist_ok=True)
os.makedirs(REL_PNG, exist_ok=True)

# ── Mapping Premium → nombre de release ──────────────────────────────────────
MAPPING = [
    ("aimlabs.ico",           "Aimlabs"),
    ("antigravity.ico",       "Antigravity"),
    ("atlauncher.ico",        "ATLauncher"),
    ("blitz.ico",             "Blitz"),
    ("canva.ico",             "Canva"),
    ("ccleaner.ico",          "Ccleaner"),
    ("chatgpt.ico",           "Chatgpt"),
    ("chrome.ico",            "Chrome"),
    ("Claude-ai-icon.svg.ico","Claude Ai"),
    ("riot client.ico",       "Riot Client"),
    ("discord.ico",           "Discord"),
    ("excel.ico",             "Excel"),
    ("geek-uninstaller.ico",  "Geek Uninstaller"),
    ("github.ico",            "Github"),
    ("gmail.ico",             "Gmail"),
    ("go.ico",                "Go"),
    ("helium.ico",            "Helium"),
    ("hytale.ico",            "Hytale"),
    ("images.ico",            "Images"),
    ("iso.ico",               "Iso"),
    ("kindle.ico",            "Kindle"),
    ("labymod.ico",           "Labymod"),
    ("linkedin.ico",          "Linkedin"),
    ("lossless-scaling.ico",  "Lossless Scaling"),
    ("minecraft.ico",         "Minecraft"),
    ("MSIAFTERBURNER.ico",    "Msiafterburner"),
    ("notebooklm.ico",        "NotebookLM"),
    ("nvidia.ico",            "Nvidia App"),
    ("obs.ico",               "Obs"),
    ("olympus.ico",           "Olympus"),
    ("OPenDESInG.ico",        "Opendesign"),
    ("optimizer.ico",         "Optimizer"),
    ("outlook.ico",           "Outlook"),
    ("perplexity.ico",        "Perplexity"),
    ("pinterest.ico",         "Pinterest"),
    ("powerpoint.ico",        "Powerpoint"),
    ("ProcessLasso.ico",      "Process Lasso"),
    ("reddit.ico",            "Reddit"),
    ("roblox.ico",            "Roblox"),
    ("spotify.ico",           "Spotify"),
    ("steam.ico",             "Steam"),
    ("terraria.ico",          "Terraria"),
    ("tmodloader.ico",        "tModLoader"),
    ("valorant.ico",          "Valorant"),
    ("vscode.ico",            "Vscode"),
    ("word.ico",              "Word"),
    ("youtubemusic.ico",      "Youtube Music"),
]

# ── Graphite pipeline (para Classroom) ───────────────────────────────────────
SS = 4
ICO_SPECS = {
    256: dict(logo_frac=0.50, border=True,  shadow=True),
    128: dict(logo_frac=0.50, border=True,  shadow=True),
    64:  dict(logo_frac=0.52, border=True,  shadow=True),
    48:  dict(logo_frac=0.54, border=True,  shadow=True),
    32:  dict(logo_frac=0.62, border=False, shadow=False),
    16:  dict(logo_frac=0.68, border=False, shadow=False),
}

def resize_sil_aa(mask, target_long):
    x, y, bw, bh = cv2.boundingRect(mask)
    mask = mask[y:y+bh, x:x+bw]
    scale = target_long / max(bw, bh)
    mask  = cv2.GaussianBlur(mask,(0,0),0.5/scale) if scale<1.0 else mask
    interp = cv2.INTER_AREA if scale<1.0 else cv2.INTER_CUBIC
    nw = (max(1,round(bw*scale)), max(1,round(bh*scale)))
    a = cv2.resize(mask, nw, interpolation=interp).astype(np.float32)/255
    a = np.clip((a-0.30)/0.40,0,1); a = a*a*(3-2*a)
    a8 = (a*255).astype(np.uint8)
    return Image.fromarray(np.dstack([np.full_like(a8,255)]*3+[a8]),"RGBA")

def compose(mask, size, logo_frac, border=True, shadow=True):
    S = size*SS; r = (60/256)*S
    grad  = np.linspace(45.,10.,S,dtype=np.float32)[:,None]
    noise = np.random.default_rng(0).uniform(-0.5,0.5,(S,S)).astype(np.float32)
    g     = np.clip(np.broadcast_to(grad,(S,S))+noise,0,255).astype(np.uint8)
    canvas= Image.fromarray(np.dstack([g,g,g,np.full((S,S),255,np.uint8)]),"RGBA")
    sq    = Image.new("L",(S,S),0)
    ImageDraw.Draw(sq).rounded_rectangle((0,0,S-1,S-1),r,fill=255)
    canvas.putalpha(sq)
    if border:
        b=Image.new("RGBA",(S,S),(0,0,0,0))
        ImageDraw.Draw(b).rounded_rectangle((SS//2,SS//2,S-1-SS//2,S-1-SS//2),r,outline=(255,255,255,30),width=SS)
        canvas.alpha_composite(b)
    logo=resize_sil_aa(mask,max(1,int(S*logo_frac)))
    off =((S-logo.width)//2,(S-logo.height)//2)
    if shadow:
        la=np.zeros((S,S),np.float32)
        la[off[1]:off[1]+logo.height,off[0]:off[0]+logo.width]=np.asarray(logo)[:,:,3]/255.
        u=S/256.
        amb=cv2.GaussianBlur(la,(0,0),8*u)*0.30
        key=cv2.GaussianBlur(la,(0,0),3*u)*0.50
        dy=max(1,int(4*u)); ks=np.zeros_like(key); ks[dy:,:]=key[:-dy,:]
        sh=np.clip(amb+ks,0,1)*np.asarray(sq,np.float32)/255
        sr=np.zeros((S,S,4),np.uint8); sr[:,:,3]=(sh*255).astype(np.uint8)
        canvas.alpha_composite(Image.fromarray(sr,"RGBA"))
    canvas.alpha_composite(logo,off)
    return canvas.resize((size,size),Image.Resampling.LANCZOS)

def save_graphite(mask, name):
    sizes = sorted(ICO_SPECS,reverse=True)
    renders = {sz: compose(mask,sz,**ICO_SPECS[sz]) for sz in sizes}
    m = renders[256]
    m.save(os.path.join(REL_PNG,f"{name}.png"),format="PNG")
    m.save(os.path.join(REL_ICO,f"{name}.ico"),format="ICO",
           sizes=[(s,s) for s in sizes],
           append_images=[renders[s] for s in sizes if s!=256])

# ── PHASE 1: Bulk copy from Premium ──────────────────────────────────────────
print("=== PHASE 1: Premium bulk copy ===")
ok, skip = 0, 0
for src_name, out_name in MAPPING:
    src = os.path.join(PREM, src_name)
    if not os.path.exists(src):
        print(f"  [SKIP] {src_name}")
        skip += 1
        continue

    # Copy ICO (preserves original 7-size Premium quality)
    shutil.copy2(src, os.path.join(REL_ICO, f"{out_name}.ico"))

    # Extract 256px frame → PNG
    ico = Image.open(src)
    frame = None
    for i in range(20):
        try:
            ico.seek(i)
            if ico.size == (256,256):
                frame = ico.copy().convert("RGBA"); break
        except EOFError:
            break
    if frame:
        frame.save(os.path.join(REL_PNG, f"{out_name}.png"), format="PNG")
        print(f"  [OK] {out_name}")
        ok += 1
    else:
        print(f"  [WARN] {out_name} - ICO copiado, sin frame 256px")

print(f"\nPhase 1: {ok} OK, {skip} skipped\n")

# ── PHASE 2: Classroom via SimpleIcons SVG ────────────────────────────────────
print("=== PHASE 2: Classroom (SimpleIcons SVG) ===")
try:
    from svglib.svglib import svg2rlg
    from reportlab.graphics import renderPM

    svg_url = "https://cdn.jsdelivr.net/npm/simple-icons@v11/icons/googleclassroom.svg"
    r = requests.get(svg_url, timeout=8)
    if r.status_code == 200:
        drawing = svg2rlg(io.BytesIO(r.content))
        scale   = 1024 / max(drawing.width, drawing.height)
        png_data= renderPM.drawToString(drawing, fmt="PNG", dpi=int(72*scale))
        img = Image.open(io.BytesIO(png_data)).convert("RGBA")
        gray= cv2.cvtColor(np.array(img), cv2.COLOR_RGBA2GRAY)
        mask= np.where((255-gray)>=128, 255, 0).astype(np.uint8)
        if np.any(mask):
            save_graphite(mask, "Classroom")
            print("  [OK] Classroom")
        else:
            print("  [FAIL] Classroom - mask vacío")
    else:
        print(f"  [FAIL] Classroom - HTTP {r.status_code}")
except ImportError:
    print("  [WARN] svglib no disponible, usando fallback PNG de SimpleIcons")
    try:
        # SimpleIcons CDN también sirve PNG via shields.io si hay proxy
        png_url = "https://cdn.simpleicons.org/googleclassroom/ffffff"
        r = requests.get(png_url, timeout=8, headers={"User-Agent":"Mozilla/5.0"})
        if r.status_code == 200 and len(r.content) > 500:
            img = Image.open(io.BytesIO(r.content)).convert("RGBA")
            arr = np.array(img)
            alpha = arr[:,:,3]
            mask  = np.where(alpha >= 64, 255, 0).astype(np.uint8)
            if np.any(mask):
                save_graphite(mask, "Classroom")
                print("  [OK] Classroom (PNG fallback)")
            else:
                print("  [FAIL] Classroom - sin silueta en PNG")
        else:
            print(f"  [FAIL] Classroom fallback PNG - HTTP {r.status_code}")
    except Exception as e:
        print(f"  [ERROR] Classroom: {e}")
except Exception as e:
    print(f"  [ERROR] Classroom: {e}")

print("\nFinalizado.")
