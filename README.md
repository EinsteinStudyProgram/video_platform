# 🎬 视频分享平台 (Video Platform)

一个基于 **Django 5 + Celery + FFmpeg** 的现代化视频分享平台，支持视频上传、转码、弹幕互动和个性化推荐。

---

## 📋 功能概览

| 模块 | 功能 | 状态 |
|------|------|------|
| **用户系统** | 注册、登录、个人中心、头像上传 | ✅ 完成 |
| **视频管理** | 上传、播放、多分辨率转码(480p/720p/1080p) | ✅ 完成 |
| **分类搜索** | 分类浏览、标题/描述/标签全文搜索 | ✅ 完成 |
| **互动系统** | 点赞、收藏、评论（AJAX 异步交互） | ✅ 完成 |
| **弹幕系统** | Canvas 实时渲染、颜色/类型选择、Ctrl+Enter 发送 | ✅ 完成 |
| **推荐引擎** | 协同过滤+内容推荐+热门融合、行为日志上报 | ✅ 完成 |
| **定时任务** | 标签权重计算、日志清理、缓存预热（Celery Beat） | ✅ 完成 |
| **流媒体** | HTTP Range 分块加载、分辨率自适应选择 | ✅ 完成 |

---

## 🚀 快速开始

### 环境要求

- Python 3.10+
- Redis（Celery Broker）
- FFmpeg（视频转码）
- Node.js（可选，前端依赖）

### 1. 克隆项目

```bash
git clone <your-repo-url>
cd video_platform
```

### 2. 创建虚拟环境

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

复制 `.env.example` 为 `.env`，按需修改：

```bash
cp .env.example .env
```

关键配置项：
- `SECRET_KEY` — Django 密钥（生产环境务必修改）
- `DEBUG` — 开发模式开关
- `DATABASE_URL` — 数据库连接（默认 SQLite）
- `CELERY_BROKER_URL` — Redis 连接地址
- `FFMPEG_BIN` — FFmpeg 可执行文件路径

### 5. 初始化数据库

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 6. 启动服务

```bash
# 终端 1：Django 开发服务器
python manage.py runserver

# 终端 2：Celery Worker（视频转码、异步任务）
celery -A video_platform worker -l info

# 终端 3：Celery Beat（定时任务）
celery -A video_platform beat -l info
```

访问 http://127.0.0.1:8000/ 即可打开平台。

---

## 🏗️ 项目结构

```
video_platform/
├── apps/                          # Django 应用
│   ├── users/                     # 用户模块
│   │   ├── models.py              #   用户模型（头像、简介）
│   │   ├── views.py               #   注册/登录/个人中心
│   │   └── urls.py                #   路由配置
│   ├── videos/                    # 视频模块
│   │   ├── models.py              #   视频/分类模型
│   │   ├── views.py               #   上传/播放/列表/搜索
│   │   ├── tasks.py               #   异步转码（Celery）
│   │   └── utils.py              #   文件校验/元数据提取
│   ├── interactions/              # 互动模块
│   │   ├── models.py              #   评论/点赞/收藏模型
│   │   ├── views.py               #   AJAX 交互接口
│   │   └── urls.py                #   路由配置
│   ├── danmaku/                   # 弹幕模块
│   │   ├── models.py              #   弹幕模型
│   │   ├── views.py               #   弹幕API（列表/发送/删除）
│   │   └── urls.py                #   路由配置
│   └── recommend/                 # 推荐模块
│       ├── models.py              #   行为日志/标签权重
│       ├── engine.py              #   ★ 推荐引擎核心
│       ├── views.py               #   推荐API/行为上报API
│       ├── tasks.py               #   定时任务（权重/清理/缓存）
│       └── urls.py                #   路由配置
├── config/                        # 项目配置
│   ├── settings.py               #   主配置（应用注册/中间件/数据库）
│   ├── urls.py                    #   根路由
│   └── celery.py                 #   Celery 配置
├── templates/                     # 模板文件
│   ├── base.html                  #   基础模板
│   ├── videos/                    #   视频页面
│   │   ├── index.html             #     首页/列表
│   │   ├── detail.html            #     ★ 播放页（弹幕+推荐）
│   │   └── upload.html            #     上传页
│   └── users/                     #   用户页面
├── static/                        # 静态资源
├── media/                         # 用户上传文件（视频/缩略图）
│   ├── videos/                    #   视频文件
│   └── thumbnails/               #   缩略图
├── requirements.txt               # Python 依赖
├── README.md                      # 本文件
└── manage.py                      # Django 管理脚本
```

