# Claude Chat App

A local desktop interface for the Anthropic Claude API, built with Python and `customtkinter`.

---

## Features

| Feature | Details |
|---|---|
| **Chat window** | Real-time streaming responses from Claude |
| **Markdown rendering** | Full markdown support in all message bubbles — bold, italic, headings, inline code, code blocks with syntax highlighting, tables, and deeply nested elements |
| **Chat history** | Every conversation saved to `~/.claude_chat_app/history/` as JSON; reopenable from the sidebar |
| **Message Log tab** | Diagnostic view of the active chat — color-coded by role, with timestamps, token counts per message, and stop-reason badges |
| **Settings editor** | GUI editor for API key, model, max tokens, temperature, and system prompt |
| **Response indicator** | `✓` (green) = `end_turn`, `⚠` (amber) = any other stop reason — hover to see the exact reason |
| **Token & cost counter** | Top-right shows cumulative tokens used and estimated USD cost; persists across restarts. Click for a per-model breakdown |
| **Dark theme** | Clean, modern dark UI with CSS-matched markdown styling |

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the app

```bash
python main.py
```

### 3. Add your API key

Click **⚙ Settings** in the bottom-left, paste your Anthropic API key, and click **Save Settings**.

---

## Dependencies

| Package | Version | Purpose |
|---|---|---|
| `anthropic` | ≥ 0.34.0 | Anthropic API client with streaming support |
| `customtkinter` | ≥ 5.2.2 | Modern dark-themed UI framework |
| `tkinterweb` | ≥ 3.24.8 | Embedded HTML renderer for markdown display |
| `markdown` | ≥ 3.6 | Converts Claude's markdown responses to HTML |
| `pygments` | ≥ 2.18.0 | Syntax highlighting inside fenced code blocks |

---

## Markdown Support

All message bubbles (in both the Chat tab and the Message Log tab) render full markdown via an HTML engine. Supported elements include:

- **Bold**, *italic*, and combined `**_nested_**` formatting
- `# Headings` at all levels (H1–H6)
- `` `inline code` `` with monospace font
- Fenced code blocks with language-aware syntax highlighting
- Ordered and unordered lists, including nested lists
- **Tables** with proper column alignment
- Blockquotes
- Horizontal rules

---

## File Structure

```
claude_chat_app/
├── main.py              ← UI, app logic, entry point
├── config_manager.py    ← Reads/writes ~/.claude_chat_app/config.json
├── history_manager.py   ← Chat sessions + persistent token tracking
├── requirements.txt
└── README.md
```

### Data stored on disk

```
~/.claude_chat_app/
├── config.json          ← API key, model choice, parameters
├── usage.json           ← Cumulative token counts and cost (never resets)
└── history/
    ├── <uuid>.json      ← One file per chat session
    └── ...
```

---

## Keyboard Shortcuts

| Key | Action |
|---|---|
| `Enter` | Send message |
| `Shift + Enter` | Insert a newline in the input box |

---

## Pricing Reference (as of Feb 2026)

| Model | Input (per M tokens) | Output (per M tokens) |
|---|---|---|
| claude-opus-4-6 | $5.00 | $25.00 |
| claude-sonnet-4-6 | $3.00 | $15.00 |
| claude-haiku-4-5-20251001 | $1.00 | $5.00 |

> Source: Anthropic official pricing, February 2026. Update `MODEL_PRICING` in `history_manager.py` if Anthropic changes pricing.

---

## Requirements

- Python 3.10+
- See `requirements.txt` for all packages