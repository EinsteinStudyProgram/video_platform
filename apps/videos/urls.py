"""
============================================================
 视频模块 - URL 路由配置
============================================================
 注意：本 urls.py 会被根路由同时挂载到 /videos/ 和 /（首页）。
 为避免命名空间冲突，不设置 app_name，通过根路由区分命名空间。
"""
from django.urls import path, re_path
from . import views

# 不设置 app_name，因为会被同时挂载到 /videos/ 和 / 路径下
# 在根路由中通过 namespace 参数区分

urlpatterns = [
    # 首页 / 视频列表
    path('', views.VideoListView.as_view(), name='index'),

    # 视频播放页
    path('<int:pk>/', views.VideoDetailView.as_view(), name='detail'),

    # 视频上传
    path('upload/', views.VideoUploadView.as_view(), name='upload'),

    # 分类视频列表
    path('category/<slug:slug>/', views.CategoryVideoListView.as_view(), name='category'),

    # 视频搜索
    path('search/', views.VideoSearchView.as_view(), name='search'),

    # ============================================================
    # 视频流媒体播放路由（支持 HTTP Range 请求）
    # ============================================================
    # 原始分辨率：/videos/stream/1/
    path('stream/<int:video_id>/', views.VideoStreamView.as_view(), name='video_stream'),

    # 指定分辨率：/videos/stream/1/720p/
    path('stream/<int:video_id>/<str:resolution>/',
         views.VideoStreamView.as_view(), name='video_stream_resolution'),

    # ============================================================
    # 视频下载
    # ============================================================
    path('download/<int:video_id>/', views.VideoDownloadView.as_view(), name='video_download'),

    # ============================================================
    # 视频转码状态查询（前端轮询用）
    # ============================================================
    path('status/<int:video_id>/', views.VideoStatusView.as_view(), name='video_status'),

    # ============================================================
    # 分片上传接口（预留）
    # ============================================================
    path('chunked-upload/init/', views.ChunkedUploadInitView.as_view(), name='chunked_upload_init'),
]
