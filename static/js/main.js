/* ============================================================
   VideoHub 视频平台 - 全局 JavaScript
   ============================================================ */

(function() {
    'use strict';

    // ============================================================
    // 自动隐藏消息提示（5 秒后自动消失）
    // ============================================================
    document.addEventListener('DOMContentLoaded', function() {
        const alerts = document.querySelectorAll('.alert-dismissible');
        alerts.forEach(function(alert) {
            setTimeout(function() {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }, 5000);
        });
    });

    // ============================================================
    // 视频播放器：记住播放进度
    // ============================================================
    document.addEventListener('DOMContentLoaded', function() {
        const player = document.getElementById('videoPlayer');
        if (!player) return;

        const videoId = window.location.pathname.split('/').filter(Boolean).pop();
        const storageKey = 'vh_progress_' + videoId;

        // 恢复进度
        try {
            const saved = localStorage.getItem(storageKey);
            if (saved) {
                const data = JSON.parse(saved);
                // 只恢复 2 小时内的进度，且大于 5 秒才恢复
                if (Date.now() - data.time < 2 * 60 * 60 * 1000 && data.currentTime > 5) {
                    player.currentTime = data.currentTime;
                }
            }
        } catch(e) {}

        // 保存进度（每 10 秒保存一次）
        player.addEventListener('timeupdate', function() {
            try {
                localStorage.setItem(storageKey, JSON.stringify({
                    currentTime: player.currentTime,
                    time: Date.now()
                }));
            } catch(e) {}
        });

        // 播放完成时清除进度记录
        player.addEventListener('ended', function() {
            try {
                localStorage.removeItem(storageKey);
            } catch(e) {}
        });
    });

    // ============================================================
    // 评论回复：展开/收起回复输入框
    // ============================================================
    document.addEventListener('DOMContentLoaded', function() {
        // 回复按钮点击
        document.querySelectorAll('.reply-btn').forEach(function(btn) {
            btn.addEventListener('click', function(e) {
                e.preventDefault();
                const commentId = this.dataset.commentId;
                const form = document.getElementById('replyForm_' + commentId);
                if (form) {
                    const isHidden = form.style.display === 'none';
                    // 先隐藏所有回复表单
                    document.querySelectorAll('.reply-form').forEach(function(f) {
                        f.style.display = 'none';
                    });
                    form.style.display = isHidden ? 'block' : 'none';
                    if (isHidden) {
                        form.querySelector('.reply-input').focus();
                    }
                }
            });
        });
    });

    // ============================================================
    // 通用 AJAX 请求函数
    // ============================================================
    window.VideoHub = {
        /**
         * 发送 AJAX POST 请求
         * @param {string} url - 请求地址
         * @param {object} data - 表单数据
         * @param {function} onSuccess - 成功回调
         * @param {function} onError - 失败回调
         */
        post: function(url, data, onSuccess, onError) {
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
            const headers = {
                'X-Requested-With': 'XMLHttpRequest',
            };
            if (csrfToken) {
                headers['X-CSRFToken'] = csrfToken.value;
            }

            fetch(url, {
                method: 'POST',
                headers: headers,
                body: data,
            })
            .then(function(response) {
                if (!response.ok) {
                    throw new Error('HTTP ' + response.status);
                }
                return response.json();
            })
            .then(function(data) {
                if (typeof onSuccess === 'function') {
                    onSuccess(data);
                }
            })
            .catch(function(error) {
                console.error('AJAX Error:', error);
                if (typeof onError === 'function') {
                    onError(error);
                }
            });
        },

        /**
         * 发送 AJAX GET 请求
         */
        get: function(url, onSuccess, onError) {
            fetch(url, {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                },
            })
            .then(function(response) {
                if (!response.ok) throw new Error('HTTP ' + response.status);
                return response.json();
            })
            .then(function(data) {
                if (typeof onSuccess === 'function') onSuccess(data);
            })
            .catch(function(error) {
                console.error('AJAX Error:', error);
                if (typeof onError === 'function') onError(error);
            });
        }
    };

})();
