#!/usr/bin/env python3
"""
Deuce — The governed AI terminal.
One sentence in. Eight files out. Watch it happen.
"""

import asyncio
import json
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
from widgets.live_preview import LivePreview
from widgets.split_bar import SplitBar
from connector import DeuceConnector

# Config file stores persistent settings (last workspace, etc.)
CONFIG_PATH = Path.home() / ".deuce" / "config.json"


def _load_config() -> dict:
    """Load persistent config from ~/.deuce/config.json."""
    try:
        if CONFIG_PATH.exists():
            return json.loads(CONFIG_PATH.read_text())
    except Exception:
        pass
    return {}


def _save_config(config: dict) -> None:
    """Save persistent config to ~/.deuce/config.json."""
    try:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(json.dumps(config, indent=2))
    except Exception:
        pass


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
        ("ctrl+c", "cancel_task", "Cancel"),
        ("ctrl+l", "clear_ledger", "Clear Ledger"),
        ("ctrl+n", "new_session", "New Session"),
        ("ctrl+q", "quit", "Quit"),
    ]

    def __init__(self, workspace: str = "./workspace", **kwargs):
        super().__init__(**kwargs)
        self.workspace = workspace
        Path(workspace).mkdir(exist_ok=True)

        self._confirm_future: asyncio.Future | None = None
        self._current_worker = None
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
        # Build provider options from discovered providers
        provider_options = {
            pid: cfg.name
            for pid, cfg in self.deuce_connector.providers.items()
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
            with Vertical(id="right-column"):
                yield ActionLedger(id="action-ledger")
                yield SplitBar(id="ledger-split")
                yield LivePreview(id="live-preview")
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
        self._current_worker = self._run_message(event.text)

    @work(exclusive=True)
    async def _run_message(self, text: str) -> None:
        """Deuce's agent loop — uses send_message, not execute_task.

        Each turn updates the UI immediately. The AI calls tools until
        it responds with text and no tool calls. No synthetic prompts.
        No iteration counting. The model decides when it's done.
        """
        chat = self.query_one(ChatPanel)
        ledger = self.query_one(ActionLedger)
        chat.set_working(True)
        ledger.log_task_received(text)

        total_tokens = 0
        files_created = []
        tool_call_count = 0

        try:
            async for turn, response in self.deuce_connector.agent_loop(text):
                content = response.get("content", "")
                tool_calls = response.get("tool_calls", [])
                tool_results = response.get("tool_results", [])
                usage = response.get("usage", {})

                # Track stats
                total_tokens += usage.get("total_tokens", 0)
                tool_call_count += len(tool_calls) if tool_calls else 0

                # Show AI text in chat as it arrives — each turn, not at the end
                if content:
                    chat.add_ai_message(content)

                # Track created files from tool results
                for tr in (tool_results or []):
                    result = tr.get("result", {})
                    if isinstance(result, dict) and result.get("path"):
                        files_created.append(result["path"])

                # Refresh file browser after tool use
                if tool_calls or tool_results:
                    self._refresh_files()

            # Update totals
            self._total_tokens += total_tokens
            self._files_created.extend(files_created)

            # Estimate cost (rough: $3 per 1M tokens for most providers)
            cost = total_tokens * 0.000003
            self._total_cost += cost

            # Show completion in ledger if work was done
            if tool_call_count > 0:
                ledger.log_complete(files_created, total_tokens, cost)

        except Exception as e:
            chat.add_system_message(f"Error: {e}")
            ledger.log_error(e)
        finally:
            chat.set_working(False)
            self._update_footer()

    # ── Nexus hooks (called during execute_task) ────────

    def _handle_tool_call(self, tc: dict) -> None:
        try:
            self.query_one(ActionLedger).log_tool_call(tc)
        except Exception:
            pass
        try:
            name = tc.get("name", "")
            args = tc.get("arguments", {})
            if name in ("create_file", "write_file", "edit_file"):
                content = args.get("content", "")
                path = args.get("path", args.get("filename", ""))
                if content and path:
                    self.query_one(LivePreview).show_file(path, content)
            elif name == "execute_command":
                cmd = args.get("command", "")
                if cmd:
                    self.query_one(LivePreview).show_file(
                        "$ " + cmd, f"Running: {cmd}\n\nWaiting for output..."
                    )
        except Exception:
            pass

    def _handle_tool_result(self, tr: dict) -> None:
        try:
            self.query_one(ActionLedger).log_tool_result(tr)
            self._refresh_files()
        except Exception:
            pass
        try:
            name = tr.get("name", "")
            result = tr.get("result", {})
            if name == "execute_command" and isinstance(result, dict):
                output = result.get("output", result.get("stdout", ""))
                if output:
                    self.query_one(LivePreview).show_output("Output", str(output))
        except Exception:
            pass

    def _handle_step(self, step: int, status: str) -> None:
        pass  # Agent loop doesn't use steps

    def _handle_error(self, error: Exception) -> None:
        try:
            self.query_one(ActionLedger).log_error(error)
        except Exception:
            pass

    def _handle_provider_switch(self, old: str, new: str, reason: str) -> None:
        try:
            self.query_one(ActionLedger).log_provider_switch(old, new, reason)
            self.query_one(ChatPanel).add_system_message(
                f"Switched from {old} to {new}: {reason}"
            )
        except Exception:
            pass

    # ── File browser ─────────────────────────────────────

    def _refresh_files(self) -> None:
        try:
            browser = self.query_one(FileBrowser)
            browser.refresh_tree()
        except Exception:
            pass

    # ── Workspace navigation (from file browser) ──────────

    def on_file_browser_workspace_changed(self, event: FileBrowser.WorkspaceChanged) -> None:
        """User double-clicked a folder or navigated up in the file browser."""
        self._switch_workspace(event.path)

    # ── Provider switching ────────────────────────────────

    def on_provider_switcher_provider_changed(self, event: ProviderSwitcher.ProviderChanged) -> None:
        """User selected a new provider from the dropdown."""
        provider_id = event.provider_id
        chat = self.query_one(ChatPanel)
        ledger = self.query_one(ActionLedger)

        success = self.deuce_connector.switch_provider(provider_id)
        if success:
            name = self.deuce_connector.provider_display_name
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

        # Persist the workspace choice
        config = _load_config()
        config["workspace"] = folder
        _save_config(config)

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

    def action_cancel_task(self) -> None:
        """Cancel the currently running task."""
        if self._current_worker and self._current_worker.is_running:
            self._current_worker.cancel()
            self._current_worker = None
            chat = self.query_one(ChatPanel)
            ledger = self.query_one(ActionLedger)
            chat.set_working(False)
            chat.add_system_message("Task cancelled.")
            ledger.log_info("Task cancelled by user.")
            # Clear conversation history to avoid corrupted state
            self.deuce_connector.clear_history()

    def action_clear_ledger(self) -> None:
        self.query_one(ActionLedger).clear()

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
    # Priority: CLI arg > saved config > default
    if len(sys.argv) > 1:
        workspace = sys.argv[1]
    else:
        config = _load_config()
        workspace = config.get("workspace", "./workspace")

    app = Deuce(workspace=workspace)
    app.run()


if __name__ == "__main__":
    main()
