"""
============================================================
 视频模块 - Django Admin 后台管理
============================================================
 视频元数据管理、分类管理、评论审核。
============================================================
"""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html

from .models import Category, Video


# ============================================================
# 分类管理
# ============================================================
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """
    视频分类管理界面
    """
    list_display = [
        'name', 'slug', 'parent', 'sort_order',
        'is_active', 'video_count', 'created_at',
    ]
    list_filter = ['is_active']
    search_fields = ['name', 'slug']
    list_editable = ['sort_order', 'is_active']
    prepopulated_fields = {'slug': ('name',)}    # 自动根据名称生成 slug
    list_per_page = 20

    def video_count(self, obj):
        """显示该分类下的视频数量"""
        return obj.videos.count()
    video_count.short_description = _('视频数量')


# ============================================================
# 视频管理
# ============================================================
@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    """
    视频元数据管理界面

    管理员可在此管理视频的上下架、修改元数据等操作。
    """
    # 列表页显示的字段
    # 注意：list_editable 的字段必须在 list_display 中存在
    list_display = [
        'id', 'title', 'uploader_name', 'category_name',
        'status_colored', 'status', 'views_count', 'duration_display',
        'created_at',
    ]
    list_filter = ['status', 'category', 'created_at']
    search_fields = ['title', 'description', 'uploader__username']
    list_per_page = 20
    date_hierarchy = 'created_at'

    # 可点击进入编辑的字段
    list_display_links = ['id', 'title']

    # 列表页可编辑字段（必须在 list_display 中）
    list_editable = ['status']

    # 详情页字段分组
    fieldsets = (
        (_('基本信息'), {
            'fields': (
                'title', 'description', 'category', 'tags',
            ),
        }),
        (_('文件信息'), {
            'fields': (
                'video_file', 'thumbnail', 'duration',
                'file_size', 'transcoded_files',
            ),
        }),
        (_('统计信息'), {
            'fields': (
                'views_count', 'likes_count',
                'favorites_count', 'comments_count',
            ),
        }),
        (_('状态设置'), {
            'fields': (
                'status', 'allow_comment',
            ),
        }),
        (_('关联信息'), {
            'fields': ('uploader',),
        }),
    )

    # 详情页只读字段
    readonly_fields = [
        'views_count', 'likes_count', 'favorites_count',
        'comments_count', 'duration', 'file_size',
        'transcoded_files', 'created_at', 'updated_at',
        'published_at',
    ]

    # ----- 自定义显示方法 -----

    def uploader_name(self, obj):
        return obj.uploader.username
    uploader_name.short_description = _('上传者')
    uploader_name.admin_order_field = 'uploader__username'

    def category_name(self, obj):
        return obj.category.name if obj.category else '-'
    category_name.short_description = _('分类')
    category_name.admin_order_field = 'category__name'

    def status_colored(self, obj):
        """带颜色的状态标签"""
        colors = {
            'pending': 'orange',
            'transcoding': 'blue',
            'published': 'green',
            'failed': 'red',
            'private': 'gray',
            'blocked': 'darkred',
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display(),
        )
    status_colored.short_description = _('状态')
    status_colored.admin_order_field = 'status'

    def duration_display(self, obj):
        return obj.duration_formatted
    duration_display.short_description = _('时长')

    # 操作按钮：批量下架
    actions = ['block_selected_videos', 'publish_selected_videos']

    def block_selected_videos(self, request, queryset):
        """批量下架视频"""
        updated = queryset.update(status=Video.StatusChoices.BLOCKED)
        self.message_user(request, f'已成功下架 {updated} 个视频')
    block_selected_videos.short_description = _('批量下架选中的视频')

    def publish_selected_videos(self, request, queryset):
        """批量发布视频"""
        from django.utils import timezone
        updated = queryset.update(
            status=Video.StatusChoices.PUBLISHED,
            published_at=timezone.now(),
        )
        self.message_user(request, f'已成功发布 {updated} 个视频')
    publish_selected_videos.short_description = _('批量发布选中的视频')
