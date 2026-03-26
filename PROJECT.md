# Deuce

**One sentence in. Eight files out. Watch it happen.**

---

## The Magic Trick

```python
from nexus.easy import build

result = build("Create a REST API with auth")
```

That one line creates files, writes code, runs commands, catches errors, fixes them, and finishes. Under the hood, `build()` calls `execute_task()`, which runs a loop of `@tool`-decorated functions — `create_file`, `write_file`, `execute_command`, `edit_file` — until the job is done.

The `@tool` decorator is the primitive that makes all of it work:

```python
from nexus import tool

@tool(description="Search our database")
def search_db(query: str) -> str:
    return database.search(query)
```

Three lines. Now the AI can call your function. Any function. The decorator extracts the signature, builds the schema, and registers it. The AI sees it as a capability. When it decides to use it, the executor runs it, captures the result, and feeds it back.

**Every AI "action" is just a function call.** File creation? Function. Running a command? Function. Searching files? Function. Your custom database query? Function. The `@tool` decorator is what turns regular code into AI capabilities.

The problem is: nobody can see it happening.

---

## The Problem

When `build("Create a REST API with auth")` runs, it makes 30+ function calls across 5-10 iterations. Files appear on disk. Commands run. Errors get caught and fixed. The AI switches strategies. All of it invisible — the user stares at a loading cursor and gets a result dict at the end.

The Nexus SDK has 40+ features. The web UI shows 10%. The CLI shows 20%. The developer who runs `build()` in a script sees a return value. Everything between "user typed a sentence" and "8 files on disk" is a black box.

## The Insight

**Every `@tool` call should be visible.** Not in a log file. Not in a callback. On screen, in real-time, as it happens.

**The UI is where you gatekeep.** You control what's exposed, what needs confirmation, what the AI can and can't do. A TUI puts that control layer where developers already live — the terminal.

**The folder is the interface.** The workspace directory isn't just where files land — it's a live panel. Files appear as the AI creates them. The project takes shape in real-time. No window switching.

---

## What Deuce Is

A Textual TUI with three panels in one terminal:

```
┌──────────────────────────────────┬──────────────────────┐
│                                  │                      │
│           CHAT PANEL             │    ACTION LEDGER     │
│                                  │                      │
│  > Build a Flask app with auth   │  🔧 create_file      │
│                                  │     app.py           │
│  I'll create that for you.       │  ✅ 42 lines         │
│  Setting up the project          │  🔧 create_file      │
│  structure first...              │     models.py        │
│                                  │  ✅ 28 lines         │
│                                  │  🔧 execute_command  │
│                                  │     pip install flask │
│                                  │  ✅ exit code 0      │
├──────────────┬───────────────────│  🔧 create_file      │
│              │                   │     tests/test_app.py │
│  FILE BROWSER│   FILE PREVIEW    │  ✅ 35 lines         │
│              │                   │  ❌ pytest failed     │
│  📁 workspace│  # app.py         │  🔧 edit_file        │
│  ├── app.py ★│  from flask ...   │     app.py (fix)     │
│  ├── models. │  app = Flask(__)  │  ✅ replaced 3 lines │
│  ├── require │  ...              │  🔧 execute_command  │
│  ├── config. │                   │     pytest           │
│  └── tests/  │                   │  ✅ 4 passed         │
│      └── tes │                   │                      │
└──────────────┴───────────────────┴──────────────────────┘
  anthropic ▾ │ ./workspace │ 3,847 tokens │ $0.04 │ 8 files
```

### Chat Panel (top-left)
- Talk to any AI provider through Nexus
- Markdown rendered natively by Rich
- Provider switcher in the footer
- Confirmation dialogs appear inline when the AI wants to do something destructive — a real prompt, not a code callback
- This is where you type one sentence and watch everything else react

### Action Ledger (right)
- **Every `@tool` function call, visible in real-time**
- `create_file`, `write_file`, `edit_file`, `execute_command`, `search_files` — the built-ins
- `search_db`, `deploy`, `alert_slack` — your custom `@tool` functions too
- Results, errors, retries, provider switches — all timestamped
- The governance value prop: you see everything the AI decides to do before, during, and after
- Collapsible entries for multi-step tasks

### File Browser (bottom-left)
- Live watches the workspace directory (`watchfiles` — already in deps)
- Tree view. Files appear as the AI creates them. No refresh.
- `★` indicator on new/modified files
- Select a file → preview its contents in the adjacent pane with Rich syntax highlighting
- The workspace IS the project. The folder IS the UI.

### Footer Bar
- Current provider + model
- Workspace path
- Token count + cost for current session
- Files created count

---

## The `@tool` Connection

This is the thread that ties everything together:

