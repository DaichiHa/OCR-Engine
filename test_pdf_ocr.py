import google.generativeai as genai
from PIL import Image

KEY_FILE = "gemini_api_key.txt"
IMAGE_PATH = "01190600a00002_p1.png"
OUTPUT_FILE = "test_pdf_ultra_p1.md"

PROMPT = """
あなたは歴史的な公文書（明治時代の日本の統計資料）をデジタル化する専門家です。
この画像を解析し、以下の指示に従ってMarkdown形式で出力してください。

1. **基本構成**:
   - 上部の「146」「第六表」「明治三十九年」を記載。
   - 複雑な入れ子構造の表をMarkdownテーブルで完全に再現してください。
   - 「輸入」「輸出」などの区分、および「瓦」「米」「大麦」などの品目、数量、価額、仕出地/仕向地を正確に抽出。

2. **品質基準**:
   - 旧字体（例：價額、数量、鳥取）をそのまま再現。
   - 単位（石、斤、噸、圓など）を数値に付随させて正確に記載。
   - 表が左右に分かれている場合は、Markdownの見出しや複数のテーブルを使って構造を崩さず表現してください。

3. **出力形式**:
   - Markdownのみ。説明不要。
"""


def main():
    api_key = open(KEY_FILE, "r").read().strip()
    genai.configure(api_key=api_key)
    # 現在成功している gemini-2.0-flash を使用
    model = genai.GenerativeModel("gemini-2.0-flash-lite")

    print(f"Testing the current ULTRA method on: {IMAGE_PATH}")

    try:
        img = Image.open(IMAGE_PATH)
        # 高精度維持のためリサイズせず、または大きめに維持
        img.thumbnail((3072, 3072))

        response = model.generate_content([PROMPT, img])

        content = response.text
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"Success! Result saved to {OUTPUT_FILE}")
        print("\n--- Result Preview ---")
        print(content[:1000])  # 最初の1000文字を表示
        print("--- End Preview ---")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
