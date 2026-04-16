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
  - **流式响应**：默认开启，支持推理模型（如 o1/o3/gpt-5.x），可通过面板开关关闭
  - **推理模型兼容**：自动解析 `reasoning_content`，仅返回最终结论，推理过程记录在日志中

- **模型管理**
  - 根据当前 API 模式（云端/本地）从对应端点自动拉取可用模型列表
  - 模型列表本地缓存（`models_cache.json`），离线时可加载上次缓存
  - 支持手动输入自定义模型名，自动记忆并持久化
  - 云端模式拉取失败时自动降级到内置备选模型列表

- **扩展与预览**
  - 支持中心、上、下、左、右多方向扩展矩形框
  - 实时预览扩展后的虚线框范围

- **结果保存**
  - 保存单张或全量带标签的结果图片
  - 导出 Excel 表格（含框坐标、扩展后坐标、复判结果、渲染缩略图）

- **提示词增强**
  - 系统提示词和用户提示词支持 Markdown 导入、导出和实时预览

- **画布操作**
  - 鼠标滚轮缩放
  - 中键拖拽平移（任何缩放级别、任何模式下均可用）
  - 左键拖拽绘制检测框（绘制模式）

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

首次启动会自动生成 `settings.json` 配置文件。

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
│   ├── llm_client.py       # 支持流式/非流式、推理模型兼容
│   ├── inspection_engine.py
│   ├── label_parsers.py
│   ├── excel_exporter.py
│   ├── model_fetcher.py    # 通用模型拉取 + JSON 缓存
│   └── settings_manager.py
└── ui/                     # 界面组件
    ├── main_window.py
    ├── image_canvas.py     # 支持中键平移
    ├── control_panel.py    # 含流式开关
    ├── model_selector.py   # 模式感知刷新 + 自定义模型记忆
    ├── file_list_widget.py
    └── ...
```

## 日志排查

运行后会在项目目录下生成 `logs/` 文件夹：
- `logs/app.log` —— UI 操作日志
- `logs/api_calls.log` —— API 请求与响应日志，包括：
  - `[API PROMPTS]` —— 发送给模型的提示词
  - `[STREAM CONTENT]` / `[API CONTENT]` —— 模型返回的完整内容
  - `[STREAM REASONING]` / `[API REASONING]` —— 推理模型的推理过程
  - `[API RAW RESPONSE]` —— 非流式模式下的原始响应体

## 技术栈

- PyQt5
- Pillow
- requests
- openpyxl
