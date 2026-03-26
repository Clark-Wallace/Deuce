"""Chat panel — RichLog for messages + Input for user text."""

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Input, RichLog
from textual.message import Message
from rich.markdown import Markdown
from rich.text import Text


class ChatPanel(Vertical):
    """Chat display with input."""

    class MessageSubmitted(Message):
        """User submitted a message."""
        def __init__(self, text: str) -> None:
            super().__init__()
            self.text = text

    def compose(self) -> ComposeResult:
        yield RichLog(id="chat-log", markup=True, wrap=True)
        yield Input(
            id="chat-input",
            placeholder="Type a message... (Enter to send)",
        )

    def on_mount(self) -> None:
        log = self.query_one("#chat-log", RichLog)
        log.write(Text("Deuce", style="bold"))
        log.write(Text(""))
        log.write(Text("  What do you want to build?", style="bold"))
        log.write(Text(""))
        log.write(Text('  💬  "Build a Flask API with user auth"', style="dim"))
        log.write(Text('  📄  "Create a script that generates an HTML report"', style="dim"))
        log.write(Text('  🔧  "Write a CLI tool that converts CSV to JSON"', style="dim"))
        log.write(Text('  🤖  "Make a Python script that calls the OpenAI API"', style="dim"))
        log.write(Text(""))
        log.write(Text("  Or just type anything.\n", style="dim"))

    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if not text:
            return
        event.input.value = ""
        self.add_user_message(text)
        self.post_message(self.MessageSubmitted(text))

    def add_user_message(self, text: str) -> None:
        log = self.query_one("#chat-log", RichLog)
        log.write(Text(f"\n▶ You", style="bold cyan"))
        log.write(Text(f"  {text}"))

    def add_ai_message(self, text: str) -> None:
        log = self.query_one("#chat-log", RichLog)
        log.write(Text(f"\n◀ AI", style="bold green"))
        try:
            log.write(Markdown(text))
        except Exception:
            log.write(Text(f"  {text}"))

    def add_system_message(self, text: str) -> None:
        log = self.query_one("#chat-log", RichLog)
        log.write(Text(f"  {text}", style="dim italic"))

    def set_working(self, working: bool) -> None:
        input_widget = self.query_one("#chat-input", Input)
        if working:
            input_widget.placeholder = "AI is working..."
            input_widget.disabled = True
        else:
            input_widget.placeholder = "Type a message... (Enter to send)"
            input_widget.disabled = False
            input_widget.focus()
