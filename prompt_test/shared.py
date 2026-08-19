from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from huggingface_hub import InferenceClient

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app  # noqa: E402

OUTPUT_DIR = ROOT / "prompt_test" / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MODELS = {
    "krea": "krea/Krea-2-Turbo",
    "tongyi": "Tongyi-MAI/Z-Image-Turbo",
}

CASES: dict[str, dict[str, Any]] = {
    "xianxia_avatar": {
        "selections": {
            "style_base": ["古风仙侠"],
            "outfit_style": ["汉服"],
            "scene_anime": ["古风庭院"],
            "pose_basic": ["坐姿"],
            "mood_emotion": ["清冷疏离"],
            "social_avatar_adaptation": ["正方形裁剪兼容"],
        },
        "customPromptZh": "面部居中，人物气质干净高级，适合社交头像展示",
        "generation": {
            "width": 768,
            "height": 768,
        },
    },
    "campus_boy_avatar": {
        "selections": {
            "style_base": ["校园清新"],
            "appearance_face": ["清冷眼距"],
            "appearance_face_detail": ["泪痣"],
            "persona_school_role": ["校草风男生"],
            "outfit_accessories": ["耳机"],
            "pose_basic": ["侧脸"],
            "pose_atmosphere_action": ["戴耳机听歌"],
            "scene_school": ["图书馆"],
            "mood_emotion": ["清冷疏离"],
            "social_avatar_adaptation": ["微信头像", "圆形裁剪兼容"],
        },
        "customPromptZh": "脸部清晰，五官集中，适合头像裁剪",
        "generation": {
            "width": 768,
            "height": 768,
        },
    },
}


def get_client() -> InferenceClient:
    token = os.environ.get("HF_TOKEN")
    if not token:
        raise RuntimeError("HF_TOKEN is not set. Please export your Hugging Face token first.")
    return InferenceClient(provider="fal-ai", api_key=token)



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



def build_prompt_result(case_name: str) -> dict[str, Any]:
    return app.build_prompt(build_case_payload(case_name))



def save_metadata(case_name: str, model_key: str, prompt_result: dict[str, Any]) -> Path:
    meta_path = OUTPUT_DIR / f"{case_name}_{model_key}_prompt.json"
    meta_path.write_text(json.dumps(prompt_result, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta_path



def run_generation(case_name: str, model_key: str) -> tuple[Path, Path, dict[str, Any]]:
    if model_key not in MODELS:
        raise KeyError(f"Unknown model key: {model_key}")

    client = get_client()
    prompt_result = build_prompt_result(case_name)
    model_id = MODELS[model_key]

    image = client.text_to_image(
        prompt=prompt_result["positivePrompt"],
        negative_prompt=prompt_result["negativePrompt"],
        model=model_id,
    )

    image_path = OUTPUT_DIR / f"{case_name}_{model_key}.png"
    image.save(image_path)
    meta_path = save_metadata(case_name, model_key, prompt_result)
    return image_path, meta_path, prompt_result
