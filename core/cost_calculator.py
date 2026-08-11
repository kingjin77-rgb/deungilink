"""
등기비용 자동 계산 모듈
소유권이전 + 근저당설정 전체 비용 산출
"""

import math
import configparser
from pathlib import Path


# ─── 설정 로드 ────────────────────────────────────────────────────────────────

def _load_config() -> dict:
    """
    config.ini [cost] 값을 읽되, 없으면 rates_2026.json 기본값으로 폴백.
    → 채권율·증지대·고정비는 config.ini 로 현장별 조정, 미설정 시 외부 세율표 사용.
    """
    from core.rates import bond, fixed_costs
    b  = bond()
    fc = fixed_costs()

    cfg = configparser.ConfigParser()
    cfg.read(str(Path(__file__).parent.parent / "config.ini"), encoding="utf-8")

    def _pct(key, default_dec):
        raw = cfg.get("cost", key, fallback="").strip()
        if raw == "":
            return default_dec
        try:
            return float(raw) / 100
        except ValueError:
            return default_dec

    def _intv(key, default):
        try:
            return cfg.getint("cost", key, fallback=default)
        except ValueError:
            return default

    return {
        "채권할인율":       _pct("채권할인율",     b["discount_rate"]),
        "이전채권매입율":   _pct("이전채권매입율", b["transfer_purchase_rate_small"]),
        "이전채권매입율_대형": b["transfer_purchase_rate_large"],
        "이전채권_기준면적":  b["transfer_area_threshold"],
        "설정채권매입율":   _pct("설정채권매입율", b["mortgage_purchase_rate"]),
        "증지대_이전":      _intv("증지대_이전", fc["revenue_stamp_transfer"]),
        "증지대_설정":      _intv("증지대_설정", fc["revenue_stamp_mortgage"]),
        "교통비":           _intv("교통비",     fc["transport"]),
        "제증명료":         _intv("제증명료",   fc["certificate"]),
        "송달료":           _intv("송달료",     fc["delivery"]),
    }

CFG = _load_config()


# ─── 채권매입금액 ─────────────────────────────────────────────────────────────

def calc_이전채권(과표: int, 기준시가: int, 아파트유형: str, 전용면적: float) -> dict:
    """
    소유권이전 채권매입금액 계산
    분양아파트:     취득세과표 × 매입율
    분양전환아파트: 전환매매가(= 과표) × 매입율  ← 동일 기준으로 통일
    """
    # 면적에 따른 매입율 (기준면적 이하 소형율, 초과 대형율) — rates_2026.json
    매입율 = (CFG["이전채권매입율"] if 전용면적 <= CFG["이전채권_기준면적"]
             else CFG["이전채권매입율_대형"])

    # 분양전환도 과표(=전환매매가) 기준으로 통일
    기준금액 = 과표
    채권매입금액 = _round1000(기준금액 * 매입율)
    채권할인금액 = _round10(채권매입금액 * CFG["채권할인율"])

    return {
        "채권매입금액_이전": 채권매입금액,
        "채권할인금액_이전": 채권할인금액,
    }


def calc_설정채권(채권최고액: int) -> dict:
    """근저당 설정 채권매입금액"""
    매입율 = CFG["설정채권매입율"]
    채권매입금액 = _round1000(채권최고액 * 매입율)
    채권할인금액 = _round10(채권매입금액 * CFG["채권할인율"])
    return {
        "채권매입금액_설정": 채권매입금액,
        "채권할인금액_설정": 채권할인금액,
    }


# ─── 인지대 ──────────────────────────────────────────────────────────────────

def calc_인지대_이전(취득가액: int) -> int:
    """소유권이전 인지대 — 매수인 단독 부담 (구간표: rates_2026.json)"""
    from core.rates import stamp_transfer_brackets
    브래킷 = stamp_transfer_brackets()
    for 상한, 금액 in 브래킷:
        if 취득가액 < 상한:
            return 금액
    return 브래킷[-1][1]


