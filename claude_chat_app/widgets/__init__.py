"""
widgets — UI component package for Claude Chat App.
"""

from widgets.markdown_frame import MarkdownFrame, render_html
from widgets.bubbles import (
    UserBubble,
    AssistantBubble,
    StreamingBubble,
    LogBubble,
    add_stop_indicator,
)
from widgets.dialogs import Tooltip, SettingsDialog, UsageDetailDialog

__all__ = [
    "MarkdownFrame",
    "render_html",
    "UserBubble",
    "AssistantBubble",
    "StreamingBubble",
    "LogBubble",
    "add_stop_indicator",
    "Tooltip",
    "SettingsDialog",
    "UsageDetailDialog",
]
