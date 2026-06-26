"""
============================================================
 视频模块 - 模板上下文处理器
============================================================
 向所有模板注入全局变量，如网站名称、分类导航等。
============================================================
"""
from typing import Dict, Any
from django.http import HttpRequest

# 导入分类模型（延迟导入，避免循环引用）
from django.utils.functional import SimpleLazyObject


def _get_all_categories():
    """
    延迟加载所有视频分类列表
    使用 SimpleLazyObject 实现懒加载，仅在模板真正使用时才查询数据库
    """
    from .models import Category
    return Category.objects.filter(is_active=True).order_by('sort_order', 'id')


def site_global(request: HttpRequest) -> Dict[str, Any]:
    """
    向所有模板注入全局变量

    注入的变量：
        - site_name: 网站名称
        - site_description: 网站描述
        - all_categories: 所有启用的视频分类列表
    """
    return {
        'site_name': 'VideoHub 视频平台',
        'site_description': '高质量视频分享平台',
        'all_categories': SimpleLazyObject(_get_all_categories),
    }
