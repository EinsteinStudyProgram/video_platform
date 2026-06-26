"""
============================================================
 推荐模块 - 视图（Views）
============================================================
 提供推荐视频列表 API，以及行为日志记录接口。
============================================================
"""
from django.http import JsonResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import json

from apps.videos.models import Video
from .engine import get_recommend_engine


class RecommendListView(View):
    """
    推荐视频列表接口

    返回推荐视频的 JSON 数据，供前端异步加载推荐模块使用。

    GET /api/recommend/?count=12
    """
    def get(self, request):
        count = int(request.GET.get('count', 12))
        video_id = request.GET.get('video_id')  # 传入当前视频 ID
        if video_id:
            try:
                video_id = int(video_id)
            except ValueError:
                video_id = None

        engine = get_recommend_engine()

        # 获取推荐视频
        recommended = engine.get_recommendations(
            user=request.user,
            video_id=video_id,
            count=count,
        )

        # 格式化为 JSON
        data = []
        for video in recommended:
            data.append({
                'id': video.pk,
                'title': video.title,
                'thumbnail': video.thumbnail.url if video.thumbnail else None,
                'duration': video.duration_formatted,
                'views_count': video.views_count,
                'uploader': video.uploader.username,
                'url': f'/videos/{video.pk}/',
            })

        return JsonResponse({
            'code': 0,
            'data': data,
            'total': len(data),
        })


@method_decorator(csrf_exempt, name='dispatch')
class ActionLogView(View):
    """
    用户行为记录接口

    前端通过 AJAX 异步上报用户行为。

    POST /api/recommend/log/
    Body: {
        "action": "view",
        "video_id": 1,
        "source": "recommend",
        "value": 1
    }
    """
    def post(self, request):
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            body = request.POST.dict()

        action = body.get('action')
        video_id = body.get('video_id')
        source = body.get('source', '')
        value = body.get('value')

        if not action:
            return JsonResponse({'code': 1, 'msg': '缺少行为类型'})

        video = None
        if video_id:
            try:
                video = Video.objects.get(pk=int(video_id))
            except (Video.DoesNotExist, ValueError):
                pass

        engine = get_recommend_engine()
        engine.log_user_action(
            user=request.user,
            action=action,
            video=video,
            source=source,
            value=float(value) if value else None,
        )

        return JsonResponse({'code': 0, 'msg': 'ok'})


@method_decorator(csrf_exempt, name='dispatch')
class BatchActionLogView(View):
    """
    批量行为记录接口

    用于前端上报多条行为（如批量浏览、批量推荐曝光等）

    POST /api/recommend/batch-log/
    Body: {
        "actions": [
            {"action": "view", "video_id": 1, "source": "recommend"},
            {"action": "view", "video_id": 2, "source": "recommend"},
        ]
    }
    """
    def post(self, request):
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'code': 1, 'msg': 'JSON 格式错误'})

        actions = body.get('actions', [])
        if not actions:
            return JsonResponse({'code': 1, 'msg': '行为列表为空'})

        engine = get_recommend_engine()
        count = 0

        for item in actions:
            action = item.get('action')
            video_id = item.get('video_id')
            source = item.get('source', '')

            video = None
            if video_id:
                try:
                    video = Video.objects.get(pk=int(video_id))
                except (Video.DoesNotExist, ValueError):
                    continue

            engine.log_user_action(
                user=request.user,
                action=action,
                video=video,
                source=source,
            )
            count += 1

        return JsonResponse({'code': 0, 'msg': f'已记录 {count} 条行为'})
