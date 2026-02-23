"""
scroll.py — Mouse-wheel scroll utilities.

Applies the customtkinter/tkinterweb compatibility patch at import time,
then provides enable_scroll() and _setup_global_scroll() for the app to use.
"""

import tkinter as tk
import customtkinter as ctk

# ── Patch customtkinter's scroll handler to tolerate tkinterweb string widgets ─
# tkinterweb fires scroll events where event.widget is a path string, not a
# widget object. customtkinter's check_if_master_is_canvas calls .master on it
# and crashes. We replace it with an identical but string-safe version.
try:
    from customtkinter.windows.widgets.ctk_scrollable_frame import CTkScrollableFrame as _CTkSF

    def _safe_check_if_master_is_canvas(self, widget):
        try:
            while widget is not None:
                if isinstance(widget, str) or not hasattr(widget, "master"):
                    return False
                if widget is self._parent_canvas:
                    return True
                widget = widget.master
        except Exception:
            pass
        return False

    _CTkSF.check_if_master_is_canvas = _safe_check_if_master_is_canvas
except Exception:
    pass

# ── Scroll target registry ────────────────────────────────────────────────────
_SCROLL_TARGETS: list = []

# Fraction of viewport height to scroll per tick (8% = consistent feel)
SCROLL_SPEED = 0.08


def enable_scroll(scrollable_frame: ctk.CTkScrollableFrame):
    """Register a CTkScrollableFrame as a mouse-wheel scroll target."""
    if scrollable_frame not in _SCROLL_TARGETS:
        _SCROLL_TARGETS.append(scrollable_frame)


def _scroll_canvas_by_fraction(canvas: tk.Canvas, direction: int):
    """
    Scroll *canvas* by SCROLL_SPEED × viewport height regardless of total
    content height, keeping speed consistent across short and long chats.

    Guards:
      - winfo_height < 10  → widget not yet laid out, skip
      - bbox("all") is None → canvas empty, skip
    """
    try:
        viewport_h = canvas.winfo_height()
        if viewport_h < 10:
            return

        bbox = canvas.bbox("all")
        if bbox is None:
            return

        total_h = bbox[3] - bbox[1]
        if total_h <= 0:
            return

        fraction = (viewport_h * SCROLL_SPEED) / total_h
        current  = canvas.yview()[0]
        canvas.yview_moveto(current + direction * fraction)
    except Exception:
        pass


def setup_global_scroll(root: tk.Tk):
    """
    Bind a single mouse-wheel handler on the root window.

    On each event, finds the first registered AND visible scrollable frame
    under the cursor and scrolls it by a fixed viewport fraction.
    winfo_viewable() ensures the hidden tab's frame is never scrolled
    instead of the visible one.
    """
    def _scroll(event):
        if event.num == 4:
            direction = -1
        elif event.num == 5:
            direction = 1
        elif event.delta:
            direction = -1 if event.delta > 0 else 1
        else:
            return

        try:
            x, y = root.winfo_pointerx(), root.winfo_pointery()
        except Exception:
            return

        for sf in _SCROLL_TARGETS:
            try:
                if not sf.winfo_viewable():
                    continue
                wx = sf.winfo_rootx()
                wy = sf.winfo_rooty()
                ww = sf.winfo_width()
                wh = sf.winfo_height()
                if wx <= x <= wx + ww and wy <= y <= wy + wh:
                    _scroll_canvas_by_fraction(sf._parent_canvas, direction)
                    return
            except Exception:
                continue

    root.bind_all("<MouseWheel>", _scroll, add="+")
    root.bind_all("<Button-4>",   _scroll, add="+")
    root.bind_all("<Button-5>",   _scroll, add="+")
