import os
from PIL import Image, ImageDraw

RAW_DIR = r"E:\Shoshin\IA_Proyect\DesktopIcons\2_Assets\Raw_Silhouettes"
os.makedirs(RAW_DIR, exist_ok=True)

def draw_epic_games():
    img = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Draw Epic Games shield outline
    # A shield shape: flat top, curved bottom to a point
    draw.polygon([(120, 100), (392, 100), (392, 300), (256, 450), (120, 300)], fill=(0,0,0,0), outline=(255,255,255,255), width=35)
    # Inner solid block representing 'E' but abstract
    draw.rectangle([(200, 180), (312, 220)], fill=(255,255,255,255))
    draw.rectangle([(200, 240), (280, 280)], fill=(255,255,255,255))
    draw.rectangle([(200, 300), (312, 340)], fill=(255,255,255,255))
    
    img.save(os.path.join(RAW_DIR, "Epic Games.png"))
    print("Drew Epic Games.")

def draw_minecraft():
    img = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Creeper face
    draw.rectangle([(100, 100), (412, 412)], fill=(255,255,255,255))
    
    # Eyes (transparent cutouts)
    draw.rectangle([(140, 160), (220, 240)], fill=(0,0,0,0))
    draw.rectangle([(292, 160), (372, 240)], fill=(0,0,0,0))
    
    # Nose / Mouth (transparent cutouts)
    draw.rectangle([(220, 240), (292, 330)], fill=(0,0,0,0))
    draw.rectangle([(180, 280), (220, 370)], fill=(0,0,0,0))
    draw.rectangle([(292, 280), (332, 370)], fill=(0,0,0,0))
    
    img.save(os.path.join(RAW_DIR, "Minecraft.png"))
    print("Drew Minecraft.")

def draw_lossless_scaling():
    img = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Abstract pixel art Duck shape
    # We'll use a grid of blocks
    blocks = [
        (256, 100, 350, 200), # Head
        (350, 140, 420, 180), # Beak
        (150, 200, 350, 350), # Body
        (100, 250, 150, 300), # Tail
        (200, 350, 240, 400), # Leg 1
        (280, 350, 320, 400), # Leg 2
    ]
    for b in blocks:
        draw.rectangle([b[:2], b[2:]], fill=(255,255,255,255))
        
    # Eye cutout
    draw.rectangle([(300, 120), (330, 150)], fill=(0,0,0,0))
    # Wing cutout
    draw.rectangle([(220, 240), (280, 280)], fill=(0,0,0,0))

    img.save(os.path.join(RAW_DIR, "Lossless Scaling.png"))
    print("Drew Lossless Scaling.")

def draw_iso():
    img = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # A sleek cyberpunk diamond/hexagon structure
    draw.polygon([(256, 80), (420, 256), (256, 432), (92, 256)], fill=(255,255,255,255))
    # Inner cutout to make it look like a sci-fi shield/barrier
    draw.polygon([(256, 130), (370, 256), (256, 382), (142, 256)], fill=(0,0,0,0))
    # Inner solid core
    draw.polygon([(256, 180), (320, 256), (256, 332), (192, 256)], fill=(255,255,255,255))
    
    img.save(os.path.join(RAW_DIR, "Iso.png"))
    print("Drew Iso.")

def draw_images():
    img = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Photo frame
    draw.rectangle([(80, 120), (432, 392)], outline=(255,255,255,255), width=25)
    # Mountains (solid)
    draw.polygon([(80, 392), (200, 250), (300, 392)], fill=(255,255,255,255))
    draw.polygon([(200, 392), (320, 200), (432, 392)], fill=(255,255,255,255))
    # Sun
    draw.ellipse([(120, 160), (180, 220)], fill=(255,255,255,255))
    
    img.save(os.path.join(RAW_DIR, "Images.png"))
    print("Drew Images.")

if __name__ == "__main__":
    draw_epic_games()
    draw_minecraft()
    draw_lossless_scaling()
    draw_iso()
    draw_images()
