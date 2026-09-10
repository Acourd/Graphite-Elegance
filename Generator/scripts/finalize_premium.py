import os
import re
import shutil
from PIL import Image

BASE_DIR = r"E:\Shoshin\IA_Proyect\DesktopIcons\1_Themes\Graphite_Elegance"
SELECTION_DIR = os.path.join(BASE_DIR, "Premium_Selection")
ICO_DIR = os.path.join(BASE_DIR, "ICO")
PNG_DIR = os.path.join(BASE_DIR, "PNG")
RESPALDO_DIR = os.path.join(BASE_DIR, "REspaldo")

def normalize_name(f):
    # Remove extension
    name = os.path.splitext(f)[0]
    # Remove hyphens, underscores and extra spaces, lowercase
    name = re.sub(r'[\-_]', ' ', name)
    name = re.sub(r'\s+', ' ', name).strip().lower()
    return name

def run_cleanup():
    if not os.path.exists(SELECTION_DIR):
        print("Selection directory not found. Exiting.")
        return

    # 1. Deduplicate
    print("Deduplicating...")
    unique_apps = {}
    for f in os.listdir(SELECTION_DIR):
        if not f.endswith('.ico'): continue
        
        norm = normalize_name(f)
        
        # Prefer names without hyphens/underscores or with spaces (e.g. 'Lossless Scaling.ico' > 'lossless-scaling.ico')
        if norm in unique_apps:
            existing = unique_apps[norm]
            # Simple heuristic: title case with spaces is usually better looking filename
            if f.replace('.ico', '').istitle() and ' ' in f:
                unique_apps[norm] = f
            elif ' ' in f and ' ' not in existing:
                unique_apps[norm] = f
            # otherwise keep existing
        else:
            unique_apps[norm] = f

    print(f"Selected {len(unique_apps)} unique icons out of {len(os.listdir(SELECTION_DIR))}.")

    # 2. Overwrite ICO directory & Generate PNG
    print("Populating ICO and PNG directories...")
    # Clear current ICO/PNG to ensure clean slate? The user said "sustituir... en la carpeta original".
    # I'll clear them to be absolutely sure there are no leftovers.
    if os.path.exists(ICO_DIR): shutil.rmtree(ICO_DIR)
    if os.path.exists(PNG_DIR): shutil.rmtree(PNG_DIR)
    os.makedirs(ICO_DIR)
    os.makedirs(PNG_DIR)

    for norm, f in unique_apps.items():
        src_ico = os.path.join(SELECTION_DIR, f)
        dst_ico = os.path.join(ICO_DIR, f)
        dst_png = os.path.join(PNG_DIR, f.replace('.ico', '.png'))
        
        # Copy ICO
        shutil.copy2(src_ico, dst_ico)
        
        # Generate PNG (read largest frame from ICO)
        try:
            img = Image.open(src_ico)
            # Pillow reads the largest size automatically or provides it
            img.save(dst_png, format="PNG")
        except Exception as e:
            print(f"Error converting {f} to PNG: {e}")

    # 3. Purge REspaldo and Premium_Selection
    print("Purging temporary directories...")
    try:
        shutil.rmtree(RESPALDO_DIR)
        shutil.rmtree(SELECTION_DIR)
        print("Purge complete.")
    except Exception as e:
        print(f"Error purging directories: {e}")

    print("Cleanup and finalization complete! All icons ready in ICO and PNG.")

if __name__ == "__main__":
    run_cleanup()
