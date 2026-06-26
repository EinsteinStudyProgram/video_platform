"""
============================================================
 视频模块 - 视图（Views）
============================================================
 核心功能：视频上传（含安全校验）、播放、列表、分类、搜索。
 技术难点：文件类型校验、播放量统计、异步转码触发。
============================================================
"""
import os
import json
import uuid
import logging
from typing import Any, Dict

from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponse, FileResponse, Http404
from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Q, Count, F
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from .models import Video, Category
from .utils import validate_video_file, get_video_metadata

# 导入 Celery 任务（延迟导入，避免循环引用）
from .tasks import process_video_task

logger = logging.getLogger(__name__)


# ============================================================
# 首页 - 视频列表
# ============================================================
class VideoListView(ListView):
    """
    首页 - 视频列表
    展示所有已发布的视频，支持分页浏览。
    """
    model = Video
    template_name = 'videos/index.html'
    context_object_name = 'videos'
    paginate_by = 12  # 每页 12 个视频

    def get_queryset(self):
        """只获取已发布的视频，使用 select_related 优化关联查询"""
        return Video.objects.filter(
            status=Video.StatusChoices.PUBLISHED
        ).select_related('uploader', 'category').order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # 热门视频：按播放量倒序
        context['hot_videos'] = Video.objects.filter(
            status=Video.StatusChoices.PUBLISHED
        ).order_by('-views_count')[:8]
        return context


# ============================================================
# 分类视频列表
# ============================================================
class CategoryVideoListView(ListView):
    """
    分类视频列表
    按分类筛选视频。
    """
    model = Video
    template_name = 'videos/index.html'
    context_object_name = 'videos'
    paginate_by = 12

    def get_queryset(self):
        self.category = get_object_or_404(Category, slug=self.kwargs['slug'])
        return Video.objects.filter(
            status=Video.StatusChoices.PUBLISHED,
            category=self.category,
        ).select_related('uploader', 'category').order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_category'] = self.category
        return context


# ============================================================
# 视频搜索
# ============================================================
class VideoSearchView(ListView):
    """
    视频搜索
    支持按标题、描述、标签搜索。
    """
    model = Video
    template_name = 'videos/index.html'
    context_object_name = 'videos'
    paginate_by = 12

    def get_queryset(self):
        query = self.request.GET.get('q', '').strip()
        if query:
            return Video.objects.filter(
                Q(status=Video.StatusChoices.PUBLISHED),
                Q(title__icontains=query) |
                Q(description__icontains=query) |
                Q(tags__icontains=query),
            ).select_related('uploader', 'category').order_by('-created_at')
        return Video.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        return context


# ============================================================
# 视频播放页（核心功能）
# ============================================================
class VideoDetailView(DetailView):
    """
    视频播放页

    展示视频播放器、详细信息、评论等。
    播放量 +1 使用 F 表达式避免并发问题。
    """
    model = Video
    template_name = 'videos/detail.html'

    def get_object(self, queryset=None):
        video = super().get_object(queryset)

        # 播放量 +1（使用 F 表达式保证并发安全）
        Video.objects.filter(pk=video.pk).update(views_count=F('views_count') + 1)
        # 重新从数据库读取以获取更新后的值
        video.refresh_from_db()

        return video

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        video = self.object



        # 推荐视频（使用推荐引擎：内容+协同+热门融合）
        from apps.recommend.engine import get_recommend_engine
        engine = get_recommend_engine()
        recommended = engine.get_recommendations(
            user=self.request.user,
            video_id=video.pk,
            count=6,
        )
        context['recommended'] = recommended

        # 热门视频（作为侧边栏补充）
        context['trending'] = Video.objects.filter(
            status=Video.StatusChoices.PUBLISHED,


        ).order_by('-views_count')[:6]

        # 用户是否已点赞/收藏（用于前端按钮状态）
        if self.request.user.is_authenticated:
            from apps.interactions.models import Like, Favorite
            context['user_liked'] = Like.objects.filter(
                video=video, user=self.request.user
            ).exists()
            context['user_favorited'] = Favorite.objects.filter(
                video=video, user=self.request.user
            ).exists()
            # 记录浏览行为到推荐引擎
            engine.log_user_action(
                user=self.request.user,
                action='view',
                video=video,
                source='detail',
            )
        else:
            context['user_liked'] = False
            context['user_favorited'] = False

        return context


