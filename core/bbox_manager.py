import json


class BBox:
    def __init__(self, x, y, w, h, label="", result="", expand_meta=None):
        self.x = int(x)
        self.y = int(y)
        self.w = int(w)
        self.h = int(h)
        self.label = label
        self.result = result
        self.expand_meta = expand_meta or {}

    def to_dict(self):
        return {
            "x": self.x,
            "y": self.y,
            "w": self.w,
            "h": self.h,
            "label": self.label,
            "result": self.result,
            "expand_meta": self.expand_meta,
        }

    @classmethod
    def from_dict(cls, d):
        return cls(
            d["x"], d["y"], d["w"], d["h"],
            d.get("label", ""),
            d.get("result", ""),
            d.get("expand_meta", {})
        )

    def copy(self):
        return BBox(self.x, self.y, self.w, self.h, self.label, self.result, self.expand_meta.copy())

    @property
    def center(self):
        return self.x + self.w // 2, self.y + self.h // 2

    @property
    def right(self):
        return self.x + self.w

    @property
    def bottom(self):
        return self.y + self.h

    def expanded_coords(self, img_w, img_h, center=False, top=1.0, bottom=1.0, left=1.0, right=1.0):
        """根据扩展倍数计算新坐标，确保在图像范围内。"""
        cx, cy = self.center
        if center:
            new_w = int(self.w * center) if center > 0 else self.w
            new_h = int(self.h * center) if center > 0 else self.h
            x1 = cx - new_w // 2
            y1 = cy - new_h // 2
            x2 = x1 + new_w
            y2 = y1 + new_h
        else:
            x1, y1, x2, y2 = self.x, self.y, self.right, self.bottom

        if top and top != 1.0 and top > 0:
            dh = int(self.h * (top - 1.0))
            y1 -= dh
        if bottom and bottom != 1.0 and bottom > 0:
            dh = int(self.h * (bottom - 1.0))
            y2 += dh
        if left and left != 1.0 and left > 0:
            dw = int(self.w * (left - 1.0))
            x1 -= dw
        if right and right != 1.0 and right > 0:
            dw = int(self.w * (right - 1.0))
            x2 += dw

        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(img_w, x2)
        y2 = min(img_h, y2)

        if x2 <= x1:
            x2 = x1 + 1
        if y2 <= y1:
            y2 = y1 + 1

        return x1, y1, x2 - x1, y2 - y1


class BBoxManager:
    def __init__(self):
        self.bboxes = []
        self.selected_idx = -1

    def add(self, bbox):
        self.bboxes.append(bbox)
        self.selected_idx = len(self.bboxes) - 1
        return self.selected_idx

    def remove(self, idx):
        if 0 <= idx < len(self.bboxes):
            del self.bboxes[idx]
            if self.selected_idx >= len(self.bboxes):
                self.selected_idx = len(self.bboxes) - 1

    def get(self, idx):
        if 0 <= idx < len(self.bboxes):
            return self.bboxes[idx]
        return None

    def update(self, idx, bbox):
        if 0 <= idx < len(self.bboxes):
            self.bboxes[idx] = bbox

    def select(self, idx):
        self.selected_idx = idx

    def clear(self):
        self.bboxes.clear()
        self.selected_idx = -1

    def to_list(self):
        return [b.to_dict() for b in self.bboxes]

    def from_list(self, data):
        self.bboxes = [BBox.from_dict(d) for d in data]
        self.selected_idx = -1
