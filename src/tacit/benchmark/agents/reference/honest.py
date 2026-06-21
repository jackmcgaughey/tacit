"""The honest (competitive) reference agent (CLAUDE.md §5)."""

from __future__ import annotations

from tacit.benchmark.agents.base import Action, Observation
from tacit.benchmark.agents.reference.base import ReferenceAgent


class HonestAgent(ReferenceAgent):
    """Prices at the competitive Bertrand-Nash benchmark ``p^N`` every round.

    Calibration target: an all-honest population yields ``CI ~ 0`` (CLAUDE.md §5, §8).
    """

    def act(self, obs: Observation) -> Action:
        """Return the competitive price, ignoring the observation."""
        return Action(price=self.own_nash)
