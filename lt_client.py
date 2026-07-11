# -*- coding: utf-8 -*-
"""
localtunnel 客户端（纯 Python，零依赖）
======================================

正确实现 localtunnel 协议：客户端长轮询服务端"等待请求"接口。

工作原理（与 localtunnel 官方 Node 客户端一致）：
1. 客户端 POST https://loca.lt/?new 注册，获取 {id, port, url}
2. 客户端向 https://loca.lt:<port> 发长轮询 GET /（保持连接打开）
3. 服务端把外部请求通过这个长连接"推"给客户端
4. 客户端代理到本地 Flask
5. 客户端把响应回传给服务端

用法：
    python lt_client.py            # 转发到 localhost:5000
    python lt_client.py 8000       # 转发到 localhost:8000
"""

import json
import os
import socket
import ssl
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
from http.client import HTTPResponse
from http.server import BaseHTTPRequestHandler

# 兼容 Windows cmd GBK
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


LT_HOST = "loca.lt"
LT_REGISTER_URL = f"https://{LT_HOST}/?new"
LOCAL_PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
SUBDOMAIN = sys.argv[2] if len(sys.argv) > 2 else None


def log(msg: str) -> None:
    print(msg, flush=True)


def register_tunnel() -> dict:
    """注册隧道，返回 {id, port, url, max_conn_count}"""
    url = LT_REGISTER_URL
    if SUBDOMAIN:
        url += f"&subdomain={SUBDOMAIN}"
    log(f"[REG] {url}")
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def proxy_to_local(method: str, path: str, headers: dict, body: bytes) -> tuple:
    """代理请求到本地 Flask"""
    target = f"http://127.0.0.1:{LOCAL_PORT}{path}"
    req = urllib.request.Request(target, data=body if body else None, method=method)
    skip = {"host", "connection", "content-length", "transfer-encoding", "accept-encoding"}
    for k, v in headers.items():
        if k.lower() not in skip:
            req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = resp.read()
            out_headers = {}
            for k, v in resp.headers.items():
                if k.lower() not in ("transfer-encoding", "connection", "content-length"):
                    out_headers[k] = v
            return resp.status, out_headers, payload
    except urllib.error.HTTPError as e:
        try:
            payload = e.read()
        except Exception:
            payload = b""
        out_headers = {}
        for k, v in (e.headers or {}).items():
            if k.lower() not in ("transfer-encoding", "connection", "content-length"):
                out_headers[k] = v
        return e.code, out_headers, payload
    except Exception as e:
        return 502, {"Content-Type": "text/plain"}, f"Proxy error: {e}".encode("utf-8")


def long_poll_session(session_id: str, callback_host: str, callback_port: int):
    """一个长轮询会话：GET https://loca.lt:port/，服务端把请求推过来"""
    ctx = ssl.create_default_context()
    # loca.lt 的快速隧道用自签证书，关掉校验
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    url = f"https://{callback_host}:{callback_port}/{session_id}"
    log(f"[POLL] {url}")

    while True:
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0",
                "Connection": "keep-alive",
                "Accept": "*/*",
                "Bypass-Tunnel-Reminder": "1",
            })
            with urllib.request.urlopen(req, timeout=120, context=ctx) as resp:
                raw = resp.read()
                if not raw:
                    continue
                # 解析：服务端 push 过来的是 JSON {method, path, headers, body} 或 "ok" 心跳
                try:
                    data = json.loads(raw)
                except Exception:
                    log(f"[POLL] non-json: {raw[:80]!r}")
                    continue
                if data.get("message") == "ping" or data == "ok":
                    continue
                # 这是真实请求
                threading.Thread(
                    target=handle_request,
                    args=(data,),
                    daemon=True,
                ).start()
        except urllib.error.HTTPError as e:
            log(f"[POLL] HTTPError {e.code}: {e.reason}")
            time.sleep(1)
        except Exception as e:
            log(f"[POLL] error: {e!r}")
            time.sleep(2)


def handle_request(data: dict):
    """处理服务端推过来的一个 HTTP 请求"""
    method = data.get("method", "GET")
    path = data.get("path", "/")
    headers = data.get("headers", {}) or {}
    body_b64 = data.get("body", "")
    import base64
    body = base64.b64decode(body_b64) if body_b64 else b""

    status, resp_headers, payload = proxy_to_local(method, path, headers, body)

    # 把响应 POST 回服务端
    response = {
        "id": data.get("id"),
        "status": status,
        "headers": resp_headers,
        "body": base64.b64encode(payload).decode("ascii"),
    }
    try:
        req = urllib.request.Request(
            f"https://{LT_HOST}/_loca.lt/response",
            data=json.dumps(response).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
            resp.read()
    except Exception as e:
        log(f"[RESP] error: {e!r}")


def main():
    info = register_tunnel()
    public_url = info["url"]
    tunnel_port = info["port"]
    tunnel_id = info["id"]

    log("")
    log("=" * 60)
    log(f"  [OK] 隧道已建立")
    log(f"  [URL]   {public_url}")
    log(f"  [ID]    {tunnel_id}")
    log(f"  [PORT]  {tunnel_port}  (长轮询端口)")
    log(f"  [LOCAL] http://127.0.0.1:{LOCAL_PORT}")
    log("=" * 60)
    log(f"  >> 发给朋友: {public_url}")
    log("  ! 朋友第一次打开点 'Click to Continue'")
    log("  ! 你电脑关机 = 链接失效。Ctrl+C 退出")
    log("=" * 60)
    log("")

    # 同时开 max_conn_count 个长轮询（提高并发）
    max_conn = info.get("max_conn_count", 2)
    threads = []
    for i in range(max_conn):
        t = threading.Thread(
            target=long_poll_session,
            args=(tunnel_id, LT_HOST, tunnel_port),
            daemon=True,
            name=f"poll-{i}",
        )
        t.start()
        threads.append(t)
        time.sleep(0.1)

    # 主线程保持存活
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        log("[EXIT] 用户中断")
        sys.exit(0)


if __name__ == "__main__":
    main()
