import argparse
import json
import os

from PIL import Image, ImageDraw


def run(page, outdir, langs, gpu):
    import easyocr

    reader = easyocr.Reader(langs.split(","), gpu=(gpu.lower() == "true"))
    os.makedirs(outdir, exist_ok=True)

    full = reader.readtext(page)
    # make JSON-serializable
    serial_full = []
    for bbox, text, prob in full:
        bbox2 = [[int(float(x)), int(float(y))] for x, y in bbox]
        serial_full.append({"bbox": bbox2, "text": str(text), "prob": float(prob)})
    with open(os.path.join(outdir, "full_easyocr.json"), "w", encoding="utf-8") as f:
        json.dump(serial_full, f, ensure_ascii=False, indent=2)

    im = Image.open(page).convert("RGB")
    d = ImageDraw.Draw(im)
    for bbox, text, prob in full:
        d.polygon([tuple(b) for b in bbox], outline="red")
    im.save(os.path.join(outdir, "easyocr_boxes.png"))

    W, H = im.size
    cw, ch = int(W * 0.18), int(H * 0.12)
    box = (W - cw, H - ch, W, H)
    crop = im.crop(box)
    crop_path = os.path.join(outdir, "br_crop.png")
    crop.save(crop_path)

    crop_res = reader.readtext(crop_path)
    serial_crop = []
    for bbox, text, prob in crop_res:
        bbox2 = [[int(float(x)), int(float(y))] for x, y in bbox]
        serial_crop.append({"bbox": bbox2, "text": str(text), "prob": float(prob)})
    with open(os.path.join(outdir, "crop_easyocr.json"), "w", encoding="utf-8") as f:
        json.dump(serial_crop, f, ensure_ascii=False, indent=2)

    summary_path = os.path.join(outdir, "easyocr_summary.txt")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("FULL PAGE DETECTIONS:\n")
        for item in serial_full:
            f.write(f"{item['prob']:.3f}\t{item['text']}\n")
        f.write("\nCROP DETECTIONS:\n")
        for item in serial_crop:
            f.write(f"{item['prob']:.3f}\t{item['text']}\n")

    print("WROTE", outdir)
    print("full_count=", len(full), "crop_count=", len(crop_res))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--page", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--langs", default="ja,en")
    p.add_argument("--gpu", default="false")
    args = p.parse_args()
    run(args.page, args.out, args.langs, args.gpu)


if __name__ == "__main__":
    main()
