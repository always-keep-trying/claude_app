# Claude Chat App

A local desktop interface for the Anthropic Claude API, built with Python and `customtkinter`.

---

## Features

| Feature | Details |
|---|---|
| **Chat window** | Real-time streaming responses from Claude |
| **Chat history** | Every conversation is saved to `~/.claude_chat_app/history/` as JSON, and can be reopened |
| **Settings editor** | GUI editor for API key, model, max tokens, temperature, and system prompt |
| **Response indicator** | `✓` (green) = `end_turn`, `⚠` (amber) = any other stop reason — hover to see the exact reason |
| **Token & cost counter** | Top-right shows cumulative tokens used and estimated USD cost; persists across restarts. Click it for a per-model breakdown |
| **Dark theme** | Clean, modern dark UI |

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
| claude-opus-4-6 | $15.00 | $75.00 |
| claude-sonnet-4-6 | $3.00 | $15.00 |
| claude-haiku-4-5-20251001 | $0.80 | $4.00 |

> Update `MODEL_PRICING` in `history_manager.py` if Anthropic changes pricing.

---

## Requirements

- `Python 3.10+`
- `anthropic >= 0.34.0`
- `customtkinter >= 5.2.2`