# ============================================================
# 视频上传（核心功能 - 含安全校验）
# ============================================================
class VideoUploadView(LoginRequiredMixin, View):
    """
    视频上传页

    上传流程：
        1. GET 请求：展示上传表单
        2. POST 请求：校验文件 -> 保存到数据库 -> 触发异步转码

    安全校验：
        - 文件扩展名白名单（仅 mp4/mov/avi 等）
        - 文件大小限制（最大 2GB）
        - MIME 类型检查
        - CSRF 保护（Django 默认启用）
    """
    template_name = 'videos/upload.html'

    def get(self, request):
        """GET 请求：展示上传表单"""
        categories = Category.objects.filter(is_active=True)
        return render(request, self.template_name, {
            'categories': categories,
            'max_file_size': settings.FILE_UPLOAD_MAX_MEMORY_SIZE,
            'allowed_extensions': ['.mp4', '.mov', '.avi', '.mkv', '.webm'],
        })

    def post(self, request):
        """
        POST 请求：处理视频上传

        处理流程：
            1. 文件安全校验（扩展名、大小、MIME）
            2. 表单数据校验（标题、分类）
            3. 保存 Video 记录到数据库
            4. 触发 Celery 异步转码任务
            5. 返回成功响应
        """
        # ---- 步骤 1：获取表单数据 ----
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        category_id = request.POST.get('category')
        tags = request.POST.get('tags', '').strip()
        video_file = request.FILES.get('video_file')

        # ---- 步骤 2：表单数据基本校验 ----
        errors = []

        if not title:
            errors.append('视频标题不能为空')
        elif len(title) > 200:
            errors.append('视频标题不能超过 200 个字')

        if not video_file:
            errors.append('请选择要上传的视频文件')

        if errors:
            for error in errors:
                messages.error(request, error)
            return self._render_form(request, title, description, category_id, tags)

        # ---- 步骤 3：视频文件安全校验 ----
        try:
            validate_video_file(video_file)
        except ValidationError as e:
            for error in e.messages:
                messages.error(request, error)
            return self._render_form(request, title, description, category_id, tags)

        # ---- 步骤 4：解析分类 ----
        category = None
        if category_id:
            try:
                category = Category.objects.get(pk=int(category_id), is_active=True)
            except (Category.DoesNotExist, ValueError):
                messages.warning(request, '所选分类不存在，已使用默认分类')

        # ---- 步骤 5：保存视频记录到数据库 ----
        try:
            video = Video(
                title=title,
                description=description,
                category=category,
                tags=tags,
                video_file=video_file,      # Django 自动处理文件存储
                uploader=request.user,
                # 文件大小由后续 FFprobe 提取，此处先设为文件实际大小
                file_size=video_file.size,
                status=Video.StatusChoices.PENDING,
            )
            video.save()
            logger.info(f'视频记录已创建: id={video.id}, title="{title}", '
                        f'size={video_file.size / 1024 / 1024:.1f}MB')

        except Exception as e:
            logger.exception(f'视频记录创建失败: {e}')
            messages.error(request, '视频上传失败，请稍后重试')
            return self._render_form(request, title, description, category_id, tags)

        # ---- 步骤 6：触发 Celery 异步转码任务 ----
        try:
            # 异步执行视频处理任务
            # 包括：元数据提取、缩略图生成、多分辨率转码
            process_video_task.delay(video.id)
            logger.info(f'Celery 转码任务已触发: video_id={video.id}')
        except Exception as e:
            # Celery 调度失败不应阻塞用户操作
            # 视频状态保持 "待转码"，后续可通过管理后台手动重试
            logger.error(f'Celery 任务调度失败: {e}')
            messages.warning(request, '视频已上传，转码任务将在稍后自动开始')

        # ---- 步骤 7：返回成功响应 ----
        messages.success(
            request,
            f'🎉 视频《{title}》上传成功！正在后台转码处理，请稍后查看。'
        )
        return redirect('detail', pk=video.id)

    def _render_form(self, request, title='', description='',
                     category_id=None, tags=''):
        """
        辅助方法：表单校验失败时重新渲染上传页面（保留用户已填数据）
        """
        categories = Category.objects.filter(is_active=True)
        return render(request, self.template_name, {
            'categories': categories,
            'form_data': {
                'title': title,
                'description': description,
                'category_id': category_id,
                'tags': tags,
            },
        })


