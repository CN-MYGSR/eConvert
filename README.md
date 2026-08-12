# eConvert 🎛️

一个 UWP / Fluent 风格的本地文件格式转换工具，基于 **PyQt6**，无需联网，批量转换。

| PDF 转 Word | 音频 | 图片 | 视频 |
|---|---|---|---|
| pdf2docx（保留排版/表格/图片，逐页进度） | pydub + FFmpeg | Pillow | MoviePy + FFmpeg |

## ✨ 功能特性

- **UWP 风格界面**：无边框圆角窗口、可拖拽/边缘缩放、左侧导航、拖放批量添加文件
- **毛玻璃（液态玻璃）**：Windows 11 原生背景模糊（Win10 回退亚克力效果）
- **深色模式**：即时切换，无需重启
- **PDF 转 Word**：逐页进度显示，扫描件自动回退处理
- **音频转换**：MP3 / WAV / FLAC / OGG / M4A / OPUS，支持从视频中提取音频
- **图片转换**：PNG / JPG / WebP / GIF / BMP / TIFF / ICO，自动 EXIF 方向修正、透明底合成
- **视频转换**：MP4 / MKV / MOV / AVI / WEBM / GIF
- **详细设置**（自动保存到 `settings.json`）：
  - 视频：恒定质量 CRF 1~22、分辨率 360p~4K、帧率 24~90fps、编码 H.264 / H.265 / AV1
  - 音频：音量 1%~150%（>100% 时提示听力健康警告）、采样率 8000Hz~384kHz
  - 图片：压缩率 1%~100%
- **后台线程转换**：界面不卡顿，进度条 + 实时状态，可随时取消

## 📦 环境要求

- Windows 10 / 11（毛玻璃效果需 Windows 11）
- Python 3.10+
- FFmpeg（见下方说明）

## 🚀 快速开始

```bash
pip install -r requirements.txt

# 源码运行（两种方式均可）
python script\main.py
python assets\main.py
```

`assets\` 目录是自包含的分发目录：主程序 + 依赖清单 + FFmpeg 运行时，可整体拷贝到其他电脑直接使用。

## 🔧 FFmpeg 配置

本项目使用 **BtbN/ffmpeg-builds** 的 `ffmpeg-master-latest-win64-gpl` 版本（包含 H.265 / AV1 / VP9 编码器）。

### 方式一：直接下载现成包

从 [GitHub Releases](https://github.com/CN-MYGSR/eConvert/releases) 下载 **eConvert-ffmpeg-win64.zip**，
解压后把 `ffmpeg-master-latest-win64-gpl` 整个文件夹放到：

```
assets\
└── ffmpeg-master-latest-win64-gpl\
    └── bin\
        ├── ffmpeg.exe
        ├── ffprobe.exe
        └── ffplay.exe
```

### 方式二：自行下载 FFmpeg

1. 前往 [BtbN/ffmpeg-builds releases](https://github.com/BtbN/FFmpeg-Builds/releases)
2. 下载 `ffmpeg-master-latest-win64-gpl.zip`
3. 解压后按上述目录结构放入 `assets\`，或通过环境变量指定路径：

```powershell
$env:ECONVERT_FFMPEG = "D:\tools\ffmpeg\bin\ffmpeg.exe"
```

应用启动时按以下顺序自动探测 FFmpeg：

1. `ECONVERT_FFMPEG` 环境变量（最高优先级）
2. `assets\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe`（随应用分发）
3. `assets\ffmpeg\bin\ffmpeg.exe`
4. 系统 `PATH` 中的 `ffmpeg`

窗口左下角状态点显示 FFmpeg 是否就绪。

## ⚙️ 转换设置

| 分区 | 选项 |
|---|---|
| 常规 | 毛玻璃效果开关、深色模式开关 |
| 视频 | 恒定质量 CRF 1~22（越小画质越好）、分辨率 360p~4K、帧率 24~90fps、编码 H.264/H.265/AV1（WebM 容器自动回退 VP9） |
| 音频 | 音量 1%~150%（超过 100% 提示"过高音量会损伤听力"）、采样率 8000Hz~384000Hz |
| 图片 | 压缩率 1%~100%（影响 JPEG/WebP 质量与 PNG 压缩级别） |
| PDF 文档 | 固定输出 Word，暂无参数 |

设置自动保存于 `settings.json`（已在 `.gitignore` 中排除）。

## 📦 打包为可执行文件

仓库附带 `main.spec`（PyInstaller）：

```bash
pip install pyinstaller
pyinstaller main.spec
```

打包后可执行文件位于 `dist\main\`，把 `assets\` 目录放在 exe 同级即可。

## 🛠️ 技术栈

- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) — GUI
- [pdf2docx](https://github.com/dothinking/pdf2docx) — PDF → Word
- [pydub](https://github.com/jiaaro/pydub) + FFmpeg — 音频
- [Pillow](https://python-pillow.org/) — 图片
- [MoviePy](https://zulko.github.io/moviepy/) + FFmpeg — 视频

## 📄 开源协议

[GPLv3](LICENSE)

本项目基于以下同样采用 GPL 兼容许可的组件：

- **PyQt6** — GPLv3（Qt 的 GPL 组件）
- **FFmpeg** — GPLv2+（GitHub Release 附带的 `win64-gpl` 构建）
- **pdf2docx / pydub / MoviePy / Pillow** — MIT / LGPL 兼容许可

因此本项目整体以 **GPLv3** 发布：修改、分发或商用本软件时，需以相同许可（或兼容许可）开源其修改版本。