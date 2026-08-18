"""
서류 분류 및 항목 추출 모듈
Tesseract OCR 텍스트 → 서류별 정규식 추출
"""

import re
from pathlib import Path


# ── 유틸리티 ──────────────────────────────────────────────────────────────────

def clean_amount(s: str) -> int:
    try:
        return int(re.sub(r"[^0-9]", "", str(s)))
    except:
        return 0

def _to_float_safe(s) -> "float | str":
    """면적 등 소수 필드를 float 로 변환. 실패 시 원본 문자열 보존(데이터 유실 방지)."""
    try:
        return float(str(s).replace(",", "").strip())
    except (ValueError, TypeError):
        return s

def normalize_date(s: str) -> str:
    """날짜 정규화 → YYYY-MM-DD"""
    s = re.sub(r"[년.\s]", "-", s).replace("월", "-").replace("일", "").strip()
    parts = [p.strip().zfill(2) for p in s.split("-") if p.strip()]
    if len(parts) >= 3:
        return f"{parts[0]}-{parts[1]}-{parts[2]}"
    return s

def _first(patterns, text, group=1):
    for p in patterns:
        m = re.search(p, text)
        if m:
            return m.group(group)
    return ""


# ── 서류 분류 ─────────────────────────────────────────────────────────────────

def classify_document(text: str) -> str:
    t = text[:2000]  # 앞부분만 확인
    # 발코니확장계약서 — 선택품목보다 먼저 체크 (발코니가 선택품목에 포함될 수 있어 순서 중요)
    if any(k in t for k in ["발코니확장계약서", "발코니 확장 공급계약서", "발코니확장공급계약서"]):
        return "발코니확장계약서"
    if any(k in t for k in ["선택품목계약서", "선택품목", "시스템에어컨", "아일랜드장"]):
        return "선택품목계약서"
    if any(k in t for k in ["공급계약서", "분양계약서", "잠실르엘", "아이파크", "르엘", "넥스티엘 공급계약서"]):
        return "분양계약서"
    if any(k in t for k in ["근저당권설정계약서", "근저당권 설정계약서", "근저당"]):
        return "근저당설정계약서"
    if any(k in t for k in ["인감증명서", "인 감 증 명 서", "인감증명법"]):
        return "인감증명서"
    if any(k in t for k in ["가족관계증명서", "가 족 관 계 증 명 서"]):
        return "가족관계증명서"
    if any(k in t for k in ["위임장", "위 임 장"]):
        return "위임장"
    if any(k in t for k in ["자동차운전면허증", "운전면허증", "Driver's License", "Driver License"]):
        return "운전면허증"
    # 등본은 초본보다 먼저 — "주민등록표" 키워드가 양쪽 다 매칭되므로
    if any(k in t for k in ["주민등록표등본", "주민등록표 등본",
                              "주민등록등본", "등 본", "주민등록표(등본)"]):
        return "주민등록등본"
    if any(k in t for k in ["주민등록표초본", "주민등록표 초본",
                              "주민등록초본", "주민등록표", "초본", "초 본"]):
        return "주민등록초본"
    if any(k in t for k in ["증여계약서", "증 여 계 약 서", "수증인", "증여할지분"]):
        return "증여계약서"
    if any(k in t for k in ["부동산거래계약신고서", "거래신고필증", "신고필증번호"]):
        return "거래신고필증"
    if any(k in t for k in ["권리의무승계계약서", "분양권매매", "명의변경"]):
        return "명의변경계약서"
    if any(k in t for k in ["등기부등본", "등기사항전부증명서", "갑구", "을구"]):
        return "등기부등본"
    return ""


# ── 분양계약서 ────────────────────────────────────────────────────────────────

