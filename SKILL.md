---
name: vibo-skillqa
description: "Test and certify AI agent skills: 7 automated checks, grade A–D, certificate. Use when asked to check, test, or certify a skill."
version: 0.1.5
author: Viacheslav Bochkarev
license: Proprietary — https://wwwvibo.com
metadata:
  license_type: cloud-skillqa
  trial: 2 days
  price: "$5/month"
---

# ViBo SkillQA

Autonomous QA and certification for agent skills (structure: a folder with
SKILL.md + helper scripts). Runs 7 checks and issues a certificate
(grade A–D) you can show to buyers.

## Commands (run from the skillqa folder)

```bash
python3 skillqa.py test <path-to-skill> [--lang en|ru] [--skip module1,module2] [--load N] [--parallel [N]] [--timeout S]
python3 skillqa.py selftest          # test the tester itself
python3 skillqa.py license --status  # license state (demo vs pro)
```

- **demo**: static scan + teaser report (free, no license needed)
- **pro**: all 7 modules + certificate + JSON for CI (license key, $5/month,
  trial 2 days — https://wwwvibo.com)

## When to use

- User asks to check, test, review, or certify a skill.
- Before publishing a skill to a marketplace — run the check, show the grade.
- After editing a skill — re-run to prove nothing broke.

## Rules

- All executables run in a sandbox: fake tokens, no network, hard timeouts.
- Never run a skill's scripts outside the sandbox.
- Report honestly: pass/warn/fail per module, final grade A–D, certificate path.
- The tester tests itself (`selftest`) — if it fails, say so, don't hide it.
