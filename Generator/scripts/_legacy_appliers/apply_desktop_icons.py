import os
import glob
import sys
try:
    import win32com.client
except ImportError:
    print("Error: pypiwin32 or pywin32 is not installed.")
    print("Please run: pip install pywin32")
    exit(1)

def apply_icons_to_desktop(theme_name="Graphite_Elegance"):
    desktop_path = os.path.join(os.environ['USERPROFILE'], 'Desktop')
    icons_dir = rf"E:\Shoshin\IA_Proyect\DesktopIcons\1_Themes\{theme_name}\ICO"
    
    if not os.path.exists(icons_dir):
        print(f"Directory not found: {icons_dir}")
        print("Please check the theme name or path.")
        return

    # Load available ICO files into a dictionary for quick lookup
    # Key: normalized name (lowercase, no extension), Value: full path
    available_icons = {}
    for f in os.listdir(icons_dir):
        if f.lower().endswith('.ico'):
            name = os.path.splitext(f)[0].lower()
            available_icons[name] = os.path.join(icons_dir, f)
            
            # Add some common aliases for matching
            name_no_spaces = name.replace(" ", "")
            if name_no_spaces != name:
                available_icons[name_no_spaces] = os.path.join(icons_dir, f)

    # Scan desktop for shortcuts
    shell = win32com.client.Dispatch("WScript.Shell")
    shortcuts = glob.glob(os.path.join(desktop_path, "*.lnk"))
    
    applied_count = 0
    
    print(f"Scanning {len(shortcuts)} shortcuts on Desktop...")
    
    for lnk_path in shortcuts:
        shortcut_name = os.path.splitext(os.path.basename(lnk_path))[0].lower()
        
        # Exact match or specific mapping
        icon_to_apply = available_icons.get(shortcut_name)
        
        # Try finding a partial match if exact fails
        if not icon_to_apply:
            for icon_name, icon_path in available_icons.items():
                if icon_name in shortcut_name or shortcut_name in icon_name:
                    icon_to_apply = icon_path
                    break
        
        if icon_to_apply:
            try:
                shortcut = shell.CreateShortcut(lnk_path)
                current_icon = shortcut.IconLocation
                
                # Format: "Path, Index"
                new_icon_location = f"{icon_to_apply}, 0"
                
                if current_icon != new_icon_location:
                    shortcut.IconLocation = new_icon_location
                    shortcut.Save()
                    print(f"[OK] Applied '{os.path.basename(icon_to_apply)}' to '{os.path.basename(lnk_path)}'")
                    applied_count += 1
            except Exception as e:
                print(f"[FAIL] Could not modify '{os.path.basename(lnk_path)}': {e}")
                
    print(f"\nFinished! Successfully updated {applied_count} shortcuts.")
    print("Note: If icons don't visually update immediately, you may need to press F5 on your desktop or restart Explorer.")

if __name__ == "__main__":
    theme = "Gradiance" if len(sys.argv) > 1 and sys.argv[1] == "Gradiance" else (sys.argv[1] if len(sys.argv) > 1 else "Graphite_Elegance")
    apply_icons_to_desktop(theme)
