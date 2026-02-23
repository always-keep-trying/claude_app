"""
main.py  –  Claude Chat App
A local desktop interface for the Anthropic Claude API.

Usage:
    pip install -r requirements.txt
    python main.py
"""

import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk
import markdown as md_lib
from anthropic import Anthropic
from tkinterweb import HtmlFrame

from config_manager import AVAILABLE_MODELS, ConfigManager
from history_manager import MODEL_PRICING, HistoryManager

# ── Global appearance ────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

APP_DIR = Path.home() / ".claude_chat_app"
APP_DIR.mkdir(parents=True, exist_ok=True)

# Colours — chat
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

# Colours — log tab
CLR_LOG_USER_BG   = "#0f2a45"
CLR_LOG_USER_HDR  = "#1a3f63"
CLR_LOG_USER_ROLE = "#60a5fa"
CLR_LOG_ASST_BG   = "#1e1030"
CLR_LOG_ASST_HDR  = "#2d1a4a"
CLR_LOG_ASST_ROLE = "#a78bfa"

# ── Markdown extensions ───────────────────────────────────────────────────────
MD_EXTENSIONS = [
    "tables",
    "fenced_code",
    "codehilite",
    "nl2br",
    "sane_lists",
    "attr_list",
]
MD_EXT_CONFIGS = {
    "codehilite": {"css_class": "highlight", "guess_lang": True},
}

# ── Base CSS injected into every rendered bubble ──────────────────────────────
def _make_css(bg: str, text: str = CLR_TEXT) -> str:
    return f"""
    <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
        background: {bg};
        color: {text};
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        font-size: 13px;
        line-height: 1.6;
        padding: 10px 14px;
        word-wrap: break-word;
    }}
    h1, h2, h3, h4, h5, h6 {{
        color: #f0f4ff;
        margin: 14px 0 6px 0;
        line-height: 1.3;
    }}
    h1 {{ font-size: 1.5em; border-bottom: 1px solid #334155; padding-bottom: 4px; }}
    h2 {{ font-size: 1.25em; }}
    h3 {{ font-size: 1.1em;  }}
    p {{ margin: 6px 0; }}
    a {{ color: #60a5fa; }}
    strong {{ color: #f8fafc; font-weight: 600; }}
    em {{ color: #e2d9f3; font-style: italic; }}
    code {{
        font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
        font-size: 12px;
        background: #0d1117;
        color: #e6edf3;
        padding: 1px 5px;
        border-radius: 4px;
    }}
    pre {{
        background: #0d1117;
        color: #e6edf3;
        border: 1px solid #30363d;
        border-radius: 6px;
        padding: 12px 14px;
        margin: 10px 0;
        overflow-x: auto;
        font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
        font-size: 12px;
        line-height: 1.5;
    }}
    pre code {{ background: none; padding: 0; border-radius: 0; }}
    blockquote {{
        border-left: 3px solid #475569;
        color: {CLR_SUBTEXT};
        margin: 8px 0;
        padding: 4px 0 4px 14px;
        font-style: italic;
    }}
    ul, ol {{
        margin: 6px 0 6px 22px;
        padding: 0;
    }}
    li {{ margin: 3px 0; }}
    ul ul, ol ol, ul ol, ol ul {{
        margin-top: 3px;
        margin-bottom: 3px;
    }}
    table {{
        border-collapse: collapse;
        width: 100%;
        margin: 10px 0;
        font-size: 12px;
    }}
    th {{
        background: #1e293b;
        color: #94a3b8;
        font-weight: 600;
        text-align: left;
        padding: 7px 10px;
        border: 1px solid #334155;
    }}
    td {{
        padding: 6px 10px;
        border: 1px solid #2d3748;
        vertical-align: top;
    }}
    tr:nth-child(even) td {{ background: #181f2a; }}
    tr:nth-child(odd)  td {{ background: {bg}; }}
    hr {{
        border: none;
        border-top: 1px solid #334155;
        margin: 12px 0;
    }}
    /* pygments code highlighting */
    .highlight .hll {{ background-color: #49483e }}
    .highlight .c  {{ color: #75715e; font-style: italic }}
    .highlight .k  {{ color: #66d9ef }}
    .highlight .n  {{ color: #f8f8f2 }}
    .highlight .o  {{ color: #f92672 }}
    .highlight .cm {{ color: #75715e; font-style: italic }}
    .highlight .cp {{ color: #75715e; font-weight: bold }}
    .highlight .cs {{ color: #75715e; font-style: italic }}
    .highlight .kc {{ color: #66d9ef }}
    .highlight .kd {{ color: #66d9ef }}
    .highlight .kn {{ color: #f92672 }}
    .highlight .kp {{ color: #66d9ef }}
    .highlight .kr {{ color: #66d9ef }}
    .highlight .kt {{ color: #66d9ef }}
    .highlight .s  {{ color: #e6db74 }}
    .highlight .na {{ color: #a6e22e }}
    .highlight .nb {{ color: #f8f8f2 }}
    .highlight .nc {{ color: #a6e22e }}
    .highlight .nd {{ color: #a6e22e }}
    .highlight .ne {{ color: #a6e22e }}
    .highlight .nf {{ color: #a6e22e }}
    .highlight .ni {{ color: #f8f8f2 }}
    .highlight .nn {{ color: #f8f8f2 }}
    .highlight .nt {{ color: #f92672 }}
    .highlight .nv {{ color: #f8f8f2 }}
    .highlight .s1 {{ color: #e6db74 }}
    .highlight .s2 {{ color: #e6db74 }}
    .highlight .se {{ color: #ae81ff }}
    .highlight .si {{ color: #e6db74 }}
    .highlight .mi {{ color: #ae81ff }}
    .highlight .mf {{ color: #ae81ff }}
    .highlight .mh {{ color: #ae81ff }}
    </style>
    """


