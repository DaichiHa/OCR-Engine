"""
Markdown Cleaner for "日本帝國港灣統計"
Cleans up the raw OCR Markdown output.
"""

import re
import os

def clean_markdown_table(md_content):
    lines = md_content.split('\n')
    cleaned_lines = []
    
    # Simple heuristic to identify table header
    # and remove empty columns
    
    for line in lines:
        if not line.strip().startswith('|'):
            cleaned_lines.append(line)
            continue
            
        # It's a table row
        # Remove whitespace inside cells? No, might be text.
        # Remove '| ? |' garbage?
        
        # 1. Remove empty cells at start/end if they are just pipe artifacts?
        # No, markdown tables need consistent cols.
        
        # 2. Fix numeric columns with spaces (e.g. "1 000")
        # Regex to look for digits separated by space
        # Careful with dates or text. 
        # But this stats table is mostly numbers.
        
        # Replace "12 345" inside a cell with "12345" if it looks like a number
        # Pattern: [|] \s* \d+ \s+ \d+ \s* [|]
        
        cells = line.split('|')
        new_cells = []
        for cell in cells:
            clean_cell = cell.strip()
            # If cell contains only digits and spaces, compact it
            if re.match(r'^[\d\s,\.]+$', clean_cell):
                # Remove spaces, but keep commas/dots?
                # Actually historical Japanese stats often use spaces for grouping.
                compacted = clean_cell.replace(' ', '')
                new_cells.append(' ' + compacted + ' ')
            else:
                new_cells.append(' ' + clean_cell + ' ')
        
        new_line = '|'.join(new_cells)
        cleaned_lines.append(new_line)

    return '\n'.join(cleaned_lines)

if __name__ == "__main__":
    # Test on page_008.md
    input_path = r"c:\Users\User\Downloads\日本帝國港灣統計_0001\intermediate_md\page_008.md"
    output_path = r"c:\Users\User\Downloads\日本帝國港灣統計_0001\intermediate_md\page_008_cleaned.md"
    
    if os.path.exists(input_path):
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        cleaned = clean_markdown_table(content)
        
        print("Original partial:")
        print(content[:500])
        print("\nCleaned partial:")
        print(cleaned[:500])
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(cleaned)
