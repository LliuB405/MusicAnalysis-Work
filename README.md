# MusicAnalysis-Work

一个面向网易云音乐榜单的数据分析与在线播放项目。播放器采用 Apple Music 风格的沉浸式视觉，分析页采用深色音乐工作台布局，并可选接入 Spotify 官方 Web Playback SDK。

![播放器桌面端](docs/assets/screenshots/player-desktop.png)

## 功能

- 12 个榜单：热歌、飙升、新歌、原创、古典、电音、中文说唱、ACG、韩语、欧美热歌、欧美新歌和日语榜
- 响应式播放器：播放/暂停、上一首、下一首、进度、音量、队列、顺序播放、随机播放和单曲循环
- 搜索与原榜单恢复、歌词、收藏和歌曲详情
- 榜单分析、跨榜对比、历史快照、排名趋势、Excel/PDF/CSV 导出和定时更新
- Spotify OAuth PKCE + 官方 Web Playback SDK（可选，完整播放需要 Spotify Premium）
- Windows 一键启动，以及 Cloudflare Quick Tunnel 临时手机分享

> 本项目不绕过会员、付费、地区或版权限制。歌曲是否可播放，以对应平台和当前账号返回的授权结果为准。Spotify 音频由官方 SDK 播放，不经过本站下载或缓存。

## 快速开始

要求：Windows、Python 3.8+。

```powershell
git clone https://github.com/LliuB405/MusicAnalysis-Work.git
cd MusicAnalysis-Work
python -m pip install -r requirements.txt
```

双击 `start.bat`，或运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\MusicAnalysis-Start.ps1
```

启动器会：

1. 自动选择真正安装了项目依赖的 Python；
2. 重启 Flask，确保加载当前仓库中的最新界面；
3. 首次运行时下载 `cloudflared`；
4. 打开 <http://127.0.0.1:5000/player>；
5. 把临时公网地址显示在窗口中，并写入 `public_url.txt`。

关闭服务可双击 `stop.bat`，或运行 `MusicAnalysis-Stop.ps1`。如需桌面快捷方式：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows\install-shortcuts.ps1
```

Quick Tunnel 地址每次启动都可能变化；电脑、Flask 和 `cloudflared` 必须保持运行，朋友的手机才能访问。

## Spotify 官方播放（可选）

复制 `.env.example` 中的配置思路，并在启动前设置环境变量：

```powershell
$env:SPOTIFY_CLIENT_ID = '你的公开 Client ID'
$env:SPOTIFY_REDIRECT_URI = 'http://127.0.0.1:5000/player'
.\start.bat
```

无需、也不要填写 Client Secret。完整步骤见 [Spotify 官方播放配置](docs/integrations/spotify.md)。

## 开发与测试

```powershell
$env:PYTHONPATH = "$PWD\src"
python -m pytest -q
```

项目采用 `src` 布局：

```text
MusicAnalysis-Work/
├─ app.py                         # Flask 页面与 API
├─ daemon.py                      # 后台服务生命周期
├─ templates/                     # 当前唯一一套网页模板
├─ static/                        # 播放器、主题、弹窗及封面资源
├─ src/music_analytics/           # 抓取、分析、历史、调度与可视化
├─ tests/                         # 自动化测试
├─ docs/                          # 使用、技术和课程文档
├─ data/samples/                  # 示例榜单快照
├─ artifacts/analysis/            # 已生成的分析图片
└─ scripts/                       # 隧道与 Windows 辅助脚本
```

更完整的文件分类见 [docs/README.md](docs/README.md)。

## 本地数据与安全

以下内容只保留在本机，不会提交到 GitHub：

- `.env`、`.vip_session.json`：本机配置与登录状态
- `.favorites.json`：当前实例共享的收藏数据
- `src/data/history.db`：榜单历史数据库
- 日志、PID、覆盖率、缓存、临时公网地址与下载的 `cloudflared`

收藏是单实例共享数据，适合个人或可信朋友临时访问；它不是多用户账号系统。公开部署前应增加身份认证和用户隔离。
