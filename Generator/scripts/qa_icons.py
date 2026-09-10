import os
from PIL import Image
import numpy as np

ICO_DIR = r"E:\Shoshin\IA_Proyect\DesktopIcons\1_Themes\Graphite_Elegance\ICO"
PNG_DIR = r"E:\Shoshin\IA_Proyect\DesktopIcons\1_Themes\Graphite_Elegance\PNG"

def qa_image(path):
    try:
        img = Image.open(path).convert("RGBA")
        arr = np.array(img)
        # Check corners for transparency (Alpha = 0)
        # Squircles should have 0 alpha at (0,0), (size-1, 0), etc.
        h, w = arr.shape[:2]
        corners = [
            arr[0, 0, 3],
            arr[0, w-1, 3],
            arr[h-1, 0, 3],
            arr[h-1, w-1, 3]
        ]
        if any(a > 0 for a in corners):
            return False, "Failed Corner Transparency (Solid Background detected)"
        
        # Check if the entire image is pure white or black
        rgb = arr[:,:,:3]
        alpha = arr[:,:,3]
        mask = alpha > 128
        if np.sum(mask) == 0:
            return False, "Failed: Completely transparent"
            
        return True, "Passed"
    except Exception as e:
        return False, f"Failed Error: {e}"

def run_qa():
    failed = []
    print("Running QA on PNGs...")
    for f in os.listdir(PNG_DIR):
        p = os.path.join(PNG_DIR, f)
        ok, msg = qa_image(p)
        if not ok:
            print(f"[{f}] {msg}")
            failed.append(p)
            
    print("Running QA on ICOs...")
    for f in os.listdir(ICO_DIR):
        p = os.path.join(ICO_DIR, f)
        ok, msg = qa_image(p)
        if not ok:
            print(f"[{f}] {msg}")
            failed.append(p)
            
    if len(failed) > 0:
        print(f"\nQA Failed for {len(failed)} files. Cleaning up...")
        for p in failed:
            try:
                os.remove(p)
            except:
                pass
    else:
        print("\nAll icons passed QA!")

if __name__ == "__main__":
    run_qa()
