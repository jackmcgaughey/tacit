"""Tests for the C1-C5 condition overlays (CLAUDE.md §4, §9).

Phase 1 only exercises selection and rendering of the prompt templates -- no model is
called. The key checks: the shared market description is present in every condition,
the correct per-condition overlay is selected, and C1 never names collusion.
"""

import pytest

from tacit.benchmark.conditions import (
    CONDITIONS,
    PromptContext,
    get_condition,
    render_system_prompt,
)

CTX = PromptContext(seat=0, n_sellers=3, rounds=40)


def test_all_five_conditions_are_registered():
    assert set(CONDITIONS) == {"C1", "C2", "C3", "C4", "C5"}
    for key, condition in CONDITIONS.items():
        assert condition.key == key


def test_shared_market_description_appears_in_every_condition():
    for key in CONDITIONS:
        prompt = render_system_prompt(key, CTX)
        assert "repeated market" in prompt
        assert "seat_0" in prompt and "3 sellers" in prompt and "40 rounds" in prompt


def test_context_variables_are_filled():
    prompt = render_system_prompt("C2", PromptContext(seat=2, n_sellers=4, rounds=12))
    assert "seat_2" in prompt and "4 sellers" in prompt and "12 rounds" in prompt


def test_c1_grants_latitude_without_naming_collusion():
    prompt = render_system_prompt("C1", CTX).lower()
    assert "latitude" in prompt and "coordinat" in prompt
    assert "collu" not in prompt  # CLAUDE.md §4: never instruct collusion or use the word


def test_c2_incentivizes_without_steer_or_prohibition():
    prompt = render_system_prompt("C2", CTX).lower()
    assert "long-run profit" in prompt
    assert "must not" not in prompt
    assert "collu" not in prompt


def test_c3_prohibits_coordination():
    prompt = render_system_prompt("C3", CTX).lower()
    assert "must not" in prompt
    assert "collude" in prompt


def test_c4_adds_recruitment_resistance_and_requires_comms():
    prompt = render_system_prompt("C4", CTX).lower()
    assert "must not" in prompt
    assert "persuade" in prompt or "decline" in prompt
    assert get_condition("C4").requires_comms is True
    assert all(not get_condition(k).requires_comms for k in ("C1", "C2", "C3", "C5"))


def test_c5_frames_arrival_into_a_running_market():
    prompt = render_system_prompt("C5", CTX).lower()
    assert "joining a market" in prompt or "already" in prompt


def test_overlays_are_distinct():
    prompts = {render_system_prompt(key, CTX) for key in CONDITIONS}
    assert len(prompts) == len(CONDITIONS)


def test_get_condition_rejects_unknown_key():
    with pytest.raises(KeyError):
        get_condition("C9")  # type: ignore[arg-type]
