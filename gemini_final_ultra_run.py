import concurrent.futures
import glob
import os
import time

import google.generativeai as genai
from PIL import Image

# --- 設定 ---
KEY_FILE = "gemini_api_key.txt"
INPUT_DIR = "pages"
OUTPUT_DIR = "intermediate_md_ultra_final"
MAX_WORKERS = 6  # 安定性を考慮し、少し絞った6並列

# モデルプール
MODEL_POOL = [
    "gemini-3-flash-preview",
    "gemini-2.5-flash",
    "gemini-2.0-flash-001",
    "gemini-2.0-flash-lite",  # Liteも追加して分散
]

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
   - Markdownの本文のみ。余計な挨拶や説明は不要です。
"""


def load_key():
    with open(KEY_FILE, "r") as f:
        return f.read().strip()


def process_page_hyper(task):
    image_path, out_path, model_name, page_num = task

    # 既存ファイルのスキップ
    if os.path.exists(out_path) and os.path.getsize(out_path) > 100:
        return True

    print(f"[Starting] Page {page_num} | {model_name}")

    genai.configure(api_key=load_key())
    model = genai.GenerativeModel(model_name)

    max_retries = 5
    for attempt in range(max_retries):
        try:
            img = Image.open(image_path)
            img.thumbnail((2048, 2048))

            response = model.generate_content([PROMPT, img])

            with open(out_path, "w", encoding="utf-8") as f:
                f.write(response.text)

            print(f"[Success]  Page {page_num} | {model_name}")
            return True
        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg:
                wait = 60  # クォータ制限時はしっかり1分休む
                print(
                    f"[Limit] Page {page_num} (429) on {model_name}. Waiting {wait}s..."
                )
                time.sleep(wait)
            elif "500" in err_msg or "503" in err_msg:
                print(f"[Server Error] Page {page_num}. Retrying in 10s...")
                time.sleep(10)
            else:
                print(f"[Error] Page {page_num}: {e}")
                time.sleep(2)
    return False


def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # 全151ページを取得
    files = sorted(glob.glob(os.path.join(INPUT_DIR, "page_*.png")))
    tasks = []

    for i, file_path in enumerate(files):
        filename = os.path.basename(file_path)
        page_num = filename.replace("page_", "").replace(".png", "")
        out_path = os.path.join(OUTPUT_DIR, f"page_{page_num}.md")
        # モデルを順繰りに割り当て
        model_name = MODEL_POOL[i % len(MODEL_POOL)]
        tasks.append((file_path, out_path, model_name, page_num))

    print("--- STARTING FINAL ULTRA RUN ---")
    print(f"Target: {len(tasks)} pages | Workers: {MAX_WORKERS}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        executor.map(process_page_hyper, tasks)

    print("--- ALL PROCESSING COMPLETE ---")


if __name__ == "__main__":
    main()
