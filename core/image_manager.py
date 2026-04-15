import io
import base64
from PIL import Image, ImageDraw, ImageFont
import numpy as np


class ImageManager:
    def __init__(self):
        self.original_image = None
        self.display_image = None
        self.file_path = ""

    def load(self, path):
        self.file_path = path
        self.original_image = Image.open(path).convert("RGB")
        self.display_image = self.original_image.copy()
        return self.original_image

    @property
    def size(self):
        if self.original_image:
            return self.original_image.size
        return (0, 0)

    def rotate(self, angle):
        if self.original_image:
            self.original_image = self.original_image.rotate(angle, expand=True)
            self.display_image = self.original_image.copy()

    def resize(self, width, height):
        if self.original_image:
            self.original_image = self.original_image.resize((width, height), Image.LANCZOS)
            self.display_image = self.original_image.copy()

    def reset_display(self):
        if self.original_image:
            self.display_image = self.original_image.copy()

    def crop(self, x, y, w, h):
        if self.original_image:
            return self.original_image.crop((x, y, x + w, y + h))
        return None

    def to_base64(self, pil_image=None, fmt="JPEG"):
        img = pil_image or self.original_image
        if img is None:
            return ""
        buffer = io.BytesIO()
        if fmt.upper() == "PNG":
            img.save(buffer, format="PNG")
            return f"data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode()}"
        else:
            img.save(buffer, format="JPEG")
            return f"data:image/jpeg;base64,{base64.b64encode(buffer.getvalue()).decode()}"

    def draw_bboxes(self, bbox_manager, show_expanded=False, expand_settings=None):
        if self.original_image is None or bbox_manager is None:
            return None
        img = self.original_image.copy()
        draw = ImageDraw.Draw(img)
        w, h = img.size

        def get_font(size=16):
            candidates = [
                "/System/Library/Fonts/PingFang.ttc",
                "/System/Library/Fonts/Hiragino Sans GB.ttc",
                "/System/Library/Fonts/STHeiti Light.ttc",
                "/Library/Fonts/Arial Unicode.ttf",
                "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "C:/Windows/Fonts/msyh.ttc",
                "C:/Windows/Fonts/simsun.ttc",
                "arial.ttf",
            ]
            for path in candidates:
                try:
                    return ImageFont.truetype(path, size)
                except Exception:
                    continue
            return ImageFont.load_default()

        font = get_font(16)
        expand_settings = expand_settings or {}

        for idx, bbox in enumerate(bbox_manager.bboxes):
            color = "red" if idx == bbox_manager.selected_idx else "blue"

            if show_expanded and expand_settings:
                ex, ey, ew, eh = bbox.expanded_coords(
                    w, h,
                    center=expand_settings.get("center", 0),
                    top=expand_settings.get("top", 1.0),
                    bottom=expand_settings.get("bottom", 1.0),
                    left=expand_settings.get("left", 1.0),
                    right=expand_settings.get("right", 1.0),
                )
                draw.rectangle([ex, ey, ex + ew, ey + eh], outline="orange", width=2)

            draw.rectangle([bbox.x, bbox.y, bbox.right, bbox.bottom], outline=color, width=2)

            text = bbox.label or f"#{idx}"
            if bbox.result:
                text += f" | {bbox.result}"
            if hasattr(font, 'getbbox'):
                l, t, r, b = font.getbbox(text)
                tw, th = r - l, b - t
            else:
                tw, th = len(text) * 8, 16
            draw.rectangle([bbox.x, bbox.y - th, bbox.x + tw, bbox.y], fill=color)
            draw.text((bbox.x, bbox.y - th), text, fill="white", font=font)

        return img

    def save(self, path):
        if self.original_image:
            self.original_image.save(path)