def render_html(text: str, bg: str) -> str:
    """Convert markdown to a full HTML document with injected dark CSS."""
    body = md_lib.markdown(
        text,
        extensions=MD_EXTENSIONS,
        extension_configs=MD_EXT_CONFIGS,
    )
    return f"<html><head>{_make_css(bg)}</head><body>{body}</body></html>"


# ── Tooltip ───────────────────────────────────────────────────────────────────
class Tooltip:
    def __init__(self, widget: tk.Widget, text: str):
        self._widget = widget
        self._text   = text
        self._win    = None
        widget.bind("<Enter>", self._show, add="+")
        widget.bind("<Leave>", self._hide, add="+")

    def _show(self, _event=None):
        if self._win:
            return
        x = self._widget.winfo_rootx() + 24
        y = self._widget.winfo_rooty() + 24
        self._win = tw = tk.Toplevel(self._widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tk.Label(tw, text=self._text, background="#1e293b", foreground="#e2e8f0",
                 relief="solid", borderwidth=1, padx=8, pady=4,
                 font=("Segoe UI", 10)).pack()

    def _hide(self, _event=None):
        if self._win:
            self._win.destroy()
            self._win = None


# ── MarkdownFrame — rendered HTML bubble content ──────────────────────────────
class MarkdownFrame(tk.Frame):
    """
    A tkinterweb HtmlFrame that renders markdown as HTML.
    Height auto-adjusts after the first render; updates cleanly for streaming.
    """
    _MIN_H = 36
    _MAX_H = 600

    def __init__(self, parent, bg: str, initial_text: str = "", **kwargs):
        super().__init__(parent, bg=bg, **kwargs)
        self._bg = bg

        self._html_frame = HtmlFrame(
            self,
            messages_enabled=False,
            horizontal_scrollbar="auto",
            vertical_scrollbar=False,
        )
        self._html_frame.pack(fill="both", expand=True)

        self._text = initial_text
        if initial_text:
            self._render(initial_text)

    def _render(self, text: str):
        html = render_html(text, self._bg)
        self._html_frame.load_html(html)
        self.after(150, self._adjust_height)

    def _adjust_height(self):
        """
        Estimate rendered height from content length and line count.
        Avoids relying on tkinterweb internal attributes that vary by version.
        """
        # Count source lines and estimate wrapped lines from character count
        line_count  = self._text.count("\n") + 1
        char_lines  = len(self._text) // 80
        # Code blocks and tables need extra vertical space
        code_blocks = self._text.count("```")  // 2
        table_rows  = self._text.count("\n|")
        estimated   = (
            max(line_count, char_lines) * 20
            + code_blocks * 28
            + table_rows  * 22
            + 24          # padding
        )
        h = max(self._MIN_H, min(estimated, self._MAX_H))
        self.configure(height=h)
        self._html_frame.configure(height=h)

    def set_text(self, text: str):
        self._text = text
        self._render(text)

    def append_text(self, chunk: str):
        self._text += chunk
        self._render(self._text)


# ── Settings dialog ───────────────────────────────────────────────────────────
class SettingsDialog(ctk.CTkToplevel):
    def __init__(self, parent, cfg: ConfigManager):
        super().__init__(parent)
        self._cfg = cfg
        self.title("Settings")
        self.geometry("520x530")
        self.resizable(False, False)
        self.configure(fg_color=CLR_BG_MID)
        self.grab_set()
        self._build()

    def _build(self):
        scroll = ctk.CTkScrollableFrame(self, fg_color=CLR_BG_MID)
        scroll.pack(fill="both", expand=True, padx=24, pady=24)

        def section(text):
            ctk.CTkLabel(scroll, text=text, anchor="w",
                         font=ctk.CTkFont(size=11, weight="bold"),
                         text_color=CLR_SUBTEXT).pack(fill="x", pady=(16, 3))

        def row_entry(label, var, show=""):
            ctk.CTkLabel(scroll, text=label, anchor="w",
                         font=ctk.CTkFont(size=13), text_color=CLR_TEXT).pack(fill="x", pady=(6, 2))
            return ctk.CTkEntry(scroll, textvariable=var, show=show,
                                fg_color=CLR_BG_LIGHT, border_color="#334155",
                                text_color=CLR_TEXT, height=36)

        section("AUTHENTICATION")
        self._api_var = tk.StringVar(value=self._cfg.get("api_key", ""))
        api_entry = row_entry("API Key", self._api_var, show="•")
        api_entry.pack(fill="x")

        def toggle():
            if api_entry.cget("show") == "•":
                api_entry.configure(show="")
                vis_btn.configure(text="Hide")
            else:
                api_entry.configure(show="•")
                vis_btn.configure(text="Show")

        vis_btn = ctk.CTkButton(scroll, text="Show", width=70, height=28,
                                fg_color=CLR_BG_LIGHT, hover_color="#334155",
                                text_color=CLR_SUBTEXT, command=toggle)
        vis_btn.pack(anchor="e", pady=(3, 0))

        section("MODEL")
        ctk.CTkLabel(scroll, text="Model", anchor="w",
                     font=ctk.CTkFont(size=13), text_color=CLR_TEXT).pack(fill="x", pady=(6, 2))
        self._model_var = tk.StringVar(value=self._cfg.get("model", AVAILABLE_MODELS[1]))
        ctk.CTkOptionMenu(scroll, variable=self._model_var, values=AVAILABLE_MODELS,
                          fg_color=CLR_BG_LIGHT, button_color=CLR_ACCENT,
                          button_hover_color=CLR_ACCENT_HV, dropdown_fg_color=CLR_BG_LIGHT,
                          text_color=CLR_TEXT, height=36).pack(fill="x")

        def _pricing_text(_=None):
            p = MODEL_PRICING.get(self._model_var.get(), {"input": "?", "output": "?"})
            return f"${p['input']}/M input · ${p['output']}/M output"

        self._pricing_label = ctk.CTkLabel(scroll, text=_pricing_text(),
                                            font=ctk.CTkFont(size=11),
                                            text_color=CLR_SUBTEXT, anchor="w")
        self._pricing_label.pack(fill="x", pady=(2, 0))
        self._model_var.trace_add("write", lambda *_: self._pricing_label.configure(text=_pricing_text()))

        section("PARAMETERS")
        self._max_tokens_var = tk.StringVar(value=str(self._cfg.get("max_tokens", 8096)))
        row_entry("Max Tokens", self._max_tokens_var).pack(fill="x")
        self._temp_var = tk.StringVar(value=str(self._cfg.get("temperature", 1.0)))
        row_entry("Temperature  (0.0 – 1.0)", self._temp_var).pack(fill="x")

        section("SYSTEM PROMPT")
        self._sys_box = ctk.CTkTextbox(scroll, height=110, wrap="word",
                                        fg_color=CLR_BG_LIGHT, border_color="#334155",
                                        text_color=CLR_TEXT, font=ctk.CTkFont(size=12))
        self._sys_box.pack(fill="x", pady=(3, 0))
        self._sys_box.insert("1.0", self._cfg.get("system_prompt", ""))

        ctk.CTkButton(scroll, text="Save Settings", height=40,
                      fg_color=CLR_ACCENT, hover_color=CLR_ACCENT_HV,
                      font=ctk.CTkFont(size=14, weight="bold"),
                      command=self._save).pack(fill="x", pady=(24, 8))

    def _save(self):
        try:
            max_tokens = int(self._max_tokens_var.get())
        except ValueError:
            messagebox.showerror("Validation Error", "Max Tokens must be a whole number.", parent=self)
            return
        try:
            temperature = float(self._temp_var.get())
            if not (0.0 <= temperature <= 1.0):
                raise ValueError
        except ValueError:
            messagebox.showerror("Validation Error", "Temperature must be 0.0 – 1.0.", parent=self)
            return
        self._cfg.update({
            "api_key":       self._api_var.get().strip(),
            "model":         self._model_var.get(),
            "max_tokens":    max_tokens,
            "temperature":   temperature,
            "system_prompt": self._sys_box.get("1.0", "end-1c"),
        })
        messagebox.showinfo("Saved", "Settings saved successfully.", parent=self)
        self.destroy()


# ── Usage detail popup ────────────────────────────────────────────────────────
class UsageDetailDialog(ctk.CTkToplevel):
    def __init__(self, parent, usage: dict):
        super().__init__(parent)
        self.title("Usage Breakdown")
        self.geometry("420x340")
        self.resizable(False, False)
        self.configure(fg_color=CLR_BG_MID)
        self.grab_set()

        frame = ctk.CTkScrollableFrame(self, fg_color=CLR_BG_MID)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(frame, text="Cumulative API Usage",
                     font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=CLR_TEXT).pack(anchor="w", pady=(0, 12))

        def row(label, value):
            f = ctk.CTkFrame(frame, fg_color="transparent")
            f.pack(fill="x", pady=2)
            ctk.CTkLabel(f, text=label, text_color=CLR_SUBTEXT,
                         font=ctk.CTkFont(size=12)).pack(side="left")
            ctk.CTkLabel(f, text=value, text_color=CLR_TEXT,
                         font=ctk.CTkFont(size=12)).pack(side="right")

        ti = usage.get("input_tokens", 0)
        to = usage.get("output_tokens", 0)
        row("Total Input Tokens",  f"{ti:,}")
        row("Total Output Tokens", f"{to:,}")
        row("Total Tokens",        f"{ti + to:,}")
        row("Estimated Cost",      f"${usage.get('total_cost', 0.0):.4f}")

        by_model = usage.get("by_model", {})
        if by_model:
            ctk.CTkLabel(frame, text="— Per Model —",
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=CLR_SUBTEXT).pack(pady=(16, 6))
            for model, stats in by_model.items():
                ctk.CTkLabel(frame, text=model, text_color=CLR_ACCENT,
                             font=ctk.CTkFont(size=12)).pack(anchor="w", pady=(6, 2))
                row("  Input",  f"{stats['input_tokens']:,}")
                row("  Output", f"{stats['output_tokens']:,}")
                row("  Cost",   f"${stats['cost']:.4f}")

        ctk.CTkButton(frame, text="Close", fg_color=CLR_BG_LIGHT,
                      hover_color="#334155", text_color=CLR_TEXT,
                      command=self.destroy).pack(pady=(20, 0))


# ── Stop reason indicator (shared) ────────────────────────────────────────────
def add_stop_indicator(parent: tk.Widget, stop_reason: str, anchor: str = "w"):
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(anchor=anchor, padx=14, pady=(0, 6))
    ok  = stop_reason == "end_turn"
    lbl = ctk.CTkLabel(row, text="✓" if ok else "⚠",
                        text_color=CLR_GREEN if ok else CLR_AMBER,
                        font=ctk.CTkFont(size=13), cursor="hand2")
    lbl.pack(side="left")
    Tooltip(lbl, f"Stop reason: {stop_reason}")


# ── Chat — User bubble ────────────────────────────────────────────────────────
class UserBubble(ctk.CTkFrame):
    """
    User message — right-aligned, markdown rendered.
    Uses a two-column grid: col 0 is a weighted spacer that pushes
    the bubble to the right; col 1 holds the bubble itself.
    No <Configure> binding needed — no GIL risk.
    """

    def __init__(self, parent, content: str, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)

        # Spacer column grows; bubble column stays as wide as its content
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)

        ctk.CTkLabel(self, text="You",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=CLR_SUBTEXT,
                     ).grid(row=0, column=0, columnspan=2, sticky="e", padx=14, pady=(4, 2))

        bubble = tk.Frame(self, bg=CLR_USER_BG, bd=0, highlightthickness=0)
        bubble.grid(row=1, column=1, sticky="e", padx=14, pady=(0, 6))

        md = MarkdownFrame(bubble, bg=CLR_USER_BG, initial_text=content)
        md.pack(fill="both", expand=True)


