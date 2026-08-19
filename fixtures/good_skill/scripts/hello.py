#!/usr/bin/env python3
"""Greeting script for the good skill.

Prints a friendly greeting and supports a --help flag.
"""

import argparse


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="hello.py",
        description="Print a greeting from the good skill.",
    )
    parser.add_argument(
        "--name",
        default="world",
        help="Who to greet (default: %(default)s).",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    print(f"Hello from good skill, {args.name}!")


if __name__ == "__main__":
    main()
