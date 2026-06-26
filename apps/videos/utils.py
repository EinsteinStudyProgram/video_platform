"""
============================================================
 视频模块 - 工具函数
============================================================
 视频上传安全校验、文件类型检测、FFprobe 元数据提取等。
============================================================
"""
import os
import re
import json
import subprocess
import uuid
from typing import Tuple, Optional, Dict, Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


# ============================================================
# 允许上传的视频文件后缀名（白名单）
# ============================================================
ALLOWED_VIDEO_EXTENSIONS = {
    '.mp4',   # MPEG-4，最通用的格式
    '.mov',   # QuickTime
    '.avi',   # AVI 格式
    '.mkv',   # Matroska 格式
    '.webm',  # WebM 格式（HTML5 标准之一）
    '.flv',   # Flash 视频
    '.wmv',   # Windows Media Video
    '.m4v',   # MPEG-4 Video
    '.3gp',   # 3GPP 移动端格式
}

# 允许的 MIME 类型白名单（基于文件内容检测）
ALLOWED_MIME_TYPES = {
    'video/mp4',
    'video/quicktime',
    'video/x-msvideo',
    'video/x-matroska',
    'video/webm',
    'video/x-flv',
    'video/x-ms-wmv',
    'video/mp4v-es',
    'video/3gpp',
}

# 最大文件大小：2GB（以字节为单位）
MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2GB


def validate_video_file(uploaded_file) -> None:
    """
    视频文件安全校验

    对上传的视频文件进行多层安全检查：
        1. 文件大小检查（不超过 2GB）
        2. 文件扩展名白名单检查
        3. MIME 类型检查（后续可加强为 Magic Bytes 检测）

    参数：
        uploaded_file: Django UploadedFile 对象

    抛出：
        ValidationError: 当文件不符合安全要求时
    """
    errors = []

    # ----- 1. 检查文件大小 -----
    if uploaded_file.size > MAX_FILE_SIZE:
        size_in_gb = uploaded_file.size / (1024 * 1024 * 1024)
        errors.append(
            f'文件大小超过限制（{size_in_gb:.1f}GB > 2GB），'
            f'建议压缩或使用分片上传功能'
        )

    if uploaded_file.size <= 0:
        errors.append('上传的文件为空，请重新选择')

    # ----- 2. 检查文件扩展名 -----
    _, ext = os.path.splitext(uploaded_file.name.lower())
    if ext not in ALLOWED_VIDEO_EXTENSIONS:
        allowed_exts = ', '.join(ALLOWED_VIDEO_EXTENSIONS)
        errors.append(
            f'不支持的文件格式 "{ext}"。'
            f'允许的格式：{allowed_exts}'
        )

    # ----- 3. 检查 MIME 类型 -----
    # Django 会根据文件内容自动判断 content_type
    # 注意：浏览器可能不总是发送正确的 MIME 类型
    mime_type = getattr(uploaded_file, 'content_type', '')
    if mime_type and mime_type not in ALLOWED_MIME_TYPES:
        errors.append(f'文件类型 "{mime_type}" 不在允许列表中')

    if errors:
        raise ValidationError(errors)


