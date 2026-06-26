"""
============================================================
 用户模块 - 自定义密码验证器
============================================================
 提供比 Django 内置更严格的密码策略验证。
============================================================
"""
import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class UpperLowerPasswordValidator:
    """
    密码必须同时包含大写字母和小写字母的验证器

    验证规则：
        - 至少包含 1 个大写英文字母（A-Z）
        - 至少包含 1 个小写英文字母（a-z）
    """
    # 验证器说明（显示在密码帮助信息中）
    help_text = _('密码必须同时包含大写字母和小写字母')

    def __init__(self, min_upper=1, min_lower=1):
        """
        初始化验证器

        参数：
            min_upper: 最少大写字母个数（默认 1）
            min_lower: 最少小写字母个数（默认 1）
        """
        self.min_upper = min_upper
        self.min_lower = min_lower

    def validate(self, password, user=None):
        """
        验证密码是否满足大小写要求

        参数：
            password: 待验证的密码字符串
            user: 关联的用户对象（可选）

        抛出：
            ValidationError: 如果密码不符合规则
        """
        # 统计大写字母个数
        upper_count = sum(1 for char in password if char.isupper())
        # 统计小写字母个数
        lower_count = sum(1 for char in password if char.islower())

        # 构建错误信息
        errors = []
        if upper_count < self.min_upper:
            errors.append(f'至少包含 {self.min_upper} 个大写字母（当前 {upper_count} 个）')
        if lower_count < self.min_lower:
            errors.append(f'至少包含 {self.min_lower} 个小写字母（当前 {lower_count} 个）')

        if errors:
            raise ValidationError(
                _('密码强度不足：') + '；'.join(errors),
                code='password_upper_lower',
            )

    def get_help_text(self):
        """返回验证器的帮助说明文本"""
        return self.help_text


class ComplexityPasswordValidator:
    """
    密码复杂度验证器

    要求密码至少包含以下四种类别中的三种：
        1. 大写字母（A-Z）
        2. 小写字母（a-z）
        3. 数字（0-9）
        4. 特殊字符（如 @, #, $, % 等）
    """
    help_text = _('密码复杂度不足：需包含大写字母、小写字母、数字、特殊字符中至少三种')

    def validate(self, password, user=None):
        """
        验证密码复杂度
        """
        categories = 0

        # 检测是否有大写字母
        if re.search(r'[A-Z]', password):
            categories += 1
        # 检测是否有小写字母
        if re.search(r'[a-z]', password):
            categories += 1
        # 检测是否有数字
        if re.search(r'[0-9]', password):
            categories += 1
        # 检测是否有特殊字符
        if re.search(r'[^A-Za-z0-9]', password):
            categories += 1

        if categories < 3:
            raise ValidationError(
                self.help_text,
                code='password_complexity',
            )

    def get_help_text(self):
        return self.help_text
