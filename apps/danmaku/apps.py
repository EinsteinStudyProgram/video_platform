"""
============================================================
 弹幕模块 - 应用配置
============================================================
"""
from django.apps import AppConfig


class DanmakuConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.danmaku'
    verbose_name = '弹幕管理'
