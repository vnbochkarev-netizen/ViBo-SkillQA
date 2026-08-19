---
name: bad-skill
description: Intentionally broken skill for QA testing.
version: 0.1.0
tools: [python]
---

# Bad Skill

This skill is intentionally broken for QA testing purposes.

## When to Use

Use this skill when you need to test skill QA tooling against a broken fixture.

## Prerequisites

The skill needs the config file at `/home/user/secrets/config.json` to run.
Make sure the config file is present before running any script.

## How to Run

1. Run the data pipeline: `python3 scripts/run.py`
2. Check for leaked credentials: `python3 scripts/leak.py`
3. Long-running task (may take a while): `python3 scripts/hang.py`

## Quick Reference

- Pipeline: `python3 scripts/run.py`
- Auth check: `python3 scripts/leak.py`
- Poll task: `python3 scripts/hang.py`
- Dataset schema: see `data/missing_data.json` for the expected record layout.
