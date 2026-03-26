"""Nexus SDK integration — wires NexusConnector hooks to Deuce widgets."""

import os
import asyncio
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

from nexus import NexusConnector
from nexus.core.base_connector import AIProvider
from tools import DEUCE_TOOLS, set_workspace
from prompt import build_system_prompt


KEY_MAP = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "google": "GOOGLE_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "xai": "XAI_API_KEY",
}

PROVIDER_NAMES = {
    "anthropic": "Anthropic Claude",
    "openai": "OpenAI",
    "google": "Google Gemini",
    "deepseek": "DeepSeek",
    "xai": "xAI Grok",
    "ollama": "Ollama (Local)",
}


def get_available_providers() -> dict[str, str]:
    """Return {provider_id: api_key} for all configured providers."""
    available = {}
    for prov, env_var in KEY_MAP.items():
        key = os.getenv(env_var)
        if key:
            available[prov] = key
    available["ollama"] = ""
    return available


def detect_default_provider() -> tuple[Optional[str], Optional[str]]:
    """Pick the first available provider."""
    default = os.getenv("NEXUS_DEFAULT_PROVIDER")
    if default and default in KEY_MAP:
        key = os.getenv(KEY_MAP[default])
        if key:
            return default, key

    for prov, env_var in KEY_MAP.items():
        key = os.getenv(env_var)
        if key:
            return prov, key
    return None, None


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

        self.available_providers = get_available_providers()
        provider, api_key = detect_default_provider()
        self.current_provider = provider
        self.current_api_key = api_key
        self._connector: Optional[NexusConnector] = None

        # Set workspace for Deuce tools
        set_workspace(workspace)

    def _build_connector(self) -> NexusConnector:
        from nexus.core.base_connector import Message as NexusMessage

        connector = NexusConnector(
            provider=self.current_provider,
            api_key=self.current_api_key,
            workspace=self.workspace,
            max_iterations=20,
            tools=DEUCE_TOOLS,
            on_tool_call=self._on_tool_call,
            on_tool_result=self._on_tool_result,
            on_step=self._on_step,
            on_error=self._on_error,
            on_provider_switch=self._on_provider_switch,
            confirm_callback=self._confirm_callback,
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
        """Send a chat message."""
        return await self.connector.send_message(message)

    async def execute_task(self, task: str) -> object:
        """Execute an autonomous task."""
        return await self.connector.execute_task(task)

    def switch_provider(self, provider_id: str) -> bool:
        """Switch to a different provider."""
        if provider_id not in self.available_providers:
            return False
        self.current_provider = provider_id
        self.current_api_key = self.available_providers[provider_id]
        self._connector = None  # rebuild on next use
        return True

    def clear_history(self) -> None:
        """Clear conversation history."""
        if self._connector:
            self._connector.clear_history()

    @property
    def model_info(self) -> dict:
        return self.connector.model_info

    @property
    def provider_display_name(self) -> str:
        return PROVIDER_NAMES.get(self.current_provider, self.current_provider or "None")
