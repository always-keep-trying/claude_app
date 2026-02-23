"""
main.py — Entry point for Claude Chat App.

Usage:
    pip install -r requirements.txt
    python main.py
"""

import scroll  # applies the customtkinter/tkinterweb patch at import time  # noqa: F401
from app import ChatApp


def main():
    ChatApp().mainloop()


if __name__ == "__main__":
    main()
