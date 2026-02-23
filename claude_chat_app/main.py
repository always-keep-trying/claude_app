"""
main.py  –  Claude Chat App
A local desktop interface for the Anthropic Claude API.

Usage:
    pip install -r requirements.txt
    python main.py
"""

import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk
from anthropic import Anthropic

from config_manager import AVAILABLE_MODELS, ConfigManager
from history_manager import MODEL_PRICING, HistoryManager

# ── Global appearance ────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

APP_DIR = Path.home() / ".claude_chat_app"
APP_DIR.mkdir(parents=True, exist_ok=True)

# Colours used throughout
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


# ── Tooltip helper ────────────────────────────────────────────────────────────
class Tooltip:
    """Lightweight hover tooltip for any widget."""

    def __init__(self, widget: tk.Widget, text: str):
        self._widget = widget
        self._text   = text
        self._win: tk.Toplevel | None = None
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
        tk.Label(
            tw,
            text=self._text,
            background="#1e293b",
            foreground="#e2e8f0",
            relief="solid",
            borderwidth=1,
            padx=8,
            pady=4,
            font=("Segoe UI", 10) if tk.TkVersion >= 8.5 else ("", 10),
        ).pack()

    def _hide(self, _event=None):
        if self._win:
            self._win.destroy()
            self._win = None


