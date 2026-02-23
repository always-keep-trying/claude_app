"""
theme.py — Colour constants and global appearance configuration.
Import from here in every module that needs colours so there is
one source of truth and no circular imports.
"""

import customtkinter as ctk

# ── Global appearance ─────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ── Chat colours ──────────────────────────────────────────────────────────────
CLR_BG_DARK   = "#141414"
CLR_BG_MID    = "#1e1e1e"
CLR_BG_LIGHT  = "#2a2a2a"
CLR_SIDEBAR   = "#181818"
CLR_USER_BG   = "#1a3a5c"
CLR_ASST_BG   = "#242424"
CLR_ACCENT    = "#3b82f6"
CLR_ACCENT_HV = "#2563eb"
CLR_TEXT      = "#e2e8f0"
CLR_SUBTEXT   = "#94a3b8"
CLR_GREEN     = "#22c55e"
CLR_AMBER     = "#f59e0b"
CLR_RED       = "#ef4444"

# ── Message Log tab colours ───────────────────────────────────────────────────
CLR_LOG_USER_BG   = "#0f2a45"
CLR_LOG_USER_HDR  = "#1a3f63"
CLR_LOG_USER_ROLE = "#60a5fa"
CLR_LOG_ASST_BG   = "#1e1030"
CLR_LOG_ASST_HDR  = "#2d1a4a"
CLR_LOG_ASST_ROLE = "#a78bfa"

# ── Tab accent colours ────────────────────────────────────────────────────────
TAB_COLORS = {
    "💬  Chat": {
        "active_bg":   "#166534",
        "active_fg":   "#bbf7d0",
        "inactive_fg": "#4ade80",
    },
    "📋  Message Log": {
        "active_bg":   "#78350f",
        "active_fg":   "#fef3c7",
        "inactive_fg": "#fbbf24",
    },
}
