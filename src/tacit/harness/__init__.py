"""The TACIT harness: the model-agnostic engine (orchestrator, logging, config, CLI).

Kept deliberately free of any model-provider coupling, because the same engine will
later run a customer-pointed product (CLAUDE.md §1).
"""
