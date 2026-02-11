import base64
import os

import requests


def test_vision_api():
    # Load Key
    try:
        with open("api_key.txt", "r") as f:
            api_key = f.read().strip()
    except:
        print("Error: api_key.txt not found")
        return

    print(f"Testing Key: {api_key[:5]}...{api_key[-5:]}")

    # Load Image (Page 1)
    img_path = "pages/page_001.png"
    if not os.path.exists(img_path):
        print("Error: Page 1 image not found")
        return

    with open(img_path, "rb") as img_file:
        img_content = base64.b64encode(img_file.read()).decode("utf-8")

    # Construct Request
    url = f"https://vision.googleapis.com/v1/images:annotate?key={api_key}"

    payload = {
        "requests": [
            {
                "image": {"content": img_content},
                "features": [{"type": "DOCUMENT_TEXT_DETECTION"}],
            }
        ]
    }

    # Send Request
    try:
        response = requests.post(url, json=payload)
        data = response.json()

        if "error" in data:
            print(f"API Error: {data['error']['message']}")
            print(f"Status: {data['error']['code']}")
        elif "responses" in data:
            text = data["responses"][0].get("fullTextAnnotation", {}).get("text", "")
            if text:
                print("Success! Vision API returned text.")
                print(f"Preview: {text[:50]}...")
            else:
                print("Success, but no text found (unexpected for text page).")
        else:
            print("Unknown response format.")
            print(str(data)[:200])

    except Exception as e:
        print(f"Request Failed: {e}")


if __name__ == "__main__":
    test_vision_api()
