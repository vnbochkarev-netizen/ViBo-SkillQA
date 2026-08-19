#!/usr/bin/env bash
# ViBo SkillQA — GitHub testing helper.
# Usage:
#   ./github_test.sh <owner>/<repo> [--comment] [--pr <number>] [--skip load,parallel]
#
# Clones the repo, runs `skillqa.py test` on the skill directory and,
# with --comment, posts the grade summary as a GitHub comment
# (issue comment, or PR review comment when --pr is given).
set -euo pipefail

REPO="${1:?usage: github_test.sh <owner>/<repo> [--comment] [--pr N]}"
shift || true
COMMENT=0
PR=""
SKIP=""
while [ $# -gt 0 ]; do
  case "$1" in
    --comment) COMMENT=1 ;;
    --pr) PR="$2"; shift ;;
    --skip) SKIP="$2"; shift ;;
  esac
  shift
done

TOKEN=$(grep '^GITHUB_TOKEN=' /root/vibo/secrets/github_token.env | cut -d= -f2-)
WORK=/tmp/gh_skill_test
rm -rf "$WORK" && mkdir -p "$WORK"

echo "==> cloning https://github.com/$REPO"
git clone -q --depth 1 "https://github.com/$REPO.git" "$WORK/repo"

# locate the skill: repo root or first SKILL.md
SKILL_DIR="$WORK/repo"
if [ ! -f "$WORK/repo/SKILL.md" ]; then
  found=$(find "$WORK/repo" -maxdepth 3 -name SKILL.md | head -1 || true)
  [ -n "$found" ] && SKILL_DIR="$(dirname "$found")"
fi

echo "==> testing: $SKILL_DIR"
if [ -n "$SKIP" ]; then
  OUT=$(cd /root/skillqa && python3 skillqa.py test "$SKILL_DIR" --lang en --skip "$SKIP" 2>&1 | tail -40 || true)
else
  OUT=$(cd /root/skillqa && python3 skillqa.py test "$SKILL_DIR" --lang en 2>&1 | tail -40 || true)
fi
echo "$OUT"

if [ "$COMMENT" = "1" ]; then
  GRADE=$(echo "$OUT" | grep -oE "Grade: [A-D] \([0-9]+/100\)" | head -1 || echo "Grade: ?")
  BODY="🛡️ **ViBo SkillQA report** (v$(cd /root/skillqa && grep -m1 'VERSION = ' skillqa.py | grep -oE '[0-9.]+'))

**$GRADE** — fail_count: $(echo "$OUT" | grep -oE 'fail_count=[0-9]+' | head -1 || echo '?')

\`\`\`
$(echo "$OUT" | tail -25)
\`\`\`

*Certified by [ViBo SkillQA](https://wwwvibo.com/skillqa) — $5/mo, 2-day free trial.*"
  BODY_JSON=$(python3 -c "import json,sys; print(json.dumps(sys.argv[1]))" "$BODY")
  if [ -n "$PR" ]; then
    echo "==> posting PR review comment (#$PR)"
    curl -s -m 30 -X POST -H "Authorization: token $TOKEN" -H "Accept: application/vnd.github+json" \
      "https://api.github.com/repos/$REPO/pulls/$PR/comments" \
      -d "{\"body\":$BODY_JSON,\"commit_id\":\"$(cd "$WORK/repo" && git rev-parse HEAD)\",\"path\":\"SKILL.md\",\"line\":1}" \
      | python3 -c "import json,sys; d=json.load(sys.stdin); print('comment:', d.get('html_url') or d.get('message'))"
  else
    echo "==> posting issue comment"
    ISSUE=$(curl -s -m 15 -H "Authorization: token $TOKEN" "https://api.github.com/repos/$REPO/issues?state=all&per_page=1" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d[0]['number'] if d else '')")
    if [ -n "$ISSUE" ]; then
      curl -s -m 30 -X POST -H "Authorization: token $TOKEN" -H "Accept: application/vnd.github+json" \
        "https://api.github.com/repos/$REPO/issues/$ISSUE/comments" \
        -d "{\"body\":$BODY_JSON}" \
        | python3 -c "import json,sys; d=json.load(sys.stdin); print('comment:', d.get('html_url') or d.get('message'))"
    else
      echo "no issues found — open one first or use --pr"
    fi
  fi
fi
