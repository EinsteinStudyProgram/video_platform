"""
============================================================
 用户模块 - Django Admin 后台管理
============================================================
 后台管理界面配置，方便管理员管理用户数据。
============================================================
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """
    自定义用户管理界面

    继承 Django 内置 UserAdmin，在其基础上添加自定义字段。
    """
    # 列表页显示的字段
    list_display = [
        'username', 'email', 'phone', 'gender',
        'is_active', 'is_staff', 'date_joined',
    ]
    list_filter = ['is_active', 'is_staff', 'gender', 'date_joined']
    search_fields = ['username', 'email', 'phone']
    ordering = ['-date_joined']

    # 列表页可点击编辑的字段
    list_display_links = ['username', 'email']

    # 每页显示条目数
    list_per_page = 20

    # 编辑页字段分组
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('个人信息'), {
            'fields': (
                'avatar', 'bio', 'phone', 'gender',
                'birthday', 'website',
            ),
        }),
        (_('联系方式'), {
            'fields': ('email',),
        }),
        (_('权限'), {
            'fields': (
                'is_active', 'is_staff', 'is_superuser',
                'groups', 'user_permissions',
            ),
        }),
        (_('重要日期'), {
            'fields': ('last_login', 'date_joined'),
        }),
    )

    # 新增用户时的表单字段
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username', 'email', 'password1', 'password2',
            ),
        }),
    )
