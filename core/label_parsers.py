import os
import json
import xml.etree.ElementTree as ET
from xml.dom import minidom
from core.bbox_manager import BBox


def _clamp(v, min_v, max_v):
    return max(min_v, min(v, max_v))


# ==================== VOC ====================
def parse_voc(xml_path, img_w, img_h):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    bboxes = []
    for obj in root.findall("object"):
        name = obj.find("name")
        label = name.text if name is not None else ""
        bndbox = obj.find("bndbox")
        if bndbox is None:
            continue
        xmin = int(float(bndbox.find("xmin").text))
        ymin = int(float(bndbox.find("ymin").text))
        xmax = int(float(bndbox.find("xmax").text))
        ymax = int(float(bndbox.find("ymax").text))
        xmin = _clamp(xmin, 0, img_w - 1)
        ymin = _clamp(ymin, 0, img_h - 1)
        xmax = _clamp(xmax, xmin + 1, img_w)
        ymax = _clamp(ymax, ymin + 1, img_h)
        bboxes.append(BBox(xmin, ymin, xmax - xmin, ymax - ymin, label=label))
    return bboxes


def save_voc(xml_path, img_path, img_w, img_h, bbox_manager):
    root = ET.Element("annotation")
    ET.SubElement(root, "folder").text = os.path.basename(os.path.dirname(img_path))
    ET.SubElement(root, "filename").text = os.path.basename(img_path)
    size = ET.SubElement(root, "size")
    ET.SubElement(size, "width").text = str(img_w)
    ET.SubElement(size, "height").text = str(img_h)
    ET.SubElement(size, "depth").text = "3"
    ET.SubElement(root, "segmented").text = "0"

    for bbox in bbox_manager.bboxes:
        obj = ET.SubElement(root, "object")
        ET.SubElement(obj, "name").text = bbox.label or "unknown"
        ET.SubElement(obj, "pose").text = "Unspecified"
        ET.SubElement(obj, "truncated").text = "0"
        ET.SubElement(obj, "difficult").text = "0"
        bndbox = ET.SubElement(obj, "bndbox")
        ET.SubElement(bndbox, "xmin").text = str(bbox.x)
        ET.SubElement(bndbox, "ymin").text = str(bbox.y)
        ET.SubElement(bndbox, "xmax").text = str(bbox.right)
        ET.SubElement(bndbox, "ymax").text = str(bbox.bottom)

    rough = ET.tostring(root, encoding="unicode")
    reparsed = minidom.parseString(rough)
    pretty = reparsed.toprettyxml(indent="  ")
    # 去掉第一行声明后的空行
    lines = [line for line in pretty.splitlines() if line.strip()]
    with open(xml_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


# ==================== YOLO ====================
def parse_yolo(txt_path, img_w, img_h, class_names=None):
    bboxes = []
    if not os.path.exists(txt_path):
        return bboxes
    with open(txt_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 5:
                continue
            class_id = int(parts[0])
            cx, cy, w, h = map(float, parts[1:5])
            abs_w = w * img_w
            abs_h = h * img_h
            abs_x = cx * img_w - abs_w / 2
            abs_y = cy * img_h - abs_h / 2
            abs_x = _clamp(abs_x, 0, img_w - 1)
            abs_y = _clamp(abs_y, 0, img_h - 1)
            abs_w = _clamp(abs_w, 1, img_w - abs_x)
            abs_h = _clamp(abs_h, 1, img_h - abs_y)
            label = class_names[class_id] if class_names and 0 <= class_id < len(class_names) else str(class_id)
            bboxes.append(BBox(int(abs_x), int(abs_y), int(abs_w), int(abs_h), label=label))
    return bboxes


def save_yolo(txt_path, img_w, img_h, bbox_manager, class_names=None):
    lines = []
    for bbox in bbox_manager.bboxes:
        label = bbox.label or "unknown"
        if class_names and label in class_names:
            class_id = class_names.index(label)
        elif class_names and label.isdigit():
            class_id = int(label)
        else:
            class_id = 0
        cx = (bbox.x + bbox.w / 2) / img_w
        cy = (bbox.y + bbox.h / 2) / img_h
        w = bbox.w / img_w
        h = bbox.h / img_h
        lines.append(f"{class_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


# ==================== COCO ====================
def parse_coco(coco_path, img_path, img_w, img_h):
    bboxes = []
    if not os.path.exists(coco_path):
        return bboxes
    with open(coco_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    images = {img["id"]: img for img in data.get("images", [])}
    img_filename = os.path.basename(img_path)
    target_img_id = None
    for img in images.values():
        if img.get("file_name") == img_filename:
            target_img_id = img["id"]
            break

    if target_img_id is None:
        return bboxes

    categories = {cat["id"]: cat.get("name", str(cat["id"])) for cat in data.get("categories", [])}

    for ann in data.get("annotations", []):
        if ann.get("image_id") != target_img_id:
            continue
        x, y, w, h = ann.get("bbox", [0, 0, 0, 0])
        x = _clamp(int(x), 0, img_w - 1)
        y = _clamp(int(y), 0, img_h - 1)
        w = _clamp(int(w), 1, img_w - x)
        h = _clamp(int(h), 1, img_h - y)
        label = categories.get(ann.get("category_id"), "")
        bboxes.append(BBox(x, y, w, h, label=label))
    return bboxes


def save_coco(coco_path, img_dir, all_image_paths, all_bbox_managers, existing_data=None):
    """将所有图片的标注保存为单个 COCO JSON 文件"""
    if existing_data and os.path.exists(coco_path):
        with open(coco_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {"images": [], "annotations": [], "categories": []}

    # 收集所有 labels
    all_labels = set()
    for bm in all_bbox_managers:
        for b in bm.bboxes:
            if b.label:
                all_labels.add(b.label)
    labels = sorted(all_labels)
    cat_id_map = {name: i for i, name in enumerate(labels)}
    data["categories"] = [{"id": i, "name": name} for i, name in enumerate(labels)]

    # 清理旧的 images/annotations 对应路径
    existing_images = {img["file_name"]: img for img in data.get("images", [])}
    existing_img_ids = {img["id"] for img in data.get("images", [])}
    max_img_id = max(existing_img_ids, default=0)
    max_ann_id = max([ann["id"] for ann in data.get("annotations", [])], default=0)

    new_images = []
    new_annotations = []

    for img_path, bm in zip(all_image_paths, all_bbox_managers):
        filename = os.path.basename(img_path)
        if filename in existing_images:
            img_id = existing_images[filename]["id"]
        else:
            max_img_id += 1
            img_id = max_img_id
            from PIL import Image
            try:
                pil = Image.open(img_path)
                w, h = pil.size
            except Exception:
                w, h = 0, 0
            new_images.append({"id": img_id, "file_name": filename, "width": w, "height": h})

        # 移除该图片旧 annotations（通过重写全部对应项）
        for bbox in bm.bboxes:
            max_ann_id += 1
            ann = {
                "id": max_ann_id,
                "image_id": img_id,
                "category_id": cat_id_map.get(bbox.label, 0),
                "bbox": [bbox.x, bbox.y, bbox.w, bbox.h],
                "area": bbox.w * bbox.h,
                "iscrowd": 0,
            }
            new_annotations.append(ann)

    # 保留未修改的图片记录
    preserved_images = [img for img in data.get("images", []) if img["file_name"] not in {os.path.basename(p) for p in all_image_paths}]
    preserved_annotations = [ann for ann in data.get("annotations", []) if ann["image_id"] not in {img["id"] for img in new_images}]

    data["images"] = preserved_images + new_images
    data["annotations"] = preserved_annotations + new_annotations

    with open(coco_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
