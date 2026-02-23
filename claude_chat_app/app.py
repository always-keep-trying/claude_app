"""
app.py — ChatApp: the main application window.

Responsible for layout, event wiring, chat history interaction,
and the Anthropic API streaming thread.
"""

import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk
from anthropic import Anthropic

from config_manager import ConfigManager
from history_manager import HistoryManager
from scroll import enable_scroll, setup_global_scroll
from theme import (
    CLR_ACCENT, CLR_ACCENT_HV, CLR_BG_DARK, CLR_BG_LIGHT, CLR_BG_MID,
    CLR_RED, CLR_SIDEBAR, CLR_SUBTEXT, CLR_TEXT, TAB_COLORS,
)
from widgets import (
    AssistantBubble, LogBubble, SettingsDialog,
    StreamingBubble, UsageDetailDialog, UserBubble,
)

APP_DIR = Path.home() / ".claude_chat_app"
APP_DIR.mkdir(parents=True, exist_ok=True)


class ChatApp(ctk.CTk):

    def __init__(self):
        super().__init__()
        self._cfg  = ConfigManager(APP_DIR)
        self._hist = HistoryManager(APP_DIR)
        self._generating   = False
        self._stream_bubble: StreamingBubble | None = None

        self.title("Claude Chat")
        self.geometry("1150x760")
        self.minsize(820, 560)
        self.configure(fg_color=CLR_BG_DARK)

        self._build_layout()
        self._refresh_chat_list()
        self._refresh_usage()
        self._new_chat()
        setup_global_scroll(self)

    # ── Layout ───────────────────────────────────────────────────────────────

    def _build_layout(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_topbar()
        self._build_sidebar()
        self._build_main_area()

    def _build_topbar(self):
        topbar = ctk.CTkFrame(self, height=58, corner_radius=0, fg_color=CLR_SIDEBAR)
        topbar.grid(row=0, column=0, columnspan=2, sticky="ew")
        topbar.grid_columnconfigure(1, weight=1)
        topbar.grid_propagate(False)

        ctk.CTkLabel(
            topbar, text="⚡  Claude Chat",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=CLR_TEXT,
        ).grid(row=0, column=0, rowspan=2, padx=16, pady=10, sticky="w")

        # ── Usage display: clickable two-line widget ──────────────────────────
        usage_frame = ctk.CTkFrame(topbar, fg_color="transparent", cursor="hand2")
        usage_frame.grid(row=0, column=2, rowspan=2, padx=16, pady=6, sticky="w")

        # Top line — total tokens + cost
        self._usage_total_label = ctk.CTkLabel(
            usage_frame,
            text="Tokens: —  |  Cost: $—",
            font=ctk.CTkFont(size=12),
            text_color=CLR_SUBTEXT,
            anchor="w",
        )
        self._usage_total_label.pack(anchor="w")

        # Bottom line — three side-by-side labels for coloured in/out breakdown
        breakdown_row = ctk.CTkFrame(usage_frame, fg_color="transparent")
        breakdown_row.pack(anchor="w")

        self._usage_in_label = ctk.CTkLabel(
            breakdown_row, text="↑ — in",
            font=ctk.CTkFont(size=11),
            text_color="#60a5fa",   # soft blue for input
            anchor="w",
        )
        self._usage_in_label.pack(side="left")

        ctk.CTkLabel(
            breakdown_row, text="  ·  ",
            font=ctk.CTkFont(size=11),
            text_color=CLR_SUBTEXT,
        ).pack(side="left")

        self._usage_out_label = ctk.CTkLabel(
            breakdown_row, text="↓ — out",
            font=ctk.CTkFont(size=11),
            text_color="#4ade80",   # soft green for output
            anchor="w",
        )
        self._usage_out_label.pack(side="left")

        # Bind click on every child widget to open the detail dialog
        for widget in [usage_frame, self._usage_total_label,
                       breakdown_row, self._usage_in_label, self._usage_out_label]:
            widget.bind("<Button-1>", lambda _e: self._show_usage_detail())

    def _build_sidebar(self):
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

        self._chat_list = ctk.CTkScrollableFrame(
            sidebar, fg_color="transparent",
            label_text="HISTORY", label_font=ctk.CTkFont(size=10),
            label_text_color=CLR_SUBTEXT,
        )
        self._chat_list.grid(row=1, column=0, padx=6, pady=(0, 6), sticky="nsew")
        self._chat_list.grid_columnconfigure(0, weight=1)
        enable_scroll(self._chat_list)

        ctk.CTkButton(
            sidebar, text="⚙  Settings", height=36,
            fg_color=CLR_BG_LIGHT, hover_color="#334155",
            text_color=CLR_TEXT, font=ctk.CTkFont(size=12),
            command=self._open_settings,
        ).grid(row=2, column=0, padx=10, pady=10, sticky="ew")

    def _build_main_area(self):
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

        try:
            self._tabs._segmented_button.configure(
                font=ctk.CTkFont(size=14, weight="bold"),
                height=42,
            )
        except Exception:
            pass

        self.after(150, self._wire_tab_colors)
        self._build_chat_tab()
        self._build_log_tab()

    # ── Tab colour theming ────────────────────────────────────────────────────

    def _wire_tab_colors(self):
        """
        Wrap each tab button's original command so switching tabs still works
        AND triggers a colour update.
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
        try:
            btns    = self._tabs._segmented_button._buttons_dict
            current = self._tabs.get()
            for name, btn in btns.items():
                cfg = TAB_COLORS.get(name, {})
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

    # ── Chat tab ──────────────────────────────────────────────────────────────

    def _build_chat_tab(self):
        tab = self._tabs.tab("💬  Chat")
        tab.grid_rowconfigure(0, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        self._messages_frame = ctk.CTkScrollableFrame(tab, fg_color=CLR_BG_DARK)
        self._messages_frame.grid(row=0, column=0, sticky="nsew")
        self._messages_frame.grid_columnconfigure(0, weight=1)
        enable_scroll(self._messages_frame)

        input_row = ctk.CTkFrame(tab, height=90, corner_radius=0, fg_color=CLR_BG_MID)
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

    # ── Message Log tab ───────────────────────────────────────────────────────

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
            font=ctk.CTkFont(size=11), text_color=CLR_SUBTEXT,
        )
        self._log_header_label.grid(row=0, column=0, padx=14, pady=8, sticky="w")

        self._log_frame = ctk.CTkScrollableFrame(tab, fg_color=CLR_BG_DARK)
        self._log_frame.grid(row=1, column=0, sticky="nsew")
        self._log_frame.grid_columnconfigure(0, weight=1)
        enable_scroll(self._log_frame)

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
        enable_scroll(self._log_frame)

    def _clear_log(self):
        for w in self._log_frame.winfo_children():
            w.destroy()

    def _update_log_header(self, chat_id=None):
        if chat_id:
            count = len(self._hist.current_messages)
            self._log_header_label.configure(
                text=f"Chat {chat_id[:8]}…   ·   {count} message{'s' if count != 1 else ''}"
            )
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
            AssistantBubble(
                self._messages_frame,
                content=msg["content"],
                stop_reason=msg.get("stop_reason"),
            ).pack(fill="x", pady=2)
        enable_scroll(self._messages_frame)

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
            messagebox.showwarning(
                "No API Key",
                "Please add your Anthropic API key in ⚙ Settings before chatting.",
            )
            return

        self._input.delete("1.0", "end")
        user_msg = self._hist.add_message("user", text)

        UserBubble(self._messages_frame, content=text).pack(fill="x", pady=2)
        self._add_log_bubble(user_msg)
        self._update_log_header(self._hist.current_chat_id)
        self._refresh_chat_list()

        self._stream_bubble = StreamingBubble(self._messages_frame)
        self._stream_bubble.pack(fill="x", pady=2)
        enable_scroll(self._messages_frame)
        self._scroll_bottom()
        self._scroll_log_bottom()

        self._generating = True
        self._send_btn.configure(state="disabled", text="…")
        threading.Thread(target=self._api_thread, args=(api_key,), daemon=True).start()

    # ── API thread ────────────────────────────────────────────────────────────

    def _api_thread(self, api_key: str):
        model       = self._cfg.get("model", "claude-sonnet-4-6")
        max_tokens  = self._cfg.get("max_tokens", 8096)
        temperature = self._cfg.get("temperature", 1.0)
        system      = self._cfg.get("system_prompt", "")

        messages = [
            {"role": m["role"], "content": m["content"]}
            for m in self._hist.current_messages
        ]

        kwargs: dict = dict(model=model, max_tokens=max_tokens, messages=messages)
        if system:             kwargs["system"]      = system
        if temperature != 1.0: kwargs["temperature"] = temperature

        full_text   = ""
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
            ctk.CTkLabel(
                self._stream_bubble,
                text=f"⚠ Error: {msg}",
                text_color=CLR_RED, wraplength=680, justify="left",
                font=ctk.CTkFont(size=12),
            ).pack(anchor="w", padx=14, pady=(0, 8))
            self._stream_bubble = None
        self._finish_generating()

    def _finish_generating(self):
        self._generating = False
        self._send_btn.configure(state="normal", text="Send")

    def _scroll_bottom(self):
        self.after(200, lambda: self._messages_frame._parent_canvas.yview_moveto(1.0))

    # ── Usage ─────────────────────────────────────────────────────────────────

    def _refresh_usage(self):
        u     = self._hist.get_total_usage()
        ti    = u["input_tokens"]
        to    = u["output_tokens"]
        total = ti + to
        self._usage_total_label.configure(
            text=f"Tokens: {total:,}  |  Cost: ${u['total_cost']:.4f}"
        )
        self._usage_in_label.configure(text=f"↑ {ti:,} in")
        self._usage_out_label.configure(text=f"↓ {to:,} out")

    def _show_usage_detail(self):
        UsageDetailDialog(self, self._hist.get_total_usage())

    def _open_settings(self):
        SettingsDialog(self, self._cfg).wait_window()