# ── Chat — Assistant bubble (static) ─────────────────────────────────────────
class AssistantBubble(ctk.CTkFrame):
    """Completed assistant message — left-aligned, markdown rendered."""

    def __init__(self, parent, content: str, stop_reason=None, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)

        ctk.CTkLabel(self, text="Claude",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=CLR_ACCENT,
                     ).pack(anchor="w", padx=14, pady=(4, 2))

        bubble = tk.Frame(self, bg=CLR_ASST_BG, bd=0, highlightthickness=0)
        bubble.pack(anchor="w", padx=14, pady=(0, 2), fill="x", expand=True)

        md = MarkdownFrame(bubble, bg=CLR_ASST_BG, initial_text=content)
        md.pack(fill="both", expand=True)

        if stop_reason:
            add_stop_indicator(self, stop_reason, anchor="w")


# ── Chat — Streaming assistant bubble ─────────────────────────────────────────
class StreamingBubble(ctk.CTkFrame):
    """
    Live assistant bubble during streaming.
    Buffers incoming chunks and re-renders markdown every REFRESH_MS milliseconds
    so partial tokens don't break markdown parsing.
    """
    REFRESH_MS = 120

    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)

        ctk.CTkLabel(self, text="Claude",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=CLR_ACCENT,
                     ).pack(anchor="w", padx=14, pady=(4, 2))

        self._bubble = tk.Frame(self, bg=CLR_ASST_BG, bd=0, highlightthickness=0)
        self._bubble.pack(anchor="w", padx=14, pady=(0, 2), fill="x", expand=True)

        self._md = MarkdownFrame(self._bubble, bg=CLR_ASST_BG, initial_text="▌")
        self._md.pack(fill="both", expand=True)

        self._text      = ""
        self._pending   = False
        self._finished  = False

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


