# ============================================================
# VideoHub 开发环境一键启动脚本
# 使用方式：在 PowerShell 中运行 .\start_dev.ps1
#
# 启动顺序：
#   1. Redis（可选，如果未安装可用模拟模式）
#   2. Celery Worker（异步任务处理器）
#   3. Django 开发服务器
# ============================================================

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  VideoHub 视频平台 - 开发环境启动"     -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 获取脚本所在目录
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

# 检查虚拟环境
if (-not (Test-Path "venv")) {
    Write-Host "[警告] 未检测到 venv 虚拟环境" -ForegroundColor Yellow
    Write-Host "        尝试使用系统 Python" -ForegroundColor Yellow
}

# 检查 Redis 是否可用
$redisAvailable = $false
try {
    $redisProcess = Get-Process -Name "redis-server" -ErrorAction SilentlyContinue
    if ($redisProcess) {
        $redisAvailable = $true
        Write-Host "[OK] Redis 服务已在运行" -ForegroundColor Green
    } else {
        Write-Host "[INFO] Redis 未检测到运行中" -ForegroundColor Yellow
        Write-Host "        Celery 需要 Redis 才能工作" -ForegroundColor Yellow
        Write-Host "        如果 Redis 未安装，请启动：redis-server" -ForegroundColor Yellow
    }
} catch {
    Write-Host "[INFO] 无法检测 Redis 状态" -ForegroundColor Yellow
}

Write-Host ""

# 步骤 1：检查数据库迁移
Write-Host "[步骤 1/3] 检查数据库迁移..." -ForegroundColor Cyan
python manage.py migrate --run-syncdb 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "  [OK] 数据库迁移已应用" -ForegroundColor Green
} else {
    Write-Host "  [WARN] 迁移可能不完整，稍后请手动执行 python manage.py migrate" -ForegroundColor Yellow
}

# 步骤 2：启动 Celery Worker（后台）
Write-Host "[步骤 2/3] 启动 Celery Worker..." -ForegroundColor Cyan
$celeryJob = Start-Job -ScriptBlock {
    param($dir)
    Set-Location $dir
    # 启动 Celery Worker，-B 表示同时启动 Beat 定时任务调度
    python -m celery -A config worker -l info --pool=solo
} -ArgumentList $ProjectRoot

Write-Host "  [OK] Celery Worker 已启动 (Job ID: $($celeryJob.Id))" -ForegroundColor Green
Write-Host "       查看日志: Get-Job -Id $($celeryJob.Id) | Receive-Job" -ForegroundColor Gray

# 步骤 3：启动 Django 开发服务器
Write-Host "[步骤 3/3] 启动 Django 开发服务器..." -ForegroundColor Cyan
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  访问地址: http://127.0.0.1:8000"       -ForegroundColor Green
Write-Host "  管理后台: http://127.0.0.1:8000/admin/" -ForegroundColor Green
Write-Host "  管理员账号: admin / Admin123456"        -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "按 Ctrl+C 停止服务器" -ForegroundColor Yellow
Write-Host ""

# 运行 Django 开发服务器（前台）
python manage.py runserver 0.0.0.0:8000

# 服务器停止后，清理 Celery 作业
Write-Host "正在停止 Celery Worker..." -ForegroundColor Yellow
Stop-Job -Id $celeryJob.Id -ErrorAction SilentlyContinue
Remove-Job -Id $celeryJob.Id -ErrorAction SilentlyContinue
Write-Host "[OK] 所有服务已停止" -ForegroundColor Green
