#!/usr/bin/env python3
"""Фикстура для регрессии: корректный CLI, которому без аргументов нечего делать.

Печатает понятное объяснение и справку, выходит с кодом 0. Ожидаемое поведение
проверки SkillQA sandbox/noargs_: **pass** (раньше — warn «молчаливый успех», который
нельзя было снять: при ненулевом коде та же проверка ставит fail).
"""
import argparse
import sys


def main() -> int:
    ap = argparse.ArgumentParser(description="Ничего не делает без входных файлов.")
    ap.add_argument("path", nargs="?", help="каталог с входными файлами")
    args = ap.parse_args()
    if not args.path:
        print("нечего обрабатывать: не передан каталог с входными файлами — "
              "укажите путь аргументом")
        ap.print_help()
        return 0
    print(f"обрабатываю {args.path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
