import base64
import html
import json
import os
import textwrap
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
CONFIG_PATH = BASE_DIR / "config" / "prompt-mapping.zh-en.json"


def load_mapping() -> dict:
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


PROMPT_MAPPING = load_mapping()


def build_prompt(payload: dict) -> dict:
    categories_by_id = {category["id"]: category for category in PROMPT_MAPPING["categories"]}
    positive_parts = list(PROMPT_MAPPING["generationDefaults"]["positivePrefix"])
    negative_parts = list(PROMPT_MAPPING["generationDefaults"]["negativePrompt"])
    selected_labels = []

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
            positive_parts.append(option["promptEn"])
            selected_labels.append(
                {
                    "categoryId": category_id,
                    "categoryZh": category["labelZh"],
                    "labelZh": label,
                    "promptEn": option["promptEn"],
                }
            )

    custom_prompt = str(payload.get("customPromptZh", "")).strip()
    if custom_prompt:
        positive_parts.append(f"additional concept: {custom_prompt}")

    positive_prompt = ", ".join(dict.fromkeys(part.strip() for part in positive_parts if part.strip()))
    negative_prompt = ", ".join(dict.fromkeys(part.strip() for part in negative_parts if part.strip()))

    defaults = PROMPT_MAPPING["generationDefaults"]["inference"]
    generation = {
        "width": int(payload.get("width", defaults["width"])),
        "height": int(payload.get("height", defaults["height"])),
        "numInferenceSteps": int(payload.get("numInferenceSteps", defaults["numInferenceSteps"])),
        "guidanceScale": float(payload.get("guidanceScale", defaults["guidanceScale"])),
    }

    return {
        "positivePrompt": positive_prompt,
        "negativePrompt": negative_prompt,
        "selectedOptions": selected_labels,
        "generation": generation,
    }


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
    if backend != "diffusers":
        return {
            "backend": "mock",
            "imageUrl": render_mock_svg(prompt_result),
            "note": "Mock mode is active. Set DIFFUSION_BACKEND=diffusers after installing model dependencies.",
        }

    try:
        import torch
        from diffusers import StableDiffusionPipeline
    except ImportError as exc:
        return {
            "backend": "mock",
            "imageUrl": render_mock_svg(prompt_result),
            "note": f"Diffusers backend requested but missing dependencies: {exc}",
        }

    model_id = os.environ.get("DIFFUSION_MODEL_ID", "runwayml/stable-diffusion-v1-5")
    device = "cuda" if torch.cuda.is_available() else "cpu"

    if not hasattr(try_generate_with_diffusers, "_pipeline"):
        dtype = torch.float16 if device == "cuda" else torch.float32
        pipeline = StableDiffusionPipeline.from_pretrained(model_id, torch_dtype=dtype)
        pipeline = pipeline.to(device)
        try_generate_with_diffusers._pipeline = pipeline

    pipeline = try_generate_with_diffusers._pipeline
    result = pipeline(
        prompt=prompt_result["positivePrompt"],
        negative_prompt=prompt_result["negativePrompt"],
        num_inference_steps=prompt_result["generation"]["numInferenceSteps"],
        guidance_scale=prompt_result["generation"]["guidanceScale"],
        width=prompt_result["generation"]["width"],
        height=prompt_result["generation"]["height"],
    )
    image = result.images[0]
    image_path = BASE_DIR / "static" / "generated-output.png"
    image.save(image_path)
    return {
        "backend": "diffusers",
        "imageUrl": "/static/generated-output.png",
        "note": f"Generated with {model_id} on {device}.",
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

    def do_GET(self) -> None:
        route = urlparse(self.path).path
        if route == "/":
            self._send_file(STATIC_DIR / "index.html", "text/html; charset=utf-8")
            return
        if route == "/static/app.js":
            self._send_file(STATIC_DIR / "app.js", "application/javascript; charset=utf-8")
            return
        if route == "/static/styles.css":
            self._send_file(STATIC_DIR / "styles.css", "text/css; charset=utf-8")
            return
        if route == "/static/generated-output.png":
            image_path = STATIC_DIR / "generated-output.png"
            if image_path.exists():
                self._send_file(image_path, "image/png")
                return
            self.send_error(HTTPStatus.NOT_FOUND, "Generated image not found")
            return
        if route == "/api/config":
            self._send_json(PROMPT_MAPPING)
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self) -> None:
        route = urlparse(self.path).path
        if route != "/api/generate":
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON payload."}, status=HTTPStatus.BAD_REQUEST)
            return

        prompt_result = build_prompt(payload)
        generation_result = try_generate_with_diffusers(prompt_result)
        self._send_json(
            {
                "ok": True,
                "prompt": prompt_result,
                "result": generation_result,
            }
        )


def main() -> None:
    host = "127.0.0.1"
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer((host, port), AppHandler)
    print(f"Server running at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
