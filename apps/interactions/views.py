"""
============================================================
 互动模块 - 视图（Views）
============================================================
 处理评论发表、点赞切换、收藏切换等 AJAX 交互。
============================================================
"""
import json
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.db.models import F

from .models import Comment, Like, Favorite
from apps.videos.models import Video


class CommentView(View):
    """
    评论列表
    获取视频的所有已审核评论。
    支持 AJAX 请求返回 JSON 数据。
    """
    def get(self, request, video_id):
        video = get_object_or_404(Video, pk=video_id)
        comments = Comment.objects.filter(
            video=video,
            is_approved=True,
            parent=None,  # 只获取顶级评论
        ).select_related('user').order_by('-created_at')[:50]

        # AJAX 请求返回 JSON
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            data = []
            for comment in comments:
                replies = comment.replies.filter(is_approved=True).select_related('user')
                data.append({
                    'id': comment.id,
                    'user': comment.user.username,
                    'avatar': comment.user.avatar_url,
                    'content': comment.content,
                    'created_at': comment.created_at.strftime('%Y-%m-%d %H:%M'),
                    'likes_count': comment.likes_count,
                    'replies': [{
                        'id': reply.id,
                        'user': reply.user.username,
                        'avatar': reply.user.avatar_url,
                        'content': reply.content,
                        'created_at': reply.created_at.strftime('%Y-%m-%d %H:%M'),
                    } for reply in replies],
                })
            return JsonResponse({'code': 0, 'data': data})

        return JsonResponse({'code': 0, 'data': list(comments.values())})


class CommentCreateView(LoginRequiredMixin, View):
    """
    发表评论
    支持顶级评论和回复评论。
    """
    def post(self, request):
        video_id = request.POST.get('video_id')
        content = request.POST.get('content', '').strip()
        parent_id = request.POST.get('parent_id')

        if not content:
            return JsonResponse({'code': 1, 'msg': '评论内容不能为空'})
        if len(content) > 2000:
            return JsonResponse({'code': 1, 'msg': '评论内容不能超过 2000 字'})

        video = get_object_or_404(Video, pk=video_id)

        parent = None
        if parent_id:
            parent = get_object_or_404(Comment, pk=parent_id)

        comment = Comment.objects.create(
            video=video,
            user=request.user,
            content=content,
            parent=parent,
        )

        # 更新视频的评论计数
        Video.objects.filter(pk=video_id).update(
            comments_count=F('comments_count') + 1
        )

        return JsonResponse({
            'code': 0,
            'msg': '评论成功',
            'data': {
                'id': comment.id,
                'user': request.user.username,
                'content': comment.content,
                'created_at': comment.created_at.strftime('%Y-%m-%d %H:%M'),
            },
        })


class CommentDeleteView(LoginRequiredMixin, View):
    """删除评论"""
    def post(self, request, comment_id):
        comment = get_object_or_404(Comment, pk=comment_id, user=request.user)
        video_id = comment.video_id
        comment.delete()

        # 更新视频的评论计数
        Video.objects.filter(pk=video_id).update(
            comments_count=F('comments_count') - 1
        )

        return JsonResponse({'code': 0, 'msg': '评论已删除'})


class LikeToggleView(LoginRequiredMixin, View):
    """
    点赞/取消点赞
    如果已点赞则取消（toggle 开关）。
    """
    def post(self, request, video_id):
        video = get_object_or_404(Video, pk=video_id)

        like, created = Like.objects.get_or_create(
            video=video,
            user=request.user,
        )

        if created:
            # 新增点赞
            Video.objects.filter(pk=video_id).update(
                likes_count=F('likes_count') + 1
            )
            return JsonResponse({
                'code': 0,
                'action': 'liked',
                'likes_count': video.likes_count + 1,
            })
        else:
            # 取消点赞
            like.delete()
            Video.objects.filter(pk=video_id).update(
                likes_count=F('likes_count') - 1
            )
            return JsonResponse({
                'code': 0,
                'action': 'unliked',
                'likes_count': max(0, video.likes_count - 1),
            })


class FavoriteToggleView(LoginRequiredMixin, View):
    """
    收藏/取消收藏
    如果已收藏则取消（toggle 开关）。
    """
    def post(self, request, video_id):
        video = get_object_or_404(Video, pk=video_id)

        fav, created = Favorite.objects.get_or_create(
            video=video,
            user=request.user,
        )

        if created:
            Video.objects.filter(pk=video_id).update(
                favorites_count=F('favorites_count') + 1
            )
            return JsonResponse({
                'code': 0,
                'action': 'favorited',
                'favorites_count': video.favorites_count + 1,
            })
        else:
            fav.delete()
            Video.objects.filter(pk=video_id).update(
                favorites_count=F('favorites_count') - 1
            )
            return JsonResponse({
                'code': 0,
                'action': 'unfavorited',
                'favorites_count': max(0, video.favorites_count - 1),
            })
