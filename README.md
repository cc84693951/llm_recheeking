# LLM ReCheck - 模拟小模型检测送检大模型复判系统

一个基于 PyQt5 的桌面应用，用于将图像检测框（小模型结果）批量送入大模型进行复判，并将结果回写到标注中。

## 核心功能

- **图像与标注管理**
  - 打开单张图片或整个文件夹
  - 支持 Pascal VOC、YOLO、COCO 格式的批量导入与导出
  - 类似 LabelImg 的矩形框绘制、编辑、删除、标签管理

- **大模型送检**
  - 支持**云端**（硅基流动 SiliconFlow）和**本地**（OpenAI 兼容接口，如 ollama / vLLM）两种模式
  - 可配置系统提示词、用户提示词、Few-Shot 示例（含图片示例）
  - 支持按 Label 过滤送检
  - 支持**单张图片**或**所有图片**批量送检
  - 3 线程并发 + Session 复用，提升送检效率

- **扩展与预览**
  - 支持中心、上、下、左、右多方向扩展矩形框
  - 实时预览扩展后的虚线框范围

- **结果保存**
  - 保存单张或全量带标签的结果图片
  - 导出 Excel 表格（含框坐标、扩展后坐标、复判结果、渲染缩略图）

- **提示词增强**
  - 系统提示词和用户提示词支持 Markdown 导入、导出和实时预览

## 快捷键

| 快捷键 | 功能 |
|--------|------|
| `W` | 进入绘制矩形框模式 |
| `Esc` | 回到浏览模式 |
| `Delete` / `Backspace` | 删除当前选中的检测框 |
| `A` | 上一张图片 |
| `D` | 下一张图片 |
| `Ctrl + S` | 保存当前结果图片 |

## 运行方式

```bash
pip install -r requirements.txt
python main.py
```

## 项目结构

```
llm_recheeking/
├── main.py                 # 程序入口
├── config.py               # 全局配置
├── requirements.txt        # 依赖清单
├── ARCHITECTURE.md         # 详细架构文档
├── core/                   # 核心逻辑
│   ├── image_manager.py
│   ├── bbox_manager.py
│   ├── llm_client.py
│   ├── inspection_engine.py
│   ├── label_parsers.py
│   ├── excel_exporter.py
│   └── settings_manager.py
└── ui/                     # 界面组件
    ├── main_window.py
    ├── image_canvas.py
    ├── control_panel.py
    ├── file_list_widget.py
    └── ...
```

## 日志排查

运行后会在项目目录下生成 `logs/` 文件夹：
- `logs/app.log` —— UI 操作日志
- `logs/api_calls.log` —— API 请求与响应日志

## 技术栈

- PyQt5
- Pillow
- requests
- openpyxl
