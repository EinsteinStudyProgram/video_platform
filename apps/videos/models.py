"""
============================================================
 视频核心模块 - 数据模型
============================================================
 包含视频分类、视频信息两大模型。
 视频文件上传后触发 Celery 异步转码任务。
============================================================
"""
import os
import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


# ============================================================
# 视频分类模型
# ============================================================
class Category(models.Model):
    """
    视频分类表

    用于对视频内容进行分类组织，支持无限极分类（通过 parent 自关联）。
    例如：科技 > 编程教程 > Python
    """
    # 分类名称（如：科技、教育、娱乐、音乐）
    name = models.CharField(
        verbose_name=_('分类名称'),
        max_length=50,
        unique=True,
        help_text='例如：科技、教育、娱乐、音乐',
    )

    # 分类别名（用于 URL 友好显示，如：technology）
    slug = models.SlugField(
        verbose_name=_('URL别名'),
        max_length=100,
        unique=True,
        help_text='用于 URL 中代替中文名称，如 "technology"',
    )

    # 父级分类（支持无限极子分类，空表示顶级分类）
    parent = models.ForeignKey(
        'self',
        verbose_name=_('父级分类'),
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='children',
        help_text='选择父分类，留空则为顶级分类',
    )

    # 分类描述
    description = models.TextField(
        verbose_name=_('分类描述'),
        max_length=500,
        blank=True,
        default='',
    )

    # 分类图标（可选，显示在分类导航中）
    icon = models.CharField(
        verbose_name=_('图标CSS类'),
        max_length=100,
        blank=True,
        default='',
        help_text='Bootstrap Icons 等 CSS 类名',
    )

    # 排序序号（数字越小越靠前）
    sort_order = models.IntegerField(
        verbose_name=_('排序序号'),
        default=0,
        help_text='数字越小，排列越靠前',
    )

    # 是否启用（禁用后前台不显示）
    is_active = models.BooleanField(
        verbose_name=_('是否启用'),
        default=True,
    )

    # 创建时间
    created_at = models.DateTimeField(
        verbose_name=_('创建时间'),
        auto_now_add=True,
    )

    class Meta:
        db_table = 'videos_category'
        verbose_name = _('视频分类')
        verbose_name_plural = _('视频分类')
        ordering = ['sort_order', 'id']

    def __str__(self):
        """显示完整分类路径，如：科技 > 编程 > Python"""
        if self.parent:
            return f'{self.parent} > {self.name}'
        return self.name


# ============================================================
# 视频文件上传路径生成函数
# ============================================================
def video_file_upload_path(instance, filename):
    """
    视频文件上传路径
    按上传日期和用户 ID 分目录存储：
        media/videos/{year}/{month}/{user_id}/{uuid}_{filename}
    """
    now = timezone.now()
    ext = filename.split('.')[-1]
    # 使用 UUID 前缀防止文件名冲突
    unique_filename = f'{uuid.uuid4().hex[:12]}_{instance.uploader_id}_{now.timestamp()}.{ext}'
    return os.path.join(
        'videos',
        str(now.year),
        str(now.month),
        unique_filename,
    )


def video_thumbnail_upload_path(instance, filename):
    """
    视频封面/缩略图上传路径
        media/thumbnails/{year}/{month}/{uuid}_{filename}
    """
    now = timezone.now()
    ext = filename.split('.')[-1]
    unique_filename = f'{uuid.uuid4().hex[:12]}.{ext}'
    return os.path.join(
        'thumbnails',
        str(now.year),
        str(now.month),
        unique_filename,
    )


