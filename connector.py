"""Nexus SDK integration — wires NexusConnector hooks to Deuce widgets."""

import os
import re
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

from dotenv import load_dotenv
load_dotenv()

from nexus import NexusConnector
from tools import DEUCE_TOOLS, set_workspace
from prompt import build_system_prompt

# ── Provider configuration ────────────────────────────────

# Native Nexus providers — detected by legacy env var names
NATIVE_PROVIDERS = {
    "anthropic": {"env": "ANTHROPIC_API_KEY", "name": "Anthropic Claude"},
    "openai":    {"env": "OPENAI_API_KEY",    "name": "OpenAI"},
    "google":    {"env": "GOOGLE_API_KEY",     "name": "Google Gemini"},
    "deepseek":  {"env": "DEEPSEEK_API_KEY",   "name": "DeepSeek"},
    "xai":       {"env": "XAI_API_KEY",        "name": "xAI Grok"},
}


@dataclass
class ProviderConfig:
    """Everything needed to connect to a provider."""
    id: str                          # unique key for the dropdown
    name: str                        # display name
    api_key: str = ""
    provider_type: str = ""          # nexus provider string ("anthropic", "openai", etc.)
    base_url: str | None = None      # for openai-compatible providers
    model: str | None = None         # override default model


def discover_providers() -> dict[str, ProviderConfig]:
    """
    Scan environment for providers. Two sources:

    1. Legacy env vars (ANTHROPIC_API_KEY, OPENAI_API_KEY, etc.)
       → detected automatically for native Nexus providers

    2. Dynamic AI_PROVIDER_# pattern:
       AI_PROVIDER_1=anthropic
       AI_PROVIDER_1_KEY=sk-ant-...
       AI_PROVIDER_1_NAME=Anthropic Claude       (optional, auto-detected for native)
       AI_PROVIDER_1_MODEL=claude-sonnet-4-...    (optional)

       AI_PROVIDER_2=openai-compatible
       AI_PROVIDER_2_KEY=...
       AI_PROVIDER_2_NAME=MiniMax M2.7            (required for openai-compatible)
       AI_PROVIDER_2_BASE_URL=https://api.minimax.io/v1  (required for openai-compatible)
       AI_PROVIDER_2_MODEL=MiniMax-M2.7           (optional)

    Dynamic providers override legacy if both define the same provider.
    """
    providers: dict[str, ProviderConfig] = {}

    # ── 1. Legacy env vars ──
    for prov_type, info in NATIVE_PROVIDERS.items():
        key = os.getenv(info["env"])
        if key:
            providers[prov_type] = ProviderConfig(
                id=prov_type,
                name=info["name"],
                api_key=key,
                provider_type=prov_type,
            )

    # ── 2. Dynamic AI_PROVIDER_# pattern ──
    # Find all numbered providers
    numbered = set()
    for var in os.environ:
        m = re.match(r"^AI_PROVIDER_(\d+)$", var)
        if m:
            numbered.add(int(m.group(1)))

    for n in sorted(numbered):
        prefix = f"AI_PROVIDER_{n}"
        prov_type = os.getenv(prefix, "").strip().lower()
        api_key = os.getenv(f"{prefix}_KEY", "").strip()
        display_name = os.getenv(f"{prefix}_NAME", "").strip()
        base_url = os.getenv(f"{prefix}_BASE_URL", "").strip() or None
        model = os.getenv(f"{prefix}_MODEL", "").strip() or None

        if not prov_type or not api_key:
            continue

        # Native provider (anthropic, openai, google, etc.)
        if prov_type in NATIVE_PROVIDERS:
            pid = prov_type
            name = display_name or NATIVE_PROVIDERS[prov_type]["name"]
            providers[pid] = ProviderConfig(
                id=pid, name=name, api_key=api_key,
                provider_type=prov_type, model=model,
            )

        # OpenAI-compatible provider (minimax, together, groq, etc.)
        elif prov_type == "openai-compatible":
            if not display_name or not base_url:
                continue  # name and base_url required for custom providers
            pid = f"custom_{n}"
            providers[pid] = ProviderConfig(
                id=pid, name=display_name, api_key=api_key,
                provider_type="openai", base_url=base_url, model=model,
            )

    # ── 3. Ollama (always available, no key) ──
    providers["ollama"] = ProviderConfig(
        id="ollama", name="Ollama (Local)",
        provider_type="ollama",
    )

    return providers


