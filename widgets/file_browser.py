"""File browser — live DirectoryTree + file preview with syntax highlighting."""

from pathlib import Path
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import DirectoryTree, TextArea, Static


class FileBrowser(Horizontal):
    """Live file browser with preview pane."""

    def __init__(self, workspace: str = "./workspace", **kwargs) -> None:
        super().__init__(**kwargs)
        self.workspace = workspace
        self.selected_file: Path | None = None

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
        """Load selected file into preview pane."""
        path = Path(event.path)
        self.selected_file = path
        title = self.query_one("#file-preview-title", Static)
        preview = self.query_one("#file-preview", TextArea)

        try:
            content = path.read_text(errors="replace")
            title.update(f" {path.name}")

            # Detect language for syntax highlighting
            lang = self._detect_language(path.suffix)
            preview.language = lang
            preview.load_text(content)
        except Exception as e:
            title.update(f" {path.name} (error)")
            preview.load_text(f"Could not read file: {e}")

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
