import os
import time

import google.generativeai as genai
from PIL import Image

# --- 設定 ---
KEY_FILE = "gemini_api_key.txt"
INPUT_DIR = "pages"
OUTPUT_DIR = "intermediate_md_ultra"

# 最高精度プロンプト
PROMPT = """
あなたは歴史的な公文書（明治時代の日本の統計資料）をデジタル化する専門家です。
この画像を解析し、以下の指示に従ってMarkdown形式で出力してください。

1. **テキストページ（序文・緒言など）**:
   - 縦書きの文章を、日本語の自然な順序で正しく書き起こしてください。
   - 旧字体（例：灣、國、實、關）やカタカナ、「ニ」「ヲ」「ハ」などの助詞もそのまま再現してください。

2. **統計表ページ**:
   - 表の行列を1マスもずらさずにMarkdownテーブルで再現してください。
   - 単位（石、噸、圓、斤など）が数字の上に小さく書いてある場合は、数値の後に含めるかヘッダーに含めてください。
   - コンマ（,）の位置も正確に再現してください。
   - 漢字の認識ミス（東京を束京とする等）を文脈から判断して修正してください。

3. **出力形式**:
   - Markdownのテキストのみ。前後の説明は一切不要です。
"""


def load_key():
    with open(KEY_FILE, "r") as f:
        return f.read().strip()


def main():
    api_key = load_key()
    genai.configure(api_key=api_key)

    # 最新かつ安定している001番を指定
    model = genai.GenerativeModel("gemini-2.0-flash-001")

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # 1ページ目のみ指定
    target_page = "page_001.png"
    file_path = os.path.join(INPUT_DIR, target_page)

    print(f"Testing Ultra Mode on {target_page}...")

    try:
        img = Image.open(file_path)
        # Quotaエラーを避けるためのリトライ処理
        response = None
        for attempt in range(3):
            try:
                response = model.generate_content([PROMPT, img])
                break
            except Exception as e:
                if "429" in str(e):
                    print(f"Waiting 30s due to quota (Attempt {attempt+1})...")
                    time.sleep(30)
                else:
                    raise e

        if response:
            out_path = os.path.join(OUTPUT_DIR, "page_001.md")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(response.text)
            print(f"Success! Output saved to {out_path}")
            print("\n--- Output Preview ---")
            print(response.text)
            print("----------------------")
        else:
            print("Failed to get response.")

    except Exception as e:
        print(f"Error during test: {e}")


if __name__ == "__main__":
    main()
