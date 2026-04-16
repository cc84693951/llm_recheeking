import os
import logging
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QAction, QFileDialog,
    QMessageBox, QInputDialog, QStatusBar, QSplitter, QVBoxLayout, QDialog,
    QToolBar, QShortcut
)
from PyQt5.QtGui import QKeySequence
from PyQt5.QtCore import Qt
from config import APP_NAME, SUPPORTED_IMAGE_EXTENSIONS

# UI 日志配置
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
ui_logger = logging.getLogger("ui")
ui_logger.setLevel(logging.DEBUG)
if not ui_logger.handlers:
    handler = logging.FileHandler(os.path.join(LOG_DIR, "app.log"), encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    handler.setFormatter(formatter)
    ui_logger.addHandler(handler)
from core.image_manager import ImageManager
from core.bbox_manager import BBoxManager, BBox
from core.settings_manager import SettingsManager
from core.llm_client import LLMClient
from core.inspection_engine import InspectionEngine
from core.label_parsers import parse_voc, save_voc, parse_yolo, save_yolo, parse_coco, save_coco
from core.excel_exporter import export_results_to_excel
from ui.file_list_widget import FileListWidget
from ui.image_canvas import ImageCanvas
from ui.control_panel import ControlPanel
from ui.settings_dialog import SettingsDialog
from ui.few_shot_dialog import FewShotDialog
from ui.progress_dialog import ProgressDialog
from ui.label_list_widget import LabelListWidget
from ui.label_filter_widget import LabelFilterWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1600, 950)

        self.settings = SettingsManager()
        self.img_manager = ImageManager()
        self.bbox_manager = BBoxManager()
        self.current_files = []
        self.current_file_index = -1
        self.result_dir = ""
        self._last_label = ""
        self._class_names = []  # 用于 YOLO class name 映射

        self._init_ui()
        self._init_menu()
        self._load_settings()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(4, 4, 4, 4)

        # 顶部工具栏
        self.toolbar = QToolBar("工具栏")
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)
        self.act_mode_browse = QAction("浏览模式 (Esc)", self)
        self.act_mode_browse.setCheckable(True)
        self.act_mode_browse.setChecked(True)
        self.act_mode_draw = QAction("绘制矩形框 (W)", self)
        self.act_mode_draw.setCheckable(True)
        self.act_mode_draw.setChecked(False)
        self.act_prev_img = QAction("上一张 (A)", self)
        self.act_next_img = QAction("下一张 (D)", self)
        self.act_save_shortcut = QAction("保存 (Ctrl+S)", self)
        self.act_del_bbox = QAction("删除框 (Del/Backspace)", self)
        self.toolbar.addAction(self.act_mode_draw)
        self.toolbar.addAction(self.act_mode_browse)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.act_prev_img)
        self.toolbar.addAction(self.act_next_img)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.act_save_shortcut)
        self.toolbar.addAction(self.act_del_bbox)

        self.act_mode_browse.triggered.connect(lambda: self._set_canvas_mode("browse"))
        self.act_mode_draw.triggered.connect(lambda: self._set_canvas_mode("draw"))
        self.act_prev_img.triggered.connect(self._prev_image)
        self.act_next_img.triggered.connect(self._next_image)
        self.act_save_shortcut.triggered.connect(self._on_save)
        self.act_del_bbox.triggered.connect(self._on_bbox_delete_from_list)

        # 快捷键
        QShortcut(QKeySequence("W"), self, activated=lambda: self._set_canvas_mode("draw"))
        QShortcut(QKeySequence("Esc"), self, activated=lambda: self._set_canvas_mode("browse"))
        QShortcut(QKeySequence("A"), self, activated=self._prev_image)
        QShortcut(QKeySequence("D"), self, activated=self._next_image)
        QShortcut(QKeySequence("Ctrl+S"), self, activated=self._on_save)
        QShortcut(QKeySequence("Delete"), self, activated=self._on_bbox_delete_from_list)
        QShortcut(QKeySequence("Backspace"), self, activated=self._on_bbox_delete_from_list)

        h_layout = QHBoxLayout()
        main_layout.addLayout(h_layout)

        # 左侧：文件列表 + Label 列表
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.file_list = FileListWidget()
        self.file_list.item_selected.connect(self._switch_image)
        self.file_list.open_image_clicked.connect(self._open_image)
        self.file_list.open_folder_clicked.connect(self._open_folder)
        self.file_list.open_annotation_clicked.connect(self._import_annotations)
        self.file_list.save_all_clicked.connect(self._on_save_all)
        self.file_list.export_excel_clicked.connect(self._on_export_excel)

        self.label_list = LabelListWidget()
        self.label_list.label_selected.connect(self._on_label_selected_from_list)
        self.label_list.label_changed.connect(self._on_label_changed_from_list)
        self.label_list.bbox_delete_requested.connect(self._on_bbox_delete_from_list)

        left_layout.addWidget(self.file_list, 2)
        left_layout.addWidget(self.label_list, 1)
        left_widget.setMaximumWidth(280)

        # 中间：画布
        self.canvas = ImageCanvas()
        self.canvas.set_image_manager(self.img_manager)
        self.canvas.set_bbox_manager(self.bbox_manager)
        self.canvas.request_label_input.connect(self._on_request_label_input)
        self.canvas.bbox_changed.connect(self._refresh_label_list)
        self.canvas.bbox_added.connect(self._refresh_label_list)

        self.canvas.mode_changed.connect(self._on_canvas_mode_changed)

        # 右侧：控制面板 + Label 过滤
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.control = ControlPanel()
        self.control.inspect_clicked.connect(self._on_inspect)
        self.control.save_clicked.connect(self._on_save)
        self.control.few_shot_clicked.connect(self._on_few_shot)
        self.control.settings_clicked.connect(self._on_settings)
        self.control.expand_preview_changed.connect(self._on_expand_preview)
        self.control.scope_changed.connect(self._on_scope_changed)
        self.control.preview_system_md_clicked.connect(self._on_preview_system_md)
        self.control.import_system_md_clicked.connect(self._on_import_system_md)
        self.control.export_system_md_clicked.connect(self._on_export_system_md)
        self.control.preview_user_md_clicked.connect(self._on_preview_user_md)
        self.control.import_user_md_clicked.connect(self._on_import_user_md)
        self.control.export_user_md_clicked.connect(self._on_export_user_md)

        self.label_filter = LabelFilterWidget()

        right_layout.addWidget(self.control, 3)
        right_layout.addWidget(self.label_filter, 1)
        right_widget.setMaximumWidth(380)

        h_layout.addWidget(left_widget, 1)
        h_layout.addWidget(self.canvas, 4)
        h_layout.addWidget(right_widget, 1)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    def _init_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("文件")
        act_open_img = QAction("打开图片", self)
        act_open_dir = QAction("打开文件夹", self)
        act_save = QAction("保存结果 (当前)", self)
        act_save_all = QAction("保存所有结果", self)
        act_export_excel = QAction("导出 Excel 表格...", self)
        act_open_img.triggered.connect(self._open_image)
        act_open_dir.triggered.connect(self._open_folder)
        act_save.triggered.connect(self._on_save)
        act_save_all.triggered.connect(self._on_save_all)
        act_export_excel.triggered.connect(self._on_export_excel)
        file_menu.addAction(act_open_img)
        file_menu.addAction(act_open_dir)
        file_menu.addSeparator()
        file_menu.addAction(act_save)
        file_menu.addAction(act_save_all)
        file_menu.addSeparator()
        file_menu.addAction(act_export_excel)

        label_menu = menubar.addMenu("标注")
        act_load_voc = QAction("导入 VOC (XML)", self)
        act_load_yolo = QAction("导入 YOLO (txt)", self)
        act_load_coco = QAction("导入 COCO (JSON)", self)
        act_save_voc = QAction("导出为 VOC", self)
        act_save_yolo = QAction("导出为 YOLO", self)
        act_save_coco = QAction("导出为 COCO", self)
        act_load_voc.triggered.connect(self._import_voc)
        act_load_yolo.triggered.connect(self._import_yolo)
        act_load_coco.triggered.connect(self._import_coco)
        act_save_voc.triggered.connect(self._export_voc)
        act_save_yolo.triggered.connect(self._export_yolo)
        act_save_coco.triggered.connect(self._export_coco)
        label_menu.addAction(act_load_voc)
        label_menu.addAction(act_load_yolo)
        label_menu.addAction(act_load_coco)
        label_menu.addSeparator()
        label_menu.addAction(act_save_voc)
        label_menu.addAction(act_save_yolo)
        label_menu.addAction(act_save_coco)
        label_menu.addSeparator()
        act_export_anno = QAction("导出标注文件...", self)
        act_export_anno.triggered.connect(self._export_annotations)
        label_menu.addAction(act_export_anno)

        img_menu = menubar.addMenu("图像")
        act_rot90 = QAction("顺时针旋转90°", self)
        act_rot270 = QAction("逆时针旋转90°", self)
        act_resize = QAction("Resize...", self)
        act_reset = QAction("重置显示", self)
        act_rot90.triggered.connect(lambda: self.canvas.rotate_image(-90))
        act_rot270.triggered.connect(lambda: self.canvas.rotate_image(90))
        act_resize.triggered.connect(self._resize_image)
        act_reset.triggered.connect(self.canvas._load_pixmap)
        img_menu.addAction(act_rot90)
        img_menu.addAction(act_rot270)
        img_menu.addAction(act_resize)
        img_menu.addAction(act_reset)

    def _sync_model_selector_config(self):
        """将当前 settings 中的 API 配置同步到 ModelSelector"""
        api_mode = self.settings.get("api_mode", "cloud")
        if api_mode == "cloud":
            base_url = self.settings.get("cloud_base_url", "")
            api_key = self.settings.get("cloud_api_key", "")
        else:
            base_url = self.settings.get("local_base_url", "")
            api_key = self.settings.get("local_api_key", "")
        self.control.model_selector.set_api_config(api_mode, base_url, api_key)

    def _load_settings(self):
        self.control.set_prompts(
            self.settings.get("system_prompt", ""),
            self.settings.get("user_prompt", ""),
        )
        self.control.set_params(self.settings.get("model_params", {}))
        self.control.set_stream(self.settings.get("stream", True))
        self._sync_model_selector_config()
        self.control.model_selector.set_current_text(self.settings.get("selected_model", ""))
        self.control.model_selector.load_cached_models()
        self.control.model_selector.set_current_text(self.settings.get("selected_model", ""))

    def _save_current_settings(self):
        sys_p, usr_p = self.control.get_prompts()
        self.settings.set("system_prompt", sys_p)
        self.settings.set("user_prompt", usr_p)
        self.settings.set("model_params", self.control.get_params())
        self.settings.set("stream", self.control.get_stream())
        self.settings.set("selected_model", self.control.model_selector.current_text())
        self.settings.save()

    def _open_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "打开图片", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp)"
        )
        if path:
            ui_logger.info(f"[OPEN IMAGE] {path}")
            self.current_files = [path]
            self.file_list.set_files([os.path.basename(path)])
            self._switch_image(0)

    def _open_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "打开文件夹")
        if folder:
            files = sorted([
                f for f in os.listdir(folder)
                if f.lower().endswith(SUPPORTED_IMAGE_EXTENSIONS)
            ])
            paths = [os.path.join(folder, f) for f in files]
            ui_logger.info(f"[OPEN FOLDER] {folder} | {len(paths)} images")
            self.current_files = paths
            self.file_list.set_files(files)
            if paths:
                self._switch_image(0)

    def _switch_image(self, idx):
        if not (0 <= idx < len(self.current_files)):
            return
        self._save_annotations()
        self.current_file_index = idx
        path = self.current_files[idx]
        self.img_manager.load(path)
        self.bbox_manager.clear()
        self._load_annotations(path)
        self.canvas.set_expand_settings(self.control.get_expand_settings())
        self.canvas._load_pixmap()
        self._refresh_label_list()
        self.status_bar.showMessage(f"{idx+1}/{len(self.current_files)}  {path}  尺寸:{self.img_manager.size}")
        self.file_list.select_index(idx)

    def _save_annotations(self):
        if self.current_file_index < 0:
            return
        path = self.current_files[self.current_file_index]
        # 默认保存为 VOC / JSON / YOLO 的同名文件（如果存在则覆盖）
        base, _ = os.path.splitext(path)
        # 内部 JSON 也保存一份
        import json
        json_path = base + "_llm.json"
        data = {"image_path": path, "bboxes": self.bbox_manager.to_list()}
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # 如果存在对应的 VOC/XML 则同步更新
        voc_path = base + ".xml"
        if os.path.exists(voc_path):
            try:
                w, h = self.img_manager.size
                save_voc(voc_path, path, w, h, self.bbox_manager)
            except Exception:
                pass
        # YOLO
        yolo_path = base + ".txt"
        if os.path.exists(yolo_path):
            try:
                w, h = self.img_manager.size
                save_yolo(yolo_path, w, h, self.bbox_manager, self._class_names or None)
            except Exception:
                pass

    def _load_annotations(self, path):
        base, _ = os.path.splitext(path)
        # 优先加载内部 JSON
        json_path = base + "_llm.json"
        if os.path.exists(json_path):
            import json
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.bbox_manager.from_list(data.get("bboxes", []))
                return
            except Exception:
                pass
        # 其次 VOC
        voc_path = base + ".xml"
        if os.path.exists(voc_path):
            try:
                w, h = self.img_manager.size
                bboxes = parse_voc(voc_path, w, h)
                self.bbox_manager.from_list([b.to_dict() for b in bboxes])
                return
            except Exception:
                pass
        # 其次 YOLO
        yolo_path = base + ".txt"
        if os.path.exists(yolo_path):
            try:
                w, h = self.img_manager.size
                bboxes = parse_yolo(yolo_path, w, h, self._class_names or None)
                self.bbox_manager.from_list([b.to_dict() for b in bboxes])
                return
            except Exception:
                pass
        # COCO 无法自动按图名关联，需要用户手动导入

    def _on_request_label_input(self, idx):
        text, ok = QInputDialog.getText(self, "设置标签", "Label:", text=self._last_label)
        if ok:
            bbox = self.bbox_manager.get(idx)
            if bbox:
                bbox.label = text.strip()
                self._last_label = text.strip()
                self.canvas._sync_items()
                self._refresh_label_list()
                self._save_annotations()

    def _on_label_selected_from_list(self, label):
        for i, bbox in enumerate(self.bbox_manager.bboxes):
            if (bbox.label or f"#{i}") == label:
                self.bbox_manager.select(i)
                self.canvas._sync_items()
                self.canvas.bbox_selected.emit(i)
                break

    def _on_label_changed_from_list(self, old_label, new_label):
        changed = False
        for bbox in self.bbox_manager.bboxes:
            if bbox.label == old_label:
                bbox.label = new_label
                changed = True
        if changed:
            self.canvas._sync_items()
            self._refresh_label_list()
            self._save_annotations()

    def _on_bbox_delete_from_list(self):
        # 删除当前选中的 bbox
        if self.bbox_manager.selected_idx >= 0:
            self.bbox_manager.remove(self.bbox_manager.selected_idx)
            self.canvas._sync_items()
            self._refresh_label_list()
            self._save_annotations()
        else:
            QMessageBox.information(self, "提示", "请先点击列表选中一个框")

    def _set_canvas_mode(self, mode):
        ui_logger.info(f"[MODE CHANGE] {mode}")
        self.canvas.set_mode(mode)

    def _on_canvas_mode_changed(self, mode):
        self.act_mode_browse.setChecked(mode == "browse")
        self.act_mode_draw.setChecked(mode == "draw")
        if mode == "draw":
            self.status_bar.showMessage("绘制模式：按住左键拖拽画框，画完自动退出")
        else:
            self.status_bar.showMessage("浏览模式：滚轮缩放，左键拖拽移动图片")

    def _prev_image(self):
        if self.current_files and self.current_file_index > 0:
            self._switch_image(self.current_file_index - 1)

    def _next_image(self):
        if self.current_files and self.current_file_index < len(self.current_files) - 1:
            self._switch_image(self.current_file_index + 1)

    def _refresh_label_list(self):
        self.label_list.refresh(self.bbox_manager)
        labels = [bbox.label for bbox in self.bbox_manager.bboxes if bbox.label]
        self.label_filter.refresh(labels)

    def _on_scope_changed(self):
        scope = self.control.get_inspect_scope()
        if scope == "all" and self.current_files:
            all_labels = set()
            for path in self.current_files:
                img_mgr = ImageManager()
                img_mgr.load(path)
                bm = BBoxManager()
                self._load_annotations_for_manager(path, img_mgr, bm)
                for b in bm.bboxes:
                    if b.label:
                        all_labels.add(b.label)
            self.label_filter.refresh(sorted(all_labels))
            ui_logger.info(f"[SCOPE ALL] collected {len(all_labels)} labels from {len(self.current_files)} images")
        else:
            self._refresh_label_list()

    def _on_expand_preview(self, checked):
        self.canvas.set_expand_settings(self.control.get_expand_settings())

    def _on_settings(self):
        dlg = SettingsDialog(self.settings, self)
        if dlg.exec_() == QDialog.Accepted:
            # 设置保存后同步 API 配置并刷新模型列表
            self._sync_model_selector_config()
            self.control.model_selector.refresh_models()

    def _on_preview_system_md(self):
        from ui.markdown_dialog import MarkdownDialog
        text = self.control.system_prompt.toPlainText()
        dlg = MarkdownDialog("系统提示词 - Markdown 预览", text, self)
        dlg.exec_()

    def _on_import_system_md(self):
        path, _ = QFileDialog.getOpenFileName(self, "导入系统提示词 Markdown", "", "Markdown (*.md)")
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self.control.system_prompt.setPlainText(f.read())
                ui_logger.info(f"[IMPORT SYSTEM MD] {path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导入失败:\n{e}")

    def _on_export_system_md(self):
        path, _ = QFileDialog.getSaveFileName(self, "导出系统提示词 Markdown", "system_prompt.md", "Markdown (*.md)")
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(self.control.system_prompt.toPlainText())
                ui_logger.info(f"[EXPORT SYSTEM MD] {path}")
                QMessageBox.information(self, "提示", f"已导出到:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败:\n{e}")

    def _on_preview_user_md(self):
        from ui.markdown_dialog import MarkdownDialog
        text = self.control.user_prompt.toPlainText()
        dlg = MarkdownDialog("用户提示词 - Markdown 预览", text, self)
        dlg.exec_()

    def _on_import_user_md(self):
        path, _ = QFileDialog.getOpenFileName(self, "导入用户提示词 Markdown", "", "Markdown (*.md)")
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self.control.user_prompt.setPlainText(f.read())
                ui_logger.info(f"[IMPORT USER MD] {path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导入失败:\n{e}")

    def _on_export_user_md(self):
        path, _ = QFileDialog.getSaveFileName(self, "导出用户提示词 Markdown", "user_prompt.md", "Markdown (*.md)")
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(self.control.user_prompt.toPlainText())
                ui_logger.info(f"[EXPORT USER MD] {path}")
                QMessageBox.information(self, "提示", f"已导出到:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败:\n{e}")

    def _on_few_shot(self):
        shots = self.settings.get("few_shots", [])
        dlg = FewShotDialog(shots, self)
        if dlg.exec_() == QDialog.Accepted:
            self.settings.set("few_shots", dlg.get_few_shots())
            self.settings.save()

    def _on_save(self):
        if self.current_file_index < 0:
            QMessageBox.warning(self, "提示", "没有可保存的内容")
            return
        self._save_annotations()
        path = self.current_files[self.current_file_index]
        base, ext = os.path.splitext(path)
        default_name = os.path.basename(base) + "_result" + ext
        save_path, _ = QFileDialog.getSaveFileName(
            self, "保存结果图片", default_name,
            "Images (*.png *.jpg *.jpeg *.bmp *.tiff *.webp)"
        )
        if not save_path:
            return
        img = self.img_manager.draw_bboxes(
            self.bbox_manager,
            show_expanded=False,
            expand_settings={}
        )
        if img:
            img.save(save_path)
            ui_logger.info(f"[SAVE RESULT] {save_path}")
            QMessageBox.information(self, "提示", f"结果已保存到:\n{save_path}")

    def _on_save_all(self):
        if not self.current_files:
            QMessageBox.warning(self, "提示", "没有可保存的内容")
            return
        folder = QFileDialog.getExistingDirectory(self, "选择保存目录")
        if not folder:
            return
        ok_count = 0
        for path in self.current_files:
            base, ext = os.path.splitext(path)
            default_name = os.path.basename(base) + "_result" + ext
            save_path = os.path.join(folder, default_name)
            img_mgr = ImageManager()
            img_mgr.load(path)
            bm = BBoxManager()
            self._load_annotations_for_manager(path, img_mgr, bm)
            img = img_mgr.draw_bboxes(bm, show_expanded=False, expand_settings={})
            if img:
                img.save(save_path)
                ok_count += 1
        ui_logger.info(f"[SAVE ALL RESULTS] folder={folder} count={ok_count}")
        QMessageBox.information(self, "提示", f"全量保存完成。\n成功: {ok_count} 张")

    def _on_export_excel(self):
        if not self.current_files:
            QMessageBox.warning(self, "提示", "没有可导出的内容")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "导出 Excel 表格", "results.xlsx", "Excel (*.xlsx)"
        )
        if not path:
            return
        try:
            expand = self.control.get_expand_settings()

            def getter(img_path):
                img_mgr = ImageManager()
                img_mgr.load(img_path)
                bm = BBoxManager()
                self._load_annotations_for_manager(img_path, img_mgr, bm)
                return img_mgr, bm, expand

            export_results_to_excel(self.current_files, getter, path)
            ui_logger.info(f"[EXPORT EXCEL] {path}")
            QMessageBox.information(self, "提示", f"Excel 已导出到:\n{path}")
        except Exception as e:
            ui_logger.error(f"[EXPORT EXCEL ERROR] {e}")
            QMessageBox.critical(self, "错误", f"导出失败:\n{e}")

    def _resize_image(self):
        if self.img_manager.original_image is None:
            return
        w, h = self.img_manager.size
        new_w, ok = QInputDialog.getInt(self, "Resize", "宽度:", w, 1, 10000)
        if not ok:
            return
        new_h, ok2 = QInputDialog.getInt(self, "Resize", "高度:", h, 1, 10000)
        if ok2:
            self.canvas.resize_image(new_w, new_h)

    # ==================== 导入导出 ====================
    def _import_voc(self):
        if not self.current_files:
            QMessageBox.warning(self, "提示", "请先打开图片或文件夹")
            return
        folder = QFileDialog.getExistingDirectory(self, "选择 VOC 标注文件夹")
        if not folder:
            return
        ok_count = 0
        fail_count = 0
        for img_path in self.current_files:
            base = os.path.splitext(os.path.basename(img_path))[0]
            xml_path = os.path.join(folder, base + ".xml")
            if os.path.exists(xml_path):
                try:
                    from PIL import Image
                    pil = Image.open(img_path)
                    bboxes = parse_voc(xml_path, *pil.size)
                    bm = BBoxManager()
                    bm.from_list([b.to_dict() for b in bboxes])
                    # 保存为内部 json
                    json_path = os.path.splitext(img_path)[0] + "_llm.json"
                    import json
                    with open(json_path, "w", encoding="utf-8") as f:
                        json.dump({"image_path": img_path, "bboxes": bm.to_list()}, f, ensure_ascii=False, indent=2)
                    ok_count += 1
                except Exception:
                    fail_count += 1
        if self.current_file_index >= 0:
            self._switch_image(self.current_file_index)
        ui_logger.info(f"[IMPORT VOC BATCH] folder={folder} success={ok_count} fail={fail_count}")
        QMessageBox.information(self, "提示", f"批量导入 VOC 完成。\n成功: {ok_count} 张\n失败/未找到: {fail_count} 张")

    def _import_yolo(self):
        if not self.current_files:
            QMessageBox.warning(self, "提示", "请先打开图片或文件夹")
            return
        folder = QFileDialog.getExistingDirectory(self, "选择 YOLO 标注文件夹")
        if not folder:
            return
        classes_path = os.path.join(folder, "classes.txt")
        class_names = None
        if os.path.exists(classes_path):
            with open(classes_path, "r", encoding="utf-8") as f:
                class_names = [line.strip() for line in f if line.strip()]
            self._class_names = class_names
        ok_count = 0
        fail_count = 0
        for img_path in self.current_files:
            base = os.path.splitext(os.path.basename(img_path))[0]
            txt_path = os.path.join(folder, base + ".txt")
            if os.path.exists(txt_path):
                try:
                    from PIL import Image
                    pil = Image.open(img_path)
                    bboxes = parse_yolo(txt_path, *pil.size, class_names)
                    bm = BBoxManager()
                    bm.from_list([b.to_dict() for b in bboxes])
                    json_path = os.path.splitext(img_path)[0] + "_llm.json"
                    import json
                    with open(json_path, "w", encoding="utf-8") as f:
                        json.dump({"image_path": img_path, "bboxes": bm.to_list()}, f, ensure_ascii=False, indent=2)
                    ok_count += 1
                except Exception:
                    fail_count += 1
        if self.current_file_index >= 0:
            self._switch_image(self.current_file_index)
        ui_logger.info(f"[IMPORT YOLO BATCH] folder={folder} success={ok_count} fail={fail_count}")
        QMessageBox.information(self, "提示", f"批量导入 YOLO 完成。\n成功: {ok_count} 张\n失败/未找到: {fail_count} 张")

    def _import_coco(self):
        if not self.current_files:
            QMessageBox.warning(self, "提示", "请先打开图片或文件夹")
            return
        path, _ = QFileDialog.getOpenFileName(self, "导入 COCO JSON", "", "JSON (*.json)")
        if not path:
            return
        ok_count = 0
        fail_count = 0
        for img_path in self.current_files:
            try:
                from PIL import Image
                pil = Image.open(img_path)
                bboxes = parse_coco(path, img_path, *pil.size)
                if bboxes:
                    bm = BBoxManager()
                    bm.from_list([b.to_dict() for b in bboxes])
                    json_path = os.path.splitext(img_path)[0] + "_llm.json"
                    import json
                    with open(json_path, "w", encoding="utf-8") as f:
                        json.dump({"image_path": img_path, "bboxes": bm.to_list()}, f, ensure_ascii=False, indent=2)
                    ok_count += 1
                else:
                    fail_count += 1
            except Exception:
                fail_count += 1
        if self.current_file_index >= 0:
            self._switch_image(self.current_file_index)
        ui_logger.info(f"[IMPORT COCO BATCH] file={path} success={ok_count} fail={fail_count}")
        QMessageBox.information(self, "提示", f"批量导入 COCO 完成。\n成功: {ok_count} 张\n失败/未找到: {fail_count} 张")

    def _import_annotations(self):
        if not self.current_files:
            QMessageBox.warning(self, "提示", "请先打开图片或文件夹")
            return
        items = ["VOC (XML)", "YOLO (txt)", "COCO (JSON)"]
        from PyQt5.QtWidgets import QInputDialog
        item, ok = QInputDialog.getItem(self, "导入标注", "选择格式:", items, 0, False)
        if not ok:
            return
        if item == "VOC (XML)":
            self._import_voc()
        elif item == "YOLO (txt)":
            self._import_yolo()
        elif item == "COCO (JSON)":
            self._import_coco()

    def _export_voc(self):
        if self.current_file_index < 0:
            QMessageBox.warning(self, "提示", "请先打开图片")
            return
        img_path = self.current_files[self.current_file_index]
        base, _ = os.path.splitext(img_path)
        path = base + ".xml"
        try:
            w, h = self.img_manager.size
            save_voc(path, img_path, w, h, self.bbox_manager)
            QMessageBox.information(self, "提示", f"已保存到:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))

    def _export_yolo(self):
        if self.current_file_index < 0:
            QMessageBox.warning(self, "提示", "请先打开图片")
            return
        img_path = self.current_files[self.current_file_index]
        base, _ = os.path.splitext(img_path)
        txt_path = base + ".txt"
        try:
            w, h = self.img_manager.size
            save_yolo(txt_path, w, h, self.bbox_manager, self._class_names or None)
            # 同时保存 classes.txt
            if self._class_names:
                classes_path = os.path.join(os.path.dirname(txt_path), "classes.txt")
                with open(classes_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(self._class_names) + "\n")
            QMessageBox.information(self, "提示", f"已保存到:\n{txt_path}")
        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))

    def _export_coco(self):
        if not self.current_files:
            QMessageBox.warning(self, "提示", "没有可导出的图片")
            return
        path, _ = QFileDialog.getSaveFileName(self, "导出 COCO JSON", "annotations.json", "JSON (*.json)")
        if not path:
            return
        try:
            # 收集所有 bbox_managers（当前只有当前图的内存数据，其他图从 _llm.json 加载）
            all_bms = []
            for p in self.current_files:
                bm = BBoxManager()
                base, _ = os.path.splitext(p)
                json_path = base + "_llm.json"
                if os.path.exists(json_path):
                    import json
                    with open(json_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    bm.from_list(data.get("bboxes", []))
                else:
                    # 尝试 voc
                    voc_path = base + ".xml"
                    if os.path.exists(voc_path):
                        from PIL import Image
                        pil = Image.open(p)
                        bboxes = parse_voc(voc_path, *pil.size)
                        bm.from_list([b.to_dict() for b in bboxes])
                all_bms.append(bm)
            save_coco(path, os.path.dirname(self.current_files[0]), self.current_files, all_bms, existing_data=False)
            ui_logger.info(f"[EXPORT COCO] {path}")
            QMessageBox.information(self, "提示", f"已保存到:\n{path}")
        except Exception as e:
            ui_logger.error(f"[EXPORT COCO ERROR] {e}")
            QMessageBox.critical(self, "错误", str(e))

    def _export_annotations(self):
        if not self.current_files:
            QMessageBox.warning(self, "提示", "没有可导出的内容")
            return
        items = ["VOC (XML)", "YOLO (txt)", "COCO (JSON)"]
        item, ok = QInputDialog.getItem(self, "导出标注", "选择格式:", items, 0, False)
        if not ok:
            return

        def clean_bbox_manager(bm):
            clean = BBoxManager()
            for b in bm.bboxes:
                clean.add(BBox(b.x, b.y, b.w, b.h, label=b.label, result=""))
            return clean

        if item == "VOC (XML)":
            if self.current_file_index < 0:
                QMessageBox.warning(self, "提示", "请先打开图片")
                return
            img_path = self.current_files[self.current_file_index]
            base, _ = os.path.splitext(img_path)
            default_name = os.path.basename(base) + ".xml"
            path, _ = QFileDialog.getSaveFileName(self, "导出 VOC", default_name, "XML (*.xml)")
            if path:
                try:
                    w, h = self.img_manager.size
                    save_voc(path, img_path, w, h, clean_bbox_manager(self.bbox_manager))
                    ui_logger.info(f"[EXPORT VOC] {path}")
                    QMessageBox.information(self, "提示", f"已导出到:\n{path}")
                except Exception as e:
                    ui_logger.error(f"[EXPORT VOC ERROR] {e}")
                    QMessageBox.critical(self, "错误", str(e))
        elif item == "YOLO (txt)":
            if self.current_file_index < 0:
                QMessageBox.warning(self, "提示", "请先打开图片")
                return
            img_path = self.current_files[self.current_file_index]
            base, _ = os.path.splitext(img_path)
            default_name = os.path.basename(base) + ".txt"
            path, _ = QFileDialog.getSaveFileName(self, "导出 YOLO", default_name, "TXT (*.txt)")
            if path:
                try:
                    w, h = self.img_manager.size
                    save_yolo(path, w, h, clean_bbox_manager(self.bbox_manager), self._class_names or None)
                    if self._class_names:
                        classes_path = os.path.join(os.path.dirname(path), "classes.txt")
                        with open(classes_path, "w", encoding="utf-8") as f:
                            f.write("\n".join(self._class_names) + "\n")
                    ui_logger.info(f"[EXPORT YOLO] {path}")
                    QMessageBox.information(self, "提示", f"已导出到:\n{path}")
                except Exception as e:
                    ui_logger.error(f"[EXPORT YOLO ERROR] {e}")
                    QMessageBox.critical(self, "错误", str(e))
        elif item == "COCO (JSON)":
            path, _ = QFileDialog.getSaveFileName(self, "导出 COCO", "annotations.json", "JSON (*.json)")
            if path:
                try:
                    all_bms = []
                    for p in self.current_files:
                        bm = BBoxManager()
                        base, _ = os.path.splitext(p)
                        json_path = base + "_llm.json"
                        if os.path.exists(json_path):
                            import json
                            with open(json_path, "r", encoding="utf-8") as f:
                                data = json.load(f)
                            bm.from_list(data.get("bboxes", []))
                        else:
                            voc_path = base + ".xml"
                            if os.path.exists(voc_path):
                                from PIL import Image
                                pil = Image.open(p)
                                bboxes = parse_voc(voc_path, *pil.size)
                                bm.from_list([b.to_dict() for b in bboxes])
                        all_bms.append(clean_bbox_manager(bm))
                    save_coco(path, os.path.dirname(self.current_files[0]), self.current_files, all_bms, existing_data=False)
                    ui_logger.info(f"[EXPORT COCO] {path}")
                    QMessageBox.information(self, "提示", f"已导出到:\n{path}")
                except Exception as e:
                    ui_logger.error(f"[EXPORT COCO ERROR] {e}")
                    QMessageBox.critical(self, "错误", str(e))

    def _load_annotations_for_manager(self, path, img_manager, bbox_manager):
        base, _ = os.path.splitext(path)
        json_path = base + "_llm.json"
        if os.path.exists(json_path):
            import json
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                bbox_manager.from_list(data.get("bboxes", []))
                return
            except Exception:
                pass
        voc_path = base + ".xml"
        if os.path.exists(voc_path):
            try:
                w, h = img_manager.size
                bboxes = parse_voc(voc_path, w, h)
                bbox_manager.from_list([b.to_dict() for b in bboxes])
                return
            except Exception:
                pass
        yolo_path = base + ".txt"
        if os.path.exists(yolo_path):
            try:
                w, h = img_manager.size
                bboxes = parse_yolo(yolo_path, w, h, self._class_names or None)
                bbox_manager.from_list([b.to_dict() for b in bboxes])
                return
            except Exception:
                pass

    # ==================== 送检 ====================
    def _on_inspect(self):
        if self.img_manager.original_image is None:
            QMessageBox.warning(self, "提示", "请先打开图片")
            return

        model = self.control.model_selector.current_text()
        if not model:
            QMessageBox.warning(self, "提示", "请选择模型")
            return
        # 记住自定义输入的模型名
        self.control.model_selector.remember_current_model()

        scope = self.control.get_inspect_scope()
        expand = self.control.get_expand_settings()
        selected_labels = self.label_filter.get_selected_labels()
        ui_logger.info(
            f"[INSPECT START] scope={scope} model={model} "
            f"labels={selected_labels} expand={expand}"
        )

        from core.inspection_engine import InspectionTask
        tasks = []

        if scope == "current":
            if not self.bbox_manager.bboxes:
                QMessageBox.warning(self, "提示", "请先绘制检测框")
                return
            filtered_bm = BBoxManager()
            original_indices = []
            for idx, bbox in enumerate(self.bbox_manager.bboxes):
                if selected_labels and bbox.label not in selected_labels:
                    continue
                filtered_bm.add(BBox(bbox.x, bbox.y, bbox.w, bbox.h, label=bbox.label, result=bbox.result))
                original_indices.append(idx)
            if not filtered_bm.bboxes:
                QMessageBox.warning(self, "提示", "当前过滤条件下没有需要送检的框")
                return
            tasks.append(InspectionTask(self.img_manager, filtered_bm, expand, original_indices, self.current_file_index))
            ui_logger.info(f"[INSPECT TASKS] current image | bboxes={len(filtered_bm.bboxes)}")
        else:
            if not self.current_files:
                QMessageBox.warning(self, "提示", "没有可送检的图片")
                return
            for fidx, path in enumerate(self.current_files):
                img_mgr = ImageManager()
                img_mgr.load(path)
                bm = BBoxManager()
                self._load_annotations_for_manager(path, img_mgr, bm)
                filtered_bm = BBoxManager()
                original_indices = []
                for idx, bbox in enumerate(bm.bboxes):
                    if selected_labels and bbox.label not in selected_labels:
                        continue
                    filtered_bm.add(BBox(bbox.x, bbox.y, bbox.w, bbox.h, label=bbox.label, result=bbox.result))
                    original_indices.append(idx)
                if filtered_bm.bboxes:
                    tasks.append(InspectionTask(img_mgr, filtered_bm, expand, original_indices, fidx))
            if not tasks:
                QMessageBox.warning(self, "提示", "所有图片中都没有符合条件的框")
                return
            total_bboxes = sum(len(t.bbox_manager.bboxes) for t in tasks)
            ui_logger.info(f"[INSPECT TASKS] all images | task_count={len(tasks)} total_bboxes={total_bboxes}")

        self._save_current_settings()
        self._inspect_task_map = {t.file_index: t for t in tasks}
        api_mode = self.settings.get("api_mode", "cloud")
        base_url = self.settings.get("cloud_base_url", "") if api_mode == "cloud" else self.settings.get("local_base_url", "")
        api_key = self.settings.get("cloud_api_key", "") if api_mode == "cloud" else self.settings.get("local_api_key", "")

        client = LLMClient(api_mode, base_url, api_key, model)
        sys_p, usr_p = self.control.get_prompts()
        params = self.control.get_params()
        few_shots = self.settings.get("few_shots", [])

        self.progress_dlg = ProgressDialog(self)
        stream = self.control.get_stream()
        self.engine = InspectionEngine(tasks, client, sys_p, usr_p, few_shots, params, stream=stream)
        self.engine.progress.connect(self.progress_dlg.set_progress)
        self.engine.result.connect(self._on_inspect_result)
        self.engine.finished_signal.connect(self._on_inspect_finished)
        self.engine.error.connect(self._on_inspect_error)
        self.progress_dlg.rejected.connect(self._cancel_inspect)
        self.progress_dlg.show()
        self.control.btn_inspect.setEnabled(False)
        self.engine.start()

    def _on_inspect_result(self, file_idx, filtered_idx, text):
        task = self._inspect_task_map.get(file_idx)
        if not task:
            return
        orig_idx = task.original_indices[filtered_idx]
        path = self.current_files[file_idx]
        base, _ = os.path.splitext(path)
        json_path = base + "_llm.json"

        import json
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            bboxes_data = data.get("bboxes", [])
        else:
            data = {"image_path": path, "bboxes": []}
            bboxes_data = data["bboxes"]

        if len(bboxes_data) <= orig_idx:
            bm = BBoxManager()
            img_mgr = ImageManager()
            img_mgr.load(path)
            self._load_annotations_for_manager(path, img_mgr, bm)
            bboxes_data = [b.to_dict() for b in bm.bboxes]
            data["bboxes"] = bboxes_data

        if 0 <= orig_idx < len(bboxes_data):
            bboxes_data[orig_idx]["result"] = text
            data["bboxes"] = bboxes_data
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        if file_idx == self.current_file_index:
            bbox = self.bbox_manager.get(orig_idx)
            if bbox:
                bbox.result = text
            self.canvas._sync_items()

    def _on_inspect_finished(self):
        self.progress_dlg.finish()
        self.control.btn_inspect.setEnabled(True)
        QMessageBox.information(self, "完成", "送检完成")
        self._refresh_label_list()

    def _on_inspect_error(self, msg):
        self.progress_dlg.finish()
        self.control.btn_inspect.setEnabled(True)
        QMessageBox.critical(self, "错误", f"送检出错:\n{msg}")

    def _cancel_inspect(self):
        if hasattr(self, "engine") and self.engine.isRunning():
            self.engine.stop()
        self.control.btn_inspect.setEnabled(True)

    def closeEvent(self, event):
        self._save_annotations()
        self._save_current_settings()
        event.accept()
