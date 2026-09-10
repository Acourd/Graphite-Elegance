import os

# Rutas relativas al proyecto (carpeta DesktopIcons/), a prueba de formateos/mudanzas.
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PNG_DIR = os.path.join(BASE, "Premium_PNG")
HTML_PATH = os.path.join(BASE, "Premium", "preview.html")

def main():
    if not os.path.exists(PNG_DIR):
        print(f"Directory {PNG_DIR} not found.")
        return
        
    pngs = [f for f in os.listdir(PNG_DIR) if f.endswith('.png')]
    
    html = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Icon Visualizer - Premium Squircle</title>
    <style>
        body { background-color: #121212; color: #e0e0e0; font-family: 'Segoe UI', sans-serif; padding: 2rem; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 2.5rem; margin-top: 2rem; }
        .icon-card { display: flex; flex-direction: column; align-items: center; gap: 1.2rem; transition: transform 0.2s; }
        .icon-card:hover { transform: scale(1.05); }
        .icon-preview { width: 128px; height: 128px; background-color: transparent; }
        .icon-preview img { width: 100%; height: 100%; object-fit: contain; drop-shadow: 0 10px 15px rgba(0,0,0,0.5); }
        h1 { text-align: center; font-weight: 300; letter-spacing: 1px; }
        span { font-size: 0.9rem; opacity: 0.8; text-transform: capitalize; }
    </style>
</head>
<body>
    <h1>Previsualización de Íconos Premium (Dark Monochrome Squircle)</h1>
    <div class="grid">
"""
    for png in sorted(pngs):
        name = png.replace('.png', '').replace('-', ' ')
        img_src = f"file:///{PNG_DIR.replace(chr(92), '/')}/{png}"
        html += f"""
        <div class="icon-card">
            <div class="icon-preview"><img src="{img_src}" alt="{name}"></div>
            <span>{name}</span>
        </div>
"""
    
    html += """
    </div>
</body>
</html>
"""
    os.makedirs(os.path.dirname(HTML_PATH), exist_ok=True)
    with open(HTML_PATH, "w", encoding="utf-8") as f:
        f.write(html)
        
    print(f"Generated {HTML_PATH}")

if __name__ == '__main__':
    main()
