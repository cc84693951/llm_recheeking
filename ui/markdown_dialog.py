from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextBrowser, QPushButton, QHBoxLayout
from PyQt5.QtCore import Qt


class MarkdownDialog(QDialog):
    def __init__(self, title, markdown_text, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(500, 400)
        layout = QVBoxLayout(self)

        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True)
        # PyQt5 QTextBrowser 原生支持部分 Markdown：
        # 标题、粗体、斜体、列表、代码块、分隔线等
        self.browser.setMarkdown(markdown_text)
        layout.addWidget(self.browser)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_ok = QPushButton("关闭")
        self.btn_ok.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_ok)
        layout.addLayout(btn_layout)
