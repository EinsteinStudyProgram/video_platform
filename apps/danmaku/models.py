"""
============================================================
 弹幕模块 - 数据模型
============================================================
 支持弹幕的发送、存储和实时展示。
 每条弹幕包含文本内容、出现时间点和显示位置。
============================================================
"""
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class Danmaku(models.Model):
    """
    弹幕数据表

    每一条弹幕记录都与一个视频关联，包含弹幕内容、
    出现时间点、显示位置和样式等信息。

    前端 DPlayer / ArtPlayer 等播放器支持弹幕渲染。
    """

    class TypeChoices(models.TextChoices):
        """弹幕滚动类型"""
        SCROLL = 'scroll', _('滚动弹幕')       # 从右到左滚动
        TOP = 'top', _('顶部弹幕')             # 固定在顶部
        BOTTOM = 'bottom', _('底部弹幕')        # 固定在底部

    class ColorChoices(models.TextChoices):
        """弹幕常用颜色"""
        WHITE = '#FFFFFF', _('白色')
        RED = '#FF0000', _('红色')
        GREEN = '#00FF00', _('绿色')
        BLUE = '#0000FF', _('蓝色')
        YELLOW = '#FFFF00', _('黄色')
        PINK = '#FF69B4', _('粉色')
        ORANGE = '#FFA500', _('橙色')
        CYAN = '#00FFFF', _('青色')

    # 关联的视频
    video = models.ForeignKey(
        'videos.Video',
        verbose_name=_('关联视频'),
        on_delete=models.CASCADE,
        related_name='danmaku_set',
        db_index=True,
    )

    # 发送弹幕的用户
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('发送用户'),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='danmaku_set',
        help_text='匿名弹幕可为空',
    )

    # 弹幕内容
    content = models.TextField(
        verbose_name=_('弹幕内容'),
        max_length=500,
        help_text='弹幕文本内容（最多 500 字）',
    )

    # 弹幕在视频中出现的时间点（秒）
    time_seconds = models.FloatField(
        verbose_name=_('出现时间(秒)'),
        help_text='弹幕在视频时间轴上的位置（单位：秒，支持小数）',
    )

    # 弹幕类型（滚动/顶部/底部）
    type = models.CharField(
        verbose_name=_('弹幕类型'),
        max_length=10,
        choices=TypeChoices.choices,
        default=TypeChoices.SCROLL,
    )

    # 弹幕颜色（十六进制色值）
    color = models.CharField(
        verbose_name=_('弹幕颜色'),
        max_length=7,
        default=ColorChoices.WHITE,
        help_text='十六进制颜色代码，如 #FF0000',
    )

    # 字体大小（像素）
    font_size = models.IntegerField(
        verbose_name=_('字体大小'),
        default=25,
        help_text='弹幕字体大小（单位：px）',
    )

    # 发送时间
    created_at = models.DateTimeField(
        verbose_name=_('发送时间'),
        auto_now_add=True,
        db_index=True,
    )

    # IP 地址（用于防刷和风控）
    ip_address = models.GenericIPAddressField(
        verbose_name=_('IP 地址'),
        blank=True,
        null=True,
    )

    class Meta:
        db_table = 'danmaku_danmaku'
        verbose_name = _('弹幕')
        verbose_name_plural = _('弹幕')
        ordering = ['time_seconds', 'created_at']
        indexes = [
            # 按视频和时间排序的复合索引，加速弹幕加载
            models.Index(fields=['video', 'time_seconds'], name='idx_danmaku_video_time'),
        ]

    def __str__(self):
        """显示：用户 在 XX 秒 发送了 "内容" """
        return f'{self.user.username if self.user else "匿名"} @{self.time_seconds:.1f}s: {self.content[:30]}'

    def to_dict(self):
        """
        将弹幕对象转换为前端播放器所需的 JSON 格式

        前端 (DPlayer) 格式：
        {
            "time": 1.5,        // 出现时间（秒）
            "type": "scroll",   // 类型：scroll / top / bottom
            "color": "#FFFFFF", // 颜色
            "author": "用户",   // 作者
            "text": "内容"      // 文本
        }
        """
        return {
            'time': round(self.time_seconds, 2),
            'type': self.type,
            'color': self.color,
            'author': self.user.username if self.user else '匿名',
            'text': self.content,
            'font_size': self.font_size,
        }
