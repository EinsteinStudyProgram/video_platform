"""
============================================================
 推荐引擎 - 核心算法
============================================================
 实现了三种推荐策略，融合后返回最终推荐结果：

    1. 基于内容的推荐 (Content-Based)
       根据视频标签的相似度进行推荐。
       用户看过 A，A 有标签 "Python, Django"，则推荐同样带这些标签的视频。

    2. 协同过滤 (Collaborative Filtering)
       根据"其他用户也喜欢"的群体行为进行推荐。
       看过 A 的用户也看过 B，则向目标用户推荐 B。

    3. 热门推荐 (Trending / Popularity)
       根据播放量、点赞率、时效性等综合热度评分。
       作为新用户的冷启动默认推荐。

    融合策略：
        对上述三种推荐的得分进行加权求和：
        - 新用户/冷启动：热门(0.7) + 内容(0.3)
        - 老用户：协同(0.4) + 内容(0.35) + 热门(0.25)
============================================================
"""
import math
import json
import random
from collections import defaultdict, Counter
from datetime import timedelta
from typing import List, Dict, Optional, Tuple

from django.db.models import Q, Count, Sum, Avg, F, FloatField, Case, When
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.conf import settings

from apps.videos.models import Video, Category
from .models import UserActionLog, VideoTagWeight


