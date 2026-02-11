import os
import time

import google.generativeai as genai
from PIL import Image

# --- 設定 (5ページ・バッチ・チェック・モード) ---
KEY_FILE = "gemini_api_key.txt"
INPUT_DIR = "pages_ultra_preprocessed"
OUTPUT_DIR = "intermediate_md_ultra_final"
BATCH_SIZE = 5
INTERVAL = 60  # 安定の60秒

# 【究極・正確性特化型プロンプト】
PROMPT = """
あなたは歴史的統計資料のデジタル化専門プログラムです。
画像内の情報を、以下の『絶対規則』に従って100%正確に書き起こしてください。

[絶対規則]
1. 思考・解説・挨拶は一切不要。出力はMarkdown形式の書き起こしのみとせよ。
2. 統計表は行列を1マスもズラさずMarkdownテーブルで完璧に再現せよ。
3. 漢字はすべて原典のまま（旧字体・異体字を維持。例：港灣、價額、數量、噸、圓、國）。
4. 数値、コンマ（,）、単位（石、斤、噸、圓等）を1文字も漏らさず正確に記載せよ。
5. 縦書きの文章は日本語の正しい順序で、助詞（ニ、ヲ、ハ）も正確に再現せよ。
6. 不鮮明な箇所は文脈から判断し、確定した文字を出力せよ。
"""


def load_key():
    with open(KEY_FILE, "r") as f:
        return f.read().strip()


def process_page(file_path, out_path, model):
    page_num = (
        os.path.basename(file_path).replace("page_", "").replace(".png", "")
    )
    print(f"[{time.strftime('%H:%M:%S')}] Processing Page {page_num}...")

    try:
        img = Image.open(file_path)
        img.thumbnail((3072, 3072))
        response = model.generate_content([PROMPT, img])

        if response.text and len(response.text) > 10:
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(response.text)
            print(f"   Done: {page_num}")
            return True
        return False
    except Exception as e:
        print(f"   Error: {e}")
        return False


def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    api_key = load_key()
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash")

    all_pages = [f"page_{i:03}.png" for i in range(1, 152)]
    processed_this_batch = 0

    print("--- 5-PAGE BATCH MODE START ---")

    for filename in all_pages:
        if processed_this_batch >= BATCH_SIZE:
            break

        img_path = os.path.join(INPUT_DIR, filename)
        if not os.path.exists(img_path):
            continue

        out_path = os.path.join(OUTPUT_DIR, filename.replace(".png", ".md"))
        if os.path.exists(out_path) and os.path.getsize(out_path) > 100:
            continue

        if process_page(img_path, out_path, model):
            processed_this_batch += 1
            if processed_this_batch < BATCH_SIZE:
                print(f"   Cooling down {INTERVAL}s...")
                time.sleep(INTERVAL)
            else:
                print("   Waiting for retry...")
            time.sleep(120)

    print(f"\n--- Batch of {processed_this_batch} Pages Complete ---")


if __name__ == "__main__":
    main()
