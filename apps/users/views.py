"""
============================================================
 用户模块 - 视图（Views）
============================================================
 处理注册、登录、个人中心等用户相关页面。
============================================================
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import login, authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.utils.translation import gettext_lazy as _

from .models import CustomUser
from apps.videos.models import Video


class RegisterView(View):
    """
    用户注册
    处理新用户注册表单提交。

    密码要求：
        - 最少 8 位
        - 必须包含大写字母（A-Z）
        - 必须包含小写字母（a-z）
        - 不能与用户名/邮箱过于相似
        - 不能是常见弱密码
    """
    template_name = 'users/register.html'

    def get(self, request):
        # 已登录用户跳转到首页
        if request.user.is_authenticated:
            return redirect('videos:index')
        return render(request, self.template_name)

    def post(self, request):
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')

        # 1. 基础字段非空验证
        errors = []
        if not username:
            errors.append('用户名不能为空')
        if not email:
            errors.append('邮箱不能为空')
        if not password:
            errors.append('密码不能为空')
        elif password != password_confirm:
            errors.append('两次输入的密码不一致')

        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, self.template_name)

        # 2. 检查用户名和邮箱是否已存在
        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, '用户名已被注册')
            return render(request, self.template_name)
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, '邮箱已被注册')
            return render(request, self.template_name)

        # 3. 使用 Django 密码验证器进行密码强度校验
        #    验证规则已配置在 settings.py 的 AUTH_PASSWORD_VALIDATORS 中：
        #    - 最小长度 8 位
        #    - 必须包含大写字母
        #    - 必须包含小写字母
        #    - 不能与个人信息相似
        #    - 不能是常见弱密码
        #    - 不能全是数字
        try:
            validate_password(password, user=CustomUser(username=username, email=email))
        except ValidationError as e:
            for error in e.messages:
                messages.error(request, error)
            return render(request, self.template_name)

        # 4. 创建用户
        user = CustomUser.objects.create_user(
            username=username,
            email=email,
            password=password,
        )
        # 自动登录
        login(request, user)
        messages.success(request, '🎉 注册成功！欢迎加入 VideoHub 视频平台！')
        return redirect('videos:index')


class ProfileView(LoginRequiredMixin, View):
    """
    个人中心
    展示和编辑用户个人信息。
    """
    template_name = 'users/profile.html'

    def get(self, request):
        return render(request, self.template_name, {
            'profile_user': request.user,
        })

    def post(self, request):
        user = request.user
        user.bio = request.POST.get('bio', '')
        user.phone = request.POST.get('phone', '')
        user.website = request.POST.get('website', '')

        # 处理头像上传
        if request.FILES.get('avatar'):
            user.avatar = request.FILES['avatar']

        user.save()
        messages.success(request, '个人信息已更新')
        return redirect('users:profile')


class MyVideosView(LoginRequiredMixin, ListView):
    """
    我的上传
    展示当前用户上传的所有视频。
    """
    model = Video
    template_name = 'users/my_videos.html'
    context_object_name = 'videos'
    paginate_by = 12

    def get_queryset(self):
        return Video.objects.filter(
            uploader=self.request.user
        ).select_related('category').order_by('-created_at')


class MyFavoritesView(LoginRequiredMixin, ListView):
    """
    我的收藏
    展示当前用户收藏的所有视频。
    """
    template_name = 'users/my_favorites.html'
    context_object_name = 'videos'
    paginate_by = 12

    def get_queryset(self):
        # 通过 Favorite 模型反向查询收藏的视频
        from apps.interactions.models import Favorite
        return Video.objects.filter(
            favorites__user=self.request.user,
            status=Video.StatusChoices.PUBLISHED,
        ).select_related('uploader', 'category').order_by('-favorites__created_at')