# ============================================================
# 视频流媒体播放（支持 Range 请求）
# ============================================================
class VideoStreamView(View):
    """
    视频流媒体播放视图

    支持 HTTP Range 请求头，实现：
        - 视频进度条拖拽（跳转到任意位置播放）
        - 分块加载（用户拖动进度条时只传输所需部分）
        - 节省带宽（无需每次都从头加载完整视频）

    这是实现视频流媒体播放的核心技术。

    Nginx 生产环境部署时，建议直接由 Nginx 处理视频文件，
    Django 只负责权限校验，配置参考：
        location /media/videos/ {
            alias /path/to/media/videos/;
            add_header Accept-Ranges bytes;
        }
    """

    def get(self, request, video_id, resolution=None):
        """
        处理视频流请求

        参数：
            video_id:   视频 ID
            resolution: 分辨率标识（如 480p, 720p, 1080p）
                        为空时返回原始视频文件
        """
        # ---- 步骤 1：获取视频对象 ----
        video = get_object_or_404(Video, pk=video_id)

        # 权限检查：未发布或已下架的视频，仅上传者和管理员可访问
        if video.status not in [Video.StatusChoices.PUBLISHED]:
            if not request.user.is_authenticated or \
               (request.user != video.uploader and not request.user.is_staff):
                raise Http404(_('视频不存在或无权访问'))

        # ---- 步骤 2：确定要播放的视频文件路径 ----
        if resolution and resolution in video.transcoded_files:
            # 如果指定了分辨率且有转码文件，播放转码版本
            file_relative_path = video.transcoded_files[resolution]
        else:
            # 否则播放原始文件
            file_relative_path = video.video_file.name

        # 构建文件的完整物理路径
        file_path = os.path.join(settings.MEDIA_ROOT, file_relative_path)

        # 检查文件是否存在
        if not os.path.exists(file_path):
            logger.warning(f'视频文件不存在: {file_path}')
            raise Http404(_('视频文件不存在'))

        # ---- 步骤 3：获取文件信息 ----
        file_size = os.path.getsize(file_path)
        content_type = self._guess_content_type(file_relative_path)

        # ---- 步骤 4：处理 HTTP Range 请求（实现进度条拖拽） ----
        range_header = request.META.get('HTTP_RANGE', '').strip()

        if range_header:
            return self._handle_range_request(
                file_path, file_size, content_type, range_header
            )

        # ---- 步骤 5：无 Range 请求头，返回完整文件 ----
        response = FileResponse(
            open(file_path, 'rb'),
            content_type=content_type,
        )
        response['Content-Length'] = file_size
        response['Accept-Ranges'] = 'bytes'  # 告知客户端支持 Range 请求
        response['Content-Disposition'] = 'inline'
        return response

    def _handle_range_request(self, file_path, file_size, content_type, range_header):
        """
        处理 HTTP Range 请求（核心方法）

        HTTP Range 协议说明：
            - 客户端请求头: Range: bytes=<start>-<end>
            - 服务端响应头: Content-Range: bytes <start>-<end>/<total>
            - 状态码: 206 Partial Content

        这个机制使得视频播放器可以只请求文件的某一部分，
        从而实现进度条拖拽而不重新加载整个视频。
        """
        import re

        # 解析 Range 头，格式如: bytes=0-1023
        range_match = re.match(r'bytes=(\d+)-(\d*)', range_header)
        if not range_match:
            # 无法解析 Range 头，返回完整文件
            response = FileResponse(
                open(file_path, 'rb'),
                content_type=content_type,
                status=206,
            )
            response['Content-Length'] = file_size
            response['Content-Range'] = f'bytes */{file_size}'
            return response

        start = int(range_match.group(1))
        end_str = range_match.group(2)
        end = int(end_str) if end_str else file_size - 1

        # 参数校验
        if start >= file_size or end >= file_size:
            # 请求范围超出文件大小，返回 416 Range Not Satisfiable
            response = HttpResponse(status=416)
            response['Content-Range'] = f'bytes */{file_size}'
            return response

        # 计算要发送的数据块大小
        chunk_size = (end - start) + 1

        # 打开文件并定位到 start 位置
        file = open(file_path, 'rb')
        file.seek(start)

        # 创建只返回指定范围的响应
        response = HttpResponse(
            file.read(chunk_size),
            content_type=content_type,
            status=206,  # 206 Partial Content
        )
        response['Content-Length'] = chunk_size
        response['Content-Range'] = f'bytes {start}-{end}/{file_size}'
        response['Accept-Ranges'] = 'bytes'
        response['Content-Disposition'] = 'inline'
        response['Cache-Control'] = 'no-cache'

        return response

    def _guess_content_type(self, file_path: str) -> str:
        """
        根据文件扩展名猜测 MIME 类型
        """
        ext = os.path.splitext(file_path)[1].lower()
        mime_map = {
            '.mp4': 'video/mp4',
            '.mov': 'video/quicktime',
            '.avi': 'video/x-msvideo',
            '.mkv': 'video/x-matroska',
            '.webm': 'video/webm',
            '.flv': 'video/x-flv',
            '.wmv': 'video/x-ms-wmv',
        }
        return mime_map.get(ext, 'application/octet-stream')


