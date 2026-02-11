import concurrent.futures
import os
import time

import google.generativeai as genai
from PIL import Image

# --- 設定 ---
KEY_FILE = "gemini_api_key.txt"
INPUT_DIR = "pages"
OUTPUT_DIR = "test_parallel_ultra"  # 別フォルダ
MAX_WORKERS = 5  # 並列数（5推奨）

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
   - 漢字の認識ミスを文脈から判断して修正してください。

3. **出力形式**:
   - Markdownのテキストのみ。
"""


def load_key():
    with open(KEY_FILE, "r") as f:
        return f.read().strip()


def process_page_parallel(task):
    image_path, out_path, model_name, page_num = task
    print(f"Starting {page_num} using {model_name}...")

    genai.configure(api_key=load_key())
    model = genai.GenerativeModel(model_name)

    max_retries = 3
    for attempt in range(max_retries):
        try:
            img = Image.open(image_path)
            # トークン節約と安定性のためのリサイズ
            img.thumbnail((2560, 2560))

            response = model.generate_content([PROMPT, img])

            with open(out_path, "w", encoding="utf-8") as f:
                f.write(response.text)

            print(f"Done Page {page_num}")
            return True
        except Exception as e:
            if "429" in str(e):
                wait = 30 * (attempt + 1)
                print(f"Quota error on {page_num}. Waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"Error on {page_num}: {e}")
                return False
    return False


def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # テスト対象ページ (P8-P12の5ページ分)
    pages_to_test = ["008", "009", "010", "011", "012"]
    tasks = []

    # モデル分散ルーチン
    models = ["gemini-3-flash-preview", "gemini-2.5-flash"]

    for i, p_num in enumerate(pages_to_test):
        img_path = os.path.join(INPUT_DIR, f"page_{p_num}.png")
        out_path = os.path.join(OUTPUT_DIR, f"page_{p_num}.md")
        # モデルを交互に割り当て
        model_name = models[i % len(models)]
        tasks.append((img_path, out_path, model_name, p_num))

    print(f"Starting parallel small test ({MAX_WORKERS} workers)...")
    start_time = time.time()

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=MAX_WORKERS
    ) as executor:
        executor.map(process_page_parallel, tasks)

    end_time = time.time()
    print(f"Test Complete in {end_time - start_time:.2f}s")


if __name__ == "__main__":
    main()
