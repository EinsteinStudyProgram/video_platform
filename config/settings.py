"""
============================================================
 Django 视频网站项目 — 核心配置文件
============================================================
 技术栈：Python 3.10+ / Django 5.0 / Celery + Redis
 数据库：开发阶段 SQLite，生产环境预留 MySQL/PostgreSQL 配置
============================================================
"""

import os
import sys
from pathlib import Path
from django.contrib.messages import constants as message_constants

# ============================================================
# 项目路径配置
# ============================================================
BASE_DIR = Path(__file__).resolve().parent.parent

# 将 apps 目录加入 Python 模块搜索路径，使得 from users.models 等导入可用
sys.path.insert(0, str(BASE_DIR / 'apps'))

# ============================================================
# 安全密钥（生产环境务必替换为随机字符串，可通过环境变量注入）
# ============================================================
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-dev-1234567890abcdefghijklmnopqrstuvwxyz'
)

# ============================================================
# 调试模式（生产环境必须为 False）
# ============================================================
DEBUG = os.environ.get('DJANGO_DEBUG', 'True').lower() in ('true', '1', 'yes')

ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', '*').split(',')

# ============================================================
# 已安装应用（按模块分组排列）
# ============================================================
INSTALLED_APPS = [
    # Django 内置应用
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # 第三方应用
    'corsheaders',          # 跨域资源共享
    'rest_framework',       # RESTful API 支持（预留）
    'django_cleanup',       # 自动清理上传文件（文件替换/删除时自动清理旧文件）

        # 自定义业务应用
    'apps.users',           # 用户模块（注册、登录、个人中心）
    'apps.videos',          # 视频核心模块（上传、播放、列表、分类）
    'apps.interactions',    # 互动模块（评论、点赞、收藏）
    'apps.danmaku',         # 弹幕模块（发送、加载、渲染）
    'apps.recommend',       # 推荐模块（个性化推荐引擎、行为日志）
]

# ============================================================
# 中间件（顺序敏感，不可随意调换）
# ============================================================
MIDDLEWARE = [
    # 安全与跨域
    'corsheaders.middleware.CorsMiddleware',        # CORS 必须放在最前面
    'django.middleware.security.SecurityMiddleware',

    # 会话与认证
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',

    # CSRF 保护（防止跨站请求伪造攻击）
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',

    # 点击劫持防护
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

# ============================================================
# 模板引擎配置
# ============================================================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'templates',          # 项目级模板目录
        ],
        'APP_DIRS': True,                     # 自动查找各 app 的 templates 子目录
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',  # 提供 request 对象
                'django.contrib.auth.context_processors.auth', # 提供 user 对象
                'django.contrib.messages.context_processors.messages',
                # 自定义上下文处理器：向所有模板注入全局变量
                'apps.videos.context_processors.site_global',
            ],
            'builtins': [
                'django.templatetags.static',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# ============================================================
# 数据库配置
# -----------------------------------------------------------
# 开发阶段使用 SQLite，零配置即可运行。
# 生产环境通过环境变量切换到 MySQL / PostgreSQL。
# ============================================================
DATABASE_ENGINE = os.environ.get('DB_ENGINE', 'sqlite')

if DATABASE_ENGINE == 'mysql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.environ.get('DB_NAME', 'video_platform'),
            'USER': os.environ.get('DB_USER', 'root'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST', '127.0.0.1'),
            'PORT': os.environ.get('DB_PORT', '3306'),
            'OPTIONS': {
                'charset': 'utf8mb4',
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            },
        }
    }
elif DATABASE_ENGINE == 'postgresql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'video_platform'),
            'USER': os.environ.get('DB_USER', 'postgres'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST', '127.0.0.1'),
            'PORT': os.environ.get('DB_PORT', '5432'),
        }
    }
