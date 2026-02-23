"""
widgets/dialogs.py — Modal dialogs and the Tooltip helper.

Tooltip           — hover tooltip for any widget
SettingsDialog    — edit API key, model, parameters, system prompt
UsageDetailDialog — cumulative token and cost breakdown popup
"""

import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from config_manager import AVAILABLE_MODELS, ConfigManager
from history_manager import MODEL_PRICING
from theme import (
    CLR_ACCENT, CLR_ACCENT_HV, CLR_BG_LIGHT, CLR_BG_MID,
    CLR_SUBTEXT, CLR_TEXT,
)


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
        tk.Label(
            tw, text=self._text,
            background="#1e293b", foreground="#e2e8f0",
            relief="solid", borderwidth=1, padx=8, pady=4,
            font=("Segoe UI", 10),
        ).pack()

    def _hide(self, _event=None):
        if self._win:
            self._win.destroy()
            self._win = None


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
            ctk.CTkLabel(
                scroll, text=text, anchor="w",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=CLR_SUBTEXT,
            ).pack(fill="x", pady=(16, 3))

        def row_entry(label, var, show=""):
            ctk.CTkLabel(
                scroll, text=label, anchor="w",
                font=ctk.CTkFont(size=13), text_color=CLR_TEXT,
            ).pack(fill="x", pady=(6, 2))
            return ctk.CTkEntry(
                scroll, textvariable=var, show=show,
                fg_color=CLR_BG_LIGHT, border_color="#334155",
                text_color=CLR_TEXT, height=36,
            )

        # API key
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

        vis_btn = ctk.CTkButton(
            scroll, text="Show", width=70, height=28,
            fg_color=CLR_BG_LIGHT, hover_color="#334155",
            text_color=CLR_SUBTEXT, command=toggle,
        )
        vis_btn.pack(anchor="e", pady=(3, 0))

        # Model
        section("MODEL")
        ctk.CTkLabel(
            scroll, text="Model", anchor="w",
            font=ctk.CTkFont(size=13), text_color=CLR_TEXT,
        ).pack(fill="x", pady=(6, 2))
        self._model_var = tk.StringVar(value=self._cfg.get("model", AVAILABLE_MODELS[1]))
        ctk.CTkOptionMenu(
            scroll, variable=self._model_var, values=AVAILABLE_MODELS,
            fg_color=CLR_BG_LIGHT, button_color=CLR_ACCENT,
            button_hover_color=CLR_ACCENT_HV, dropdown_fg_color=CLR_BG_LIGHT,
            text_color=CLR_TEXT, height=36,
        ).pack(fill="x")

        def _pricing_text(_=None):
            p = MODEL_PRICING.get(self._model_var.get(), {"input": "?", "output": "?"})
            return f"${p['input']}/M input · ${p['output']}/M output"

        self._pricing_label = ctk.CTkLabel(
            scroll, text=_pricing_text(),
            font=ctk.CTkFont(size=11), text_color=CLR_SUBTEXT, anchor="w",
        )
        self._pricing_label.pack(fill="x", pady=(2, 0))
        self._model_var.trace_add(
            "write",
            lambda *_: self._pricing_label.configure(text=_pricing_text()),
        )

        # Parameters
        section("PARAMETERS")
        self._max_tokens_var = tk.StringVar(value=str(self._cfg.get("max_tokens", 8096)))
        row_entry("Max Tokens", self._max_tokens_var).pack(fill="x")
        self._temp_var = tk.StringVar(value=str(self._cfg.get("temperature", 1.0)))
        row_entry("Temperature  (0.0 – 1.0)", self._temp_var).pack(fill="x")

        # System prompt
        section("SYSTEM PROMPT")
        self._sys_box = ctk.CTkTextbox(
            scroll, height=110, wrap="word",
            fg_color=CLR_BG_LIGHT, border_color="#334155",
            text_color=CLR_TEXT, font=ctk.CTkFont(size=12),
        )
        self._sys_box.pack(fill="x", pady=(3, 0))
        self._sys_box.insert("1.0", self._cfg.get("system_prompt", ""))

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


# ── Usage detail dialog ───────────────────────────────────────────────────────
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

        ctk.CTkLabel(
            frame, text="Cumulative API Usage",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=CLR_TEXT,
        ).pack(anchor="w", pady=(0, 12))

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
            ctk.CTkLabel(
                frame, text="— Per Model —",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=CLR_SUBTEXT,
            ).pack(pady=(16, 6))
            for model, stats in by_model.items():
                ctk.CTkLabel(
                    frame, text=model,
                    text_color=CLR_ACCENT,
                    font=ctk.CTkFont(size=12),
                ).pack(anchor="w", pady=(6, 2))
                row("  Input",  f"{stats['input_tokens']:,}")
                row("  Output", f"{stats['output_tokens']:,}")
                row("  Cost",   f"${stats['cost']:.4f}")

        ctk.CTkButton(
            frame, text="Close",
            fg_color=CLR_BG_LIGHT, hover_color="#334155",
            text_color=CLR_TEXT, command=self.destroy,
        ).pack(pady=(20, 0))
