"""Provider switcher — dropdown to change AI provider."""

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Select, Static
from textual.message import Message


class ProviderSwitcher(Horizontal):
    """Provider selection bar."""

    class ProviderChanged(Message):
        """User selected a new provider."""
        def __init__(self, provider_id: str) -> None:
            super().__init__()
            self.provider_id = provider_id

    def __init__(self, providers: dict[str, str], current: str, **kwargs):
        """
        Args:
            providers: {provider_id: display_name} for available providers
            current: currently active provider_id
        """
        super().__init__(**kwargs)
        self._providers = providers
        self._current = current

    def compose(self) -> ComposeResult:
        yield Static("Provider: ", id="provider-label")
        options = [(name, pid) for pid, name in self._providers.items()]
        yield Select(
            options,
            value=self._current,
            id="provider-select",
            allow_blank=False,
        )

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.value and event.value != self._current:
            self._current = event.value
            self.post_message(self.ProviderChanged(event.value))

    def set_provider(self, provider_id: str) -> None:
        self._current = provider_id
        select = self.query_one("#provider-select", Select)
        select.value = provider_id