# ============================================================
# 视频文件下载
# ============================================================
class VideoDownloadView(LoginRequiredMixin, View):
    """
    视频下载视图
    允许登录用户下载已发布的视频。
    """
    def get(self, request, video_id):
        video = get_object_or_404(Video, pk=video_id, status=Video.StatusChoices.PUBLISHED)

        file_path = os.path.join(settings.MEDIA_ROOT, video.video_file.name)
        if not os.path.exists(file_path):
            raise Http404(_('文件不存在'))

        response = FileResponse(
            open(file_path, 'rb'),
            as_attachment=True,
            filename=os.path.basename(video.video_file.name),
        )
        return response


# ============================================================
# video_status — 查询视频转码状态（用于前端轮询）
# ============================================================
class VideoStatusView(LoginRequiredMixin, View):
    """
    查询视频转码状态

    前端在上传后可以轮询此接口，显示转码进度。
    返回 JSON 格式的状态信息。
    """
    def get(self, request, video_id):
        video = get_object_or_404(
            Video, pk=video_id, uploader=request.user
        )
        return JsonResponse({
            'id': video.id,
            'status': video.status,
            'status_display': video.get_status_display(),
            'duration': video.duration,
            'thumbnail_url': video.thumbnail.url if video.thumbnail else None,
            'transcoded_files': video.transcoded_files,
        })


# ============================================================
# 分片上传 — 初始化（预留接口）
# ============================================================
class ChunkedUploadInitView(LoginRequiredMixin, View):
    """
    分片上传 - 初始化（预留接口）

    分片上传流程：
        1. 客户端将大文件分割为多个 5MB-10MB 的分片
        2. 调用此接口获取 upload_id
        3. 逐片上传（每个分片携带 upload_id + part_number）
        4. 所有分片上传完成后调用合并接口

    适用于超大文件（> 2GB）的断点续传场景。
    完整实现需要配合前端和临时文件存储。

    返回：
        {
            "upload_id": "uuid",
            "chunk_size": 5242880,
            "expires_in": 3600
        }
    """
    def post(self, request):
        file_name = request.POST.get('file_name', '')
        file_size = request.POST.get('file_size', 0)

        if not file_name or not file_size:
            return JsonResponse({'error': '缺少文件信息'}, status=400)

        # 生成唯一上传 ID
        upload_id = str(uuid.uuid4())

        return JsonResponse({
            'upload_id': upload_id,
            'chunk_size': 5 * 1024 * 1024,  # 5MB 每片
            'expires_in': 3600,              # 1 小时有效期
        })
