"""
widgets/bubbles.py — Chat and log bubble widgets.

UserBubble       — right-aligned user message
AssistantBubble  — left-aligned static assistant message
StreamingBubble  — live assistant message during streaming (debounced)
LogBubble        — full-width diagnostic card for the Message Log tab
add_stop_indicator — shared stop-reason badge helper
"""

import tkinter as tk
from datetime import datetime

import customtkinter as ctk

from theme import (
    CLR_ACCENT, CLR_AMBER, CLR_ASST_BG, CLR_GREEN, CLR_SUBTEXT, CLR_TEXT,
    CLR_USER_BG,
    CLR_LOG_ASST_BG, CLR_LOG_ASST_HDR, CLR_LOG_ASST_ROLE,
    CLR_LOG_USER_BG, CLR_LOG_USER_HDR, CLR_LOG_USER_ROLE,
)

# Error role colours for LogBubble
CLR_LOG_ERR_BG   = "#3b0f0f"
CLR_LOG_ERR_HDR  = "#5c1a1a"
CLR_LOG_ERR_ROLE = "#f87171"
from widgets.markdown_frame import MarkdownFrame
from widgets.dialogs import Tooltip


# ── Shared stop-reason indicator ──────────────────────────────────────────────
def add_stop_indicator(parent: tk.Widget, stop_reason: str, anchor: str = "w"):
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(anchor=anchor, padx=14, pady=(0, 6))
    ok  = stop_reason == "end_turn"
    lbl = ctk.CTkLabel(
        row,
        text="✓" if ok else "⚠",
        text_color=CLR_GREEN if ok else CLR_AMBER,
        font=ctk.CTkFont(size=13),
        cursor="hand2",
    )
    lbl.pack(side="left")
    Tooltip(lbl, f"Stop reason: {stop_reason}")


# ── User bubble ───────────────────────────────────────────────────────────────
class UserBubble(ctk.CTkFrame):
    """
    Right-aligned user message.
    Uses a two-column grid: col 0 is a weighted spacer that pushes
    the bubble right; col 1 holds the bubble itself.
    """

    def __init__(self, parent, content: str, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)

        ctk.CTkLabel(
            self, text="You",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=CLR_SUBTEXT,
        ).grid(row=0, column=0, columnspan=2, sticky="e", padx=14, pady=(4, 2))

        bubble = tk.Frame(self, bg=CLR_USER_BG, bd=0, highlightthickness=0)
        bubble.grid(row=1, column=1, sticky="e", padx=14, pady=(0, 6))

        MarkdownFrame(bubble, bg=CLR_USER_BG, initial_text=content).pack(
            fill="both", expand=True
        )

    def pack(self, **kwargs):
        """Ensure fill=x so the internal grid spacer has full row width."""
        kwargs.setdefault("fill", "x")
        super().pack(**kwargs)


# ── Assistant bubble (static) ─────────────────────────────────────────────────
class AssistantBubble(ctk.CTkFrame):
    """Left-aligned completed assistant message."""

    def __init__(self, parent, content: str, stop_reason=None, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)

        ctk.CTkLabel(
            self, text="Claude",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=CLR_ACCENT,
        ).pack(anchor="w", padx=14, pady=(4, 2))

        bubble = tk.Frame(self, bg=CLR_ASST_BG, bd=0, highlightthickness=0)
        bubble.pack(anchor="w", padx=14, pady=(0, 2), fill="x", expand=True)

        MarkdownFrame(bubble, bg=CLR_ASST_BG, initial_text=content).pack(
            fill="both", expand=True
        )

        if stop_reason:
            add_stop_indicator(self, stop_reason, anchor="w")


