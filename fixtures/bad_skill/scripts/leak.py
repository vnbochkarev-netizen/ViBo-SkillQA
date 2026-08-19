#!/usr/bin/env python3
"""Auth helper for the bad skill.

Intentionally prints a hardcoded API token to stdout.
"""

import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("leak")


def get_token() -> str:
    """Return the API token used for authenticated calls.

    BUG: the real token is hardcoded and printed to the log below.
    """
    return "Bearer sk-abcdef1234567890"


def main() -> None:
    token = get_token()
    logger.info("Authenticating with token: %s", token)  # BUG: token leak
    print(f"Auth OK, token length: {len(token)}")


if __name__ == "__main__":
    main()
