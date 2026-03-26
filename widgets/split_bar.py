"""Split bar — draggable divider between two panels."""

from textual.widgets import Static
from textual import events


class SplitBar(Static):
    """Horizontal draggable bar to resize the panels above and below it."""

    DEFAULT_CSS = """
    SplitBar {
        height: 1;
        background: #2a3542;
        color: #535d68;
        content-align: center middle;
    }
    SplitBar:hover {
        background: #3a4552;
        color: #8b949e;
    }
    SplitBar.-dragging {
        background: #3a4552;
        color: #8b949e;
    }
    """

    def __init__(self, **kwargs):
        super().__init__("━━━━━━━━━━━━ ◆ ━━━━━━━━━━━━", **kwargs)
        self._dragging = False
        self._drag_start_y = 0
        self._start_above = 0
        self._start_below = 0
        self._above = None
        self._below = None

    def on_mouse_down(self, event: events.MouseDown) -> None:
        parent = self.parent
        if not parent:
            return
        children = list(parent.children)
        try:
            idx = children.index(self)
        except ValueError:
            return
        if idx == 0 or idx >= len(children) - 1:
            return

        self._above = children[idx - 1]
        self._below = children[idx + 1]
        self._drag_start_y = event.screen_y
        self._start_above = self._above.size.height
        self._start_below = self._below.size.height
        self._dragging = True
        self.capture_mouse()
        self.add_class("-dragging")
        event.stop()

    def on_mouse_up(self, event: events.MouseUp) -> None:
        if self._dragging:
            self._dragging = False
            self.release_mouse()
            self.remove_class("-dragging")
            self._above = None
            self._below = None
            event.stop()

    def on_mouse_move(self, event: events.MouseMove) -> None:
        if not self._dragging or not self._above or not self._below:
            return

        delta = event.screen_y - self._drag_start_y
        total = self._start_above + self._start_below
        min_size = 3

        new_above = max(min_size, min(total - min_size, self._start_above + delta))
        new_below = total - new_above

        self._above.styles.height = new_above
        self._below.styles.height = new_below
        event.stop()
