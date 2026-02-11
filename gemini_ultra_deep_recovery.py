
import os
import time
import google.generativeai as genai
from PIL import Image

# --- 配置 (ULTRA-Precision & Deep Recovery Mode) ---
KEY_FILE = "gemini_api_key.txt"
INPUT_DIR = "pages"
OUTPUT_DIR = "intermediate_md_ultra_final"

# 成功時は少し速めに、失敗時は深く休む
SUCCESS_INTERVAL = 45 
QUOTA_WAIT = 600  # 429時は10分(600秒)休んでAPIを完全にリセットする

# 確実に存在し、安定しているモデルを指定
MODEL_NAME = 'gemini-2.5-flash'

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
    
    # 1ページから151ページまでの全リストを作成
    all_target_pages = [f"page_{i:03}.png" for i in range(1, 152)]
    
    print(f"--- [ULTRA-PRECISION DEEP RECOVERY] ---")
    print(f"Model: {MODEL_NAME} | Quota Wait: {QUOTA_WAIT}s")
    
    # モデルの機嫌を伺うため、最初は少し長めに待機してからスタート
    print("Initial 10s breathing...")
    time.sleep(10)

    for filename in all_target_pages:
        img_path = os.path.join(INPUT_DIR, filename)
        if not os.path.exists(img_path):
            continue
            
        md_filename = filename.replace(".png", ".md")
        out_path = os.path.join(OUTPUT_DIR, md_filename)
        
        # スキップ
        if os.path.exists(out_path) and os.path.getsize(out_path) > 100:
            continue
            
        page_num = filename.replace("page_", "").replace(".png", "")
        
        success = False
        while not success:
            print(f"[{time.strftime('%H:%M:%S')}] Processing Gap: Page {page_num}...")
            try:
                model = genai.GenerativeModel(MODEL_NAME)
                img = Image.open(img_path)
                img.thumbnail((3072, 3072))
                
                response = model.generate_content([ULTRA_PRECISION_PROMPT, img])
                
                if response.text and len(response.text) > 10:
                    with open(out_path, "w", encoding="utf-8") as f:
                        f.write(response.text)
                    print(f"   -> Success: Page {page_num}")
                    success = True
                    time.sleep(SUCCESS_INTERVAL)
                else:
                    print(f"   -> Empty response. Waiting 30s...")
                    time.sleep(30)
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "402" in err_str:
                    print(f"   [Limit] Deep Rest Required. Waiting {QUOTA_WAIT}s...")
                    time.sleep(QUOTA_WAIT)
                    # 5分待ってもダメな場合はモデルをスイッチする予備ロジック
                else:
                    print(f"   [Error] {err_str[:150]}. Waiting 60s...")
                    time.sleep(60)

    print(f"--- [COMPLETED] ---")

if __name__ == "__main__":
    main()
