"""ModelAdapter interface — STUB only in Phase 1 (CLAUDE.md §7, §10).

Defines the provider-agnostic boundary between the harness and a model. Phase 1 ships
only the interface and its message/response types; **no provider SDK is imported and
no model API is ever called**. Concrete adapters (and the model-backed agent that uses
them) arrive in Phase 2.

A model-backed agent will, each round, render its observation into a chat prompt
(system prompt from the active condition plus the market brief and history), call
``ModelAdapter.complete``, and parse the returned text into an ``Action``. The adapter
abstracts only the model call, so the rest of the harness stays provider-agnostic.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

Role = Literal["system", "user", "assistant"]


class ChatMessage(BaseModel):
    """A single provider-agnostic chat message."""

    model_config = ConfigDict(frozen=True)

    role: Role
    content: str


class ModelResponse(BaseModel):
    """A provider-agnostic model response.

    Attributes:
        text: The assistant's text output (parsed by the agent into an Action).
        model_id: The model that produced it.
        raw: Provider-specific payload, retained verbatim for the transcript.
    """

    model_config = ConfigDict(frozen=True)

    text: str
    model_id: str
    raw: dict[str, Any] = Field(default_factory=dict)


@runtime_checkable
class ModelAdapter(Protocol):
    """The interface a Phase 2 model provider must implement.

    Implementations are intentionally absent in Phase 1 (no provider is wired). The
    protocol is ``runtime_checkable`` so tests can assert conformance without a model.
    """

    model_id: str

    def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> ModelResponse:
        """Return the model's completion for a chat ``messages`` sequence."""
        ...
