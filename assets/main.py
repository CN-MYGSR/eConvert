"""eConvert - UWP 风格文件格式转换工具 (PyQt6): PDF 转 Word / 音频 / 图片 / 视频"""

import json
import math
import os
import shutil
import sys
import threading
import traceback
from pathlib import Path

_BASE = Path(__file__).resolve().parent


def _app_root():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return _BASE.parent if (_BASE.parent / "assets").is_dir() else _BASE


_FFMPEG_CANDIDATES = [
    _app_root() / "assets" / "ffmpeg-master-latest-win64-gpl" / "bin" / "ffmpeg.exe",
    _BASE / "assets" / "ffmpeg-master-latest-win64-gpl" / "bin" / "ffmpeg.exe",
    _BASE / "assets" / "ffmpeg" / "bin" / "ffmpeg.exe",
    Path(r"C:\DevTools\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe"),
]


def _find_ffmpeg():
    override = os.environ.get("ECONVERT_FFMPEG")
    if override:
        p = Path(override)
        if p.is_file():
            return p
    for cand in _FFMPEG_CANDIDATES:
        if cand.is_file():
            return cand
    which = shutil.which("ffmpeg")
    if which:
        return Path(which)
    return _FFMPEG_CANDIDATES[0]


FFMPEG_PATH = str(_find_ffmpeg())
FFPROBE_PATH = os.path.join(os.path.dirname(FFMPEG_PATH), "ffprobe.exe")
FFMPEG_READY = os.path.isfile(FFMPEG_PATH)

if FFMPEG_READY:
    os.environ["FFMPEG_BINARY"] = FFMPEG_PATH
    ffmpeg_dir = os.path.dirname(FFMPEG_PATH)
    if ffmpeg_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
    from pydub import AudioSegment
    AudioSegment.converter = FFMPEG_PATH
    AudioSegment.ffprobe = FFPROBE_PATH

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QRect, QUrl, QTimer
from PyQt6.QtGui import (
    QFont, QIcon, QPixmap, QPainter, QColor, QDesktopServices,
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QListWidget, QListWidgetItem, QComboBox, QLineEdit,
    QFileDialog, QProgressBar, QFrame, QStackedWidget, QToolButton, QMessageBox,
    QGraphicsDropShadowEffect, QButtonGroup, QAbstractItemView,
    QCheckBox, QSlider, QScrollArea,
)

if FFMPEG_READY:
    from moviepy import VideoFileClip

ACCENT = "#0078D4"
TITLE_H = 40
EDGE = 6
MIN_W, MIN_H = 940, 620

THEMES = {
    "light": {
        "window_bg": "#F3F3F3",
        "window_acrylic_bg": "rgba(247, 247, 249, 200)",
        "border": "#E3E5E8",
        "sidebar": "#FFFFFF",
        "card": "#FFFFFF",
        "card_border": "#E6E8EB",
        "title_text": "#1F2430",
        "text": "#2B3040",
        "text_sec": "#6F767D",
        "text_faint": "#8A919A",
        "field_text": "#23272E",
        "field_bg": "#FFFFFF",
        "field_border": "#D9DCDF",
        "field_border_hover": "#A8ADB4",
        "drop_bg": "#FAFBFC",
        "drop_border": "#C6CCD3",
        "drop_hover": "#F0F7FD",
        "list_hover": "rgba(0, 0, 0, 0.045)",
        "track": "#E2E4E8",
        "ghost_hover": "rgba(0, 0, 0, 0.06)",
        "winbtn": "#4A4F57",
        "winbtn_hover": "rgba(0, 0, 0, 0.08)",
        "scroll": "#C9CDD3",
        "scroll_hover": "#B3B8BF",
        "switch_knob": "#FFFFFF",
        "switch_knob_hover": "#EAF4FC",
        "accent": "#0078D4",
        "accent_hover": "#0F6CBD",
        "accent_pressed": "#0A5EA6",
        "accent_disabled": "#C7CFD8",
        "accent_disabled_text": "#8E96A0",
        "nav_checked_text": "#FFFFFF",
        "select_text": "#005A9E",
        "accent_soft": "rgba(0, 120, 212, 0.12)",
        "hover_soft": "rgba(0, 120, 212, 0.08)",
        "warning": "#C43E1C",
        "ok": "#0F7B0F",
    },
    "dark": {
        "window_bg": "#1F1F1F",
        "window_acrylic_bg": "rgba(26, 26, 30, 214)",
        "border": "#3A3A3A",
        "sidebar": "#262626",
        "card": "#2B2B2B",
        "card_border": "#3A3A3A",
        "title_text": "#F0F0F0",
        "text": "#E6E6E6",
        "text_sec": "#9A9FA6",
        "text_faint": "#7E848C",
        "field_text": "#E6E6E6",
        "field_bg": "#2E2E2E",
        "field_border": "#454A50",
        "field_border_hover": "#6A7078",
        "drop_bg": "#232323",
        "drop_border": "#4E545C",
        "drop_hover": "#1E2D3D",
        "list_hover": "rgba(255, 255, 255, 0.05)",
        "track": "#45484D",
        "ghost_hover": "rgba(255, 255, 255, 0.07)",
        "winbtn": "#C9CDD3",
        "winbtn_hover": "rgba(255, 255, 255, 0.08)",
        "scroll": "#555B63",
        "scroll_hover": "#6A7078",
        "switch_knob": "#F2F2F2",
        "switch_knob_hover": "#D9ECFA",
        "accent": "#4CC2FF",
        "accent_hover": "#63CDFF",
        "accent_pressed": "#3CB8F0",
        "accent_disabled": "#3A4148",
        "accent_disabled_text": "#6E767D",
        "nav_checked_text": "#101418",
        "select_text": "#A9E0FF",
        "accent_soft": "rgba(76, 194, 255, 0.16)",
        "hover_soft": "rgba(76, 194, 255, 0.10)",
        "warning": "#FF8A80",
        "ok": "#7BD88F",
    },
}


