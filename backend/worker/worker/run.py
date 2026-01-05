"""Minimal worker entrypoint.

In MVP we keep this simple and deterministic. Later we will wire:
- Redis queue
- LangGraph workflows
- structured logging
"""

import time


def main() -> None:
    print("Worker started (placeholder loop).")
    while True:
        time.sleep(10)


if __name__ == "__main__":
    main()