def calc_인지대_설정(채권최고액: int) -> int:
    """근저당설정 인지대 (구간표: rates_2026.json)"""
    from core.rates import stamp_mortgage_brackets
    브래킷 = stamp_mortgage_brackets()
    for 상한, 금액 in 브래킷:
        if 채권최고액 < 상한:
            return 금액
    return 브래킷[-1][1]


# ─── 법무사 등기보수표 ────────────────────────────────────────────────────────
# 대한법무사협회 표준 보수규정 — 표는 rates_2026.json 으로 외부화됨.

def _기본보수(가액: int, 기본표) -> int:
    기본보수 = 기본표[-1][1]
    for 상한, 보수 in 기본표:
        if 가액 <= 상한:
            return 보수
    return 기본보수


def _누진료(가액: int) -> float:
    """목적가액 초과분 × 율 (구간: rates_2026.json)"""
    from core.rates import fee_progressive, fee_progressive_start
    구간 = fee_progressive()
    start = fee_progressive_start()
    누진 = 0
    if 가액 > start:
        prev = start
        for 시작, 끝, 율 in 구간:
            if 가액 <= 시작:
                break
            초과분 = min(가액, 끝) - max(prev, 시작)
            if 초과분 > 0:
                누진 += 초과분 * 율
            prev = 끝
    return 누진


def calc_보수료_이전(목적가액: int) -> dict:
    """소유권이전등기 보수료 (기본보수 + 누진료)"""
    from core.rates import fee_transfer_base, fee_vat_rate
    보수료합계 = _round10(_기본보수(목적가액, fee_transfer_base()) + _누진료(목적가액))
    부가세 = _round10(보수료합계 * fee_vat_rate())
    return {"보수료": 보수료합계, "부가세_이전": 부가세}


def calc_보수료_설정(채권최고액: int) -> dict:
    """근저당설정등기 보수료"""
    from core.rates import fee_mortgage_base, fee_vat_rate
    보수료합계 = _round10(_기본보수(채권최고액, fee_mortgage_base()) + _누진료(채권최고액))
    부가세 = _round10(보수료합계 * fee_vat_rate())
    return {"보수료_설정": 보수료합계, "부가세_설정": 부가세}


# ─── 설정 등록면허세 ──────────────────────────────────────────────────────────

def calc_설정등록세(채권최고액: int) -> dict:
    """근저당설정 등록면허세 + 교육세 (율: rates_2026.json)"""
    from core.rates import mortgage_registration
    mr = mortgage_registration()
    등록세 = _round10(채권최고액 * mr["license_tax_rate"])
    교육세 = _round10(등록세 * mr["education_tax_rate"])
    return {"등록세_설정": 등록세, "교육세_설정": 교육세}


# ─── 전체 비용 통합 계산 ──────────────────────────────────────────────────────

