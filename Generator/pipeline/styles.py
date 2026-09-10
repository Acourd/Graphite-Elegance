"""
Style definitions for the Isoform icon factory.

Pure data (no heavy imports) so ``build.py --check`` can validate style names
without OpenCV. Palette values are sampled from the released 256px frames:

    graphite  : (45,45,45) -> (10,10,10)          white logo, border + shadow
    lumina    : (211,211,211) -> (245,245,245)    black logo
    kiraldark : (62,58,54) -> (34,31,28)          warm off-white logo
    kiralight : (198,190,176) -> (226,217,201)    near-black logo
    horizon   : (254,247,235) -> (252,243,226)    deep indigo logo
    midnight  : (27,18,58) -> (12,8,30)           amber logo
    pixel     : opaque transparent-corner white square, black border, black
                pixel-art logo. Sources are derived from the released icons;
                parity ~17/255 (reference kept until final tuning).
"""

STYLES = {
    "graphite": {
        "grad_top": (45, 45, 45), "grad_bottom": (10, 10, 10),
        "logo": (255, 255, 255), "border": True, "shadow": True,
    },
    "lumina": {
        "grad_top": (211, 211, 211), "grad_bottom": (245, 245, 245),
        "logo": (0, 0, 0), "border": False, "shadow": False,
    },
    "kiraldark": {
        "grad_top": (62, 58, 54), "grad_bottom": (34, 31, 28),
        "logo": (235, 225, 208), "border": False, "shadow": False,
    },
    "kiralight": {
        "grad_top": (198, 190, 176), "grad_bottom": (226, 217, 201),
        "logo": (26, 26, 26), "border": False, "shadow": False,
    },
    "horizon": {
        "grad_top": (254, 247, 235), "grad_bottom": (252, 243, 226),
        "logo": (27, 17, 58), "border": False, "shadow": False,
    },
    "midnight": {
        "grad_top": (27, 18, 58), "grad_bottom": (12, 8, 30),
        "logo": (255, 174, 66), "border": False, "shadow": False,
    },
    "pixel": {
        "grad_top": (255, 255, 255), "grad_bottom": (255, 255, 255),
        "logo": (0, 0, 0), "border": True, "border_color": (0, 0, 0, 255),
        "border_width": 4, "radius": 40, "logo_frac": 0.53,
        "pixelated": True, "pixel_grid": 32,
    },
}
