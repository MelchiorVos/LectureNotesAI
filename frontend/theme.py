"""
Shared UI theme constants and helpers used by all frontend windows.
"""

import ctypes

# ---------------------------------------------------------------------------
# Color palette
# ---------------------------------------------------------------------------

ACCENT = "#2563EB"
ACCENT_HOVER = "#1D4ED8"
BG = "#FFFFFF"
FG = "#1E293B"
MUTED = "#94A3B8"
BORDER = "#CBD5E1"
RED = "#EF4444"
RED_BG = "#FEF2F2"
GREEN_BG = "#F0FDF4"


# ---------------------------------------------------------------------------
# Window helpers
# ---------------------------------------------------------------------------


def force_focus(window) -> None:
    """Force a tkinter/CTk window to the foreground on Windows."""
    try:
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        ctypes.windll.user32.keybd_event(0x12, 0, 0, 0)
        ctypes.windll.user32.keybd_event(0x12, 0, 2, 0)
        ctypes.windll.user32.SetForegroundWindow(hwnd)
    except Exception:
        pass
