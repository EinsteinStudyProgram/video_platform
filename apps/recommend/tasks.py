"""
============================================================
 推荐模块 - Celery 定时任务
============================================================
 后台维护任务：
    1. 定期计算视频标签权重
    2. 清理过期的用户行为日志
    3. 生成热门视频缓存
============================================================
"""
import math
import logging
from collections import Counter
from datetime import timedelta

from celery import shared_task
from django.db.models import Count, Q, Sum
from django.utils import timezone
from django.conf import settings

from apps.videos.models import Video
from .models import UserActionLog, VideoTagWeight

logger = logging.getLogger(__name__)


@shared_task
def compute_tag_weights():
    """
    计算视频标签权重（定时任务）

    根据用户行为日志，分析哪些标签与视频关联更紧密。
    权重计算公式：
        weight(tag, video) = (tag在video上的行为数) / (该视频总行为数) * log(10 + 总行为数)

    触发频率：每 6 小时
    """
    logger.info('开始计算视频标签权重...')

    # 获取最近 7 天的行为日志
    since = timezone.now() - timedelta(days=7)
    logs = UserActionLog.objects.filter(
        created_at__gte=since,
        video__isnull=False,
    ).values('video_id', 'video__tags').annotate(
        action_count=Count('id')
    )[:1000]  # 限制每次处理的视频量

    count = 0
    for item in logs:
        video_id = item['video_id']
        tags_str = item.get('video__tags', '')
        if not tags_str:
            continue

        # 解析标签
        tags = [t.strip() for t in tags_str.split(',') if t.strip()]
        total_actions = item['action_count']

        for tag in tags:
            # 计算该标签在视频上的行为数
            tag_action_count = UserActionLog.objects.filter(
                video_id=video_id,
                created_at__gte=since,
            ).filter(
                Q(video__tags__icontains=tag)
            ).count()

            # 权重公式
            weight = (tag_action_count / max(total_actions, 1)) * math.log(10 + total_actions)
            weight = min(max(weight, 0.0), 1.0)  # 裁剪到 0~1

            # 更新或创建
            VideoTagWeight.objects.update_or_create(
                video_id=video_id,
                tag=tag,
                defaults={'weight': round(weight, 4)},
            )
            count += 1

    logger.info(f'标签权重计算完成: 共处理 {count} 条')
    return {'processed': count}


@shared_task
def cleanup_old_action_logs():
    """
    清理过期行为日志

    保留策略：
        - view: 30 天
        - like/favorite/comment/share: 90 天
        - search: 7 天

    触发频率：每天凌晨
    """
    now = timezone.now()
    total_deleted = 0

    # 清理浏览日志（保留 30 天）
    view_threshold = now - timedelta(days=30)
    deleted, _ = UserActionLog.objects.filter(
        action='view', created_at__lt=view_threshold
    ).delete()
    total_deleted += deleted

    # 清理搜索日志（保留 7 天）
    search_threshold = now - timedelta(days=7)
    deleted, _ = UserActionLog.objects.filter(
        action='search', created_at__lt=search_threshold
    ).delete()
    total_deleted += deleted

    # 清理其他日志（保留 90 天）
    other_threshold = now - timedelta(days=90)
    deleted, _ = UserActionLog.objects.filter(
        created_at__lt=other_threshold
    ).exclude(
        action__in=['view', 'search']
    ).delete()
    total_deleted += deleted

    logger.info(f'日志清理完成: 共删除 {total_deleted} 条过期日志')
    return {'deleted': total_deleted}


@shared_task
def warm_up_recommend_cache():
    """
    预热推荐缓存

    提前计算出推荐结果，存入缓存，减少用户请求时的计算延迟。

    逻辑：
        1. 计算今日热门 TOP 50
        2. 按分类分别计算热门 TOP 20
        3. 存入 Django 缓存

    触发频率：每 30 分钟
    """
    from django.core.cache import cache

    # 今日热门
    recent = timezone.now() - timedelta(days=3)
    trending_ids = list(Video.objects.filter(
        status=Video.StatusChoices.PUBLISHED,
        created_at__gte=recent,
    ).order_by('-views_count').values_list('pk', flat=True)[:50])

    cache.set('recommend:trending_today', trending_ids, 1800)  # 30 分钟
    logger.info(f'推荐缓存预热完成: 今日热门 {len(trending_ids)} 个视频')

    return {'trending_count': len(trending_ids)}
