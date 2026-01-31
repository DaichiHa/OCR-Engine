"""
Main Batch Processor for "日本帝國港灣統計"
Iterates through all 151 pages and applies appropriate OCR strategy.
"""

import concurrent.futures
import json
import os
import time

import hybrid_extractor
import layout_detector

def _build_markdown_table(rows):
    if not rows:
        return ["(No table data detected)"]

    lines = []
    for row in rows:
        clean_row = [str(c).replace('|', '') for c in row]
        lines.append("| " + " | ".join(clean_row) + " |")
    return lines


def _crop_region(image, bbox):
    height, width = image.shape[:2]
    x1, y1, x2, y2 = bbox
    x1 = max(0, min(int(x1), width))
    x2 = max(0, min(int(x2), width))
    y1 = max(0, min(int(y1), height))
    y2 = max(0, min(int(y2), height))
    if x2 <= x1 or y2 <= y1:
        return None
    return image[y1:y2, x1:x2]


def process_single_page_task(page_info):
    """
    Process one page based on its number
    """
    page_num, image_path = page_info
    try:
        start_time = time.time()
        
        region_metadata = []
        layout_regions = layout_detector.detect_layout_regions(image_path)
        if layout_regions:
            image = hybrid_extractor.read_image_robust(image_path)
            lines = [f"\n\n## Page {page_num}"]

            for idx, region in enumerate(layout_regions, start=1):
                region_id = f"{page_num}-{idx}"
                region_type = region["type"]
                bbox = region["bbox"]
                region_metadata.append(
                    {
                        "page": page_num,
                        "region_id": region_id,
                        "type": region_type,
                        "bbox": bbox,
                    }
                )

                region_image = _crop_region(image, bbox)
                if region_image is None:
                    lines.append(f"\n\n### Region {region_id} ({region_type})")
                    lines.append("(Skipped: invalid region bounds)")
                    continue

                lines.append(f"\n\n### Region {region_id} ({region_type})")
                if region_type == "table":
                    rows = hybrid_extractor.extract_table_content(region_image)
                    lines.extend(_build_markdown_table(rows))
                else:
                    content = hybrid_extractor.extract_vertical_text(region_image)
                    lines.append(content)

            result = "\n".join(lines)
        elif 1 <= page_num <= 6:
            # Text Mode
            content = hybrid_extractor.extract_vertical_text(image_path)
            result = f"\n\n## Page {page_num}\n\n{content}\n"
        else:
            # Table Mode
            rows = hybrid_extractor.extract_table_content(image_path)
            lines = [f"\n\n## Page {page_num}"]
            lines.extend(_build_markdown_table(rows))
            result = "\n".join(lines)
        
        elapsed = time.time() - start_time
        return page_num, result, elapsed, region_metadata
        
    except Exception as e:
        return page_num, f"\n## Page {page_num}\nError: {str(e)}\n", 0, []

if __name__ == "__main__":
    pages_dir = r"c:\Users\User\Downloads\日本帝國港灣統計_0001\pages"
    output_file = r"c:\Users\User\Downloads\日本帝國港灣統計_0001\Full_Output_Draft.md"
    boxes_file = os.path.join(os.path.dirname(output_file), "boxes.jsonl")
    
    # Get all page files
    files = sorted([f for f in os.listdir(pages_dir) if f.lower().endswith('.png')])
    
    # Map filenames to page numbers (assuming page_XXX.png)
    page_list = []
    for f in files:
        # Filter out debug images
        if f.startswith('debug_') or f.startswith('table_') or 'debug' in f:
            continue
            
        # Extract number from "page_001.png" or "page_1.png"
        try:
            # Split by '_' and take the last part, remove extension
            num_str = f.split('_')[-1].split('.')[0]
            num = int(num_str)
            page_list.append((num, os.path.join(pages_dir, f)))
        except:
            continue
            
    # Sort by page number
    page_list.sort(key=lambda x: x[0])
    
    full_results = {}
    all_region_metadata = []
    
    print(f"Starting batch processing for {len(page_list)} pages...")
    
    # Use ProcessPoolExecutor to bypass GIL for heavy OpenCV/Tesseract work
    # But Windows multiprocessing requires careful pickling. 
    # ThreadPoolExecutor is safer if modules are not perfectly picklable.
    # Tesseract releases GIL, so threading is fine.
    
    max_workers = 4
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_page = {executor.submit(process_single_page_task, p): p for p in page_list}
        
        completed_count = 0
        total_count = len(page_list)
        
        for future in concurrent.futures.as_completed(future_to_page):
            page_info = future_to_page[future]
            try:
                p_num, text, dur, region_metadata = future.result()
                full_results[p_num] = text
                all_region_metadata.extend(region_metadata)
                completed_count += 1
                print(f"[{completed_count}/{total_count}] Page {p_num} processed in {dur:.2f}s")
            except Exception as exc:
                print(f"Page {page_info[0]} generated an exception: {exc}")

    # Write final output sorted
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# 日本帝國港灣統計 OCR Result\n")
        f.write("Generated by Hybrid Structure-Aware OCR\n\n")
        
        keys = sorted(full_results.keys())
        for k in keys:
            f.write(full_results[k])
            f.write("\n\n---\n\n")

    with open(boxes_file, "w", encoding="utf-8") as f:
        for item in all_region_metadata:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            
    print(f"Processing complete. Saved to {output_file}")
    print(f"Region metadata saved to {boxes_file}")
