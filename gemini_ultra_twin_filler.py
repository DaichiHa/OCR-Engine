import concurrent.futures
import glob
import os
import time

import google.generativeai as genai
from PIL import Image

# --- 配置 ---
KEY_FILE = "gemini_api_key.txt"
INPUT_DIR = "pages"
OUTPUT_DIR = "intermediate_md_ultra_final"
MAX_WORKERS = 2  # 2本並列
INTERVAL = (
    90  # 各スレッドが処理後に置くインターバル（並列時は長めに設定して干渉を防ぐ）
)

# 利用可能なモデル（系統を分けてクォータ分散を狙う）
MODELS = ["gemini-2.0-flash", "gemini-3-flash-preview"]

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


def process_page_twin(task):
    img_path, out_path, model_name, page_num = task

    # スキップ判定
    if os.path.exists(out_path) and os.path.getsize(out_path) > 100:
        return True

    print(f"[{time.strftime('%H:%M:%S')}] Starting Page {page_num} on {model_name}")

    api_key = load_key()
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)

    max_retries = 3
    for attempt in range(max_retries):
        try:
            img = Image.open(img_path)
            img.thumbnail((3072, 3072))

            response = model.generate_content([PROMPT, img])

            with open(out_path, "w", encoding="utf-8") as f:
                f.write(response.text)

            print(
                f"[{time.strftime('%H:%M:%S')}] Success: Page {page_num} ({model_name})"
            )
            time.sleep(INTERVAL)
            return True
        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg or "402" in err_msg:
                wait = 120 + (attempt * 60)
                print(f"[Limit] Page {page_num} ({model_name}). Cooling {wait}s...")
                time.sleep(wait)
            else:
                print(f"[Error] Page {page_num}: {err_msg}")
                time.sleep(10)
    return False


def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    all_files = sorted(glob.glob(os.path.join(INPUT_DIR, "page_*.png")))
    tasks = []

    for i, file_path in enumerate(all_files):
        filename = os.path.basename(file_path)
        page_num = filename.replace("page_", "").replace(".png", "")
        out_path = os.path.join(OUTPUT_DIR, f"page_{page_num}.md")
        model_name = MODELS[i % len(MODELS)]
        tasks.append((file_path, out_path, model_name, page_num))

    print(f"--- TWIN-ENGINE ULTRA FILLER START (Workers: {MAX_WORKERS}) ---")

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        executor.map(process_page_twin, tasks)

    print("--- PROCESS FINISHED ---")


if __name__ == "__main__":
    main()
