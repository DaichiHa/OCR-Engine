import glob
import os

manual_path = (
    r"c:\Users\User\Downloads\日本帝國港灣統計_0001\日本帝國港灣統計_OCR.md"
)
output_path = r"c:\Users\User\Downloads\日本帝國港灣統計_0001\日本帝國港灣統計_Ultra_Gemini.md"

dirs = [
    r"c:\Users\User\Downloads\日本帝國港灣統計_0001\intermediate_md_gemini",
    r"c:\Users\User\Downloads\日本帝國港灣統計_0001\intermediate_md_hq",
]

with open(manual_path, "r", encoding="utf-8") as f:
    final_content = f.read()

final_content += "\n\n# --- 精密解析結果 (Gemini/HQ) ---\n\n"
added_pages = set()

for d in dirs:
    print(f"Checking {d}...")
    files = sorted(glob.glob(os.path.join(d, "page_*.md")))
    for f in files:
        p_name = os.path.basename(f)
        if p_name not in added_pages:
            with open(f, "r", encoding="utf-8") as content_f:
                text = content_f.read()
                if "Error" not in text and len(text) > 50:
                    final_content += text + "\n\n---\n\n"
                    added_pages.add(p_name)
                    print(f"Added {p_name}")

with open(output_path, "w", encoding="utf-8") as out:
    out.write(final_content)

print(f"Merge Finished: {output_path}")
