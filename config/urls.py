"""
============================================================
 项目根路由配置 (URL Configuration)
============================================================
 集中管理所有应用的路由分发。
============================================================
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Django Admin 后台管理
    path('admin/', admin.site.urls),

    # 用户模块路由（注册、登录、个人中心）
    path('users/', include('apps.users.urls')),

    # 视频模块路由（上传、播放、列表、分类）
    # 注意：首页（空路径）也包含视频模块路由，但不带 namespace
    path('videos/', include('apps.videos.urls')),
    path('', include('apps.videos.urls')),           # 首页直接使用视频列表（不带 namespace）

    # 互动模块路由（评论、点赞、收藏）
    path('interactions/', include('apps.interactions.urls')),

    # 弹幕模块路由（发送、加载弹幕）
    path('api/danmaku/', include('apps.danmaku.urls')),

    # 推荐模块路由（推荐列表、行为日志）
    path('api/recommend/', include('apps.recommend.urls')),
]

# 开发环境调试模式下提供媒体文件访问服务
# 生产环境应由 Nginx 等反向代理直接处理媒体文件路由
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