def get_video_metadata(file_path: str) -> Dict[str, Any]:
    """
    使用 FFprobe 提取视频文件元数据

    包括：
        - 视频时长（秒）
        - 视频编码格式
        - 视频分辨率（宽度 x 高度）
        - 帧率
        - 音频编码信息

    参数：
        file_path: 视频文件的绝对路径

    返回：
        dict: 包含视频元数据的字典

    如果 FFprobe 不可用或提取失败，返回空字典。
    """
    ffprobe_path = settings.FFPROBE_PATH

    try:
        # 使用 ffprobe 以 JSON 格式输出视频流信息
        cmd = [
            ffprobe_path,
            '-v', 'quiet',                       # 减少日志输出
            '-print_format', 'json',              # JSON 格式输出
            '-show_format',                      # 显示封装格式信息
            '-show_streams',                     # 显示各流信息
            file_path,
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,                          # 30 秒超时
            check=True,                          # 非零返回码触发 CalledProcessError
        )

        data = json.loads(result.stdout)
        metadata = {}

        # ----- 提取封装格式信息 -----
        fmt = data.get('format', {})
        metadata['duration'] = float(fmt.get('duration', 0))
        metadata['file_size'] = int(fmt.get('size', 0))
        metadata['bit_rate'] = int(fmt.get('bit_rate', 0))

        # ----- 提取视频流信息 -----
        video_stream = None
        audio_stream = None

        for stream in data.get('streams', []):
            if stream['codec_type'] == 'video' and not video_stream:
                video_stream = stream
            elif stream['codec_type'] == 'audio' and not audio_stream:
                audio_stream = stream

        if video_stream:
            metadata['video_codec'] = video_stream.get('codec_name', '')
            metadata['width'] = int(video_stream.get('width', 0))
            metadata['height'] = int(video_stream.get('height', 0))
            # 帧率可能是 "30/1" 或 "30000/1001" 这样的分数形式
            avg_frame_rate = video_stream.get('avg_frame_rate', '0/1')
            if '/' in avg_frame_rate:
                try:
                    num, den = avg_frame_rate.split('/')
                    metadata['fps'] = float(num) / float(den) if float(den) > 0 else 0
                except (ValueError, ZeroDivisionError):
                    metadata['fps'] = 0
            else:
                metadata['fps'] = float(avg_frame_rate)

        if audio_stream:
            metadata['audio_codec'] = audio_stream.get('codec_name', '')
            metadata['audio_channels'] = int(audio_stream.get('channels', 0))

        return metadata

    except (subprocess.CalledProcessError, subprocess.TimeoutExpired,
            FileNotFoundError, json.JSONDecodeError, ValueError) as e:
        # 记录错误但不上报异常（允许用户上传视频，即使元数据提取失败）
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f'FFprobe 提取视频元数据失败 [{file_path}]: {e}')
        return {'duration': 0, 'file_size': 0}


def generate_thumbnail(video_path: str, thumbnail_path: str,
                       time_seconds: Optional[float] = None) -> bool:
    """
    使用 FFmpeg 从视频中提取缩略图

    默认提取视频 1/3 处的帧作为封面图，也可指定时间点。

    参数：
        video_path:     视频文件绝对路径
        thumbnail_path: 缩略图输出路径
        time_seconds:   提取帧的时间点（秒），默认取视频 1/3 位置

    返回：
        bool: 生成成功返回 True，失败返回 False
    """
    ffmpeg_path = settings.FFMPEG_PATH

    try:
        # 如果未指定时间，默认提取视频 1/3 位置的帧
        if time_seconds is None:
            # 先用 ffprobe 获取视频时长
            metadata = get_video_metadata(video_path)
            duration = metadata.get('duration', 0)
            time_seconds = duration / 3 if duration > 0 else 1

        cmd = [
            ffmpeg_path,
            '-i', video_path,
            '-ss', str(time_seconds),           # 定位到指定时间
            '-vframes', '1',                     # 只提取一帧
            '-q:v', '2',                         # 图片质量（2 = 高质量）
            '-vf', 'scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2',
            # 上面这行：缩放并填充为 1280x720（16:9 标准封面尺寸）
            '-y',                                # 覆盖已存在的文件
            thumbnail_path,
        ]

        subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            check=True,
        )
        return True

    except (subprocess.CalledProcessError, subprocess.TimeoutExpired,
            FileNotFoundError) as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f'FFmpeg 生成缩略图失败 [{video_path}]: {e}')
        return False


def get_video_file_path(relative_path: str) -> str:
    """
    从相对路径获取视频文件的绝对路径

    参数：
        relative_path: 相对于 MEDIA_ROOT 的路径

    返回：
        str: 文件的绝对路径
    """
    return os.path.join(settings.MEDIA_ROOT, relative_path)


def human_readable_size(size_bytes: int) -> str:
    """
    将字节数转换为人类可读的文件大小

    例如：
        1024 -> 1.0 KB
        1048576 -> 1.0 MB
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f'{size_bytes:.1f} {unit}'
        size_bytes /= 1024
    return f'{size_bytes:.1f} PB'
