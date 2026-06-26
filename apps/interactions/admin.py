"""
============================================================
 互动模块 - Django Admin 后台管理
============================================================
 评论审核管理、交互数据概览。
============================================================
"""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Comment, Like, Favorite


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    """
    评论管理界面

    管理员可以审核评论、删除违规评论。
    """
    list_display = [
        'id', 'video_title', 'user_name', 'short_content',
        'is_approved', 'created_at',
    ]
    list_filter = ['is_approved', 'created_at']
    search_fields = ['content', 'user__username', 'video__title']
    list_editable = ['is_approved']      # 列表页直接审核
    list_per_page = 30
    date_hierarchy = 'created_at'

    def video_title(self, obj):
        """显示关联的视频标题"""
        return obj.video.title
    video_title.short_description = _('视频标题')
    video_title.admin_order_field = 'video__title'

    def user_name(self, obj):
        """显示评论者用户名"""
        return obj.user.username
    user_name.short_description = _('评论者')
    user_name.admin_order_field = 'user__username'

    def short_content(self, obj):
        """截断显示评论内容"""
        return obj.content[:50] + ('...' if len(obj.content) > 50 else '')
    short_content.short_description = _('评论内容')


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    """点赞记录（一般只读）"""
    list_display = ['id', 'user', 'video_title', 'created_at']
    search_fields = ['user__username', 'video__title']
    list_per_page = 30
    readonly_fields = ['video', 'user', 'created_at']

    def video_title(self, obj):
        return obj.video.title
    video_title.short_description = _('视频标题')


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    """收藏记录（一般只读）"""
    list_display = ['id', 'user', 'video_title', 'note', 'created_at']
    search_fields = ['user__username', 'video__title', 'note']
    list_per_page = 30

    def video_title(self, obj):
        return obj.video.title
    video_title.short_description = _('视频标题')