# ── Streaming bubble ──────────────────────────────────────────────────────────
class StreamingBubble(ctk.CTkFrame):
    """
    Live assistant bubble during API streaming.
    Chunks are buffered and markdown is re-rendered every REFRESH_MS ms
    so partial tokens don't break the markdown parser.
    """
    REFRESH_MS = 120

    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)

        ctk.CTkLabel(
            self, text="Claude",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=CLR_ACCENT,
        ).pack(anchor="w", padx=14, pady=(4, 2))

        self._bubble = tk.Frame(self, bg=CLR_ASST_BG, bd=0, highlightthickness=0)
        self._bubble.pack(anchor="w", padx=14, pady=(0, 2), fill="x", expand=True)

        self._md = MarkdownFrame(self._bubble, bg=CLR_ASST_BG, initial_text="▌")
        self._md.pack(fill="both", expand=True)

        self._text     = ""
        self._pending  = False
        self._finished = False

    def append(self, chunk: str):
        self._text += chunk
        if not self._pending:
            self._pending = True
            self.after(self.REFRESH_MS, self._flush)

    def _flush(self):
        self._pending = False
        if not self._finished:
            self._md.set_text(self._text + " ▌")

    def finish(self, stop_reason=None):
        self._finished = True
        self._md.set_text(self._text)
        if stop_reason:
            add_stop_indicator(self, stop_reason, anchor="w")


# ── Log bubble ────────────────────────────────────────────────────────────────
class LogBubble(ctk.CTkFrame):
    """
    Full-width diagnostic card for the Message Log tab.
    Deep blue = USER  /  Deep purple = ASSISTANT  /  Dark red = ERROR.
    Header shows: role · timestamp · token counts · stop-reason badge.
    Body renders the message content as markdown.
    """

    def __init__(self, parent, role: str, content: str,
                 timestamp: str = "", stop_reason=None,
                 input_tokens: int = 0, output_tokens: int = 0, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)

        is_user    = role == "user"
        is_error   = role == "error"
        bg_color   = CLR_LOG_USER_BG   if is_user else (CLR_LOG_ERR_BG   if is_error else CLR_LOG_ASST_BG)
        hdr_color  = CLR_LOG_USER_HDR  if is_user else (CLR_LOG_ERR_HDR  if is_error else CLR_LOG_ASST_HDR)
        role_color = CLR_LOG_USER_ROLE if is_user else (CLR_LOG_ERR_ROLE if is_error else CLR_LOG_ASST_ROLE)
        role_label = "USER"            if is_user else ("ERROR"           if is_error else "ASSISTANT")

        card = ctk.CTkFrame(self, fg_color=bg_color, corner_radius=10)
        card.pack(fill="x", padx=12, pady=5)

        # Header
        hdr = ctk.CTkFrame(card, fg_color=hdr_color, corner_radius=8)
        hdr.pack(fill="x")
        hdr.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            hdr, text=role_label,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=role_color,
        ).grid(row=0, column=0, padx=14, pady=9, sticky="w")

        ctk.CTkLabel(
            hdr, text=self._fmt_ts(timestamp),
            font=ctk.CTkFont(size=11),
            text_color=CLR_SUBTEXT,
        ).grid(row=0, column=1, padx=8, pady=9, sticky="w")

        parts = []
        if input_tokens:  parts.append(f"↑ {input_tokens:,} in")
        if output_tokens: parts.append(f"↓ {output_tokens:,} out")
        if parts:
            ctk.CTkLabel(
                hdr, text="  ".join(parts),
                font=ctk.CTkFont(size=11),
                text_color=CLR_SUBTEXT,
            ).grid(row=0, column=2, padx=12, pady=9, sticky="e")

        if stop_reason:
            ok  = stop_reason == "end_turn"
            lbl = ctk.CTkLabel(
                hdr,
                text="✓" if ok else "⚠",
                text_color=CLR_GREEN if ok else CLR_AMBER,
                font=ctk.CTkFont(size=14),
                cursor="hand2",
            )
            lbl.grid(row=0, column=3, padx=(0, 14), pady=9, sticky="e")
            Tooltip(lbl, f"Stop reason: {stop_reason}")

        # Body
        body = tk.Frame(card, bg=bg_color, bd=0, highlightthickness=0)
        body.pack(fill="both", expand=True, padx=2, pady=(2, 8))
        MarkdownFrame(body, bg=bg_color, initial_text=content).pack(
            fill="both", expand=True
        )

    @staticmethod
    def _fmt_ts(ts: str) -> str:
        if not ts:
            return ""
        try:
            return datetime.fromisoformat(ts).strftime("%Y-%m-%d  %H:%M:%S")
        except ValueError:
            return ts