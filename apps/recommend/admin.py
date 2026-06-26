"""
============================================================
 推荐模块 - Django Admin 后台管理
============================================================
"""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import UserActionLog, VideoTagWeight


@admin.register(UserActionLog)
class UserActionLogAdmin(admin.ModelAdmin):
    """
    用户行为日志管理
    仅查看和搜索，不支持编辑。
    """
    list_display = [
        'id', 'username', 'action', 'video_title',
        'value', 'source', 'created_at',
    ]
    list_filter = ['action', 'source', 'created_at']
    search_fields = ['user__username', 'video__title', 'search_query']
    list_per_page = 50
    date_hierarchy = 'created_at'
    readonly_fields = [field.name for field in UserActionLog._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def username(self, obj):
        return obj.user.username if obj.user else '匿名'
    username.short_description = _('用户')
    username.admin_order_field = 'user__username'

    def video_title(self, obj):
        return obj.video.title if obj.video else '-'
    video_title.short_description = _('视频')
    video_title.admin_order_field = 'video__title'


@admin.register(VideoTagWeight)
class VideoTagWeightAdmin(admin.ModelAdmin):
    """标签权重管理"""
    list_display = ['video_title', 'tag', 'weight']
    list_filter = ['tag']
    search_fields = ['video__title', 'tag']
    list_editable = ['weight']

    def video_title(self, obj):
        return obj.video.title[:30]
    video_title.short_description = _('视频')
    video_title.admin_order_field = 'video__title'
