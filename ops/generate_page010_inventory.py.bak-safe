import csv
from pathlib import Path

root = Path(__file__).parent
pattern = "page_010"
files = sorted([p for p in root.iterdir() if p.name.startswith(pattern)])

csv_path = root / "page_010_inventory.csv"
report_path = root / "page_010_cleanup_report.txt"

rows = []
anomalies = []


def try_read_text_preview(p, length=200):
    try:
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            text = f.read(length)
            return text.replace("\n", "\\n")
    except Exception:
        return ""


for p in files:
    stat = p.stat()
    size = stat.st_size
    is_image = p.suffix.lower() in [".png", ".jpg", ".jpeg", ".tif", ".tiff"]
    width = height = ""
    preview = ""
    if is_image:
        try:
            from PIL import Image

            with Image.open(p) as im:
                width, height = im.size
        except Exception as e:
            anomalies.append(f"IMAGE_ERROR: {p.name}: {e}")
    else:
        preview = try_read_text_preview(p)
    rows.append(
        {
            "filename": p.name,
            "path": str(p),
            "size_bytes": size,
            "is_image": is_image,
            "width": width,
            "height": height,
            "text_preview": preview,
        }
    )
    if size == 0:
        anomalies.append(f"ZERO_BYTE: {p.name}")
    if is_image and size > 50_000_000:
        anomalies.append(f"LARGE_IMAGE: {p.name} size={size} bytes")

# detect duplicates by basename without suffix like .resized or .orig
base_map = {}
for r in rows:
    name = r["filename"]
    # normalize by removing known modifiers
    base = (
        name.replace(".resized", "")
        .replace(".orig", "")
        .replace(".rot90", "")
        .replace(".rot270", "")
    )
    base = base.replace(".tess", "").replace(".tiled", "")
    base = base.split(".tess.tile")[0]
    base_map.setdefault(base, []).append(r["filename"])

for base, lst in base_map.items():
    if len(lst) > 1:
        anomalies.append(f"DUPLICATE_BASE: {base} -> {len(lst)} files")

with open(csv_path, "w", newline="", encoding="utf-8") as csvf:
    writer = csv.DictWriter(
        csvf,
        fieldnames=[
            "filename",
            "path",
            "size_bytes",
            "is_image",
            "width",
            "height",
            "text_preview",
        ],
    )
    writer.writeheader()
    for r in rows:
        writer.writerow(r)

with open(report_path, "w", encoding="utf-8") as rf:
    rf.write("Page 010 Inventory Report\n")
    rf.write("=" * 40 + "\n")
    rf.write(f"Total files: {len(rows)}\n")
    rf.write("\nAnomalies:\n")
    if anomalies:
        for a in anomalies:
            rf.write("- " + a + "\n")
    else:
        rf.write("None\n")
    rf.write("\nKept suggestions:\n")
    # suggest keeping cleaned/ensemble/ollama.suggested and sample.resized
    keep = [
        r["filename"]
        for r in rows
        if (
            "normalized" in r["filename"]
            or "ensemble" in r["filename"]
            or "clean.txt" in r["filename"]
            or "ollama.suggested" in r["filename"]
            or "sample" in r["filename"]
        )
    ]
    for k in keep:
        rf.write("- " + k + "\n")

print("Wrote", csv_path, "and", report_path)
