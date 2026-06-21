"""The defector reference agent (CLAUDE.md §5)."""

from __future__ import annotations

from tacit.benchmark.agents.base import Action, Observation
from tacit.benchmark.agents.reference.base import ReferenceAgent
from tacit.benchmark.generators.e1_generator import E1Instance


class DefectorAgent(ReferenceAgent):
    """Always undercuts to (or just below) the competitive price ``p^N``.

    Used to break collusion and to exercise the punish-and-revert response of
    :class:`~tacit.benchmark.agents.reference.tit_for_tat.TitForTatAgent`. The
    submitted price is clipped to the legal band by the environment.
    """

    def __init__(
        self,
        agent_id: str,
        seat: int,
        instance: E1Instance,
        *,
        undercut: float = 0.0,
    ) -> None:
        """Build a defector that prices at ``p^N_seat - undercut``.

        Args:
            agent_id: Stable identifier for logging.
            seat: This agent's seat index.
            instance: The market instance being played.
            undercut: Amount to subtract from the competitive price (>= 0).

        Raises:
            ValueError: If ``undercut`` is negative.
        """
        if undercut < 0.0:
            raise ValueError(f"undercut must be non-negative, got {undercut!r}")
        self.undercut = undercut
        super().__init__(agent_id, seat, instance)

    def act(self, obs: Observation) -> Action:
        """Return the undercutting price, ignoring the observation."""
        return Action(price=self.own_nash - self.undercut)
