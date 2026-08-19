from __future__ import annotations

import json

from shared import CASES, MODELS, run_generation


def main() -> None:
    summary = []
    for case_name in CASES:
        for model_key, model_id in MODELS.items():
            image_path, meta_path, prompt_result = run_generation(case_name, model_key)
            summary.append(
                {
                    "case": case_name,
                    "model": model_id,
                    "image": str(image_path),
                    "metadata": str(meta_path),
                    "positivePrompt": prompt_result["positivePrompt"],
                }
            )

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
