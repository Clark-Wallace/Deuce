# Deuce — CONVENTIONS.md
## Code patterns extracted from the working codebase

These patterns are derived from the existing Deuce code, not invented. Every example references an actual file. Follow what's already established — don't invent a second way to do something.

---

## File Structure

Deuce uses a flat widget directory. No subdirectories, no `panels/` vs `widgets/` split.

```
Deuce/
├── app.py              # Main Textual app — layout, hooks, keybindings
├── connector.py        # NexusConnector wrapper — the only file that imports nexus
├── prompt.py           # System prompt builder
├── tools.py            # Custom @tool functions
├── styles.tcss         # Textual CSS
└── widgets/
    ├── __init__.py     # Re-exports all widgets
    ├── action_ledger.py
    ├── chat_panel.py
    ├── confirm_dialog.py
    ├── file_browser.py
    └── provider_switcher.py
```

**File naming:** `snake_case.py`. No PascalCase files, no `-` in filenames.

---

## Widget Pattern (from chat_panel.py)

This is the established pattern. Every widget follows it.

```python
"""Chat panel — RichLog for messages + Input for user text."""
                                          # ← one-line docstring

from textual.app import ComposeResult     # ← std lib, then textual, then local
from textual.containers import Vertical
from textual.widgets import Input, RichLog
from textual.message import Message
from rich.markdown import Markdown
from rich.text import Text


class ChatPanel(Vertical):                # ← inherits a Textual container
    """Chat display with input."""

    class MessageSubmitted(Message):      # ← nested Message class for events
        """User submitted a message."""
        def __init__(self, text: str) -> None:
            super().__init__()
            self.text = text              # ← typed data on the message

    def compose(self) -> ComposeResult:   # ← compose yields the widget tree
        yield RichLog(id="chat-log", markup=True, wrap=True)
        yield Input(
            id="chat-input",
            placeholder="Type a message... (Enter to send)",
        )

    def on_mount(self) -> None:           # ← lifecycle: runs after compose
        # Initial content setup
        ...

    def on_input_submitted(self, event: Input.Submitted) -> None:
        # ← Textual event handler naming: on_<widget>_<event>
        text = event.value.strip()
        if not text:
            return
        event.input.value = ""
        self.add_user_message(text)
        self.post_message(self.MessageSubmitted(text))

    # ── Public API (called by app.py) ──

    def add_user_message(self, text: str) -> None: ...
    def add_ai_message(self, text: str) -> None: ...
    def add_system_message(self, text: str) -> None: ...
    def set_working(self, working: bool) -> None: ...
```

### What this pattern establishes:

1. **Module docstring** — one line, describes the file
2. **Imports** — standard lib → textual/rich → local (no relative `../` imports)
3. **Class inherits a Textual container** — `Vertical`, `Horizontal`, `ScrollableContainer`
4. **Nested Message classes** for events this widget emits, with typed data
5. **`compose()`** yields the widget tree with `id=` on every widget
6. **`on_mount()`** for post-compose setup
7. **Event handlers** use Textual's `on_<widget>_<event>` naming
8. **Public API methods** are what `app.py` calls — clear names, typed parameters
9. **No state initialization in `compose()`** — state lives in `__init__` or reactive properties

```python
# ❌ Bad — violates established patterns
class MyWidget(Vertical):
    def compose(self):                    # missing ComposeResult type hint
        self.items = []                   # state in compose
        yield Static()                    # no id

    def handle_click(self, data):         # not Textual event naming
        ...
```

---

## Nexus Bridge Pattern (from connector.py)

`connector.py` is the **only file** that imports from `nexus`. Widgets never import Nexus directly.

```python
# connector.py — the only nexus import point
from nexus import NexusConnector
from nexus.core.base_connector import AIProvider

class DeuceConnector:
    def __init__(self, workspace, on_tool_call, on_tool_result, ...):
        self._on_tool_call = on_tool_call    # hooks stored as callbacks
        ...
        self._connector: Optional[NexusConnector] = None  # lazy

    def _build_connector(self) -> NexusConnector:
        connector = NexusConnector(
            provider=self.current_provider,
            api_key=self.current_api_key,
            workspace=self.workspace,
            tools=DEUCE_TOOLS,               # custom @tool functions
            on_tool_call=self._on_tool_call,  # pass hooks through
            on_tool_result=self._on_tool_result,
            ...
        )
        return connector

    @property
    def connector(self) -> NexusConnector:   # lazy build on first access
        if self._connector is None:
            self._connector = self._build_connector()
        return self._connector

    def switch_provider(self, provider_id):
        self._connector = None               # null → rebuild on next use
```

