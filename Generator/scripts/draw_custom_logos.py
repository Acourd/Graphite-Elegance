import os
from PIL import Image, ImageDraw

RAW_DIR = r"E:\Shoshin\IA_Proyect\DesktopIcons\2_Assets\Raw_Silhouettes"
os.makedirs(RAW_DIR, exist_ok=True)

def draw_geek_uninstaller():
    # A crisp, minimalist trash can vector
    img = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Lid
    draw.rounded_rectangle([(156, 120), (356, 160)], radius=10, fill=(255,255,255,255))
    # Handle
    draw.rounded_rectangle([(216, 90), (296, 120)], radius=10, fill=(255,255,255,255))
    draw.rectangle([(236, 100), (276, 120)], fill=(0,0,0,0)) # Hole in handle
    
    # Body
    draw.polygon([(176, 170), (336, 170), (316, 420), (196, 420)], fill=(255,255,255,255))
    
    # Lines on body (transparent cutouts)
    draw.line([(226, 200), (236, 390)], fill=(0,0,0,0), width=15)
    draw.line([(286, 200), (276, 390)], fill=(0,0,0,0), width=15)
    
    img.save(os.path.join(RAW_DIR, "Geek Uninstaller.png"))
    print("Drew Geek Uninstaller vector.")

def draw_mini_cozy_room():
    # A minimalist isometric room / house icon
    img = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Base house
    draw.polygon([(256, 100), (100, 256), (100, 412), (412, 412), (412, 256)], fill=(255,255,255,255))
    
    # Door cutout
    draw.rectangle([(216, 312), (296, 412)], fill=(0,0,0,0))
    
    # Window cutout
    draw.ellipse([(140, 256), (200, 316)], fill=(0,0,0,0))
    draw.ellipse([(312, 256), (372, 316)], fill=(0,0,0,0))
    
    # Chimney
    draw.rectangle([(320, 100), (360, 200)], fill=(255,255,255,255))
    
    img.save(os.path.join(RAW_DIR, "Mini Cozy Room.png"))
    print("Drew Mini Cozy Room vector.")

def draw_hytale():
    # Crisp blocky H
    img = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Left pillar
    draw.rectangle([(120, 80), (200, 432)], fill=(255,255,255,255))
    # Right pillar
    draw.rectangle([(312, 80), (392, 432)], fill=(255,255,255,255))
    # Crossbar
    draw.rectangle([(200, 216), (312, 296)], fill=(255,255,255,255))
    
    img.save(os.path.join(RAW_DIR, "Hytale.png"))
    print("Drew Hytale vector.")

def draw_medal():
    # Silueta de cámara de grabación (identidad de Medal.tv — app de clips de gaming).
    # Diseño: cuerpo principal (rounded rect) + montura superior conectada +
    # agujero de lente (contraforma) + cristal interior (isla blanca).
    # 2 islas blancas → pasa MAX_ISLANDS=8. Cobertura ~29% → pasa 2–90%.
    img = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Cuerpo de la cámara
    draw.rounded_rectangle([(60, 175), (452, 405)], radius=52, fill=(255, 255, 255, 255))

    # Montura superior (viewfinder) — conectada al cuerpo (overlap en y=175)
    draw.rounded_rectangle([(162, 112), (288, 185)], radius=22, fill=(255, 255, 255, 255))

    # Recorte lente (contraforma circular transparente)
    draw.ellipse([(148, 222), (364, 358)], fill=(0, 0, 0, 0))

    # Cristal interior (isla blanca centrada dentro del recorte)
    draw.ellipse([(192, 252), (320, 328)], fill=(255, 255, 255, 255))

    img.save(os.path.join(RAW_DIR, "Medal.png"))
    print("Drew Medal vector.")


if __name__ == "__main__":
    draw_geek_uninstaller()
    draw_mini_cozy_room()
    draw_hytale()
    draw_medal()
