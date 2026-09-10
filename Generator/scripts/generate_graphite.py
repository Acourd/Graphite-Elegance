import os
import glob
from PIL import Image, ImageDraw, ImageFilter, ImageOps

_SCRIPTS   = os.path.dirname(os.path.abspath(__file__))
_GENERATOR = os.path.dirname(_SCRIPTS)
BASE_DIR   = os.path.dirname(_GENERATOR)
RAW_DIR = os.path.join(_GENERATOR, "assets", "Raw_Silhouettes")
OUT_DIR = os.path.join(BASE_DIR, "Graphite_Elegance_Release", "Icons", "ICO")

if not os.path.exists(OUT_DIR):
    os.makedirs(OUT_DIR)

def create_squircle_mask(size, radius):
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, size[0], size[1]), radius=radius, fill=255)
    return mask

def extract_silhouette(img):
    img = img.convert("RGBA")
    r, g, b, a = img.split()
    
    # If the image has a meaningful alpha channel (not all 255)
    extrema = a.getextrema()
    if extrema[0] < 255:
        return a
    
    # Otherwise, it's likely a JPG or solid background.
    # Convert to grayscale and threshold. Assume white background and dark logo,
    # or detect background color from corners.
    gray = img.convert("L")
    bg_color = gray.getpixel((0, 0))
    
    # Create mask where pixels are significantly different from background
    mask = Image.eval(gray, lambda p: 255 if abs(p - bg_color) > 30 else 0)
    
    # If the logo is mostly light on a dark background, invert the logic.
    # We just want the shape. We can check if corners are dark.
    if bg_color < 128:
        mask = Image.eval(gray, lambda p: 255 if abs(p - bg_color) > 30 else 0)
    else:
        mask = Image.eval(gray, lambda p: 255 if abs(p - bg_color) > 30 else 0)
    
    return mask

def process_image(filepath, filename):
    try:
        base_name = os.path.splitext(filename)[0]
        
        # 1. Load image and get silhouette mask
        img = Image.open(filepath)
        silhouette = extract_silhouette(img)
        
        # Crop to bounding box of the silhouette
        bbox = silhouette.getbbox()
        if bbox:
            silhouette = silhouette.crop(bbox)
        
        # Resize silhouette to fit nicely inside the icon (e.g. 150x150 max)
        target_size = 140
        silhouette.thumbnail((target_size, target_size), Image.Resampling.LANCZOS)
        
        # 2. Create the Graphite background (256x256)
        icon_size = 256
        bg = Image.new("RGBA", (icon_size, icon_size), (0, 0, 0, 0)) # Transparent base
        
        # Draw the squircle (Charcoal color #1E1E1E)
        squircle_mask = create_squircle_mask((icon_size, icon_size), radius=64)
        charcoal = Image.new("RGBA", (icon_size, icon_size), (30, 30, 30, 255))
        bg.paste(charcoal, (0, 0), squircle_mask)
        
        # 3. Create the white logo with a soft drop shadow
        # Shadow
        shadow_offset = (0, 4)
        shadow_layer = Image.new("RGBA", (icon_size, icon_size), (0, 0, 0, 0))
        shadow_x = (icon_size - silhouette.width) // 2 + shadow_offset[0]
        shadow_y = (icon_size - silhouette.height) // 2 + shadow_offset[1]
        
        # Draw black silhouette for shadow
        black_sil = Image.new("RGBA", silhouette.size, (0, 0, 0, 150)) # 150 alpha for shadow
        shadow_layer.paste(black_sil, (shadow_x, shadow_y), silhouette)
        shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=3))
        
        # Paste shadow onto background
        bg.alpha_composite(shadow_layer)
        
        # Main white logo
        logo_x = (icon_size - silhouette.width) // 2
        logo_y = (icon_size - silhouette.height) // 2
        white_sil = Image.new("RGBA", silhouette.size, (255, 255, 255, 255))
        bg.paste(white_sil, (logo_x, logo_y), silhouette)
        
        # Save as PNG
        out_png = os.path.join(OUT_DIR, f"{base_name}.png")
        bg.save(out_png, "PNG")
        
        # Save as ICO
        out_ico = os.path.join(OUT_DIR, f"{base_name}.ico")
        bg.save(out_ico, "ICO")
        
        print(f"[OK] Processed {base_name}")
    except Exception as e:
        print(f"[ERROR] Failed to process {filename}: {e}")

if __name__ == "__main__":
    files = glob.glob(os.path.join(RAW_DIR, "*.*"))
    for f in files:
        if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.ico')):
            process_image(f, os.path.basename(f))
