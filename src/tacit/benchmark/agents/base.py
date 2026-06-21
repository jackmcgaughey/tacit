"""Agent protocol and the Message/Action/Observation models (CLAUDE.md §7).

These are the model-agnostic data types exchanged between the environment and the
agents. They are frozen pydantic models so an observation cannot be mutated by an
agent (which keeps episodes deterministic) and so they serialise cleanly into the
verbatim transcript. Sequence fields use tuples rather than lists for the same
immutability reason.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict


class Message(BaseModel):
    """A single message on a communication channel.

    Attributes:
        sender: Seat label of the sender (e.g. ``"seat_0"``).
        to: Seat label of the recipient, or ``None`` for a broadcast within the
            sender's channel.
        text: The message body.
    """

    model_config = ConfigDict(frozen=True)

    sender: str
    to: str | None
    text: str


class Action(BaseModel):
    """An agent's decision for one round: a price and an optional message.

    Attributes:
        price: The submitted price (clipped to the legal band by the environment).
        message: Optional message text; ignored when the comms regime is ``none``
            or when the sender has no channel.
    """

    model_config = ConfigDict(frozen=True)

    price: float
    message: str | None = None


class Observation(BaseModel):
    """What an agent sees at the start of a round (CLAUDE.md §3, §7).

    Own profit is private; rivals' prices from the previous round are public, which
    is what enables tacit coordination through observed prices.

    Attributes:
        round: Zero-based index of the round about to be played.
        own_last_price: The agent's own clipped price last round, or ``None`` in
            round 0.
        own_last_profit: The agent's own (private) profit last round, or ``None`` in
            round 0.
        public_prices: Every firm's clipped price from the previous round, in seat
            order; empty in round 0.
        inbox: Messages delivered to this agent (sent in the previous round).
        market_brief: Natural-language description of the market for model agents
            (scripted agents ignore it).
    """

    model_config = ConfigDict(frozen=True)

    round: int
    own_last_price: float | None
    own_last_profit: float | None
    public_prices: tuple[float, ...]
    inbox: tuple[Message, ...]
    market_brief: str


@runtime_checkable
class Agent(Protocol):
    """A population member: maps an observation to an action each round (CLAUDE.md §7)."""

    agent_id: str

    def reset(self) -> None:
        """Reset any per-episode internal state."""
        ...

    def act(self, obs: Observation) -> Action:
        """Choose an action for the round described by ``obs``."""
        ...
