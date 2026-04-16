from PyQt5.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsRectItem, QGraphicsPixmapItem,
    QGraphicsItem, QMenu, QAction, QInputDialog, QMessageBox
)
from PyQt5.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt5.QtGui import QPen, QBrush, QColor, QPixmap, QPainter, QFont, QCursor
from core.bbox_manager import BBox


class BBoxItem(QGraphicsRectItem):
    def __init__(self, bbox, img_w, img_h, expand_settings=None, parent=None):
        super().__init__(parent)
        self.bbox = bbox
        self.img_w = img_w
        self.img_h = img_h
        self.expand_settings = expand_settings or {}
        self._resizing = False
        self._resize_start = None
        self._orig_rect = None
        self.setFlags(
            QGraphicsItem.ItemIsMovable |
            QGraphicsItem.ItemIsSelectable |
            QGraphicsItem.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        self._update_rect()

    def _update_rect(self):
        self.setRect(self.bbox.x, self.bbox.y, self.bbox.w, self.bbox.h)

    def update_from_rect(self):
        r = self.rect()
        self.bbox.x = int(r.x())
        self.bbox.y = int(r.y())
        self.bbox.w = int(r.width())
        self.bbox.h = int(r.height())

    def hoverMoveEvent(self, event):
        handle = self._handle_rect()
        if handle.contains(event.pos()):
            self.setCursor(QCursor(Qt.SizeFDiagCursor))
        else:
            self.setCursor(QCursor(Qt.ArrowCursor))
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            handle = self._handle_rect()
            if handle.contains(event.pos()):
                self._resizing = True
                self._resize_start = event.scenePos()
                self._orig_rect = self.rect()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._resizing:
            delta = event.scenePos() - self._resize_start
            new_rect = QRectF(self._orig_rect)
            new_rect.setWidth(max(10, self._orig_rect.width() + delta.x()))
            new_rect.setHeight(max(10, self._orig_rect.height() + delta.y()))
            self.setRect(new_rect)
            self.update_from_rect()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._resizing:
            self._resizing = False
            self._resize_start = None
            self._orig_rect = None
            self.update_from_rect()
            return
        super().mouseReleaseEvent(event)
        # 拖拽移动后，pos 会改变但 rect 不变，需要同步
        pos = self.pos()
        if pos.x() != 0 or pos.y() != 0:
            r = self.rect()
            self.setRect(r.x() + pos.x(), r.y() + pos.y(), r.width(), r.height())
            self.setPos(0, 0)
        self.update_from_rect()

    def _handle_rect(self):
        r = self.rect()
        size = 8
        return QRectF(r.right() - size, r.bottom() - size, size, size)

    def boundingRect(self):
        r = self.rect()
        # 基础矩形
        br = QRectF(r)
        # 扩展虚线框
        if self.expand_settings:
            ex, ey, ew, eh = self.bbox.expanded_coords(
                self.img_w, self.img_h,
                center=self.expand_settings.get("center", 0),
                top=self.expand_settings.get("top", 1.0),
                bottom=self.expand_settings.get("bottom", 1.0),
                left=self.expand_settings.get("left", 1.0),
                right=self.expand_settings.get("right", 1.0),
            )
            br = br.united(QRectF(ex, ey, ew, eh))
        # 标签区域（上方最多 100 宽 20 高）
        br = br.united(QRectF(r.x(), r.y() - 20, max(r.width(), 100), 20))
        # resize handle
        br = br.united(self._handle_rect())
        return br

    def paint(self, painter, option, widget=None):
        # 扩展虚线框
        if self.expand_settings:
            ex, ey, ew, eh = self.bbox.expanded_coords(
                self.img_w, self.img_h,
                center=self.expand_settings.get("center", 0),
                top=self.expand_settings.get("top", 1.0),
                bottom=self.expand_settings.get("bottom", 1.0),
                left=self.expand_settings.get("left", 1.0),
                right=self.expand_settings.get("right", 1.0),
            )
            pen = QPen(QColor("orange"))
            pen.setStyle(Qt.DashLine)
            pen.setWidth(2)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(ex, ey, ew, eh)

        # 主体框
        is_selected = self.isSelected()
        color = QColor("red") if is_selected else QColor("blue")
        pen = QPen(color)
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(self.rect())

        # 标签文字
        text = self.bbox.label or ""
        if self.bbox.result:
            text += f" | {self.bbox.result}"
        if text:
            painter.setPen(QColor("white"))
            painter.setBrush(QBrush(color))
            font = QFont("Arial", 10)
            painter.setFont(font)
            fm = painter.fontMetrics()
            tw = fm.horizontalAdvance(text) + 4
            th = fm.height()
            r = self.rect()
            painter.drawRect(int(r.x()), int(r.y()) - th, tw, th)
            painter.drawText(int(r.x()) + 2, int(r.y()) - 2, text)

        # resize handle
        if is_selected:
            painter.setPen(QPen(QColor("white")))
            painter.setBrush(QBrush(QColor("red")))
            painter.drawRect(self._handle_rect())


class ImageCanvas(QGraphicsView):
    bbox_selected = pyqtSignal(int)
    bbox_added = pyqtSignal(int)
    bbox_changed = pyqtSignal()
    request_label_input = pyqtSignal(int)
    mode_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHints(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self._pixmap_item = None
        self._img_manager = None
        self._bbox_manager = None
        self._expand_settings = {}
        self._drawing = False
        self._draw_start = None
        self._draw_rect_item = None
        self._mode = "browse"   # browse | draw
        self._panning = False
        self._pan_start = None
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_context_menu)

    def set_image_manager(self, img_manager):
        self._img_manager = img_manager
        self._load_pixmap()

    def set_bbox_manager(self, bbox_manager):
        self._bbox_manager = bbox_manager
        self._sync_items()

    def set_expand_settings(self, settings):
        self._expand_settings = settings
        self._sync_items()
        self.viewport().update()

    def _load_pixmap(self):
        self.scene.clear()
        self._pixmap_item = None
        if self._img_manager and self._img_manager.original_image:
            pil_img = self._img_manager.original_image.convert("RGBA")
            data = pil_img.tobytes("raw", "RGBA")
            from PyQt5.QtGui import QImage
            qimg = QImage(data, pil_img.width, pil_img.height, QImage.Format_RGBA8888)
            pixmap = QPixmap.fromImage(qimg)
            self._pixmap_item = QGraphicsPixmapItem(pixmap)
            self._pixmap_item.setZValue(-1)
            self.scene.addItem(self._pixmap_item)
            # 场景区域留出边距，使缩小后也能平移
            margin = max(pixmap.width(), pixmap.height()) * 0.5
            self.scene.setSceneRect(
                -margin, -margin,
                pixmap.width() + margin * 2, pixmap.height() + margin * 2
            )
            self.fitInView(self._pixmap_item.boundingRect(), Qt.KeepAspectRatio)
            self._sync_items()

    def _sync_items(self):
        # 移除旧的 BBoxItem，并强制重绘整个场景，防止虚线框残影
        for item in self.scene.items():
            if isinstance(item, BBoxItem):
                self.scene.removeItem(item)
        self.scene.invalidate(self.scene.sceneRect())
        if not self._bbox_manager or not self._img_manager:
            self.viewport().update()
            return
        img_w, img_h = self._img_manager.size
        for idx, bbox in enumerate(self._bbox_manager.bboxes):
            item = BBoxItem(bbox, img_w, img_h, self._expand_settings)
            item.setZValue(1)
            self.scene.addItem(item)
            if idx == self._bbox_manager.selected_idx:
                item.setSelected(True)
        self.viewport().update()

    def wheelEvent(self, event):
        factor = 1.15
        if event.angleDelta().y() < 0:
            factor = 1.0 / factor
        self.scale(factor, factor)

    def set_mode(self, mode):
        self._mode = mode
        if mode == "draw":
            self.setDragMode(QGraphicsView.NoDrag)
            self.setCursor(QCursor(Qt.CrossCursor))
        else:
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            self.setCursor(QCursor(Qt.ArrowCursor))
        self.mode_changed.emit(mode)

    def mousePressEvent(self, event):
        # 中键拖拽平移（任何模式、任何缩放级别）
        if event.button() == Qt.MiddleButton:
            self._panning = True
            self._pan_start = event.pos()
            self.setCursor(QCursor(Qt.ClosedHandCursor))
            event.accept()
            return
        if event.button() == Qt.LeftButton and self._img_manager and self._mode == "draw":
            item = self.itemAt(event.pos())
            if item is None or item == self._pixmap_item:
                self._drawing = True
                self._draw_start = self.mapToScene(event.pos())
                self._draw_rect_item = QGraphicsRectItem()
                pen = QPen(QColor("green"))
                pen.setWidth(2)
                self._draw_rect_item.setPen(pen)
                self._draw_rect_item.setZValue(2)
                self.scene.addItem(self._draw_rect_item)
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._panning and self._pan_start is not None:
            delta = event.pos() - self._pan_start
            self._pan_start = event.pos()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x()
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y()
            )
            event.accept()
            return
        if self._drawing and self._draw_rect_item:
            pos = self.mapToScene(event.pos())
            x = min(self._draw_start.x(), pos.x())
            y = min(self._draw_start.y(), pos.y())
            w = abs(pos.x() - self._draw_start.x())
            h = abs(pos.y() - self._draw_start.y())
            self._draw_rect_item.setRect(x, y, w, h)
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton and self._panning:
            self._panning = False
            self._pan_start = None
            # 恢复当前模式对应的光标
            if self._mode == "draw":
                self.setCursor(QCursor(Qt.CrossCursor))
            else:
                self.setCursor(QCursor(Qt.ArrowCursor))
            event.accept()
            return
        if self._drawing and self._draw_rect_item:
            r = self._draw_rect_item.rect()
            self.scene.removeItem(self._draw_rect_item)
            self._draw_rect_item = None
            self._drawing = False
            if r.width() > 5 and r.height() > 5:
                x, y, w, h = int(r.x()), int(r.y()), int(r.width()), int(r.height())
                # 限制在图像内
                if self._img_manager:
                    iw, ih = self._img_manager.size
                    x = max(0, min(x, iw - 1))
                    y = max(0, min(y, ih - 1))
                    w = min(w, iw - x)
                    h = min(h, ih - y)
                bbox = BBox(x, y, w, h)
                idx = self._bbox_manager.add(bbox)
                self._sync_items()
                self.bbox_added.emit(idx)
                self.request_label_input.emit(idx)
                # LabelImg 风格：画完一个框自动退出绘制模式
                self.set_mode("browse")
            return

        # 处理选中变化
        super().mouseReleaseEvent(event)
        self._update_selection()

    def _update_selection(self):
        selected_idx = -1
        for item in self.scene.selectedItems():
            if isinstance(item, BBoxItem):
                try:
                    selected_idx = self._bbox_manager.bboxes.index(item.bbox)
                    break
                except ValueError:
                    pass
        if selected_idx != self._bbox_manager.selected_idx:
            self._bbox_manager.select(selected_idx)
            self._sync_items()
            self.bbox_selected.emit(selected_idx)
        self.bbox_changed.emit()

    def _on_context_menu(self, pos):
        scene_pos = self.mapToScene(pos)
        item = self.scene.itemAt(scene_pos, self.viewportTransform())
        if isinstance(item, BBoxItem):
            menu = QMenu(self)
            act_edit = QAction("编辑标签", self)
            act_del = QAction("删除", self)
            menu.addAction(act_edit)
            menu.addAction(act_del)

            def do_edit():
                text, ok = QInputDialog.getText(self, "编辑标签", "标签:", text=item.bbox.label)
                if ok:
                    item.bbox.label = text
                    self._sync_items()
                    self.bbox_changed.emit()

            def do_del():
                idx = self._bbox_manager.bboxes.index(item.bbox)
                self._bbox_manager.remove(idx)
                self._sync_items()
                self.bbox_changed.emit()

            act_edit.triggered.connect(do_edit)
            act_del.triggered.connect(do_del)
            menu.exec_(self.mapToGlobal(pos))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete and self._bbox_manager:
            if self._bbox_manager.selected_idx >= 0:
                self._bbox_manager.remove(self._bbox_manager.selected_idx)
                self._sync_items()
                self.bbox_changed.emit()
        elif event.key() == Qt.Key_Escape and self._mode == "draw":
            self.set_mode("browse")
        super().keyPressEvent(event)

    def rotate_image(self, angle):
        if self._img_manager:
            self._img_manager.rotate(angle)
            self._load_pixmap()

    def resize_image(self, width, height):
        if self._img_manager:
            self._img_manager.resize(width, height)
            self._load_pixmap()
