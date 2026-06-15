"""
从原始彩图生成白底模板图。

- 源图目录: assets/screenshots/  （原始彩色截图，开发时在这里标注）
- 输出目录: ok_templates/       （白底模板 + coco_annotations.json，提交到 git）

用法: python scripts/whiteout_templates.py
"""
import json, os, sys
import cv2
import numpy as np

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_DIR = os.path.join(PROJECT_DIR, "assets", "screenshots")      # 原始彩图
TEMPLATE_DIR = os.path.join(PROJECT_DIR, "ok_templates")             # 白底输出
COCO_JSON = os.path.join(TEMPLATE_DIR, "coco_annotations.json")


def main():
    if not os.path.exists(COCO_JSON):
        print(f"[skip] {COCO_JSON} not found")
        return

    os.makedirs(TEMPLATE_DIR, exist_ok=True)

    with open(COCO_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    image_map = {img["id"]: img["file_name"] for img in data["images"]}
    annotations_by_image = {}
    for ann in data["annotations"]:
        annotations_by_image.setdefault(ann["image_id"], []).append(ann)

    for image_id, file_name in image_map.items():
        src_path = os.path.join(SOURCE_DIR, file_name)
        out_path = os.path.join(TEMPLATE_DIR, file_name)

        if not os.path.exists(src_path):
            print(f"[warn] source {src_path} missing, skip")
            continue

        img = cv2.imread(src_path)
        if img is None:
            print(f"[warn] cannot read {src_path}")
            continue

        anns = annotations_by_image.get(image_id, [])
        if not anns:
            cv2.imwrite(out_path, img)
            print(f"[copy] {file_name} (no bbox, copied as-is)")
            continue

        # 全白底图，只保留所有 bbox 内的原图
        white_bg = np.full_like(img, 255)
        for ann in anns:
            x, y, w_box, h_box = ann["bbox"]
            x1, y1 = int(x), int(y)
            x2, y2 = int(x + w_box), int(y + h_box)
            white_bg[y1:y2, x1:x2] = img[y1:y2, x1:x2]

        cv2.imwrite(out_path, white_bg)
        print(f"[done] {file_name} ({len(anns)} features) -> {out_path}")


if __name__ == "__main__":
    main()