else:
    # 默认使用 SQLite（开发环境）
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# ============================================================
# 密码验证器
# -----------------------------------------------------------
# 要求：密码至少 8 位，且必须同时包含大写字母和小写字母
# ============================================================
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
        'OPTIONS': {
            'user_attributes': ('username', 'email', 'first_name', 'last_name', 'phone'),
            'max_similarity': 0.7,
        },
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,  # 密码最小长度：8 位
        },
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
    # ============================================================
    # 自定义密码验证器：必须包含大写字母和小写字母
    # ============================================================
    {
        'NAME': 'apps.users.validators.UpperLowerPasswordValidator',
    },
]

# ============================================================
# 国际化（设置为中文）
# ============================================================
LANGUAGE_CODE = 'zh-hans'
TIME_ZONE = 'Asia/Shanghai'
USE_I18N = True
USE_TZ = True

# ============================================================
# 静态资源 (Static Files)
# ============================================================
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
# 生产环境下 collectstatic 收集目录
STATIC_ROOT = BASE_DIR / 'staticfiles'

# ============================================================
# 媒体文件（用户上传的视频、图片等）
# -----------------------------------------------------------
# 开发期使用本地 media/ 目录，生产环境可切换至云存储
# ============================================================
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ============================================================
# 自定义用户模型
# 指定使用 apps.users 中的 CustomUser 替代默认的 User 模型
# ============================================================
AUTH_USER_MODEL = 'users.CustomUser'

# ============================================================
# 登录/重定向配置
# ============================================================
LOGIN_URL = '/users/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# ============================================================
# CORS 跨域配置
# -----------------------------------------------------------
# 如果前端使用独立域名（如 Vue 前端），需配置此项
# ============================================================
CORS_ALLOW_ALL_ORIGINS = DEBUG  # 开发阶段允许所有来源
CORS_ALLOWED_ORIGINS = os.environ.get(
    'CORS_ALLOWED_ORIGINS',
    'http://localhost:8000,http://127.0.0.1:8000'
).split(',')
CORS_ALLOW_CREDENTIALS = True

# ============================================================
# CSRF 安全配置
# ============================================================
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]

# ============================================================
# 文件上传安全限制
# ============================================================
# 最大上传文件大小：2GB（以字节为单位）
DATA_UPLOAD_MAX_MEMORY_SIZE = 200 * 1024 * 1024  # 200MB 内存限制
FILE_UPLOAD_MAX_MEMORY_SIZE = 200 * 1024 * 1024

# ============================================================
# 消息提示框架配置
# ============================================================
MESSAGE_TAGS = {
    message_constants.DEBUG: 'debug',
    message_constants.INFO: 'info',
    message_constants.SUCCESS: 'success',
    message_constants.WARNING: 'warning',
    message_constants.ERROR: 'danger',
}

# ============================================================
# Celery 异步任务配置
# -----------------------------------------------------------
# 使用 Redis 作为消息代理（Broker）和结果后端（Backend）
# ============================================================
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://127.0.0.1:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://127.0.0.1:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Shanghai'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 单个任务最大执行时间：30 分钟

# ============================================================
# Celery Beat 定时任务调度
# -----------------------------------------------------------
# 启动方式：celery -A config beat -l info
# 自动发现 django_celery_beat 中的定时任务配置
# ============================================================
from celery.schedules import crontab
CELERY_BEAT_SCHEDULE = {
    # 每小时清理超时未转码的视频
    'cleanup-pending-videos-every-hour': {
        'task': 'apps.videos.tasks.cleanup_pending_videos',
        'schedule': 3600.0,           # 每 3600 秒（1 小时）执行一次
        'options': {'expires': 300},  # 任务排队超过 5 分钟则丢弃
    },
        # 每 6 小时重试失败转码
    'retry-failed-transcoding-every-6h': {
        'task': 'apps.videos.tasks.retry_failed_transcoding',
        'schedule': crontab(hour='*/6'),  # 每 6 小时执行一次
        'options': {'expires': 600},
    },
    # ============================================================
    # 推荐模块定时任务
    # ============================================================
    # 每 6 小时计算视频标签权重
    'compute-tag-weights-every-6h': {
        'task': 'apps.recommend.tasks.compute_tag_weights',
        'schedule': crontab(hour='*/6'),
        'options': {'expires': 600},
    },
    # 每天凌晨清理过期行为日志
    'cleanup-old-action-logs-daily': {
        'task': 'apps.recommend.tasks.cleanup_old_action_logs',
        'schedule': crontab(hour=3, minute=0),    # 凌晨 3 点执行
        'options': {'expires': 300},
    },
    # 每 30 分钟预热推荐缓存
    'warm-up-recommend-cache-every-30m': {
        'task': 'apps.recommend.tasks.warm_up_recommend_cache',
        'schedule': 1800.0,                       # 每 1800 秒（30 分钟）
        'options': {'expires': 120},
    },
}

