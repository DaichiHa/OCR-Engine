import csv
import os


def extract_tables_to_csv(md_file, output_dir):
    with open(md_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    table_buffer = []
    page_num = "Unknown"
    table_count = 0

    for line in lines:
        # Detect page header
        if line.startswith("## Page"):
            page_num = line.strip().replace("## ", "").replace(" ", "_")
            table_count = 0

        # Detect table row
        if "|" in line:
            # Clean up row
            row = [cell.strip() for cell in line.split("|")]
            # Remove empty first/last artifacts from split
            if row and row[0] == "":
                row.pop(0)
            if row and row[-1] == "":
                row.pop()

            # Skip separator lines |---|---|
            if set("".join(row)) <= set("-: "):
                continue

            table_buffer.append(row)
        else:
            # End of table
            if table_buffer:
                table_count += 1
                csv_filename = f"{page_num}_table_{table_count}.csv"
                csv_path = os.path.join(output_dir, csv_filename)

                with open(csv_path, "w", encoding="utf-8", newline="") as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerows(table_buffer)

                print(f"Saved {csv_path}")
                table_buffer = []

    # Flush last buffer
    if table_buffer:
        table_count += 1
        csv_filename = f"{page_num}_table_{table_count}.csv"
        csv_path = os.path.join(output_dir, csv_filename)
        with open(csv_path, "w", encoding="utf-8", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerows(table_buffer)
        print(f"Saved {csv_path}")


if __name__ == "__main__":
    md_path = r"C:\Users\User\Documents\Obsidian Vault\my-db\日本帝國港灣統計.md"
    out_dir = r"C:\Users\User\Documents\Obsidian Vault\my-db\csv_data"

    if os.path.exists(md_path):
        extract_tables_to_csv(md_path, out_dir)
    else:
        print("MD file not found.")
