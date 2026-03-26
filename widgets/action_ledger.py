"""Action ledger — ship's log of every tool call the AI makes.

Visual reference: deuce_anvil_ships_log_ledger.html
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from textual.app import ComposeResult
from textual.containers import Vertical, ScrollableContainer
from textual.widgets import Static


# ── Design tokens (from HTML reference) ───────────────────

C = {
    "bg_panel":    "#141b22",
    "bg_entry":    "#1a232d",
    "border":      "#2a3542",
    "border_dim":  "#1e2833",
    "text":        "#c9d1d9",
    "text_sec":    "#8b949e",
    "text_dim":    "#535d68",
    "text_bright": "#e6edf3",
    "create":      "#3fb950",
    "create_dim":  "#1a3a2a",
    "fail":        "#f85149",
    "fail_dim":    "#3d1a1a",
    "patch":       "#d29922",
    "patch_dim":   "#3a2e14",
    "info":        "#58a6ff",
    "info_dim":    "#1a2a3d",
    "command":     "#8b949e",
}

# Commands that indicate test/verification
VERIFY_HINTS = {"test", "pytest", "unittest", "jest", "mocha", "spec", "check", "verify", "npm test"}

# Commands that are clearly not verification
RUN_HINTS = {"mkdir", "pip", "npm install", "yarn", "cd ", "ls", "cat ", "echo ", "touch ", "chmod"}


# ── Data model ────────────────────────────────────────────

@dataclass
class LedgerEntry:
    entry_type: str          # create, verify, fail, patch, run, info
    timestamp: str           # HH:MM:SS
    tag: str                 # CREATE, VERIFY, PATCH, RUN, or "" for narrative
    label: str               # filename, command, or narrative text
    detail: str = ""         # subordinate info
    success: Optional[bool] = None

    @classmethod
    def from_tool_call(cls, tool_call: dict, last_failed: bool = False) -> "LedgerEntry":
        name = tool_call.get("name", "?")
        args = tool_call.get("arguments", {})
        ts = datetime.now().strftime("%H:%M:%S")

        # File creation
        if name in ("create_file", "write_file"):
            path = args.get("path", args.get("filename", "?"))
            content = args.get("content", "")
            lines = len(content.splitlines()) if content else 0
            detail = f"{lines} lines" if lines else ""
            return cls("create", ts, "CREATE", path, detail)

        # File edit — PATCH if previous tool failed, otherwise CREATE
        if name == "edit_file":
            path = args.get("path", args.get("filename", "?"))
            if last_failed:
                return cls("patch", ts, "PATCH", path)
            return cls("create", ts, "EDIT", path)

        # Command execution — classify as VERIFY or RUN
        if name == "execute_command":
            cmd = args.get("command", "?")
            display = cmd if len(cmd) < 55 else cmd[:52] + "..."
            # Check run hints first (more specific)
            if any(hint in cmd.lower() for hint in RUN_HINTS):
                return cls("run", ts, "RUN", display)
            # Then check verify hints
            if any(hint in cmd.lower() for hint in VERIFY_HINTS):
                return cls("verify", ts, "VERIFY", display)
            return cls("run", ts, "RUN", display)

        # File operations
        if name in ("read_file", "search_files", "list_files"):
            target = args.get("path", args.get("pattern", args.get("directory", "?")))
            return cls("info", ts, "", f"{name}: {target}")

        if name == "delete_file":
            return cls("run", ts, "RUN", f"delete {args.get('path', '?')}")

        # Custom tools
        keys = ", ".join(args.keys()) if args else ""
        return cls("run", ts, "RUN", f"{name}({keys})")

    def update_from_result(self, tool_result: dict) -> None:
        """Update entry with tool execution result."""
        result = tool_result.get("result", {})
        if isinstance(result, dict) and result.get("success") is False:
            self.success = False
            error = result.get("error", "failed")
            self.detail = error if len(error) < 80 else error[:77] + "..."
            if self.entry_type == "verify":
                self.entry_type = "fail"
                self.tag = "VERIFY"  # keep tag as VERIFY, type controls color
        else:
            self.success = True
            if isinstance(result, dict) and "output" in result:
                out = str(result["output"]).strip()
                if out and self.entry_type in ("verify", "run"):
                    self.detail = out if len(out) < 80 else out[:77] + "..."


# ── Rendering ─────────────────────────────────────────────

def _border(entry_type: str) -> str:
    """Get the border color for an entry type."""
    mapping = {
        "create": C["create"], "pass": C["create"],
        "fail": C["fail"], "patch": C["patch"],
        "info": C["info"], "verify": C["create"],
        "run": C["command"],
    }
    return mapping.get(entry_type, C["command"])


def _tag_markup(tag: str, entry_type: str, success: Optional[bool] = None) -> str:
    """Render a colored tag badge like the HTML reference."""
    if not tag:
        return ""
    colors = {
        "CREATE": (C["create"], C["create_dim"]),
        "EDIT":   (C["create"], C["create_dim"]),
        "VERIFY": (C["create"], C["create_dim"]),
        "PATCH":  (C["patch"],  C["patch_dim"]),
        "RUN":    (C["command"], C["bg_entry"]),
    }
    # Override for failures
    if success is False or entry_type == "fail":
        fg, bg = C["fail"], C["fail_dim"]
    else:
        fg, bg = colors.get(tag, (C["command"], C["bg_entry"]))
    return f"[{fg} on {bg}] {tag} [/]"


def _label_markup(entry: LedgerEntry) -> str:
    """Render the label — bright for filenames, code-style for commands."""
    if entry.tag in ("RUN", "VERIFY"):
        return f"[{C['text_sec']} on {C['bg_entry']}] {entry.label} [/]"
    else:
        return f"[bold {C['text_bright']}]{entry.label}[/]"


def _detail_markup(entry: LedgerEntry) -> str:
    """Render detail text with appropriate color."""
    if not entry.detail:
        return ""
    if entry.success is False:
        return f"[bold {C['fail']}]{entry.detail}[/]"
    if entry.success is True and entry.entry_type in ("verify", "pass"):
        return f"[{C['create']}]{entry.detail}[/]"
    return f"[{C['text_dim']}]{entry.detail}[/]"


def render_task_header(timestamp: str, task_text: str) -> str:
    """Render the TASK RECEIVED block."""
    return (
        f"[{C['text_dim']}]{timestamp}[/]  "
        f"[{C['info']}]●[/]  "
        f"[bold {C['info']}]TASK RECEIVED[/]\n"
        f"         [{C['text_sec']} italic]\"{task_text}\"[/]"
    )


def render_group(entries: list[LedgerEntry]) -> str:
    """Render a group of related entries with colored border."""
    if not entries:
        return ""

    # Determine group color from entries
    border = _border(entries[0].entry_type)
    if any(e.success is False for e in entries):
        border = C["fail"]
    elif any(e.entry_type == "patch" for e in entries):
        border = C["patch"]
    elif any(e.success is True and e.entry_type == "verify" for e in entries):
        border = C["create"]  # green for passing tests

    lines = []
    for entry in entries:
        # Timestamp + tag + label
        ts = f"[{C['text_dim']}]{entry.timestamp}[/]"
        tag = _tag_markup(entry.tag, entry.type if hasattr(entry, 'type') else entry.entry_type, entry.success)
        label = _label_markup(entry)
        lines.append(f"[{border}]▎[/] {ts}  {tag}  {label}")

        # Detail line (indented)
        detail = _detail_markup(entry)
        if detail:
            lines.append(f"[{border}]▎[/]            {detail}")

    return "\n".join(lines)


def render_narrative(timestamp: str, text: str) -> str:
    """Render a narrative entry (assessment, status, transition)."""
    return f"[{C['text_dim']}]{timestamp}[/]  [{C['text_sec']}]{text}[/]"


def render_complete(files: list, tokens: int, cost: float, tool_calls: int = 0, fix_cycles: int = 0) -> str:
    """Render the task completion footer matching the HTML reference."""
    parts = []
    if files:
        parts.append(f"[{C['text_sec']}]{len(files)}[/] [{C['text_dim']}]files[/]")
    parts.append(f"[{C['text_sec']}]{tokens:,}[/] [{C['text_dim']}]tokens[/]")
    parts.append(f"[{C['text_sec']}]${cost:.2f}[/]")
    if tool_calls:
        parts.append(f"[{C['text_sec']}]{tool_calls}[/] [{C['text_dim']}]tool calls[/]")
    if fix_cycles:
        parts.append(f"[{C['text_sec']}]{fix_cycles}[/] [{C['text_dim']}]fix cycles[/]")
    stats = "  [{0}]·[/]  ".format(C['text_dim']).join(parts)

    return (
        f"[{C['border']}]{'─' * 44}[/]\n"
        f"    [bold {C['create']}]TASK COMPLETE[/]  [{C['text_dim']}]·[/]  "
        f"[{C['text_dim']}]no human escalation[/]\n"
        f"    {stats}"
    )


# ── Main widget ───────────────────────────────────────────

class ActionLedger(Vertical):
    """Ship's log — real-time narrative of every AI action."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._entries: list[LedgerEntry] = []
        self._group_type: str | None = None
        self._group_widget: Static | None = None
        self._group_entries: list[LedgerEntry] = []
        self._last_failed = False
        self._tool_call_count = 0
        self._fix_cycle_count = 0
        self._task_text: str = ""

    def compose(self) -> ComposeResult:
        yield Static("Build Ledger", id="action-ledger-title")
        yield ScrollableContainer(id="ledger-scroll")

    @property
    def _scroll(self) -> ScrollableContainer:
        return self.query_one("#ledger-scroll", ScrollableContainer)

    def _scroll_down(self) -> None:
        self._scroll.scroll_end(animate=False)

    def _close_group(self) -> None:
        self._group_type = None
        self._group_widget = None
        self._group_entries = []

    def _mount_widget(self, widget: Static) -> None:
        self._scroll.mount(widget)
        self._scroll_down()

    def _add_to_group(self, entry: LedgerEntry) -> None:
        """Add entry to current group or start a new one."""
        # Determine grouping key
        group_key = entry.entry_type
        if group_key in ("verify", "fail"):
            group_key = "verify"

        if self._group_type == group_key and self._group_widget:
            # Extend existing group
            self._group_entries.append(entry)
            self._group_widget.update(render_group(self._group_entries))
        else:
            # Close previous group, start new one
            self._close_group()
            self._group_type = group_key
            self._group_entries = [entry]
            widget = Static(
                render_group([entry]),
                markup=True,
                classes=f"ledger-group ledger-{entry.entry_type}",
            )
            self._group_widget = widget
            self._mount_widget(widget)

        self._scroll_down()

    # ── Public API ─────────────────────────────────────────

    def log_task_received(self, task_text: str) -> None:
        """Log the TASK RECEIVED header — call this when a new task starts."""
        self._close_group()
        self._task_text = task_text
        self._tool_call_count = 0
        self._fix_cycle_count = 0
        ts = datetime.now().strftime("%H:%M:%S")
        widget = Static(
            render_task_header(ts, task_text),
            markup=True, classes="ledger-task-header",
        )
        self._mount_widget(widget)

    def log_tool_call(self, tool_call: dict) -> None:
        self._tool_call_count += 1
        entry = LedgerEntry.from_tool_call(tool_call, self._last_failed)
        self._entries.append(entry)
        self._add_to_group(entry)

    def log_tool_result(self, tool_result: dict) -> None:
        if not self._entries:
            return
        last = self._entries[-1]
        old_type = last.entry_type
        last.update_from_result(tool_result)
        self._last_failed = last.success is False

        # Track fix cycles
        if last.success is False:
            self._fix_cycle_count += 1

        # Update the group widget with new result state
        if self._group_widget and last in self._group_entries:
            if last.entry_type == "fail" and old_type != "fail":
                self._group_widget.set_classes("ledger-group ledger-fail")
            elif last.success is True and last.tag == "VERIFY":
                self._group_widget.set_classes("ledger-group ledger-pass")
            self._group_widget.update(render_group(self._group_entries))
            self._scroll_down()

    def log_step(self, step: int, status: str) -> None:
        """Minimal step marker — not verbose."""
        pass  # Steps are implied by tool calls, no need to announce them

    def log_error(self, error: Exception) -> None:
        self._close_group()
        ts = datetime.now().strftime("%H:%M:%S")
        msg = str(error)
        display = msg if len(msg) < 70 else msg[:67] + "..."
        widget = Static(
            f"[{C['text_dim']}]{ts}[/]  [bold {C['fail']}]{display}[/]",
            markup=True, classes="ledger-error",
        )
        self._mount_widget(widget)

    def log_provider_switch(self, old: str, new: str, reason: str) -> None:
        self._close_group()
        ts = datetime.now().strftime("%H:%M:%S")
        widget = Static(
            render_narrative(ts, f"Provider → {new}. {reason}."),
            markup=True, classes="ledger-narrative",
        )
        self._mount_widget(widget)

    def log_info(self, text: str) -> None:
        self._close_group()
        ts = datetime.now().strftime("%H:%M:%S")
        widget = Static(
            render_narrative(ts, text),
            markup=True, classes="ledger-narrative",
        )
        self._mount_widget(widget)

    def log_complete(self, files_created: list, tokens: int, cost: float) -> None:
        self._close_group()
        widget = Static(
            render_complete(
                files_created, tokens, cost,
                self._tool_call_count, self._fix_cycle_count,
            ),
            markup=True, classes="ledger-footer",
        )
        self._mount_widget(widget)

    def clear(self) -> None:
        self._entries.clear()
        self._close_group()
        self._last_failed = False
        self._tool_call_count = 0
        self._fix_cycle_count = 0
        self._scroll.remove_children()
