# Deuce

<div align="center">

![Deuce](https://img.shields.io/badge/Deuce-TUI-blue)
[![Built on Nexus](https://img.shields.io/badge/Built_on-Nexus_Connector-purple)](https://github.com/Clark-Wallace/The-Nexus-Connector)
[![Python](https://img.shields.io/badge/Python-3.8+-green.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**One sentence in. Eight files out. Watch it happen.**

<!-- Demo video — replace with actual recording -->
<!-- https://github.com/user-attachments/assets/YOUR-VIDEO-ID -->
<!--
<p align="center">
  <a href="https://github.com/Clark-Wallace/Deuce">
    <img src="https://img.shields.io/badge/▶_Watch_Demo-1a1a2e?style=for-the-badge&logo=youtube&logoColor=white" alt="Watch Demo">
  </a>
</p>
-->

[Quick Start](#-quick-start) • [What You See](#-what-you-see) • [The Action Ledger](#-the-action-ledger) • [Built on Nexus](#-built-on-nexus)

</div>

---

## The Problem

When an AI agent builds software, it makes 30+ function calls across 5-10 iterations. Files appear on disk. Commands run. Errors get caught and fixed. The AI switches strategies.

All of it invisible. You stare at a loading cursor and get a result dict at the end.

## The Fix

Deuce is a terminal UI that makes every AI action visible in real-time. You type one sentence. Three panels react. Files appear as the AI creates them. Tests fail and get fixed. The action ledger shows every decision. The footer tallies the cost.

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

---

## ⚡ Quick Start

```bash
git clone https://github.com/Clark-Wallace/Deuce.git
cd Deuce
pip install -r requirements.txt
cp .env.example .env
# Add at least one API key to .env
python app.py
```

That's it. Deuce opens in your terminal. Type a sentence. Watch it build.

### Want a specific workspace?

```bash
python app.py /path/to/your/project
```

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Ctrl+O` | Open a different workspace folder |
| `Ctrl+P` | Focus provider switcher |
| `Ctrl+L` | Clear the action ledger |
| `Ctrl+N` | New session (clear history) |
| `Ctrl+Q` | Quit |

---

## 👀 What You See

### Chat Panel (top-left)
Talk to any AI provider through the Nexus SDK. Type a sentence describing what you want built — or just have a conversation. Markdown renders natively. When the AI is working, the input shows "AI is working..." and re-enables when it's done.

The chat panel decides how to route your message: if it looks like a build task ("create", "build", "make", "write"), it uses Nexus's `execute_task()` for autonomous multi-step execution. Otherwise, it sends a simple message. Either way, you see everything in the other panels.

### Action Ledger (right)
Every `@tool` function call the AI makes, visible in real-time. File creates, command executions, edits, searches — timestamped and color-coded. When a test fails, you see it. When the AI fixes the code and re-runs, you see that too. When the task completes, the ledger shows the totals: files created, tokens used, cost.

This is the governance layer. You see everything the AI decides to do, as it decides to do it.

### File Browser (bottom-left)
The workspace directory as a live tree. Files appear as the AI creates them — no refresh needed. Click any file to see its contents syntax-highlighted in the preview pane. The workspace IS the project. The folder IS the interface.

### Footer Bar
Current provider and model. Workspace path. Running token count and cost for the session. Number of files created. Always visible, always updating.

---

## 📋 The Action Ledger

The ledger is what makes Deuce worth existing. It's not a log viewer — it's a **ship's log** for AI execution.

Every entry has a timestamp. Related actions group together with colored borders. The AI's decisions read like a narrative, not a debug trace:

```
15:28:14  ● TASK RECEIVED
          "Build a Python weather CLI with colored output. Include tests."

15:28:27  Assessing workspace. Clean slate — no prior artifacts.

15:28:43  CREATE  weather_cli.py
          Main module. Fetches from wttr.in, parses JSON,
          renders with colorama. 3 functions. 42 lines.

          CREATE  requirements.txt
          3 deps pinned — requests, colorama, pytest

15:29:08  CREATE  test_weather_cli.py
          4 tests: fetch success, fetch error, parse response,
          display format. Uses unittest.mock.

15:29:13  VERIFY  pytest test_weather_cli.py
          3 passed, 1 failed.
          test_display_format — expected dict, got raw JSON string.

15:29:23  PATCH   weather_cli.py
          parse_response(): added json.loads(), returns dict.
          2 lines changed.

15:29:25  VERIFY  pytest test_weather_cli.py
          4/4 passed. All green.

          ✅ Task complete · 5 files · 4,200 tokens · $0.03 · 1 fix cycle
```

Green for creates and passes. Red for failures. Amber for patches. Blue for status. Everything the AI did, everything it decided, everything it cost.

---

## 🔌 Providers

Deuce supports every provider the Nexus SDK supports. Add your API keys to `.env` and switch live from the dropdown — no restart needed.

| Provider | Models | Local |
|----------|--------|:-----:|
| **Anthropic** | Claude 4 Opus/Sonnet, Claude 3.5 | ❌ |
| **OpenAI** | GPT-4o, GPT-4, GPT-3.5 | ❌ |
| **Google** | Gemini 2.0, 1.5 Pro/Flash | ❌ |
| **xAI** | Grok-3, Grok-2 | ❌ |
| **DeepSeek** | DeepSeek-V3, Coder | ❌ |
| **Ollama** | Llama, Mistral, CodeLlama, any | ✅ |

Ollama works automatically if running locally — no API key needed. Full privacy, zero cost.

---

## 🛡️ Governance Built In

Deuce inherits the Nexus SDK's safety model:

**Human-in-the-loop confirmation.** When the AI wants to do something destructive — delete a file, run a dangerous command — Deuce shows a modal confirmation dialog. You allow or deny. The AI doesn't proceed until you decide.

**Cost transparency.** Every session shows running token count and dollar cost in the footer. You always know what the AI is spending.

**Observable execution.** The action ledger isn't optional chrome — it's the point. Every tool call, every result, every error, every retry. The AI can't do anything you don't see.

**Workspace isolation.** Files are created in the workspace directory. The AI operates in its sandbox.

---

## 🧠 Project Memory

Deuce includes five `@tool` functions that give the AI persistent project memory:

```bash
# The AI can store and recall project decisions
context("framework", "Flask")
context("database", "SQLite")

# Capture structured requirements
user_story("a registered user", "to save recipes", "I can find them later")

# Create build plans
plan("Weather CLI", "1. Create main module\n2. Add tests\n3. Install deps")

# Review progress against stories
review()

# Mark stories complete
complete_story(1)
```

These persist to `.deuce/` in your workspace as JSON and markdown. The system prompt loads them every turn, so the AI remembers your project decisions across the full session.

---

## 🔨 Built on Nexus

Deuce is a showcase for the [Nexus Connector](https://github.com/Clark-Wallace/The-Nexus-Connector) SDK. Everything you see in Deuce is a Nexus feature made visible:

| What Deuce Shows | Nexus Feature Underneath |
|-----------------|------------------------|
| Action ledger streaming tool calls | `on_tool_call` / `on_tool_result` hooks |
| Files appearing in the browser | `@tool` decorator + `ToolExecutor` |
| AI fixing its own errors | `execute_task()` iterative loop |
| Provider dropdown switching live | Multi-provider `UnifiedAIWrapper` |
| Confirmation dialog on destructive ops | `confirm_callback` + `destructive=True` |
| Token count and cost in footer | `TaskResult` metrics |
| Project memory tools | Custom `@tool` functions registered at runtime |

Deuce adds exactly **one dependency** beyond Nexus: [Textual](https://textual.textualize.io/) for the terminal UI. Everything else — Rich markdown, syntax highlighting, provider routing, tool execution, retry logic — is already in the SDK.

**The Nexus SDK has 40+ features. Deuce makes them visible.**

---

## Architecture

```
Deuce (what you see)
  ├── Chat Panel       → NexusConnector.send_message() / execute_task()
  ├── Action Ledger    → on_tool_call, on_tool_result, on_step, on_error
  ├── File Browser     → workspace directory, refreshed on tool results
  ├── File Preview     → Rich syntax highlighting
  ├── Confirm Dialog   → confirm_callback (destructive=True)
  ├── Provider Switch  → Nexus provider routing + key detection
  └── Footer Stats     → TaskResult.tokens_used, .cost, .files_created

Nexus SDK (what powers it)
  ├── UnifiedAIWrapper    6 providers, auto key detection
  ├── ToolExecutor        8 built-in tools + @tool custom
  ├── Router              7 strategies, auto task classification
  ├── ExecutionLog        16 event types, JSON export
  ├── RetryHandler        circuit breaker + 4 retry configs
  ├── RateLimiter         token bucket, sliding window
  └── MCPManager          filesystem, github, memory, postgres...
```

---

## The Demo

1. Terminal opens. `python app.py` launches. Three panels appear.
2. You type: **"Build a Flask app with user authentication and SQLite"**
3. Chat panel: AI responds, starts working.
4. Action ledger scrolls — `create_file: app.py`, `create_file: models.py`, `create_file: requirements.txt`
5. File browser: files appear one by one. The tree grows in real-time.
6. Click `app.py` — full source code in the preview pane.
7. Ledger: `execute_command: pytest` → ❌ 1 failed
8. Ledger: `edit_file: app.py` → ✅ fixed
9. Ledger: `execute_command: pytest` → ✅ 4 passed
10. Footer: **8 files │ 3,847 tokens │ $0.04 │ 12 tool calls**

One sentence in. Eight files out. Watched it happen.

---

## What Deuce Is NOT

- **Not a code editor** — use your editor for editing. Deuce is for watching.
- **Not a web app** — Nexus has `ui.py` for that. Deuce lives in the terminal.
- **Not a multi-agent framework** — one agent, governed, transparent.
- **Not rebuilding Nexus** — Deuce is a surface, not an engine.

---

## Common Issues

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: nexus` | Run `pip install -r requirements.txt` |
| No providers available | Add at least one API key to `.env` |
| Ollama not connecting | Start Ollama: `ollama serve` then `ollama pull llama3.2` |
| Terminal looks broken | Make sure your terminal supports 256 colors and Unicode |
| Files not appearing | Check that the workspace directory exists and is writable |

---

## Name

**Deuce** — the second thing built on the Nexus SDK. The ace is the engine. The deuce is what you play with it.

---

<div align="center">

**Built on the [Nexus Connector](https://github.com/Clark-Wallace/The-Nexus-Connector)** — the governed AI execution SDK.

Stop guessing what the AI did. **Watch it happen.**

</div>
# Deuce
