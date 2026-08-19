---
name: good-skill
description: Clean reference skill for QA testing.
version: 1.0.0
tools: [python]
---

# Good Skill

This is a clean reference skill used for QA testing. It has no secrets,
no absolute paths, and no hanging processes. The only dependency is the
Python standard library.

## When to Use

Use this skill when you need a known-good skill fixture to compare against.

## How to Run

Run the greeting script:

```
python3 scripts/hello.py
```

Pass `--help` to see the available options:

```
python3 scripts/hello.py --help
```

## Verification

- `python3 scripts/hello.py` prints `Hello from good skill`.
- `python3 scripts/hello.py --help` prints usage information and exits 0.
- No files outside this skill directory are read or written.
