"""
취득세 자동 계산 모듈
실무 수식 그대로 적용:
=ROUNDDOWN(IF(AND(감면="생애최초",600000000>과표),과표*1%-2000000,
IF(AND(감면="생애최초",900000000<과표),과표*3%-2000000,
IF(AND(감면="생애최초",600000000<과표),과표*누진세율-2000000,
IF(AND(감면="해당없음",과표<600000000),과표*1%,
IF(AND(감면="해당없음",과표>900000000),과표*3%,
IF(AND(감면="해당없음",과표>600000000),과표*누진세율,
과표*누진세율)))))),-1)
"""

import math

from core.rates import acquisition


def _round_down_10(v: float) -> int:
    """ROUNDDOWN(..., -1) : 10원 단위 절사"""
    return int(v // 10) * 10


def _누진세율(과표: int) -> float:
    """ROUND(mult*(과표/div)-sub, n) / 100  — 파라미터는 rates_2026.json"""
    f = acquisition()["single_home"]["progressive_formula"]
    rate_pct = round(f["mult"] * (과표 / f["div"]) - f["sub"], f["round_decimals"])
    return rate_pct / 100


def calc_취득세_1주택(과표: int, 감면: str) -> int:
    """
    1주택 취득세 — 실무 수식 완전 동일 적용
    감면: "생애최초" | "해당없음" | "" (해당없음과 동일 처리)
    세율·구간·감면액은 rates_2026.json 에서 로드.
    """
    감면 = 감면 or "해당없음"
    sh   = acquisition()["single_home"]
    low  = sh["low_threshold"]     # 6억
    high = sh["high_threshold"]    # 9억
    lr   = sh["low_rate"]          # 1%
    hr   = sh["high_rate"]         # 3%
    감면액 = acquisition()["first_time_buyer_deduction"]

    if 감면 == "생애최초":
        if low > 과표:                               # 6억 미만
            세금 = 과표 * lr - 감면액
        elif high < 과표:                            # 9억 초과
            세금 = 과표 * hr - 감면액
        else:                                        # 6억~9억 누진
            세금 = 과표 * _누진세율(과표) - 감면액
    else:  # 해당없음 (기타 모두 포함)
        if 과표 < low:                               # 6억 미만
            세금 = 과표 * lr
        elif 과표 > high:                            # 9억 초과
            세금 = 과표 * hr
        elif 과표 > low:                             # 6억~9억 누진
            세금 = 과표 * _누진세율(과표)
        else:                                        # 경계값 fallback
            세금 = 과표 * _누진세율(과표)

    return _round_down_10(세금)


def calc_취득세_다주택(과표: int, 주택수: int, 조정대상지역: bool = True) -> int:
    """
    다주택 취득세 — rates_2026.json 의 multi_home 세율.
    조정대상지역=True(기본): 2주택 8%, 3주택+ 12%
    조정대상지역=False:       2~3주택 8%, 4주택+ 12% (비조정 확장)
    """
    mh = acquisition()["multi_home"]
    if 조정대상지역:
        rate = mh["adjusted"]["2"] if 주택수 == 2 else mh["adjusted"]["3plus"]
    else:
        na = mh["non_adjusted"]
        if 주택수 == 2:
            rate = na["2"]
        elif 주택수 == 3:
            rate = na["3"]
        else:
            rate = na["4plus"]
    return _round_down_10(과표 * rate)


def calc_과표(record: dict) -> int:
    """
    취득세과표(BL) 계산
    - 분양전환아파트: 전환매매가(거래가액) + 옵션
    - 승계(매매):     거래가액 + 옵션
    - 분양아파트:     분양대금 + 부가세 + 옵션
    """
    승계       = record.get("승계여부", "")
    아파트유형  = record.get("아파트유형", "분양")
    발코니     = _int(record.get("발코니금액", 0))
    옵션       = _int(record.get("옵션금액", 0))

    if 아파트유형 == "분양전환":
        전환매매가 = _int(record.get("거래가액", 0)) or _int(record.get("분양대금", 0))
        return 전환매매가 + 발코니 + 옵션
    elif 승계 == "승계(매매)":
        return _int(record.get("거래가액", 0)) + 발코니 + 옵션
    else:
        return (_int(record.get("분양대금", 0))
                + _int(record.get("부가세", 0))
                + 발코니 + 옵션)


def calc_취득세(record: dict) -> dict:
    """
    취득세 전체 계산 후 딕셔너리 반환
    {취득세과표, 취득세, 교육세, 농특세, 취득세합계, 감면액, 적용세율}
    """
    과표    = calc_과표(record)
    주택수  = _int(record.get("주택수", 1)) or 1
    감면    = record.get("감면여부", "") or "해당없음"
    전용면적 = _float(record.get("전용면적", 0))

    조정대상지역 = record.get("조정대상지역", True)
    조정대상지역 = True if 조정대상지역 in (None, "") else bool(조정대상지역)

    # ── 취득세 ──────────────────────────────────────────
    if 주택수 == 1:
        취득세 = calc_취득세_1주택(과표, 감면)
    else:
        취득세 = calc_취득세_다주택(과표, 주택수, 조정대상지역)

    # ── 감면액 역산 (표시용) ────────────────────────────
    감면액 = 0
    if 감면 == "생애최초" and 주택수 == 1:
        감면액 = acquisition()["first_time_buyer_deduction"]

    # ── 교육세: 취득세 × 교육세율 ───────────────────────
    교육세 = _round_down_10(취득세 * acquisition()["education_tax_rate"])

    # ── 농특세: 기준면적 이하 비과세, 초과 시 과표×율 ──
    _rt = acquisition()["rural_tax"]
    농특세 = 0 if 전용면적 <= _rt["exempt_area_max"] else _round_down_10(과표 * _rt["rate"])

    취득세합계 = 취득세 + 교육세 + 농특세

    # 적용세율 계산 (표시용)
    세율 = (취득세 + 감면액) / 과표 if 과표 else 0

    return {
        "취득세과표":  과표,
        "취득세":     취득세,
        "교육세":     교육세,
        "농특세":     농특세,
        "취득세합계": 취득세합계,
        "감면액":     감면액,
        "적용세율":   f"{세율*100:.2f}%",
    }


# ── 유틸 ─────────────────────────────────────────────────────────────────────
def _int(v) -> int:
    try:
        return int(str(v).replace(",", "").strip()) if v else 0
    except:
        return 0

def _float(v) -> float:
    try:
        return float(str(v).replace(",", "").strip()) if v else 0.0
    except:
        return 0.0
