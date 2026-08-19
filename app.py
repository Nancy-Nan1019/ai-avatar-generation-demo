import base64
import cgi
import html
import json
import os
import textwrap
from io import BytesIO
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from uuid import uuid4


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
CONFIG_PATH = BASE_DIR / "config" / "prompt-mapping.zh-en.json"
BACKGROUND_CONFIG_PATH = BASE_DIR / "config" / "backgrounds.json"


def load_mapping() -> dict:
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


PROMPT_MAPPING = load_mapping()


def load_background_catalog() -> list[dict]:
    with BACKGROUND_CONFIG_PATH.open("r", encoding="utf-8-sig") as file:
        return json.load(file)


BACKGROUND_CATALOG = load_background_catalog()

PROMPT_GROUP_ORDER = [
    "quality",
    "style",
    "persona",
    "appearance",
    "outfit",
    "pose",
    "scene",
    "mood",
    "composition",
    "custom",
]

PROMPT_BUCKET_ORDER = [
    "quality",
    "style",
    "subject",
    "outfit",
    "pose",
    "scene",
    "mood",
    "output",
    "custom",
]

CHINESE_POSITIVE_PREFIX = [
    "???",
    "????",
    "????",
]

CATEGORY_GROUP_MAP = {
    "style_base": "style",
    "style_ip_derivative": "style",
    "style_texture": "appearance",
    "appearance_hair": "appearance",
    "appearance_face": "appearance",
    "appearance_face_detail": "appearance",
    "persona_school_role": "persona",
    "persona_anime_role": "persona",
    "persona_special": "persona",
    "outfit_style": "outfit",
    "outfit_accessories": "outfit",
    "pose_basic": "pose",
    "pose_interaction": "pose",
    "pose_atmosphere_action": "pose",
    "scene_school": "scene",
    "scene_anime": "scene",
    "scene_simple_background": "scene",
    "mood_emotion": "mood",
    "mood_palette": "mood",
    "social_avatar_adaptation": "composition",
    "social_special_requirement": "composition",
}

CATEGORY_BUCKET_MAP = {
    "style_base": "style",
    "style_ip_derivative": "style",
    "style_texture": "style",
    "appearance_hair": "subject",
    "appearance_face": "subject",
    "appearance_face_detail": "subject",
    "persona_school_role": "subject",
    "persona_anime_role": "subject",
    "persona_special": "subject",
    "outfit_style": "outfit",
    "outfit_accessories": "outfit",
    "pose_basic": "pose",
    "pose_interaction": "pose",
    "pose_atmosphere_action": "pose",
    "scene_school": "scene",
    "scene_anime": "scene",
    "scene_simple_background": "scene",
    "mood_emotion": "mood",
    "mood_palette": "mood",
    "social_avatar_adaptation": "output",
    "social_special_requirement": "output",
}

SOFT_CONFLICT_RULES = [
    {
        "name": "crop_vs_full_body",
        "labels": {"全身像", "微信头像", "QQ头像", "小红书头像", "微博头像", "圆形裁剪兼容"},
        "message": "全身像和头像裁剪适配同时出现时，构图意图可能冲突。",
    },
    {
        "name": "scene_vs_plain_background",
        "labels": {"图书馆", "樱花树下", "古风庭院", "赛博朋克街道", "纯色背景（白）", "纯色背景（粉）", "纯色背景（蓝）", "留白设计"},
        "message": "具体场景和极简背景同时出现时，背景描述可能互相削弱。",
    },
    {
        "name": "duo_vs_avatar_crop",
        "labels": {"情侣头像（双人互动）", "闺蜜头像（同款不同色）", "兄弟羁绊风", "圆形裁剪兼容", "微信头像"},
        "message": "双人设定和头像裁剪同时出现时，人物留白会变得更紧。",
    },
]

def flatten_selected_labels(selections: dict) -> set[str]:
    labels = set()
    for option_labels in selections.values():
        if isinstance(option_labels, list):
            labels.update(option_labels)
        elif option_labels:
            labels.add(option_labels)
    return labels


def resolve_negative_profiles(selections: dict) -> list[str]:
    profiles = ["portrait"]
    selected_labels = flatten_selected_labels(selections)

    duo_labels = {
        "情侣头像（双人互动）",
        "闺蜜头像（同款不同色）",
        "兄弟羁绊风",
    }
    action_labels = {
        "热血战斗",
        "打篮球",
        "魔法施法",
        "战斗姿势",
    }

    if selected_labels & duo_labels:
        profiles.append("duo")
    if "全身像" in selected_labels:
        profiles.append("full_body")
    if selected_labels & action_labels:
        profiles.append("action")
    if any(label.startswith("纯色背景") for label in selected_labels) or "留白设计" in selected_labels:
        profiles.append("clean_background")

    return profiles


def dedupe_parts(parts: list[str]) -> list[str]:
    return list(dict.fromkeys(part.strip() for part in parts if part and part.strip()))


def build_prompt_buckets() -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    buckets_en = {bucket: [] for bucket in PROMPT_BUCKET_ORDER}
    buckets_zh = {bucket: [] for bucket in PROMPT_BUCKET_ORDER}
    buckets_en["quality"] = list(PROMPT_MAPPING["generationDefaults"]["positivePrefix"])
    buckets_zh["quality"] = list(CHINESE_POSITIVE_PREFIX)
    return buckets_en, buckets_zh


def assemble_prompt_from_sections(section_map: dict[str, list[str]], order: list[str]) -> tuple[dict[str, list[str]], list[str]]:
    normalized_sections = {section: dedupe_parts(section_map.get(section, [])) for section in order}
    ordered_parts: list[str] = []
    for section in order:
        ordered_parts.extend(normalized_sections[section])
    return normalized_sections, dedupe_parts(ordered_parts)


def join_prompt_parts(parts: list[str]) -> str:
    return ", ".join(dedupe_parts(parts))


def join_instruction_parts(parts: list[str]) -> str:
    return " ".join(part.strip() for part in parts if part and part.strip())


