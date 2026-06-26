"""
============================================================
 弹幕模块 - URL 路由配置
============================================================
"""
from django.urls import path
from . import views

app_name = 'danmaku'

urlpatterns = [
    # 弹幕列表（GET）
    path('list/<int:video_id>/', views.DanmakuListView.as_view(), name='danmaku_list'),

    # 发送弹幕（POST）
    path('send/', views.DanmakuSendView.as_view(), name='danmaku_send'),

    # 删除单条弹幕（POST）
    path('delete/<int:danmaku_id>/', views.DanmakuDeleteView.as_view(), name='danmaku_delete'),

    # 清空视频的所有弹幕（POST，仅管理员）
    path('clear/<int:video_id>/', views.DanmakuClearView.as_view(), name='danmaku_clear'),
]
