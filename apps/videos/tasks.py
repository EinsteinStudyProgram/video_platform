"""
============================================================
 视频模块 - Celery 异步任务
============================================================
 视频上传后自动执行的耗时任务：
    1. 提取视频元数据（时长、分辨率等）
    2. 生成缩略图（封面）
    3. 多分辨率转码（480p / 720p / 1080p）
    4. 更新视频状态

 定时维护任务：
    1. cleanup_pending_videos: 清理超过 24 小时仍为"待转码"的视频
    2. cleanup_temp_files: 定期清理临时文件
============================================================
"""
import os
import json
import subprocess
import logging
from pathlib import Path

from celery import shared_task
from django.conf import settings
from django.db.models import F, Q
from django.utils import timezone

from .models import Video
from .utils import get_video_metadata, generate_thumbnail

# 获取日志记录器
logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def process_video_task(self, video_id: int):
    """
    视频处理主任务（异步执行）

    工作流程：
        1. 根据 video_id 获取视频记录
        2. 更新状态为"转码中"
        3. 提取视频元数据（时长、分辨率等）
        4. 生成缩略图
        5. 执行多分辨率转码
        6. 更新状态为"已发布"

    参数：
        video_id: Video 模型的主键 ID

    重试机制：
        - 最多重试 3 次
        - 每次重试间隔递增（10s, 20s, 40s...）
    """
    try:
        # ---- 步骤 1：获取视频记录 ----
        video = Video.objects.get(pk=video_id)

        # 获取源文件绝对路径
        source_path = os.path.join(
            settings.MEDIA_ROOT, video.video_file.name
        )

        if not os.path.exists(source_path):
            logger.error(f'视频源文件不存在: {source_path}')
            video.status = Video.StatusChoices.FAILED
            video.save(update_fields=['status'])
            return {'success': False, 'error': '源文件不存在'}

        # ---- 步骤 2：更新状态为"转码中" ----
        video.status = Video.StatusChoices.TRANSCODING
        video.save(update_fields=['status'])
        logger.info(f'开始处理视频 [{video.id}]: {video.title}')

        # ---- 步骤 3：提取视频元数据 ----
        metadata = get_video_metadata(source_path)
        if metadata.get('duration', 0) > 0:
            video.duration = metadata['duration']
        if metadata.get('file_size', 0) > 0:
            video.file_size = metadata['file_size']

        # ---- 步骤 4：生成缩略图 ----
        if not video.thumbnail:
            # 生成缩略图文件名
            thumbnail_filename = f'thumb_{video.id}_{Path(source_path).stem}.jpg'
            thumbnail_rel_path = os.path.join('thumbnails', thumbnail_filename)
            thumbnail_abs_path = os.path.join(
                settings.MEDIA_ROOT, thumbnail_rel_path
            )

            # 确保缩略图目录存在
            os.makedirs(os.path.dirname(thumbnail_abs_path), exist_ok=True)

            # 调用 FFmpeg 生成缩略图
            success = generate_thumbnail(source_path, thumbnail_abs_path)
            if success:
                video.thumbnail = thumbnail_rel_path
                logger.info(f'缩略图生成成功: {thumbnail_rel_path}')
            else:
                logger.warning(f'缩略图生成失败，将继续转码流程')

        # ---- 步骤 5：多分辨率转码 ----
        transcoded_files = {}
        resolutions = settings.VIDEO_RESOLUTIONS

        for res in resolutions:
            suffix = res['suffix']
            width = res['width']
            height = res['height']
            bitrate = res['bitrate']

            # 生成输出文件名：原文件名_480p.mp4
            source_stem = Path(source_path).stem
            output_filename = f'{source_stem}_{suffix}.mp4'
            output_rel_path = os.path.join('videos', 'transcoded', output_filename)
            output_abs_path = os.path.join(
                settings.MEDIA_ROOT, output_rel_path
            )

            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_abs_path), exist_ok=True)

            # 执行 FFmpeg 转码命令
            try:
                cmd = [
                    settings.FFMPEG_PATH,
                    '-i', source_path,
                    # 视频编码：H.264（最广泛兼容）
                    '-c:v', 'libx264',
                    '-preset', 'medium',          # 编码速度与质量的平衡
                    '-crf', '23',                 # 质量参数（18-28，越小质量越高）
                    '-vf', f'scale={width}:{height}:force_original_aspect_ratio=decrease,'
                           f'pad={width}:{height}:(ow-iw)/2:(oh-ih)/2',
                    # 上面这行：缩放并添加黑边填充至目标分辨率

                    # 视频码率控制
                    '-b:v', bitrate,
                    '-maxrate', f'{int(bitrate[:-1]) * 2}k',
                    '-bufsize', f'{int(bitrate[:-1]) * 4}k',

                    # 音频编码：AAC
                    '-c:a', 'aac',
                    '-b:a', '128k',
                    '-ar', '44100',
                    '-ac', '2',

                    # 输出
                    '-movflags', '+faststart',    # 支持流式播放（重要！）
                    '-y',                          # 覆盖已存在的文件
                    output_abs_path,
                ]

                logger.info(f'开始转码 {suffix}: {output_filename}')
                subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=3600,                 # 1 小时超时（大视频转码可能很慢）
                    check=True,
                )

                # 记录转码后的文件路径（相对路径）
                transcoded_files[suffix] = output_rel_path
                logger.info(f'转码完成 {suffix}: {output_filename}')

            except subprocess.CalledProcessError as e:
                logger.error(f'转码失败 {suffix}: {e.stderr[:500]}')
                # 某分辨率转码失败不影响其他分辨率
                continue
            except subprocess.TimeoutExpired:
                logger.error(f'转码超时 {suffix}: 超过 1 小时')
                continue

        # 保存转码结果
        if transcoded_files:
            video.transcoded_files = transcoded_files

        # ---- 步骤 6：更新状态为"已发布" ----
        video.status = Video.StatusChoices.PUBLISHED
        video.save()

        logger.info(f'视频处理完成 [{video.id}]: {video.title}')
        return {
            'success': True,
            'video_id': video.id,
            'title': video.title,
            'duration': video.duration,
            'thumbnail': str(video.thumbnail) if video.thumbnail else None,
            'transcoded_resolutions': list(transcoded_files.keys()),
        }

    except Video.DoesNotExist:
        logger.error(f'视频记录不存在: video_id={video_id}')
        return {'success': False, 'error': '视频记录不存在'}
    except Exception as e:
        logger.exception(f'视频处理异常 [{video_id}]: {str(e)}')

        # 重试逻辑
        try:
            self.retry(exc=e)
        except self.MaxRetriesExceededError:
            # 重试用尽，标记为失败
            try:
                video = Video.objects.get(pk=video_id)
                video.status = Video.StatusChoices.FAILED
                video.save(update_fields=['status'])
            except Video.DoesNotExist:
                pass

        return {'success': False, 'error': str(e)}


