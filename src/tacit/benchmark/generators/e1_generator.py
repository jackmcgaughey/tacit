"""Seeded E1 instance generator and dev/heldout split assignment (CLAUDE.md §3).

Perturbs per-firm parameters to defeat memorisation while keeping the game
interior and solvable, caches the computed pᴺ/pᴹ on each instance, and assigns
a deterministic split label by hashing the instance seed.

Scaffolded in Milestone 1; implemented in Milestone 3.
"""
