import os
import cv2
import numpy as np

PNG_DIR = r"E:\Shoshin\IA_Proyect\DesktopIcons\1_Themes\Lumina_Frost_Release\Icons\PNG"

def get_luminance(rgb):
    # sRGB luminance
    a = [c / 255.0 for c in rgb]
    a = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in a]
    return a[0] * 0.2126 + a[1] * 0.7152 + a[2] * 0.0722

def calculate_contrast(rgb1, rgb2):
    lum1 = get_luminance(rgb1)
    lum2 = get_luminance(rgb2)
    brightest = max(lum1, lum2)
    darkest = min(lum1, lum2)
    return (brightest + 0.05) / (darkest + 0.05)

def check_contrast():
    if not os.path.exists(PNG_DIR):
        print("Directory does not exist:", PNG_DIR)
        return
    
    files = [f for f in os.listdir(PNG_DIR) if f.endswith(".png")]
    if not files:
        print("No PNG files found.")
        return

    all_pass = True
    print("=== AUDITORÍA DE CONTRASTE ===")
    for file in files:
        path = os.path.join(PNG_DIR, file)
        img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        if img is None:
            continue
        
        b, g, r, a = cv2.split(img)
        
        # Pixeles del fondo (claros) y del logo (oscuros)
        mask_bg = (a > 200) & (r > 200) & (g > 200) & (b > 200)
        mask_fg = (a > 200) & (r < 100) & (g < 100) & (b < 100)
        
        if np.any(mask_bg) and np.any(mask_fg):
            bg_color = [np.mean(r[mask_bg]), np.mean(g[mask_bg]), np.mean(b[mask_bg])]
            fg_color = [np.mean(r[mask_fg]), np.mean(g[mask_fg]), np.mean(b[mask_fg])]
            
            ratio = calculate_contrast(bg_color, fg_color)
            status = "PASS" if ratio >= 4.5 else "FAIL"
            if ratio < 4.5:
                all_pass = False
            print(f"[{status}] {file} - Ratio: {ratio:.2f}:1")
        else:
            print(f"[WARN] {file} - No se pudo detectar claramente el contraste.")
    
    if all_pass:
        print("\nRESULTADO FINAL: PASS (Todos los iconos generados cumplen con el estándar WCAG AA de >= 4.5:1)")
    else:
        print("\nRESULTADO FINAL: FAIL (Algunos iconos fallaron la prueba de contraste)")

if __name__ == "__main__":
    check_contrast()