### What this pattern establishes:

- **One bridge, one file.** No widget ever does `from nexus import ...`
- **Lazy construction.** Connector is built on first use, not at init
- **Provider switching nulls the connector.** Next access rebuilds with new provider
- **Hooks are callbacks passed through.** `app.py` defines them, `connector.py` wires them to Nexus

```python
# ❌ Bad — widget imports nexus directly
# widgets/action_ledger.py
from nexus import NexusConnector        # WRONG — only connector.py touches nexus
```

---

## @tool Pattern (from tools.py)

Custom tools use Nexus's `@tool` decorator and a module-level workspace variable.

```python
from nexus import tool

_workspace: str = "./workspace"

def set_workspace(workspace: str) -> None:
    global _workspace
    _workspace = workspace

def _deuce_dir() -> Path:
    d = Path(_workspace) / ".deuce"
    d.mkdir(parents=True, exist_ok=True)
    return d

@tool(description="Store project context — decisions, constraints, tech choices.")
def context(key: str, value: str) -> str:
    """Store a project context entry.

    Args:
        key: Context key (e.g. "framework", "database")
        value: Context value (e.g. "Flask", "SQLite")
    """
    path = _deuce_dir() / "context.json"
    data = {}
    if path.exists():
        data = json.loads(path.read_text())
    data[key] = {"value": value, "updated": datetime.now().isoformat()}
    path.write_text(json.dumps(data, indent=2))
    return f"Context saved: {key} = {value}"

# Collected at bottom of file
DEUCE_TOOLS = [context, user_story, plan, review, complete_story]
```

### What this pattern establishes:

- **`@tool(description=...)` decorator** with a clear, imperative description
- **Typed parameters** — the decorator extracts the signature for schema building
- **Docstring with `Args:` section** — Nexus uses this for parameter descriptions
- **Returns a string** — tool results are always strings fed back to the AI
- **Persistent state via JSON files** in `.deuce/`
- **All tools collected in `DEUCE_TOOLS` list** at the bottom, imported by `connector.py`

---

## Hook Wiring Pattern (from app.py)

`app.py` defines hook callbacks and passes them to `DeuceConnector`. Hooks catch their own exceptions so a rendering error never crashes the execution loop.

```python
class Deuce(App):
    def __init__(self, workspace="./workspace", **kwargs):
        super().__init__(**kwargs)
        self.deuce_connector = DeuceConnector(
            workspace=workspace,
            on_tool_call=self._handle_tool_call,
            on_tool_result=self._handle_tool_result,
            on_step=self._handle_step,
            on_error=self._handle_error,
            on_provider_switch=self._handle_provider_switch,
        )

    def _handle_tool_call(self, tc: dict) -> None:
        try:
            ledger = self.query_one(ActionLedger)
            ledger.log_tool_call(tc)
        except Exception:
            pass                           # never crash the AI execution loop

    def _handle_tool_result(self, tr: dict) -> None:
        try:
            ledger = self.query_one(ActionLedger)
            ledger.log_tool_result(tr)
            self._refresh_files()          # file browser updates on every result
        except Exception:
            pass
```

### What this pattern establishes:

- **Hooks are methods on the App class** prefixed `_handle_`
- **Every hook wraps in try/except** — rendering failures must not break Nexus execution
- **Hooks delegate to widget public API** — `ledger.log_tool_call(tc)`, not direct rendering
- **`_handle_tool_result` triggers file browser refresh** — this is how files appear in real-time

---

## Ledger Public API (preserve this during rewrite)

The action ledger has an established public API that `app.py` calls. The ledger rewrite changes internal rendering, not this interface:

```python
class ActionLedger(Vertical):
    def log_tool_call(self, tool_call: dict) -> None: ...
    def log_tool_result(self, tool_result: dict) -> None: ...
    def log_step(self, step: int, status: str) -> None: ...
    def log_error(self, error: Exception) -> None: ...
    def log_provider_switch(self, old: str, new: str, reason: str) -> None: ...
    def log_info(self, text: str) -> None: ...
    def log_complete(self, files_created: list, tokens: int, cost: float) -> None: ...
```

**The tool_call dict shape** (from Nexus hooks):
```python
{
    "name": "create_file",        # tool function name
    "arguments": {                # kwargs passed to the tool
        "path": "app.py",
        "content": "from flask import Flask\n..."
    }
}
```

**The tool_result dict shape:**
```python
{
    "name": "create_file",
    "result": {
        "success": True,          # or False with "error" key
        ...
    }
}
```

---

