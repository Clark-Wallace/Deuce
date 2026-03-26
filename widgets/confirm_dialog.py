"""Confirm dialog — modal screen for destructive tool operations."""

import asyncio
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Static, Button


class ConfirmDialog(ModalScreen[bool]):
    """Modal confirmation dialog for destructive operations."""

    CSS = """
    ConfirmDialog {
        align: center middle;
    }

    #confirm-container {
        width: 60;
        height: auto;
        max-height: 16;
        background: $surface;
        border: solid $warning;
        padding: 1 2;
    }

    #confirm-title {
        text-style: bold;
        color: $warning;
        margin-bottom: 1;
    }

    #confirm-detail {
        margin-bottom: 1;
        color: $text;
    }

    #confirm-buttons {
        layout: horizontal;
        height: 3;
        align: center middle;
    }

    #confirm-buttons Button {
        margin: 0 1;
        min-width: 12;
    }
    """

    def __init__(self, tool_name: str, arguments: dict, **kwargs) -> None:
        super().__init__(**kwargs)
        self.tool_name = tool_name
        self.arguments = arguments

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-container"):
            yield Static(f"⚠️  Destructive Operation", id="confirm-title")
            yield Static(
                f"The AI wants to run: {self.tool_name}\n"
                f"Arguments: {self._format_args()}",
                id="confirm-detail",
            )
            with Horizontal(id="confirm-buttons"):
                yield Button("Allow", id="allow-btn", variant="warning")
                yield Button("Deny", id="deny-btn", variant="error")

    def _format_args(self) -> str:
        parts = []
        for k, v in self.arguments.items():
            val = str(v)
            if len(val) > 50:
                val = val[:47] + "..."
            parts.append(f"  {k}: {val}")
        return "\n".join(parts) if parts else "(none)"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "allow-btn")

    def key_y(self) -> None:
        self.dismiss(True)

    def key_n(self) -> None:
        self.dismiss(False)

    def key_escape(self) -> None:
        self.dismiss(False)
