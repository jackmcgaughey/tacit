"""Tests for the Phase 2 ModelAdapter interface stub (CLAUDE.md §9, §10).

Phase 1 ships only the interface; no provider is wired. These tests confirm the
message/response models and that the runtime-checkable protocol is satisfiable by a
trivial (non-model) implementation.
"""

from collections.abc import Sequence

import pytest
from pydantic import ValidationError

from tacit.adapters.base import ChatMessage, ModelAdapter, ModelResponse


def test_chat_message_and_response_models():
    message = ChatMessage(role="system", content="be a seller")
    assert message.role == "system"
    response = ModelResponse(text="1.50", model_id="stub")
    assert response.text == "1.50"
    assert response.raw == {}


def test_role_literal_rejects_unknown_role():
    with pytest.raises(ValidationError):
        ChatMessage(role="tool", content="x")  # type: ignore[arg-type]


def test_model_adapter_protocol_is_satisfiable_without_a_provider():
    class EchoAdapter:
        model_id = "echo"

        def complete(
            self,
            messages: Sequence[ChatMessage],
            *,
            temperature: float = 0.0,
            max_tokens: int | None = None,
        ) -> ModelResponse:
            return ModelResponse(text=messages[-1].content, model_id=self.model_id)

    adapter = EchoAdapter()
    assert isinstance(adapter, ModelAdapter)  # runtime-checkable protocol
    out = adapter.complete([ChatMessage(role="user", content="ping")])
    assert out.text == "ping" and out.model_id == "echo"
