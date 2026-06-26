# 视频网站部署说明

## 开发环境启动

```bash
# 1. 启动 Redis（Celery 消息代理）
redis-server

# 2. 启动 Celery Worker（处理转码等异步任务）
celery -A config worker -l info

# 3. 启动 Django 开发服务器
python manage.py runserver 0.0.0.0:8000
```

## Nginx 生产环境配置

1. 将 `nginx_video.conf` 复制到 Nginx 配置目录
2. 修改其中的路径和域名
3. 重新加载 Nginx：`nginx -s reload`

### HTTP Range 请求支持（视频进度条拖拽）

Nginx 默认支持 Range 请求，关键配置：
```nginx
add_header Accept-Ranges bytes;
```
Django 端 `VideoStreamView` 也实现了 Range 处理逻辑，
当不使用 Nginx 直连 Django 开发服务器时也能工作。

## 大文件上传：分片上传方案

对于超过 2GB 的超大文件，推荐使用分片上传：

```
客户端                          服务端
  |                                |
  |-- POST /init (文件名, 大小) --->|  生成 upload_id
  |<-- { upload_id, chunk_size } --|
  |                                |
  |-- POST /chunk (片1) ---------->|  保存临时文件
  |-- POST /chunk (片2) ---------->|
  |-- POST /chunk (片N) ---------->|
  |                                |
  |-- POST /complete ------------->|  合并分片，触发转码
  |<-- { video_id, status } -------|
```

前端实现要点：
- 使用 File.slice() 分割文件
- 每片上传后记录进度
- 支持断点续传（记录已上传的分片索引）
- 网络中断后可从断点继续上传

## 视频转码流程

```
用户上传视频
    |
    v
保存 Video 记录（status=pending）
    |
    v
Celery 任务: process_video_task.delay(video_id)
    |
    ├── 提取元数据 (FFprobe)
    ├── 生成缩略图 (FFmpeg)
    └── 多分辨率转码 (FFmpeg)
            ├── 480p  (854x480)
            ├── 720p  (1280x720)
            └── 1080p (1920x1080)
    |
    v
更新状态为 published
    |
    v
用户可播放视频
```

## Nginx 支持断点续传的配置

```nginx
location /media/ {
    # 关键：启用 Range 请求支持
    add_header Accept-Ranges bytes;

    # 如果使用 proxy_pass 到 Django
    # 需要确保后端也支持 Range
}
```