## Ledger Design System (for the rewrite)

These conventions apply specifically to the Action Ledger rewrite. They're derived from `deuce_anvil_ships_log_ledger.html`.

### Entry Types

| Tool Name | Ledger Type | Tag |
|-----------|------------|-----|
| `create_file`, `write_file` | `create` | CREATE |
| `execute_command` (test/verify) | `verify` | VERIFY |
| `execute_command` (other) | `run` | RUN |
| `edit_file` (after a failure) | `patch` | PATCH |
| `edit_file` (otherwise) | `create` | CREATE |
| Step/assessment entries | `info` | — (narrative, no tag) |
| Errors | `fail` | — (shown in result color) |

### Grouping Rules

- Sequential tool calls of the same type → one action group
- Type change → new group
- Narrative entry (info/step) → breaks any open group
- Each group gets: colored left border, background tint, one or more child entries

### Color Mapping to Textual CSS

The HTML reference uses CSS custom properties. Map them to Textual:

```
HTML reference          → Textual CSS
--bg-deep: #0c1117     → Screen background
--bg-panel: #141b22    → ActionLedger background
--bg-entry: #1a232d    → Entry background
--text-primary: #c9d1d9 → Default text
--text-secondary: #8b949e → Detail text
--text-dim: #535d68     → Timestamps
--accent-create: #3fb950 → Create/pass borders and tags
--accent-fail: #f85149   → Fail borders and tags
--accent-patch: #d29922  → Patch borders and tags
--accent-info: #58a6ff   → Info borders and tags
```

### Narrative Voice Rules

Narrative entries (assessment, transitions, final checks) use ship's log voice:

- Present tense, declarative
- No first person ("I", "we")
- No filler words ("now", "just", "simply")
- No passive voice ("was completed")
- Em dashes for elaboration, not parentheses
- Period at the end, not ellipsis

---

## Anti-Patterns

### Code Quality
- **Comments restating the code.** The codebase has almost no comments — and it's readable. Keep it that way.
- **Dead code.** No commented-out blocks, no unused imports, no "just in case" functions.
- **Raw dicts for data shapes.** If you're passing structured data, define a dataclass or NamedTuple. The tool_call/tool_result dicts are a Nexus interface — don't add more raw dicts on the Deuce side.
- **Verbose names when context is clear.** `ledger_entry_widget` in a file called `action_ledger.py` — just `entry`.

### Architecture
- **Widgets importing nexus.** Only `connector.py` touches Nexus.
- **Modifying working components.** The ledger rewrite is internal to `action_ledger.py`. Don't change `app.py` hook wiring, `connector.py`, `prompt.py`, or `tools.py`.
- **Multiple ways to do the same thing.** If `chat_panel.py` uses `RichLog` for display and `Input` for user text, don't introduce a different pattern in a new widget without justification.
- **Global mutable state beyond `tools.py`.** The `_workspace` global in `tools.py` is the one exception — it exists because `@tool` functions need workspace access. Don't add more module-level mutables.

### Design
- **Log-format rendering in the ledger.** `[INFO] 15:28:43 create_file app.py` is a log. The target is a ship's log with narrative voice, grouped actions, and color-coded types.
- **Hardcoded colors outside the design system.** Every color has a semantic name. Don't put hex values inline in widget code — define them in styles or as constants.
- **Inconsistent timestamps.** Always `HH:MM:SS` via `datetime.now().strftime("%H:%M:%S")` — already established in the current ledger.

---

## Testing (when added)

Follow `pytest` conventions. Mock Nexus at the connector boundary — never call real APIs in tests.

```python
# tests/test_action_ledger.py

def test_tool_call_creates_entry_with_correct_type():
    """create_file tool call → LedgerEntry with type 'create'."""
    tc = {"name": "create_file", "arguments": {"path": "app.py", "content": "..."}}
    entry = LedgerEntry.from_tool_call(tc)
    assert entry.entry_type == "create"
    assert entry.file_name == "app.py"

def test_sequential_creates_form_one_group():
    """Three create_file entries in sequence → one ActionGroup."""
    entries = [make_entry("create"), make_entry("create"), make_entry("create")]
    groups = ActionGroup.from_entries(entries)
    assert len(groups) == 1

def test_type_change_breaks_group():
    """create then run → two groups."""
    entries = [make_entry("create"), make_entry("run")]
    groups = ActionGroup.from_entries(entries)
    assert len(groups) == 2
```

Test names: `test_<what>_<condition>` or `test_<what>_<condition>_<expected>`. No single-letter variables. No tests that assert `is not None` and call it a day.
