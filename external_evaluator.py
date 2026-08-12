from __future__ import annotations

import sys
from typing import Sequence


def parse_lisp_vector(text: str) -> Sequence[float]:
    cleaned = text.strip()
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = cleaned[1:-1]
    return [float(item) for item in cleaned.split() if item]


def main() -> int:
    if len(sys.argv) < 2:
        print("(0 0 0)")
        return 0

    values = parse_lisp_vector(sys.argv[1])
    score = sum(values)
    print(f"({score} {score} {score})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
