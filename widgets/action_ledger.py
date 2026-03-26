"""Action ledger — real-time log of every tool call the AI makes."""

from datetime import datetime
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Log, Static


class ActionLedger(Vertical):
    """Real-time action log showing tool calls, results, and events."""

    def compose(self) -> ComposeResult:
        yield Static("Action Ledger", id="action-ledger-title")
        yield Log(id="ledger-log", auto_scroll=True)

    def _ts(self) -> str:
        return datetime.now().strftime("%H:%M:%S")

    def log_tool_call(self, tool_call: dict) -> None:
        log = self.query_one("#ledger-log", Log)
        name = tool_call.get("name", "?")
        args = tool_call.get("arguments", {})

        if name in ("create_file", "write_file"):
            detail = args.get("path", args.get("filename", "?"))
            log.write_line(f"{self._ts()} 🔧 {name}: {detail}")
        elif name == "execute_command":
            cmd = args.get("command", "?")
            display = cmd if len(cmd) < 40 else cmd[:37] + "..."
            log.write_line(f"{self._ts()} 🔧 run: {display}")
        elif name == "edit_file":
            detail = args.get("path", args.get("filename", "?"))
            log.write_line(f"{self._ts()} 🔧 edit: {detail}")
        elif name in ("read_file", "search_files", "list_files"):
            detail = args.get("path", args.get("pattern", args.get("directory", "?")))
            log.write_line(f"{self._ts()} 🔧 {name}: {detail}")
        elif name == "delete_file":
            detail = args.get("path", "?")
            log.write_line(f"{self._ts()} 🔧 delete: {detail}")
        else:
            keys = ", ".join(args.keys()) if args else ""
            log.write_line(f"{self._ts()} 🔧 {name}({keys})")

    def log_tool_result(self, tool_result: dict) -> None:
        log = self.query_one("#ledger-log", Log)
        name = tool_result.get("name", "?")
        result = tool_result.get("result", {})

        if isinstance(result, dict) and result.get("success") is False:
            error = result.get("error", "failed")
            display = error if len(error) < 50 else error[:47] + "..."
            log.write_line(f"         ❌ {display}")
        else:
            log.write_line(f"         ✅ done")

    def log_step(self, step: int, status: str) -> None:
        log = self.query_one("#ledger-log", Log)
        log.write_line(f"{self._ts()} 📍 step {step}: {status}")

    def log_error(self, error: Exception) -> None:
        log = self.query_one("#ledger-log", Log)
        msg = str(error)
        display = msg if len(msg) < 60 else msg[:57] + "..."
        log.write_line(f"{self._ts()} ❌ {display}")

    def log_provider_switch(self, old: str, new: str, reason: str) -> None:
        log = self.query_one("#ledger-log", Log)
        log.write_line(f"{self._ts()} 🔄 {old} → {new}: {reason}")

    def log_info(self, text: str) -> None:
        log = self.query_one("#ledger-log", Log)
        log.write_line(f"{self._ts()} ℹ️  {text}")

    def log_complete(self, files_created: list, tokens: int, cost: float) -> None:
        log = self.query_one("#ledger-log", Log)
        log.write_line(f"")
        log.write_line(f"  ✅ Task complete")
        if files_created:
            log.write_line(f"     {len(files_created)} files created")
        log.write_line(f"     {tokens:,} tokens, ${cost:.4f}")
