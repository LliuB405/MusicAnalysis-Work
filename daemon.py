# -*- coding: utf-8 -*-
"""
Flask 服务守护脚本
==================
解决 WorkBuddy run_in_background 模式下 Flask 进程被异常杀掉的问题。

用法：
    python daemon.py start     # 启动服务
    python daemon.py stop      # 停止服务
    python daemon.py status    # 查看状态
    python daemon.py restart   # 重启服务

实现方式：
    使用 .NET Process 完全脱离父 shell 启动子进程。
    父进程退出后子进程仍可独立运行，不会被 WorkBuddy 沙箱清理。
"""

import os
import sys
import time
import subprocess
from pathlib import Path
from typing import Optional

PROJECT_DIR = Path(__file__).resolve().parent
PYTHON_EXE = r"C:\Users\22283\.workbuddy\binaries\python\versions\3.13.12\python.exe"
APP_SCRIPT = PROJECT_DIR / "app.py"
LOG_FILE = PROJECT_DIR / "flask.log"
ERR_FILE = PROJECT_DIR / "flask.err.log"
PID_FILE = PROJECT_DIR / "flask.pid"


def _is_listening(port: int = 5000) -> bool:
    """检查端口是否在监听（用 socket 跨平台，不用 netstat）"""
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            return s.connect_ex(("127.0.0.1", port)) == 0
    except OSError:
        return False


def _is_pid_alive(pid: int) -> bool:
    """检查进程是否存活（用 ctypes，不依赖 tasklist）"""
    import ctypes
    kernel32 = ctypes.windll.kernel32
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    STILL_ACTIVE = 259
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return False
    try:
        exit_code = ctypes.c_ulong()
        if kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
            return exit_code.value == STILL_ACTIVE
        return False
    finally:
        kernel32.CloseHandle(handle)


def _read_pid() -> Optional[int]:
    """从 pid 文件读取 PID"""
    if not PID_FILE.exists():
        return None
    try:
        return int(PID_FILE.read_text().strip())
    except (ValueError, OSError):
        return None


def _is_alive(pid: Optional[int]) -> bool:
    """检查进程是否存活"""
    if pid is None:
        return False
    return _is_pid_alive(pid)


def start() -> int:
    """启动 Flask（完全独立进程）"""
    if _is_listening():
        pid = _read_pid()
        print(f"[已运行] Flask 正在监听 5000 端口 (PID: {pid})")
        return 0

    if not APP_SCRIPT.exists():
        print(f"[错误] 找不到 {APP_SCRIPT}")
        return 1

    # 关键：用 cmd /c start 完全脱离 shell 启动
    # /B 表示不创建新窗口（仅在已经脱离时才有意义，配合 start /B）
    cmd = (
        f'cd /d "{PROJECT_DIR}" && '
        f'start /B "" "{PYTHON_EXE}" "{APP_SCRIPT}" '
        f'> "{LOG_FILE}" 2> "{ERR_FILE}"'
    )
    subprocess.Popen(cmd, shell=True)

    # 等待启动
    for _ in range(20):
        time.sleep(0.5)
        if _is_listening():
            print(f"[成功] Flask 已在 http://127.0.0.1:5000 启动")
            print(f"       日志: {LOG_FILE}")
            return 0

    print(f"[失败] 启动超时，请检查 {ERR_FILE}")
    return 1


def stop() -> int:
    """停止 Flask"""
    pid = _read_pid()
    if pid and _is_alive(pid):
        subprocess.run(f"taskkill /F /PID {pid}", shell=True, capture_output=True)
        print(f"[已停止] 终止 PID {pid}")
        return 0
    # PID 文件可能陈旧，但旧版服务仍占用 5000。只终止明确监听该端口的进程，
    # 避免 launcher 误以为旧模板已经是最新版。
    if _is_listening():
        try:
            result = subprocess.run(
                ["netstat", "-ano", "-p", "tcp"],
                capture_output=True, text=True, errors="ignore", check=False,
            )
            listener_pids = set()
            for line in result.stdout.splitlines():
                if ":5000" in line and "LISTENING" in line.upper():
                    parts = line.split()
                    if parts and parts[-1].isdigit():
                        listener_pids.add(int(parts[-1]))
            for listener_pid in listener_pids:
                subprocess.run(
                    ["taskkill", "/F", "/PID", str(listener_pid)],
                    capture_output=True, check=False,
                )
                print(f"[已停止] 终止占用 5000 端口的旧服务 PID {listener_pid}")
            if listener_pids:
                return 0
        except OSError as exc:
            print(f"[警告] 无法清理旧服务: {exc}")
    print("[未运行] Flask 未在运行")
    return 0


def status() -> int:
    """查看 Flask 状态"""
    pid = _read_pid()
    listening = _is_listening()
    alive = _is_alive(pid)

    print(f"PID file:     {pid or '(none)'}")
    print(f"Process:      {'alive' if alive else 'dead'}")
    print(f"Port 5000:    {'LISTENING' if listening else 'CLOSED'}")

    if listening and not alive:
        print("[警告] 端口在监听但 PID 文件中的进程已死，建议 restart")
        return 2
    if not listening and alive:
        print("[警告] 进程在运行但端口未监听，可能启动中或出错了")
        return 2
    if not listening and not alive:
        print("[提示] Flask 未运行")
        return 1
    return 0


def restart() -> int:
    """重启 Flask"""
    stop()
    time.sleep(1)
    return start()


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 0
    cmd = sys.argv[1].lower()
    result = {
        "start": start,
        "stop": stop,
        "status": status,
        "restart": restart,
    }.get(cmd, lambda: (print(f"未知命令: {cmd}"), 1)[1])()
    return int(result or 0)


if __name__ == "__main__":
    sys.exit(main())
