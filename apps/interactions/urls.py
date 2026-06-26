"""
============================================================
 互动模块 - URL 路由配置
============================================================
"""
from django.urls import path
from . import views

app_name = 'interactions'

urlpatterns = [
    # 评论相关
    path('comment/<int:video_id>/', views.CommentView.as_view(), name='comment_list'),
    path('comment/add/', views.CommentCreateView.as_view(), name='comment_add'),
    path('comment/delete/<int:comment_id>/', views.CommentDeleteView.as_view(), name='comment_delete'),

    # 点赞相关
    path('like/toggle/<int:video_id>/', views.LikeToggleView.as_view(), name='like_toggle'),

    # 收藏相关
    path('favorite/toggle/<int:video_id>/', views.FavoriteToggleView.as_view(), name='favorite_toggle'),
]