# ── Settings dialog ───────────────────────────────────────────────────────────
class SettingsDialog(ctk.CTkToplevel):
    """Modal window for editing the local configuration file."""

    def __init__(self, parent: "ChatApp", cfg: ConfigManager):
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

        def section(text: str):
            ctk.CTkLabel(
                scroll, text=text, anchor="w",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=CLR_SUBTEXT,
            ).pack(fill="x", pady=(16, 3))

        def row_entry(label: str, var: tk.Variable, show: str = ""):
            ctk.CTkLabel(scroll, text=label, anchor="w",
                         font=ctk.CTkFont(size=13), text_color=CLR_TEXT).pack(fill="x", pady=(6, 2))
            return ctk.CTkEntry(scroll, textvariable=var, show=show,
                                fg_color=CLR_BG_LIGHT, border_color="#334155",
                                text_color=CLR_TEXT, height=36)

        # ── API Key ──────────────────────────────────────────────────────────
        section("AUTHENTICATION")
        self._api_var = tk.StringVar(value=self._cfg.get("api_key", ""))
        api_entry = row_entry("API Key", self._api_var, show="•")
        api_entry.pack(fill="x")

        def toggle_visibility():
            if api_entry.cget("show") == "•":
                api_entry.configure(show="")
                vis_btn.configure(text="Hide")
            else:
                api_entry.configure(show="•")
                vis_btn.configure(text="Show")

        vis_btn = ctk.CTkButton(scroll, text="Show", width=70, height=28,
                                fg_color=CLR_BG_LIGHT, hover_color="#334155",
                                text_color=CLR_SUBTEXT, command=toggle_visibility)
        vis_btn.pack(anchor="e", pady=(3, 0))

        # ── Model ────────────────────────────────────────────────────────────
        section("MODEL")
        ctk.CTkLabel(scroll, text="Model", anchor="w",
                     font=ctk.CTkFont(size=13), text_color=CLR_TEXT).pack(fill="x", pady=(6, 2))
        self._model_var = tk.StringVar(value=self._cfg.get("model", AVAILABLE_MODELS[1]))
        ctk.CTkOptionMenu(scroll, variable=self._model_var, values=AVAILABLE_MODELS,
                          fg_color=CLR_BG_LIGHT, button_color=CLR_ACCENT,
                          button_hover_color=CLR_ACCENT_HV, dropdown_fg_color=CLR_BG_LIGHT,
                          text_color=CLR_TEXT, height=36).pack(fill="x")

        # Pricing hint
        def _pricing_text(_=None):
            m = self._model_var.get()
            p = MODEL_PRICING.get(m, {"input": "?", "output": "?"})
            return f"${p['input']}/M input · ${p['output']}/M output"

        self._pricing_label = ctk.CTkLabel(scroll, text=_pricing_text(),
                                            font=ctk.CTkFont(size=11),
                                            text_color=CLR_SUBTEXT, anchor="w")
        self._pricing_label.pack(fill="x", pady=(2, 0))
        self._model_var.trace_add("write", lambda *_: self._pricing_label.configure(text=_pricing_text()))

        # ── Parameters ───────────────────────────────────────────────────────
        section("PARAMETERS")
        self._max_tokens_var = tk.StringVar(value=str(self._cfg.get("max_tokens", 8096)))
        e = row_entry("Max Tokens", self._max_tokens_var)
        e.pack(fill="x")

        self._temp_var = tk.StringVar(value=str(self._cfg.get("temperature", 1.0)))
        e2 = row_entry("Temperature  (0.0 – 1.0)", self._temp_var)
        e2.pack(fill="x")

        # ── System prompt ────────────────────────────────────────────────────
        section("SYSTEM PROMPT")
        self._sys_box = ctk.CTkTextbox(scroll, height=110, wrap="word",
                                        fg_color=CLR_BG_LIGHT, border_color="#334155",
                                        text_color=CLR_TEXT, font=ctk.CTkFont(size=12))
        self._sys_box.pack(fill="x", pady=(3, 0))
        self._sys_box.insert("1.0", self._cfg.get("system_prompt", ""))

        # ── Save ─────────────────────────────────────────────────────────────
        ctk.CTkButton(
            scroll, text="Save Settings", height=40,
            fg_color=CLR_ACCENT, hover_color=CLR_ACCENT_HV,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._save,
        ).pack(fill="x", pady=(24, 8))

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
            messagebox.showerror("Validation Error", "Temperature must be a number between 0.0 and 1.0.", parent=self)
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
    """Shows a breakdown of token usage and costs per model."""

    def __init__(self, parent: "ChatApp", usage: dict):
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

        total_in  = usage.get("input_tokens", 0)
        total_out = usage.get("output_tokens", 0)
        total_cost = usage.get("total_cost", 0.0)

        def row(label, value):
            f = ctk.CTkFrame(frame, fg_color="transparent")
            f.pack(fill="x", pady=2)
            ctk.CTkLabel(f, text=label, text_color=CLR_SUBTEXT,
                         font=ctk.CTkFont(size=12)).pack(side="left")
            ctk.CTkLabel(f, text=value, text_color=CLR_TEXT,
                         font=ctk.CTkFont(size=12)).pack(side="right")

        row("Total Input Tokens",  f"{total_in:,}")
        row("Total Output Tokens", f"{total_out:,}")
        row("Total Tokens",        f"{total_in + total_out:,}")
        row("Estimated Cost",      f"${total_cost:.4f}")

        by_model = usage.get("by_model", {})
        if by_model:
            ctk.CTkLabel(frame, text="— Per Model —",
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=CLR_SUBTEXT).pack(pady=(16, 6))
            for model, stats in by_model.items():
                ctk.CTkLabel(frame, text=model, text_color=CLR_ACCENT,
                             font=ctk.CTkFont(size=12)).pack(anchor="w", pady=(6, 2))
                row("  Input", f"{stats['input_tokens']:,}")
                row("  Output", f"{stats['output_tokens']:,}")
                row("  Cost", f"${stats['cost']:.4f}")

        ctk.CTkButton(frame, text="Close", fg_color=CLR_BG_LIGHT,
                      hover_color="#334155", text_color=CLR_TEXT,
                      command=self.destroy).pack(pady=(20, 0))


