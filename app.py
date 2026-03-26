#!/usr/bin/env python3
"""
Deuce — The governed AI terminal.
One sentence in. Eight files out. Watch it happen.
"""

import asyncio
import sys
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Footer, Static
from textual import work

from widgets.chat_panel import ChatPanel
from widgets.action_ledger import ActionLedger
from widgets.file_browser import FileBrowser
from widgets.confirm_dialog import ConfirmDialog
from widgets.provider_switcher import ProviderSwitcher
from connector import DeuceConnector, PROVIDER_NAMES


class Deuce(App):
    """The governed AI terminal — built on the Nexus SDK."""

    TITLE = "Deuce"
    SUB_TITLE = "The governed AI terminal"
    CSS_PATH = "styles.tcss"

    BINDINGS = [
        ("tab", "focus_next", "Next"),
        ("shift+tab", "focus_previous", "Prev"),
        ("ctrl+o", "open_folder", "Open Folder"),
        ("ctrl+p", "focus_provider", "Provider"),
        ("ctrl+l", "clear_ledger", "Clear Ledger"),
        ("ctrl+n", "new_session", "New Session"),
        ("ctrl+q", "quit", "Quit"),
    ]

    def __init__(self, workspace: str = "./workspace", **kwargs):
        super().__init__(**kwargs)
        self.workspace = workspace
        Path(workspace).mkdir(exist_ok=True)

        self._confirm_future: asyncio.Future | None = None
        self._total_tokens = 0
        self._total_cost = 0.0
        self._files_created: list[str] = []

        self.deuce_connector = DeuceConnector(
            workspace=workspace,
            on_tool_call=self._handle_tool_call,
            on_tool_result=self._handle_tool_result,
            on_step=self._handle_step,
            on_error=self._handle_error,
            on_provider_switch=self._handle_provider_switch,
        )

    def compose(self) -> ComposeResult:
        yield Header()
        # Build provider options from available providers
        available = self.deuce_connector.available_providers
        provider_options = {
            pid: PROVIDER_NAMES.get(pid, pid)
            for pid in available
        }
        yield ProviderSwitcher(
            providers=provider_options,
            current=self.deuce_connector.current_provider,
            id="provider-bar",
        )
        with Horizontal(id="main-container"):
            with Vertical(id="left-column"):
                yield ChatPanel(id="chat-area")
                yield FileBrowser(workspace=self.workspace, id="file-area")
            yield ActionLedger(id="action-ledger")
        yield Footer()

    def on_mount(self) -> None:
        provider = self.deuce_connector.provider_display_name
        chat = self.query_one(ChatPanel)
        chat.add_system_message(f"Provider: {provider}")
        chat.add_system_message(f"Workspace: {self.workspace}")
        chat.add_system_message(f"Type a message to chat, or describe something to build.\n")

        # Focus the chat input
        chat.query_one("#chat-input").focus()

    # ── Message handling ──────────────────────────────────

    def on_chat_panel_message_submitted(self, event: ChatPanel.MessageSubmitted) -> None:
        """User submitted a message — send it to the AI."""
        self._run_message(event.text)

    @work(exclusive=True)
    async def _run_message(self, text: str) -> None:
        """Send message or execute task via Nexus."""
        chat = self.query_one(ChatPanel)
        ledger = self.query_one(ActionLedger)
        chat.set_working(True)

        # Heuristic: if the message looks like a task, use execute_task
        is_task = any(
            kw in text.lower()
            for kw in ["create", "build", "make", "write", "generate", "set up", "implement", "add"]
        )

        try:
            if is_task:
                ledger.log_info(f"Executing task...")
                result = await self.deuce_connector.execute_task(text)

                # Update stats
                self._total_tokens += result.tokens_used
                self._total_cost += result.cost
                self._files_created.extend(result.files_created)

                # Show result in chat
                if result.content:
                    chat.add_ai_message(result.content)

                # Show completion in ledger
                ledger.log_complete(
                    result.files_created,
                    result.tokens_used,
                    result.cost,
                )

                # Refresh file browser
                self._refresh_files()
            else:
                ledger.log_info("Sending message...")
                response = await self.deuce_connector.send_message(text)

                # Update stats
                usage = response.get("usage", {})
                tokens = usage.get("total_tokens", 0)
                self._total_tokens += tokens

                # Show response
                if response.get("content"):
                    chat.add_ai_message(response["content"])

                # If there were tool calls, refresh files
                if response.get("tool_calls"):
                    self._refresh_files()

        except Exception as e:
            chat.add_system_message(f"Error: {e}")
            ledger.log_error(e)
        finally:
            chat.set_working(False)
            self._update_footer()

    # ── Nexus hooks (called from connector) ──────────────

    def _handle_tool_call(self, tc: dict) -> None:
        try:
            ledger = self.query_one(ActionLedger)
            ledger.log_tool_call(tc)
        except Exception:
            pass

    def _handle_tool_result(self, tr: dict) -> None:
        try:
            ledger = self.query_one(ActionLedger)
            ledger.log_tool_result(tr)
            self._refresh_files()
        except Exception:
            pass

    def _handle_step(self, step: int, status: str) -> None:
        try:
            ledger = self.query_one(ActionLedger)
            ledger.log_step(step, status)
        except Exception:
            pass

    def _handle_error(self, error: Exception) -> None:
        try:
            ledger = self.query_one(ActionLedger)
            ledger.log_error(error)
        except Exception:
            pass

    def _handle_provider_switch(self, old: str, new: str, reason: str) -> None:
        try:
            ledger = self.query_one(ActionLedger)
            ledger.log_provider_switch(old, new, reason)
            chat = self.query_one(ChatPanel)
            chat.add_system_message(f"Switched from {old} to {new}: {reason}")
        except Exception:
            pass

    # ── File browser ─────────────────────────────────────

    def _refresh_files(self) -> None:
        try:
            browser = self.query_one(FileBrowser)
            browser.refresh_tree()
        except Exception:
            pass

    # ── Provider switching ────────────────────────────────

    def on_provider_switcher_provider_changed(self, event: ProviderSwitcher.ProviderChanged) -> None:
        """User selected a new provider from the dropdown."""
        provider_id = event.provider_id
        chat = self.query_one(ChatPanel)
        ledger = self.query_one(ActionLedger)

        success = self.deuce_connector.switch_provider(provider_id)
        if success:
            name = PROVIDER_NAMES.get(provider_id, provider_id)
            chat.add_system_message(f"Switched to {name}")
            ledger.log_info(f"Provider → {name}")
            self._update_footer()
        else:
            chat.add_system_message(f"Failed to switch to {provider_id}")

    def action_focus_provider(self) -> None:
        self.query_one("#provider-select").focus()

    # ── Workspace switching ────────────────────────────────

    def action_open_folder(self) -> None:
        """Open native folder picker and switch workspace."""
        self._pick_folder()

    @work(thread=True)
    def _pick_folder(self) -> None:
        """Open native macOS folder picker via osascript."""
        import subprocess
        start_dir = str(Path(self.workspace).resolve())
        script = (
            'set chosenFolder to choose folder with prompt '
            '"Open Workspace" default location POSIX file "' + start_dir + '"\n'
            'return POSIX path of chosenFolder'
        )
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, text=True, timeout=60,
            )
            folder = result.stdout.strip().rstrip("/")
            if result.returncode == 0 and folder:
                self.call_from_thread(self._switch_workspace, folder)
        except Exception:
            pass

    def _switch_workspace(self, folder: str) -> None:
        """Switch everything to the new workspace folder."""
        self.workspace = folder
        Path(folder).mkdir(parents=True, exist_ok=True)

        # Repoint the connector
        from tools import set_workspace
        set_workspace(folder)
        self.deuce_connector.workspace = folder
        self.deuce_connector._connector = None  # rebuild with new context

        # Repoint the file browser
        browser = self.query_one(FileBrowser)
        tree = browser.query_one("#file-tree")
        tree.path = folder
        tree.reload()

        # Reset session stats
        self._total_tokens = 0
        self._total_cost = 0.0
        self._files_created = []

        # Notify user
        chat = self.query_one(ChatPanel)
        ledger = self.query_one(ActionLedger)
        short = self._short_path(folder)
        chat.add_system_message(f"Workspace → {short}")
        ledger.log_info(f"Workspace → {short}")
        self._update_footer()

    @staticmethod
    def _short_path(path: str) -> str:
        """Shorten path for display."""
        home = str(Path.home())
        if path.startswith(home):
            return "~" + path[len(home):]
        return path

    # ── Actions ──────────────────────────────────────────

    def action_clear_ledger(self) -> None:
        ledger = self.query_one("#ledger-log")
        ledger.clear()

    def action_new_session(self) -> None:
        self.deuce_connector.clear_history()
        self._total_tokens = 0
        self._total_cost = 0.0
        self._files_created = []
        chat = self.query_one(ChatPanel)
        chat.add_system_message("Session cleared.")
        self._update_footer()

    # ── Footer stats ─────────────────────────────────────

    def _update_footer(self) -> None:
        provider = self.deuce_connector.provider_display_name
        n_files = len(self._files_created)
        ws = self._short_path(self.workspace)
        self.sub_title = (
            f"{provider} │ {ws} │ {self._total_tokens:,} tokens │ "
            f"${self._total_cost:.4f} │ {n_files} files"
        )


def main():
    workspace = "./workspace"
    if len(sys.argv) > 1:
        workspace = sys.argv[1]

    app = Deuce(workspace=workspace)
    app.run()


if __name__ == "__main__":
    main()
