#!/usr/bin/env python3
"""Data pipeline for the bad skill.

Intentionally crashes with an unhandled ZeroDivisionError.
"""


def compute_average(items: list) -> float:
    """Return the average of a list of numbers."""
    total = sum(items)
    count = len(items)
    return total / count  # BUG: ZeroDivisionError when items is empty


def main() -> None:
    scores = []
    average = compute_average(scores)
    print(f"Average score: {average:.2f}")


if __name__ == "__main__":
    main()
