"""
build_coco.py — 从 img/ 目录下所有 PNG 生成 OK 框架可用的 COCO JSON 特征文件。

用法: python src/features/build_coco.py
输出: src/features/assets/coco_annotations.json + 压缩后的模板图片
"""

import json
import os
import shutil
import cv2
import numpy as np

# ---- 配置 ----
REF_WIDTH = 1920
REF_HEIGHT = 1080
GRID_CELL_W = 200
GRID_CELL_H = 200
GRID_COLS = REF_WIDTH // GRID_CELL_W  # 9 列
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
BUILD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".build")
IMG_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "img"))
# 把项目根目录加到 sys.path，确保能 import ok
import sys
_proj_root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _proj_root not in sys.path:
    sys.path.insert(0, _proj_root)

# 排除文件
EXCLUDE = {"_current_screen.png", "_after_sortie.png", "_after_claim.png", "_current.png"}


def collect_pngs(root: str) -> dict:
    """递归收集所有 PNG 文件，返回 {category_name: file_path}。"""
    result = {}
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if fn.endswith(".png") and fn not in EXCLUDE and not fn.startswith("_"):
                category = os.path.splitext(fn)[0]
                subdir = os.path.basename(os.path.relpath(dirpath, root))
                if subdir != ".":
                    category = f"{subdir}/{category}"
                result[category] = os.path.join(dirpath, fn)
    return result


def build_coco(pngs: dict) -> str:
    """生成 COCO JSON 和 canvas 图片，返回中间 JSON 路径。"""
    os.makedirs(BUILD_DIR, exist_ok=True)
    images_dir = os.path.join(BUILD_DIR, "images")
    os.makedirs(images_dir, exist_ok=True)

    # 将所有 PNG 放在一张大 canvas 上
    canvas = np.full((REF_HEIGHT, REF_WIDTH, 3), 255, dtype=np.uint8)

    images = []
    annotations = []
    categories = []
    cat_id = 0
    ann_id = 0
    image_id = 1  # 所有特征共享一张 canvas

    canvas_name = "canvas.png"
    canvas_path = os.path.join(images_dir, canvas_name)

    for category_name, png_path in sorted(pngs.items()):
        tpl = cv2.imdecode(np.fromfile(png_path, dtype=np.uint8), cv2.IMREAD_COLOR)
        if tpl is None:
            print(f"  [SKIP] 无法读取: {png_path}")
            continue

        th, tw = tpl.shape[:2]
        if th > REF_HEIGHT or tw > REF_WIDTH:
            print(f"  [SKIP] 尺寸过大: {category_name} ({tw}x{th})")
            continue

        # 计算网格位置
        row = cat_id // GRID_COLS
        col = cat_id % GRID_COLS
        x = col * GRID_CELL_W
        y = row * GRID_CELL_H

        # 确保不超出 canvas
        if y + th > REF_HEIGHT or x + tw > REF_WIDTH:
            print(f"  [SKIP] 超出 canvas: {category_name}")
            continue

        # 粘贴到 canvas
        canvas[y:y+th, x:x+tw] = tpl

        cat_id += 1
        ann_id += 1

        images.append({
            "id": image_id,
            "file_name": f"images/{canvas_name}",
            "width": REF_WIDTH,
            "height": REF_HEIGHT,
        })

        annotations.append({
            "id": ann_id,
            "image_id": image_id,
            "category_id": cat_id,
            "bbox": [x, y, tw, th],
            "area": tw * th,
            "iscrowd": 0,
        })

        categories.append({
            "id": cat_id,
            "name": category_name,
            "supercategory": "",
        })

        print(f"  {category_name}: ({x},{y}) {tw}x{th}")

    # 保存 canvas
    cv2.imwrite(canvas_path, canvas)
    print(f"\nCanvas: {canvas_path} ({REF_WIDTH}x{REF_HEIGHT})")

    # 去重 images
    unique_images = []
    seen_ids = set()
    for img in images:
        if img["id"] not in seen_ids:
            unique_images.append(img)
            seen_ids.add(img["id"])

    coco = {
        "images": unique_images,
        "annotations": annotations,
        "categories": categories,
    }

    json_path = os.path.join(BUILD_DIR, "coco_intermediate.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(coco, f, ensure_ascii=False, indent=2)

    print(f"JSON: {json_path}")
    print(f"  {len(categories)} 个类别, {len(annotations)} 个标注")
    return json_path


def compress(json_path: str):
    """调用 OK 框架的 compress_copy_coco 压缩特征。"""
    from ok.feature.FeatureSet import compress_copy_coco

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"\n压缩中 → {OUTPUT_DIR} ...")
    compress_copy_coco(
        coco_json=json_path,
        target_folder=OUTPUT_DIR,
    )
    print(f"完成: {os.path.join(OUTPUT_DIR, 'coco_annotations.json')}")


def main():
    print("收集 PNG 模板...")
    pngs = collect_pngs(IMG_ROOT)
    print(f"  找到 {len(pngs)} 个 PNG\n")

    json_path = build_coco(pngs)
    compress(json_path)

    # 清理临时文件
    if os.path.exists(BUILD_DIR):
        shutil.rmtree(BUILD_DIR)
        print("临时文件已清理")


if __name__ == "__main__":
    main()
