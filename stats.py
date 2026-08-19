#!/usr/bin/env python3
"""ViBo SkillQA — статистика тестирования. Сканирует qa_reports/*/*.json и
пишет сводку в /root/vibo/docs/SKILLQA_STATS.md"""
import json, glob, os, re
from collections import Counter
from datetime import datetime, date

REPORTS = glob.glob("/root/skillqa/qa_reports/*/*.json")
today = date.today().isoformat()

grades = Counter()
fails = 0
clean = 0
secret_hits = 0
total_score = 0.0
all_rows = []

for f in REPORTS:
    try:
        r = json.load(open(f))
    except Exception:
        continue
    g = r.get("grade", "?")
    grades[g] += 1
    sc = r.get("score_pct", 0)
    total_score += sc
    fc = r.get("fail_count", 0)
    fails += fc
    if fc == 0:
        clean += 1
    for m in r.get("modules", []):
        for c in m.get("checks", []):
            if c.get("name") == "secret_leak" and c.get("status") == "fail":
                secret_hits += 1
    all_rows.append((r.get("date", ""), r.get("skill_name", "?"), g, round(sc * 100), fc))

n = len(all_rows)
rows = sorted(all_rows)
lines = []
lines.append("# 📊 ViBo SkillQA — статистика тестирования\n")
lines.append(f"**Обновлено:** {datetime.now().strftime('%Y-%m-%d %H:%M')}  ·  всего отчётов: **{n}**\n")
lines.append("## Распределение оценок\n")
lines.append("| Оценка | Кол-во | % |")
lines.append("|---|---|---|")
for g in ["A", "B", "C", "D"]:
    c = grades.get(g, 0)
    lines.append(f"| {g} | {c} | {round(100 * c / max(n, 1))}% |")
lines.append("")
lines.append("## Ключевые метрики\n")
lines.append(f"- **Чистых (fail_count=0):** {clean} ({round(100*clean/max(n,1))}%)")
lines.append(f"- **С дефектами (fail>0):** {n - clean} ({round(100*(n-clean)/max(n,1))}%)")
lines.append(f"- **Всего fail-проверок:** {fails}")
lines.append(f"- **Скиллы с найденными секретами:** {secret_hits}")
lines.append(f"- **Средний score:** {round(100 * total_score / max(n,1))}%")
lines.append("")
lines.append("## Чужие скиллы (GitHub-батчи 1-7, только внешние репо)\n")
lines.append("| Показатель | Значение |")
lines.append("|---|---|")
g_ext = Counter()
n_ext = 0
f_ext = 0
c_ext = 0
for bf in sorted(glob.glob("/root/vibo/docs/skillqa_batch*_20260819.txt")):
    for line in open(bf, encoding="utf-8", errors="replace"):
        m = re.search(r"Grade: ([A-D]) \((\d+)/100\) — fail_count=(\d+)", line)
        if m:
            g_ext[m.group(1)] += 1
            n_ext += 1
            if int(m.group(3)) == 0:
                c_ext += 1
            else:
                f_ext += 1
lines.append(f"- **Протестировано внешних репо:** {n_ext}")
if n_ext:
    lines.append(f"- **Чистых (fail 0):** {c_ext} ({round(100*c_ext/n_ext)}%)")
    lines.append(f"- **С дефектами (fail>0):** {f_ext} ({round(100*f_ext/n_ext)}%)")
    for g in ["A", "B", "C", "D"]:
        c = g_ext.get(g, 0)
        if c:
            lines.append(f"- **Оценка {g}:** {c} ({round(100*c/n_ext)}%)")
lines.append("")

lines.append("## Последние 20 отчётов\n")
lines.append("| Дата | Скилл | Оценка | Score | Fail |")
lines.append("|---|---|---|---|---|")
for d, s, g, sc, fc in rows[-20:]:
    lines.append(f"| {d[:10]} | {s} | {g} | {sc} | {fc} |")
lines.append("")

os.makedirs("/root/vibo/docs", exist_ok=True)
out = "/root/vibo/docs/SKILLQA_STATS.md"
open(out, "w", encoding="utf-8").write("\n".join(lines) + "\n")
print(f"OK: {n} отчётов → {out}")
print(f"A={grades.get('A',0)} B={grades.get('B',0)} C={grades.get('C',0)} D={grades.get('D',0)} чистых={clean} секретов={secret_hits}")
