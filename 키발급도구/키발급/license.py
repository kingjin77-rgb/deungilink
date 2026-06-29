"""
라이선스 검증 모듈
- PC 고유번호 기반 기기 인증
- 월 단위 만료 관리
- 오프라인 동작 (서버 불필요)
"""

import hashlib, hmac, base64, json, os, re
from datetime import datetime, date
from pathlib import Path

# ── 판매자 전용 비밀키 (절대 외부 공개 금지) ─────────────────────────────────
_SECRET = b"JEIL_REGISTRY_2026_SECRET_KEY_DO_NOT_SHARE"

LICENSE_FILE = Path(__file__).parent / "license.dat"
PRODUCT_NAME = "법무법인제이엘 등기자동화"


# ── 기기 고유 ID ──────────────────────────────────────────────────────────────

def get_machine_id() -> str:
    """PC 고유번호 생성 (MAC주소 + 디스크 시리얼 기반)"""
    import uuid, subprocess, sys
    raw = ""

    try:
        # MAC 주소
        mac = hex(uuid.getnode())
        raw += mac
    except:
        pass

    try:
        # Windows 디스크 시리얼
        if sys.platform == "win32":
            result = subprocess.check_output(
                "wmic diskdrive get SerialNumber",
                shell=True, stderr=subprocess.DEVNULL
            ).decode(errors="ignore")
            serial = "".join(result.split()).replace("SerialNumber","")
            raw += serial[:16]
    except:
        pass

    if not raw:
        raw = str(uuid.getnode())

    return hashlib.sha256(raw.encode()).hexdigest()[:16].upper()


# ── 라이선스 키 생성 (판매자 전용) ───────────────────────────────────────────

def generate_key(machine_id: str, customer_name: str,
                 expire_year: int, expire_month: int) -> str:
    """
    라이선스 키 생성 — 판매자만 사용 (keygen.py)
    machine_id: get_machine_id() 결과 (고객에게 받아야 함)
    """
    payload = {
        "mid":  machine_id,
        "name": customer_name,
        "exp":  f"{expire_year:04d}{expire_month:02d}",
    }
    payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    payload_b64  = base64.urlsafe_b64encode(payload_json.encode()).decode()

    sig = hmac.new(_SECRET,
                   payload_b64.encode(),
                   hashlib.sha256).hexdigest()[:24].upper()

    # 키 포맷: JEIL-XXXX-XXXX-XXXX-XXXX-XXXX
    key_raw = payload_b64[:8].upper() + sig
    # 5자리씩 분리
    key_parts = [key_raw[i:i+5] for i in range(0, min(25, len(key_raw)), 5)]
    key = "JEIL-" + "-".join(key_parts)

    # 검증용 전체 데이터도 저장
    full = payload_b64 + "." + sig
    return key + "|" + full


# ── 라이선스 검증 ─────────────────────────────────────────────────────────────

class LicenseResult:
    def __init__(self, valid: bool, msg: str = "",
                 customer: str = "", days_left: int = 0):
        self.valid     = valid
        self.msg       = msg
        self.customer  = customer
        self.days_left = days_left


def validate_license(license_key: str) -> LicenseResult:
    """라이선스 키 검증"""
    if not license_key or "|" not in license_key:
        return LicenseResult(False, "라이선스 키 형식이 올바르지 않습니다.")

    try:
        _, full = license_key.split("|", 1)
        payload_b64, stored_sig = full.rsplit(".", 1)

        # 서명 검증
        expected_sig = hmac.new(_SECRET,
                                payload_b64.encode(),
                                hashlib.sha256).hexdigest()[:24].upper()
        if not hmac.compare_digest(stored_sig.upper(), expected_sig):
            return LicenseResult(False, "라이선스 키가 유효하지 않습니다.")

        # 페이로드 파싱
        payload = json.loads(base64.urlsafe_b64decode(payload_b64 + "=="))
        mid    = payload["mid"]
        name   = payload["name"]
        exp    = payload["exp"]  # YYYYMM

        # 기기 확인
        my_mid = get_machine_id()
        if mid != my_mid:
            return LicenseResult(False,
                f"이 PC에서 사용할 수 없는 라이선스입니다.\n"
                f"(이 PC 코드: {my_mid})")

        # 만료일 확인
        exp_year  = int(exp[:4])
        exp_month = int(exp[4:])
        today     = date.today()
        # 해당 월 말일까지 사용 가능
        if today.year > exp_year or (today.year == exp_year and today.month > exp_month):
            return LicenseResult(False,
                f"라이선스가 만료되었습니다. ({exp_year}년 {exp_month}월)\n"
                f"갱신은 법무법인제이엘에 문의하세요.")

        # 남은 일수
        import calendar
        last_day = calendar.monthrange(exp_year, exp_month)[1]
        expire_date = date(exp_year, exp_month, last_day)
        days_left = (expire_date - today).days

        return LicenseResult(True,
            f"인증 완료 ✅  ({exp_year}년 {exp_month}월까지)",
            customer=name,
            days_left=days_left)

    except Exception as e:
        return LicenseResult(False, f"라이선스 검증 오류: {e}")


# ── 라이선스 파일 저장/로드 ───────────────────────────────────────────────────

def save_license(license_key: str):
    """라이선스 키를 파일에 저장"""
    encoded = base64.b64encode(license_key.encode()).decode()
    LICENSE_FILE.write_text(encoded, encoding="utf-8")


def load_license() -> str:
    """저장된 라이선스 키 로드"""
    if not LICENSE_FILE.exists():
        return ""
    try:
        encoded = LICENSE_FILE.read_text(encoding="utf-8").strip()
        return base64.b64decode(encoded).decode()
    except:
        return ""


def check_startup() -> LicenseResult:
    """프로그램 시작 시 라이선스 자동 확인"""
    key = load_license()
    if not key:
        return LicenseResult(False, "라이선스가 등록되지 않았습니다.")
    return validate_license(key)
