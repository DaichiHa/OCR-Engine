
import os
import glob
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
   - Markdownのテキストのみ。前後の説明（Here is the table...等）は一切不要です。
"""

def load_key():
    with open(KEY_FILE, "r") as f:
        return f.read().strip()

def process_page_ultra(model, image_path, page_num):
    print(f"Processing Page {page_num} [ULTRA MODE]...")
    max_retries = 5
    quota_delay = 90
    
    for attempt in range(max_retries):
        try:
            img = Image.open(image_path)
            if img.width > 3000 or img.height > 3000:
                img.thumbnail((3072, 3072))
            
            response = model.generate_content([PROMPT, img])
            return response.text
        except Exception as e:
            err_str = str(e)
            if "429" in err_str:
                print(f"Quota exceeded. Waiting {quota_delay}s... (Attempt {attempt+1}/{max_retries})")
                time.sleep(quota_delay)
            elif "500" in err_str or "503" in err_str:
                print("Server error. Waiting 10s...")
                time.sleep(10)
            else:
                return f"Error: {err_str}"
    return "Error: Failed"

def main():
    api_key = load_key()
    genai.configure(api_key=api_key)
    
    # 複数のモデルを候補に入れ、制限回避を狙う
    # gemini-3-flash-preview は最新の試験運用版で、制限が別枠の可能性があります
    model_name = 'gemini-3-flash-preview' 
    print(f"Using model: {model_name}")
    model = genai.GenerativeModel(model_name)

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # 全ページを取得し、数値順にソート
    files = sorted(glob.glob(os.path.join(INPUT_DIR, "page_*.png")))
    
    # 全ページ処理 (151ページすべて)
    for file_path in files:
        filename = os.path.basename(file_path)
        page_num = filename.replace("page_", "").replace(".png", "")
        out_path = os.path.join(OUTPUT_DIR, f"page_{page_num}.md")
        
        # 既存ファイルはスキップ（レジューム機能）
        if os.path.exists(out_path) and os.path.getsize(out_path) > 100:
            print(f"Skipping {filename}")
            continue

        result = process_page_ultra(model, file_path, page_num)
        
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(result)
        
        if "Error" not in result:
            print(f"Page {page_num} Success. Cooling down for 15s...")
            time.sleep(15) 
        else:
            print(f"Page {page_num} Failed: {result}")
            # エラー時は長めに待機
            time.sleep(60)

    print("--- ULTRA PROCESSING COMPLETE ---")

if __name__ == "__main__":
    main()
