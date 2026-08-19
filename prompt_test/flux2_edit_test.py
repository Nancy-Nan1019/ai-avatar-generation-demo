from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from huggingface_hub import InferenceClient
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app  # noqa: E402
from prompt_test.shared import CASES  # noqa: E402

OUTPUT_DIR = ROOT / "prompt_test" / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

EDIT_MODEL = "black-forest-labs/FLUX.2-dev"

EDIT_INSTRUCTION_TEMPLATES = {
    "xianxia_avatar": "Convert the existing portrait into an elegant xianxia-style avatar. Keep the same face identity, preserve the overall composition, refine the outfit into flowing hanfu, and strengthen the calm, cool, high-end mood.",
    "campus_boy_avatar": "Keep the same boy identity and face structure. Refine the portrait into a clean, polished campus avatar with clearer facial focus, stronger headphones styling, and a more natural profile composition.",
}


def get_client() -> InferenceClient:
    token = os.environ.get("HF_TOKEN")
    if not token:
        raise RuntimeError("HF_TOKEN is not set. Please export your Hugging Face token first.")
    return InferenceClient(api_key=token)



def build_case_payload(case_name: str) -> dict[str, Any]:
    if case_name not in CASES:
        raise KeyError(f"Unknown case: {case_name}")

    base_payload = CASES[case_name]
    payload = {
        "selections": dict(base_payload["selections"]),
        "customPromptZh": base_payload.get("customPromptZh", ""),
    }
    payload.update(base_payload.get("generation", {}))
    return payload



def build_edit_prompt(case_name: str, instruction_en: str, instruction_zh: str = "") -> dict[str, Any]:
    prompt_result = app.build_prompt(build_case_payload(case_name))

    prompt_parts = [
        "Edit the input image while preserving the same main character identity, face structure, hairstyle, and overall framing as much as possible.",
        "Only modify the requested visual attributes and keep the result suitable for a polished avatar presentation.",
        f"Target visual direction: {prompt_result['positivePrompt']}",
        f"Specific edit request: {instruction_en}",
    ]
    if instruction_zh.strip():
        prompt_parts.append(f"Additional user note in Chinese: {instruction_zh.strip()}")

    edit_prompt = " ".join(prompt_parts)
    return {
        "editPrompt": edit_prompt,
        "basePrompt": prompt_result["positivePrompt"],
        "negativePrompt": prompt_result["negativePrompt"],
        "promptGroups": prompt_result["promptGroups"],
        "selectedOptions": prompt_result["selectedOptions"],
        "softConflicts": prompt_result["softConflicts"],
    }



def run_edit(input_image_path: Path, case_name: str, instruction_en: str, instruction_zh: str = "") -> tuple[Path, Path]:
    client = get_client()
    prompt_bundle = build_edit_prompt(case_name, instruction_en, instruction_zh)

    with Image.open(input_image_path) as image:
        result = client.image_to_image(
            image=image,
            prompt=prompt_bundle["editPrompt"],
            model=EDIT_MODEL,
        )

    output_image_path = OUTPUT_DIR / f"{input_image_path.stem}_{case_name}_flux2_edit.png"
    output_meta_path = OUTPUT_DIR / f"{input_image_path.stem}_{case_name}_flux2_edit.json"
    result.save(output_image_path)
    output_meta_path.write_text(json.dumps(prompt_bundle, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_image_path, output_meta_path



def main() -> None:
    parser = argparse.ArgumentParser(description="Run image-to-image edit with FLUX.2-dev through Hugging Face.")
    parser.add_argument("input_image", help="Path to the existing image you want to edit.")
    parser.add_argument("case", choices=sorted(CASES.keys()))
    parser.add_argument("--instruction-en", dest="instruction_en", default="", help="English edit instruction. Recommended.")
    parser.add_argument("--instruction-zh", dest="instruction_zh", default="", help="Chinese edit note. Optional helper note, but English is recommended for stability.")
    args = parser.parse_args()

    input_image_path = Path(args.input_image)
    if not input_image_path.exists():
        raise FileNotFoundError(f"Input image not found: {input_image_path}")

    instruction_en = args.instruction_en.strip() or EDIT_INSTRUCTION_TEMPLATES[args.case]
    output_image_path, output_meta_path = run_edit(input_image_path, args.case, instruction_en, args.instruction_zh)

    print(json.dumps({
        "model": EDIT_MODEL,
        "input": str(input_image_path.resolve()),
        "case": args.case,
        "instructionEn": instruction_en,
        "instructionZh": args.instruction_zh,
        "outputImage": str(output_image_path.resolve()),
        "outputMeta": str(output_meta_path.resolve()),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
