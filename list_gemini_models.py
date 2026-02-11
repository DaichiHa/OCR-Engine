
import google.generativeai as genai


def load_key():
    with open("gemini_api_key.txt", "r") as f:
        return f.read().strip()


genai.configure(api_key=load_key())

print("Available models and their supported methods:")
for m in genai.list_models():
    if "generateContent" in m.supported_generation_methods:
        print(f"Model: {m.name}")
