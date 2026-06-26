"""
============================================================
 弹幕模块 - Django Admin 后台管理
============================================================
"""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Danmaku


@admin.register(Danmaku)
class DanmakuAdmin(admin.ModelAdmin):
    """
    弹幕管理界面
    管理员可查看/删除弹幕。
    """
    list_display = [
        'id', 'video_title', 'user_name', 'short_content',
        'time_display', 'type', 'color_display', 'created_at',
    ]
    list_filter = ['type', 'created_at']
    search_fields = ['content', 'video__title', 'user__username']
    list_per_page = 50
    date_hierarchy = 'created_at'

    def video_title(self, obj):
        return obj.video.title
    video_title.short_description = _('视频')
    video_title.admin_order_field = 'video__title'

    def user_name(self, obj):
        return obj.user.username if obj.user else '匿名'
    user_name.short_description = _('用户')
    user_name.admin_order_field = 'user__username'

    def short_content(self, obj):
        return obj.content[:40] + ('...' if len(obj.content) > 40 else '')
    short_content.short_description = _('内容')

    def time_display(self, obj):
        minutes = int(obj.time_seconds // 60)
        seconds = int(obj.time_seconds % 60)
        return f'{minutes:02d}:{seconds:02d}'
    time_display.short_description = _('时间点')

    def color_display(self, obj):
        from django.utils.html import format_html
        return format_html(
            '<span style="display:inline-block;width:16px;height:16px;'
            'border-radius:50%;background:{};border:1px solid #ccc;"></span> {}',
            obj.color, obj.color
        )
    color_display.short_description = _('颜色')
