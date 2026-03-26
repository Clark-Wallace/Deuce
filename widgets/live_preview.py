"""Live preview — shows file content and command output as the AI works."""

from pathlib import Path
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static, RichLog
from rich.syntax import Syntax
from rich.text import Text


class LivePreview(Vertical):
    """Activity pane — shows code being written and command output."""

    def compose(self) -> ComposeResult:
        yield Static("Live Preview", id="preview-title")
        yield RichLog(id="preview-content", markup=True, wrap=True)

    def show_file(self, name: str, content: str) -> None:
        """Display a file's content with syntax highlighting."""
        title = self.query_one("#preview-title", Static)
        log = self.query_one("#preview-content", RichLog)
        title.update(f" ● {name}")
        log.clear()
        lang = self._detect_language(Path(name).suffix)
        if lang:
            log.write(Syntax(content, lang, theme="monokai",
                            line_numbers=True, word_wrap=True))
        else:
            log.write(Text(content))

    def show_output(self, label: str, output: str) -> None:
        """Display command output."""
        title = self.query_one("#preview-title", Static)
        log = self.query_one("#preview-content", RichLog)
        title.update(f" ● {label}")
        log.clear()
        log.write(Text(output))

    def clear(self) -> None:
        """Reset to empty state."""
        title = self.query_one("#preview-title", Static)
        log = self.query_one("#preview-content", RichLog)
        title.update("Live Preview")
        log.clear()

    @staticmethod
    def _detect_language(suffix: str) -> str | None:
        lang_map = {
            ".py": "python", ".js": "javascript", ".ts": "javascript",
            ".json": "json", ".html": "html", ".css": "css",
            ".md": "markdown", ".yaml": "yaml", ".yml": "yaml",
            ".toml": "toml", ".sql": "sql", ".sh": "bash",
            ".bash": "bash", ".rs": "rust", ".go": "go",
            ".rb": "ruby", ".java": "java", ".xml": "xml",
        }
        return lang_map.get(suffix.lower())
