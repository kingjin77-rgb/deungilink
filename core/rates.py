"""
세율·보수표 외부화 로더 (rates)
================================
data/rates_2026.json 에서 취득세율·법무사 보수표·채권매입율·인지대 구간·
신탁말소 단가·고정비를 로드한다. 법령/보수표 개정 시 JSON 만 수정하면
tax_calculator / cost_calculator 전체에 반영된다.

- JSON 의 null 은 float('inf') 로 변환 (구간 상한 무한대).
- load_rates() 는 캐시된 dict 를 반환. reload_rates() 로 강제 재로딩.
"""

import json
from pathlib import Path

_RATES_PATH = Path(__file__).resolve().parent.parent / "data" / "rates_2026.json"

_cache = None


def _to_inf(v):
    """JSON null → 무한대(구간 상한)."""
    return float("inf") if v is None else v


def _convert_brackets(brackets):
    """[[상한|null, 값], ...] → [(상한|inf, 값), ...]"""
    return [(_to_inf(b[0]), b[1]) for b in brackets]


def _convert_progressive(rows):
    """[[시작, 끝|null, 율], ...] → [(시작, 끝|inf, 율), ...]"""
    return [(r[0], _to_inf(r[1]), r[2]) for r in rows]


def load_rates() -> dict:
    """rates_2026.json 로드 (캐시). 구간 데이터는 inf 변환된 튜플 리스트로 후처리."""
    global _cache
    if _cache is not None:
        return _cache

    with open(_RATES_PATH, encoding="utf-8") as f:
        raw = json.load(f)

    # 구간 데이터 후처리 (inf 변환)
    raw["stamp_duty"]["transfer_brackets"] = _convert_brackets(raw["stamp_duty"]["transfer_brackets"])
    raw["stamp_duty"]["mortgage_brackets"] = _convert_brackets(raw["stamp_duty"]["mortgage_brackets"])
    raw["fee_transfer_base"] = _convert_brackets(raw["fee_transfer_base"])
    raw["fee_mortgage_base"] = _convert_brackets(raw["fee_mortgage_base"])
    raw["fee_progressive"] = _convert_progressive(raw["fee_progressive"])

    _cache = raw
    return _cache


def reload_rates() -> dict:
    """캐시를 비우고 다시 로드 (설정 변경 후 호출)."""
    global _cache
    _cache = None
    return load_rates()


# ── 편의 접근자 ──────────────────────────────────────────────────────────────

def acquisition() -> dict:
    return load_rates()["acquisition_tax"]


def bond() -> dict:
    return load_rates()["bond"]


def stamp_transfer_brackets():
    return load_rates()["stamp_duty"]["transfer_brackets"]


def stamp_mortgage_brackets():
    return load_rates()["stamp_duty"]["mortgage_brackets"]


def fee_transfer_base():
    return load_rates()["fee_transfer_base"]


def fee_mortgage_base():
    return load_rates()["fee_mortgage_base"]


def fee_progressive():
    return load_rates()["fee_progressive"]


def fee_progressive_start() -> int:
    return load_rates()["fee_progressive_start"]


def fee_vat_rate() -> float:
    return load_rates()["fee_vat_rate"]


def mortgage_registration() -> dict:
    return load_rates()["mortgage_registration"]


def trust_cancellation() -> dict:
    return load_rates()["trust_cancellation"]


def fixed_costs() -> dict:
    return load_rates()["fixed_costs"]
