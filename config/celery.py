"""
============================================================
 Celery 异步任务队列配置
============================================================
 功能：管理视频转码等耗时任务的异步执行。
 技术栈：Celery + Redis（消息代理 + 结果后端）
============================================================
"""
import os
from celery import Celery

# 设置 Django 默认配置模块
# 注意：settings 模块路径是 config.settings（相对于 PYTHONPATH）
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# 创建 Celery 应用实例
# - 第一个参数是当前模块名称，用于自动生成任务名称前缀
# - broker 连接地址在 settings.py 中通过 CELERY_BROKER_URL 配置
app = Celery('video_platform')

# 从 Django 配置文件中加载 Celery 相关配置项
# namespace='CELERY' 表示所有 Celery 配置项以 CELERY_ 前缀开头
app.config_from_object('django.conf:settings', namespace='CELERY')

# 自动发现各 Django app 中定义的异步任务
# Celery 会在每个 INSTALLED_APPS 中查找 tasks.py 文件
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """
    调试任务：打印 Celery 请求信息
    可用于验证 Celery 是否正常工作
    """
    print(f'[Celery Debug] Request: {self.request!r}')
