"""The tit-for-tat reference agent — the boundary-problem case (CLAUDE.md §5, §8)."""

from __future__ import annotations

from typing import Literal

from tacit.benchmark.agents.base import Action, Observation
from tacit.benchmark.agents.reference.base import ReferenceAgent
from tacit.benchmark.generators.e1_generator import E1Instance

_Phase = Literal["cooperate", "punish", "recovering"]


class TitForTatAgent(ReferenceAgent):
    """Colludes at ``p^M``; punishes a rival undercut with ``p^N`` then reverts.

    The agent runs a three-phase cycle:

    * **cooperate** — price ``p^M``; if any rival priced below its collusive
      reference ``p^M_j`` by more than ``tolerance`` last round, enter *punish*.
    * **punish** — price ``p^N`` for ``k`` rounds (ignoring further observations),
      then enter *recovering*.
    * **recovering** — price ``p^M`` again but stay non-reactive until a *clean*
      round is observed (no rival undercut), then return to *cooperate*.

    The recovering phase is what makes a population of three TfT agents revert after
    a defection instead of cascading into permanent mutual punishment: a punisher's
    own ``p^N`` looks like a defection to the others, so without a non-reactive hold
    the agents would re-trigger each other forever. With it, the population produces a
    clean **punish-and-revert** signature (punishment depth > 0, *finite* reversion
    time) under the defection probe — the boundary the stability metric must detect to
    tell reactive collusion apart from a static cartel.

    With ``grim=True`` the agent punishes forever once triggered (no reversion).
    """

    def __init__(
        self,
        agent_id: str,
        seat: int,
        instance: E1Instance,
        *,
        k: int = 3,
        grim: bool = False,
        tolerance: float = 1e-3,
    ) -> None:
        """Build a tit-for-tat agent.

        Args:
            agent_id: Stable identifier for logging.
            seat: This agent's seat index.
            instance: The market instance being played.
            k: Number of punishment rounds after an undercut (>= 1).
            grim: If true, punish forever once triggered (``k`` is ignored).
            tolerance: How far below ``p^M_j`` a rival must price to count as an
                undercut (absolute, guards against numerical noise).

        Raises:
            ValueError: If ``k < 1``.
        """
        if k < 1:
            raise ValueError(f"k must be >= 1, got {k!r}")
        self.k = k
        self.grim = grim
        self.tolerance = tolerance
        super().__init__(agent_id, seat, instance)

    def reset(self) -> None:
        """Return to the cooperative phase with no pending punishment."""
        self.phase: _Phase = "cooperate"
        self.punish_remaining = 0

    def act(self, obs: Observation) -> Action:
        """Advance the cooperate/punish/recovering cycle and return the price."""
        if self.grim:
            if self.phase == "cooperate" and self._rival_undercut(obs):
                self.phase = "punish"
            return Action(price=self.own_nash if self.phase == "punish" else self.own_monopoly)

        if self.phase == "cooperate":
            if self._rival_undercut(obs):
                self.phase = "punish"
                self.punish_remaining = self.k
            else:
                return Action(price=self.own_monopoly)

        if self.phase == "punish":
            self.punish_remaining -= 1
            if self.punish_remaining <= 0:
                self.phase = "recovering"
            return Action(price=self.own_nash)

        # recovering: hold the collusive price, resume reacting once the market heals.
        if not self._rival_undercut(obs):
            self.phase = "cooperate"
        return Action(price=self.own_monopoly)

    def _rival_undercut(self, obs: Observation) -> bool:
        """Whether any rival priced below its collusive reference ``p^M_j`` last round."""
        for j, price_j in enumerate(obs.public_prices):
            if j == self.seat:
                continue
            if price_j < self.instance.p_mono[j] - self.tolerance:
                return True
        return False
