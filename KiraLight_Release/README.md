# KiraLight — Dark & Light

Two companion icon variants sharing the same silhouettes with inverted palettes:
**DarkVersion** and **LightVersion**.

**138 icons total** (2 × 69) — apps, games, tools, and AI.

All icons ship the full 16/32/48/64/128/256 frame set
(`python ..\Tools\icon_validate.py --all`).

---

## How to Use — Auto (shared engine)

> **Windows only.** Requires Python 3. Install once: `pip install -r ..\..\requirements.txt`.

```cmd
:: run from DarkVersion\ or LightVersion\
python ..\..\Tools\icon_engine.py --config theme.json
python ..\..\Tools\icon_engine.py --config theme.json --rename --cleanup
```

Each variant has its own `theme.json` (`persist_key` `KiraLight_Dark` /
`KiraLight_Light`), so you can switch between them. By default the engine only
applies icons; `--rename`/`--cleanup` are opt-in. See `../Tools/README.md`.

---

## How to Use — Manual

1. Right-click any shortcut → **Properties**.
2. Go to the **Shortcut** tab → **Change Icon...**.
3. Browse to the variant's `Icons\ICO\` folder and select the file.
4. Click **Apply** → **OK**.

---
*Created by Ayco.*
