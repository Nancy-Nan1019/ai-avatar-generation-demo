import os
from pathlib import Path

from huggingface_hub import InferenceClient


PROMPT = """
masterpiece, best quality, highly detailed, xianxia fantasy illustration,
elegant ancient chinese aesthetic, flowing hanfu outfit, traditional chinese clothing,
traditional chinese courtyard, elegant architectural setting, natural seated pose,
cool distant mood, reserved expression, square-crop friendly composition, centered subject
""".strip()


def main() -> None:
    token = os.environ.get("HF_TOKEN")
    if not token:
        raise RuntimeError("HF_TOKEN is not set. Please export your Hugging Face token first.")

    client = InferenceClient(
        provider="fal-ai",
        api_key=token,
    )

    image = client.text_to_image(
        prompt=PROMPT,
        model="Tongyi-MAI/Z-Image-Turbo",
    )

    output_path = Path("zimage_xianxia_test.png")
    image.save(output_path)
    print(f"saved to {output_path.resolve()}")


if __name__ == "__main__":
    main()