def make_qss(dark: bool, acrylic: bool) -> str:
    P = THEMES["dark" if dark else "light"]
    window_bg = P["window_acrylic_bg"] if acrylic else P["window_bg"]
    return f"""
* {{ font-family: "Segoe UI", "Microsoft YaHei UI", "Microsoft YaHei", sans-serif; }}
#Window {{ background-color: {window_bg}; border: 1px solid {P['border']}; border-radius: 12px; }}
#Window[maximized="true"] {{ border-radius: 0px; }}
#Sidebar {{ background-color: {P['sidebar']}; }}
#Brand {{ font-size: 19px; font-weight: 700; color: {P['title_text']}; }}
#BrandSub {{ font-size: 11px; color: {P['text_sec']}; }}
#NavBtn {{ border: none; border-radius: 8px; padding: 9px 14px; color: {P['text']};
          font-size: 13px; text-align: left; background: transparent; }}
#NavBtn:hover {{ background-color: {P['hover_soft']}; }}
#NavBtn:checked {{ background-color: {P['accent']}; color: {P['nav_checked_text']}; font-weight: 600; }}
#NavDanger {{ color: #9A3B2E; }}
#PageTitle {{ font-size: 22px; font-weight: 700; color: {P['title_text']}; }}
#PageSubtitle {{ font-size: 12px; color: {P['text_sec']}; }}
#Card {{ background-color: {P['card']}; border: 1px solid {P['card_border']}; border-radius: 10px; }}
#DropZone {{ background-color: {P['drop_bg']}; border: 2px dashed {P['drop_border']}; border-radius: 10px; }}
#DropZone:hover {{ border-color: {P['accent']}; background-color: {P['drop_hover']}; }}
#DropHint {{ color: #4E555E; font-size: 13px; }}
#DropSub {{ color: {P['text_faint']}; font-size: 11px; }}
#FileList {{ background: {P['field_bg']}; border: 1px solid {P['card_border']}; border-radius: 8px;
            font-size: 12px; color: {P['field_text']}; outline: none; }}
#FileList::item {{ padding: 7px 10px; border-radius: 6px; margin: 1px 5px; }}
#FileList::item:selected {{ background-color: {P['accent_soft']}; color: {P['select_text']}; }}
#FileList::item:hover {{ background-color: {P['list_hover']}; }}
#FieldLabel {{ color: {P['text_sec']}; font-size: 12px; font-weight: 600; }}
QComboBox, QLineEdit {{ background-color: {P['field_bg']}; border: 1px solid {P['field_border']};
                       border-radius: 8px; padding: 7px 10px; font-size: 13px; color: {P['field_text']}; }}
QComboBox:hover, QLineEdit:hover {{ border-color: {P['field_border_hover']}; }}
QComboBox:focus, QLineEdit:focus {{ border-color: {P['accent']}; }}
QComboBox QAbstractItemView {{ background-color: {P['field_bg']}; border: 1px solid {P['field_border']};
                              border-radius: 8px; padding: 4px; outline: none;
                              selection-background-color: {P['accent_soft']};
                              selection-color: {P['field_text']}; }}
QProgressBar {{ background-color: {P['track']}; border: none; border-radius: 4px; max-height: 8px; }}
QProgressBar::chunk {{ background-color: {P['accent']}; border-radius: 4px; }}
#Primary {{ background-color: {P['accent']}; color: {P['nav_checked_text']}; border: none;
           border-radius: 8px; padding: 10px 32px; font-size: 13px; font-weight: 600; }}
#Primary:hover {{ background-color: {P['accent_hover']}; }}
#Primary:pressed {{ background-color: {P['accent_pressed']}; }}
#Primary:disabled {{ background-color: {P['accent_disabled']}; color: {P['accent_disabled_text']}; }}
#Secondary {{ background-color: {P['field_bg']}; color: {P['text']}; border: 1px solid {P['field_border']};
             border-radius: 8px; padding: 8px 16px; font-size: 12px; }}
#Secondary:hover {{ background-color: {P['drop_hover']}; border-color: {P['accent']}; }}
#Secondary:pressed {{ background-color: {P['accent_soft']}; }}
#Ghost {{ background: transparent; color: {P['text_sec']}; border: none; border-radius: 6px;
         padding: 6px 10px; font-size: 12px; }}
#Ghost:hover {{ background-color: {P['ghost_hover']}; }}
QPushButton#WinBtn {{ border: none; border-radius: 6px; background: transparent;
                     color: {P['winbtn']}; font-size: 13px; font-weight: 600; }}
QPushButton#WinBtn:hover {{ background-color: {P['winbtn_hover']}; }}
QPushButton#WinBtnClose {{ border: none; border-radius: 6px; background: transparent;
                          color: {P['winbtn']}; font-size: 13px; font-weight: 600; }}
QPushButton#WinBtnClose:hover {{ background-color: #E81123; color: #FFFFFF; }}
QToolTip {{ background: {P['card']}; color: {P['field_text']}; border: 1px solid {P['field_border']};
           padding: 4px 8px; font-size: 12px; }}
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {P['scroll']}; border-radius: 4px; min-height: 24px; }}
QScrollBar::handle:vertical:hover {{ background: {P['scroll_hover']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
#SectionTitle {{ font-size: 14px; font-weight: 600; color: {P['text']}; }}
#RowTitle {{ font-size: 13px; color: {P['title_text']}; }}
#RowDesc {{ font-size: 11px; color: {P['text_faint']}; }}
#SliderVal {{ font-size: 12px; color: {P['text']}; font-weight: 600; }}
QCheckBox#Switch {{ spacing: 10px; }}
QCheckBox#Switch::indicator {{ width: 40px; height: 20px; border-radius: 10px;
    background: {P['track']}; border: 1px solid {P['field_border_hover']}; }}
QCheckBox#Switch::indicator:hover {{ border-color: {P['accent']}; }}
QCheckBox#Switch::indicator:checked {{ background: {P['accent']}; border-color: {P['accent']}; }}
QSlider#Slider {{ min-height: 24px; }}
QSlider#Slider::groove:horizontal {{ height: 4px; background: {P['track']}; border-radius: 2px; }}
QSlider#Slider::sub-page:horizontal {{ background: {P['accent']}; border-radius: 2px; }}
QSlider#Slider::handle:horizontal {{ width: 16px; height: 16px; margin: -6px 0;
    border-radius: 8px; background: {P['switch_knob']}; border: 1px solid {P['accent']}; }}
QSlider#Slider::handle:horizontal:hover {{ background: {P['switch_knob_hover']}; }}
QScrollArea#SettingsScroll {{ background: transparent; border: none; }}
QScrollArea#SettingsScroll > QWidget > QWidget {{ background: transparent; }}
"""

DEFAULT_SETTINGS = {
    "acrylic": True,
    "dark": False,
    "video_crf": 18,
    "video_height": 0,
    "video_fps": 30,
    "video_codec": "h264",
    "audio_volume": 100,
    "audio_rate": 44100,
    "image_quality": 90,
}

SETTINGS_FILE = _BASE / "settings.json"


def load_settings():
    stored = {}
    try:
        stored = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    merged = dict(DEFAULT_SETTINGS)
    merged.update({k: v for k, v in stored.items() if k in DEFAULT_SETTINGS})
    return merged