def extract_분양계약서(text: str) -> dict:
    result = {}

    # 동/호 — \d{1,5} 로 확장: 2자리(10동)~5자리(10101동) 모두 처리
    m = re.search(r"제\s*(\d{1,5})\s*동\s*제\s*(\d{1,5})\s*호", text)
    if not m:
        m = re.search(r"(\d{1,5})\s*동\s*(\d{3,5})\s*호", text)
    if m:
        result["동"] = m.group(1)
        result["호"] = m.group(2)

    # 전용면적 (소수점 4자리) — float 로 반환 (엑셀 기입 시 숫자로 취급되도록)
    m = re.search(r"전용\s*면적\s*[:\s]*([0-9.]+)\s*㎡", text)
    if not m:
        m = re.search(r"([5-9]\d\.[0-9]{4})\s*㎡", text)
    if m:
        result["전용면적"] = _to_float_safe(m.group(1))

    # 대지지분
    m = re.search(r"대지\s*(?:지분|면적)\s*[:\s]*([0-9.]+)\s*㎡", text)
    if not m:
        nums = re.findall(r"(\d{2,3}\.\d{4})", text)
        if len(nums) >= 2:
            result["대지지분"] = _to_float_safe(nums[1])
    else:
        result["대지지분"] = _to_float_safe(m.group(1))

    # 분양계약일 (계약금 납부 기한 직전 날짜)
    m = re.search(r"계약금.*?(\d{4}[.\-년]\s*\d{1,2}[.\-월]\s*\d{1,2})", text, re.S)
    if not m:
        m = re.search(r"(\d{4}[-년.]\s*\d{1,2}[-월.]\s*\d{1,2})", text)
    if m:
        result["분양계약일"] = normalize_date(m.group(1))

    # 분양대금 (총공급금액)
    m = re.search(r"총\s*공급\s*금액\s*[:\s]*([0-9,]{8,})", text)
    if not m:
        m = re.search(r"분양\s*대금\s*[:\s]*([0-9,]{8,})", text)
    if not m:
        # 1,8xx,xxx,xxx 패턴
        m = re.search(r"([1-9],\d{3},\d{3},\d{3})", text)
    if m:
        result["분양대금"] = clean_amount(m.group(1))

    # 부가세
    m = re.search(r"부가\s*가\s*치\s*세\s*[:\s]*([0-9,]+)", text)
    if m:
        result["부가세"] = clean_amount(m.group(1))
    else:
        result["부가세"] = 0

    return result


# ── 선택품목계약서 ────────────────────────────────────────────────────────────

def extract_선택품목계약서(text: str) -> dict:
    result = {}

    # 발코니금액
    m = re.search(r"발코니[^\n]*?([0-9,]{7,})\s*원?\s*\(?VAT\s*포함\)?", text)
    if not m:
        m = re.search(r"발코니[^\n]*?([0-9,]{7,})", text)
    if m:
        result["발코니금액"] = clean_amount(m.group(1))

    # 시스템에어컨 옵션금액
    m = re.search(r"시스템\s*에어컨[^\n]*?([0-9,]{7,})\s*원?\s*\(?VAT\s*포함\)?", text)
    if not m:
        m = re.search(r"에어컨[^\n]*?([0-9,]{7,})", text)
    if m:
        result["옵션금액"] = clean_amount(m.group(1))

    return result


# ── 발코니확장계약서 (선택품목계약서와 별도로 단독 체결되는 경우) ─────────────

