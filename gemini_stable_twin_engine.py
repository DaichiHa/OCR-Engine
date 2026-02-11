
import os
import glob
import time
import concurrent.futures
import google.generativeai as genai
from PIL import Image

# --- 設定 ---
KEY_FILE = "gemini_api_key.txt"
INPUT_DIR = "pages"
OUTPUT_DIR = "intermediate_md_ultra_final"
MAX_WORKERS = 2 # 安定型ツイン・エンジン（2並列）

# クォータを分散させるためのモデルプール
MODELS = ["gemini-3-flash-preview", "gemini-2.5-flash"]
COOLDOWN = 30 # 1リクエストごとの待機時間

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
   - Markdownの本文のみ。余計な説明は不要です。
"""

def load_key():
    with open(KEY_FILE, "r") as f:
        return f.read().strip()

def process_page_stable(task):
    file_path, out_path, model_name, page_num = task
    
    # スキップ判定
    if os.path.exists(out_path) and os.path.getsize(out_path) > 100:
        return True

    print(f"[Starting] Page {page_num} | {model_name}")
    
    genai.configure(api_key=load_key())
    model = genai.GenerativeModel(model_name)
    
    max_retries = 5
    for attempt in range(max_retries):
        try:
            img = Image.open(file_path)
            img.thumbnail((2560, 2560))
            
            response = model.generate_content([PROMPT, img])
            
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(response.text)
            
            print(f"[Success]  Page {page_num} | {model_name}")
            # 安定走行のためのインターバル
            time.sleep(COOLDOWN)
            return True
        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg or "402" in err_msg:
                wait = 60 + (attempt * 30)
                print(f"[Limit] Page {page_num} on {model_name}. Cooling down {wait}s...")
                time.sleep(wait)
            else:
                print(f"[Error] Page {page_num}: {err_msg}")
                time.sleep(10)
    return False

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    files = sorted(glob.glob(os.path.join(INPUT_DIR, "page_*.png")))
    tasks = []
    
    # モデルを交互に割り当て
    for i, file_path in enumerate(files):
        filename = os.path.basename(file_path)
        page_num = filename.replace("page_", "").replace(".png", "")
        out_path = os.path.join(OUTPUT_DIR, f"page_{page_num}.md")
        model_name = MODELS[i % len(MODELS)]
        tasks.append((file_path, out_path, model_name, page_num))

    print("--- LAUNCHING STABLE TWIN-ENGINE OCR ---")
    print(f"Total: {len(tasks)} pages | Parallel: {MAX_WORKERS} | Target Cooldown: {COOLDOWN}s")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        executor.map(process_page_stable, tasks)

    print("--- ALL PROCESSING COMPLETE ---")

if __name__ == "__main__":
    main()
