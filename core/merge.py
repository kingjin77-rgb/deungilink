"""
서류 신뢰도 기반 필드 병합 (merge)
==================================
여러 서류에서 추출한 값이 충돌할 때, "어떤 서류의 값을 믿을지"를
필드별 우선순위 + Vision confidence 로 결정한다.

기존 processor.merge_unit_records 는 FIELD_SOURCE_PRIORITY 딕셔너리를
정의만 하고 실제로는 'PDF 파일 순서'에 의존했다(설계-구현 괴리).
이 모듈이 그 우선순위를 실제로 구현한다.

병합 규칙(필드별):
  1. 값이 있는(빈문자/None 아닌) 서류 후보만 대상.
  2. 필드 우선순위 목록에서 서류 유형의 순번이 빠를수록 우선.
     (목록에 없는 유형은 맨 뒤)
  3. 동순위면 Vision confidence 높은 값.
  4. 그래도 같으면 먼저 등장한 값.
"""

# ── 필드별 서류 신뢰 우선순위 (앞이 우선) ────────────────────────────────────
FIELD_SOURCE_PRIORITY = {
    "성명":         ["명의변경계약서", "증여계약서", "주민등록초본", "주민등록등본",
                     "인감증명서", "등기부등본", "분양계약서"],
    "주민등록번호": ["주민등록초본", "주민등록등본", "인감증명서", "증여계약서", "분양계약서"],
    "주소":         ["주민등록초본", "주민등록등본", "등기부등본"],
    "전화번호":     ["주민등록초본", "주민등록등본", "분양계약서", "근저당설정계약서",
                     "명의변경계약서", "증여계약서"],
    "전용면적":     ["분양계약서", "등기부등본"],
    "대지지분":     ["분양계약서", "등기부등본"],
    "동":           ["분양계약서", "등기부등본"],
    "호":           ["분양계약서", "등기부등본"],
    "분양대금":     ["분양계약서"],
    "부가세":       ["분양계약서"],
    "분양계약일":   ["분양계약서"],
    "발코니금액":   ["선택품목계약서", "발코니확장계약서", "분양계약서"],
    "옵션금액":     ["선택품목계약서"],
    "채권최고액":   ["근저당설정계약서"],
    "대출은행":     ["근저당설정계약서"],
    "대출지점":     ["근저당설정계약서"],
    "근저당설정계약일": ["근저당설정계약서"],
    "거래가액":     ["거래신고필증", "명의변경계약서"],
    "거래신고필증번호": ["거래신고필증"],
    "초본발행일":   ["주민등록초본"],
    "등본발행일":   ["주민등록등본"],
    "인감발행일":   ["인감증명서"],
    "건물등기접수일자": ["등기부등본"],
    "세대원수":     ["주민등록등본"],
    "양도인성명":   ["명의변경계약서", "증여계약서"],
    "증여지분":     ["증여계약서"],
    "국적":         ["등기부등본"],
    "공동명의자":   ["등기부등본"],
    # 세대별 신탁 — 등기부등본에서 (단지 전체 획일 적용 아님)
    "신탁건수":     ["등기부등본"],
    "신탁유무":     ["등기부등본"],
}

# 0 도 유효값으로 인정할 필드 (그 외 필드는 0/빈값을 '없음'으로 취급)
_ZERO_OK = {"부가세", "거래가액", "세대원수", "신탁건수"}


def _is_empty(field: str, v) -> bool:
    if v is None:
        return True
    if isinstance(v, str) and v.strip() == "":
        return True
    if v == 0 and field not in _ZERO_OK:
        return True
    return False


def merge_documents(records: list) -> dict:
    """
    서류 레코드 리스트 → 필드별 우선순위/신뢰도 병합된 단일 dict.
    각 레코드는 doc_type, (선택)_confidence, 그리고 필드들을 가진다.
    '_' 로 시작하는 키와 doc_type 은 결과에 포함하지 않는다.
    """
    # 모든 필드명 수집
    fields = set()
    for r in records:
        for k in r:
            if not k.startswith("_") and k != "doc_type":
                fields.add(k)

    merged = {}
    for field in fields:
        prio = FIELD_SOURCE_PRIORITY.get(field)
        best_key = None
        best_val = None
        for idx, r in enumerate(records):
            v = r.get(field)
            if _is_empty(field, v):
                continue
            dt = r.get("doc_type", "")
            if prio:
                pi = prio.index(dt) if dt in prio else len(prio) + 1
            else:
                pi = 0
            conf = r.get("_confidence", 0) or 0
            # 정렬키: (우선순위 작을수록, confidence 클수록, 먼저 등장할수록)
            key = (pi, -conf, idx)
            if best_key is None or key < best_key:
                best_key = key
                best_val = v
        if best_val is not None:
            merged[field] = best_val

    # ── 서류별 실패 승격 ────────────────────────────────────────────────
    # 위 루프는 '_' 로 시작하는 키를 전부 버린다. 그러나 개별 서류의 OCR/추출
    # 실패(_오류)까지 버리면, 5개 PDF 중 3개가 실패해도 세대 레코드에는 아무
    # 흔적이 없어 "완료"로 표시된다. 실패 사실만은 반드시 위로 올린다.
    서류오류 = []
    for r in records:
        err = r.get("_오류")
        if err:
            파일 = r.get("_파일명") or r.get("doc_type") or "서류"
            서류오류.append(f"{파일}: {str(err)[:80]}")
    if 서류오류:
        merged["_서류오류"] = 서류오류

    return merged
