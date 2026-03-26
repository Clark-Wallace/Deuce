"""File browser — live DirectoryTree + file preview with syntax highlighting."""

import subprocess
import time
from pathlib import Path
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import DirectoryTree, TextArea, Static


class FileBrowser(Horizontal):
    """Live file browser with preview pane."""

    DOUBLE_CLICK_THRESHOLD = 0.4  # seconds

    def __init__(self, workspace: str = "./workspace", **kwargs) -> None:
        super().__init__(**kwargs)
        self.workspace = workspace
        self.selected_file: Path | None = None
        self._last_click_path: Path | None = None
        self._last_click_time: float = 0

    def compose(self) -> ComposeResult:
        with Vertical(id="file-tree-container"):
            yield Static("Files", id="file-tree-title")
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
            self._open_with_system(path)
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

    @staticmethod
    def _open_with_system(path: Path) -> None:
        """Open a file with the system default application."""
        try:
            subprocess.Popen(["open", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
