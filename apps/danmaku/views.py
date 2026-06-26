"""
============================================================
 弹幕模块 - 视图（Views）
============================================================
 提供弹幕的 GET（加载）和 POST（发送）接口。
 支持 AJAX 和 JSONP 方式获取弹幕列表。
============================================================
"""
import json
import math
from django.shortcuts import get_object_or_404
from django.views import View
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from apps.videos.models import Video
from .models import Danmaku


class DanmakuListView(View):
    """
    弹幕列表获取接口

    加载指定视频的所有弹幕数据。
    支持根据时间范围分段加载（减少首次加载数据量）。

    GET /api/danmaku/<video_id>/?start=0&end=9999

    返回格式（DPlayer 兼容格式）：
    {
        "code": 0,
        "data": [
            {"time": 1.5, "type": "scroll", "color": "#FFFFFF",
             "author": "用户", "text": "666"},
            ...
        ]
    }
    """
    # 每次最多返回的弹幕数量
    MAX_DANMAKU_LIMIT = 2000

    def get(self, request, video_id):
        # 验证视频是否存在
        video = get_object_or_404(Video, pk=video_id)

        # 解析时间范围参数（可选）
        try:
            start = float(request.GET.get('start', 0))
            end = float(request.GET.get('end', 99999))
        except (ValueError, TypeError):
            start, end = 0, 99999

        # 查询弹幕
        danmaku_list = Danmaku.objects.filter(
            video=video,
            time_seconds__gte=start,
            time_seconds__lte=end,
        ).select_related('user').order_by('time_seconds')[:self.MAX_DANMAKU_LIMIT]

        # 转为前端兼容格式
        data = [d.to_dict() for d in danmaku_list]

        return JsonResponse({
            'code': 0,
            'data': data,
            'total': len(data),
            'video_id': video_id,
        })


@method_decorator(csrf_exempt, name='dispatch')
class DanmakuSendView(LoginRequiredMixin, View):
    """
    弹幕发送接口

    登录用户发送弹幕。
    需要在视频播放页面通过 AJAX POST 调用。

    POST /api/danmaku/send/
    Body: {
        "video_id": 1,
        "content": "666",
        "time": 12.5,
        "type": "scroll",
        "color": "#FFFFFF"
    }
    """
    def post(self, request):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            data = request.POST.dict()

        video_id = data.get('video_id')
        content = data.get('content', '').strip()
        time_seconds = data.get('time')
        danmaku_type = data.get('type', Danmaku.TypeChoices.SCROLL)
        color = data.get('color', Danmaku.ColorChoices.WHITE)
        font_size = data.get('font_size', 25)

        # ---- 参数校验 ----

        # 1. 校验视频
        if not video_id:
            return JsonResponse({'code': 1, 'msg': '缺少视频ID'})
        try:
            video = Video.objects.get(pk=int(video_id))
        except (Video.DoesNotExist, ValueError):
            return JsonResponse({'code': 1, 'msg': '视频不存在'})

        # 2. 校验内容
        if not content:
            return JsonResponse({'code': 1, 'msg': '弹幕不能为空'})
        if len(content) > 500:
            return JsonResponse({'code': 1, 'msg': '弹幕内容不能超过 500 字'})

        # 3. 校验时间
        if time_seconds is None:
            return JsonResponse({'code': 1, 'msg': '缺少弹幕出现时间'})
        try:
            time_seconds = float(time_seconds)
        except (ValueError, TypeError):
            return JsonResponse({'code': 1, 'msg': '时间格式错误'})

        if time_seconds < 0:
            return JsonResponse({'code': 1, 'msg': '弹幕时间不能为负数'})

        # 4. 校验颜色格式
        if color and not color.startswith('#'):
            color = '#' + color

        # ---- 发送频率限制（防刷）----
        # 目前仅检查同 IP 30 秒内发送数量（简单防刷）
        # 生产环境可使用 Redis 或 Django Ratelimit 库
        ip = request.META.get('REMOTE_ADDR', '')
        recent_count = Danmaku.objects.filter(
            ip_address=ip,
            created_at__gte=timezone.now() - timezone.timedelta(seconds=30),
        ).count()

        # 匿名/刚注册用户发送频率限制更严格
        from django.utils import timezone
        if recent_count > 30:
            return JsonResponse({'code': 1, 'msg': '发送频率过快，请稍后再试'})

        # ---- 创建弹幕 ----
        danmaku = Danmaku.objects.create(
            video=video,
            user=request.user if request.user.is_authenticated else None,
            content=content,
            time_seconds=time_seconds,
            type=danmaku_type,
            color=color,
            font_size=int(font_size) if font_size else 25,
            ip_address=ip,
        )

        return JsonResponse({
            'code': 0,
            'msg': '发送成功',
            'data': danmaku.to_dict(),
        })


class DanmakuDeleteView(LoginRequiredMixin, View):
    """
    弹幕删除接口

    允许弹幕发送者或管理员删除弹幕。
    """
    def post(self, request, danmaku_id):
        try:
            danmaku = Danmaku.objects.get(pk=danmaku_id)
        except Danmaku.DoesNotExist:
            return JsonResponse({'code': 1, 'msg': '弹幕不存在'})

        # 仅作者和管理员可删除
        if danmaku.user != request.user and not request.user.is_staff:
            return JsonResponse({'code': 1, 'msg': '无权删除'})

        danmaku.delete()
        return JsonResponse({'code': 0, 'msg': '删除成功'})


class DanmakuClearView(LoginRequiredMixin, View):
    """
    批量清理弹幕（管理员功能）

    清空指定视频的所有弹幕。
    仅管理员可执行。
    """
    def post(self, request, video_id):
        if not request.user.is_staff:
            return JsonResponse({'code': 1, 'msg': '无权限'})

        video = get_object_or_404(Video, pk=video_id)
        count, _ = Danmaku.objects.filter(video=video).delete()

        return JsonResponse({
            'code': 0,
            'msg': f'已删除 {count} 条弹幕',
        })
