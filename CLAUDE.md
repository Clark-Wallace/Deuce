# Deuce — CLAUDE.md
## The Nexus Connector's Governed Terminal

Deuce is a first-party application inside the [Nexus Connector](https://github.com/Clark-Wallace/The-Nexus-Connector) repository. It showcases the SDK's core value propositions in a single terminal session: `@tool` execution, observable hooks, multi-provider switching, human-in-the-loop confirmation, cost tracking, and autonomous task completion. One sentence in, eight files out, watch it happen.

**Built on the Nexus SDK.** Deuce depends on `nexus-connector` installed from GitHub. Every feature Deuce exposes is a Nexus SDK feature made visible. For SDK internals, see the [Nexus Connector](https://github.com/Clark-Wallace/The-Nexus-Connector) repo's `ARCHITECTURE.md`, `API_REFERENCE.md`, and `ROADMAP.md`.

---

## What Deuce Demonstrates (Nexus SDK Features)

| Nexus Feature | How Deuce Surfaces It |
|---------------|----------------------|
| `@tool` decorator + ToolExecutor | Action Ledger shows every tool call in real-time |
| `on_tool_call` / `on_tool_result` hooks | Feed the ledger stream as events fire |
| `on_step` / `on_error` hooks | Step progress and error entries in the ledger |
| `on_provider_switch` hook | Provider change events in ledger + chat notification |
| `confirm_callback` (destructive=True) | Modal confirmation dialog blocks execution until human approves |
| `TaskResult` (tokens, cost, files) | Footer bar with running session totals |
| Multi-provider switching | Dropdown selector, live swap, connector rebuild |
| `execute_task()` iterative loop | Full autonomous build visible across all panels |
| Custom `@tool` functions | Project management tools (context, user_story, plan, review) registered alongside built-ins |

---

## Current Architecture

```
Deuce/
├── app.py              ─ DeuceApp(App): layout, hook wiring, keybindings, workspace switching
├── connector.py        ─ DeuceConnector: wraps NexusConnector, provider detection, lazy build
├── prompt.py           ─ System prompt builder: onboarder + .deuce/ project state injection
├── tools.py            ─ 5 custom @tool functions for project memory
├── styles.tcss         ─ Textual CSS layout
├── widgets/
│   ├── __init__.py
│   ├── chat_panel.py       ─ RichLog + Input, markdown rendering, working state
│   ├── action_ledger.py    ─ Tool call stream (⚠️ current: flat Log widget)
│   ├── file_browser.py     ─ DirectoryTree + TextArea code preview
│   ├── confirm_dialog.py   ─ Modal screen for destructive=True tools
│   └── provider_switcher.py ─ Select dropdown with ProviderChanged message
├── requirements.txt    ─ nexus-connector from GitHub + Textual
├── .env.example        ─ API key template
├── .gitignore
├── deuce_anvil_ships_log_ledger.html  ─ Canonical ledger visual reference
└── workspace/          ─ Default workspace directory
```

### How the Pieces Connect

```
User types message
    │
    ▼
app.py on_chat_panel_message_submitted()
    │
    ├─ Heuristic: task keywords? ──→ connector.execute_task(text)
    │                                     │
    │                                     ▼
    │                               NexusConnector iterative loop
    │                                     │
    │                               on_tool_call ──→ ledger.log_tool_call()
    │                               on_tool_result ─→ ledger.log_tool_result()
    │                                                  + file_browser.refresh_tree()
    │                               on_step ────────→ ledger.log_step()
    │                               on_error ───────→ ledger.log_error()
    │                                     │
    │                               TaskResult ────→ chat.add_ai_message()
    │                                                  + ledger.log_complete()
    │                                                  + footer stats update
    │
    └─ Otherwise ──→ connector.send_message(text)
                          │
                          ▼
                    Response dict ──→ chat.add_ai_message()
```

### connector.py — The Nexus Bridge

`DeuceConnector` is the single point of contact with the Nexus SDK. It:
- Detects available providers from environment variables
- Lazily builds a `NexusConnector` with hooks, tools, and system prompt
- Registers Deuce's 5 custom `@tool` functions alongside Nexus built-ins
- Injects project state from `.deuce/` into the system prompt every session
- Handles provider switching by nulling the connector and rebuilding on next use

### tools.py — Project Memory via @tool

Deuce extends Nexus with 5 project management tools that persist to `.deuce/` in the workspace:
- `context(key, value)` — store decisions, constraints, tech choices
- `user_story(as_a, i_want, so_that)` — structured requirements
- `plan(task, steps)` — build plan with checkboxes
- `review()` — compare built files against stories and plan
- `complete_story(story_id)` — mark a story done

These demonstrate the `@tool` decorator's extensibility — the AI can call project management functions the same way it calls `create_file` or `execute_command`.

### prompt.py — Context Injection

The system prompt builder loads `.deuce/context.json`, `.deuce/stories/`, and `.deuce/plan.md` and injects them into every AI turn. This means the AI remembers project decisions across the full session — demonstrating how custom tools + prompt engineering create persistent agent memory on top of Nexus.

---

## What's Built and Working

| Component | Lines | Status |
|-----------|-------|--------|
| App shell, layout, keybindings, workspace switching | 327 | ✅ Complete |
| DeuceConnector (Nexus bridge, provider detection) | 154 | ✅ Complete |
| System prompt + .deuce/ state injection | 112 | ✅ Complete |
| 5 custom @tool project management functions | 199 | ✅ Complete |
| ChatPanel (RichLog, markdown, user/AI/system messages) | 73 | ✅ Complete |
| FileBrowser (DirectoryTree + code preview) | 76 | ✅ Complete |
| ConfirmDialog (modal, allow/deny, keyboard shortcuts) | 86 | ✅ Complete |
| ProviderSwitcher (Select dropdown, ProviderChanged msg) | 46 | ✅ Complete |
| Layout styles (Textual CSS) | 139 | ✅ Functional |
| ActionLedger (flat Log with emoji) | 80 | ⚠️ Basic — needs rewrite |

**Everything works end-to-end.** You can launch Deuce, type a task, watch the AI build software, see tool calls in the ledger, browse created files, switch providers, and get cost/token totals. The remaining work is about making the ledger match the design vision.

---

## Remaining Build Work

### Priority 1: Action Ledger Rewrite

The ledger is the showcase. Right now it's a flat `Log` widget writing timestamped emoji lines. The target is the **ship's log** design defined in `deuce_anvil_ships_log_ledger.html` (repo root).

**Current output:**
```
15:28:43 🔧 create_file: app.py
         ✅ done
15:28:44 🔧 create_file: models.py
         ✅ done
```

**Target output:** Grouped action entries with colored left borders, narrative voice, typed tags (CREATE / VERIFY / PATCH / RUN), detail lines with file descriptions and line counts, error analysis, and a task completion footer with session stats.

**What this requires:**
- Replace `Log` widget with a `ScrollableContainer` that mounts styled child widgets
- Data model for `LedgerEntry` and `ActionGroup` (typed, timestamped, grouped)
- Grouping logic: sequential same-type tool calls collapse into one group
- Color system: green (create/pass), red (fail), amber (patch), blue (info), gray (run)
- Narrative voice generation for assessment and transition entries
- Task footer widget showing completion status + stats
- Map the HTML reference's CSS to Textual CSS equivalents

**What this does NOT require:**
- Changing `connector.py`, `app.py` hook wiring, or any other working component
- The ledger's public API (`log_tool_call`, `log_tool_result`, `log_step`, `log_error`, `log_complete`) stays the same — only the internal rendering changes

### Priority 2: Style Alignment

`styles.tcss` currently uses Textual's default design variables (`$primary-darken-2`, `$surface`, etc.). The HTML reference defines a specific palette. Aligning these is a targeted edit to the stylesheet and the ledger's widget styles — not a rewrite of the layout.

### Priority 3: Tests

No tests exist yet. After the ledger rewrite, add tests for:
- Ledger entry creation from tool call dicts
- Action grouping logic (sequential same-type → one group, type change → new group)
- Narrative voice generation
- Data model serialization

---

## Layout

```
┌──────────────────────────────────┬──────────────────────┐
│                                  │                      │
│           CHAT PANEL             │    ACTION LEDGER     │
│    (RichLog + Input)             │    (ship's log)      │
│                                  │                      │
├──────────────┬───────────────────│                      │
│  FILE BROWSER│   FILE PREVIEW    │                      │
│  (DirTree)   │   (TextArea)      │                      │
└──────────────┴───────────────────┴──────────────────────┘
  Provider ▾ │ workspace path │ tokens │ cost │ files
```

---

## Dev Commands

```bash
# Setup
pip install -r requirements.txt   # installs Nexus SDK from GitHub + Textual
cp .env.example .env              # add your API keys

# Run Deuce
python app.py                     # default workspace: ./workspace
python app.py /path/to/dir        # custom workspace

# Run tests (when they exist)
pytest tests/ -v
```

---

## Scope Boundary

### In Scope (MVP — current state + ledger rewrite)
- Everything currently built and working
- Action Ledger rewrite to ship's log design
- Style alignment with HTML reference palette
- Tests for ledger data model and grouping logic

### Out of Scope (Do Not Build)
- Changes to connector.py, prompt.py, tools.py, or any working component
- Session persistence / save-resume
- Multiple workspaces / project tabs
- File browser write operations
- Ledger export or filtering
- Standalone pip package
- Anything that requires modifying Nexus SDK internals

---

## Build Session Protocol

- Read CONVENTIONS.md before writing any code
- Read the existing widget code in `widgets/` to match established patterns
- **Do not modify working components.** The ledger rewrite is internal to `action_ledger.py` (and potentially a new data model file). The public API stays the same.
- Follow the patterns from `chat_panel.py` — it's the reference implementation for Deuce widgets
- Run the app after changes to verify nothing broke: `python app.py`
- If something won't work as planned, document why and propose an alternative — don't silently deviate

---

## The Ledger: Design Reference

The file `deuce_anvil_ships_log_ledger.html` in the repo root is the canonical visual reference. Key design decisions from that file:

### Color System
| Type | Border/Tag | Background Gradient |
|------|-----------|-------------------|
| create | #3fb950 (green) | #1a3a2a → transparent |
| pass | #3fb950 (green) | #1a3a2a → transparent |
| fail | #f85149 (red) | #3d1a1a → transparent |
| patch | #d29922 (amber) | #3a2e14 → transparent |
| info | #58a6ff (blue) | #1a2a3d → transparent |
| run | #8b949e (gray) | bg-entry only |

### Narrative Voice
Present tense, declarative, no pronouns, no filler:
- ✅ "Assessing workspace. Clean slate — no prior artifacts."
- ✅ "Installing dependencies. `pip install -r requirements.txt` — clean."
- ❌ "I'm going to check the workspace now."
- ❌ "INFO: Workspace assessment complete."

### Entry Structure
`timestamp → tag → filename/command → indented detail`

### Grouping
Sequential same-type tool calls collapse into one bordered group. Type change or narrative entry breaks the group.

### Fonts
- Entries/timestamps: JetBrains Mono (or terminal monospace fallback)
- Labels/headers: IBM Plex Sans (or terminal sans fallback)