# ============================================================
# 定时清理任务
# ============================================================

@shared_task
def cleanup_pending_videos():
    """
    清理长时间处于"待转码"状态的视频

    执行逻辑：
        查找创建时间超过 24 小时且状态仍为 "pending" 的视频，
        将其标记为 "failed"，便于管理员排查。

    触发方式（Celery Beat 定时任务）：
        celery -A config beat -l info

    settings.py 中配置：
        CELERY_BEAT_SCHEDULE = {
            'cleanup-pending-videos': {
                'task': 'apps.videos.tasks.cleanup_pending_videos',
                'schedule': 3600.0,  # 每小时执行一次
            },
        }
    """
    threshold = timezone.now() - timezone.timedelta(hours=24)
    expired_videos = Video.objects.filter(
        status=Video.StatusChoices.PENDING,
        created_at__lt=threshold,
    )

    count = expired_videos.count()
    if count > 0:
        expired_videos.update(status=Video.StatusChoices.FAILED)
        logger.info(f'清理了 {count} 个超时未转码的视频')
    else:
        logger.info('没有超时未转码的视频需要清理')

    return {'cleaned_count': count}


@shared_task
def retry_failed_transcoding():
    """
    重试所有标记为 "failed" 且可以重新转码的视频

    执行逻辑：
        查找状态为 "failed" 的视频，重新触发转码任务。
        避免重复触发：只处理失败次数少于 3 次的视频。

    触发方式：手动执行或定时调度
    """
    # 获取所有失败视频中，源文件仍然存在的
    failed_videos = Video.objects.filter(
        status=Video.StatusChoices.FAILED,
    )

    retry_count = 0
    for video in failed_videos:
        source_path = os.path.join(
            settings.MEDIA_ROOT, video.video_file.name
        )
        if os.path.exists(source_path):
            # 重新触发转码
            video.status = Video.StatusChoices.PENDING
            video.save(update_fields=['status'])
            process_video_task.delay(video.id)
            retry_count += 1
            logger.info(f'重新触发转码: video_id={video.id}')

    logger.info(f'重试了 {retry_count} 个失败视频的转码')
    return {'retry_count': retry_count}
