"""
김사무장 업무자동화 — 런처
Flask 로컬 서버(127.0.0.1:5000) + Chrome 앱 모드
"""
import json, logging, os, socket, subprocess, sys, threading, time
from pathlib import Path

# Flask 자동 설치
try:
    from flask import Flask, jsonify, request, send_from_directory
except ImportError:
    print("Flask 설치 중...")
    subprocess.run([sys.executable, "-m", "pip", "install", "flask"], check=True)
    from flask import Flask, jsonify, request, send_from_directory

PORT     = 5000
_HERE    = Path(__file__).parent
PYTHONW  = Path(sys.executable).parent / "pythonw.exe"
CFG_FILE = _HERE / "launcher_config.json"
NAS_LOG  = r"N:\등기자동화프로그램(클릭금지)\activity_log.txt"
PC_NAME  = socket.gethostname()

# ─── 설정 로드 / 자동 탐지 ───────────────────────────────────────────────────

# app_id → 탐지 후보 파일명 목록 (순서대로 첫 번째 존재하는 파일 사용)
_CANDIDATES: dict[str, list[str]] = {
    "registry":            ["gui.py", "main.py"],
    "blog_ai":             ["blog_ai.py", "blog.py"],
    "sales_auto":          ["sales_auto.py", "sales.py", "영업자동화.py"],
    "cost_calc":           ["cost_calc.py", "cost.py", "등기비용계산기.py"],
    "consult":             ["consult.py", "상담관리.py"],
    "announce_ai":         ["announce_ai.py", "announce.py", "분양공고문AI.py"],
    "individual_registry": ["대시보드_실행하기.bat", "dashboard.py"],
}


