"""
============================================================
 推荐模块 - 数据模型
============================================================
 存储用户行为日志和视频特征向量，用于推荐算法计算。
============================================================
"""
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class UserActionLog(models.Model):
    """
    用户行为日志表

    记录用户在平台上的各种行为，用于推荐算法训练。
    包括浏览、点赞、收藏、评论、分享等行为。

    行为特征（ActionType）：
        - view:    浏览（播放视频，>=30 秒算有效浏览）
        - like:    点赞
        - favorite: 收藏
        - comment:  评论
        - share:   分享
        - search:  搜索关键词
        - watch:   观看时长（秒）

    此表数据量会快速增长，建议：
        1. 3 天内的数据用于实时推荐
        2. 30 天内的数据用于协同过滤
        3. 超过 30 天的数据可归档或降采样
    """

    class ActionType(models.TextChoices):
        VIEW = 'view', _('浏览')
        LIKE = 'like', _('点赞')
        FAVORITE = 'favorite', _('收藏')
        COMMENT = 'comment', _('评论')
        SHARE = 'share', _('分享')
        SEARCH = 'search', _('搜索')
        WATCH_DURATION = 'watch', _('观看时长')

    # 用户
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('用户'),
        on_delete=models.CASCADE,
        related_name='action_logs',
        null=True,        # 匿名用户可为空
        blank=True,
        db_index=True,
    )

    # 行为类型
    action = models.CharField(
        verbose_name=_('行为类型'),
        max_length=20,
        choices=ActionType.choices,
        db_index=True,
    )

    # 目标视频（如果是跟视频相关的行为）
    video = models.ForeignKey(
        'videos.Video',
        verbose_name=_('关联视频'),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='action_logs',
    )

    # 目标分类（如果是分类相关的行为）
    category = models.ForeignKey(
        'videos.Category',
        verbose_name=_('关联分类'),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    # 搜索关键词（action=search 时使用）
    search_query = models.CharField(
        verbose_name=_('搜索关键词'),
        max_length=200,
        blank=True,
        default='',
    )

    # 行为数值（如观看时长秒数、点赞=1等）
    value = models.FloatField(
        verbose_name=_('行为数值'),
        default=1.0,
        help_text='浏览=1, 点赞=2, 收藏=3, 评论=4, 分享=5; 观看时长为实际秒数',
    )

    # 来源页面
    source = models.CharField(
        verbose_name=_('来源'),
        max_length=50,
        blank=True,
        default='',
        help_text='如: index, detail, search, recommend',
    )

    # IP 地址（用于去重和反作弊）
    ip_address = models.GenericIPAddressField(
        verbose_name=_('IP'),
        blank=True,
        null=True,
    )

    # 行为时间
    created_at = models.DateTimeField(
        verbose_name=_('行为时间'),
        auto_now_add=True,
        db_index=True,
    )

    # 客户端信息
    user_agent = models.TextField(
        verbose_name=_('User Agent'),
        blank=True,
        default='',
    )

    class Meta:
        db_table = 'recommend_action_log'
        verbose_name = _('用户行为日志')
        verbose_name_plural = _('用户行为日志')
        ordering = ['-created_at']
        indexes = [
            # 按用户和时间查询的索引
            models.Index(fields=['user', 'created_at'], name='idx_action_user_time'),
            # 按视频和行为类型查询
            models.Index(fields=['video', 'action'], name='idx_action_video_type'),
        ]

    def __str__(self):
        return f'{self.user.username if self.user else "匿名"}: {self.action} - {self.created_at:%H:%M}'


class VideoTagWeight(models.Model):
    """
    视频-标签权重表

    记录视频与标签之间的关联强度，用于基于内容的推荐。
    权重越高，表示该视频在该标签上的特征越显著。

    示例：
        视频 A: Python(0.9), Django(0.8), 教程(0.7)
        视频 B: Python(0.6), 数据分析(0.9)
    """
    video = models.ForeignKey(
        'videos.Video',
        verbose_name=_('视频'),
        on_delete=models.CASCADE,
        related_name='tag_weights',
    )
    tag = models.CharField(
        verbose_name=_('标签'),
        max_length=50,
        db_index=True,
    )
    weight = models.FloatField(
        verbose_name=_('权重'),
        default=0.5,
        help_text='0~1 之间的浮点数，表示视频在该标签上的特征强度',
    )

    class Meta:
        db_table = 'recommend_video_tag_weight'
        verbose_name = _('视频标签权重')
        verbose_name_plural = _('视频标签权重')
        unique_together = ['video', 'tag']
        indexes = [
            models.Index(fields=['tag', 'weight'], name='idx_tag_weight'),
        ]

    def __str__(self):
        return f'{self.video.title[:20]}: {self.tag}({self.weight:.2f})'
