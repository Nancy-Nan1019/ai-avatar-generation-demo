from __future__ import annotations

import argparse
import json

from shared import CASES, build_prompt_result


def main() -> None:
    parser = argparse.ArgumentParser(description="Preview structured prompt output without generation.")
    parser.add_argument("case", choices=sorted(CASES.keys()))
    args = parser.parse_args()

    result = build_prompt_result(args.case)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
