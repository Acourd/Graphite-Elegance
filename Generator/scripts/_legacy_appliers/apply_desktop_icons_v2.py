import os
import glob
import configparser
try:
    import win32com.client
except ImportError:
    print("Error: pypiwin32 is not installed.")
    exit(1)

def apply_icons_to_desktop(theme_name="Graphite_Elegance"):
    # Both User and Public Desktops
    desktops = [
        os.path.join(os.environ['USERPROFILE'], 'Desktop'),
        os.path.join(os.environ['PUBLIC'], 'Desktop')
    ]
    
    icons_dir = rf"E:\Shoshin\IA_Proyect\DesktopIcons\1_Themes\{theme_name}\ICO"
    
    if not os.path.exists(icons_dir):
        print(f"Directory not found: {icons_dir}")
        return

    # Load available ICO files
    available_icons = {}
    for f in os.listdir(icons_dir):
        if f.lower().endswith('.ico'):
            name = os.path.splitext(f)[0].lower()
            available_icons[name] = os.path.join(icons_dir, f)
            available_icons[name.replace(" ", "")] = os.path.join(icons_dir, f)

    shell = win32com.client.Dispatch("WScript.Shell")
    applied_count = 0
    
    for desktop_path in desktops:
        if not os.path.exists(desktop_path): continue
            
        # Get both .lnk and .url
        shortcuts = glob.glob(os.path.join(desktop_path, "*.lnk")) + glob.glob(os.path.join(desktop_path, "*.url"))
        
        for file_path in shortcuts:
            shortcut_name = os.path.splitext(os.path.basename(file_path))[0].lower()
            
            # Find matching icon
            icon_to_apply = available_icons.get(shortcut_name)
            if not icon_to_apply:
                for icon_name, icon_path in available_icons.items():
                    if icon_name in shortcut_name or shortcut_name in icon_name:
                        icon_to_apply = icon_path
                        break
            
            if icon_to_apply:
                ext = os.path.splitext(file_path)[1].lower()
                try:
                    if ext == '.lnk':
                        shortcut = shell.CreateShortcut(file_path)
                        new_icon_location = f"{icon_to_apply}, 0"
                        if shortcut.IconLocation != new_icon_location:
                            shortcut.IconLocation = new_icon_location
                            shortcut.Save()
                            print(f"[OK] LNK: Applied '{os.path.basename(icon_to_apply)}' to '{os.path.basename(file_path)}'")
                            applied_count += 1
                            
                    elif ext == '.url':
                        # .url files are INI format
                        config = configparser.ConfigParser()
                        # Steam .url files often don't have a strict INI structure at the start, but configparser can read them if formatted right.
                        # Actually, writing directly is safer
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            lines = f.readlines()
                        
                        has_icon = False
                        for i, line in enumerate(lines):
                            if line.lower().startswith('iconfile='):
                                lines[i] = f"IconFile={icon_to_apply}\n"
                                has_icon = True
                            elif line.lower().startswith('iconindex='):
                                lines[i] = "IconIndex=0\n"
                                
                        if not has_icon:
                            # Add to the end of [InternetShortcut] section
                            for i, line in enumerate(lines):
                                if line.strip().lower() == '[internetshortcut]':
                                    lines.insert(i+1, f"IconFile={icon_to_apply}\n")
                                    lines.insert(i+2, "IconIndex=0\n")
                                    break
                                    
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.writelines(lines)
                        print(f"[OK] URL: Applied '{os.path.basename(icon_to_apply)}' to '{os.path.basename(file_path)}'")
                        applied_count += 1

                except Exception as e:
                    print(f"[FAIL] Could not modify '{os.path.basename(file_path)}': {e}")
                
    print(f"\nFinished! Successfully updated {applied_count} shortcuts.")
    print("Note: If icons don't visually update immediately, you may need to press F5 on your desktop or restart Explorer.")

if __name__ == "__main__":
    import sys
    theme = "Gradiance" if len(sys.argv) > 1 and sys.argv[1] == "Gradiance" else (sys.argv[1] if len(sys.argv) > 1 else "Graphite_Elegance")
    apply_icons_to_desktop(theme)
