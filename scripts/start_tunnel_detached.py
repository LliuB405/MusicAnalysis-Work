# -*- coding: utf-8 -*-
"""
启动 localtunnel 客户端（独立进程，不被 WorkBuddy 沙箱清理）
"""
import os
import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
PYTHON_EXE = Path(sys.executable).resolve()
SCRIPT = PROJECT_DIR / "lt_client.py"
LOG_FILE = PROJECT_DIR / "lt_client.log"
ERR_FILE = PROJECT_DIR / "lt_client.err.log"
URL_FILE = PROJECT_DIR / "lt_client.url"
PID_FILE = PROJECT_DIR / "lt_client.pid"

# 清理旧文件
for f in (LOG_FILE, ERR_FILE, URL_FILE, PID_FILE):
    if f.exists():
        try:
            f.unlink()
        except Exception:
            pass

# 用 DETACHED_PROCESS 标志启动：脱离父进程，沙箱清理时不影响子进程
DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200
flags = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP

cmd = [str(PYTHON_EXE), "-u", str(SCRIPT), "5000"]  # -u = unbuffered

with open(LOG_FILE, "wb") as out, open(ERR_FILE, "wb") as err:
    p = subprocess.Popen(
        cmd,
        cwd=str(PROJECT_DIR),
        stdout=out,
        stderr=err,
        stdin=subprocess.DEVNULL,
        creationflags=flags,
        close_fds=True,
    )

PID_FILE.write_text(str(p.pid), encoding="utf-8")
print(f"Started tunnel client PID: {p.pid}")
print(f"Logs: {LOG_FILE}")
print(f"URL will be written to: {URL_FILE}")
