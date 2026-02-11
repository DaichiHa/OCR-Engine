import concurrent.futures
import os
import time

import google.generativeai as genai
from PIL import Image

# --- 設定 ---
KEY_FILE = "gemini_api_key.txt"
INPUT_DIR = "pages"
OUTPUT_DIR = "test_stable_multi_model"
MODELS = ["gemini-3-flash-preview", "gemini-2.5-flash", "gemini-2.0-flash-001"]
BATCH_SIZE = len(MODELS)  # 一度に3枚ずつ
COOLDOWN = 65  # 確実に1分を超えるクールダウン

PROMPT = """
あなたは歴史的な公文書（明治時代の日本の統計資料）をデジタル化する専門家です。
この画像を解析し、以下の指示に従ってMarkdown形式で出力してください。

1. **テキストページ（序文・緒言など）**:
   - 縦書きの文章を、日本語の自然な順序で正しく書き起こしてください。
   - 旧字体や助詞（ニ、ヲ、ハ）もそのまま再現してください。

2. **統計表ページ**:
   - 表の行列を1マスもずらさずにMarkdownテーブルで再現してください。
   - 単位（石、噸、圓、斤など）を正確に含めてください。
   - コンマ（,）の位置も正確に再現してください。

3. **出力形式**:
   - Markdownの本文のみ。
"""


def load_key():
    with open(KEY_FILE, "r") as f:
        return f.read().strip()


def process_page_stable(task):
    image_path, out_path, model_name, page_num = task
    print(f"[Start] Page {page_num} | Model: {model_name}")

    genai.configure(api_key=load_key())
    model = genai.GenerativeModel(model_name)

    try:
        img = Image.open(image_path)
        img.thumbnail((2048, 2048))
        response = model.generate_content([PROMPT, img])

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(response.text)

        print(f"[Done]  Page {page_num} via {model_name}")
        return True
    except Exception as e:
        print(f"[Error] Page {page_num} on {model_name}: {e}")
        return False


def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # テスト対象ページ (P24-P29: 2回分のバッチ)
    test_pages = [f"{i:03}" for i in range(24, 30)]

    print(f"--- Stable Multi-Model Test (Batch Size: {BATCH_SIZE}, Cooldown: {COOLDOWN}s) ---")
    start_time = time.time()

    # 3ページずつのバッチ処理
    for i in range(0, len(test_pages), BATCH_SIZE):
        batch = test_pages[i : i + BATCH_SIZE]
        tasks = []
        for j, p_num in enumerate(batch):
            img_path = os.path.join(INPUT_DIR, f"page_{p_num}.png")
            out_path = os.path.join(OUTPUT_DIR, f"page_{p_num}.md")
            tasks.append((img_path, out_path, MODELS[j], p_num))

        print(f"\n[Batch] Starting Batch {i//BATCH_SIZE + 1}...")

        with concurrent.futures.ThreadPoolExecutor(max_workers=BATCH_SIZE) as executor:
            executor.map(process_page_stable, tasks)

        if i + BATCH_SIZE < len(test_pages):
            print(f"[Wait] Cooling down for {COOLDOWN}s to reset ALL models' quotas...")
            time.sleep(COOLDOWN)

    print(f"\n--- Multi-Model Test Complete in {time.time() - start_time:.2f}s ---")


if __name__ == "__main__":
    main()