def extract_발코니확장계약서(text: str) -> dict:
    """
    분양계약과 별도로 체결되는 발코니 확장공사 전용 계약서.
    선택품목계약서에 발코니가 포함된 경우와 달리, 이 서류는 발코니
    확장비용 단독 계약서이므로 계약 총액을 발코니금액으로 매핑한다.
    """
    result = {}
    patterns = [
        r"발코니\s*확장\s*(?:비용|공사비|대금)[^\n]*?([0-9,]{7,})\s*원?",
        r"발코니[^\n]*?([0-9,]{7,})\s*원?\s*\(?VAT\s*포함\)?",
        r"(?:계약\s*금액|총\s*(?:계약)?\s*금액|공급\s*금액)[:\s]*([0-9,]{7,})\s*원?",
        r"발코니[^\n]*?([0-9,]{7,})",
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            result["발코니금액"] = clean_amount(m.group(1))
            break

    return result


# ── 근저당설정계약서 ──────────────────────────────────────────────────────────

def extract_근저당설정계약서(text: str) -> dict:
    result = {}

    # 은행명 + 지점 (취급사무소 포함)
    bank_map = {
        "농협": "NH농협", "국민": "국민은행", "신한": "신한은행",
        "우리": "우리은행", "하나": "하나은행", "기업": "IBK기업은행",
        "SC": "SC제일은행", "카카오": "카카오뱅크", "케이뱅크": "케이뱅크",
        "토스": "토스뱅크",
    }
    for k, v in bank_map.items():
        if k in text:
            result["대출은행"] = v
            break

    # 지점명 (취급사무소, 지점 우선)
    m = re.search(r"취급\s*사무소\s*[:\s]*([가-힣\w]+지점)", text)
    if not m:
        m = re.search(r"([가-힣\w]+지점)", text)
    if not m:
        m = re.search(r"취급사무소\s*[:\s]*([가-힣\w]+)", text)
    if m:
        result["대출지점"] = m.group(1)

    # 채권최고액 — 다양한 패턴
    # 패턴1: "채권최고액: 1,500,000,000원"
    m = re.search(r"채권\s*최고\s*액\s*[:\s]*[^0-9]*([1-9][0-9,]{7,})\s*원?", text)
    if not m:
        # 패턴2: "1순위 금 1,500,000,000 원"
        m = re.search(r"1\s*순위\s*금\s+([1-9][0-9,]{7,})\s*원", text)
    if not m:
        # 패턴3: "금 X,XXX,XXX,XXX원"
        m = re.search(r"금\s+([1-9][0-9,]{7,})\s*원", text)
    if not m:
        # 패턴4: 단독 금액 (10억 이상)
        m = re.search(r"([1-9],\d{3},\d{3},\d{3})", text)
    if m:
        amt = clean_amount(m.group(1))
        if amt > 10_000_000:  # 1천만원 이상만 채권최고액으로 인정
            result["채권최고액"] = amt

    # 근저당설정계약일
    m = re.search(r"20\s*(\d{2})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일", text)
    if m:
        result["근저당설정계약일"] = f"20{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)}"

    return result


# ── 주민등록초본 ──────────────────────────────────────────────────────────────

def extract_주민등록초본(text: str) -> dict:
    result = {}

    # 성명
    m = re.search(r"성\s*명\s*\(?한자\)?\s*([가-힣]{2,5})", text)
    if not m:
        m = re.search(r"신청인\s*:\s*([가-힣]{2,5})", text)
    if m:
        result["성명"] = m.group(1).strip()

    # 주민등록번호
    m = re.search(r"(\d{6}[-–]\d{7})", text)
    if m:
        result["주민등록번호"] = m.group(1).replace("–", "-")

    # 최신 주소 — "이하 여백" 직전 마지막 주소 (행번호 정제 방식)
    city_keys = ["서울","경기","인천","부산","대구","대전","광주","울산","세종",
                 "강원","충북","충남","전북","전남","경북","경남","제주"]
    lines = text.split("\n")
    last_addr = ""

    def _clean_addr_line(raw: str) -> str:
        """행번호·날짜·OCR 노이즈 제거"""
        cl = re.sub(r"^\d+\s+", "", raw)                        # 선행 행번호
        cl = re.sub(r"\s+\d{4}[-~]\d{2}[-~]\d{2}.*$", "", cl) # 후미 날짜 (- 또는 ~ 구분자)
        cl = re.sub(r"^[^가-힣\d]+", "", cl)                    # 선두 OCR 특수문자(ㅣ 등)
        cl = re.sub(r"\s+[a-zA-Z]{1,4}$", "", cl)              # 후미 영문 OCR 노이즈(ae 등)
        return cl.strip()

    def _has_city(cl):
        return any(k in cl for k in city_keys)

    def _is_addr_strict(cl):
        """도시 키워드 + 아파트 '호' — 오래된 지번주소를 오인식하는 false positive 방지"""
        return _has_city(cl) and "호" in cl

    def _is_addr_relaxed(cl):
        """도시 키워드 + 번지/도로 숫자 — '호' 없는 주소(연립/단독) 대상"""
        return _has_city(cl) and bool(re.search(r'\d+[-번]', cl) or re.search(r'\d{1,6}$', cl))

    def _search_reversed(pred):
        for ln in reversed(lines):
            cl = _clean_addr_line(ln)
            if pred(cl):
                return cl
        return ""

    # "이하 여백" 마커로 탐색 (strict → relaxed)
    for i, line in enumerate(lines):
        if any(k in line for k in ["이하 여백","== 이하","이 하 여 백"]):
            for j in range(i - 1, max(0, i - 10), -1):
                cl = _clean_addr_line(lines[j])
                if _is_addr_strict(cl):
                    last_addr = cl; break
            if not last_addr:
                for j in range(i - 1, max(0, i - 10), -1):
                    cl = _clean_addr_line(lines[j])
                    if _is_addr_relaxed(cl):
                        last_addr = cl; break
            break

    # 폴백 reversed 탐색: 1) '호' 있는 주소 우선, 2) 번지/도로 주소
    if not last_addr:
        last_addr = _search_reversed(_is_addr_strict)
    if not last_addr:
        last_addr = _search_reversed(_is_addr_relaxed)

    if last_addr:
        result["주소"] = last_addr

    # 전화번호
    m = re.search(r"0\d{1,2}-\d{3,4}-\d{4}", text)
    if m:
        result["전화번호"] = m.group(0)

    # 초본 발행일 — 마지막 페이지 하단 "신청일/발급일/발행일" 패턴
    # 우선순위: "발급일자" > "발행일자" > "발급일" > "발행일" > 최종 "신청일"
    발행일 = _extract_발행일(text)
    if 발행일:
        # 매핑 JSON 에 두 가지 키 표기가 공존 — 동시 채움
        result["초본발행일"] = 발행일
        result["초본"] = 발행일

    return result


# ── 발행일 공통 추출 헬퍼 ────────────────────────────────────────────────────

def _extract_발행일(text: str) -> str:
    """
    각종 증명서의 발행일/발급일을 YYYY-MM-DD 로 정규화하여 반환.
    초본·등본·인감증명서의 발급일자 추출에 공통 사용.
    """
    # "발급일자 2024년 06월 15일" / "발행일 : 2024.06.15." / "2024. 06. 15"
    patterns = [
        r"(?:발급|발행)\s*일\s*자?\s*[:\s]*(\d{4})\s*[년.\-]\s*(\d{1,2})\s*[월.\-]\s*(\d{1,2})",
        r"(?:신청|교부)\s*일\s*자?\s*[:\s]*(\d{4})\s*[년.\-]\s*(\d{1,2})\s*[월.\-]\s*(\d{1,2})",
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            y, mo, d = m.group(1), m.group(2).zfill(2), m.group(3).zfill(2)
            return f"{y}-{mo}-{d}"
    # 폴백: 텍스트 후반부의 마지막 "YYYY년 MM월 DD일" — 통상 발급일이 마지막에 위치
    tail = text[-600:] if len(text) > 600 else text
    dates = re.findall(r"(\d{4})\s*[년.\-]\s*(\d{1,2})\s*[월.\-]\s*(\d{1,2})", tail)
    if dates:
        y, mo, d = dates[-1][0], dates[-1][1].zfill(2), dates[-1][2].zfill(2)
        return f"{y}-{mo}-{d}"
    return ""


# ── 인감증명서 ────────────────────────────────────────────────────────────────

def extract_인감증명서(text: str) -> dict:
    """
    인감증명서 OCR → 성명·주민번호·인감발행일 추출.
    매핑의 인감발행일 열을 채우기 위한 핵심 추출기.
    """
    result = {}

    # 성명 — "성명 홍길동" / "성    명  :  홍길동"
    m = re.search(r"성\s*명\s*[:：]?\s*([가-힣]{2,5})(?!\s*(?:법|법인))", text)
    if not m:
        m = re.search(r"성\s*명\s*\(?한자\)?\s*([가-힣]{2,5})", text)
    if m:
        result["성명"] = m.group(1).strip()

    # 주민등록번호
    m = re.search(r"(\d{6}[-–]\d{7})", text)
    if m:
        result["주민등록번호"] = m.group(1).replace("–", "-")

    # 인감발행일 — 발급일자 우선
    발행일 = _extract_발행일(text)
    if 발행일:
        result["인감발행일"] = 발행일
        result["인감"] = 발행일

    return result


# ── 주민등록등본 ──────────────────────────────────────────────────────────────

def extract_주민등록등본(text: str) -> dict:
    """
    주민등록등본 OCR → 세대주 성명·주민번호·주소·등본발행일·세대원수 추출.
    1주택 감면·세대분리 판단에 사용.
    """
    result = {}

    # 세대주 성명 (첫 번째로 등장하는 성명 — 보통 세대주)
    m = re.search(r"세\s*대\s*주\s*[:：]?\s*([가-힣]{2,5})", text)
    if not m:
        m = re.search(r"성\s*명\s*\(?한자\)?\s*([가-힣]{2,5})", text)
    if m:
        result["성명"] = m.group(1).strip()

    # 주민등록번호 (세대주 = 첫 번째)
    m = re.search(r"(\d{6}[-–]\d{7})", text)
    if m:
        result["주민등록번호"] = m.group(1).replace("–", "-")

    # 주소 — "이하 여백" 직전 마지막 도시 키워드 라인
    city_keys = ["서울", "경기", "인천", "부산", "대구", "대전", "광주",
                 "울산", "세종", "강원", "충북", "충남", "전북", "전남",
                 "경북", "경남", "제주"]
    lines = text.split("\n")
    best_addr = ""
    for line in lines:
        ln = re.sub(r"^\d+\s+", "", line).strip()
        if any(k in ln for k in city_keys) and ("호" in ln or re.search(r"\d+[-번]", ln)):
            # 첫 번째 매칭 = 등본 상단의 세대주 주소
            best_addr = ln
            break
    if best_addr:
        result["주소"] = best_addr

    # 전화번호
    m = re.search(r"0\d{1,2}-\d{3,4}-\d{4}", text)
    if m:
        result["전화번호"] = m.group(0)

    # 등본 발행일
    발행일 = _extract_발행일(text)
    if 발행일:
        result["등본발행일"] = 발행일
        result["등본"] = 발행일

    # 세대원 수 — "세대원수" 직접 매칭 또는 주민번호 등장 횟수
    m = re.search(r"세\s*대\s*원\s*수?\s*[:：]?\s*(\d+)", text)
    if m:
        result["세대원수"] = int(m.group(1))
    else:
        # 폴백: 주민번호 개수 (마스킹 *** 포함)
        cnt = len(re.findall(r"\d{6}[-–][\d\*]{7}", text))
        if cnt >= 1:
            result["세대원수"] = cnt

    return result


# ── 가족관계증명서 ────────────────────────────────────────────────────────────

def extract_가족관계증명서(text: str) -> dict:
    """
    가족관계증명서 → 대상자(본인) 성명·주민등록번호 추출.
    상속등기 등에서 상속인 확인용으로 제출되는 서류.
    """
    result = {}

    # "본인" 행의 성명 우선 (가족관계증명서 표 첫 행은 대상자 본인)
    m = re.search(r"본\s*인\s+([가-힣]{2,5})", text)
    if not m:
        m = re.search(r"성\s*명\s*[:：]?\s*([가-힣]{2,5})", text)
    if m:
        result["성명"] = m.group(1).strip()

    m = re.search(r"(\d{6}[-–]\d{7})", text)
    if m:
        result["주민등록번호"] = m.group(1).replace("–", "-")

    return result


# ── 위임장 ────────────────────────────────────────────────────────────────────

def extract_위임장(text: str) -> dict:
    """위임장 → 위임인(본인) 성명 추출. 등기신청을 위임한 당사자 확인용."""
    result = {}

    m = re.search(r"위\s*임\s*인\s*[:：]?\s*([가-힣]{2,5})", text)
    if not m:
        m = re.search(r"성\s*명\s*[:：]?\s*([가-힣]{2,5})", text)
    if m:
        result["성명"] = m.group(1).strip()

    return result


# ── 증여계약서 ────────────────────────────────────────────────────────────────

def extract_증여계약서(text: str) -> dict:
    result = {}
    result["승계여부"] = "승계(증여)"

    # 증여일
    m = re.search(r"(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일", text)
    if m:
        result["승계일"] = f"{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)}"

    # 증여인
    m = re.search(r"증\s*여\s*인\s*[:\s]*([가-힣]{2,5})", text)
    if m:
        result["양도인성명"] = m.group(1).strip()

    # 수증인 (최종 매수인)
    m = re.search(r"수\s*증\s*인\s*[:\s]*([가-힣]{2,5})", text)
    if m:
        result["성명"] = m.group(1).strip()   # 수증인 = 최종 권리자
        result["양수인성명"] = m.group(1).strip()

    # 수증인 주민번호
    # 증여계약서에서 수증인 주민번호 추출 (증여인 다음에 나오는 주민번호)
    patterns = re.findall(r"\d{6}[-–]\d{7}", text)
    if len(patterns) >= 2:
        result["주민등록번호"] = patterns[1].replace("–", "-")  # 두 번째 = 수증인
    elif len(patterns) == 1:
        result["주민등록번호"] = patterns[0].replace("–", "-")

    # 수증인 전화번호 (수증인 이름 뒤에 나오는 전화번호)
    phones = re.findall(r"0\d{1,2}-\d{3,4}-\d{4}", text)
    if len(phones) >= 2:
        result["전화번호"] = phones[1]  # 두 번째 = 수증인
    elif len(phones) == 1:
        result["전화번호"] = phones[0]

    # 증여 지분
    # 증여지분: "( 2 )분의 ( 1 )" 패턴
    m = re.search(r"지\s*분\s*[:\s]*\(?\s*(\d+)\s*\)?\s*분\s*의\s*\(?\s*(\d+)\s*\)?", text)
    if m:
        result["증여지분"] = f"{m.group(1)}분의{m.group(2)}"

    # 증여이므로 거래신고필증/가액 공란
    result["거래신고필증번호"] = ""
    result["거래가액"] = ""

    return result


# ── 명의변경계약서 (매매승계) ─────────────────────────────────────────────────

def extract_명의변경계약서(text: str) -> dict:
    result = {}
    result["승계여부"] = "승계(매매)"

    # 승계일
    m = re.search(r"(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일", text)
    if m:
        result["승계일"] = f"{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)}"

    # 매도인/양도인
    m = re.search(r"(매도인|양도인)\s*[:\s]*([가-힣]{2,5})", text)
    if m:
        result["양도인성명"] = m.group(2).strip()

    # 매수인/양수인 = 최종 매수인
    m = re.search(r"(매수인|양수인)\s*[:\s]*([가-힣]{2,5})", text)
    if m:
        result["성명"] = m.group(2).strip()
        result["양수인성명"] = m.group(2).strip()

    # 거래가액
    m = re.search(r"(매매\s*대금|거래\s*가액)\s*[:\s금]*([0-9,]{8,})\s*원?", text)
    if m:
        result["거래가액"] = clean_amount(m.group(2))

    return result


# ── 거래신고필증 ──────────────────────────────────────────────────────────────

def extract_거래신고필증(text: str) -> dict:
    result = {}

    # 신고필증번호
    m = re.search(r"신고\s*(?:필증)?\s*번호\s*[:\s]*([0-9\-]+)", text)
    if not m:
        m = re.search(r"([0-9]{4}-[0-9]{2}-[0-9]+)", text)
    if m:
        result["거래신고필증번호"] = m.group(1)

    # 거래가액
    m = re.search(r"실제\s*거래\s*가격\s*[:\s금]*([0-9,]{8,})\s*원?", text)
    if not m:
        m = re.search(r"거래\s*가액\s*[:\s금]*([0-9,]{8,})\s*원?", text)
    if m:
        result["거래가액"] = clean_amount(m.group(1))

    return result


# ── 등기부등본 ────────────────────────────────────────────────────────────────

def extract_등기부등본(text: str) -> dict:
    """
    집합건물 등기부등본 OCR → 주소명단 필드 추출
    핵심 원칙:
      - 동/호: 소재지번 첫 줄에서만 추출
      - 건물면적: 표제부 전유부분 구조 면적
      - 대지권면적: 대지권비율 분의 뒤 숫자
      - 접수일자: 소유권보존 등기 접수일
      - 주소: 최종소유자 주소 (등기이전 이력 완전 배제)
    """
    result = {}

    # OCR 노이즈 전처리 (공백 정리)
    # 실제 Tesseract 출력에서 숫자 사이 공백 제거
    clean = re.sub(r"(\d)\s+\.\s+(\d)", r"\1.\2", text)   # "84 . 12" → "84.12"
    clean = re.sub(r"\s{2,}", " ", clean)                       # 다중공백 단일화

    # ── 신탁 ─────────────────────────────────────────────────────────────────
    신탁_count = len(re.findall(r"신탁\s*(?:등기|원부|말소)", text))
    result["신탁건수"] = min(신탁_count, 10)
    result["신탁유무"] = "있음" if 신탁_count > 0 else "없음"

    # ── 동·호수 (소재지번 첫 줄에서만) ─────────────────────────────────────
    # 등기부등본 상단 "소재지번 및 건물번호" 또는 "소재지번" 행에서만 추출
    # 형식: "제104동 제2302호"  /  "104동 2302호"
    소재지번_블록 = re.search(
        r"(?:소재지번|건물번호)[^\n]{0,200}", text, re.DOTALL)
    소재지_text = 소재지번_블록.group(0) if 소재지번_블록 else text[:300]

    m = re.search(r"제\s*(\d{2,4})\s*동\s*제\s*(\d{3,4})\s*호", 소재지_text)
    if not m:
        m = re.search(r"(\d{2,4})\s*동\s*(\d{3,4})\s*호", 소재지_text)
    if m:
        result["동"] = m.group(1).strip()
        result["호"] = m.group(2).strip()

    # ── 건물면적 (표제부 전유부분 — 철근콘크리트 구조 뒤 ㎡) ────────────────
    # 실제 패턴: "철근콘크리트구조 ... 23층 84.1200㎡"
    # ㎡ 직전 소수점 숫자 중 30~200 범위 (전용면적 범위)
    면적_candidates = re.findall(
        r"(\d{2,3}[.]\d{2,6})\s*(?:㎡|m2|㎡)", clean)
    건물면적 = None
    for v in 면적_candidates:
        try:
            f = float(v)
            if 20 < f < 500:   # 전용면적 현실적 범위
                건물면적 = v
                break
        except ValueError:
            pass
    # 전유부분 섹션이 있으면 그 안에서만 탐색
    전유 = re.search(r"전유부분[\s\S]{0,400}?(?=\[|갑구|을구|\Z)", text)
    if 전유:
        in_candidates = re.findall(r"(\d{2,3}[.]\d{2,6})\s*(?:㎡|m2)", 전유.group(0))
        for v in in_candidates:
            try:
                if 20 < float(v) < 500:
                    건물면적 = v
                    break
            except ValueError:
                pass
    if 건물면적:
        result["전용면적"] = _to_float_safe(건물면적)

    # ── 건물등기 접수일자 (소유권이전등기 접수일) ────────────────────────────
    이전_dates = []
    for m in re.finditer(
            r"소유권\s*이전[\s\S]{0,400}?접수\s*(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일", text):
        y, mo, d = m.group(1), m.group(2), m.group(3)
        이전_dates.append(f"{y}-{int(mo):02d}-{int(d):02d}")
    if 이전_dates:
        result["건물등기접수일자"] = sorted(이전_dates)[-1]  # 최신일
    else:
        # fallback: 소유권보존 접수일
        보존_블록 = re.search(
            r"소유권\s*보존[\s\S]{0,400}?접수\s*(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일",
            text)
        if 보존_블록:
            y, mo, d = 보존_블록.group(1), 보존_블록.group(2), 보존_블록.group(3)
            result["건물등기접수일자"] = f"{y}-{int(mo):02d}-{int(d):02d}"

    # ── 소유자 성명 (갑구 최신 소유권 — 마지막 소유자) ─────────────────────
    # "소유자 홍길동 901010-1234567" 패턴에서 이름만
    owners = re.findall(
        r"소유자\s+([가-힣]{2,5})\s+\d{6}[-–*]", text)
    if not owners:
        owners = re.findall(r"소유자\s+([가-힣]{2,5})(?=\s|$)", text, re.MULTILINE)
    if owners:
        result["성명"] = owners[-1]
        if len(owners) >= 2:
            # 공동명의: 같은 소유권이전 순위에 2명 → 마지막 두 명
            result["공동명의자"] = owners[-2]

    # ── 최종소유자 주소 ───────────────────────────────────────────────────────
    # 전략: 마지막 "소유자 [이름]" 블록 이후의 주소행만 사용
    #       "제NNNNN호", "매매", "증여" 등 등기이력 키워드 배제
    city_keys = ["서울", "경기", "인천", "부산", "대구", "광주", "대전",
                 "울산", "세종", "강원", "제주", "충북", "충남", "전북",
                 "전남", "경북", "경남"]

    REJECT_KEYWORDS = [
        "집합건물", "표제부", "갑구", "을구", "등기부", "열람",
        "고유번호", "소유자", "등기목적", "접수", "등기원인",
        "매매", "증여", "교환", "판결", "상속",
        r"제\d{4,6}호",          # 접수번호 패턴 (제43307호 등)
    ]

    # 마지막 소유자 이름 이후 텍스트에서 주소 탐색
    last_owner_pos = -1
    if owners:
        # 마지막 소유자 이름 위치
        for m2 in re.finditer(re.escape(owners[-1]), text):
            last_owner_pos = m2.end()

    search_area = text[last_owner_pos:last_owner_pos + 400] if last_owner_pos >= 0 else text

    best_addr = ""
    for line in search_area.splitlines():
        line = line.strip()
        if not line or len(line) < 8:
            continue
        # 거부 키워드 체크
        if any(kw in line for kw in
               ["집합건물","표제부","갑구","을구","등기부","열람",
                "고유번호","소유자","등기목적","등기원인",
                "매매","증여","교환","판결","상속"]):
            continue
        if re.search(r"제\d{4,6}호", line):    # 접수번호 포함 행 제거
            continue
        if any(k in line for k in city_keys):
            if ("로" in line or "길" in line or "동" in line or "가" in line) and len(line) > 8:
                # 이름·주민번호 앞부분 제거
                addr = re.sub(r"^[가-힣]{2,5}\s+\d{6}[-–*\d]+\s*", "", line).strip()
                addr = re.sub(r"^\d+\s+", "", addr).strip()
                if addr and len(addr) > 8:
                    best_addr = addr
                    break  # 첫 번째 매칭만 (최종소유자 주소)

    if best_addr:
        result["주소"] = best_addr

    # ── 국적 (외국인 여부) ───────────────────────────────────────────────────
    외국인_kw = ["외국인등록", "여권번호", "FOREIGN", "外國人", "국적코드"]
    result["국적"] = "외국인" if any(k in text for k in 외국인_kw) else ""

    return result

# ── EXTRACTORS 매핑 ───────────────────────────────────────────────────────────

EXTRACTORS = {
    "분양계약서":     extract_분양계약서,
    "선택품목계약서": extract_선택품목계약서,
    "발코니확장계약서": extract_발코니확장계약서,
    "근저당설정계약서": extract_근저당설정계약서,
    "주민등록초본":   extract_주민등록초본,
    "주민등록등본":   extract_주민등록등본,
    "인감증명서":     extract_인감증명서,
    "가족관계증명서": extract_가족관계증명서,
    "위임장":         extract_위임장,
    "증여계약서":     extract_증여계약서,
    "명의변경계약서": extract_명의변경계약서,
    "거래신고필증":   extract_거래신고필증,
    "등기부등본":     extract_등기부등본,
}


# ── 승계 횟수 + 유형 분석 ─────────────────────────────────────────────────────

def detect_succession_type(text: str) -> str:
    if any(k in text for k in ["증여", "수증인", "무상이전"]):
        return "증여"
    if "교환" in text:
        return "교환"
    return "매매"


def count_and_classify_successions(doc_list: list) -> dict:
    """
    여러 승계계약서 분석 → 마지막 건 기준으로 입력
    """
    successions = []
    for doc in doc_list:
        dtype = doc.get("doc_type", "")
        text  = doc.get("_텍스트", "") or ""
        if dtype in ("증여계약서", "명의변경계약서", "권리의무승계계약서"):
            stype = "증여" if dtype == "증여계약서" else detect_succession_type(text)
            m = re.search(r"(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일", text)
            date_str = f"{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)}" if m else ""
            successions.append({"type": stype, "date": date_str, "doc": doc})

    if not successions:
        return {"승계여부": "해당없음", "승계일": "", "승계횟수": 0}

    # ★ 마지막 승계 기준
    last = successions[-1]
    count = len(successions)
    label = f"승계({last['type']})"
    if count > 1:
        label = f"승계({last['type']}) {count}회"

    return {
        "승계여부":  label,
        "승계일":    last["date"],
        "승계횟수":  count,
        "_last_doc": last["doc"],   # 마지막 승계 문서 (성명 등 참조용)
    }


# ── 미비서류 자동 체크 ────────────────────────────────────────────────────────

DOC_NAMES = {
    "분양계약서":       "분양계약서",
    "선택품목계약서":   "선택품목계약서",
    "발코니확장계약서": "발코니확장계약서",
    "근저당설정계약서": "근저당설정계약서",
    "주민등록초본":     "주민등록초본",
    "주민등록등본":     "주민등록등본",
    "인감증명서":       "인감증명서",
    "증여계약서":       "증여계약서(권리의무승계)",
    "명의변경계약서":   "명의변경계약서(권리의무승계)",
    "거래신고필증":     "거래신고필증",
    "가족관계증명서":   "가족관계증명서",
    "위임장":           "위임장",
}


def check_missing_docs(found_types: list, has_loan: bool = True,
                        has_succession: bool = False,
                        succession_type: str = "") -> str:
    """
    필수서류 미비 체크.
    분양 기본 필수: 분양계약서, 주민등록초본, 인감증명서
    대출 있으면:    + 근저당설정계약서
    승계(매매):     + 명의변경계약서 + 거래신고필증
    승계(증여):     + 증여계약서
    """
    required = ["분양계약서", "주민등록초본", "인감증명서"]
    if has_loan:
        required.append("근저당설정계약서")
    if has_succession:
        if succession_type == "증여":
            required.append("증여계약서")
        else:
            required.append("명의변경계약서")
            required.append("거래신고필증")

    found_set = set(found_types)
    missing = [DOC_NAMES.get(r, r) for r in required if r not in found_set]
    return ", ".join(missing) if missing else "없음"
