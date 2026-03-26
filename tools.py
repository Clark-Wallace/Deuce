"""
Deuce project tools — @tool functions that give the AI project memory.

These tools write structured data to .deuce/ in the workspace.
The system prompt loader reads them back before every turn,
injecting project state into the AI's context.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from textwrap import dedent

from nexus import tool

# These get set by the app before registering tools
_workspace: str = "./workspace"


def set_workspace(workspace: str) -> None:
    global _workspace
    _workspace = workspace


def _deuce_dir() -> Path:
    d = Path(_workspace) / ".deuce"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _stories_dir() -> Path:
    d = _deuce_dir() / "stories"
    d.mkdir(exist_ok=True)
    return d


# ── Context Tool ─────────────────────────────────────────

@tool(description="Store project context — decisions, constraints, tech choices. Call this to remember something about the project. Keys: project, framework, database, auth, style, constraint, or any custom key.")
def context(key: str, value: str) -> str:
    """Store a project context entry.

    Args:
        key: Context key (e.g. "framework", "database", "auth", "constraint")
        value: Context value (e.g. "Flask", "SQLite", "JWT with refresh tokens")
    """
    path = _deuce_dir() / "context.json"
    data = {}
    if path.exists():
        data = json.loads(path.read_text())

    data[key] = {
        "value": value,
        "updated": datetime.now().isoformat(),
    }
    path.write_text(json.dumps(data, indent=2))
    return f"Context saved: {key} = {value}"


# ── User Story Tool ──────────────────────────────────────

@tool(description="Capture a user story — a structured requirement for the project. Call this to record what a user needs before building.")
def user_story(as_a: str, i_want: str, so_that: str) -> str:
    """Capture a user story.

    Args:
        as_a: The user role (e.g. "a registered user")
        i_want: What the user wants (e.g. "to save recipes to my favorites")
        so_that: Why they want it (e.g. "I can find them quickly later")
    """
    stories_dir = _stories_dir()
    existing = list(stories_dir.glob("story_*.json"))
    idx = len(existing) + 1

    story = {
        "id": idx,
        "as_a": as_a,
        "i_want": i_want,
        "so_that": so_that,
        "status": "pending",
        "created": datetime.now().isoformat(),
    }

    path = stories_dir / f"story_{idx:03d}.json"
    path.write_text(json.dumps(story, indent=2))
    return f"Story #{idx}: As {as_a}, I want {i_want}, so that {so_that}"


# ── Plan Tool ────────────────────────────────────────────

@tool(description="Create a build plan — break a task into ordered steps before executing. Call this after capturing context and stories, before building.")
def plan(task: str, steps: str) -> str:
    """Create a build plan.

    Args:
        task: High-level description of what to build
        steps: Numbered steps, one per line (e.g. "1. Set up project structure\\n2. Create models\\n3. Build API routes")
    """
    path = _deuce_dir() / "plan.md"

    content = f"# Build Plan\n\n"
    content += f"**Task:** {task}\n\n"
    content += f"**Created:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
    content += f"## Steps\n\n"

    for line in steps.strip().split("\n"):
        line = line.strip()
        if line:
            # Add checkbox if not already present
            if not line.startswith("- ["):
                # Strip leading number/dot
                cleaned = line.lstrip("0123456789.-) ").strip()
                content += f"- [ ] {cleaned}\n"
            else:
                content += f"{line}\n"

    path.write_text(content)
    return f"Plan created: {task}"


# ── Review Tool ──────────────────────────────────────────

@tool(description="Review the project — compare what was built against the user stories and plan. Call this after building to check completeness.")
def review() -> str:
    """Review project completeness against stories and plan."""
    result_parts = []

    # Load context
    ctx_path = _deuce_dir() / "context.json"
    if ctx_path.exists():
        ctx = json.loads(ctx_path.read_text())
        result_parts.append("## Context")
        for k, v in ctx.items():
            result_parts.append(f"- {k}: {v['value']}")
    else:
        result_parts.append("## Context\nNo context captured yet.")

    # Load stories
    stories_dir = _stories_dir()
    story_files = sorted(stories_dir.glob("story_*.json"))
    if story_files:
        result_parts.append("\n## User Stories")
        for sf in story_files:
            s = json.loads(sf.read_text())
            status = "✅" if s.get("status") == "done" else "⬜"
            result_parts.append(
                f"{status} #{s['id']}: As {s['as_a']}, I want {s['i_want']}, so that {s['so_that']}"
            )
    else:
        result_parts.append("\n## User Stories\nNo stories captured yet.")

    # Load plan
    plan_path = _deuce_dir() / "plan.md"
    if plan_path.exists():
        result_parts.append(f"\n## Plan\n{plan_path.read_text()}")
    else:
        result_parts.append("\n## Plan\nNo plan created yet.")

    # List workspace files (excluding .deuce)
    workspace = Path(_workspace)
    files = [
        str(f.relative_to(workspace))
        for f in workspace.rglob("*")
        if f.is_file() and ".deuce" not in f.parts
    ]
    if files:
        result_parts.append(f"\n## Files Built ({len(files)})")
        for f in sorted(files):
            result_parts.append(f"- {f}")
    else:
        result_parts.append("\n## Files Built\nNone yet.")

    return "\n".join(result_parts)


# ── Complete Story Tool ──────────────────────────────────

@tool(description="Mark a user story as complete. Call this after building a feature that fulfills a story.")
def complete_story(story_id: int) -> str:
    """Mark a user story as done.

    Args:
        story_id: The story number to mark complete
    """
    path = _stories_dir() / f"story_{story_id:03d}.json"
    if not path.exists():
        return f"Story #{story_id} not found"

    story = json.loads(path.read_text())
    story["status"] = "done"
    story["completed"] = datetime.now().isoformat()
    path.write_text(json.dumps(story, indent=2))
    return f"Story #{story_id} marked complete"


# ── Collect all Deuce tools ──────────────────────────────

DEUCE_TOOLS = [context, user_story, plan, review, complete_story]
