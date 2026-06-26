import os
from pathlib import Path

from huggingface_hub import InferenceClient


PROMPT = """
masterpiece, best quality, highly detailed, fresh school-life illustration,
bright youthful atmosphere, cool distant gaze,
sharp refined eyes, small beauty mark under the eye,
handsome schoolboy with polished campus-idol look, stylish over-ear headphones,
side-profile composition, wearing headphones, immersed in music,
inside a quiet school library, cool distant mood, reserved expression,
centered face, full head visible, avatar-friendly composition
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

    output_path = Path("zimage_test3.png")
    image.save(output_path)
    print(f"saved to {output_path.resolve()}")


if __name__ == "__main__":
    main()
