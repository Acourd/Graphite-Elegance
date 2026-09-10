import io
import os
import cv2
import numpy as np
from PIL import Image
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM
import urllib.request

def debug_svg(url, name):
    print(f"Testing {name}...")
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    svg_bytes = urllib.request.urlopen(req).read()
    
    drawing = svg2rlg(io.BytesIO(svg_bytes))
    png_data = renderPM.drawToString(drawing, fmt="PNG", dpi=192)
    
    img = Image.open(io.BytesIO(png_data)).convert("RGBA")
    img_np = np.array(img)
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGBA2GRAY)
    
    # White background = 255, Black logo = 0
    # Map to Alpha: White -> 0 (transparent), Black -> 255 (opaque)
    alpha = 255 - gray
    img_np[:,:,3] = alpha
    
    white_logo = Image.fromarray(img_np)
    
    white_layer = Image.new("RGBA", white_logo.size, (255, 255, 255, 255))
    final_logo = Image.new("RGBA", white_logo.size, (0, 0, 0, 0))
    final_logo.paste(white_layer, (0, 0), white_logo.split()[3])

    bbox = final_logo.getbbox()
    print(f"BBox: {bbox}")
    if bbox:
        final_logo = final_logo.crop(bbox)
        print(f"Cropped size: {final_logo.size}")
        final_logo.save(f"debug_{name}.png")

if __name__ == "__main__":
    debug_svg("https://cdn.jsdelivr.net/npm/simple-icons@v11/icons/discord.svg", "discord")
    debug_svg("https://cdn.jsdelivr.net/npm/simple-icons@v11/icons/steam.svg", "steam")
