
import os
import glob
import time
import re
import google.generativeai as genai
from PIL import Image

# --- 配置 ---
KEY_FILE = "gemini_api_key.txt"
INPUT_DIR = "pages"
OUTPUT_DIR = "intermediate_md_ultra_final"
INTERVAL = 60 # 1分おきに確実に1枚 (無料枠の最大安定速度)

# 最高精度プロンプト
PROMPT = """
あなたは歴史的な公文書（明治時代の日本の統計資料）をデジタル化する専門家です。
この画像を解析し、以下の指示に従ってMarkdown形式で出力してください。

1. **テキストページ（序文・緒言など）**:
   - 縦書きの文章を、日本語の自然な順序で正しく書き起こしてください。
   - 旧字体（例：灣、國、實、關）やカタカナ、「ニ」「ヲ」「ハ」などの助詞もそのまま再現してください。

2. **統計表ページ**:
   - 表の行列を1マスもずらさずにMarkdownテーブルで再現してください。
   - 単位（石、噸、圓、斤など）を正確に含めてください。
   - コンマ（,）の位置も正確に再現してください。
   - 漢字の認識ミス（東京を束京とする等）を文脈から判断して修正してください。

3. **出力形式**:
   - Markdownの本文のみ。説明文は一切加えないでください。
"""

def load_key():
    with open(KEY_FILE, "r") as f:
        return f.read().strip()

def process_single_page(file_path, out_path, model):
    page_num = os.path.basename(file_path).replace("page_", "").replace(".png", "")
    print(f"[{time.strftime('%H:%M:%S')}] Processing Missing Page {page_num}...")
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            img = Image.open(file_path)
            img.thumbnail((3072, 3072))
            
            response = model.generate_content([PROMPT, img])
            
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(response.text)
            
            print(f"Success: Page {page_num}")
            return True
        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg or "402" in err_msg:
                wait = 120 # 制限時は2分休む
                print(f"Quota Hit on Page {page_num}. Sleeping {wait}s...")
                time.sleep(wait)
            else:
                print(f"Error on Page {page_num}: {err_msg}")
                time.sleep(10)
    return False

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    api_key = load_key()
    genai.configure(api_key=api_key)
    # 最もバランスの良い2.0-flashを使用
    model = genai.GenerativeModel('gemini-2.0-flash')

    # 1.1~151ページまでのリストを作成
    all_pages = [f"page_{i:03}.png" for i in range(1, 152)]
    
    print("--- ULTRA QUALITY FILLER MODE START ---")
    
    for filename in all_pages:
        img_path = os.path.join(INPUT_DIR, filename)
        if not os.path.exists(img_path):
            continue
            
        md_filename = filename.replace(".png", ".md")
        out_path = os.path.join(OUTPUT_DIR, md_filename)
        
        # 既に存在し、かつ中身がある場合は飛ばす
        if os.path.exists(out_path) and os.path.getsize(out_path) > 100:
            continue
            
        # 未処理のページを処理
        success = process_single_page(img_path, out_path, model)
        
        if success:
            # 完了ごとにインターバルを置く
            print(f"Waiting {INTERVAL}s for next token bucket reset...")
            time.sleep(INTERVAL)
        else:
            print(f"Failed to process Page {filename} after retries. Moving to next.")

    print("--- ALL PAGES COMPLETED OR SKIPPED ---")

if __name__ == "__main__":
    main()
