
import google.generativeai as genai

api_key = open('gemini_api_key.txt').read().strip()
genai.configure(api_key=api_key)

with open('all_models.txt', 'w') as f:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            f.write(f"{m.name}\n")
print("Done")
