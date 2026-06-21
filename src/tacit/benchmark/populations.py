"""Population tiers and the agent registry (CLAUDE.md §1, §5).

Phase 1 has a single tier of population members: **Tier R**, the deterministic
scripted reference agents. This module maps the declarative agent specs used in
experiment configs (e.g. ``"scripted:cartel"``) to concrete agent classes, so the
orchestrator can build a population from a YAML cell without importing each agent.

The richer cross-play composition sweep is explicitly out of scope for Phase 1
(CLAUDE.md §10); this module provides only the registry and a factory.
"""

from __future__ import annotations

from tacit.benchmark.agents.reference.base import ReferenceAgent
from tacit.benchmark.agents.reference.cartel import CartelAgent
from tacit.benchmark.agents.reference.defector import DefectorAgent
from tacit.benchmark.agents.reference.honest import HonestAgent
from tacit.benchmark.agents.reference.recruiter import RecruiterAgent
from tacit.benchmark.agents.reference.tit_for_tat import TitForTatAgent
from tacit.benchmark.generators.e1_generator import E1Instance

# Tier R: the scripted reference agents (CLAUDE.md §5), keyed by their spec name.
_REFERENCE_AGENTS: dict[str, type[ReferenceAgent]] = {
    "honest": HonestAgent,
    "cartel": CartelAgent,
    "tit_for_tat": TitForTatAgent,
    "defector": DefectorAgent,
    "recruiter": RecruiterAgent,
}

#: The names of the Tier R reference agents.
TIER_R: tuple[str, ...] = tuple(_REFERENCE_AGENTS)

#: Prefix marking a scripted (non-model) agent spec.
SCRIPTED_PREFIX = "scripted"

__all__ = ["SCRIPTED_PREFIX", "TIER_R", "make_agent", "reference_agent_names"]


def reference_agent_names() -> tuple[str, ...]:
    """Return the registered Tier R agent names."""
    return TIER_R


def make_agent(
    spec: str,
    *,
    agent_id: str,
    seat: int,
    instance: E1Instance,
) -> ReferenceAgent:
    """Build a scripted reference agent from a declarative spec.

    Args:
        spec: An agent spec of the form ``"scripted:<name>"`` (e.g.
            ``"scripted:cartel"``). ``<name>`` must be a Tier R agent.
        agent_id: Stable identifier for logging.
        seat: The agent's seat index in the population.
        instance: The market instance being played.

    Returns:
        A constructed reference agent (with default parameters for its type).

    Raises:
        ValueError: If ``spec`` is not a ``"scripted:<name>"`` spec, or names an
            unknown agent. (Model-backed specs are a Phase 2 concern.)
    """
    tier, sep, name = spec.partition(":")
    if sep != ":" or tier != SCRIPTED_PREFIX:
        raise ValueError(f"unsupported agent spec {spec!r}; expected '{SCRIPTED_PREFIX}:<name>'")
    try:
        agent_cls = _REFERENCE_AGENTS[name]
    except KeyError:
        raise ValueError(
            f"unknown scripted agent {name!r}; known: {sorted(_REFERENCE_AGENTS)}"
        ) from None
    return agent_cls(agent_id=agent_id, seat=seat, instance=instance)
