"""Run-directory writer and JSONL transcript schema (CLAUDE.md §7).

One run dir per invocation: ``runs/<UTC-timestamp>__<config-hash>/`` containing
``config.snapshot.yaml``, ``env_version.txt``, ``transcript.jsonl`` (one record per
round), and ``scores.json``. Nothing in ``runs/`` is ever edited by hand.

Scaffolded in Milestone 1; implemented in Milestone 7.
"""
