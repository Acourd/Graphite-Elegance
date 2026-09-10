import os
import re

raw_dir = r"E:\Shoshin\IA_Proyect\DesktopIcons\2_Assets\Raw_Silhouettes"
for f in os.listdir(raw_dir):
    name, ext = os.path.splitext(f)
    # Exceptions or special cases
    if name.lower() == 'msiafterburner': name = 'MSI Afterburner'
    elif name.lower() == 'opendesing': name = 'OpenDesign'
    elif name.lower() == 'processlasso': name = 'Process Lasso'
    elif name.lower() == 'wallpapaerengine': name = 'Wallpaper Engine'
    elif name.lower() == 'valotracker': name = 'Valorant Tracker'
    elif name.lower() == 'minicozyroom': name = 'Mini Cozy Room'
    elif name.lower() == 'atlauncher': name = 'ATLauncher'
    elif name.lower() == 'losslessscaling': name = 'Lossless Scaling'
    elif name.lower() == 'blasmepheus': name = 'Blasphemous'
    elif name.lower() == 'aistudio': name = 'AI Studio'
    elif name.lower() == 'antigravity': name = 'Antigravity'
    elif name.lower() == 'epicgames': name = 'Epic Games'
    elif name.lower() == 'notebooklm': name = 'NotebookLM'
    elif name.lower() == 'tmodloader': name = 'tModLoader'
    elif name.lower() == 'claude-ai-icon.svg': name = 'Claude AI'
    elif name.lower() == 'geek-uninstaller': name = 'Geek Uninstaller'
    else:
        name = name.replace('-', ' ').replace('_', ' ').title()
    
    new_f = f"{name}{ext}"
    if f != new_f:
        try:
            os.rename(os.path.join(raw_dir, f), os.path.join(raw_dir, new_f))
            print(f"Renamed {f} -> {new_f}")
        except Exception as e:
            print(f"Failed to rename {f}: {e}")
