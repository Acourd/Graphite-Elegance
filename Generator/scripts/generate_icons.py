import os
import io
import re
import requests
from PIL import Image
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM

# Rutas relativas al proyecto (carpeta DesktopIcons/), a prueba de formateos/mudanzas.
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESKTOP_DIRS = [
    os.path.join(os.path.expanduser("~"), "Desktop"),
    os.path.join(os.environ.get("PUBLIC", r"C:\Users\Public"), "Desktop"),
]

OUT_DIR = os.path.join(BASE, "Premium")
PNG_DIR = os.path.join(BASE, "_scratch")

def clean_app_name(name):
    name = name.replace('.lnk', '')
    name = re.sub(r' release-stable-win', '', name)
    name = re.sub(r' \d+$', '', name)
    return name

def get_slug(name):
    name = name.lower()
    if name == 'cliente de riot': return 'riotgames'
    if name == 'riot client': return 'riotgames'
    if name == 'vlc media player': return 'vlcmediaplayer'
    return re.sub(r'[^a-z0-9]', '', name)

def get_domain(name):
    name = name.lower()
    if 'obs' in name: return 'obsproject.com'
    if 'vlc' in name: return 'videolan.org'
    if 'steam' in name: return 'store.steampowered.com'
    if 'valorant' in name: return 'playvalorant.com'
    if 'riot' in name: return 'riotgames.com'
    if 'nordvpn' in name: return 'nordvpn.com'
    if 'discord' in name: return 'discord.com'
    if 'ccleaner' in name: return 'ccleaner.com'
    if 'terabox' in name: return 'terabox.com'
    if 'flow launcher' in name: return 'flowlauncher.com'
    return f"{get_slug(name)}.com"

def save_image(img, base_name):
    img = img.resize((256, 256), Image.Resampling.LANCZOS)
    
    png_path = os.path.join(PNG_DIR, f"{base_name}.png")
    img.save(png_path, format="PNG")
    
    ico_path = os.path.join(OUT_DIR, f"{base_name}.ico")
    img.save(ico_path, format="ICO")

def generate_from_svg(svg_bytes, base_name):
    try:
        drawing = svg2rlg(io.BytesIO(svg_bytes))
        if not drawing: return False
        
        png_data = renderPM.drawToString(drawing, fmt='PNG', dpi=300)
        img = Image.open(io.BytesIO(png_data)).convert("RGBA")
        
        alpha = img.split()[3]
        bg = Image.new("RGBA", img.size, (0, 0, 0, 255))
        white_layer = Image.new("RGBA", img.size, (255, 255, 255, 255))
        final = Image.composite(white_layer, bg, alpha)
        
        bbox = alpha.getbbox()
        if bbox:
            final = final.crop(bbox)
            size = max(final.size)
            new_size = int(size * 1.6)
            sq_bg = Image.new("RGBA", (new_size, new_size), (0, 0, 0, 255))
            offset = ((new_size - final.width) // 2, (new_size - final.height) // 2)
            sq_bg.paste(final, offset)
            final = sq_bg
        
        save_image(final, base_name)
        return True
    except Exception as e:
        print(f"SVG error: {e}")
        return False

def generate_from_png(png_bytes, base_name):
    try:
        img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
        alpha = img.split()[3]
        extrema = alpha.getextrema()
        
        if extrema[0] == 255 and extrema[1] == 255:
            return False
            
        bg = Image.new("RGBA", img.size, (0, 0, 0, 255))
        white_layer = Image.new("RGBA", img.size, (255, 255, 255, 255))
        final = Image.composite(white_layer, bg, alpha)
        
        bbox = alpha.getbbox()
        if bbox:
            final = final.crop(bbox)
            size = max(final.size)
            new_size = int(size * 1.6)
            sq_bg = Image.new("RGBA", (new_size, new_size), (0, 0, 0, 255))
            offset = ((new_size - final.width) // 2, (new_size - final.height) // 2)
            sq_bg.paste(final, offset)
            final = sq_bg
            
        save_image(final, base_name)
        return True
    except Exception as e:
        print(f"PNG error: {e}")
        return False

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(PNG_DIR, exist_ok=True)
        
    apps = set()
    for d in DESKTOP_DIRS:
        if os.path.exists(d):
            for f in os.listdir(d):
                if f.endswith('.lnk'):
                    apps.add(clean_app_name(f))
                    
    print(f"Found apps: {apps}")
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    for app in apps:
        print(f"Processing {app}...")
        success = False
        
        slug = get_slug(app)
        svg_url = f"https://cdn.simpleicons.org/{slug}/white"
        try:
            resp = requests.get(svg_url, headers=headers, timeout=5)
            if resp.status_code == 200:
                if generate_from_svg(resp.content, app):
                    print(f"[OK] SimpleIcons -> {app}")
                    success = True
        except: pass
        
        if not success:
            domain = get_domain(app)
            png_url = f"https://logo.clearbit.com/{domain}?size=256&format=png"
            try:
                resp = requests.get(png_url, headers=headers, timeout=5)
                if resp.status_code == 200:
                    if generate_from_png(resp.content, app):
                        print(f"[OK] Clearbit -> {app}")
                        success = True
            except: pass
            
        if not success:
            print(f"[FAIL] Could not generate icon for {app}")

if __name__ == '__main__':
    main()