# ── Log tab — bubble ──────────────────────────────────────────────────────────
class LogBubble(ctk.CTkFrame):
    """
    Full-width diagnostic card for the Message Log tab.
    Deep blue = USER  /  Deep purple = ASSISTANT
    Header: role label · timestamp · token counts · stop-reason badge
    Body: markdown-rendered message content
    """

    def __init__(self, parent, role: str, content: str,
                 timestamp: str = "", stop_reason=None,
                 input_tokens: int = 0, output_tokens: int = 0, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)

        is_user    = role == "user"
        bg_color   = CLR_LOG_USER_BG   if is_user else CLR_LOG_ASST_BG
        hdr_color  = CLR_LOG_USER_HDR  if is_user else CLR_LOG_ASST_HDR
        role_color = CLR_LOG_USER_ROLE if is_user else CLR_LOG_ASST_ROLE
        role_label = "USER" if is_user else "ASSISTANT"

        card = ctk.CTkFrame(self, fg_color=bg_color, corner_radius=10)
        card.pack(fill="x", padx=12, pady=5)

        # ── Header ───────────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(card, fg_color=hdr_color, corner_radius=8)
        hdr.pack(fill="x")
        hdr.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(hdr, text=role_label,
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=role_color,
                     ).grid(row=0, column=0, padx=14, pady=9, sticky="w")

        ctk.CTkLabel(hdr, text=self._fmt_ts(timestamp),
                     font=ctk.CTkFont(size=11),
                     text_color=CLR_SUBTEXT,
                     ).grid(row=0, column=1, padx=8, pady=9, sticky="w")

        parts = []
        if input_tokens:  parts.append(f"↑ {input_tokens:,} in")
        if output_tokens: parts.append(f"↓ {output_tokens:,} out")
        if parts:
            ctk.CTkLabel(hdr, text="  ".join(parts),
                         font=ctk.CTkFont(size=11),
                         text_color=CLR_SUBTEXT,
                         ).grid(row=0, column=2, padx=12, pady=9, sticky="e")

        if stop_reason:
            ok  = stop_reason == "end_turn"
            lbl = ctk.CTkLabel(hdr, text="✓" if ok else "⚠",
                                text_color=CLR_GREEN if ok else CLR_AMBER,
                                font=ctk.CTkFont(size=14), cursor="hand2")
            lbl.grid(row=0, column=3, padx=(0, 14), pady=9, sticky="e")
            Tooltip(lbl, f"Stop reason: {stop_reason}")

        # ── Markdown content ──────────────────────────────────────────────────
        body = tk.Frame(card, bg=bg_color, bd=0, highlightthickness=0)
        body.pack(fill="both", expand=True, padx=2, pady=(2, 8))

        md = MarkdownFrame(body, bg=bg_color, initial_text=content)
        md.pack(fill="both", expand=True)

    @staticmethod
    def _fmt_ts(ts: str) -> str:
        if not ts:
            return ""
        try:
            return datetime.fromisoformat(ts).strftime("%Y-%m-%d  %H:%M:%S")
        except ValueError:
            return ts


