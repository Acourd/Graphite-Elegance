import os
from PIL import Image

raw_dir = r"E:\Shoshin\IA_Proyect\DesktopIcons\2_Assets\Raw_Silhouettes"
for f in os.listdir(raw_dir):
    if f.lower().endswith('.webp'):
        path = os.path.join(raw_dir, f)
        img = Image.open(path).convert("RGBA")
        new_path = path.rsplit('.', 1)[0] + '.png'
        img.save(new_path, "PNG")
        os.remove(path)
        print(f"Converted {f} to PNG")