def calc_등기비용(record: dict) -> dict:
    """
    소유권이전 + 근저당설정 전체 등기비용 계산
    """
    # 기본 데이터
    과표       = int(record.get("취득세과표", 0) or 0)
    기준시가    = int(record.get("기준시가", 0) or 0)
    채권최고액  = int(record.get("채권최고액", 0) or 0)
    전용면적    = float(str(record.get("전용면적", 0) or 0))
    아파트유형  = record.get("아파트유형", "분양")  # "분양" | "분양전환"
    취득세합계  = int(record.get("취득세합계", 0) or 0)

    result = {}

    # ── 1. 이전채권 ─────────────────────────────────────────────────────
    r = calc_이전채권(과표, 기준시가, 아파트유형, 전용면적)
    result.update(r)

    # ── 2. 인지대 ───────────────────────────────────────────────────────
    result["인지대_이전"] = calc_인지대_이전(과표)
    if 채권최고액:
        result["인지대_설정"] = calc_인지대_설정(채권최고액)

    # ── 3. 증지대 ───────────────────────────────────────────────────────
    result["증지대_이전"] = CFG["증지대_이전"]
    if 채권최고액:
        result["증지대_설정"] = CFG["증지대_설정"]

    # ── 4. 이전 보수료 ──────────────────────────────────────────────────
    r = calc_보수료_이전(과표)
    result.update(r)

    # ── 5. 설정 비용 ────────────────────────────────────────────────────
    if 채권최고액:
        r = calc_설정등록세(채권최고액)
        result.update(r)
        r = calc_설정채권(채권최고액)
        result.update(r)
        r = calc_보수료_설정(채권최고액)
        result.update(r)

    # ── 6. 고정비용 (config) ────────────────────────────────────────────
    result["교통비"]   = CFG["교통비"]
    result["제증명료"] = CFG["제증명료"]
    result["송달료"]   = CFG["송달료"]

    # ── 6-1. 신탁말소 비용 ─────────────────────────────────────────────
    신탁건수 = int(record.get("신탁건수", 0) or 0)
    신탁 = calc_신탁말소(신탁건수)
    result.update(신탁)

    # ── 7. 이전 등기비용 합계 ───────────────────────────────────────────
    이전소계 = (
        취득세합계
        + result.get("채권매입금액_이전", 0)
        - result.get("채권할인금액_이전", 0)
        + result.get("인지대_이전", 0)
        + result.get("증지대_이전", 0)
        + result.get("보수료", 0)
        + result.get("부가세_이전", 0)
        + result.get("교통비", 0)
        + result.get("제증명료", 0)
        + result.get("송달료", 0)
        + result.get("신탁말소비용", 0)
    )

    # ── 8. 설정 비용 합계 ───────────────────────────────────────────────
    설정소계 = (
        result.get("등록세_설정", 0)
        + result.get("교육세_설정", 0)
        + result.get("채권매입금액_설정", 0)
        - result.get("채권할인금액_설정", 0)
        + result.get("인지대_설정", 0)
        + result.get("증지대_설정", 0)
        + result.get("보수료_설정", 0)
        + result.get("부가세_설정", 0)
    )

    result["이전비용합계"] = 이전소계
    result["설정비용합계"] = 설정소계
    result["등기비용총합계"] = 이전소계 + 설정소계

    return result


# ─── 유틸 ────────────────────────────────────────────────────────────────────

def _round10(v: float) -> int:
    return int(v // 10) * 10

def _round1000(v: float) -> int:
    return int(v // 1000) * 1000


# ─── 신탁말소 비용 ────────────────────────────────────────────────────────────

def calc_신탁말소(신탁건수: int) -> dict:
    """
    신탁말소 비용 계산 (단가: rates_2026.json, 보수료 단가는 config.ini override)
    신탁건수: 등기부등본에서 추출한 신탁 건수
    """
    if not 신탁건수 or 신탁건수 <= 0:
        return {"신탁말소비용": 0, "신탁건수": 0, "신탁유무": "없음"}

    from core.rates import trust_cancellation
    tc = trust_cancellation()

    # config.ini 로 보수료 단가 override (미설정 시 rates 기본값)
    cfg = configparser.ConfigParser()
    cfg.read(str(Path(__file__).parent.parent / "config.ini"), encoding="utf-8")
    보수료단가 = cfg.getint("cost", "신탁말소_보수료단가", fallback=tc["fee"])

    부가세단가 = _round10(보수료단가 * tc["vat_rate"])
    건당 = (tc["license_tax"] + tc["education_tax"] + tc["revenue_stamp"]
            + 보수료단가 + 부가세단가)
    합계 = 건당 * 신탁건수

    return {
        "신탁유무":          "있음",
        "신탁건수":          신탁건수,
        "신탁말소_등록면허세": tc["license_tax"] * 신탁건수,
        "신탁말소_교육세":    tc["education_tax"] * 신탁건수,
        "신탁말소_증지대":    tc["revenue_stamp"] * 신탁건수,
        "신탁말소_보수료":    보수료단가 * 신탁건수,
        "신탁말소_부가세":    부가세단가 * 신탁건수,
        "신탁말소비용":       합계,
    }
