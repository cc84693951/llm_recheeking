from concurrent.futures import ThreadPoolExecutor, as_completed
from PyQt5.QtCore import QThread, pyqtSignal
from core.llm_client import LLMClient


class InspectionTask:
    def __init__(self, img_manager, bbox_manager, expand_settings, original_indices, file_index):
        self.img_manager = img_manager
        self.bbox_manager = bbox_manager
        self.expand_settings = expand_settings
        self.original_indices = original_indices
        self.file_index = file_index


class InspectionEngine(QThread):
    progress = pyqtSignal(int, int)  # current, total
    result = pyqtSignal(int, int, str)  # file_idx, bbox_idx_in_filtered, text
    finished_signal = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, tasks, client, system_prompt, user_prompt, few_shots, params, max_workers=3):
        super().__init__()
        self.tasks = tasks
        self.client = client
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
        self.few_shots = few_shots
        self.params = params
        self.max_workers = max_workers
        self._running = True

    def run(self):
        try:
            total = sum(len(t.bbox_manager.bboxes) for t in self.tasks)
            current = 0

            def inspect_one(task, i):
                bbox = task.bbox_manager.bboxes[i]
                img_w, img_h = task.img_manager.size
                x, y, w, h = bbox.expanded_coords(
                    img_w, img_h,
                    center=task.expand_settings.get("center", 0),
                    top=task.expand_settings.get("top", 1.0),
                    bottom=task.expand_settings.get("bottom", 1.0),
                    left=task.expand_settings.get("left", 1.0),
                    right=task.expand_settings.get("right", 1.0),
                )
                crop = task.img_manager.crop(x, y, w, h)
                if crop is None:
                    return task.file_index, i, "裁剪失败"

                text = self.client.inspect(
                    crop,
                    self.system_prompt,
                    self.user_prompt,
                    self.few_shots,
                    self.params,
                )
                return task.file_index, i, text.strip()

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_map = {}
                for task in self.tasks:
                    if not self._running:
                        break
                    for i in range(len(task.bbox_manager.bboxes)):
                        future = executor.submit(inspect_one, task, i)
                        future_map[future] = (task, i)

                for future in as_completed(future_map):
                    if not self._running:
                        break
                    current += 1
                    self.progress.emit(current, total)
                    try:
                        file_idx, filtered_idx, text = future.result()
                        self.result.emit(file_idx, filtered_idx, text)
                    except Exception as e:
                        task, i = future_map[future]
                        self.result.emit(task.file_index, i, f"Error: {str(e)}")

            if self._running:
                self.finished_signal.emit()
        except Exception as e:
            self.error.emit(str(e))

    def stop(self):
        self._running = False
        self.wait(2000)
