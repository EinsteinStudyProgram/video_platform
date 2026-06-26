"""
============================================================
 用户模块 - 应用配置
============================================================
"""
from django.apps import AppConfig


class UsersConfig(AppConfig):
    """用户模块应用配置"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.users'
    verbose_name = '用户管理'
