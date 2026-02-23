"""
widgets/markdown_frame.py — Markdown-to-HTML rendering widget.

MarkdownFrame wraps tkinterweb.HtmlFrame and converts markdown text to a
styled HTML document using a dark CSS theme. Height is estimated from
content length so the bubble sizes itself without querying tkinterweb
internals (which vary by version).
"""

import tkinter as tk

import markdown as md_lib
from tkinterweb import HtmlFrame

from theme import CLR_TEXT, CLR_SUBTEXT

# ── Markdown extensions ───────────────────────────────────────────────────────
_MD_EXTENSIONS = [
    "tables",
    "fenced_code",
    "codehilite",
    "nl2br",
    "sane_lists",
    "attr_list",
]
_MD_EXT_CONFIGS = {
    "codehilite": {"css_class": "highlight", "guess_lang": True},
}


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
    h3 {{ font-size: 1.1em; }}
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
    ul, ol {{ margin: 6px 0 6px 22px; padding: 0; }}
    li {{ margin: 3px 0; }}
    ul ul, ol ol, ul ol, ol ul {{ margin-top: 3px; margin-bottom: 3px; }}
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
    hr {{ border: none; border-top: 1px solid #334155; margin: 12px 0; }}
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
    """Convert markdown text to a complete dark-themed HTML document."""
    body = md_lib.markdown(
        text,
        extensions=_MD_EXTENSIONS,
        extension_configs=_MD_EXT_CONFIGS,
    )
    return f"<html><head>{_make_css(bg)}</head><body>{body}</body></html>"


class MarkdownFrame(tk.Frame):
    """
    A tkinterweb HtmlFrame that renders markdown as styled HTML.
    Height is estimated from content length; no tkinterweb internals queried.
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
        self._html_frame.load_html(render_html(text, self._bg))
        self.after(150, self._adjust_height)

    def _adjust_height(self):
        line_count  = self._text.count("\n") + 1
        char_lines  = len(self._text) // 80
        code_blocks = self._text.count("```") // 2
        table_rows  = self._text.count("\n|")
        estimated   = (
            max(line_count, char_lines) * 20
            + code_blocks * 28
            + table_rows  * 22
            + 24
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