# ── Message bubble widget ─────────────────────────────────────────────────────
class MessageBubble(ctk.CTkFrame):
    """Renders a single chat message (user or assistant)."""

    _CHAR_WIDTH = 90   # approximate chars per line for height estimation

    def __init__(self, parent, role: str, content: str,
                 stop_reason: str | None = None, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)

        is_user = role == "user"

        # Role badge
        ctk.CTkLabel(
            self,
            text="You" if is_user else "Claude",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=CLR_SUBTEXT if is_user else CLR_ACCENT,
        ).pack(anchor="e" if is_user else "w", padx=14, pady=(4, 2))

        # Bubble frame
        bubble = ctk.CTkFrame(self, fg_color=CLR_USER_BG if is_user else CLR_ASST_BG,
                               corner_radius=12)
        bubble.pack(
            anchor="e" if is_user else "w",
            padx=14,
            fill="x" if not is_user else None,
            expand=not is_user,
        )

        # Text box
        tb = ctk.CTkTextbox(
            bubble,
            wrap="word",
            activate_scrollbars=False,
            fg_color="transparent",
            text_color=CLR_TEXT,
            font=ctk.CTkFont(size=13),
            height=self._estimate_height(content),
        )
        tb.pack(fill="both", expand=True, padx=12, pady=10)
        tb.insert("1.0", content)
        tb.configure(state="disabled")

        # Stop-reason indicator (assistant only)
        if not is_user and stop_reason:
            self._add_indicator(stop_reason)

    def _estimate_height(self, text: str) -> int:
        lines = text.count("\n") + 1
        wrapped = max(lines, len(text) // self._CHAR_WIDTH + 1)
        return min(max(wrapped * 22 + 20, 44), 500)

    def _add_indicator(self, stop_reason: str):
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(anchor="w", padx=14, pady=(0, 4))

        ok = stop_reason == "end_turn"
        symbol = "✓" if ok else "⚠"
        color  = CLR_GREEN if ok else CLR_AMBER

        lbl = ctk.CTkLabel(row, text=symbol, text_color=color,
                            font=ctk.CTkFont(size=13), cursor="hand2")
        lbl.pack(side="left")
        Tooltip(lbl, f"Stop reason: {stop_reason}")


# ── Streaming assistant bubble ────────────────────────────────────────────────
class StreamingBubble(ctk.CTkFrame):
    """A live-updating assistant bubble for streaming responses."""

    _CHAR_WIDTH = 90

    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)

        ctk.CTkLabel(
            self, text="Claude",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=CLR_ACCENT,
        ).pack(anchor="w", padx=14, pady=(4, 2))

        self._bubble = ctk.CTkFrame(self, fg_color=CLR_ASST_BG, corner_radius=12)
        self._bubble.pack(anchor="w", padx=14, fill="x", expand=True)

        self._tb = ctk.CTkTextbox(
            self._bubble, wrap="word", activate_scrollbars=False,
            fg_color="transparent", text_color=CLR_TEXT,
            font=ctk.CTkFont(size=13), height=44,
        )
        self._tb.pack(fill="both", expand=True, padx=12, pady=10)
        self._tb.insert("1.0", "▌")

        self._text = ""

    def append(self, chunk: str):
        self._text += chunk
        self._tb.configure(state="normal")
        self._tb.delete("1.0", "end")
        self._tb.insert("1.0", self._text + " ▌")
        h = min(max((self._text.count("\n") + 1 + len(self._text) // self._CHAR_WIDTH + 1) * 22 + 20, 44), 500)
        self._tb.configure(height=h, state="disabled")

    def finish(self, stop_reason: str | None):
        """Remove cursor, show final text, and add stop-reason indicator."""
        self._tb.configure(state="normal")
        self._tb.delete("1.0", "end")
        self._tb.insert("1.0", self._text)
        self._tb.configure(state="disabled")

        if stop_reason:
            row = ctk.CTkFrame(self, fg_color="transparent")
            row.pack(anchor="w", padx=14, pady=(0, 4))
            ok     = stop_reason == "end_turn"
            symbol = "✓" if ok else "⚠"
            color  = CLR_GREEN if ok else CLR_AMBER
            lbl    = ctk.CTkLabel(row, text=symbol, text_color=color,
                                   font=ctk.CTkFont(size=13), cursor="hand2")
            lbl.pack(side="left")
            Tooltip(lbl, f"Stop reason: {stop_reason}")


# ── Main application window ───────────────────────────────────────────────────
class ChatApp(ctk.CTk):

    def __init__(self):
        super().__init__()

        self._cfg  = ConfigManager(APP_DIR)
        self._hist = HistoryManager(APP_DIR)

        self._generating = False
        self._stream_bubble: StreamingBubble | None = None

        self.title("Claude Chat")
        self.geometry("1150x760")
        self.minsize(820, 560)
        self.configure(fg_color=CLR_BG_DARK)

        self._build_layout()
        self._refresh_chat_list()
        self._refresh_usage()

        # Open a blank chat on launch
        self._new_chat()

    # ── Layout ───────────────────────────────────────────────────────────────

    def _build_layout(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ── Top bar ──────────────────────────────────────────────────────────
        topbar = ctk.CTkFrame(self, height=48, corner_radius=0, fg_color=CLR_SIDEBAR,
                               border_width=0)
        topbar.grid(row=0, column=0, columnspan=2, sticky="ew")
        topbar.grid_columnconfigure(1, weight=1)
        topbar.grid_propagate(False)

        ctk.CTkLabel(topbar, text="⚡  Claude Chat",
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=CLR_TEXT).grid(row=0, column=0, padx=16, pady=10, sticky="w")

        # Clickable usage display (opens breakdown dialog)
        self._usage_btn = ctk.CTkButton(
            topbar, text="Tokens: —  |  Cost: $—",
            font=ctk.CTkFont(size=12),
            text_color=CLR_SUBTEXT,
            fg_color="transparent", hover_color=CLR_BG_LIGHT,
            command=self._show_usage_detail,
            anchor="e",
        )
        self._usage_btn.grid(row=0, column=2, padx=16, pady=10, sticky="e")

        # ── Sidebar ───────────────────────────────────────────────────────────
        sidebar = ctk.CTkFrame(self, width=230, corner_radius=0, fg_color=CLR_SIDEBAR)
        sidebar.grid(row=1, column=0, sticky="nsew")
        sidebar.grid_rowconfigure(1, weight=1)
        sidebar.grid_columnconfigure(0, weight=1)
        sidebar.grid_propagate(False)

        ctk.CTkButton(
            sidebar, text="＋  New Chat", height=38,
            fg_color=CLR_ACCENT, hover_color=CLR_ACCENT_HV,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._new_chat,
        ).grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self._chat_list = ctk.CTkScrollableFrame(sidebar, fg_color="transparent",
                                                  label_text="HISTORY",
                                                  label_font=ctk.CTkFont(size=10),
                                                  label_text_color=CLR_SUBTEXT)
        self._chat_list.grid(row=1, column=0, padx=6, pady=(0, 6), sticky="nsew")
        self._chat_list.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            sidebar, text="⚙  Settings", height=36,
            fg_color=CLR_BG_LIGHT, hover_color="#334155",
            text_color=CLR_TEXT, font=ctk.CTkFont(size=12),
            command=self._open_settings,
        ).grid(row=2, column=0, padx=10, pady=10, sticky="ew")

        # ── Main chat area ────────────────────────────────────────────────────
        main = ctk.CTkFrame(self, corner_radius=0, fg_color=CLR_BG_DARK)
        main.grid(row=1, column=1, sticky="nsew", padx=(1, 0))
        main.grid_rowconfigure(0, weight=1)
        main.grid_columnconfigure(0, weight=1)

        self._messages_frame = ctk.CTkScrollableFrame(main, fg_color=CLR_BG_DARK)
        self._messages_frame.grid(row=0, column=0, sticky="nsew")
        self._messages_frame.grid_columnconfigure(0, weight=1)

        # Input row
        input_row = ctk.CTkFrame(main, height=90, corner_radius=0, fg_color=CLR_BG_MID)
        input_row.grid(row=1, column=0, sticky="ew")
        input_row.grid_columnconfigure(0, weight=1)
        input_row.grid_propagate(False)

        self._input = ctk.CTkTextbox(
            input_row, height=60, wrap="word",
            fg_color=CLR_BG_LIGHT, text_color=CLR_TEXT,
            border_color="#334155", border_width=1,
            font=ctk.CTkFont(size=13),
        )
        self._input.grid(row=0, column=0, padx=(12, 6), pady=14, sticky="ew")
        self._input.bind("<Return>",       self._on_enter)
        self._input.bind("<Shift-Return>", lambda e: None)

        self._send_btn = ctk.CTkButton(
            input_row, text="Send", width=88, height=60,
            fg_color=CLR_ACCENT, hover_color=CLR_ACCENT_HV,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._send,
        )
        self._send_btn.grid(row=0, column=1, padx=(0, 12), pady=14)

    # ── Chat list helpers ─────────────────────────────────────────────────────

    def _refresh_chat_list(self):
        for w in self._chat_list.winfo_children():
            w.destroy()

        current = self._hist.current_chat_id
        for chat in self._hist.list_chats():
            is_active = chat["id"] == current
            btn = ctk.CTkButton(
                self._chat_list,
                text=chat["title"],
                anchor="w",
                font=ctk.CTkFont(size=11),
                fg_color=CLR_BG_LIGHT if is_active else "transparent",
                hover_color=CLR_BG_LIGHT,
                text_color=CLR_TEXT if is_active else CLR_SUBTEXT,
                command=lambda cid=chat["id"]: self._load_chat(cid),
            )
            btn.pack(fill="x", padx=2, pady=1)

    def _new_chat(self):
        if self._generating:
            return
        self._hist.new_chat()
        self._clear_messages()
        self._refresh_chat_list()

    def _load_chat(self, chat_id: str):
        if self._generating:
            return
        messages = self._hist.load_chat(chat_id)
        self._clear_messages()
        for msg in messages:
            MessageBubble(
                self._messages_frame,
                role=msg["role"],
                content=msg["content"],
                stop_reason=msg.get("stop_reason"),
            ).pack(fill="x", pady=2)
        self._refresh_chat_list()
        self._scroll_bottom()

    def _clear_messages(self):
        for w in self._messages_frame.winfo_children():
            w.destroy()

    # ── Message sending ───────────────────────────────────────────────────────

    def _on_enter(self, event):
        if not (event.state & 0x1):   # Shift not held
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

        # Clear input and show user bubble
        self._input.delete("1.0", "end")
        self._hist.add_message("user", text)
        MessageBubble(self._messages_frame, role="user", content=text).pack(fill="x", pady=2)
        self._refresh_chat_list()

        # Prepare streaming bubble
        self._stream_bubble = StreamingBubble(self._messages_frame)
        self._stream_bubble.pack(fill="x", pady=2)
        self._scroll_bottom()

        # Disable UI
        self._generating = True
        self._send_btn.configure(state="disabled", text="…")

        threading.Thread(target=self._api_thread, args=(api_key, text), daemon=True).start()

    def _api_thread(self, api_key: str, _user_text: str):
        model       = self._cfg.get("model", "claude-sonnet-4-6")
        max_tokens  = self._cfg.get("max_tokens", 8096)
        temperature = self._cfg.get("temperature", 1.0)
        system      = self._cfg.get("system_prompt", "")

        # Build full message list for this request
        messages = [
            {"role": m["role"], "content": m["content"]}
            for m in self._hist.current_messages
        ]

        kwargs: dict = dict(model=model, max_tokens=max_tokens, messages=messages)
        if system:
            kwargs["system"] = system
        if temperature != 1.0:
            kwargs["temperature"] = temperature

        full_text   = ""
        stop_reason = None
        in_tokens   = 0
        out_tokens  = 0

        try:
            client = Anthropic(api_key=api_key)
            with client.messages.stream(**kwargs) as stream:
                for chunk in stream.text_stream:
                    full_text += chunk
                    self.after(0, self._on_chunk, chunk)

            final = stream.get_final_message()
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

    def _on_done(self, full_text: str, stop_reason: str | None,
                 in_tok: int, out_tok: int, model: str):
        if self._stream_bubble:
            self._stream_bubble.finish(stop_reason)
            self._stream_bubble = None

        self._hist.add_message("assistant", full_text, stop_reason, in_tok, out_tok)
        self._hist.record_usage(in_tok, out_tok, model)
        self._refresh_usage()
        self._refresh_chat_list()
        self._finish_generating()
        self._scroll_bottom()

    def _on_error(self, msg: str):
        if self._stream_bubble:
            # Show error inside the bubble
            err_lbl = ctk.CTkLabel(
                self._stream_bubble, text=f"⚠ Error: {msg}",
                text_color=CLR_RED, wraplength=680, justify="left",
                font=ctk.CTkFont(size=12),
            )
            err_lbl.pack(anchor="w", padx=14, pady=(0, 8))
            self._stream_bubble = None

        self._finish_generating()

    def _finish_generating(self):
        self._generating = False
        self._send_btn.configure(state="normal", text="Send")

    # ── Scroll ────────────────────────────────────────────────────────────────

    def _scroll_bottom(self):
        self.after(80, lambda: self._messages_frame._parent_canvas.yview_moveto(1.0))

    # ── Usage ─────────────────────────────────────────────────────────────────

    def _refresh_usage(self):
        u = self._hist.get_total_usage()
        total = u["input_tokens"] + u["output_tokens"]
        cost  = u["total_cost"]
        self._usage_btn.configure(text=f"Tokens: {total:,}  |  Cost: ${cost:.4f}")

    def _show_usage_detail(self):
        UsageDetailDialog(self, self._hist.get_total_usage())

    # ── Settings ──────────────────────────────────────────────────────────────

    def _open_settings(self):
        dlg = SettingsDialog(self, self._cfg)
        dlg.wait_window()


# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    app = ChatApp()
    app.mainloop()


if __name__ == "__main__":
    main()
