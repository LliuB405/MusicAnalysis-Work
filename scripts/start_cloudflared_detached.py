# -*- coding: utf-8 -*-
"""启动 cloudflared quick tunnel（独立进程）"""
import os
import re
import shutil
import signal
import subprocess
import time
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]


def find_cloudflared() -> str:
    """Locate cloudflared without tying the project to one Windows account."""
    executable_name = "cloudflared.exe" if os.name == "nt" else "cloudflared"
    candidates = [
        os.environ.get("CLOUDFLARED_PATH"),
        PROJECT_DIR / "scripts" / "bin" / executable_name,
        shutil.which("cloudflared"),
        Path.home() / ".workbuddy" / "binaries" / executable_name,
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(Path(candidate).resolve())
    raise FileNotFoundError(
        "cloudflared was not found. Run MusicAnalysis-Start.ps1 or start.bat "
        "once so it can be downloaded automatically."
    )


EXE = find_cloudflared()
LOG = PROJECT_DIR / "cloudflared.log"
PID = PROJECT_DIR / "cloudflared.pid"

def _is_cloudflared_process(pid: int) -> bool:
    """Avoid terminating an unrelated process if a stale PID was reused."""
    if os.name != "nt":
        return True
    result = subprocess.run(
        ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0 and "cloudflared.exe" in result.stdout.lower()


def _stop_previous_tunnel() -> None:
    """Stop only the tunnel recorded for this project, not every tunnel on the PC."""
    if not PID.exists():
        return
    try:
        pid = int(PID.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return
    if not _is_cloudflared_process(pid):
        print(f"Ignoring stale non-cloudflared PID: {pid}")
        return
    try:
        os.kill(pid, signal.SIGTERM)
        print(f"Stopped previous project tunnel PID: {pid}")
    except OSError as exc:
        print(f"  warn: cannot stop previous tunnel {pid}: {exc}")


# 1. Stop only this project's previous tunnel.
_stop_previous_tunnel()
time.sleep(1)

# 2. 尝试清理旧 log（可能被占用就忽略）
for f in (LOG, PID):
    try:
        if f.exists():
            f.unlink()
    except OSError as e:
        print(f"  warn: cannot remove {f.name}: {e}")

time.sleep(1)  # 等文件锁释放

# 3. 启动新 cloudflared
DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200
flags = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP

p = subprocess.Popen(
    [EXE, "tunnel", "--url", "http://127.0.0.1:5000", "--no-autoupdate", "--logfile", str(LOG)],
    cwd=str(PROJECT_DIR),
    stdin=subprocess.DEVNULL,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    creationflags=flags,
    close_fds=True,
)
try:
    PID.write_text(str(p.pid), encoding="utf-8")
except OSError:
    pass
print(f"Started cloudflared PID: {p.pid}")
print(f"Log: {LOG}")

# 等 cloudflared 注册 + 写公网 URL 到独立文件（方便 bat 提取）
URL_FILE = PROJECT_DIR / "public_url.txt"
print("Waiting for cloudflared to assign URL (up to 20s)...")
for i in range(40):  # 最多等 20 秒
    time.sleep(0.5)
    try:
        if not LOG.exists():
            continue
        content = LOG.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", content)
        if m:
            url = m.group(0)
            try:
                URL_FILE.write_text(url, encoding="utf-8")
            except OSError:
                pass
            print(f"Public URL: {url}")
            print(f"Saved to:  {URL_FILE}")
            break
    except OSError:
        continue
else:
    print("[WARN] Public URL not found within 20s. Check cloudflared.log")