def detect_soft_conflicts(selected_labels: set[str]) -> list[dict]:
    conflicts = []
    for rule in SOFT_CONFLICT_RULES:
        matched = sorted(selected_labels & rule["labels"])
        if len(matched) >= 2:
            conflicts.append(
                {
                    "name": rule["name"],
                    "message": rule["message"],
                    "matchedLabels": matched,
                }
            )
    return conflicts


def is_translation_enabled() -> bool:
    return str(os.environ.get("AI_TRANSLATION_ENABLED", "")).strip().lower() in {"1", "true", "yes", "on"}


def translate_text_to_english_if_configured(text: str, purpose: str) -> dict:
    source_text = str(text or "").strip()
    result = {
        "sourceText": source_text,
        "translatedText": "",
        "used": False,
        "enabled": is_translation_enabled(),
        "purpose": purpose,
        "provider": "deepseek-reserved",
    }

    if not source_text:
        return result

    if not result["enabled"]:
        result["status"] = "disabled"
        return result

    api_key = os.environ.get("AI_API_KEY", "").strip()
    api_url = os.environ.get("AI_API_URL", "https://api.deepseek.com/chat/completions").strip()
    model = os.environ.get("AI_MODEL", "deepseek-chat").strip()

    result["apiUrl"] = api_url
    result["model"] = model

    if not api_key:
        result["status"] = "missing_api_key"
        return result

    request_payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "Translate Chinese avatar-design notes into concise English visual prompt phrases. Return plain English only.",
            },
            {
                "role": "user",
                "content": source_text,
            },
        ],
        "temperature": 0.2,
    }

    request = Request(
        api_url,
        data=json.dumps(request_payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=45) as response:
            payload = json.loads(response.read().decode("utf-8"))
        translated_text = (
            payload.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )
        if translated_text:
            result["translatedText"] = translated_text
            result["used"] = True
            result["status"] = "translated"
        else:
            result["status"] = "empty_response"
    except Exception as exc:
        result["status"] = "request_failed"
        result["error"] = str(exc)

    return result


def collect_prompt_context(payload: dict) -> dict:
    categories_by_id = {category["id"]: category for category in PROMPT_MAPPING["categories"]}
    negative_parts = list(PROMPT_MAPPING["generationDefaults"]["negativePrompt"])
    selected_labels = []
    grouped_positive_parts = {group: [] for group in PROMPT_GROUP_ORDER}
    grouped_positive_parts_zh = {group: [] for group in PROMPT_GROUP_ORDER}
    grouped_positive_parts["quality"] = list(PROMPT_MAPPING["generationDefaults"]["positivePrefix"])
    grouped_positive_parts_zh["quality"] = list(CHINESE_POSITIVE_PREFIX)
    prompt_buckets, prompt_buckets_zh = build_prompt_buckets()

    selections = payload.get("selections", {})
    for category_id, option_labels in selections.items():
        category = categories_by_id.get(category_id)
        if not category:
            continue

        label_list = option_labels if isinstance(option_labels, list) else [option_labels]
        options_by_label = {option["labelZh"]: option for option in category["options"]}

        for label in label_list:
            option = options_by_label.get(label)
            if not option:
                continue

            prompt_entry = {
                "categoryId": category_id,
                "categoryZh": category["labelZh"],
                "labelZh": label,
                "promptEn": option["promptEn"],
                "promptZh": label,
                "promptGroup": CATEGORY_GROUP_MAP.get(category_id, "appearance"),
                "promptBucket": CATEGORY_BUCKET_MAP.get(category_id, "subject"),
            }
            grouped_positive_parts[prompt_entry["promptGroup"]].append(option["promptEn"])
            grouped_positive_parts_zh[prompt_entry["promptGroup"]].append(label)
            prompt_buckets[prompt_entry["promptBucket"]].append(option["promptEn"])
            prompt_buckets_zh[prompt_entry["promptBucket"]].append(label)
            selected_labels.append(prompt_entry)

    custom_prompt = str(payload.get("customPromptZh", "")).strip()
    custom_prompt_translation = translate_text_to_english_if_configured(custom_prompt, "custom_prompt")
    if custom_prompt:
        custom_prompt_en = custom_prompt_translation.get("translatedText", "").strip() or custom_prompt
        grouped_positive_parts["custom"].append(custom_prompt_en)
        grouped_positive_parts_zh["custom"].append(custom_prompt)
        prompt_buckets["custom"].append(custom_prompt_en)
        prompt_buckets_zh["custom"].append(custom_prompt)

    negative_profiles = resolve_negative_profiles(selections)
    negative_profile_map = PROMPT_MAPPING["generationDefaults"].get("negativePromptProfiles", {})
    for profile in negative_profiles:
        negative_parts.extend(negative_profile_map.get(profile, []))

    prompt_groups, _ = assemble_prompt_from_sections(grouped_positive_parts, PROMPT_GROUP_ORDER)
    prompt_groups_zh, _ = assemble_prompt_from_sections(grouped_positive_parts_zh, PROMPT_GROUP_ORDER)
    prompt_buckets, ordered_positive_parts = assemble_prompt_from_sections(prompt_buckets, PROMPT_BUCKET_ORDER)
    prompt_buckets_zh, ordered_positive_parts_zh = assemble_prompt_from_sections(prompt_buckets_zh, PROMPT_BUCKET_ORDER)
    negative_prompt = ", ".join(dedupe_parts(negative_parts))
    soft_conflicts = detect_soft_conflicts(flatten_selected_labels(selections))

    defaults = PROMPT_MAPPING["generationDefaults"]["inference"]
    generation = {
        "width": int(payload.get("width", defaults["width"])),
        "height": int(payload.get("height", defaults["height"])),
        "numInferenceSteps": int(payload.get("numInferenceSteps", defaults["numInferenceSteps"])),
        "guidanceScale": float(payload.get("guidanceScale", defaults["guidanceScale"])),
    }

    return {
        "negativePrompt": negative_prompt,
        "negativeProfilesApplied": negative_profiles,
        "promptGroups": prompt_groups,
        "promptGroupsZh": prompt_groups_zh,
        "promptBuckets": prompt_buckets,
        "promptBucketsZh": prompt_buckets_zh,
        "orderedPositiveParts": ordered_positive_parts,
        "orderedPositivePartsZh": ordered_positive_parts_zh,
        "softConflicts": soft_conflicts,
        "selectedOptions": selected_labels,
        "customPromptTranslation": custom_prompt_translation,
        "generation": generation,
    }


def build_generate_prompt(payload: dict) -> dict:
    prompt_context = collect_prompt_context(payload)
    positive_prompt = join_prompt_parts(prompt_context["orderedPositiveParts"])
    positive_prompt_zh = join_prompt_parts(prompt_context["orderedPositivePartsZh"])
    prompt_context["positivePrompt"] = positive_prompt
    prompt_context["positivePromptZh"] = positive_prompt_zh
    prompt_context["promptMode"] = "generate"
    return prompt_context


def build_prompt(payload: dict) -> dict:
    return build_generate_prompt(payload)


def build_edit_prompt(payload: dict, prompt_result: dict) -> dict:
    instruction_zh = str(payload.get("editInstructionZh") or payload.get("editInstruction") or "").strip()
    instruction_translation = translate_text_to_english_if_configured(instruction_zh, "edit_instruction")
    translated_instruction = instruction_translation.get("translatedText", "").strip()
    edit_mode = str(payload.get("editMode", "character")).strip().lower() or "character"

    subject_parts = (
        prompt_result.get("promptBuckets", {}).get("subject", [])
        or prompt_result.get("promptGroups", {}).get("persona", []) + prompt_result.get("promptGroups", {}).get("appearance", [])
    )
    outfit_parts = prompt_result.get("promptBuckets", {}).get("outfit", [])
    style_parts = prompt_result.get("promptBuckets", {}).get("style", [])
    scene_parts = prompt_result.get("promptBuckets", {}).get("scene", [])
    mood_parts = prompt_result.get("promptBuckets", {}).get("mood", [])
    output_parts = prompt_result.get("promptBuckets", {}).get("output", [])

    preserve_parts = [
        "Preserve the same main character identity, face structure, hairstyle, and core visual silhouette.",
    ]
    if subject_parts:
        preserve_parts.append(f"Keep these subject traits consistent: {join_prompt_parts(subject_parts)}.")
    if outfit_parts:
        preserve_parts.append(f"Retain the overall costume identity unless the edit request explicitly changes it: {join_prompt_parts(outfit_parts)}.")

    mode_instruction_map = {
        "character": "Focus the edit on the character design itself, such as face expression, hairstyle, clothing details, and character presence.",
        "style": "Focus the edit on style, palette, rendering mood, and overall atmosphere while keeping the same character recognizable.",
        "background": "Focus the edit on the background direction and scene atmosphere while keeping the main character stable and visually dominant.",
    }

    target_parts = []
    if style_parts:
        target_parts.append(f"Target style direction: {join_prompt_parts(style_parts)}.")
    if scene_parts:
        target_parts.append(f"Reference scene direction: {join_prompt_parts(scene_parts)}.")
    if mood_parts:
        target_parts.append(f"Reference mood direction: {join_prompt_parts(mood_parts)}.")
    target_parts.append(mode_instruction_map.get(edit_mode, mode_instruction_map["character"]))

    edit_request_parts = []
    if translated_instruction:
        edit_request_parts.append(f"Specific edit request: {translated_instruction}.")
    elif instruction_zh:
        edit_request_parts.append(f"Specific edit request in Chinese: {instruction_zh}.")
    else:
        edit_request_parts.append("Refine the image while keeping the avatar more polished, coherent, and presentation-ready.")

    quality_parts = [
        "Keep the result suitable for a polished avatar presentation with clear facial rendering and coherent lighting.",
    ]
    if output_parts:
        quality_parts.append(f"Output constraints: {join_prompt_parts(output_parts)}.")
    if prompt_result["negativePrompt"]:
        quality_parts.append(f"Avoid these issues: {prompt_result['negativePrompt']}.")

    prompt_parts = preserve_parts + target_parts + edit_request_parts + quality_parts

    return {
        "editPrompt": join_instruction_parts(prompt_parts),
        "editMode": edit_mode,
        "instructionZh": instruction_zh,
        "instructionTranslation": instruction_translation,
        "preservePromptParts": preserve_parts,
        "targetPromptParts": target_parts,
        "editRequestParts": edit_request_parts,
        "qualityPromptParts": quality_parts,
    }


def build_local_edit_prompt(payload: dict, prompt_result: dict) -> dict:
    edit_prompt_bundle = build_edit_prompt(payload, prompt_result)
    instruction_zh = edit_prompt_bundle["instructionZh"]
    translated_instruction = edit_prompt_bundle["instructionTranslation"].get("translatedText", "").strip()
    prompt_buckets = prompt_result.get("promptBuckets", {})
    edit_mode = edit_prompt_bundle.get("editMode", "character")

    local_parts = [
        join_prompt_parts(prompt_buckets.get("style", [])),
        join_prompt_parts(prompt_buckets.get("subject", [])),
        join_prompt_parts(prompt_buckets.get("outfit", [])),
        "same character, preserve identity, preserve face, preserve hairstyle",
        "avatar portrait, clean composition, coherent lighting, clear facial details",
    ]

    if edit_mode == "style":
        local_parts.append("refine rendering style, mood, color palette, and atmosphere")
    elif edit_mode == "background":
        local_parts.append("adjust background direction and scene mood while keeping the character stable")
    else:
        local_parts.append("refine face, outfit details, and character expression")

    if translated_instruction:
        local_parts.append(translated_instruction)
    elif instruction_zh:
        local_parts.append(instruction_zh)

    local_parts.extend(prompt_buckets.get("mood", []))
    local_parts.extend(prompt_buckets.get("output", []))

    local_negative = prompt_result["negativePrompt"]
    return {
        "editPrompt": join_prompt_parts(local_parts),
        "negativePrompt": local_negative,
        "instructionZh": instruction_zh,
        "instructionTranslation": edit_prompt_bundle["instructionTranslation"],
        "localPromptParts": dedupe_parts(local_parts),
    }


def generate_edit_via_diffusers(prompt_result: dict, image_bytes: bytes, payload: dict) -> dict:
    try:
        import torch
        from PIL import Image
        from diffusers import StableDiffusionImg2ImgPipeline
    except ImportError as exc:
        return {
            "backend": "edit-error",
            "imageUrl": "",
            "note": f"Missing local edit dependencies: {exc}",
        }

    model_id = os.environ.get("EDIT_DIFFUSERS_MODEL_ID", os.environ.get("DIFFUSION_MODEL_ID", "segmind/small-sd")).strip()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32
    cached_model_id = getattr(generate_edit_via_diffusers, "_model_id", None)

    if not hasattr(generate_edit_via_diffusers, "_pipeline") or cached_model_id != model_id:
        try:
            pipeline = StableDiffusionImg2ImgPipeline.from_pretrained(
                model_id,
                torch_dtype=dtype,
            )
        except Exception as exc:
            return {
                "backend": "edit-error",
                "imageUrl": "",
                "note": f"Failed to load local image-to-image model {model_id}: {exc}",
            }

        pipeline = pipeline.to(device)
        try:
            pipeline.enable_attention_slicing()
        except Exception:
            pass

        generate_edit_via_diffusers._pipeline = pipeline
        generate_edit_via_diffusers._model_id = model_id

    pipeline = generate_edit_via_diffusers._pipeline
    edit_bundle = build_local_edit_prompt(payload, prompt_result)

    try:
        input_image = Image.open(BytesIO(image_bytes)).convert("RGB")
    except Exception as exc:
        return {
            "backend": "edit-error",
            "imageUrl": "",
            "note": f"Failed to open edit source image: {exc}",
        }

    width = int(payload.get("width", prompt_result["generation"]["width"]))
    height = int(payload.get("height", prompt_result["generation"]["height"]))
    if width > 0 and height > 0:
        input_image = input_image.resize((width, height))

    steps = int(payload.get("editNumInferenceSteps", max(10, min(prompt_result["generation"]["numInferenceSteps"], 20))))
    guidance_scale = float(payload.get("editGuidanceScale", prompt_result["generation"]["guidanceScale"]))
    strength = float(payload.get("editStrength", os.environ.get("EDIT_STRENGTH", "0.6")))
    strength = max(0.2, min(strength, 0.85))

    try:
        result = pipeline(
            prompt=edit_bundle["editPrompt"],
            negative_prompt=edit_bundle["negativePrompt"],
            image=input_image,
            strength=strength,
            num_inference_steps=steps,
            guidance_scale=guidance_scale,
        )
    except Exception as exc:
        return {
            "backend": "edit-error",
            "imageUrl": "",
            "note": f"Local image-to-image generation failed: {exc}",
            "model": model_id,
            "editPrompt": edit_bundle["editPrompt"],
        }

    image = result.images[0]
    output_name = f"edited-{uuid4().hex[:12]}.png"
    output_path = STATIC_DIR / output_name
    image.save(output_path)

    metadata_name = f"edited-{uuid4().hex[:12]}.json"
    metadata_path = STATIC_DIR / metadata_name
    metadata_path.write_text(
        json.dumps(
            {
                "model": model_id,
                "mode": "diffusers-img2img",
                "prompt": prompt_result,
                "edit": edit_bundle,
                "settings": {
                    "strength": strength,
                    "steps": steps,
                    "guidanceScale": guidance_scale,
                    "device": device,
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return {
        "backend": "diffusers-edit",
        "imageUrl": f"/static/{output_name}",
        "note": f"Edited locally with {model_id} on {device}.",
        "model": model_id,
        "editPrompt": edit_bundle["editPrompt"],
        "metadataUrl": f"/static/{metadata_name}",
    }


def generate_edit_via_huggingface(prompt_result: dict, image_bytes: bytes, payload: dict) -> dict:
    try:
        from huggingface_hub import InferenceClient
        from PIL import Image
    except ImportError as exc:
        return {
            "backend": "edit-error",
            "imageUrl": "",
            "note": f"Missing edit dependencies: {exc}",
        }

    token = os.environ.get("HF_TOKEN", "").strip()
    if not token:
        return {
            "backend": "edit-error",
            "imageUrl": "",
            "note": "HF_TOKEN is not set.",
        }

    model_id = os.environ.get("EDIT_IMAGE_MODEL", "black-forest-labs/FLUX.2-dev").strip()
    provider = os.environ.get("HF_PROVIDER", "").strip()
    client_kwargs = {"api_key": token}
    if provider:
        client_kwargs["provider"] = provider

    edit_prompt_bundle = build_edit_prompt(payload, prompt_result)

    try:
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
        client = InferenceClient(**client_kwargs)
        result = client.image_to_image(
            image=image,
            prompt=edit_prompt_bundle["editPrompt"],
            model=model_id,
        )
    except Exception as exc:
        return {
            "backend": "edit-error",
            "imageUrl": "",
            "note": f"Hugging Face edit request failed: {exc}",
            "model": model_id,
            "editPrompt": edit_prompt_bundle["editPrompt"],
        }

    output_name = f"edited-{uuid4().hex[:12]}.png"
    output_path = STATIC_DIR / output_name
    result.save(output_path)

    metadata_name = f"edited-{uuid4().hex[:12]}.json"
    metadata_path = STATIC_DIR / metadata_name
    metadata_path.write_text(
        json.dumps(
            {
                "model": model_id,
                "prompt": prompt_result,
                "edit": edit_prompt_bundle,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return {
        "backend": "huggingface-edit",
        "imageUrl": f"/static/{output_name}",
        "note": f"Edited with {model_id}.",
        "model": model_id,
        "editPrompt": edit_prompt_bundle["editPrompt"],
        "metadataUrl": f"/static/{metadata_name}",
    }


def is_truthy_flag(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def decode_data_url_image(data_url: str) -> bytes:
    if not data_url.startswith("data:image/") or "," not in data_url:
        raise ValueError("Invalid image data URL.")
    _, encoded = data_url.split(",", 1)
    return base64.b64decode(encoded)


def get_latest_editable_image_path() -> Path | None:
    candidates = []
    generated_output = STATIC_DIR / "generated-output.png"
    if generated_output.exists():
        candidates.append(generated_output)

    candidates.extend(STATIC_DIR.glob("edited-*.png"))
    if not candidates:
        return None
    return max(candidates, key=lambda item: item.stat().st_mtime)


def resolve_edit_source_from_payload(payload: dict) -> tuple[bytes, str]:
    current_data_url = str(payload.get("currentImageDataUrl", "")).strip()
    if current_data_url:
        return decode_data_url_image(current_data_url), "current-image-data-url"

    current_image_url = str(payload.get("currentImageUrl", "")).strip()
    if current_image_url:
        if current_image_url.startswith("data:image/"):
            return decode_data_url_image(current_image_url), "current-image-data-url"
        if current_image_url.startswith("/static/"):
            relative_path = current_image_url.removeprefix("/static/")
            file_path = (STATIC_DIR / relative_path).resolve()
            if STATIC_DIR.resolve() not in file_path.parents and file_path != STATIC_DIR.resolve():
                raise ValueError("Current image path is outside static directory.")
            if not file_path.exists() or not file_path.is_file():
                raise ValueError("Current image file was not found.")
            return file_path.read_bytes(), file_path.name
        raise ValueError("Unsupported currentImageUrl format.")

    if is_truthy_flag(payload.get("useCurrentResult")):
        latest_image = get_latest_editable_image_path()
        if latest_image is None:
            raise ValueError("No current result image is available yet.")
        return latest_image.read_bytes(), latest_image.name

    raise ValueError("No edit image source provided.")


def list_background_options() -> dict:
    return {"schools": BACKGROUND_CATALOG}


def find_background_entry(background_id: str) -> tuple[dict, dict]:
    for school in BACKGROUND_CATALOG:
        for background in school.get("backgrounds", []):
            if background.get("id") == background_id:
                return school, background
    raise ValueError("Unknown background id.")


def remove_background_from_portrait(image_bytes: bytes) -> bytes:
    try:
        from rembg import remove
    except ImportError as exc:
        raise RuntimeError(
            "Background removal dependency is missing. Install rembg and onnxruntime first."
        ) from exc

    return remove(image_bytes)


def compose_subject_on_background(subject_bytes: bytes, background_path: Path, placement: str, scale_preset: str) -> bytes:
    from PIL import Image, ImageFilter

    if not background_path.exists():
        raise FileNotFoundError("Background image file was not found.")

    background = Image.open(background_path).convert("RGBA")
    subject = Image.open(BytesIO(subject_bytes)).convert("RGBA")

    bbox = subject.getbbox()
    if bbox:
        subject = subject.crop(bbox)

    scale_map = {
        "close": 0.62,
        "medium": 0.48,
        "small": 0.36,
    }
    scale_ratio = scale_map.get(scale_preset, 0.48)
    target_height = max(220, int(background.height * scale_ratio))
    target_width = max(180, int(subject.width * target_height / max(subject.height, 1)))
    subject = subject.resize((target_width, target_height), Image.LANCZOS)

    x_map = {
        "left": int(background.width * 0.18),
        "center": int((background.width - target_width) / 2),
        "right": int(background.width * 0.68 - target_width / 2),
    }
    x = max(0, min(background.width - target_width, x_map.get(placement, x_map["center"])))
    y = max(0, background.height - target_height - int(background.height * 0.08))

    shadow = Image.new("RGBA", subject.size, (0, 0, 0, 0))
    shadow_alpha = subject.split()[-1].point(lambda value: min(140, int(value * 0.38)))
    shadow.putalpha(shadow_alpha)
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))

    composite = background.copy()
    composite.alpha_composite(shadow, (x + 16, y + 24))
    composite.alpha_composite(subject, (x, y))

    buffer = BytesIO()
    composite.convert("RGB").save(buffer, format="PNG")
    return buffer.getvalue()


def compose_background_scene(payload: dict, image_bytes: bytes) -> dict:
    background_id = str(payload.get("backgroundId", "")).strip()
    if not background_id:
        return {
            "backend": "compose-error",
            "imageUrl": "",
            "note": "backgroundId is required.",
        }

    placement = str(payload.get("placement", "center")).strip().lower() or "center"
    scale_preset = str(payload.get("scalePreset", "medium")).strip().lower() or "medium"

    try:
        school, background = find_background_entry(background_id)
    except ValueError as exc:
        return {
            "backend": "compose-error",
            "imageUrl": "",
            "note": str(exc),
        }

    try:
        cutout_bytes = remove_background_from_portrait(image_bytes)
        composed_bytes = compose_subject_on_background(
            cutout_bytes,
            STATIC_DIR / background["file"],
            placement,
            scale_preset,
        )
    except Exception as exc:
        return {
            "backend": "compose-error",
            "imageUrl": "",
            "note": f"Background compose failed: {exc}",
            "backgroundId": background_id,
        }

    output_name = f"composed-{uuid4().hex[:12]}.png"
    output_path = STATIC_DIR / output_name
    output_path.write_bytes(composed_bytes)

    meta_name = f"composed-{uuid4().hex[:12]}.json"
    meta_path = STATIC_DIR / meta_name
    meta_path.write_text(
        json.dumps(
            {
                "backgroundId": background_id,
                "school": school,
                "background": background,
                "placement": placement,
                "scalePreset": scale_preset,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return {
        "backend": "background-compose",
        "imageUrl": f"/static/{output_name}",
        "note": f"Composed with {school['labelZh']} - {background['labelZh']}.",
        "backgroundId": background_id,
        "metadataUrl": f"/static/{meta_name}",
    }


def resolve_generated_image_bytes(generation_result: dict) -> tuple[bytes, str]:
    image_url = str(generation_result.get("imageUrl", "")).strip()
    if not image_url:
        raise ValueError("Generated result did not include imageUrl.")
    if image_url.startswith("data:image/svg+xml"):
        raise ValueError("current result is only a mock preview")
    if image_url.startswith("data:image/"):
        return decode_data_url_image(image_url), "generated-data-url"
    if image_url.startswith("/static/"):
        relative_path = image_url.removeprefix("/static/")
        file_path = (STATIC_DIR / relative_path).resolve()
        if STATIC_DIR.resolve() not in file_path.parents and file_path != STATIC_DIR.resolve():
            raise ValueError("Generated image path is outside static directory.")
        if not file_path.exists() or not file_path.is_file():
            raise ValueError("Generated image file was not found.")
        return file_path.read_bytes(), file_path.name
    raise ValueError("Unsupported generated image format.")


def maybe_compose_generated_result(payload: dict, generation_result: dict) -> dict:
    if not is_truthy_flag(payload.get("applyBackgroundOnGenerate")):
        return generation_result

    background_id = str(payload.get("backgroundId", "")).strip()
    if not background_id:
        return {
            "backend": "compose-error",
            "imageUrl": "",
            "note": "backgroundId is required.",
        }

    try:
        image_bytes, source_name = resolve_generated_image_bytes(generation_result)
    except Exception as exc:
        return {
            "backend": "compose-error",
            "imageUrl": "",
            "note": f"Background composition could not continue: {exc}",
            "baseGeneration": generation_result,
        }

    compose_payload = {
        "backgroundId": background_id,
        "placement": payload.get("placement", "center"),
        "scalePreset": payload.get("scalePreset", "medium"),
    }
    composed_result = compose_background_scene(compose_payload, image_bytes)
    composed_result["baseGeneration"] = generation_result
    composed_result["sourceImageName"] = source_name
    return composed_result


def is_result_error(result: dict) -> bool:
    backend = str(result.get("backend", "")).strip().lower()
    return backend.endswith("-error") or backend == "compose-error"


def render_mock_svg(prompt_result: dict) -> str:
    summary_lines = [
        "Mock Diffusion Preview",
        "",
        "Positive prompt:",
        textwrap.fill(prompt_result["positivePrompt"], width=54),
        "",
        "Negative prompt:",
        textwrap.fill(prompt_result["negativePrompt"], width=54),
    ]
    summary_text = "\n".join(summary_lines)
    escaped_text = html.escape(summary_text)

    svg = f"""<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"768\" height=\"768\" viewBox=\"0 0 768 768\">\n<defs>\n  <linearGradient id=\"bg\" x1=\"0\" x2=\"1\" y1=\"0\" y2=\"1\">\n    <stop offset=\"0%\" stop-color=\"#f4efe6\"/>\n    <stop offset=\"100%\" stop-color=\"#d7e7f5\"/>\n  </linearGradient>\n</defs>\n<rect width=\"768\" height=\"768\" fill=\"url(#bg)\"/>\n<circle cx=\"384\" cy=\"250\" r=\"120\" fill=\"#ffffff\" fill-opacity=\"0.55\"/>\n<rect x=\"88\" y=\"360\" width=\"592\" height=\"260\" rx=\"28\" fill=\"#ffffff\" fill-opacity=\"0.78\"/>\n<text x=\"384\" y=\"128\" text-anchor=\"middle\" font-family=\"Segoe UI, Arial, sans-serif\" font-size=\"34\" font-weight=\"700\" fill=\"#1f2937\">Diffusion Demo</text>\n<text x=\"384\" y=\"176\" text-anchor=\"middle\" font-family=\"Segoe UI, Arial, sans-serif\" font-size=\"20\" fill=\"#334155\">Model not configured yet, prompt pipeline is working.</text>\n<text x=\"120\" y=\"404\" font-family=\"Consolas, Menlo, monospace\" font-size=\"20\" fill=\"#111827\" xml:space=\"preserve\">{escaped_text}</text>\n</svg>"""
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")


def generate_via_huggingface(prompt_result: dict) -> dict:
    try:
        from huggingface_hub import InferenceClient
    except ImportError as exc:
        return {
            "backend": "huggingface-error",
            "note": f"Hugging Face backend requested but missing dependencies: {exc}",
            "fallbackPreviewUrl": render_mock_svg(prompt_result),
        }

    token = os.environ.get("HF_TOKEN", "").strip()
    if not token:
        return {
            "backend": "huggingface-error",
            "note": "Hugging Face backend requested but HF_TOKEN is not set.",
            "fallbackPreviewUrl": render_mock_svg(prompt_result),
        }

    model_id = os.environ.get("HF_TEXT_TO_IMAGE_MODEL", "black-forest-labs/FLUX.1-schnell").strip()
    provider = os.environ.get("HF_PROVIDER", "").strip()
    client_kwargs = {"api_key": token}
    if provider:
        client_kwargs["provider"] = provider

    request_kwargs = {
        "prompt": prompt_result["positivePrompt"],
        "negative_prompt": prompt_result["negativePrompt"],
        "model": model_id,
    }

    width = prompt_result["generation"]["width"]
    height = prompt_result["generation"]["height"]
    steps = prompt_result["generation"]["numInferenceSteps"]
    guidance_scale = prompt_result["generation"]["guidanceScale"]

    if model_id != "black-forest-labs/FLUX.1-schnell":
        request_kwargs["width"] = width
        request_kwargs["height"] = height
        request_kwargs["num_inference_steps"] = steps
        request_kwargs["guidance_scale"] = guidance_scale

    try:
        client = InferenceClient(**client_kwargs)
        image = client.text_to_image(**request_kwargs)
    except TypeError:
        fallback_kwargs = {
            "prompt": prompt_result["positivePrompt"],
            "model": model_id,
        }
        try:
            client = InferenceClient(**client_kwargs)
            image = client.text_to_image(**fallback_kwargs)
        except Exception as exc:
            return {
                "backend": "huggingface-error",
                "note": f"Hugging Face text-to-image request failed: {exc}",
                "model": model_id,
                "fallbackPreviewUrl": render_mock_svg(prompt_result),
            }
    except Exception as exc:
        return {
            "backend": "huggingface-error",
            "note": f"Hugging Face text-to-image request failed: {exc}",
            "model": model_id,
            "fallbackPreviewUrl": render_mock_svg(prompt_result),
        }

    output_name = f"generated-{uuid4().hex[:12]}.png"
    output_path = STATIC_DIR / output_name
    image.save(output_path)

    metadata_name = f"generated-{uuid4().hex[:12]}.json"
    metadata_path = STATIC_DIR / metadata_name
    metadata_path.write_text(
        json.dumps(
            {
                "model": model_id,
                "prompt": prompt_result,
                "request": request_kwargs,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return {
        "backend": "huggingface",
        "imageUrl": f"/static/{output_name}",
        "note": f"Generated with {model_id} via Hugging Face.",
        "model": model_id,
        "metadataUrl": f"/static/{metadata_name}",
    }


def generate_via_remote(prompt_result: dict) -> dict:
    remote_url = os.environ.get("DIFFUSION_REMOTE_URL", "").strip()
    if not remote_url:
        return {
            "backend": "mock",
            "imageUrl": render_mock_svg(prompt_result),
            "note": "Remote backend requested but DIFFUSION_REMOTE_URL is not set.",
        }

    endpoint = remote_url.rstrip("/") + "/generate"
    request_body = json.dumps(
        {
            "prompt": prompt_result["positivePrompt"],
            "negative_prompt": prompt_result["negativePrompt"],
            "width": prompt_result["generation"]["width"],
            "height": prompt_result["generation"]["height"],
            "num_inference_steps": prompt_result["generation"]["numInferenceSteps"],
            "guidance_scale": prompt_result["generation"]["guidanceScale"],
        }
    ).encode("utf-8")

    request = Request(
        endpoint,
        data=request_body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=180) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        return {
            "backend": "mock",
            "imageUrl": render_mock_svg(prompt_result),
            "note": f"Remote backend request failed: {exc}",
        }

    image_base64 = payload.get("image_base64")
    if not image_base64:
        return {
            "backend": "mock",
            "imageUrl": render_mock_svg(prompt_result),
            "note": "Remote backend succeeded but did not return image_base64.",
        }

    return {
        "backend": "remote",
        "imageUrl": f"data:image/png;base64,{image_base64}",
        "note": payload.get("note", f"Generated by remote backend at {remote_url}."),
    }


def try_generate_with_diffusers(prompt_result: dict) -> dict:
    backend = os.environ.get("DIFFUSION_BACKEND", "mock").lower()
    if backend == "remote":
        return generate_via_remote(prompt_result)
    if backend == "huggingface":
        return generate_via_huggingface(prompt_result)
    if backend != "diffusers":
        return {
            "backend": "mock",
            "imageUrl": render_mock_svg(prompt_result),
            "note": "Mock mode is active. Set DIFFUSION_BACKEND=huggingface or diffusers to generate real images.",
        }

    try:
        import torch
        from diffusers import HunyuanDiTPipeline, StableDiffusionPipeline, StableDiffusionXLPipeline
    except ImportError as exc:
        return {
            "backend": "mock",
            "imageUrl": render_mock_svg(prompt_result),
            "note": f"Diffusers backend requested but missing dependencies: {exc}",
        }

    model_id = os.environ.get("DIFFUSION_MODEL_ID", "segmind/small-sd")
    model_source = model_id
    local_model_path = Path(model_id).expanduser()
    if local_model_path.exists():
        model_source = str(local_model_path)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model_family = "sd15"
    if model_id == "segmind/SSD-1B":
        model_family = "sdxl"
    if "hunyuandit" in model_id.lower():
        model_family = "hunyuan"

    if local_model_path.exists() and local_model_path.is_dir():
        model_index_path = local_model_path / "model_index.json"
        if model_index_path.exists():
            try:
                model_index = json.loads(model_index_path.read_text(encoding="utf-8"))
                class_name = str(model_index.get("_class_name", "")).lower()
                if "hunyuan" in class_name:
                    model_family = "hunyuan"
                elif "stablediffusionxl" in class_name:
                    model_family = "sdxl"
                elif "stablediffusion" in class_name:
                    model_family = "sd15"
            except Exception:
                pass

    cached_model_id = getattr(try_generate_with_diffusers, "_model_id", None)
    if not hasattr(try_generate_with_diffusers, "_pipeline") or cached_model_id != model_source:
        dtype = torch.float16 if device == "cuda" else torch.float32
        try:
            if model_family == "hunyuan":
                pipeline = HunyuanDiTPipeline.from_pretrained(
                    model_source,
                    torch_dtype=dtype,
                    local_files_only=local_model_path.exists(),
                )
            elif model_family == "sdxl":
                pipeline = StableDiffusionXLPipeline.from_pretrained(
                    model_source,
                    torch_dtype=dtype,
                    local_files_only=local_model_path.exists(),
                )
            else:
                pipeline = StableDiffusionPipeline.from_pretrained(
                    model_source,
                    torch_dtype=dtype,
                    local_files_only=local_model_path.exists(),
                )
        except Exception as exc:
            return {
                "backend": "diffusers-error",
                "imageUrl": "",
                "note": f"Failed to load diffusers model {model_source}: {exc}",
            }

        pipeline = pipeline.to(device)
        try:
            pipeline.enable_attention_slicing()
        except Exception:
            pass

        try_generate_with_diffusers._pipeline = pipeline
        try_generate_with_diffusers._model_id = model_source
        try_generate_with_diffusers._model_family = model_family

    pipeline = try_generate_with_diffusers._pipeline
    num_inference_steps = prompt_result["generation"]["numInferenceSteps"]
    guidance_scale = prompt_result["generation"]["guidanceScale"]
    width = prompt_result["generation"]["width"]
    height = prompt_result["generation"]["height"]
    prompt_text = prompt_result["positivePrompt"]

    if model_family == "hunyuan":
        prompt_text = prompt_result.get("positivePromptZh") or prompt_result["positivePrompt"]
    elif model_family == "sdxl":
        num_inference_steps = max(8, min(num_inference_steps, 30))
        guidance_scale = 9.0 if guidance_scale <= 0 else guidance_scale
        width = max(768, width)
        height = max(768, height)

    result = pipeline(
        prompt=prompt_text,
        negative_prompt=prompt_result["negativePrompt"],
        num_inference_steps=num_inference_steps,
        guidance_scale=guidance_scale,
        width=width,
        height=height,
    )
    image = result.images[0]
    image_path = BASE_DIR / "static" / "generated-output.png"
    image.save(image_path)
    source_note = "local files" if local_model_path.exists() else "huggingface cache"
    return {
        "backend": "diffusers",
        "imageUrl": "/static/generated-output.png",
        "note": f"Generated with {model_source} on {device}. Prompt language: {'Chinese' if model_family == 'hunyuan' else 'English'}. Source: {source_note}.",
    }


class AppHandler(BaseHTTPRequestHandler):
    def _send_json(self, payload: dict, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, file_path: Path, content_type: str) -> None:
        body = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> dict | None:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length)
        try:
            return json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            return None

    def _parse_edit_form(self) -> tuple[dict, bytes, str | None]:
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": self.headers.get("Content-Type", ""),
            },
        )

        payload_raw = form.getvalue("payload")
        if payload_raw:
            payload = json.loads(payload_raw)
        else:
            payload = {
                "selections": json.loads(form.getvalue("selections", "{}")),
                "customPromptZh": form.getvalue("customPromptZh", ""),
                "editInstructionZh": form.getvalue("editInstructionZh", ""),
            }
            for key in [
                "width",
                "height",
                "numInferenceSteps",
                "guidanceScale",
                "currentImageUrl",
                "currentImageDataUrl",
                "useCurrentResult",
                "backgroundId",
                "placement",
                "scalePreset",
                "applyBackgroundOnGenerate",
            ]:
                value = form.getvalue(key)
                if value not in (None, ""):
                    payload[key] = value

        if "image" in form and getattr(form["image"], "file", None):
            image_field = form["image"]
            image_bytes = image_field.file.read()
            image_name = image_field.filename or "uploaded-image.png"
            return payload, image_bytes, image_name

        image_bytes, image_name = resolve_edit_source_from_payload(payload)
        return payload, image_bytes, image_name

    def _guess_static_content_type(self, file_path: Path) -> str:
        suffix = file_path.suffix.lower()
        return {
            ".js": "application/javascript; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
            ".json": "application/json; charset=utf-8",
            ".svg": "image/svg+xml",
        }.get(suffix, "application/octet-stream")

    def do_GET(self) -> None:
        route = urlparse(self.path).path
        if route == "/":
            self._send_file(STATIC_DIR / "index.html", "text/html; charset=utf-8")
            return
        if route.startswith("/static/"):
            relative_path = route.removeprefix("/static/")
            file_path = (STATIC_DIR / relative_path).resolve()
            if STATIC_DIR.resolve() not in file_path.parents and file_path != STATIC_DIR.resolve():
                self.send_error(HTTPStatus.FORBIDDEN, "Forbidden")
                return
            if file_path.exists() and file_path.is_file():
                self._send_file(file_path, self._guess_static_content_type(file_path))
                return
            self.send_error(HTTPStatus.NOT_FOUND, "Static file not found")
            return
        if route == "/api/config":
            self._send_json(PROMPT_MAPPING)
            return
        if route == "/api/backgrounds":
            self._send_json(list_background_options())
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self) -> None:
        route = urlparse(self.path).path

        if route == "/api/generate":
            payload = self._read_json_body()
            if payload is None:
                self._send_json({"error": "Invalid JSON payload."}, status=HTTPStatus.BAD_REQUEST)
                return

            prompt_result = build_prompt(payload)
            generation_result = try_generate_with_diffusers(prompt_result)
            final_result = maybe_compose_generated_result(payload, generation_result)
            ok = not is_result_error(final_result)
            self._send_json(
                {
                    "ok": ok,
                    "prompt": prompt_result,
                    "result": final_result,
                },
                status=HTTPStatus.OK if ok else HTTPStatus.BAD_GATEWAY,
            )
            return

        if route == "/api/compose-background":
            content_type = self.headers.get("Content-Type", "")
            try:
                if content_type.startswith("multipart/form-data"):
                    payload, image_bytes, image_name = self._parse_edit_form()
                else:
                    payload = self._read_json_body()
                    if payload is None:
                        self._send_json({"error": "Invalid JSON payload."}, status=HTTPStatus.BAD_REQUEST)
                        return
                    image_bytes, image_name = resolve_edit_source_from_payload(payload)
            except ValueError as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            except json.JSONDecodeError:
                self._send_json({"error": "Invalid JSON in compose request."}, status=HTTPStatus.BAD_REQUEST)
                return

            compose_result = compose_background_scene(payload, image_bytes)
            self._send_json(
                {
                    "ok": compose_result.get("backend") != "compose-error",
                    "inputImageName": image_name,
                    "result": compose_result,
                },
                status=HTTPStatus.OK if compose_result.get("backend") != "compose-error" else HTTPStatus.BAD_GATEWAY,
            )
            return

        if route == "/api/edit":
            content_type = self.headers.get("Content-Type", "")
            try:
                if content_type.startswith("multipart/form-data"):
                    payload, image_bytes, image_name = self._parse_edit_form()
                else:
                    payload = self._read_json_body()
                    if payload is None:
                        self._send_json({"error": "Invalid JSON payload."}, status=HTTPStatus.BAD_REQUEST)
                        return
                    image_bytes, image_name = resolve_edit_source_from_payload(payload)
            except ValueError as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            except json.JSONDecodeError:
                self._send_json({"error": "Invalid JSON in edit request."}, status=HTTPStatus.BAD_REQUEST)
                return

            prompt_result = build_prompt(payload)
            edit_backend = os.environ.get("DIFFUSION_BACKEND", "mock").lower()
            if edit_backend == "diffusers":
                edit_result = generate_edit_via_diffusers(prompt_result, image_bytes, payload)
            else:
                edit_result = generate_edit_via_huggingface(prompt_result, image_bytes, payload)
            self._send_json(
                {
                    "ok": edit_result.get("backend") != "edit-error",
                    "inputImageName": image_name,
                    "prompt": prompt_result,
                    "result": edit_result,
                },
                status=HTTPStatus.OK if edit_result.get("backend") != "edit-error" else HTTPStatus.BAD_GATEWAY,
            )
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not found")


def main() -> None:
    host = "127.0.0.1"
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer((host, port), AppHandler)
    print(f"Server running at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