class RecommendEngine:
    """
    推荐引擎主类

    使用方式：
        engine = RecommendEngine()
        videos = engine.get_recommendations(user=request.user, count=12)
    """

    # 各类行为的权重评分
    ACTION_WEIGHTS = {
        'view': 1.0,       # 浏览
        'like': 3.0,       # 点赞
        'favorite': 5.0,   # 收藏
        'comment': 4.0,    # 评论
        'share': 6.0,      # 分享
        'watch': 0.01,     # 观看时长（每秒）
    }

    def __init__(self):
        self.now = timezone.now()

    def get_recommendations(self, user=None, video_id=None, count=12,
                            exclude_ids=None) -> List[Video]:
        """
        获取推荐视频列表

        参数：
            user:        当前用户（可选，为 None 时使用热门推荐）
            video_id:    当前视频 ID（用于"看了又看"推荐）
            count:       需要返回的视频数量
            exclude_ids: 需要排除的视频 ID 集合（如已在页面上显示的）

        返回：
            按推荐度排序的 Video QuerySet
        """
        exclude_ids = set(exclude_ids or [])

        # ---- 策略选择 ----
        if user and user.is_authenticated and self._has_user_history(user):
            # 有行为的登录用户：融合推荐
            scores = self._get_hybrid_scores(user, video_id=video_id)
        elif video_id:
            # 有当前视频：基于内容的"看了又看"推荐
            scores = self._get_content_based_scores(video_id)
        else:
            # 新用户/未登录：热门推荐
            scores = self._get_trending_scores()

        # ---- 过滤和排序 ----
        # 排除已看过的视频和自定义排除列表
        if user and user.is_authenticated:
            watched_ids = set(UserActionLog.objects.filter(
                user=user, action__in=['view', 'watch']
            ).values_list('video_id', flat=True)[:200])
            exclude_ids |= watched_ids

        # 去掉需要排除的视频
        for vid in exclude_ids:
            scores.pop(vid, None)

        # 按得分排序取前 N 个
        sorted_videos = sorted(scores.items(), key=lambda x: -x[1])[:count * 2]
        video_ids = [vid for vid, _ in sorted_videos]

        # 如果数量不足，用热门推荐补充
        if len(video_ids) < count:
            trending = self._get_trending_scores(exclude=set(video_ids) | exclude_ids)
            for vid, score in sorted(trending.items(), key=lambda x: -x[1]):
                if vid not in video_ids:
                    video_ids.append(vid)
                if len(video_ids) >= count:
                    break

        # 转为 Video 对象并保持排序
        result = list(Video.objects.filter(
            pk__in=video_ids[:count],
            status=Video.StatusChoices.PUBLISHED,
        ))

        # 保持分数排序
        result.sort(key=lambda v: video_ids.index(v.pk) if v.pk in video_ids else 999)

        return result

    # ============================================================
    # 策略 1：基于内容的推荐
    # ============================================================

    def _get_content_based_scores(self, video_id: int) -> Dict[int, float]:
        """
        基于内容的推荐（"看了又看"模式）

        根据目标视频的标签和分类，找到特征相似的其他视频。
        """
        try:
            target_video = Video.objects.get(pk=video_id)
        except Video.DoesNotExist:
            return {}

        scores = {}

        # ----- 1.1 标签相似度（核心）-----
        target_tags = self._extract_tags_from_video(target_video)
        if target_tags:
            # 查找拥有相同标签的视频
            similar_by_tags = VideoTagWeight.objects.filter(
                tag__in=target_tags,
            ).exclude(video_id=video_id).values('video_id').annotate(
                similarity=Sum('weight')
            ).order_by('-similarity')[:30]

            for item in similar_by_tags:
                scores[item['video_id']] = item['similarity'] * 0.6

        # ----- 1.2 同分类推荐 -----
        if target_video.category_id:
            category_videos = Video.objects.filter(
                category=target_video.category,
                status=Video.StatusChoices.PUBLISHED,
            ).exclude(pk=video_id).values_list('pk', 'views_count')

            for vid, views in category_videos:
                # 同分类视频基础得分 + 播放量权重
                base_score = scores.get(vid, 0) + 0.3
                popularity = math.log(views + 1) * 0.05
                scores[vid] = base_score + popularity

        # ----- 1.3 标签字符串模糊匹配 -----
        if target_video.tags:
            raw_tags = [t.strip() for t in target_video.tags.split(',') if t.strip()]
            for tag in raw_tags:
                similar_videos = Video.objects.filter(
                    tags__icontains=tag,
                    status=Video.StatusChoices.PUBLISHED,
                ).exclude(pk=video_id).values_list('pk', flat=True)[:20]

                for vid in similar_videos:
                    scores[vid] = scores.get(vid, 0) + 0.2

        return scores

    # ============================================================
    # 策略 2：协同过滤
    # ============================================================

    def _get_collaborative_scores(self, user) -> Dict[int, float]:
        """
        基于用户的协同过滤推荐

        原理：找到与当前用户行为相似的其他用户（"品味相似"的用户），
        然后将这些用户喜欢但当前用户未看过的视频推荐过来。

        算法步骤：
            1. 找到当前用户最近观看/互动的视频列表
            2. 找到同样看过这些视频的其他用户
            3. 统计这些用户还看过哪些其他视频
            4. 按共现频率排序推荐
        """
        # 步骤 1：获取当前用户最近 50 个有行为的视频
        user_video_ids = set(UserActionLog.objects.filter(
            user=user,
            video__isnull=False,
        ).order_by('-created_at').values_list('video_id', flat=True)[:50])

        if not user_video_ids:
            return {}

        # 步骤 2：找到同样看过这些视频的其他用户（排除当前用户）
        similar_users = UserActionLog.objects.filter(
            video_id__in=user_video_ids,
            action__in=['view', 'like', 'favorite'],
        ).exclude(user=user).values_list('user', flat=True).distinct()[:200]

        if not similar_users:
            return {}

        # 步骤 3：这些用户还看了什么
        candidate_logs = UserActionLog.objects.filter(
            user__in=similar_users,
            action__in=['view', 'like', 'favorite'],
        ).exclude(
            video_id__in=user_video_ids
        ).values('video_id').annotate(
            score=Count('id') * 0.2 + Coalesce(Sum('value'), 0.0) * 0.1
        ).order_by('-score')[:50]

        scores = {}
        for item in candidate_logs:
            scores[item['video_id']] = float(item['score'])

        return scores

    # ============================================================
    # 策略 3：热门推荐
    # ============================================================

    def _get_trending_scores(self, exclude: set = None) -> Dict[int, float]:
        """
        热门视频推荐

        综合评分公式：
            score = 播放量权重 + 时效权重 + 互动率权重

        适用场景：用户冷启动、未登录用户、推荐结果不足时补充
        """
        exclude = exclude or set()

        # 统计周期：最近 7 天
        recent = self.now - timedelta(days=7)
        scores = {}

        # 获取所有已发布视频，按热度排序
        videos = Video.objects.filter(
            status=Video.StatusChoices.PUBLISHED,
        ).exclude(pk__in=exclude).order_by('-views_count')[:100]

        for video in videos:
            score = 0.0

            # ----- 播放量权重（对数缩放，避免头部效应）-----
            score += math.log(video.views_count + 1) * 0.3

            # ----- 时效权重（越新权重越高）-----
            hours_old = (self.now - video.created_at).total_seconds() / 3600
            if hours_old < 24:          # 24 小时内发布
                score += 2.0
            elif hours_old < 72:        # 3 天内
                score += 1.0
            elif hours_old < 168:       # 7 天内
                score += 0.5
            else:
                score += max(0, 0.3 - hours_old / 720)  # 30 天后衰减到 0

            # ----- 互动率权重（点赞+收藏+评论）/ 播放量 -----
            interactions = video.likes_count + video.favorites_count + video.comments_count
            if video.views_count > 0:
                engagement = interactions / video.views_count
                score += min(engagement * 2, 1.0)  # 上限 1 分

            scores[video.pk] = score

        return scores

    # ============================================================
    # 融合推荐
    # ============================================================

    def _get_hybrid_scores(self, user, video_id=None) -> Dict[int, float]:
        """
        融合推荐：将三种策略的得分加权合并

        权重分配（可根据实际效果调整）：
            - 协同过滤：40%（群体智慧的体现）
            - 内容推荐：35%（个性化匹配）
            - 热门推荐：25%（兜底和多样性）
        """
        weights = {
            'collaborative': 0.40,
            'content': 0.35,
            'trending': 0.25,
        }

        # 计算各策略得分
        collab_scores = self._get_collaborative_scores(user)
        content_scores = self._get_content_based_scores(video_id) if video_id else {}
        trending_scores = self._get_trending_scores()

        # 归一化各策略得分到 0~1 区间
        collab_scores = self._normalize_scores(collab_scores)
        content_scores = self._normalize_scores(content_scores)
        trending_scores = self._normalize_scores(trending_scores)

        # 加权融合
        final_scores = defaultdict(float)
        all_keys = set(collab_scores) | set(content_scores) | set(trending_scores)

        for vid in all_keys:
            final_scores[vid] = (
                collab_scores.get(vid, 0) * weights['collaborative'] +
                content_scores.get(vid, 0) * weights['content'] +
                trending_scores.get(vid, 0) * weights['trending']
            )

        return dict(final_scores)

    # ============================================================
    # 辅助方法
    # ============================================================

    def _has_user_history(self, user) -> bool:
        """判断用户是否有行为历史"""
        return UserActionLog.objects.filter(user=user).exists()

    def _extract_tags_from_video(self, video) -> List[str]:
        """
        从视频中提取标签列表

        优先使用 VideoTagWeight 中的结构化标签，
        其次解析 tags 字段（逗号分隔的字符串）。
        """
        # 先从结构化标签权重表中取
        weighted_tags = VideoTagWeight.objects.filter(
            video=video
        ).order_by('-weight').values_list('tag', flat=True)[:10]

        if weighted_tags:
            return list(weighted_tags)

        # 兜底：从 tags 字段解析
        if video.tags:
            return [t.strip() for t in video.tags.split(',') if t.strip()]

        return []

    def _normalize_scores(self, scores: Dict[int, float]) -> Dict[int, float]:
        """
        将得分归一化到 0~1 区间

        使用 min-max 归一化：x' = (x - min) / (max - min)
        """
        if not scores:
            return {}

        max_val = max(scores.values())
        min_val = min(scores.values())

        if max_val == min_val:
            return {k: 1.0 for k in scores}

        return {
            k: (v - min_val) / (max_val - min_val)
            for k, v in scores.items()
        }

    def log_user_action(self, user, action: str, video=None,
                        search_query='', source='', value=None):
        """
        记录用户行为（由视图层调用）

        参数：
            user:       用户对象
            action:     行为类型（view/like/favorite/comment/share/search/watch）
            video:      关联的视频（可选）
            search_query: 搜索关键词（action=search 时使用）
            source:     来源（index/detail/recommend 等）
            value:      行为数值（默认使用 ACTION_WEIGHTS 中的值）
        """
        if value is None:
            value = self.ACTION_WEIGHTS.get(action, 1.0)

        import logging
        logger = logging.getLogger(__name__)

        try:
            UserActionLog.objects.create(
                user=user if user.is_authenticated else None,
                action=action,
                video=video,
                search_query=search_query[:200],
                source=source[:50],
                value=value,
            )
        except Exception as e:
            logger.warning(f'记录用户行为失败: {e}')

    def get_defaul_recommendations(self, count=12):
        """
        默认推荐（未登录用户）

        从热门视频中选取，加入随机扰动增加多样性。
        """
        return Video.objects.filter(
            status=Video.StatusChoices.PUBLISHED,
        ).order_by('-views_count', '-likes_count')[:count]


# ============================================================
# 单例工厂函数
# ============================================================

_engine_instance = None


def get_recommend_engine() -> RecommendEngine:
    """
    获取推荐引擎单例

    避免每次请求都重新创建 RecommendEngine 对象。
    """
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = RecommendEngine()
    return _engine_instance
