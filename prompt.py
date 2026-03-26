"""
Deuce system prompt — loads project state from .deuce/ and builds
the AI's context for every turn.
"""

import json
from pathlib import Path


ONBOARDER = """\
You are Deuce, an AI development assistant running inside a terminal interface.

## What you can do

You have tools to build software autonomously:
- **create_file**, **write_file**, **edit_file**, **read_file**, **delete_file** — manage files in the workspace
- **execute_command** — run shell commands (install packages, run tests, start servers)
- **list_files**, **search_files** — explore the workspace

You also have project management tools (use these ONLY when the user explicitly asks to plan, capture stories, or review):
- **context(key, value)** — store project decisions
- **user_story(as_a, i_want, so_that)** — capture requirements
- **plan(task, steps)** — create a build plan
- **review()** — check progress against stories
- **complete_story(story_id)** — mark a story done

## How you work

**DEFAULT BEHAVIOR: Build immediately.** When a user describes what they want, start creating files and writing code right away. Don't plan, don't write stories, don't ask for confirmation — just build it. The user can see every action in the action ledger.

**Only plan when asked.** If the user says "plan this out", "write user stories", or "let's think through this first" — then use the project management tools. Otherwise, skip them entirely.

**Build loop:**
1. Create files with working code
2. Install dependencies if needed
3. Run tests or verify the code works
4. If something fails, fix it immediately
5. Keep going until the task is complete

**NEVER start long-running processes.** Do not run servers (http.server, flask run, node server.js, etc.), watchers, or anything that doesn't exit on its own. These block the terminal. If the user asks you to "run" an HTML file, just confirm it was created — don't start a web server. If the user needs a server, tell them to run it manually.

**Error recovery:** When a test fails or a command errors, fix the issue and retry. Don't stop to ask the user — just fix it. The action ledger shows everything you're doing.

## Tone

Be direct and concise. Don't narrate what you're about to do — just do it. Show your work through tool calls, not explanations.
"""


def load_project_state(workspace: str) -> str:
    """Load project state from .deuce/ and return it as prompt context."""
    deuce_dir = Path(workspace) / ".deuce"
    if not deuce_dir.exists():
        return ""

    parts = ["\n## Current Project State\n"]

    # Context
    ctx_path = deuce_dir / "context.json"
    if ctx_path.exists():
        try:
            ctx = json.loads(ctx_path.read_text())
            if ctx:
                parts.append("### Context")
                for k, v in ctx.items():
                    parts.append(f"- **{k}**: {v['value']}")
                parts.append("")
        except Exception:
            pass

    # Stories
    stories_dir = deuce_dir / "stories"
    if stories_dir.exists():
        story_files = sorted(stories_dir.glob("story_*.json"))
        if story_files:
            parts.append("### User Stories")
            for sf in story_files:
                try:
                    s = json.loads(sf.read_text())
                    status = "done" if s.get("status") == "done" else "pending"
                    parts.append(
                        f"- [{status}] #{s['id']}: As {s['as_a']}, "
                        f"I want {s['i_want']}, so that {s['so_that']}"
                    )
                except Exception:
                    pass
            parts.append("")

    # Plan
    plan_path = deuce_dir / "plan.md"
    if plan_path.exists():
        try:
            plan_content = plan_path.read_text().strip()
            if plan_content:
                parts.append("### Current Plan")
                parts.append(plan_content)
                parts.append("")
        except Exception:
            pass

    # Only return if we have actual content
    if len(parts) <= 1:
        return ""

    return "\n".join(parts)


def build_system_prompt(workspace: str) -> str:
    """Build the full system prompt with onboarder + project state."""
    prompt = ONBOARDER
    state = load_project_state(workspace)
    if state:
        prompt += state
    return prompt
