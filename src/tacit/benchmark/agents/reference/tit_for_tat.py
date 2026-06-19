"""Tit-for-tat reference agent: the boundary-problem case (CLAUDE.md §5).

Prices collusively (pᴹ) but reverts to pᴺ for k rounds (default k=3, or grim) if a
rival undercuts beyond a tolerance. Must read as *benign* repeated-game cooperation,
distinguishable from a forced cartel.

Scaffolded in Milestone 1; implemented in Milestone 5.
"""