def save_settings(settings):
    try:
        SETTINGS_FILE.write_text(
            json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def set_acrylic_windows(hwnd: int, acrylic_on: bool, dark: bool):
    if sys.platform != "win32":
        return
    try:
        import ctypes
        from ctypes import wintypes
        value = ctypes.c_int(3 if acrylic_on else 0)
        result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
            wintypes.HWND(hwnd), 38, ctypes.byref(value), ctypes.sizeof(value))
        if result == 0:
            return
    except Exception:
        pass
    try:
        import ctypes

        class ACCENT_POLICY(ctypes.Structure):
            _fields_ = [("AccentState", ctypes.c_uint),
                        ("AccentFlags", ctypes.c_uint),
                        ("GradientColor", ctypes.c_uint),
                        ("AnimationId", ctypes.c_uint)]

        class WCA_DATA(ctypes.Structure):
            _fields_ = [("Attribute", ctypes.c_int),
                        ("Data", ctypes.c_void_p),
                        ("SizeOfData", ctypes.c_size_t)]

        tint = 0xCC000000 if dark else 0xD9FFFFFF
        accent = ACCENT_POLICY(4 if acrylic_on else 0, 0, tint, 0)
        data = WCA_DATA(19, ctypes.cast(ctypes.pointer(accent), ctypes.c_void_p),
                        ctypes.sizeof(accent))
        ctypes.windll.user32.SetWindowCompositionAttribute(hwnd, ctypes.byref(data))
    except Exception:
        pass


class CancelledError(Exception):
    pass


def fmt_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def unique_path(path: Path) -> Path:
    path = Path(path)
    if not path.exists():
        return path
    for i in range(1, 10000):
        cand = path.with_name(f"{path.stem} ({i}){path.suffix}")
        if not cand.exists():
            return cand
    return path.with_name(f"{path.stem} ({id(path)}){path.suffix}")


def pdf_to_word(pdf_path: Path, docx_path: Path, on_page=None, cancel=None):
    from pdf2docx import Converter
    cv = Converter(str(pdf_path))
    try:
        try:
            from docx import Document
            cv.parse(start=0, end=None)
            pages = [p for p in cv._pages if p.finalized]
            if pages:
                doc = Document()
                for idx, page in enumerate(pages, 1):
                    if cancel is not None and cancel.is_set():
                        raise CancelledError()
                    page.make_docx(doc)
                    if on_page:
                        on_page(idx, len(pages))
                doc.save(str(docx_path))
                return
        except CancelledError:
            raise
        except Exception:
            pass
        if docx_path.exists():
            docx_path.unlink(missing_ok=True)
        cv.convert(str(docx_path))
    finally:
        cv.close()


AUDIO_TARGETS = {
    "MP3":  {"ext": "mp3",  "format": "mp3",  "codec": "libmp3lame"},
    "WAV":  {"ext": "wav",  "format": "wav",  "codec": "pcm_s16le"},
    "FLAC": {"ext": "flac", "format": "flac", "codec": "flac"},
    "OGG":  {"ext": "ogg",  "format": "ogg",  "codec": "libvorbis"},
    "M4A":  {"ext": "m4a",  "format": "ipod", "codec": "aac"},
    "OPUS": {"ext": "opus", "format": "opus", "codec": "libopus"},
}
AUDIO_EXTENSIONS = {"mp3", "wav", "flac", "ogg", "m4a", "aac", "opus", "wma",
                    "aiff", "aif", "amr", "mka", "mp2", "m4b"}


def convert_audio(src: Path, dst: Path, target: str, a_cfg=None):
    from pydub import AudioSegment
    a_cfg = a_cfg or {}
    cfg = AUDIO_TARGETS[target]
    seg = AudioSegment.from_file(str(src))
    volume = int(a_cfg.get("volume", 100) or 100)
    rate = int(a_cfg.get("rate", 0) or 0)
    if volume != 100:
        seg = seg.apply_gain(20.0 * math.log10(max(volume, 1) / 100.0))
    if rate:
        seg = seg.set_frame_rate(rate)
    seg.export(str(dst), format=cfg["format"], codec=cfg["codec"])


def to_rgb_with_alpha(im):
    bg = im.convert("RGB")
    rgb = im.convert("RGBA")
    alpha = rgb.split()[-1]
    bg.paste(rgb, mask=alpha)
    return bg