# 记录 Celery 任务日志到文件
CELERYD_LOG_FILE = BASE_DIR / 'logs' / 'celery.log'
CELERYD_LOG_LEVEL = 'INFO'

# ============================================================
# FFmpeg 配置（视频转码工具路径）
# ============================================================
FFMPEG_PATH = os.environ.get('FFMPEG_PATH', 'ffmpeg')   # 默认使用系统 PATH 中的 ffmpeg
FFPROBE_PATH = os.environ.get('FFPROBE_PATH', 'ffprobe') # 默认使用系统 PATH 中的 ffprobe

# 视频转码输出分辨率列表（宽度 x 高度）
VIDEO_RESOLUTIONS = [
    {'suffix': '480p', 'width': 854,  'height': 480,  'bitrate': '800k'},
    {'suffix': '720p', 'width': 1280, 'height': 720,  'bitrate': '1500k'},
    {'suffix': '1080p','width': 1920, 'height': 1080, 'bitrate': '3000k'},
]

# ============================================================
# 云存储配置（预留接口）
# -----------------------------------------------------------
# 开发期注释掉，生产环境取消注释并配置对应的云存储参数
# ============================================================
# AWS S3 示例配置
# DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
# AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
# AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
# AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME')
# AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME', 'ap-northeast-1')
# AWS_S3_CUSTOM_DOMAIN = os.environ.get('AWS_S3_CUSTOM_DOMAIN')
# AWS_DEFAULT_ACL = 'public-read'

# 阿里云 OSS 示例配置
# DEFAULT_FILE_STORAGE = 'aliyun_oss2_storage.backends.AliyunMediaStorage'
# ALIYUN_OSS_ACCESS_KEY_ID = os.environ.get('ALIYUN_OSS_ACCESS_KEY_ID')
# ALIYUN_OSS_ACCESS_KEY_SECRET = os.environ.get('ALIYUN_OSS_ACCESS_KEY_SECRET')
# ALIYUN_OSS_BUCKET_NAME = os.environ.get('ALIYUN_OSS_BUCKET_NAME')
# ALIYUN_OSS_ENDPOINT = os.environ.get('ALIYUN_OSS_ENDPOINT')

# ============================================================
# Django REST Framework 配置（预留）
# ============================================================
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 12,
}

# ============================================================
# 日志配置
# -----------------------------------------------------------
# 开发环境日志到控制台，生产环境日志到文件
# ============================================================
import logging.config

# 确保日志目录存在
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {module}: {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        # 控制台输出（仅开发环境）
        'console': {
            'level': 'INFO',
            'filters': ['require_debug_true'],
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        # Django 应用日志文件
        'file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'django.log',
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        # 视频相关日志（单独文件便于排查）
        'video_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'video.log',
            'maxBytes': 1024 * 1024 * 50,  # 50MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        # Celery 任务日志
        'celery_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'celery.log',
            'maxBytes': 1024 * 1024 * 50,
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        # Django 默认日志
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['file'],
            'level': 'ERROR',
            'propagate': False,
        },
        # 视频模块日志
        'apps.videos': {
            'handlers': ['video_file'],
            'level': 'INFO',
            'propagate': False,
        },
        # Celery 任务日志
        'celery': {
            'handlers': ['celery_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# ============================================================
# 主键字段类型
# ============================================================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