def detect_default_provider(
    providers: dict[str, ProviderConfig],
) -> str:
    """Pick the default provider. Priority: env setting > first cloud > ollama."""
    default = os.getenv("NEXUS_DEFAULT_PROVIDER", "").strip().lower()
    if default and default in providers:
        return default

    # First non-ollama provider
    for pid, cfg in providers.items():
        if pid != "ollama" and cfg.api_key:
            return pid

    return "ollama"


class DeuceConnector:
    """Wraps NexusConnector and exposes hooks for the TUI."""

    def __init__(
        self,
        workspace: str = "./workspace",
        on_tool_call=None,
        on_tool_result=None,
        on_step=None,
        on_error=None,
        on_provider_switch=None,
        confirm_callback=None,
    ):
        self.workspace = workspace
        self._on_tool_call = on_tool_call
        self._on_tool_result = on_tool_result
        self._on_step = on_step
        self._on_error = on_error
        self._on_provider_switch = on_provider_switch
        self._confirm_callback = confirm_callback

        # Discover all providers from env
        self.providers = discover_providers()
        self.current_provider = detect_default_provider(self.providers)
        self._connector: Optional[NexusConnector] = None

        # Set workspace for Deuce tools
        set_workspace(workspace)

    @property
    def available_providers(self) -> dict[str, str]:
        """Return {provider_id: api_key} for backwards compat with app.py."""
        return {pid: cfg.api_key for pid, cfg in self.providers.items()}

    @property
    def provider_display_name(self) -> str:
        cfg = self.providers.get(self.current_provider)
        return cfg.name if cfg else self.current_provider or "None"

    def _build_connector(self) -> NexusConnector:
        from nexus.core.base_connector import Message as NexusMessage

        cfg = self.providers[self.current_provider]
        kwargs = {}
        if cfg.base_url:
            kwargs["base_url"] = cfg.base_url
        if cfg.model:
            kwargs["model"] = cfg.model

        connector = NexusConnector(
            provider=cfg.provider_type,
            api_key=cfg.api_key,
            workspace=self.workspace,
            max_iterations=20,
            tools=DEUCE_TOOLS,
            on_tool_call=self._on_tool_call,
            on_tool_result=self._on_tool_result,
            on_step=self._on_step,
            on_error=self._on_error,
            on_provider_switch=self._on_provider_switch,
            confirm_callback=self._confirm_callback,
            **kwargs,
        )

        # Inject system prompt with project state
        system_prompt = build_system_prompt(self.workspace)
        connector.conversation_history.insert(
            0, NexusMessage(role="system", content=system_prompt)
        )

        return connector

    @property
    def connector(self) -> NexusConnector:
        if self._connector is None:
            self._connector = self._build_connector()
        return self._connector

    async def send_message(self, message: str) -> dict:
        """Send a single message. Tools auto-execute. Returns response dict."""
        return await self.connector.send_message(message)

    async def agent_loop(self, task: str, max_turns: int = 20):
        """Deuce's own agent loop — replaces Nexus execute_task.

        Uses send_message in a loop. The AI calls tools until it responds
        with text and no tool calls. No synthetic 'Continue' prompts.
        No completion heuristics. The model decides when it's done.

        Yields (turn, response) tuples so the caller can update the UI
        after each turn.
        """
        message = task
        for turn in range(max_turns):
            response = await self.connector.send_message(message)

            content = response.get("content", "")
            tool_calls = response.get("tool_calls", [])
            tool_results = response.get("tool_results", [])
            usage = response.get("usage", {})

            yield turn, response

            # If the AI used tools, there may be more work.
            # Send empty message to let it continue from tool results.
            if tool_calls or tool_results:
                message = ""
                continue

            # AI responded with text and no tools — done.
            if content:
                break

        # If we exhausted max_turns, the last yield already happened.

    async def execute_task(self, task: str) -> object:
        """Legacy execute_task — still available but agent_loop is preferred."""
        return await self.connector.execute_task(task)

    def switch_provider(self, provider_id: str) -> bool:
        """Switch to a different provider."""
        if provider_id not in self.providers:
            return False
        self.current_provider = provider_id
        self._connector = None  # rebuild on next use
        return True

    def clear_history(self) -> None:
        """Clear conversation history."""
        if self._connector:
            self._connector.clear_history()

    @property
    def model_info(self) -> dict:
        return self.connector.model_info