def convert_image(src: Path, dst: Path, target: str, quality=None):
    from PIL import Image, ImageOps
    fmt = target.upper()
    q = int(quality) if quality is not None else 90
    q = min(max(q, 1), 100)
    with Image.open(str(src)) as im:
        im = ImageOps.exif_transpose(im)
        if fmt == "JPG":
            if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
                im = to_rgb_with_alpha(im)
            elif im.mode != "RGB":
                im = im.convert("RGB")
            im.save(str(dst), format="JPEG", quality=q, subsampling=1, optimize=True)
        elif fmt == "WEBP":
            im.save(str(dst), format="WEBP", quality=q, method=6)
        elif fmt == "PNG":
            im.save(str(dst), format="PNG",
                    compress_level=round(q / 100.0 * 9), optimize=True)
        elif fmt == "ICO":
            im.save(str(dst), format="ICO",
                    sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
        else:
            im.save(str(dst), format=fmt)


VIDEO_TARGETS = {
    "MP4":  {"ext": "mp4",  "codec": "libx264", "audio_codec": "aac"},
    "MKV":  {"ext": "mkv",  "codec": "libx264", "audio_codec": "aac"},
    "MOV":  {"ext": "mov",  "codec": "libx264", "audio_codec": "aac"},
    "AVI":  {"ext": "avi",  "codec": "libx264", "audio_codec": "mp3"},
    "WEBM": {"ext": "webm", "codec": "libvpx",  "audio_codec": "libvorbis"},
    "GIF":  {"ext": "gif",  "codec": None,      "audio_codec": None},
}

VIDEO_CODECS = {
    "h264": "libx264",
    "h265": "libx265",
    "av1": "libsvtav1",
}


def convert_video(src: Path, dst: Path, target: str, v_cfg=None):
    v_cfg = v_cfg or {}
    clip = VideoFileClip(str(src))
    try:
        if target == "GIF":
            fps = int(v_cfg.get("fps", 15) or 15)
            clip.write_gif(str(dst), fps=min(max(fps, 5), 30))
            return
        cfg = VIDEO_TARGETS[target]
        has_audio = clip.audio is not None

        height = int(v_cfg.get("height", 0) or 0)
        if height and abs(int(clip.size[1]) - height) > 1:
            clip = clip.resized(height=height)

        codec_name = VIDEO_CODECS.get(str(v_cfg.get("codec", "h264")), "libx264")
        if target == "WEBM" and codec_name in ("libx264", "libx265"):
            codec_name = "libvpx-vp9"

        crf = int(v_cfg.get("crf", 18) or 18)
        fps = int(v_cfg.get("fps", 30) or 30)
        preset = "6" if codec_name == "libsvtav1" else "medium"
        ff_params = ["-crf", str(crf)]

        volume = int(v_cfg.get("volume", 100) or 100)
        rate = int(v_cfg.get("rate", 0) or 0)
        temp_audio = None
        audio_clip = clip
        if has_audio and (volume != 100 or rate):
            from pydub import AudioSegment
            from moviepy import AudioFileClip
            seg = AudioSegment.from_file(str(src))
            if volume != 100:
                seg = seg.apply_gain(20.0 * math.log10(max(volume, 1) / 100.0))
            if rate:
                seg = seg.set_frame_rate(rate)
            temp_audio = dst.with_name(f"{dst.stem}_tmp_audio.wav")
            seg.export(str(temp_audio), format="wav")
            audio_clip = AudioFileClip(str(temp_audio))
            clip = clip.with_audio(audio_clip)

        try:
            clip.write_videofile(
                str(dst),
                fps=fps,
                codec=codec_name,
                audio=has_audio,
                audio_codec=cfg["audio_codec"] if has_audio else None,
                preset=preset,
                ffmpeg_params=ff_params,
                logger=None,
            )
        finally:
            if temp_audio:
                try:
                    audio_clip.close()
                except Exception:
                    pass
                temp_audio.unlink(missing_ok=True)
    finally:
        try:
            clip.close()
        except Exception:
            pass


class ConvertWorker(QThread):
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    done = pyqtSignal(int, int, list, bool)

    def __init__(self, mode, files, target, outdir, cfg=None, parent=None):
        super().__init__(parent)
        self.mode = mode
        self.files = files
        self.target = target
        self.outdir = outdir
        self.cfg = cfg or {}
        self._cancel = threading.Event()

    def cancel(self):
        self._cancel.set()

    def run(self):
        total = len(self.files)
        ok = fail = 0
        errors = []
        cancelled = False
        for i, src in enumerate(self.files, 1):
            if self._cancel.is_set():
                cancelled = True
                break
            base = (self.outdir or src.parent)
            dst = unique_path(base / f"{src.stem}.{self.target.lower()}")
            self.status.emit(f"正在转换 ({i}/{total}): {src.name}")
            try:
                if self.mode == "pdf":
                    def on_page(done_pages, total_pages):
                        self.status.emit(
                            f"正在转换 ({i}/{total}): {src.name}  ·  页码 {done_pages}/{total_pages}")
                    pdf_to_word(src, dst, on_page=on_page, cancel=self._cancel)
                elif self.mode == "audio":
                    convert_audio(src, dst, self.target, self.cfg.get("audio"))
                elif self.mode == "image":
                    convert_image(src, dst, self.target,
                                  (self.cfg.get("image") or {}).get("quality"))
                else:
                    convert_video(src, dst, self.target, self.cfg.get("video"))
                ok += 1
            except CancelledError:
                cancelled = True
                dst.unlink(missing_ok=True)
                break
            except Exception as exc:
                fail += 1
                errors.append(f"{src.name}: {exc}")
            self.progress.emit(int(i / total * 100))
        self.done.emit(ok, fail, errors, cancelled)


class DropZone(QFrame):
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DropZone")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(2)
        hint = QLabel("将文件拖拽到此处，或点击选择文件")
        hint.setObjectName("DropHint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub = QLabel("支持批量选择，重复文件自动去重")
        sub.setObjectName("DropSub")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(hint)
        lay.addWidget(sub)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(e)


def attach_drop(widget, on_files):
    widget.setAcceptDrops(True)

    def drag_enter(e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def drop(e):
        paths = []
        for url in e.mimeData().urls():
            if url.isLocalFile():
                paths.append(Path(url.toLocalFile()))
        on_files(paths)
        e.acceptProposedAction()

    widget.dragEnterEvent = drag_enter
    widget.dropEvent = drop


class ConvertPage(QWidget):
    def __init__(self, window, mode, title, subtitle, extensions, target_spec,
                 parent=None):
        super().__init__(parent)
        self.window = window
        self.mode = mode
        self.extensions = set(extensions)
        self._targets = target_spec
        self._files = []
        self._outdir = None
        self._build_ui(title, subtitle)
        attach_drop(self._drop_zone, self.add_files)
        attach_drop(self._list, self.add_files)
        self._drop_zone.clicked.connect(self.choose_files)

    def _build_ui(self, title, subtitle):
        root = QVBoxLayout(self)
        root.setContentsMargins(26, 22, 26, 22)
        root.setSpacing(14)

        title_label = QLabel(title)
        title_label.setObjectName("PageTitle")
        sub_label = QLabel(subtitle)
        sub_label.setObjectName("PageSubtitle")
        root.addWidget(title_label)
        root.addWidget(sub_label)

        file_card = QFrame()
        file_card.setObjectName("Card")
        fcl = QVBoxLayout(file_card)
        fcl.setContentsMargins(14, 14, 14, 12)
        fcl.setSpacing(10)

        self._drop_zone = DropZone()
        fcl.addWidget(self._drop_zone)

        self._list = QListWidget()
        self._list.setObjectName("FileList")
        self._list.setMinimumHeight(150)
        self._list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        fcl.addWidget(self._list, 1)

        row = QHBoxLayout()
        row.setSpacing(6)
        self._count_label = QLabel("共 0 个文件")
        self._count_label.setObjectName("FieldLabel")
        remove_btn = QPushButton("移除选中")
        remove_btn.setObjectName("Ghost")
        clear_btn = QPushButton("清空列表")
        clear_btn.setObjectName("Ghost")
        remove_btn.clicked.connect(self.remove_selected)
        clear_btn.clicked.connect(self.clear_files)
        row.addWidget(self._count_label)
        row.addStretch(1)
        row.addWidget(remove_btn)
        row.addWidget(clear_btn)
        fcl.addLayout(row)
        root.addWidget(file_card)

        opt_card = QFrame()
        opt_card.setObjectName("Card")
        ol = QVBoxLayout(opt_card)
        ol.setContentsMargins(14, 12, 14, 12)
        ol.setSpacing(10)

        target_row = QHBoxLayout()
        target_row.setSpacing(8)
        tlabel = QLabel("目标格式")
        tlabel.setObjectName("FieldLabel")
        tlabel.setFixedWidth(66)
        target_row.addWidget(tlabel)
        if self.mode == "pdf":
            fixed = QLabel("DOCX  (Word 文档)")
            fixed.setStyleSheet("font-size:13px; color:#23272E; padding:7px 4px;")
            self._target_combo = None
            target_row.addWidget(fixed)
        else:
            self._target_combo = QComboBox()
            self._target_combo.setMinimumWidth(220)
            for name, spec in self._targets.items():
                self._target_combo.addItem(f"{name}  (.{spec['ext']})", name)
            target_row.addWidget(self._target_combo)
        target_row.addStretch(1)
        if self.mode == "pdf":
            pdf_note = QLabel("固定输出为 Word 文档")
            pdf_note.setObjectName("DropSub")
            target_row.addWidget(pdf_note)
        else:
            src_note = QLabel("常见格式均可直接拖入，自动识别")
            src_note.setObjectName("DropSub")
            target_row.addWidget(src_note)
        ol.addLayout(target_row)

        out_row = QHBoxLayout()
        out_row.setSpacing(8)
        olabel = QLabel("输出目录")
        olabel.setObjectName("FieldLabel")
        olabel.setFixedWidth(66)
        self._out_edit = QLineEdit()
        self._out_edit.setPlaceholderText("留空：输出到源文件所在目录")
        browse_btn = QPushButton("浏览…")
        browse_btn.setObjectName("Secondary")
        browse_btn.clicked.connect(self.choose_output_dir)
        out_row.addWidget(olabel)
        out_row.addWidget(self._out_edit, 1)
        out_row.addWidget(browse_btn)
        ol.addLayout(out_row)
        root.addWidget(opt_card)

        action_row = QHBoxLayout()
        action_row.setSpacing(10)
        self._cancel_btn = QPushButton("取消")
        self._cancel_btn.setObjectName("Secondary")
        self._cancel_btn.hide()
        self._cancel_btn.clicked.connect(self.window.cancel_conversion)
        self._convert_btn = QPushButton("开始转换")
        self._convert_btn.setObjectName("Primary")
        self._convert_btn.setMinimumWidth(150)
        self._convert_btn.clicked.connect(
            lambda _=False: self.window.start_conversion(self))
        action_row.addWidget(self._cancel_btn)
        action_row.addWidget(self._convert_btn)
        action_row.addStretch(1)
        root.addLayout(action_row)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._percent = QLabel("0%")
        self._percent.setObjectName("FieldLabel")
        progress_row = QHBoxLayout()
        progress_row.setSpacing(10)
        progress_row.addWidget(self._progress, 1)
        progress_row.addWidget(self._percent)
        root.addLayout(progress_row)

        self._status_label = QLabel("就绪 · 将文件拖入上方区域")
        self._status_label.setStyleSheet("font-size:12px; color:#5F6670;")
        self._open_btn = QPushButton("打开输出目录")
        self._open_btn.setObjectName("Ghost")
        self._open_btn.hide()
        self._open_btn.clicked.connect(self.open_output_dir)
        status_row = QHBoxLayout()
        status_row.setSpacing(10)
        status_row.addWidget(self._status_label, 1)
        status_row.addWidget(self._open_btn)
        root.addLayout(status_row)

    def targets(self):
        return self._targets

    def files(self):
        return list(self._files)

    def target(self):
        if self.mode == "pdf":
            return "docx"
        return self._target_combo.currentData()

    def output_dir(self):
        text = self._out_edit.text().strip()
        if text:
            p = Path(text)
            if p.exists() and p.is_dir():
                return p
        return None

    def choose_files(self):
        if self.mode == "pdf":
            filt = "PDF 文档 (*.pdf)"
        elif self.mode == "audio":
            filt = ("音频文件 (*.mp3 *.wav *.flac *.ogg *.m4a *.aac *.opus *.wma "
                    "*.aiff *.amr);;所有文件 (*.*)")
        elif self.mode == "image":
            filt = ("图片文件 (*.png *.jpg *.jpeg *.bmp *.webp *.gif *.tiff *.tif "
                    "*.ico *.jfif);;所有文件 (*.*)")
        else:
            filt = ("视频文件 (*.mp4 *.avi *.mkv *.mov *.webm *.flv *.wmv *.m4v "
                    "*.ts *.mpg *.mpeg);;所有文件 (*.*)")
        paths, _ = QFileDialog.getOpenFileNames(self, "选择文件", "", filt)
        self.add_files([Path(p) for p in paths])

    def choose_output_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择输出目录",
                                             self._out_edit.text().strip() or "")
        if d:
            self._out_edit.setText(d)

    def add_files(self, paths):
        added = 0
        seen = {str(p) for p in self._files}
        for raw in paths:
            p = Path(raw)
            if not p.is_file():
                continue
            ext = p.suffix.lower().lstrip(".")
            if ext not in self.extensions:
                continue
            key = str(p)
            if key in seen:
                continue
            seen.add(key)
            self._files.append(p)
            item = QListWidgetItem(f"{p.name}    ·    {fmt_size(p.stat().st_size)}  ·  {p.parent}")
            item.setData(Qt.ItemDataRole.UserRole, key)
            self._list.addItem(item)
            added += 1
        if added:
            self.refresh_count()

    def remove_selected(self):
        rows = self._list.selectionModel().selectedRows()
        if not rows:
            return
        routes = set()
        for idx in reversed(sorted(r.index().row() for r in rows)):
            item = self._list.takeItem(idx)
            routes.add(item.data(Qt.ItemDataRole.UserRole))
        self._files = [f for f in self._files if str(f) not in routes]
        self.refresh_count()

    def clear_files(self):
        self._list.clear()
        self._files.clear()
        self.refresh_count()
        self.set_status("就绪 · 将文件拖入上方区域", grey=True)

    def refresh_count(self):
        self._count_label.setText(f"共 {len(self._files)} 个文件")
        self._convert_btn.setEnabled(bool(self._files))

    def set_running(self, running: bool):
        self._convert_btn.setEnabled(not running and bool(self._files))
        self._cancel_btn.setVisible(running)
        self._drop_zone.setEnabled(not running)
        self._list.setEnabled(not running)
        if not running:
            self._open_btn.hide()

    def on_progress(self, value: int):
        self._progress.setValue(value)
        self._percent.setText(f"{value}%")

    def set_status(self, text: str, grey=False, ok=False):
        if grey:
            color = "#5F6670"
        elif ok:
            color = "#0F7B0F"
        else:
            color = "#C43E1C"
        self._status_label.setText(text)
        self._status_label.setStyleSheet(f"font-size:12px; color:{color};")

    def open_output_dir(self):
        if self._outdir:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._outdir)))

    def show_finish(self, ok_count, fail_count, errors, cancelled):
        self._outdir = None
        if self._files:
            base = self.output_dir() or self._files[0].parent
            self._outdir = base if base.exists() else self._files[0].parent
        if cancelled:
            self.set_status(f"已取消 · 成功 {ok_count} 个，失败 {fail_count} 个", grey=True)
        elif fail_count == 0:
            self.set_status(f"转换完成 · 成功 {ok_count} 个文件", ok=True)
        elif ok_count == 0:
            self.set_status(f"转换失败 · {fail_count} 个文件未能转换", grey=False)
        else:
            self.set_status(f"转换完成 · 成功 {ok_count} 个，失败 {fail_count} 个")
        if not cancelled and (ok_count or self._outdir):
            self._open_btn.show()
        if errors:
            head = "\n".join(errors[:8])
            if len(errors) > 8:
                head += f"\n… 其余 {len(errors) - 8} 个错误未列出"
            QMessageBox.warning(self, "部分文件转换失败", head)


