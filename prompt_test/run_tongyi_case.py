from __future__ import annotations

import argparse
import json

from shared import CASES, run_generation


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one Tongyi prompt test case.")
    parser.add_argument("case", choices=sorted(CASES.keys()))
    args = parser.parse_args()

    image_path, meta_path, prompt_result = run_generation(args.case, "tongyi")
    print(json.dumps({
        "model": "Tongyi-MAI/Z-Image-Turbo",
        "case": args.case,
        "image": str(image_path),
        "metadata": str(meta_path),
        "positivePrompt": prompt_result["positivePrompt"],
        "negativePrompt": prompt_result["negativePrompt"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
