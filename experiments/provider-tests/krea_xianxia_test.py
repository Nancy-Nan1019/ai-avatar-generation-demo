import os
from huggingface_hub import InferenceClient

client = InferenceClient(
    provider="fal-ai",
    api_key=os.environ["HF_TOKEN"],
)

image = client.text_to_image(
    prompt="""
masterpiece, best quality, highly detailed, xianxia fantasy illustration,
elegant ancient chinese aesthetic, flowing hanfu outfit, traditional chinese clothing,
traditional chinese courtyard, elegant architectural setting, natural seated pose,
cool distant mood, reserved expression, square-crop friendly composition, centered subject
""",
    model="krea/Krea-2-Turbo",
)

image.save("krea_xianxia_test.png")
print("saved to krea_xianxia_test.png")