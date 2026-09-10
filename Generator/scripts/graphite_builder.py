import asyncio
import os
import requests
import re
from playwright.async_api import async_playwright

def get_simpleicons_path(icon_name):
    url = f'https://cdn.jsdelivr.net/npm/simple-icons@v11/icons/{icon_name}.svg'
    r = requests.get(url)
    if r.status_code != 200:
        raise Exception(f"Failed to fetch {icon_name}")
    # Extract the <path d="..." />
    match = re.search(r'd="([^"]+)"', r.text)
    if not match:
        raise Exception("Path not found in SVG")
    return match.group(1)

def build_graphite_svg(path_d):
    # Graphite Elegance template
    # Base: 256x256
    # Squircle: rx=60 (or rounded square), fill=#232323
    # Inner path: scale it up, center it, fill=white, drop shadow
    
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="100%" height="100%">
  <defs>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="4" stdDeviation="4" flood-color="#000000" flood-opacity="0.6"/>
    </filter>
  </defs>
  <rect x="16" y="16" width="224" height="224" rx="56" fill="#232323" />
  
  <g transform="translate(64, 64) scale(5.333)" filter="url(#shadow)">
     <!-- 24x24 simple icons viewBox, scaled by 5.333 to fit 128x128 centered in 256x256 -->
     <path d="{path_d}" fill="#FFFFFF" />
  </g>
</svg>"""

async def render_svg_to_png(svg_content, output_png_path, size=1024):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": size, "height": size})
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ margin: 0; padding: 0; overflow: hidden; background: transparent; width: {size}px; height: {size}px; }}
                svg {{ width: 100%; height: 100%; }}
            </style>
        </head>
        <body>
            {svg_content}
        </body>
        </html>
        """
        await page.set_content(html_content)
        await page.screenshot(path=output_png_path, omit_background=True, clip={"x": 0, "y": 0, "width": size, "height": size})
        await browser.close()

async def main():
    minecraft_path = get_simpleicons_path("minecraft")
    graphite_svg = build_graphite_svg(minecraft_path)
    
    _scripts   = os.path.dirname(os.path.abspath(__file__))
    _generator = os.path.dirname(_scripts)
    _root      = os.path.dirname(_generator)
    out_dir = os.path.join(_root, "Graphite_Elegance_Release", "Icons", "PNG")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "minecraft.png")
    
    print("Renderizando a", out_path)
    await render_svg_to_png(graphite_svg, out_path, size=512)
    print("Done")

if __name__ == '__main__':
    asyncio.run(main())
