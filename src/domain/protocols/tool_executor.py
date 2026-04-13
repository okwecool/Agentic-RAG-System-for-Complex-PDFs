"""Tool execution protocol."""

from typing import Any, Protocol


class ToolExecutor(Protocol):
    def name(self) -> str:
        """Tool name."""

    def description(self) -> str:
        """Tool description."""

    def invoke(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Invoke the tool with structured arguments."""

