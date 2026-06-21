"""Tier R scripted reference agents (CLAUDE.md §5).

Deterministic and prompt-ignoring; they calibrate the metrics and serve as fixed
population members: honest, cartel, tit_for_tat, defector, recruiter.
"""

from tacit.benchmark.agents.reference.base import ReferenceAgent
from tacit.benchmark.agents.reference.cartel import CartelAgent
from tacit.benchmark.agents.reference.defector import DefectorAgent
from tacit.benchmark.agents.reference.honest import HonestAgent
from tacit.benchmark.agents.reference.recruiter import (
    PERSUASION_LADDER,
    LadderRung,
    RecruiterAgent,
)
from tacit.benchmark.agents.reference.tit_for_tat import TitForTatAgent

__all__ = [
    "PERSUASION_LADDER",
    "CartelAgent",
    "DefectorAgent",
    "HonestAgent",
    "LadderRung",
    "RecruiterAgent",
    "ReferenceAgent",
    "TitForTatAgent",
]
