"""
Main Batch Processor for "日本帝國港灣統計"
Iterates through all 151 pages and applies appropriate OCR strategy.
"""

import os
import hybrid_extractor
import concurrent.futures
import time
import json

FAIL_MEAN_CONF = 70
FAIL_LOW_RATIO = 0.30

def append_queue(queue_path, item):
    with open(queue_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")

def aggregate_metrics(metrics_list):
    if not metrics_list:
        return {'mean_conf': 0.0, 'low_ratio': 1.0, 'count': 0}
    total_count = sum(m.get('count', 0) for m in metrics_list)
    if total_count == 0:
        return {'mean_conf': 0.0, 'low_ratio': 1.0, 'count': 0}
    mean_conf = sum(m.get('mean_conf', 0.0) * m.get('count', 0) for m in metrics_list) / total_count
    low_ratio = sum(m.get('low_ratio', 0.0) * m.get('count', 0) for m in metrics_list) / total_count
    return {'mean_conf': mean_conf, 'low_ratio': low_ratio, 'count': total_count}

def process_single_page_task(page_info, user_words_path=None, user_patterns_path=None, queue_path=None):
    """
    Process one page based on its number
    """
    page_num, image_path = page_info
    try:
        start_time = time.time()
        
        if 1 <= page_num <= 6:
            # Text Mode
            content, metrics = hybrid_extractor.extract_vertical_text(
                image_path,
                user_words_path=user_words_path,
                user_patterns_path=user_patterns_path,
                return_metrics=True,
            )
            # Wrap in minimal markdown
            result = f"\n\n## Page {page_num}\n\n{content}\n"
            
        else:
            # Table Mode
            full_image = hybrid_extractor.read_image_robust(image_path)
            table_regions = hybrid_extractor.detect_table_regions(full_image)
            if not table_regions:
                table_regions = [None]

            all_rows = []
            metrics_list = []
            for region in table_regions:
                rows, region_metrics = hybrid_extractor.extract_table_content(
                    image_path,
                    table_region=region,
                    user_words_path=user_words_path,
                    user_patterns_path=user_patterns_path,
                    return_metrics=True,
                )
                if rows:
                    all_rows.extend(rows)
                metrics_list.append(region_metrics)
            metrics = aggregate_metrics(metrics_list)

            rows = all_rows
            if not rows:
                result = f"\n\n## Page {page_num}\n\n(No table data detected)\n"
            else:
                lines = []
                lines.append(f"\n\n## Page {page_num}")
                # Construct Markdown Table
                for row_idx, row in enumerate(rows):
                    # Clean up: Replace pipes with generic separator or escape them
                    clean_row = [str(c).replace('|', '') for c in row]
                    lines.append("| " + " | ".join(clean_row) + " |")
                result = "\n".join(lines)
        
        elapsed = time.time() - start_time

        if queue_path:
            if metrics['mean_conf'] < FAIL_MEAN_CONF or metrics['low_ratio'] > FAIL_LOW_RATIO:
                append_queue(queue_path, {
                    'path': image_path,
                    'mode': 'body' if 1 <= page_num <= 6 else 'table',
                    'attempt': 1,
                    'preset': 'baseline',
                })
        return page_num, result, elapsed
        
    except Exception as e:
        return page_num, f"\n## Page {page_num}\nError: {str(e)}\n", 0

if __name__ == "__main__":
    pages_dir = r"c:\Users\User\Downloads\日本帝國港灣統計_0001\pages"
    output_file = r"c:\Users\User\Downloads\日本帝國港灣統計_0001\Full_Output_Draft.md"
    queue_path = os.path.join(os.path.dirname(output_file), "queue.jsonl")

    user_words_path = os.path.join(os.path.dirname(__file__), "user_words.txt")
    user_patterns_path = os.path.join(os.path.dirname(__file__), "user_patterns.txt")
    if not os.path.exists(user_words_path):
        user_words_path = None
    if not os.path.exists(user_patterns_path):
        user_patterns_path = None
    
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
    
    print(f"Starting batch processing for {len(page_list)} pages...")
    
    # Use ProcessPoolExecutor to bypass GIL for heavy OpenCV/Tesseract work
    # But Windows multiprocessing requires careful pickling. 
    # ThreadPoolExecutor is safer if modules are not perfectly picklable.
    # Tesseract releases GIL, so threading is fine.
    
    max_workers = 4
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_page = {
            executor.submit(process_single_page_task, p, user_words_path, user_patterns_path, queue_path): p
            for p in page_list
        }
        
        completed_count = 0
        total_count = len(page_list)
        
        for future in concurrent.futures.as_completed(future_to_page):
            page_info = future_to_page[future]
            try:
                p_num, text, dur = future.result()
                full_results[p_num] = text
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
            
    print(f"Processing complete. Saved to {output_file}")
