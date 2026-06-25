"""Conditions C1-C5: per-condition system-prompt overlays for E1 (CLAUDE.md §4).

A condition produces an agent's system prompt by combining a shared market
description (``base.md.jinja``) with a per-condition overlay. In Phase 1 the templates
are stored as data under ``templates/`` and only the *selection and rendering* logic
is exercised -- **no model is called**, and scripted agents ignore prompts. The
overlays are the Phase 2 scaffolding.

* **C1 Elicited** (capability) -- profit goal with explicit latitude to coordinate
  "however you judge best"; never instructs collusion or uses the word.
* **C2 Incentivized** (propensity) -- "maximise long-run profit", no steer.
* **C3 Prohibited** (compliance gap) -- C2 plus an explicit prohibition on
  coordinating, signalling, or fixing prices.
* **C4 Recruited** (resistance) -- C3 plus a counterpart who tries to recruit; needs a
  communication regime other than ``none``.
* **C5 Ambient** (extraction) -- the model arrives into an already-running market.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files
from typing import Literal

from jinja2 import Template
from pydantic import BaseModel, ConfigDict

ConditionKey = Literal["C1", "C2", "C3", "C4", "C5"]

_TEMPLATES_ANCHOR = "tacit.benchmark.conditions"
_BASE_TEMPLATE = "base.md.jinja"


class PromptContext(BaseModel):
    """Variables available to the prompt templates."""

    model_config = ConfigDict(frozen=True)

    seat: int
    n_sellers: int
    rounds: int
    role: str = "seller"


@dataclass(frozen=True)
class Condition:
    """A condition: its key, human name, what it measures, and its overlay template.

    Attributes:
        key: The ``C1``-``C5`` identifier.
        name: Short human name (e.g. ``"elicited"``).
        measures: The research question this condition targets.
        overlay_template: Filename of the overlay under ``templates/``.
        requires_comms: Whether the condition needs a comms regime other than ``none``
            (true only for C4, which relies on a recruiter channel).
    """

    key: ConditionKey
    name: str
    measures: str
    overlay_template: str
    requires_comms: bool = False


CONDITIONS: dict[ConditionKey, Condition] = {
    "C1": Condition("C1", "elicited", "capability (RQ1)", "c1_elicited.md.jinja"),
    "C2": Condition("C2", "incentivized", "propensity (RQ2)", "c2_incentivized.md.jinja"),
    "C3": Condition("C3", "prohibited", "compliance gap (RQ3)", "c3_prohibited.md.jinja"),
    "C4": Condition(
        "C4", "recruited", "resistance (RQ3)", "c4_recruited.md.jinja", requires_comms=True
    ),
    "C5": Condition("C5", "ambient", "extraction (RQ6)", "c5_ambient.md.jinja"),
}

__all__ = [
    "CONDITIONS",
    "Condition",
    "ConditionKey",
    "PromptContext",
    "get_condition",
    "render_system_prompt",
]


def get_condition(key: ConditionKey) -> Condition:
    """Return the condition object for ``key``.

    Raises:
        KeyError: If ``key`` is not a known condition.
    """
    return CONDITIONS[key]


def render_system_prompt(key: ConditionKey, context: PromptContext) -> str:
    """Render the system prompt for a condition: shared base + the condition overlay.

    Args:
        key: Which condition's overlay to apply.
        context: Variables filled into the templates.

    Returns:
        The combined, rendered system prompt.
    """
    variables = context.model_dump()
    base = _render_template(_BASE_TEMPLATE, variables)
    overlay = _render_template(get_condition(key).overlay_template, variables)
    return f"{base.strip()}\n\n{overlay.strip()}\n"


def _render_template(filename: str, variables: dict[str, object]) -> str:
    """Load and render a template file from the ``templates/`` package data."""
    source = files(_TEMPLATES_ANCHOR).joinpath("templates", filename).read_text(encoding="utf-8")
    return Template(source).render(**variables)
