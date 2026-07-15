# Spotify 官方播放接入

本项目使用 Spotify Web Playback SDK 和 OAuth Authorization Code with PKCE。
用户密码、Spotify Cookie 与 Client Secret 都不会进入本项目；访问令牌仅保存在当前浏览器的 `sessionStorage` 中。

## 1. 创建 Spotify 应用

1. 打开 <https://developer.spotify.com/dashboard> 并创建应用。
2. 复制公开的 **Client ID**。
3. 在应用的 Redirect URIs 中添加：

   `http://127.0.0.1:5000/player`

回调地址必须与实际访问网站的协议、域名、端口和路径完全一致。若使用线上域名，请把线上 `/player` 地址同时加入 Spotify Dashboard。

## 2. 启动前设置环境变量

PowerShell：

```powershell
$env:SPOTIFY_CLIENT_ID='你的公开 Client ID'
$env:SPOTIFY_REDIRECT_URI='http://127.0.0.1:5000/player'
python app.py
```

不要设置或提交 Client Secret；PKCE 流程不需要它。

## 3. 使用

1. 打开数据看板或 `/player`。
2. 点击“连接 Spotify”。
3. 在 Spotify 官方页面登录并授权。
4. 返回网站后等待按钮变成绿色“Spotify 已连接”。
5. 点击榜单歌曲，网站会在 Spotify 曲库搜索匹配曲目，并交给官方播放器播放。

完整播放要求当前登录用户拥有有效的 Spotify Premium。歌曲仍受账号所在地、Spotify 曲库可用性和平台政策限制。

## 临时公网地址

Spotify 要求回调地址与 Dashboard 中登记的地址完全一致。Cloudflare Quick Tunnel 的域名每次启动都可能变化，因此它适合临时展示网站，但不适合作为长期固定的 Spotify OAuth 回调。

如果确实要在手机上测试 Spotify 登录，需要把本次的 HTTPS `/player` 地址同时登记到 Spotify Dashboard，并将 `SPOTIFY_REDIRECT_URI` 设置成完全相同的值。更稳定的方案是部署到固定 HTTPS 域名。

## 合规边界

- 音频始终由 Spotify 官方 SDK 播放，不经过本站服务器下载或缓存。
- 本站不会保存 Spotify 密码、Cookie 或 Client Secret。
- 网易云播放只使用项目已有的正式解析流程，并遵守当前账号与平台接口返回的 VIP、付费、地区和版权状态。
- 商业部署前需要确认并遵守 Spotify Developer Policy，必要时取得书面许可。
