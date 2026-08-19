#!/usr/bin/env python3
"""Long-running task for the bad skill.

Intentionally sleeps for 30 seconds so a tester must kill it by timeout.
"""

import time


def poll_remote_job() -> None:
    """Simulate polling a remote job that never finishes quickly.

    BUG: sleeps 30 seconds; a tester should time out and kill this process.
    """
    time.sleep(30)


def main() -> None:
    print("Polling remote job...")
    poll_remote_job()
    print("Job finished.")


if __name__ == "__main__":
    main()