# ============================================================
# 视频核心模型
# ============================================================
class Video(models.Model):
    """
    视频核心表

    存储视频的元数据信息，包括标题、描述、文件路径、
    封面图、上传者、播放量等核心字段。

    视频文件上传后，Celery 异步任务会自动进行转码和缩略图提取。
    """
    class StatusChoices(models.TextChoices):
        """视频状态"""
        PENDING = 'pending', _('待转码')       # 刚上传，等待转码
        TRANSCODING = 'transcoding', _('转码中')  # 正在转码
        PUBLISHED = 'published', _('已发布')     # 转码完成，已发布
        FAILED = 'failed', _('转码失败')        # 转码出错
        PRIVATE = 'private', _('私密')         # 仅上传者可见
        BLOCKED = 'blocked', _('已下架')        # 管理员下架

    # ----- 基本信息 -----
    title = models.CharField(
        verbose_name=_('视频标题'),
        max_length=200,
        help_text='请填写视频标题（最多 200 字）',
    )

    description = models.TextField(
        verbose_name=_('视频描述'),
        max_length=5000,
        blank=True,
        default='',
        help_text='详细描述视频内容（支持 Markdown 格式，最多 5000 字）',
    )

    # ----- 分类关联 -----
    category = models.ForeignKey(
        Category,
        verbose_name=_('所属分类'),
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='videos',
        help_text='选择视频所属分类',
    )

    # 标签：简单的逗号分隔存储（如需复杂标签系统可建多对多关系表）
    tags = models.CharField(
        verbose_name=_('标签'),
        max_length=500,
        blank=True,
        default='',
        help_text='多个标签用逗号分隔，如：Python, Django, 教程',
    )

    # ----- 文件与媒体 -----
    # 原始视频文件（用户上传的源文件）
    video_file = models.FileField(
        verbose_name=_('视频源文件'),
        upload_to=video_file_upload_path,
        help_text='支持的格式：MP4, MOV, AVI, MKV',
    )

    # 视频封面图（从视频中提取的第一帧或用户自定义上传）
    thumbnail = models.ImageField(
        verbose_name=_('封面图'),
        upload_to=video_thumbnail_upload_path,
        blank=True,
        null=True,
        help_text='建议尺寸 16:9，如 1280x720 像素',
    )

    # 视频时长（秒）
    duration = models.FloatField(
        verbose_name=_('视频时长'),
        default=0.0,
        help_text='视频时长（秒），上传时由 FFprobe 自动获取',
    )

    # 视频大小（字节）
    file_size = models.BigIntegerField(
        verbose_name=_('文件大小'),
        default=0,
        help_text='文件大小（字节）',
    )

    # ----- 转码后的多分辨率视频文件路径 -----
    # 存储为 JSON 格式，如：
    #   {"480p": "/media/videos/xxx_480p.mp4", "720p": "/media/videos/xxx_720p.mp4"}
    transcoded_files = models.JSONField(
        verbose_name=_('转码文件'),
        default=dict,
        blank=True,
        help_text='存储转码后各分辨率文件的路径',
    )

    # ----- 统计数据 -----
    views_count = models.PositiveIntegerField(
        verbose_name=_('播放量'),
        default=0,
        help_text='视频被播放的次数',
    )

    likes_count = models.PositiveIntegerField(
        verbose_name=_('点赞数'),
        default=0,
        editable=False,
        help_text='通过点赞记录实时统计',
    )

    favorites_count = models.PositiveIntegerField(
        verbose_name=_('收藏数'),
        default=0,
        editable=False,
        help_text='通过收藏记录实时统计',
    )

    comments_count = models.PositiveIntegerField(
        verbose_name=_('评论数'),
        default=0,
        editable=False,
        help_text='通过评论记录实时统计',
    )

    # ----- 状态与权限 -----
    status = models.CharField(
        verbose_name=_('状态'),
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.PENDING,
        db_index=True,           # 添加数据库索引，提高按状态查询的效率
    )

    # 是否允许评论
    allow_comment = models.BooleanField(
        verbose_name=_('允许评论'),
        default=True,
    )

    # ----- 关联用户 -----
    uploader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('上传者'),
        on_delete=models.CASCADE,            # 用户删除时，其上传的视频也一并删除
        related_name='videos_uploaded',
        help_text='视频的上传用户',
    )

    # ----- 时间戳 -----
    created_at = models.DateTimeField(
        verbose_name=_('上传时间'),
        auto_now_add=True,
        db_index=True,                       # 排序常用字段，加索引优化性能
    )

    updated_at = models.DateTimeField(
        verbose_name=_('最后修改时间'),
        auto_now=True,
    )

    # 发布时间（状态变为已发布时记录）
    published_at = models.DateTimeField(
        verbose_name=_('发布时间'),
        blank=True,
        null=True,
    )

    class Meta:
        db_table = 'videos_video'
        verbose_name = _('视频')
        verbose_name_plural = _('视频')
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        """
        重写 save 方法：
        当状态变为 "已发布" 时，自动记录发布时间
        """
        if self.status == self.StatusChoices.PUBLISHED and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    @property
    def duration_formatted(self):
        """
        格式化视频时长
        返回格式：HH:MM:SS 或 MM:SS
        """
        if not self.duration:
            return '00:00'
        total_seconds = int(self.duration)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        if hours > 0:
            return f'{hours:02d}:{minutes:02d}:{seconds:02d}'
        return f'{minutes:02d}:{seconds:02d}'

    @property
    def file_size_display(self):
        """
        格式化文件大小显示
        返回如：102.5 MB
        """
        if not self.file_size:
            return '未知'
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f'{size:.1f} {unit}'
            size /= 1024
        return f'{size:.1f} PB'
