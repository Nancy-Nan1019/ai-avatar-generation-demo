import base64
from io import BytesIO

import torch
from diffusers import StableDiffusionPipeline
from fastapi import FastAPI
from pydantic import BaseModel


MODEL_ID = "runwayml/stable-diffusion-v1-5"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
DTYPE = torch.float16 if DEVICE == "cuda" else torch.float32

app = FastAPI(title="Colab Diffusion Server")
pipeline = StableDiffusionPipeline.from_pretrained(MODEL_ID, torch_dtype=DTYPE)
pipeline = pipeline.to(DEVICE)

if DEVICE == "cuda":
    pipeline.enable_attention_slicing()


class GenerateRequest(BaseModel):
    prompt: str
    negative_prompt: str = ""
    width: int = 512
    height: int = 512
    num_inference_steps: int = 20
    guidance_scale: float = 6.0


@app.get("/health")
def health() -> dict:
    return {"ok": True, "model": MODEL_ID, "device": DEVICE}


@app.post("/generate")
def generate(request: GenerateRequest) -> dict:
    result = pipeline(
        prompt=request.prompt,
        negative_prompt=request.negative_prompt,
        width=request.width,
        height=request.height,
        num_inference_steps=request.num_inference_steps,
        guidance_scale=request.guidance_scale,
    )
    image = result.images[0]
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return {
        "image_base64": image_base64,
        "note": f"Generated with {MODEL_ID} on {DEVICE} in Colab.",
    }
