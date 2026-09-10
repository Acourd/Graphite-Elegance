import cv2
import numpy as np
import os
from PIL import Image

RAW_DIR = r"E:\Shoshin\IA_Proyect\DesktopIcons\2_Assets\Raw_Silhouettes"

def process_word():
    path = os.path.join(RAW_DIR, "Word.jpg")
    if not os.path.exists(path): return
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    # Threshold to binary
    _, thresh = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    
    # User wants Word to be a completely solid silhouette.
    # We will use morphological closing (dilation then erosion) with a large kernel
    # to fill any internal holes (like the lines in the Word icon).
    kernel = np.ones((25, 25), np.uint8)
    solid = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    # Also dilate a bit to merge the 'W' block and the document block if they are disconnected
    solid = cv2.dilate(solid, np.ones((10, 10), np.uint8), iterations=1)
    
    # Save as PNG with alpha
    out = np.zeros((solid.shape[0], solid.shape[1], 4), dtype=np.uint8)
    out[solid > 0] = [255, 255, 255, 255]
    Image.fromarray(out).save(os.path.join(RAW_DIR, "Word.png"))
    os.remove(path)
    print("Word refined into solid silhouette.")

def process_hytale():
    path = os.path.join(RAW_DIR, "Hytale.jpg")
    if not os.path.exists(path): return
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    _, thresh = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    
    # User wants Hytale cleaned up (remove noise, keep the H)
    # Morphological opening (erosion then dilation) removes small noise specs
    kernel = np.ones((5, 5), np.uint8)
    clean = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
    
    # Save as PNG with alpha
    out = np.zeros((clean.shape[0], clean.shape[1], 4), dtype=np.uint8)
    out[clean > 0] = [255, 255, 255, 255]
    Image.fromarray(out).save(os.path.join(RAW_DIR, "Hytale.png"))
    os.remove(path)
    print("Hytale cleaned of noise.")

def process_blasphemous():
    path = os.path.join(RAW_DIR, "Blasphemous.jpg")
    if not os.path.exists(path): return
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    _, thresh = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    
    kernel = np.ones((3, 3), np.uint8)
    clean = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
    
    out = np.zeros((clean.shape[0], clean.shape[1], 4), dtype=np.uint8)
    out[clean > 0] = [255, 255, 255, 255]
    Image.fromarray(out).save(os.path.join(RAW_DIR, "Blasphemous.png"))
    os.remove(path)
    print("Blasphemous cleaned.")

if __name__ == "__main__":
    process_word()
    process_hytale()
    process_blasphemous()