# ── Main application window ───────────────────────────────────────────────────
class ChatApp(ctk.CTk):

    def __init__(self):
        super().__init__()
        self._cfg  = ConfigManager(APP_DIR)
        self._hist = HistoryManager(APP_DIR)
        self._generating  = False
        self._stream_bubble: StreamingBubble | None = None

        self.title("Claude Chat")
        self.geometry("1150x760")
        self.minsize(820, 560)
        self.configure(fg_color=CLR_BG_DARK)

        self._build_layout()
        self._refresh_chat_list()
        self._refresh_usage()
        self._new_chat()

    # ── Layout ───────────────────────────────────────────────────────────────

    def _build_layout(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Top bar
        topbar = ctk.CTkFrame(self, height=48, corner_radius=0, fg_color=CLR_SIDEBAR)
        topbar.grid(row=0, column=0, columnspan=2, sticky="ew")
        topbar.grid_columnconfigure(1, weight=1)
        topbar.grid_propagate(False)

        ctk.CTkLabel(topbar, text="⚡  Claude Chat",
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=CLR_TEXT).grid(row=0, column=0, padx=16, pady=10, sticky="w")

        self._usage_btn = ctk.CTkButton(
            topbar, text="Tokens: —  |  Cost: $—",
            font=ctk.CTkFont(size=12), text_color=CLR_SUBTEXT,
            fg_color="transparent", hover_color=CLR_BG_LIGHT,
            command=self._show_usage_detail, anchor="e")
        self._usage_btn.grid(row=0, column=2, padx=16, pady=10, sticky="e")

        # Sidebar
        sidebar = ctk.CTkFrame(self, width=230, corner_radius=0, fg_color=CLR_SIDEBAR)
        sidebar.grid(row=1, column=0, sticky="nsew")
        sidebar.grid_rowconfigure(1, weight=1)
        sidebar.grid_columnconfigure(0, weight=1)
        sidebar.grid_propagate(False)

        ctk.CTkButton(sidebar, text="＋  New Chat", height=38,
                      fg_color=CLR_ACCENT, hover_color=CLR_ACCENT_HV,
                      font=ctk.CTkFont(size=13, weight="bold"),
                      command=self._new_chat).grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self._chat_list = ctk.CTkScrollableFrame(
            sidebar, fg_color="transparent",
            label_text="HISTORY", label_font=ctk.CTkFont(size=10),
            label_text_color=CLR_SUBTEXT)
        self._chat_list.grid(row=1, column=0, padx=6, pady=(0, 6), sticky="nsew")
        self._chat_list.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(sidebar, text="⚙  Settings", height=36,
                      fg_color=CLR_BG_LIGHT, hover_color="#334155",
                      text_color=CLR_TEXT, font=ctk.CTkFont(size=12),
                      command=self._open_settings).grid(row=2, column=0, padx=10, pady=10, sticky="ew")

        # Main area with tabs
        main = ctk.CTkFrame(self, corner_radius=0, fg_color=CLR_BG_DARK)
        main.grid(row=1, column=1, sticky="nsew", padx=(1, 0))
        main.grid_rowconfigure(0, weight=1)
        main.grid_columnconfigure(0, weight=1)

        self._tabs = ctk.CTkTabview(
            main,
            fg_color=CLR_BG_DARK,
            segmented_button_fg_color=CLR_BG_MID,
            segmented_button_selected_color=CLR_ACCENT,
            segmented_button_selected_hover_color=CLR_ACCENT_HV,
            segmented_button_unselected_color=CLR_BG_MID,
            segmented_button_unselected_hover_color=CLR_BG_LIGHT,
            text_color=CLR_TEXT,
            text_color_disabled=CLR_SUBTEXT,
        )
        self._tabs.grid(row=0, column=0, sticky="nsew")
        self._tabs.add("💬  Chat")
        self._tabs.add("📋  Message Log")

        # Larger tab buttons
        try:
            self._tabs._segmented_button.configure(
                font=ctk.CTkFont(size=14, weight="bold"),
                height=42,
            )
        except Exception:
            pass

        # Per-tab colours — bind to each button directly, and apply on startup
        self.after(150, self._wire_tab_colors)

        self._build_chat_tab()
        self._build_log_tab()

    # Tab colours: green for Chat, yellow for Log
    _TAB_COLORS = {
        "💬  Chat":        {"active_bg": "#166534", "active_fg": "#bbf7d0", "inactive_fg": "#4ade80"},
        "📋  Message Log": {"active_bg": "#78350f", "active_fg": "#fef3c7", "inactive_fg": "#fbbf24"},
    }

    def _wire_tab_colors(self):
        """
        Wrap each tab button's original command so it still switches tabs
        AND triggers a color update. Then apply colors for the initial state.
        """
        try:
            for name, btn in self._tabs._segmented_button._buttons_dict.items():
                original_cmd = btn.cget("command")

                def make_handler(orig=original_cmd):
                    def handler():
                        if orig:
                            orig()
                        self.after(50, self._apply_tab_colors)
                    return handler

                btn.configure(command=make_handler())
        except Exception:
            pass
        self._apply_tab_colors()

    def _apply_tab_colors(self):
        """Color each tab button independently: green=Chat, yellow=Log."""
        try:
            btns    = self._tabs._segmented_button._buttons_dict
            current = self._tabs.get()
            for name, btn in btns.items():
                cfg = self._TAB_COLORS.get(name, {})
                if name == current:
                    btn.configure(
                        fg_color=cfg.get("active_bg", CLR_ACCENT),
                        text_color=cfg.get("active_fg", CLR_TEXT),
                        hover_color=cfg.get("active_bg", CLR_ACCENT),
                    )
                else:
                    btn.configure(
                        fg_color=CLR_BG_MID,
                        text_color=cfg.get("inactive_fg", CLR_SUBTEXT),
                        hover_color=CLR_BG_LIGHT,
                    )
        except Exception:
            pass

    def _build_chat_tab(self):
        tab = self._tabs.tab("💬  Chat")
        tab.grid_rowconfigure(0, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        self._messages_frame = ctk.CTkScrollableFrame(tab, fg_color=CLR_BG_DARK)
        self._messages_frame.grid(row=0, column=0, sticky="nsew")
        self._messages_frame.grid_columnconfigure(0, weight=1)

        input_row = ctk.CTkFrame(tab, height=90, corner_radius=0, fg_color=CLR_BG_MID)
        input_row.grid(row=1, column=0, sticky="ew")
        input_row.grid_columnconfigure(0, weight=1)
        input_row.grid_propagate(False)

        self._input = ctk.CTkTextbox(
            input_row, height=60, wrap="word",
            fg_color=CLR_BG_LIGHT, text_color=CLR_TEXT,
            border_color="#334155", border_width=1, font=ctk.CTkFont(size=13))
        self._input.grid(row=0, column=0, padx=(12, 6), pady=14, sticky="ew")
        self._input.bind("<Return>",       self._on_enter)
        self._input.bind("<Shift-Return>", lambda e: None)

        self._send_btn = ctk.CTkButton(
            input_row, text="Send", width=88, height=60,
            fg_color=CLR_ACCENT, hover_color=CLR_ACCENT_HV,
            font=ctk.CTkFont(size=13, weight="bold"), command=self._send)
        self._send_btn.grid(row=0, column=1, padx=(0, 12), pady=14)

    def _build_log_tab(self):
        tab = self._tabs.tab("📋  Message Log")
        tab.grid_rowconfigure(1, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        hdr = ctk.CTkFrame(tab, fg_color=CLR_BG_MID, height=36, corner_radius=0)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        hdr.grid_columnconfigure(0, weight=1)

        self._log_header_label = ctk.CTkLabel(
            hdr, text="No active chat", anchor="w",
            font=ctk.CTkFont(size=11), text_color=CLR_SUBTEXT)
        self._log_header_label.grid(row=0, column=0, padx=14, pady=8, sticky="w")

        self._log_frame = ctk.CTkScrollableFrame(tab, fg_color=CLR_BG_DARK)
        self._log_frame.grid(row=1, column=0, sticky="nsew")
        self._log_frame.grid_columnconfigure(0, weight=1)

    # ── Log helpers ───────────────────────────────────────────────────────────

    def _add_log_bubble(self, msg: dict):
        LogBubble(
            self._log_frame,
            role=msg["role"],
            content=msg["content"],
            timestamp=msg.get("timestamp", ""),
            stop_reason=msg.get("stop_reason"),
            input_tokens=msg.get("input_tokens", 0),
            output_tokens=msg.get("output_tokens", 0),
        ).pack(fill="x", pady=0)

    def _clear_log(self):
        for w in self._log_frame.winfo_children():
            w.destroy()

    def _update_log_header(self, chat_id=None):
        if chat_id:
            count = len(self._hist.current_messages)
            self._log_header_label.configure(
                text=f"Chat {chat_id[:8]}…   ·   {count} message{'s' if count != 1 else ''}")
        else:
            self._log_header_label.configure(text="No active chat")

    def _scroll_log_bottom(self):
        self.after(200, lambda: self._log_frame._parent_canvas.yview_moveto(1.0))

    # ── Chat list ─────────────────────────────────────────────────────────────

    def _refresh_chat_list(self):
        for w in self._chat_list.winfo_children():
            w.destroy()
        current = self._hist.current_chat_id
        for chat in self._hist.list_chats():
            is_active = chat["id"] == current
            ctk.CTkButton(
                self._chat_list, text=chat["title"], anchor="w",
                font=ctk.CTkFont(size=11),
                fg_color=CLR_BG_LIGHT if is_active else "transparent",
                hover_color=CLR_BG_LIGHT,
                text_color=CLR_TEXT if is_active else CLR_SUBTEXT,
                command=lambda cid=chat["id"]: self._load_chat(cid),
            ).pack(fill="x", padx=2, pady=1)

    def _new_chat(self):
        if self._generating:
            return
        self._hist.new_chat()
        self._clear_messages()
        self._clear_log()
        self._update_log_header()
        self._refresh_chat_list()

    def _load_chat(self, chat_id: str):
        if self._generating:
            return
        messages = self._hist.load_chat(chat_id)
        self._clear_messages()
        self._clear_log()
        for msg in messages:
            self._append_chat_bubble(msg)
            self._add_log_bubble(msg)
        self._update_log_header(chat_id)
        self._refresh_chat_list()
        self._scroll_bottom()

    def _append_chat_bubble(self, msg: dict):
        if msg["role"] == "user":
            UserBubble(self._messages_frame, content=msg["content"]).pack(fill="x", pady=2)
        else:
            AssistantBubble(self._messages_frame,
                            content=msg["content"],
                            stop_reason=msg.get("stop_reason")).pack(fill="x", pady=2)

    def _clear_messages(self):
        for w in self._messages_frame.winfo_children():
            w.destroy()

    # ── Message sending ───────────────────────────────────────────────────────

    def _on_enter(self, event):
        if not (event.state & 0x1):
            self._send()
            return "break"

    def _send(self):
        if self._generating:
            return
        text = self._input.get("1.0", "end-1c").strip()
        if not text:
            return
        api_key = self._cfg.get("api_key", "")
        if not api_key:
            messagebox.showwarning("No API Key",
                                   "Please add your Anthropic API key in ⚙ Settings before chatting.")
            return

        self._input.delete("1.0", "end")
        user_msg = self._hist.add_message("user", text)

        UserBubble(self._messages_frame, content=text).pack(fill="x", pady=2)
        self._add_log_bubble(user_msg)
        self._update_log_header(self._hist.current_chat_id)
        self._refresh_chat_list()

        self._stream_bubble = StreamingBubble(self._messages_frame)
        self._stream_bubble.pack(fill="x", pady=2)
        self._scroll_bottom()
        self._scroll_log_bottom()

        self._generating = True
        self._send_btn.configure(state="disabled", text="…")
        threading.Thread(target=self._api_thread, args=(api_key,), daemon=True).start()

    def _api_thread(self, api_key: str):
        model       = self._cfg.get("model", "claude-sonnet-4-6")
        max_tokens  = self._cfg.get("max_tokens", 8096)
        temperature = self._cfg.get("temperature", 1.0)
        system      = self._cfg.get("system_prompt", "")

        messages = [{"role": m["role"], "content": m["content"]}
                    for m in self._hist.current_messages]

        kwargs = dict(model=model, max_tokens=max_tokens, messages=messages)
        if system:       kwargs["system"] = system
        if temperature != 1.0: kwargs["temperature"] = temperature

        full_text = ""
        stop_reason = in_tokens = out_tokens = None

        try:
            client = Anthropic(api_key=api_key)
            with client.messages.stream(**kwargs) as stream:
                for chunk in stream.text_stream:
                    full_text += chunk
                    self.after(0, self._on_chunk, chunk)
            final       = stream.get_final_message()
            stop_reason = final.stop_reason
            in_tokens   = final.usage.input_tokens
            out_tokens  = final.usage.output_tokens
            self.after(0, self._on_done, full_text, stop_reason, in_tokens, out_tokens, model)
        except Exception as exc:
            self.after(0, self._on_error, str(exc))

    def _on_chunk(self, chunk: str):
        if self._stream_bubble:
            self._stream_bubble.append(chunk)
            self._scroll_bottom()

    def _on_done(self, full_text, stop_reason, in_tok, out_tok, model):
        if self._stream_bubble:
            self._stream_bubble.finish(stop_reason)
            self._stream_bubble = None

        asst_msg = self._hist.add_message("assistant", full_text, stop_reason, in_tok, out_tok)
        self._hist.record_usage(in_tok, out_tok, model)

        self._add_log_bubble(asst_msg)
        self._update_log_header(self._hist.current_chat_id)
        self._scroll_log_bottom()

        self._refresh_usage()
        self._refresh_chat_list()
        self._finish_generating()
        self._scroll_bottom()

    def _on_error(self, msg: str):
        if self._stream_bubble:
            ctk.CTkLabel(self._stream_bubble, text=f"⚠ Error: {msg}",
                         text_color=CLR_RED, wraplength=680, justify="left",
                         font=ctk.CTkFont(size=12)).pack(anchor="w", padx=14, pady=(0, 8))
            self._stream_bubble = None
        self._finish_generating()

    def _finish_generating(self):
        self._generating = False
        self._send_btn.configure(state="normal", text="Send")

    def _scroll_bottom(self):
        self.after(200, lambda: self._messages_frame._parent_canvas.yview_moveto(1.0))

    # ── Usage ─────────────────────────────────────────────────────────────────

    def _refresh_usage(self):
        u = self._hist.get_total_usage()
        total = u["input_tokens"] + u["output_tokens"]
        self._usage_btn.configure(text=f"Tokens: {total:,}  |  Cost: ${u['total_cost']:.4f}")

    def _show_usage_detail(self):
        UsageDetailDialog(self, self._hist.get_total_usage())

    def _open_settings(self):
        SettingsDialog(self, self._cfg).wait_window()


# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    ChatApp().mainloop()


if __name__ == "__main__":
    main()