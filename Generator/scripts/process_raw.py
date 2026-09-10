import os
import io
import requests
from PIL import Image
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM

# Rutas relativas al proyecto (carpeta DesktopIcons/), a prueba de formateos/mudanzas.
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE, "raw")
OUT_DIR = os.path.join(BASE, "Premium")
PNG_DIR = os.path.join(BASE, "_scratch")

def save_image(img, base_name):
    img = img.resize((256, 256), Image.Resampling.LANCZOS)
    
    png_path = os.path.join(PNG_DIR, f"{base_name}.png")
    img.save(png_path, format="PNG")
    
    ico_path = os.path.join(OUT_DIR, f"{base_name}.ico")
    img.save(ico_path, format="ICO")

def process_png(path, base_name):
    try:
        img = Image.open(path).convert("RGBA")
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
        print(f"[OK] Processed {base_name}")
    except Exception as e:
        print(f"Error processing {base_name}: {e}")

def process_overwatch():
    try:
        resp = requests.get("https://cdn.simpleicons.org/overwatch/white", headers={'User-Agent': 'Mozilla/5.0'})
        if resp.status_code == 200:
            drawing = svg2rlg(io.BytesIO(resp.content))
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
            
            save_image(final, "Overwatch")
            print("[OK] Processed Overwatch")
    except Exception as e:
        print(f"Error processing Overwatch: {e}")

def main():
    if os.path.exists(RAW_DIR):
        for f in sorted(os.listdir(RAW_DIR)):
            if f.endswith('.png'):
                base_name = f.replace('.png', '')
                process_png(os.path.join(RAW_DIR, f), base_name)
    process_overwatch()

if __name__ == '__main__':
    main()
