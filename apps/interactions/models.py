"""
============================================================
 互动模块 - 数据模型
============================================================
 包含评论（支持楼中楼回复）、点赞、收藏三大互动功能。
============================================================
"""
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


# ============================================================
# 评论模型（支持楼中楼回复）
# ============================================================
class Comment(models.Model):
    """
    评论表

    支持多层嵌套的楼中楼回复功能，通过 parent 字段实现。
    设计为单层嵌套（即回复只支持一级），避免无限深层嵌套
    带来的性能和维护问题。

    表结构说明：
        - video:    关联的视频
        - user:     发表评论的用户
        - parent:   父评论（为空表示顶级评论，有值表示回复）
        - content:  评论内容
    """
    # 关联的视频（删除视频时级联删除评论）
    video = models.ForeignKey(
        'videos.Video',
        verbose_name=_('关联视频'),
        on_delete=models.CASCADE,
        related_name='comments',
        db_index=True,
        help_text='评论所属的视频',
    )

    # 评论者
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('评论用户'),
        on_delete=models.CASCADE,
        related_name='comments',
        help_text='发表评论的用户',
    )

    # 父评论（实现楼中楼回复）
    # 为空 -> 顶级评论；不为空 -> 对某条评论的回复
    parent = models.ForeignKey(
        'self',
        verbose_name=_('父评论'),
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='replies',
        help_text='回复哪条评论（为空表示顶级评论）',
    )

    # 评论内容
    content = models.TextField(
        verbose_name=_('评论内容'),
        max_length=2000,
        help_text='评论内容（最多 2000 字）',
    )

    # 是否已审核（后台管理审核评论）
    # 为 True 时前台可见，为 False 时仅评论者自己可见
    is_approved = models.BooleanField(
        verbose_name=_('是否审核通过'),
        default=True,     # 开发阶段默认通过，生产环境建议改为 False
        help_text='是否已审核通过，未审核的评论前台不显示',
    )

    # 点赞数（冗余字段，避免每次统计都需要聚合查询）
    likes_count = models.PositiveIntegerField(
        verbose_name=_('点赞数'),
        default=0,
        editable=False,
    )

    # 评论时间
    created_at = models.DateTimeField(
        verbose_name=_('评论时间'),
        auto_now_add=True,
        db_index=True,
    )

    # 最后修改时间
    updated_at = models.DateTimeField(
        verbose_name=_('修改时间'),
        auto_now=True,
    )

    class Meta:
        db_table = 'interactions_comment'
        verbose_name = _('评论')
        verbose_name_plural = _('评论')
        ordering = ['-created_at']

    def __str__(self):
        """简化显示：用户名 评论了 视频标题"""
        return f'{self.user.username} 评论了 "{self.video.title}"'


# ============================================================
# 点赞模型
# ============================================================
class Like(models.Model):
    """
    点赞表

    记录用户对视频的点赞行为。
    一个用户对一个视频只能点赞一次（通过 unique_together 约束）。
    """
    # 点赞的视频
    video = models.ForeignKey(
        'videos.Video',
        verbose_name=_('视频'),
        on_delete=models.CASCADE,
        related_name='likes',
        help_text='被点赞的视频',
    )

    # 点赞的用户
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('用户'),
        on_delete=models.CASCADE,
        related_name='likes',
        help_text='点赞的用户',
    )

    # 点赞时间
    created_at = models.DateTimeField(
        verbose_name=_('点赞时间'),
        auto_now_add=True,
    )

    class Meta:
        db_table = 'interactions_like'
        verbose_name = _('点赞')
        verbose_name_plural = _('点赞')
        # 联合唯一约束：一个用户对一个视频只能点赞一次
        # 用户再次点击即为取消点赞（删除记录）
        constraints = [
            models.UniqueConstraint(
                fields=['video', 'user'],
                name='unique_video_user_like',
                violation_error_message='不能重复点赞同一视频',
            ),
        ]

    def __str__(self):
        return f'{self.user.username} 赞了 "{self.video.title}"'


# ============================================================
# 收藏模型
# ============================================================
class Favorite(models.Model):
    """
    收藏表

    记录用户对视频的收藏行为。
    一个用户对一个视频只能收藏一次。
    """
    # 收藏的视频
    video = models.ForeignKey(
        'videos.Video',
        verbose_name=_('视频'),
        on_delete=models.CASCADE,
        related_name='favorites',
        help_text='被收藏的视频',
    )

    # 收藏的用户
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('用户'),
        on_delete=models.CASCADE,
        related_name='favorites',
        help_text='收藏的用户',
    )

    # 收藏时间
    created_at = models.DateTimeField(
        verbose_name=_('收藏时间'),
        auto_now_add=True,
    )

    # 收藏备注（可选，用户可以添加自己的标签）
    note = models.CharField(
        verbose_name=_('备注'),
        max_length=200,
        blank=True,
        default='',
        help_text='添加个人备注（可选）',
    )

    class Meta:
        db_table = 'interactions_favorite'
        verbose_name = _('收藏')
        verbose_name_plural = _('收藏')
        constraints = [
            models.UniqueConstraint(
                fields=['video', 'user'],
                name='unique_video_user_favorite',
                violation_error_message='不能重复收藏同一视频',
            ),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username} 收藏了 "{self.video.title}"'
