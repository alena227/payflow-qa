"""Генерирует docs/test-cases.md и docs/qase/qase-import.csv из cases.py.

Запуск из корня проекта:  python docs/qase/build.py

Формат CSV — Qase CSV v1 (первая колонка `id`). Сначала идут строки-сюиты
(suite_without_cases = 1), затем тест-кейсы, ссылающиеся на suite_id.
Шаги: каждый шаг — отдельная пронумерованная строка внутри ячейки.
Если Qase не примет заголовки — поправь список HEADER и перезапусти скрипт.
"""
import csv
from collections import Counter
from pathlib import Path

from cases import CASES, SUITES

HERE = Path(__file__).parent
DOCS = HERE.parent

HEADER = [
    "id", "title", "description", "preconditions", "postconditions",
    "priority", "severity", "type", "layer", "behavior", "automation", "status",
    "suite_id", "suite", "suite_parent_id", "suite_without_cases",
    "steps_actions", "steps_result", "steps_data",
]


def numbered(lines):
    return "\n".join(f"{i}. {x}" for i, x in enumerate(lines, 1))


def build_csv():
    suite_ids = {name: i for i, name in enumerate(SUITES, 1)}
    path = HERE / "qase-import.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=HEADER)
        w.writeheader()
        for name, sid in suite_ids.items():
            w.writerow({"suite_id": sid, "suite": name, "suite_without_cases": 1})
        for tc in CASES:
            w.writerow({
                "title": f"{tc['id']} {tc['title']}",
                "description": f"Требования: {tc['req']}",
                "preconditions": tc["pre"],
                "priority": tc["priority"],
                "severity": tc["severity"],
                "type": tc["type"],
                "layer": tc["layer"],
                "behavior": tc["behavior"],
                "automation": tc["automation"],
                "status": "actual",
                "suite_id": suite_ids[tc["suite"]],
                "suite": tc["suite"],
                "steps_actions": numbered(a for a, _ in tc["steps"]),
                "steps_result": numbered(r for _, r in tc["steps"]),
            })
    return path


def build_md():
    lines = [
        "# Тест-кейсы PayFlow",
        "",
        "> Сгенерировано из `docs/qase/cases.py` скриптом `docs/qase/build.py`. Не редактировать вручную.",
        "> Импорт в Qase: `docs/qase/qase-import.csv`.",
        "",
        f"Всего: **{len(CASES)}**. По приоритету: "
        + ", ".join(f"{k} — {v}" for k, v in Counter(t['priority'] for t in CASES).most_common()) + ".",
        "",
        "## Матрица трассируемости",
        "",
        "| Требование | Тест-кейсы |",
        "|---|---|",
    ]
    trace: dict[str, list[str]] = {}
    for tc in CASES:
        for req in (r.strip() for r in tc["req"].split(",")):
            trace.setdefault(req, []).append(tc["id"])
    for req in sorted(trace):
        lines.append(f"| {req} | {', '.join(trace[req])} |")

    for suite in SUITES:
        lines += ["", f"## {suite}"]
        for tc in (t for t in CASES if t["suite"] == suite):
            lines += [
                "",
                f"### {tc['id']} {tc['title']}",
                "",
                f"**Требования:** {tc['req']} · **Приоритет:** {tc['priority']} · **Severity:** {tc['severity']} · "
                f"**Тип:** {tc['type']} · **Поведение:** {tc['behavior']}",
                "",
                f"**Предусловия:** {tc['pre']}",
                "",
                "| # | Шаг | Ожидаемый результат |",
                "|---|---|---|",
            ]
            for i, (a, r) in enumerate(tc["steps"], 1):
                lines.append(f"| {i} | {a.replace('|', '\\|')} | {r.replace('|', '\\|')} |")
    path = DOCS / "test-cases.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


if __name__ == "__main__":
    ids = [t["id"] for t in CASES]
    assert len(ids) == len(set(ids)), "duplicate test case ids"
    assert all(t["suite"] in SUITES for t in CASES), "unknown suite"
    print(build_csv())
    print(build_md())
    print(f"{len(CASES)} test cases")
