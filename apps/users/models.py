"""
============================================================
 用户模块 - 数据模型
============================================================
 继承 Django 内置的 AbstractUser，扩展用户自定义字段。
 支持头像上传、个人简介等社交功能。
============================================================
"""
import os
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.conf import settings


def user_avatar_upload_path(instance, filename):
    """
    用户头像上传路径生成函数
    按用户 ID 分目录存储，防止同名文件冲突：
        media/avatars/user_{id}/filename
    """
    ext = filename.split('.')[-1]
    filename = f'avatar.{ext}'
    return os.path.join('avatars', f'user_{instance.id}', filename)


class CustomUser(AbstractUser):
    """
    自定义用户模型

    继承自 Django AbstractUser，保留以下内置字段：
        - username（用户名，唯一）
        - password（密码，自动哈希）
        - email（邮箱）
        - first_name / last_name（姓名）
        - date_joined（注册时间）
        - is_active（是否激活）
        - is_staff（是否管理员）

    扩展字段：
        - avatar: 用户头像
        - bio: 个人简介
        - phone: 手机号（可选）
        - gender: 性别
        - birthday: 出生日期
        - website: 个人网站/社交链接
    """
    class GenderChoices(models.TextChoices):
        """性别选项"""
        MALE = 'M', _('男')
        FEMALE = 'F', _('女')
        OTHER = 'O', _('保密')

    # 头像：上传至 avatars/ 目录，允许为空
    avatar = models.ImageField(
        verbose_name=_('头像'),
        upload_to=user_avatar_upload_path,
        blank=True,
        null=True,
        help_text='建议尺寸 200x200 像素，支持 JPG/PNG 格式',
    )

    # 个人简介
    bio = models.TextField(
        verbose_name=_('个人简介'),
        max_length=500,
        blank=True,
        default='',
        help_text='简单介绍一下自己吧（最多 500 字）',
    )

    # 手机号（可选，用于后续手机验证码登录）
    phone = models.CharField(
        verbose_name=_('手机号'),
        max_length=20,
        blank=True,
        default='',
    )

    # 性别
    gender = models.CharField(
        verbose_name=_('性别'),
        max_length=1,
        choices=GenderChoices.choices,
        default=GenderChoices.OTHER,
    )

    # 出生日期
    birthday = models.DateField(
        verbose_name=_('出生日期'),
        blank=True,
        null=True,
    )

    # 个人网站
    website = models.URLField(
        verbose_name=_('个人网站'),
        max_length=200,
        blank=True,
        default='',
    )

    class Meta:
        db_table = 'users_user'                     # 数据库表名
        verbose_name = _('用户')
        verbose_name_plural = _('用户')
        ordering = ['-date_joined']                  # 按注册时间倒序排列

    def __str__(self):
        """字符串表示：显示用户名和邮箱"""
        return f'{self.username} ({self.email or "未设置邮箱"})'

    @property
    def avatar_url(self):
        """
        获取头像 URL
        如果用户没有上传头像，返回默认头像地址
        """
        if self.avatar and hasattr(self.avatar, 'url'):
            return self.avatar.url
        # 返回静态默认头像（需要准备一张默认头像图片）
        return f'{settings.STATIC_URL}img/default_avatar.png'
