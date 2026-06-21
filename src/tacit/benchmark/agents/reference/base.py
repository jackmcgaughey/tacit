"""Shared base for the Tier R scripted reference agents (CLAUDE.md §5).

Tier R agents are deterministic and prompt-ignoring: they ignore ``market_brief``
and decide purely from the numeric observation and the instance's cached benchmark
prices. They both calibrate the metrics and serve as fixed population members. Each
is constructed from the :class:`~tacit.benchmark.generators.e1_generator.E1Instance`
it plays in plus its seat, so it can read its own ``p^N``/``p^M`` and observe rivals'
prices; the environment does not hand out benchmarks.
"""

from __future__ import annotations

from tacit.benchmark.agents.base import Action, Observation
from tacit.benchmark.generators.e1_generator import E1Instance


class ReferenceAgent:
    """Base class for scripted reference agents.

    Subclasses implement :meth:`act`. State-carrying subclasses override
    :meth:`reset`, which is called once at construction and again by the
    orchestrator between episodes.
    """

    def __init__(self, agent_id: str, seat: int, instance: E1Instance) -> None:
        """Bind the agent to a seat in an instance and initialise its state.

        Args:
            agent_id: Stable identifier for logging.
            seat: This agent's seat index in ``[0, n_sellers)``.
            instance: The market instance being played (supplies the benchmarks).

        Raises:
            ValueError: If ``seat`` is outside ``[0, instance.n_sellers)``.
        """
        if not 0 <= seat < instance.n_sellers:
            raise ValueError(f"seat {seat} out of range for n_sellers={instance.n_sellers}")
        self.agent_id = agent_id
        self.seat = seat
        self.instance = instance
        self.reset()

    @property
    def own_nash(self) -> float:
        """This agent's competitive Bertrand-Nash benchmark price ``p^N_seat``."""
        return self.instance.p_nash[self.seat]

    @property
    def own_monopoly(self) -> float:
        """This agent's joint-profit (cartel) benchmark price ``p^M_seat``."""
        return self.instance.p_mono[self.seat]

    def reset(self) -> None:
        """Reset per-episode internal state (no-op for stateless agents)."""

    def act(self, obs: Observation) -> Action:
        """Choose an action for the round described by ``obs`` (subclass override)."""
        raise NotImplementedError
