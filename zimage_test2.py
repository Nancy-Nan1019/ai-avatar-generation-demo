import os
from pathlib import Path

from huggingface_hub import InferenceClient


PROMPT = """
masterpiece, best quality, highly detailed, dynamic action anime style, 
intense battle energy, dramatic anime lighting, taisho-era fantasy mood, 
sharp visual contrast, pastel macaron palette, soft sweet colors, silver-toned hair, 
striking fantasy hair color, sheathed sword accessory, passionate high-energy emotion, 
intense presence
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

    output_path = Path("zimage_test2.png")
    image.save(output_path)
    print(f"saved to {output_path.resolve()}")


if __name__ == "__main__":
    main()