```
User types sentence
        │
        ▼
  NexusConnector.execute_task()
        │
        ▼
  AI decides what to do
        │
        ▼
  @tool function called  ──────→  Action Ledger shows it
        │
        ▼
  Function runs           ──────→  File Browser updates
        │
        ▼
  Result fed back to AI   ──────→  Action Ledger shows result
        │
        ▼
  AI decides next step... (loop)
        │
        ▼
  Task complete           ──────→  Footer shows totals
```

**Every arrow is a Nexus hook that already exists:**
- `on_tool_call` → feeds the action ledger (call)
- `on_tool_result` → feeds the action ledger (result)
- `on_step` → feeds the progress indicator
- `on_error` → feeds the error display
- `on_provider_switch` → shows fallback events
- `confirm_callback` → powers the inline confirmation dialog
- `get_created_files()` → feeds the file browser
- `ExecutionLog` → the whole session is structured and exportable

The hooks are built. The execution engine is built. The tool system is built. Deuce just makes all of it visible.

## Extensibility

Because `@tool` is the primitive, extending Deuce is extending Nexus:

```python
from nexus import tool

@tool(description="Query production database", destructive=False)
async def query_db(sql: str) -> str:
    return await db.execute(sql)

@tool(description="Deploy to staging", destructive=True)
async def deploy(version: str) -> str:
    return await k8s.deploy("staging", version)
```

Register these with the connector, and they show up in the action ledger automatically. `destructive=True` means Deuce shows a confirmation dialog before execution. The user didn't build a UI plugin — they wrote a function and decorated it.

---

## The Demo (the video)

1. Terminal opens. `deuce` launches. Three panels appear.
2. User types: "Build a Flask app with user authentication and SQLite"
3. Chat panel: AI responds, starts working
4. Action ledger starts scrolling — `create_file: app.py`, `create_file: models.py`, `create_file: requirements.txt`
5. File browser: files appear one by one. The tree grows in real-time.
6. User clicks `app.py` — full source code appears in the preview pane
7. Action ledger: `execute_command: pytest` → `❌ 1 failed`
8. Action ledger: `edit_file: app.py` → `✅ fixed`
9. Action ledger: `execute_command: pytest` → `✅ 4 passed`
10. Footer: `8 files │ 3,847 tokens │ $0.04 │ 12 tool calls`

One sentence in. Eight files out. Watched it happen.

---

## The Stack

| Component | Tool | Notes |
|-----------|------|-------|
| TUI framework | **Textual** | Only new dep. Built on Rich. Layouts, mouse, CSS-like styling. |
| File watching | **watchfiles** | Already installed (uvicorn dep). Rust-backed, fast. |
| AI engine | **Nexus SDK** | Everything — execution, tools, routing, observability. |
| Markdown | **Rich** | Already installed. Native terminal markdown. |
| Syntax highlighting | **Rich** | Already installed. Code preview in file pane. |

## Architecture

```
Deuce (TUI — the surface)
  ├── ChatPanel        → NexusConnector.send_message() / execute_task()
  ├── ActionLedger     → on_tool_call, on_tool_result, on_step, on_error
  ├── FileBrowser      → watchfiles on workspace dir
  ├── FilePreview      → Rich syntax highlighting
  ├── ConfirmDialog    → confirm_callback (destructive=True tools)
  ├── ProviderSwitcher → Nexus router + provider list
  └── StatusBar        → TaskResult metrics, token count, cost
          │
          ▼
Nexus SDK (the engine — already built)
  ├── UnifiedAIWrapper    (6 providers, auto key detection)
  ├── ToolExecutor        (8 built-in tools + @tool custom)
  ├── Router              (7 strategies, auto task classification)
  ├── ExecutionLog        (16 event types, JSON export)
  ├── RetryHandler        (4 configs + circuit breaker)
  ├── RateLimiter         (token bucket, sliding window, concurrency)
  ├── Metrics             (Prometheus-compatible)
  └── MCP client          (filesystem, github, memory, postgres, ...)
```

## What Deuce Is NOT

- Not a code editor — use your editor for editing
- Not a web app — `ui.py` stays in Nexus for that
- Not a multi-agent framework — one agent, governed
- Not rebuilding Nexus — it's a surface, not an engine

## Name

**Deuce** — the second thing built on the Nexus SDK. The ace is the engine. The deuce is what you play with it.

## Open Questions

1. CLI command (`nexus deuce`) or standalone (`pip install deuce`)?
2. Session persistence — save/resume TUI sessions?
3. Multiple workspaces / project tabs?
4. File browser: read-only or basic operations (rename, delete, new)?
5. Export action ledger to JSON/markdown?
6. Should the action ledger support filtering (e.g., only file ops, only errors)?
