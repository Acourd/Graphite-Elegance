import os
import shutil
import numpy as np
from PIL import Image

RESPALDO_DIR = r"E:\Shoshin\IA_Proyect\DesktopIcons\1_Themes\Graphite_Elegance\REspaldo"
ICO_DIR = r"E:\Shoshin\IA_Proyect\DesktopIcons\1_Themes\Graphite_Elegance\ICO"
SELECTION_DIR = r"E:\Shoshin\IA_Proyect\DesktopIcons\1_Themes\Graphite_Elegance\Premium_Selection"

os.makedirs(SELECTION_DIR, exist_ok=True)

def evaluate_quality(img_path):
    try:
        img = Image.open(img_path).convert("RGBA")
        img = img.resize((256, 256))
        arr = np.array(img)
        
        # Calculate Logo Area (Non-black, non-transparent pixels)
        # Assuming background is black (R < 50, G < 50, B < 50) or Transparent
        alpha = arr[:,:,3]
        r, g, b = arr[:,:,0], arr[:,:,1], arr[:,:,2]
        
        # Mask for logo (pixels that are bright whiteish and opaque)
        logo_mask = (alpha > 128) & ((r > 150) | (g > 150) | (b > 150))
        
        coords = np.argwhere(logo_mask)
        if len(coords) == 0:
            return 0, 0, 0 # Empty logo
            
        y_min, x_min = coords.min(axis=0)
        y_max, x_max = coords.max(axis=0)
        
        # Bounding box area percentage relative to the 256x256 image
        bbox_area = (y_max - y_min) * (x_max - x_min)
        bbox_percent = (bbox_area / (256 * 256)) * 100
        
        # Integrity check: how much of the bounding box is actually filled with the logo?
        # A perfectly solid logo has high integrity. Holes reduce integrity.
        pixels_in_bbox = len(coords)
        integrity = (pixels_in_bbox / bbox_area) * 100 if bbox_area > 0 else 0
        
        # Perfect scale is around 25-45% of the total squircle area
        scale_score = 100 - abs(35 - bbox_percent)
        
        return scale_score, integrity, bbox_percent
    except Exception as e:
        print(f"Error evaluating {img_path}: {e}")
        return 0, 0, 0

def run_evaluation():
    respaldo_files = {f.lower().replace('.ico',''): f for f in os.listdir(RESPALDO_DIR) if f.endswith('.ico')}
    ico_files = {f.lower().replace('.ico',''): f for f in os.listdir(ICO_DIR) if f.endswith('.ico')}
    
    all_apps = set(respaldo_files.keys()).union(set(ico_files.keys()))
    
    winners = []
    
    for app in all_apps:
        resp_file = respaldo_files.get(app)
        ico_file = ico_files.get(app)
        
        if resp_file and ico_file:
            resp_path = os.path.join(RESPALDO_DIR, resp_file)
            ico_path = os.path.join(ICO_DIR, ico_file)
            
            resp_scale, resp_integ, resp_bbox = evaluate_quality(resp_path)
            ico_scale, ico_integ, ico_bbox = evaluate_quality(ico_path)
            
            # Decision Logic
            resp_score = (resp_scale * 0.7) + (resp_integ * 0.3)
            ico_score = (ico_scale * 0.7) + (ico_integ * 0.3)
            
            # Heavily penalize tiny dots
            if ico_bbox < 5: ico_score -= 50
            if resp_bbox < 5: resp_score -= 50
            
            if resp_score >= ico_score:
                shutil.copy2(resp_path, os.path.join(SELECTION_DIR, resp_file))
                winners.append((app, "REspaldo", resp_bbox, ico_bbox))
            else:
                shutil.copy2(ico_path, os.path.join(SELECTION_DIR, ico_file))
                winners.append((app, "Generado", ico_bbox, resp_bbox))
                
        elif resp_file:
            shutil.copy2(os.path.join(RESPALDO_DIR, resp_file), os.path.join(SELECTION_DIR, resp_file))
            winners.append((app, "REspaldo (Único)", 0, 0))
        elif ico_file:
            shutil.copy2(os.path.join(ICO_DIR, ico_file), os.path.join(SELECTION_DIR, ico_file))
            winners.append((app, "Generado (Único)", 0, 0))
            
    # Print results summary
    print("\n=== QA EVALUATION RESULTS ===")
    resp_wins = sum(1 for w in winners if "REspaldo" in w[1])
    gen_wins = sum(1 for w in winners if "Generado" in w[1])
    print(f"Total Apps Evaluated: {len(winners)}")
    print(f"REspaldo Wins: {resp_wins}")
    print(f"Generado Wins: {gen_wins}\n")
    
    print(f"{'App Name':<25} | {'Winner':<18} | {'Win Area %':<10} | {'Lose Area %'}")
    print("-" * 75)
    for w in sorted(winners, key=lambda x: x[0]):
        print(f"{w[0]:<25} | {w[1]:<18} | {w[2]:.1f}%{'':<9} | {w[3]:.1f}%")

if __name__ == "__main__":
    run_evaluation()
