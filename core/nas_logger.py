"""
NAS 공유폴더 접속 로그 기록 모듈
- 실행/종료 이벤트를 NAS CSV에 append
- 실패해도 메인 앱에 영향 없음 (비동기, 예외 무시)
"""
import csv, socket, datetime, threading, configparser
from pathlib import Path


def _cfg():
    c = configparser.ConfigParser()
    c.read(str(Path(__file__).parent.parent / "config.ini"), encoding="utf-8")
    return c


def _nas_log_path() -> str:
    return _cfg().get("nas", "log_path", fallback="").strip()


def _local_info():
    hostname = socket.gethostname()
    try:
        ip = socket.gethostbyname(hostname)
    except Exception:
        ip = "알수없음"
    return hostname, ip


def log_event(event: str, customer: str = ""):
    """
    NAS 로그 파일에 이벤트 기록.
    event: "실행" | "종료" | 임의 문자열
    customer: 라이선스 고객명 (없으면 빈 문자열)
    """
    def _write():
        try:
            path = _nas_log_path()
            if not path:
                return
            hostname, ip = _local_info()
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            row = [now, customer, hostname, ip, event]
            log_file = Path(path)
            log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(log_file, "a", encoding="utf-8-sig", newline="") as f:
                csv.writer(f).writerow(row)
        except Exception:
            pass  # NAS 연결 불가 시 조용히 무시

    threading.Thread(target=_write, daemon=True).start()


def read_log(max_rows: int = 500) -> list[dict]:
    """
    NAS 로그 파일 읽기. 최신순 정렬.
    반환: [{"일시":..., "사무소":..., "PC":..., "IP":..., "이벤트":...}, ...]
    """
    path = _nas_log_path()
    if not path:
        return []
    try:
        log_file = Path(path)
        if not log_file.exists():
            return []
        rows = []
        with open(log_file, encoding="utf-8-sig", newline="") as f:
            for row in csv.reader(f):
                if len(row) >= 5:
                    rows.append({
                        "일시":   row[0],
                        "사무소": row[1],
                        "PC":    row[2],
                        "IP":    row[3],
                        "이벤트": row[4],
                    })
        return list(reversed(rows))[:max_rows]
    except Exception:
        return []
