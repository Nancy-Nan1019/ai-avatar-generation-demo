from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import torch
from diffusers import StableDiffusionXLPipeline

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app  # noqa: E402
from prompt_test.shared import CASES, OUTPUT_DIR, build_case_payload  # noqa: E402

MODEL_ID = "segmind/SSD-1B"


def load_pipeline(model_id: str) -> StableDiffusionXLPipeline:
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32

    pipeline = StableDiffusionXLPipeline.from_pretrained(
        model_id,
        torch_dtype=dtype,
    )
    pipeline = pipeline.to(device)
    try:
        pipeline.enable_attention_slicing()
    except Exception:
        pass
    return pipeline


def save_result(case_name: str, prompt_result: dict, image, model_id: str, steps: int, guidance_scale: float, width: int, height: int) -> tuple[Path, Path]:
    image_path = OUTPUT_DIR / f"{case_name}_ssd1b.png"
    image.save(image_path)

    meta = {
        "model": model_id,
        "case": case_name,
        "positivePrompt": prompt_result["positivePrompt"],
        "negativePrompt": prompt_result["negativePrompt"],
        "generation": {
            "width": width,
            "height": height,
            "numInferenceSteps": steps,
            "guidanceScale": guidance_scale,
        },
    }
    meta_path = OUTPUT_DIR / f"{case_name}_ssd1b_prompt.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return image_path, meta_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one local SSD-1B prompt test case.")
    parser.add_argument("case", choices=sorted(CASES.keys()))
    parser.add_argument("--steps", type=int, default=12)
    parser.add_argument("--cfg", type=float, default=8.0)
    parser.add_argument("--width", type=int, default=768)
    parser.add_argument("--height", type=int, default=768)
    parser.add_argument("--model", default=MODEL_ID)
    args = parser.parse_args()

    payload = build_case_payload(args.case)
    payload["width"] = args.width
    payload["height"] = args.height
    payload["numInferenceSteps"] = args.steps
    payload["guidanceScale"] = args.cfg
    prompt_result = app.build_prompt(payload)

    pipe = load_pipeline(args.model)
    result = pipe(
        prompt=prompt_result["positivePrompt"],
        negative_prompt=prompt_result["negativePrompt"],
        num_inference_steps=args.steps,
        guidance_scale=args.cfg,
        width=args.width,
        height=args.height,
    )

    image_path, meta_path = save_result(
        args.case,
        prompt_result,
        result.images[0],
        args.model,
        args.steps,
        args.cfg,
        args.width,
        args.height,
    )

    print(json.dumps({
        "model": args.model,
        "case": args.case,
        "image": str(image_path),
        "metadata": str(meta_path),
        "positivePrompt": prompt_result["positivePrompt"],
        "negativePrompt": prompt_result["negativePrompt"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
