import os
from huggingface_hub import InferenceClient

client = InferenceClient(
    provider="fal-ai",
    api_key=os.environ["HF_TOKEN"],
)

image = client.text_to_image(
    prompt="""
masterpiece, best quality, highly detailed, fresh school-life illustration,
bright youthful atmosphere, high ponytail hairstyle, cool distant gaze,
sharp refined eyes, small beauty mark under the eye,
handsome schoolboy with polished campus-idol look, stylish over-ear headphones,
side-profile composition, wearing headphones, immersed in music,
inside a quiet school library, cool distant mood, reserved expression
""",
    model="krea/Krea-2-Turbo",
)

image.save("krea_test.png")
print("saved to krea_test.png")