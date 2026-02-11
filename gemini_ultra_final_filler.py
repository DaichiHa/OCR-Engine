
import os
import time
import google.generativeai as genai
from PIL import Image

# --- 設定 (ULTRA-Precision & Fixed Stability) ---
KEY_FILE = "gemini_api_key.txt"
INPUT_DIR = "pages"
OUTPUT_DIR = "intermediate_md_ultra_final"
INTERVAL = 60  # 1ページごとに60秒休む (無料枠の絶対安定速度)
MAX_WORKERS = 1  # 1本に絞って確実に進める

# 【究極・正確性特化型プロンプト】
ULTRA_PRECISION_PROMPT = """
あなたは歴史的統計資料のデジタル化専門プログラムです。
画像内の情報を、以下の『絶対規則』に従って100%正確に書き起こしてください。

[絶対規則]
1. 思考・解説・挨拶は一切不要。出力はMarkdown形式の書き起こしのみとせよ。
2. 統計表は行列を1マスもズラさずMarkdownテーブルで完璧に再現せよ。
3. 漢字はすべて原典のまま（旧字体・異体字を維持。例：港灣、價額、數量、噸、圓、國）。
4. 数値、コンマ（,）、単位（石、斤、噸、圓等）を1文字も漏らさず正確に記載せよ。
5. 縦書きの文章は日本語の正しい順序で、助詞（ニ、ヲ、ハ）も正確に再現せよ。
6. 不鮮明な箇所は文脈から判断し、確定した文字を出力せよ。

[品質目標]
これはデジタルアーカイブのマスターデータとなる。歴史的価値を損なわないよう、一字一句を正確に複製せよ。
"""

def load_key():
    with open(KEY_FILE, "r") as f:
        return f.read().strip()

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    api_key = load_key()
    genai.configure(api_key=api_key)
    # 視覚能力が最も安定している最新世代を使用
    model = genai.GenerativeModel('gemini-2.0-flash')

    # 1. 1ページから151ページまでの全リストを作成 (抜け漏れチェック用)
    all_target_pages = [f"page_{i:03}.png" for i in range(1, 152)]
    
    print(f"--- [ULTRA-PRECISION MODE] Starting Page-by-Page Completion ---")
    print(f"Target: {len(all_target_pages)} pages (Checking for gaps...)")
    
    overall_start = time.time()
    
    for filename in all_target_pages:
        img_path = os.path.join(INPUT_DIR, filename)
        if not os.path.exists(img_path):
            print(f"[Warning] Source image not found: {filename}")
            continue
            
        md_filename = filename.replace(".png", ".md")
        out_path = os.path.join(OUTPUT_DIR, md_filename)
        
        # 既に存在し、かつ十分なサイズがある場合はスキップ (100バイト以下は失敗とみなす)
        if os.path.exists(out_path) and os.path.getsize(out_path) > 100:
            continue
            
        # 未処理または失敗ページを処理
        page_num = filename.replace("page_", "").replace(".png", "")
        print(f"[{time.strftime('%H:%M:%S')}] Processing Gap: Page {page_num}...")
        
        success = False
        retry_delay = 120 # 429時は2分休む
        
        while not success:
            try:
                img = Image.open(img_path)
                # 最大解像度で視認性を確保
                if img.width > 3072 or img.height > 3072:
                    img.thumbnail((3072, 3072))
                
                response = model.generate_content([ULTRA_PRECISION_PROMPT, img])
                
                if response.text and len(response.text) > 10:
                    with open(out_path, "w", encoding="utf-8") as f:
                        f.write(response.text)
                    print(f"   -> Success: Page {page_num} stored.")
                    success = True
                    # 成功した場合はご指示通り60秒のクールダウン
                    print(f"   Waiting {INTERVAL}s for next step...")
                    time.sleep(INTERVAL)
                else:
                    print(f"   -> Error: Response empty for Page {page_num}. Retrying...")
                    time.sleep(10)
                    
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "402" in err_str:
                    print(f"   [Limit] Quota reached. Cooling down {retry_delay}s...")
                    time.sleep(retry_delay)
                else:
                    print(f"   [Error] Unexpected: {err_str[:100]}. Waiting 30s...")
                    time.sleep(30)
                    # 重大なエラーでも一応ループ継続（レジューム性確保）

    print(f"\n--- [COMPLETED] Final output generated in {OUTPUT_DIR} ---")
    print(f"Total time elapsed: {(time.time() - overall_start)/60:.1f} minutes.")

if __name__ == "__main__":
    main()
