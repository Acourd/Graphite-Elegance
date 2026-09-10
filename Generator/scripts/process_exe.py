import os
import cv2
import numpy as np
from PIL import Image

# Rutas relativas al proyecto (carpeta DesktopIcons/), a prueba de formateos/mudanzas.
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE, "raw")
OUT_DIR = os.path.join(BASE, "Premium")
PNG_DIR = os.path.join(BASE, "_scratch")

def save_image(img, base_name):
    # Resize and paste onto a larger black square to look like a proper app icon
    size = max(img.size)
    new_size = int(size * 1.6)
    sq_bg = Image.new("RGBA", (new_size, new_size), (0, 0, 0, 255))
    offset = ((new_size - img.width) // 2, (new_size - img.height) // 2)
    sq_bg.paste(img, offset)
    
    sq_bg = sq_bg.resize((256, 256), Image.Resampling.LANCZOS)
    
    png_path = os.path.join(PNG_DIR, f"{base_name}.png")
    sq_bg.save(png_path, format="PNG")
    
    ico_path = os.path.join(OUT_DIR, f"{base_name}.ico")
    sq_bg.save(ico_path, format="ICO")

def process_image(path, base_name):
    try:
        # Load image with alpha channel
        img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        if img is None: return
        
        # Ensure it has 4 channels
        if img.shape[2] == 3:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
            
        b, g, r, a = cv2.split(img)
        
        # Create a grayscale version of the BGR part
        gray = cv2.cvtColor(cv2.merge([b,g,r]), cv2.COLOR_BGR2GRAY)
        
        # We need a smart threshold. Otsu's method works well to separate background/foreground.
        # But we only want to consider pixels where alpha > 0
        mask = a > 0
        if not np.any(mask): return
        
        valid_pixels = gray[mask]
        
        # If the image is mostly uniform (like a solid circle), standard threshold might fail
        # Let's try Otsu
        ret, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        
        # Some icons like Discord are just a solid color shape with transparent bg.
        # For these, the alpha channel itself is the best logo shape!
        # We can detect this by checking if the variance of gray pixels is very low.
        variance = np.var(valid_pixels)
        
        if variance < 500:
            # It's a solid shape (like Discord or Riot Client).
            # Just use the alpha channel as the white shape.
            final_a = a
        else:
            # It has internal details (like Steam or Antigravity).
            # Use the thresholded image. 
            # We want the bright parts to be white, dark parts to be black.
            # Mask out the transparent areas
            thresh[~mask] = 0
            final_a = thresh
            
        # Create a new RGBA image: White pixels where final_a > 0
        out_img = np.zeros((img.shape[0], img.shape[1], 4), dtype=np.uint8)
        
        # If the resulting threshold made almost everything black, invert it
        if np.sum(final_a > 0) < (final_a.size * 0.05):
            final_a = cv2.bitwise_not(thresh)
            final_a[~mask] = 0
            
        out_img[final_a > 0] = [255, 255, 255, 255]
        
        # Convert back to PIL
        pil_img = Image.fromarray(cv2.cvtColor(out_img, cv2.COLOR_BGRA2RGBA))
        
        # Crop to bbox
        bbox = pil_img.getbbox()
        if bbox:
            pil_img = pil_img.crop(bbox)
            
        save_image(pil_img, base_name)
        print(f"[OK] Processed {base_name}")
        
    except Exception as e:
        print(f"Error processing {base_name}: {e}")

def main():
    if os.path.exists(RAW_DIR):
        for f in os.listdir(RAW_DIR):
            if f.endswith('.png'):
                base_name = f.replace('.png', '')
                process_image(os.path.join(RAW_DIR, f), base_name)

if __name__ == '__main__':
    main()
