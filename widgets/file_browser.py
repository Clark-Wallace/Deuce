"""File browser — live DirectoryTree + file preview with syntax highlighting."""

import subprocess
import time
from pathlib import Path
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import DirectoryTree, TextArea, Static, Button
from textual.message import Message


class FileBrowser(Horizontal):
    """Live file browser with preview pane."""

    DOUBLE_CLICK_THRESHOLD = 0.4  # seconds

    class WorkspaceChanged(Message):
        """User navigated to a new workspace directory."""
        def __init__(self, path: str) -> None:
            super().__init__()
            self.path = path

    def __init__(self, workspace: str = "./workspace", **kwargs) -> None:
        super().__init__(**kwargs)
        self.workspace = workspace
        self.selected_file: Path | None = None
        self._last_click_path: Path | None = None
        self._last_click_time: float = 0
        self._last_dir_path: Path | None = None
        self._last_dir_time: float = 0

    def compose(self) -> ComposeResult:
        with Vertical(id="file-tree-container"):
            with Horizontal(id="file-nav-bar"):
                yield Button("↑ ..", id="nav-up", variant="default")
                yield Static(self._short_path(self.workspace), id="nav-path")
            yield DirectoryTree(self.workspace, id="file-tree")
        with Vertical(id="file-preview-container"):
            yield Static("Preview", id="file-preview-title")
            yield TextArea.code_editor(
                "",
                id="file-preview",
                read_only=True,
                show_line_numbers=True,
                soft_wrap=True,
            )

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        """Single click: preview. Double click: open with system default."""
        path = Path(event.path)
        now = time.time()

        # Double-click detection: same file clicked within threshold
        if (self._last_click_path == path
                and (now - self._last_click_time) < self.DOUBLE_CLICK_THRESHOLD):
            suffix = path.suffix.lower()
            if suffix in self._RUN_IN_TERMINAL:
                self._run_in_terminal(path)
            elif suffix in self._OPEN_WITH_SYSTEM:
                self._open_with_system(path)
            else:
                self._open_with_system(path)  # fallback
            self._last_click_path = None
            self._last_click_time = 0
            return

        self._last_click_path = path
        self._last_click_time = now
        self.selected_file = path

        # Single click: show in preview
        title = self.query_one("#file-preview-title", Static)
        preview = self.query_one("#file-preview", TextArea)

        try:
            content = path.read_text(errors="replace")
            title.update(f" {path.name}")
            lang = self._detect_language(path.suffix)
            preview.language = lang
            preview.load_text(content)
        except Exception as e:
            title.update(f" {path.name} (error)")
            preview.load_text(f"Could not read file: {e}")

    def on_directory_tree_directory_selected(self, event) -> None:
        """Double-click a folder to navigate into it as the new workspace."""
        path = Path(event.path)
        now = time.time()

        if (self._last_dir_path == path
                and (now - self._last_dir_time) < self.DOUBLE_CLICK_THRESHOLD):
            self._navigate_to(path)
            self._last_dir_path = None
            self._last_dir_time = 0
            return

        self._last_dir_path = path
        self._last_dir_time = now

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle nav-up button."""
        if event.button.id == "nav-up":
            parent = Path(self.workspace).resolve().parent
            self._navigate_to(parent)

    def _navigate_to(self, path: Path) -> None:
        """Switch the workspace to a new directory."""
        resolved = str(path.resolve())
        self.workspace = resolved

        # Update the tree
        tree = self.query_one("#file-tree", DirectoryTree)
        tree.path = resolved
        tree.reload()

        # Update the nav path display
        self.query_one("#nav-path", Static).update(self._short_path(resolved))

        # Notify the app so it can update the connector and config
        self.post_message(self.WorkspaceChanged(resolved))

    @staticmethod
    def _short_path(path: str) -> str:
        home = str(Path.home())
        if path.startswith(home):
            return "~" + path[len(home):]
        return path

    # Files that should be run in a new Terminal window on double-click
    _RUN_IN_TERMINAL = {
        ".py": "python3",
        ".sh": "bash",
        ".rb": "ruby",
        ".js": "node",
    }

    # Files that open with system default (browser, editor, etc.)
    _OPEN_WITH_SYSTEM = {".html", ".htm", ".pdf", ".png", ".jpg", ".jpeg", ".gif", ".svg"}

    @staticmethod
    def _open_with_system(path: Path) -> None:
        """Open a file with the system default application."""
        try:
            subprocess.Popen(["open", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    @classmethod
    def _run_in_terminal(cls, path: Path) -> None:
        """Run a script in a new Terminal.app window."""
        runner = cls._RUN_IN_TERMINAL.get(path.suffix.lower())
        if not runner:
            return
        # Build the shell command — use the absolute path to avoid quoting issues
        abs_path = str(path.resolve())
        parent = str(path.parent.resolve())
        shell_cmd = f"cd '{parent}' && {runner} '{abs_path}'"
        try:
            subprocess.Popen([
                "osascript", "-e",
                f'tell application "Terminal" to do script "{shell_cmd}"',
                "-e",
                'tell application "Terminal" to activate',
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    def refresh_tree(self) -> None:
        """Reload the directory tree."""
        tree = self.query_one("#file-tree", DirectoryTree)
        tree.reload()

    @staticmethod
    def _detect_language(suffix: str) -> str | None:
        lang_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "javascript",
            ".json": "json",
            ".html": "html",
            ".css": "css",
            ".md": "markdown",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".toml": "toml",
            ".sql": "sql",
            ".sh": "bash",
            ".bash": "bash",
            ".rs": "rust",
            ".go": "go",
            ".rb": "ruby",
            ".java": "java",
            ".xml": "xml",
            ".txt": None,
        }
        return lang_map.get(suffix.lower())
