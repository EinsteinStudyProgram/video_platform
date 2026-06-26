"""
============================================================
 视频模块 - 应用配置
============================================================
"""
from django.apps import AppConfig


class VideosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.videos'
    verbose_name = '视频管理'
