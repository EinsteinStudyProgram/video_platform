"""
============================================================
 用户模块 - URL 路由配置
============================================================
"""
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

# 命名空间名称，用于模板中的 URL 反向解析
app_name = 'users'

urlpatterns = [
    # 用户注册
    path('register/', views.RegisterView.as_view(), name='register'),

    # 用户登录（使用 Django 内置认证视图）
    path('login/', auth_views.LoginView.as_view(
        template_name='users/login.html',
    ), name='login'),

    # 用户退出
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # 个人中心
    path('profile/', views.ProfileView.as_view(), name='profile'),

    # 我的上传
    path('my-videos/', views.MyVideosView.as_view(), name='my_videos'),

    # 我的收藏
    path('my-favorites/', views.MyFavoritesView.as_view(), name='my_favorites'),

    # 密码重置
    path('password-reset/',
         auth_views.PasswordResetView.as_view(
             template_name='users/password_reset.html',
         ),
         name='password_reset'),
    path('password-reset/done/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='users/password_reset_done.html',
         ),
         name='password_reset_done'),
    path('password-reset/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='users/password_reset_confirm.html',
         ),
         name='password_reset_confirm'),
    path('password-reset/complete/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='users/password_reset_complete.html',
         ),
         name='password_reset_complete'),
]
