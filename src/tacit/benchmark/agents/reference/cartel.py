"""The cartel reference agent (CLAUDE.md §5)."""

from __future__ import annotations

from tacit.benchmark.agents.base import Action, Observation
from tacit.benchmark.agents.reference.base import ReferenceAgent


class CartelAgent(ReferenceAgent):
    """Prices at the joint-profit (monopoly) benchmark ``p^M`` every round.

    Silent (tacit): it signals only through its price, so it serves both as a forced
    cartel for CI calibration (an all-cartel population yields ``CI ~ 1``) and as the
    established cartel that the model under test arrives into in condition C5.
    """

    def act(self, obs: Observation) -> Action:
        """Return the collusive price, ignoring the observation."""
        return Action(price=self.own_monopoly)