---

## 🎯 核心功能详解

### 视频上传与转码

```
用户上传 → 文件安全校验 → 数据库记录 → Celery 异步转码
                                              ├── FFprobe 提取元数据
                                              ├── 缩略图生成
                                              └── 多分辨率转码 (480p/720p/1080p)
```

- 视频文件限制：最大 2GB，支持 mp4/mov/avi/mkv/webm
- 转码状态实时查询，前端可轮询进度
- 失败自动重试机制

### 弹幕系统

- **后端**：Django ViewSet，支持列表/发送/删除/批量清理
- **前端**：Canvas 实时渲染，覆盖在 video 元素上
- 支持三种弹幕类型：滚动、顶部、底部
- 8 种颜色可选，Ctrl+Enter 快捷发送
- 发送频率限制（30秒内同一IP最多10条）

### 推荐引擎

**融合推荐算法**：

```
权重分配：
  - 协同过滤（基于用户行为相似度） → 40%
  - 内容推荐（基于视频标签匹配）    → 35%
  - 热门补全（播放量降序）         → 25%
```

**冷启动策略**：
| 用户状态 | 推荐策略 |
|----------|----------|
| 未登录 | 热门推荐 |
| 新用户（行为<5条） | 内容推荐 + 热门 |
| 老用户 | 协同+内容+热门融合 |

**行为上报流程**：
```
播放页加载 → 记录 view
播放 >30秒 → 记录 watch（有效观看）
点赞/收藏/评论 → 实时同步到推荐引擎
```

### 定时任务（Celery Beat）

| 任务 | 频率 | 说明 |
|------|------|------|
| `compute_tag_weights` | 每6小时 | 基于行为日志计算标签-视频权重 |
| `cleanup_old_action_logs` | 每天3:00 | 清理过期日志（view:30天/其他:90天） |
| `warm_up_recommend_cache` | 每30分钟 | 预计算热门推荐并缓存 |
| `process_video_task` | 触发式 | 上传后异步转码 |
| `retry_failed_transcoding` | 每6小时 | 重试失败转码 |

---

## 🔌 API 接口一览

| 方法 | 路由 | 说明 |
|------|------|------|
| GET | `/api/danmaku/list/<video_id>/` | 获取弹幕列表 |
| POST | `/api/danmaku/send/` | 发送弹幕 |
| POST | `/api/danmaku/delete/<id>/` | 删除弹幕 |
| GET | `/api/recommend/list/` | 获取推荐视频列表 |
| POST | `/api/recommend/log/` | 记录用户行为 |
| POST | `/api/recommend/batch-log/` | 批量记录行为 |
| GET | `/interactions/like/toggle/<id>/` | 点赞/取消点赞 |
| GET | `/interactions/favorite/toggle/<id>/` | 收藏/取消收藏 |
| POST | `/interactions/comment/add/` | 添加评论 |
| GET | `/videos/<id>/stream/` | 视频流（支持 Range） |
| GET | `/videos/<id>/stream/<resolution>/` | 指定分辨率视频流 |

---

## 🛠️ 技术栈

| 技术 | 用途 |
|------|------|
| Django 5.x | Web 框架 |
| SQLite（开发）/ PostgreSQL（生产） | 数据库 |
| Celery + Redis | 异步任务队列 |
| FFmpeg | 视频转码、元数据提取 |
| Bootstrap 5 | 前端 UI |
| HTML5 Canvas | 弹幕渲染 |
| AJAX (Fetch API) | 异步交互 |

---

## 📝 开发指南

### 代码风格

```bash
# Python 代码检查
ruff check .
ruff format .

# 类型检查
mypy apps/
```

### 数据库变更

```bash
python manage.py makemigrations
python manage.py migrate
```

### 新增应用步骤

1. `python manage.py startapp apps/<app_name>`
2. 在 `config/settings.py` 注册应用
3. 定义模型，执行迁移
4. 在 `admin.py` 注册管理后台
5. 编写视图和路由
6. 在 `config/urls.py` 挂载路由

---

## 📄 许可证

MIT License

---

## 👥 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/amazing`)
3. 提交更改 (`git commit -m 'feat: add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing`)
5. 创建 Pull Request

提交信息规范：`<type>: <description>`
- `feat`: 新功能
- `fix`: 修复
- `docs`: 文档
- `refactor`: 重构
- `perf`: 性能优化
