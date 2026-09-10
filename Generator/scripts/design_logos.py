import os
from PIL import Image, ImageDraw
import math

BASE_DIR = r"E:\Shoshin\IA_Proyect\DesktopIcons\2_Assets\Raw_Silhouettes"
os.makedirs(BASE_DIR, exist_ok=True)

def make_transparent(img, func):
    pixels = img.load()
    size = img.width
    func(pixels, size)

def draw_msi_afterburner():
    size = 512
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    center = (size // 2, size // 2)
    # GPU Fan Ring
    draw.arc([center[0]-220, center[1]-220, center[0]+220, center[1]+220], start=0, end=360, fill=(255, 255, 255, 255), width=24)
    draw.arc([center[0]-160, center[1]-160, center[0]+160, center[1]+160], start=0, end=360, fill=(255, 255, 255, 255), width=8)
    
    # Fan blades
    for i in range(7):
        angle = math.radians(i * 360/7)
        outer_x = center[0] + 200 * math.cos(angle)
        outer_y = center[1] + 200 * math.sin(angle)
        draw.line([center, (outer_x, outer_y)], fill=(255, 255, 255, 255), width=16)
        
    # Center Fire / Jet Engine
    draw.ellipse([center[0]-80, center[1]-80, center[0]+80, center[1]+80], fill=(255, 255, 255, 255))
    # Draw fire triangle
    draw.polygon([(center[0], center[1]-140), (center[0]-40, center[1]), (center[0]+40, center[1])], fill=(255, 255, 255, 255))
    
    # Cutout
    def eraser(pixels, size):
        # Center hole
        for a in range(360):
            r = 30
            x = int(center[0] + r * math.cos(math.radians(a)))
            y = int(center[1] + r * math.sin(math.radians(a)))
            for dx in range(-r, r):
                for dy in range(-r, r):
                    if dx*dx + dy*dy <= r*r and 0 <= x+dx < size and 0 <= y+dy < size:
                        pixels[x+dx, y+dy] = (0,0,0,0)
    make_transparent(img, eraser)
    img.save(os.path.join(BASE_DIR, "MSI Afterburner.png"))

def draw_driver_booster():
    size = 512
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    center = (size // 2, size // 2)
    # Update Radar Ring
    draw.arc([100, 100, 412, 412], start=45, end=315, fill=(255, 255, 255, 255), width=24)
    # Arrow head
    draw.polygon([(412, 256), (370, 210), (370, 300)], fill=(255, 255, 255, 255))
    # Inner tech nodes
    draw.ellipse([210, 210, 302, 302], outline=(255, 255, 255, 255), width=20)
    draw.ellipse([240, 240, 272, 272], fill=(255, 255, 255, 255))
    draw.line([(256, 150), (256, 210)], fill=(255, 255, 255, 255), width=16)
    draw.line([(256, 302), (256, 362)], fill=(255, 255, 255, 255), width=16)
    draw.line([(150, 256), (210, 256)], fill=(255, 255, 255, 255), width=16)
    img.save(os.path.join(BASE_DIR, "Driver Booster.png"))

def draw_excel():
    size = 512
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Spreadsheet background
    draw.rounded_rectangle([200, 100, 460, 412], radius=20, outline=(255, 255, 255, 255), width=24)
    # Grid lines
    draw.line([(200, 204), (460, 204)], fill=(255, 255, 255, 255), width=16)
    draw.line([(200, 308), (460, 308)], fill=(255, 255, 255, 255), width=16)
    draw.line([(330, 100), (330, 412)], fill=(255, 255, 255, 255), width=16)
    
    # Front square with X
    draw.rounded_rectangle([52, 160, 276, 352], radius=16, fill=(255, 255, 255, 255))
    
    def eraser(pixels, size):
        def line(p1, p2, w):
            x1, y1 = p1; x2, y2 = p2
            length = math.hypot(x2 - x1, y2 - y1)
            for i in range(int(length)):
                x = int(x1 + (x2 - x1) * i / length); y = int(y1 + (y2 - y1) * i / length)
                for dx in range(-w, w):
                    for dy in range(-w, w):
                        if dx*dx + dy*dy <= w*w and 0 <= x+dx < size and 0 <= y+dy < size:
                            pixels[x+dx, y+dy] = (0,0,0,0)
        # Draw X
        line((110, 200), (210, 312), 16)
        line((210, 200), (110, 312), 16)
    make_transparent(img, eraser)
    img.save(os.path.join(BASE_DIR, "Excel.png"))

def draw_outlook():
    size = 512
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Envelope Background
    draw.rounded_rectangle([150, 120, 480, 400], radius=16, outline=(255, 255, 255, 255), width=24)
    draw.line([(150, 120), (315, 250)], fill=(255, 255, 255, 255), width=16)
    draw.line([(480, 120), (315, 250)], fill=(255, 255, 255, 255), width=16)
    
    # Front square with O
    draw.rounded_rectangle([32, 160, 236, 352], radius=16, fill=(255, 255, 255, 255))
    
    def eraser(pixels, size):
        def circle(cx, cy, r, w):
            for a in range(360):
                x = int(cx + r * math.cos(math.radians(a))); y = int(cy + r * math.sin(math.radians(a)))
                for dx in range(-w, w):
                    for dy in range(-w, w):
                        if dx*dx + dy*dy <= w*w and 0 <= x+dx < size and 0 <= y+dy < size:
                            pixels[x+dx, y+dy] = (0,0,0,0)
        circle(134, 256, 45, 16)
    make_transparent(img, eraser)
    img.save(os.path.join(BASE_DIR, "Outlook.png"))

def draw_overwatch():
    size = 512
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    center = (size // 2, size // 2)
    # Overwatch Logo
    draw.arc([80, 80, 432, 432], start=145, end=35, fill=(255, 255, 255, 255), width=48)
    # Inner W shapes
    draw.polygon([(256, 140), (160, 360), (220, 360), (256, 260)], fill=(255, 255, 255, 255))
    draw.polygon([(256, 140), (352, 360), (292, 360), (256, 260)], fill=(255, 255, 255, 255))
    img.save(os.path.join(BASE_DIR, "Overwatch.png"))

if __name__ == "__main__":
    draw_msi_afterburner()
    draw_driver_booster()
    draw_excel()
    draw_outlook()
    draw_overwatch()
    print("New vector logos designed.")
