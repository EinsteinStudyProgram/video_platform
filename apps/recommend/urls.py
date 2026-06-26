"""
============================================================
 推荐模块 - URL 路由配置
============================================================
"""
from django.urls import path, re_path
from . import views

app_name = 'recommend'

urlpatterns = [
    # 推荐列表
    path('list/', views.RecommendListView.as_view(), name='recommend_list'),

    # 单条行为记录
    path('log/', views.ActionLogView.as_view(), name='action_log'),

    # 批量行为记录
    path('batch-log/', views.BatchActionLogView.as_view(), name='batch_action_log'),
]