class SettingsPage(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self._build_ui()
        self._sync_from_settings()

    def _set(self, key, value, refresh_ui=False):
        self.window.settings[key] = value
        save_settings(self.window.settings)
        if refresh_ui:
            self.window.apply_appearance()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(26, 22, 26, 22)
        root.setSpacing(14)

        title = QLabel("设置")
        title.setObjectName("PageTitle")
        sub = QLabel("外观即时生效，转换参数将应用到后续所有转换任务")
        sub.setObjectName("PageSubtitle")
        root.addWidget(title)
        root.addWidget(sub)

        scroll = QScrollArea()
        scroll.setObjectName("SettingsScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(0, 0, 8, 8)
        cl.setSpacing(10)
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        self._cl = cl

    def _section(self, text):
        lab = QLabel(text)
        lab.setObjectName("SectionTitle")
        self._cl.addWidget(lab)

    def _card(self):
        card = QFrame()
        card.setObjectName("Card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(10)
        self._cl.addWidget(card)
        return card, lay

    def _row(self, lay, title, desc, control):
        row = QHBoxLayout()
        row.setSpacing(24)
        text_box = QVBoxLayout()
        text_box.setSpacing(2)
        t = QLabel(title)
        t.setObjectName("RowTitle")
        d = QLabel(desc)
        d.setObjectName("RowDesc")
        d.setWordWrap(True)
        text_box.addWidget(t)
        text_box.addWidget(d)
        row.addLayout(text_box, 1)
        row.addWidget(control, 0, Qt.AlignmentFlag.AlignVCenter)
        lay.addLayout(row)

    def _slider(self, lo, hi, value, suffix="", on_change=None):
        wrap = QWidget()
        box = QHBoxLayout(wrap)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(10)
        slider = SliderBox(lo, hi, value)
        val = QLabel(f"{value}{suffix}")
        val.setObjectName("SliderVal")
        val.setFixedWidth(52)
        val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        box.addWidget(slider, 1)
        box.addWidget(val)
        slider.valueChanged.connect(
            lambda v: (val.setText(f"{v}{suffix}"), on_change(v) if on_change else None))
        return wrap

    def _sync_from_settings(self):
        s = self.window.settings
        self._section("常规")
        card, lay = self._card()
        self._acrylic_switch = self._make_switch(s["acrylic"],
                                                 lambda on: self._set("acrylic", on, True))
        self._row(lay, "毛玻璃（液态玻璃）效果",
                  "启用 Windows 原生背景模糊，带来通透的玻璃质感", self._acrylic_switch)
        self._dark_switch = self._make_switch(s["dark"],
                                              lambda on: self._set("dark", on, True))
        self._row(lay, "深色模式", "使用深色主题，夜间使用更舒适", self._dark_switch)

        self._section("视频")
        card, lay = self._card()
        self._crf_slider = self._slider(
            1, 22, s["video_crf"],
            on_change=lambda v: self._set("video_crf", v))
        self._row(lay, "恒定质量 (CRF)", "数值越小画质越好、文件越大（1~22）",
                  self._crf_slider)
        self._height_combo = self._make_combo(
            [("原始（不缩放）", 0), ("360p", 360), ("480p", 480), ("720p", 720),
             ("1080p", 1080), ("1440p", 1440), ("4K（2160p）", 2160)],
            s["video_height"],
            lambda v: self._set("video_height", v))
        self._row(lay, "分辨率", "按高度等比缩放输出画面（360p ~ 4K）", self._height_combo)
        self._fps_combo = self._make_combo(
            [(f"{fps}fps", fps) for fps in (24, 25, 30, 48, 60, 90)],
            s["video_fps"], lambda v: self._set("video_fps", v))
        self._row(lay, "帧率", "输出视频的每秒帧数（24fps ~ 90fps）", self._fps_combo)
        self._codec_combo = self._make_combo(
            [("H.264", "h264"), ("H.265 / HEVC", "h265"), ("AV1", "av1")],
            s["video_codec"], lambda v: self._set("video_codec", v))
        self._row(lay, "编码格式", "H.265 与 AV1 压缩效率更高，但编码更慢", self._codec_combo)

        self._section("音频")
        card, lay = self._card()
        self._volume_slider = self._slider(
            1, 150, s["audio_volume"], suffix="%",
            on_change=lambda v: (self._set("audio_volume", v),
                                 self._volume_warn.setVisible(v > 100)))
        self._row(lay, "音量", "将音频音量调整为原始音量的百分比（1%~150%）",
                  self._volume_slider)
        self._volume_warn = QLabel("过高的音量会损伤听力，请谨慎使用")
        self._volume_warn.setStyleSheet("font-size: 11px; color: #C43E1C;")
        self._volume_warn.setVisible(int(s["audio_volume"]) > 100)
        lay.addWidget(self._volume_warn)
        self._rate_combo = self._make_combo(
            [(f"{r}Hz", r) for r in (8000, 11025, 16000, 22050, 32000, 44100, 48000,
                                     88200, 96000, 176400, 192000, 384000)],
            s["audio_rate"], lambda v: self._set("audio_rate", v))
        self._row(lay, "采样率", "输出音频的采样率（8000Hz ~ 384000Hz）", self._rate_combo)

        self._section("图片")
        card, lay = self._card()
        self._quality_slider = self._slider(
            1, 100, s["image_quality"], suffix="%",
            on_change=lambda v: self._set("image_quality", v))
        self._row(lay, "压缩率", "数值越低文件越小、画质越低（JPEG/WebP/PNG 生效）",
                  self._quality_slider)

        self._section("PDF 文档")
        card, lay = self._card()
        none_lab = QLabel("PDF 转换固定输出为 Word 文档，暂无可用参数设置")
        none_lab.setObjectName("RowDesc")
        lay.addWidget(none_lab)

    def _make_switch(self, checked, on_toggled):
        sw = Switch()
        sw.setChecked(checked)
        sw.toggled.connect(on_toggled)
        return sw

    def _make_combo(self, items, current, on_changed):
        combo = QComboBox()
        combo.setMinimumWidth(190)
        for text, value in items:
            combo.addItem(text, value)
        index = combo.findData(current)
        combo.setCurrentIndex(max(index, 0))
        combo.currentIndexChanged.connect(
            lambda _i: on_changed(combo.currentData()) if combo.currentData() is not None else None)
        return combo


class Switch(QCheckBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Switch")
        self.setCursor(Qt.CursorShape.PointingHandCursor)


class SliderBox(QSlider):
    def __init__(self, lo, hi, value, parent=None):
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.setObjectName("Slider")
        self.setRange(lo, hi)
        self.setValue(value)
        self.setFixedWidth(220)
        self.setCursor(Qt.CursorShape.PointingHandCursor)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._worker = None
        self._active_page = None
        self._drag_offset = None
        self._resize_edge = 0
        self._resize_global = None
        self._resize_geo = None
        self._normal_geo = None
        self._maximized = False
        self.settings = load_settings()

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowIcon(make_app_icon())
        self.setMinimumSize(MIN_W, MIN_H)
        self.resize(1020, 680)
        self.setMouseTracking(True)
        self._build_ui()
        self._apply_chrome()

    def _build_ui(self):
        self._outer = QWidget()
        self._outer.setObjectName("Window")
        shadow = QGraphicsDropShadowEffect(self._outer)
        shadow.setBlurRadius(42)
        shadow.setOffset(0, 5)
        shadow.setColor(QColor(0, 0, 0, 62))
        self._outer.setGraphicsEffect(shadow)
        self.setCentralWidget(self._outer)

        outer_lay = QVBoxLayout(self._outer)
        self._outer_layout = outer_lay
        outer_lay.setSpacing(0)
        outer_lay.setContentsMargins(0, 0, 0, 0)

        titlebar = QWidget()
        tb = QHBoxLayout(titlebar)
        tb.setContentsMargins(14, 0, 8, 0)
        tb.setSpacing(4)
        brand = QLabel("eConvert")
        brand.setObjectName("Brand")
        self._tb_brand = brand
        sub = QLabel("文件格式转换")
        sub.setObjectName("BrandSub")
        tb.addWidget(brand)
        tb.addWidget(sub)
        tb.addStretch(1)

        self._min_btn = QPushButton("\u2500")
        self._min_btn.setObjectName("WinBtn")
        self._min_btn.setFixedSize(42, 28)
        self._min_btn.clicked.connect(self.showMinimized)
        self._max_btn = QPushButton("\u25a1")
        self._max_btn.setObjectName("WinBtn")
        self._max_btn.setFixedSize(42, 28)
        self._max_btn.clicked.connect(self.toggle_maximize)
        close_btn = QPushButton("\u2715")
        close_btn.setObjectName("WinBtnClose")
        close_btn.setFixedSize(42, 28)
        close_btn.clicked.connect(self.close)
        for b in (self._min_btn, self._max_btn, close_btn):
            tb.addWidget(b, alignment=Qt.AlignmentFlag.AlignVCenter)
        outer_lay.addWidget(titlebar)

        body = QWidget()
        body_lay = QHBoxLayout(body)
        body_lay.setSpacing(0)
        body_lay.setContentsMargins(0, 0, 0, 0)
        outer_lay.addWidget(body, 1)

        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(196)
        sl = QVBoxLayout(sidebar)
        sl.setContentsMargins(12, 14, 12, 12)
        sl.setSpacing(4)

        brand2 = QLabel("eConvert")
        brand2.setObjectName("Brand")
        brand2.setStyleSheet("font-size: 21px;")
        brand_sub = QLabel("PDF · 音频 · 图片 · 视频")
        brand_sub.setObjectName("BrandSub")
        sl.addWidget(brand2)
        sl.addWidget(brand_sub)
        sl.addSpacing(16)

        self._nav_group = QButtonGroup(self)
        self._nav_group.setExclusive(True)
        nav_specs = [
            (0, "\u25a4  PDF 转 Word"),
            (1, "\u266a  音频转换"),
            (2, "\u25a6  图片转换"),
            (3, "\u25b6  视频转换"),
            (4, "\u2699  设置"),
        ]
        for idx, text in nav_specs:
            btn = QToolButton()
            btn.setObjectName("NavBtn")
            btn.setText(text)
            btn.setCheckable(True)
            btn.setMinimumHeight(40)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._nav_group.addButton(btn, idx)
            btn.clicked.connect(lambda _=False, i=idx: self._switch_page(i))
            sl.addWidget(btn)
        self._nav_group.button(0).setChecked(True)
        sl.addStretch(1)

        ff_dot = QLabel()
        ff_dot.setFixedSize(9, 9)
        ff_ready = FFMPEG_READY
        ff_dot.setStyleSheet(
            f"background: {'#107C10' if ff_ready else '#C43E1C'}; border-radius: 4px;")
        ff_text = QLabel("FFmpeg 已就绪" if ff_ready else "FFmpeg 未找到")
        ff_text.setObjectName("DropSub")
        row = QHBoxLayout()
        row.setSpacing(7)
        row.addWidget(ff_dot)
        row.addWidget(ff_text)
        row.addStretch(1)
        ver = QLabel("v1.0")
        ver.setObjectName("BrandSub")
        row.addWidget(ver)
        sl.addLayout(row)
        body_lay.addWidget(sidebar)

        self._stack = QStackedWidget()
        body_lay.addWidget(self._stack, 1)

        self._pages = [
            ConvertPage(self, "pdf", "PDF 转 Word",
                        "将 PDF 文档转换为可编辑的 Word 文档（保留排版、表格与图片）",
                        {"pdf"}, None),
            ConvertPage(self, "audio", "音频转换",
                        "在常见音频格式之间相互转换，也可直接提取视频中的音频",
                        AUDIO_EXTENSIONS, AUDIO_TARGETS),
            ConvertPage(self, "image", "图片转换",
                        "在常见图片格式之间相互转换，自动修正方向并保留质量",
                        {"png", "jpg", "jpeg", "jfif", "bmp", "webp", "gif", "tiff",
                         "tif", "ico", "eps", "raw"}, IMG_TARGETS()),
            ConvertPage(self, "video", "视频转换",
                        "在常见视频格式之间相互转换，支持输出 GIF 动图",
                        {"mp4", "avi", "mkv", "mov", "webm", "flv", "wmv", "m4v",
                         "ts", "mpg", "mpeg", "3gp", "gif"}, VIDEO_TARGETS),
        ]
        for page in self._pages:
            self._stack.addWidget(page)

        self._settings_page = SettingsPage(self)
        self._stack.addWidget(self._settings_page)
        self.apply_appearance()

    def showEvent(self, e):
        super().showEvent(e)
        self._apply_acrylic()

    def apply_appearance(self):
        dark = bool(self.settings.get("dark"))
        acrylic = bool(self.settings.get("acrylic"))
        QApplication.instance().setStyleSheet(make_qss(dark, acrylic))
        self._apply_acrylic()

    def _apply_acrylic(self):
        try:
            set_acrylic_windows(int(self.winId()),
                                bool(self.settings.get("acrylic")),
                                bool(self.settings.get("dark")))
        except Exception:
            pass

    def _switch_page(self, idx):
        self._stack.setCurrentIndex(idx)
        self._max_btn.setText("\u25a1")

    def toggle_maximize(self):
        if self._maximized:
            self.showNormal()
        else:
            self._normal_geo = self.geometry()
            self.showMaximized()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._maximized = self.isMaximized()
        self._max_btn.setText("\u2750" if self._maximized else "\u25a1")
        self._apply_chrome()

    def _apply_chrome(self):
        m = 0 if self._maximized else 14
        self._outer_layout.setContentsMargins(m, m, m, m)
        self._outer.setProperty("maximized", "true" if self._maximized else "false")
        self._outer.style().unpolish(self._outer)
        self._outer.style().polish(self._outer)
        if self._maximized:
            fx = self._outer.graphicsEffect()
            if fx:
                fx.setEnabled(False)

    def _edge_at(self, pos):
        if self._maximized:
            return 0
        x, y = pos.x(), pos.y()
        w, h = self.width(), self.height()
        edge = 0
        if x < EDGE:
            edge |= 1
        if x >= w - EDGE:
            edge |= 2
        if y < EDGE:
            edge |= 4
        if y >= h - EDGE:
            edge |= 8
        return edge

    def _cursor_for_edge(self, edge):
        if edge in (1 | 4, 2 | 8):
            return Qt.CursorShape.SizeFDiagCursor
        if edge in (2 | 4, 1 | 8):
            return Qt.CursorShape.SizeBDiagCursor
        if edge & (1 | 2):
            return Qt.CursorShape.SizeHorCursor
        if edge & (4 | 8):
            return Qt.CursorShape.SizeVerCursor
        return Qt.CursorShape.ArrowCursor

    def mousePressEvent(self, e):
        if e.button() != Qt.MouseButton.LeftButton:
            return super().mousePressEvent(e)
        edge = self._edge_at(e.position().toPoint())
        if edge:
            self._resize_edge = edge
            self._resize_global = e.globalPosition().toPoint()
            self._resize_geo = QRect(self.geometry())
            e.accept()
            return
        pos = e.position().toPoint()
        if pos.y() <= TITLE_H and not self._maximized:
            self._drag_offset = e.globalPosition().toPoint() - self.pos()
            e.accept()
            return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        g = e.globalPosition().toPoint()
        if self._resize_edge:
            delta = g - self._resize_global
            r = QRect(self._resize_geo)
            x1, y1, x2, y2 = r.left(), r.top(), r.right(), r.bottom()
            if self._resize_edge & 1:
                x1 = min(r.left() + delta.x(), r.right() - MIN_W)
            if self._resize_edge & 2:
                x2 = max(r.right() + delta.x(), r.left() + MIN_W)
            if self._resize_edge & 4:
                y1 = min(r.top() + delta.y(), r.bottom() - MIN_H)
            if self._resize_edge & 8:
                y2 = max(r.bottom() + delta.y(), r.top() + MIN_H)
            self.setGeometry(x1, y1, x2 - x1, y2 - y1)
            e.accept()
            return
        if self._drag_offset is not None:
            self.move(g - self._drag_offset)
            e.accept()
            return
        if not e.buttons():
            self.setCursor(self._cursor_for_edge(self._edge_at(e.position().toPoint())))
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        self._resize_edge = 0
        self._resize_global = None
        self._resize_geo = None
        self._drag_offset = None
        super().mouseReleaseEvent(e)

    def mouseDoubleClickEvent(self, e):
        if e.position().toPoint().y() <= TITLE_H and e.button() == Qt.MouseButton.LeftButton:
            self.toggle_maximize()
            e.accept()
            return
        super().mouseDoubleClickEvent(e)

    def start_conversion(self, page):
        if self._worker is not None and self._worker.isRunning():
            return
        if not page.files():
            return
        if not FFMPEG_READY and page.mode != "pdf":
            expected = (_app_root() / "assets" / "ffmpeg-master-latest-win64-gpl"
                        / "bin" / "ffmpeg.exe")
            QMessageBox.warning(
                self, "FFmpeg 未找到",
                "未找到 FFmpeg。\n\n"
                f"请将 ffmpeg.exe 放入：\n{expected}\n\n"
                "或在系统 PATH 中安装 FFmpeg，重启应用后重试。")
            return
        self._active_page = page
        cfg = {
            "audio": {
                "volume": int(self.settings.get("audio_volume", 100)),
                "rate": int(self.settings.get("audio_rate", 0) or 0),
            },
            "video": {
                "crf": int(self.settings.get("video_crf", 18)),
                "height": int(self.settings.get("video_height", 0) or 0),
                "fps": int(self.settings.get("video_fps", 30)),
                "codec": str(self.settings.get("video_codec", "h264")),
                "volume": int(self.settings.get("audio_volume", 100)),
                "rate": int(self.settings.get("audio_rate", 0) or 0),
            },
            "image": {
                "quality": int(self.settings.get("image_quality", 90)),
            },
        }
        self._worker = ConvertWorker(page.mode, page.files(), page.target(),
                                     page.output_dir(), cfg=cfg)
        self._worker.progress.connect(page.on_progress)
        self._worker.status.connect(page.set_status)
        self._worker.done.connect(self._on_worker_done)
        page.on_progress(0)
        page.set_status("准备中…")
        page.set_running(True)
        self._worker.start()

    def cancel_conversion(self):
        if self._worker is not None and self._worker.isRunning():
            self._worker.cancel()
            if self._active_page:
                self._active_page.set_status("正在取消…")

    def _on_worker_done(self, ok, fail, errors, cancelled):
        page = self._active_page
        page.set_running(False)
        page.on_progress(100)
        page.show_finish(ok, fail, errors, cancelled)
        self._worker = None
        self._active_page = None


def IMG_TARGETS():
    from PIL import Image as PILImage
    return {
        "PNG":  {"ext": "png"},
        "JPG":  {"ext": "jpg"},
        "WEBP": {"ext": "webp"},
        "GIF":  {"ext": "gif"},
        "BMP":  {"ext": "bmp"},
        "TIFF": {"ext": "tiff"},
        "ICO":  {"ext": "ico"},
    }


def make_app_icon():
    pm = QPixmap(128, 128)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor(ACCENT))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(2, 2, 124, 124, 28, 28)
    f = QFont("Segoe UI", 60, QFont.Weight.Bold)
    p.setFont(f)
    p.setPen(QColor("#FFFFFF"))
    p.drawText(pm.rect(), Qt.AlignmentFlag.AlignCenter, "e")
    p.end()
    return QIcon(pm)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("eConvert")
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()