def _load_cfg() -> dict:
    """launcher_config.json 전체 로드 (없으면 빈 dict)."""
    if CFG_FILE.exists():
        try:
            return json.loads(CFG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_cfg(cfg: dict):
    CFG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def _auto_detect_and_save():
    """같은 폴더의 파이썬 파일을 탐지해 config에 자동 저장 (기존 경로는 덮어쓰지 않음)."""
    cfg     = _load_cfg()
    updated = False
    for pid, names in _CANDIDATES.items():
        existing = cfg.get(pid, {}).get("path", "")
        if existing and Path(existing).exists():
            continue  # 이미 유효한 경로 있음
        for name in names:
            candidate = _HERE / name
            if candidate.exists():
                cfg.setdefault(pid, {})["path"] = str(candidate)
                updated = True
                print(f"  자동 탐지: {pid} → {candidate}")
                break
        else:
            cfg.setdefault(pid, {}).setdefault("path", "")
    if updated:
        _save_cfg(cfg)


def _load_paths() -> dict:
    """app_id → 실행 경로 dict 반환 (config 기준)."""
    paths: dict = {}
    cfg = _load_cfg()
    for pid, v in cfg.items():
        if isinstance(v, dict) and v.get("path"):
            paths[pid] = v["path"]
    return paths


# ─── 프로세스 관리 ────────────────────────────────────────────────────────────

_procs: dict = {}
_lock  = threading.Lock()


def _is_running(pid: str) -> bool:
    with _lock:
        p = _procs.get(pid)
        return p is not None and p.poll() is None


def _launch(app_id: str) -> dict:
    if _is_running(app_id):
        return {"ok": True, "running": True, "msg": "이미 실행 중"}

    cfg   = _load_cfg()
    entry = cfg.get(app_id, {})

    # URL 타입: 브라우저에서 열기
    url = entry.get("url", "")
    if url:
        import webbrowser
        webbrowser.open(url)
        _write_log(app_id, "URL열기")
        return {"ok": True, "msg": f"브라우저에서 열림: {url}"}

    # 파일 타입
    path = entry.get("path", "")
    if not path or not Path(path).exists():
        return {"ok": False, "msg": f"실행 파일 없음: {path or '경로 미설정'}"}

    try:
        p   = Path(path)
        ext = p.suffix.lower()
        if ext == ".py":
            exe = str(PYTHONW) if PYTHONW.exists() else sys.executable
            cmd = [exe, str(p)]
        elif ext == ".bat":
            cmd = ["cmd.exe", "/c", str(p)]
        else:
            cmd = [str(p)]

        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        proc  = subprocess.Popen(cmd, cwd=str(p.parent), creationflags=flags)
        with _lock:
            _procs[app_id] = proc

        _write_log(app_id, "시작")
        threading.Thread(target=_monitor, args=(app_id, proc), daemon=True).start()
        return {"ok": True, "running": True, "msg": f"{app_id} 실행됨"}
    except Exception as e:
        return {"ok": False, "msg": str(e)}


def _monitor(pid: str, proc: subprocess.Popen):
    proc.wait()
    _write_log(pid, "종료")
    with _lock:
        if _procs.get(pid) is proc:
            del _procs[pid]


# ─── NAS 로그 ─────────────────────────────────────────────────────────────────

def _write_log(prog: str, action: str):
    def _do():
        try:
            import datetime
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            Path(NAS_LOG).parent.mkdir(parents=True, exist_ok=True)
            with open(NAS_LOG, "a", encoding="utf-8") as f:
                f.write(f"{now} | {PC_NAME} | {prog} | {action}\n")
        except Exception:
            pass
    threading.Thread(target=_do, daemon=True).start()


def _read_log(n: int = 80) -> list:
    try:
        p = Path(NAS_LOG)
        if not p.exists():
            return []
        lines = [l for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
        return list(reversed(lines[-n:]))
    except Exception:
        return []


# ─── Flask 앱 ─────────────────────────────────────────────────────────────────

flask_app = Flask(__name__)

# werkzeug 접속 로그 억제
logging.getLogger("werkzeug").setLevel(logging.ERROR)


@flask_app.route("/")
def index():
    return send_from_directory(str(_HERE), "launcher.html")


@flask_app.route("/run")
def run():
    app_id = request.args.get("app", "")
    return jsonify(_launch(app_id))


@flask_app.route("/status")
def status():
    cfg = _load_cfg()
    result = {}
    for pid, entry in cfg.items():
        has_path = bool(entry.get("path") and Path(entry["path"]).exists())
        has_url  = bool(entry.get("url"))
        result[pid] = {
            "running":    _is_running(pid),
            "configured": has_path or has_url,
            "type":       "url" if (has_url and not has_path) else "file",
        }
    return jsonify(result)


@flask_app.route("/log")
def log():
    n = int(request.args.get("n", 80))
    return jsonify({"lines": _read_log(n)})


# ─── Chrome 실행 ──────────────────────────────────────────────────────────────

def _find_chrome() -> str | None:
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramW6432%\Google\Chrome\Application\chrome.exe"),
    ]
    return next((c for c in candidates if Path(c).exists()), None)


def _open_chrome(url: str):
    chrome = _find_chrome()
    if chrome:
        subprocess.Popen([
            chrome,
            f"--app={url}",
            "--start-fullscreen",
            "--no-first-run",
            "--disable-features=TranslateUI",
        ])
    else:
        import webbrowser
        webbrowser.open(url)


# ─── 진입점 ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    url = f"http://localhost:{PORT}"

    # 경로 자동 탐지 및 config 저장
    print("경로 자동 탐지 중...")
    _auto_detect_and_save()

    # 이미 실행 중이면 Chrome만 열고 종료
    try:
        test_sock = socket.socket()
        test_sock.bind(("127.0.0.1", PORT))
        test_sock.close()
        already_running = False
    except OSError:
        already_running = True

    if already_running:
        print(f"서버 이미 실행 중 → Chrome만 실행")
        _open_chrome(url)
        sys.exit(0)

    # Flask 서버 스레드 시작
    server_thread = threading.Thread(
        target=lambda: flask_app.run(
            host="127.0.0.1", port=PORT,
            debug=False, use_reloader=False
        ),
        daemon=True
    )
    server_thread.start()
    print(f"Flask 서버 시작: {url}")

    time.sleep(0.8)
    _open_chrome(url)
    print("Chrome 실행됨 (Ctrl+C 로 서버 종료)")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("서버 종료")
