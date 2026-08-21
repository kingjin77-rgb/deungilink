"""
Claude Vision 구조화 추출 엔진 (vision_extract)
================================================
정규식 하드코딩 파서(core/extractor.py)를 대체하는 실전 코어.

스캔 PDF(이미지)를 Claude Vision 에 이미지로 전달하고, schema.py 로 생성한
JSON 스키마에 맞춰 서류 유형 분류 + 필드 추출을 한 번에 수행한다.
→ 신규 단지/서식이 와도 정규식 수정 없이 자동 대응.

설계 원칙:
  • 순수 함수(build_extraction_prompt / parse_vision_json / normalize_record)는
    API 없이 단위 테스트 가능.
  • API 키 없으면 extract_unit() 이 None 반환 → 호출측이 정규식 경로로 폴백.
  • Claude 응답은 반드시 JSON. 파싱 실패/부분 응답도 견고하게 처리.
"""

import json
import re
from pathlib import Path

from core.schema import DOC_SCHEMA, FIELD_DESC, field_type
from core.extractor import normalize_date, clean_amount


# ══════════════════════════════════════════════════════════════════════
#  1. 프롬프트 생성 (순수 함수)
# ══════════════════════════════════════════════════════════════════════

def build_extraction_prompt(doc_types=None) -> str:
    """
    schema.py 기반으로 Vision 추출 지시문 생성.
    doc_types 를 주면 그 유형만, 없으면 전체 유형.
    """
    types = doc_types or list(DOC_SCHEMA.keys())

    lines = [
        "당신은 한국 부동산 등기 서류 판독 전문가입니다.",
        "첨부된 이미지들은 한 세대(집)의 등기 관련 서류 묶음입니다.",
        "각 서류의 종류를 식별하고, 아래 스키마에 따라 정보를 정확히 추출하세요.",
        "",
        "【추출 가능한 서류 유형과 필드】",
    ]
    for dt in types:
        fields = DOC_SCHEMA.get(dt, [])
        lines.append(f"■ {dt}")
        for f in fields:
            lines.append(f"   - {f}: {FIELD_DESC.get(f, f)}")
    lines += [
        "",
        "【출력 형식】 — 반드시 아래 JSON 만 출력 (설명·마크다운 금지):",
        '{',
        '  "documents": [',
        '    {"doc_type": "서류유형", "fields": {"필드명": "값", ...}, "confidence": 0.0~1.0},',
        '    ...',
        '  ]',
        '}',
        "",
        "【규칙】",
        "1. 날짜는 모두 YYYY-MM-DD 형식.",
        "2. 금액은 숫자만 (콤마·'원' 제거). 없으면 필드 생략.",
        "3. 추출 못 한 필드는 넣지 말 것(추측 금지). 워터마크·배경 문구 무시.",
        "4. 성명은 개명 시 '변경 후(현재)' 이름. 주소는 최신 1건만.",
        "5. 승계여부는 매매면 '승계(매매)', 증여면 '승계(증여)'.",
        "6. confidence 는 판독 확신도(흐림·부분가림이면 낮게).",
        "7. 같은 서류가 여러 장이면 하나로 합쳐 1개 document 로.",
    ]
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════
#  2. 응답 파싱 (순수 함수)
# ══════════════════════════════════════════════════════════════════════

def parse_vision_json(text: str) -> dict:
    """
    Claude 응답 문자열에서 JSON 추출. 코드펜스·앞뒤 잡텍스트 제거 후 파싱.
    실패 시 {"documents": []} 반환.
    """
    if not text:
        return {"documents": []}
    s = text.strip()
    # ```json ... ``` 펜스 제거
    s = re.sub(r"^```(?:json)?\s*", "", s)
    s = re.sub(r"\s*```$", "", s)
    # 첫 { 부터 마지막 } 까지
    start = s.find("{")
    end = s.rfind("}")
    if start >= 0 and end > start:
        s = s[start:end + 1]
    try:
        data = json.loads(s)
    except json.JSONDecodeError:
        return {"documents": []}
    if not isinstance(data, dict):
        return {"documents": []}
    data.setdefault("documents", [])
    if not isinstance(data["documents"], list):
        data["documents"] = []
    return data


# ══════════════════════════════════════════════════════════════════════
#  3. 값 정규화 (순수 함수)
# ══════════════════════════════════════════════════════════════════════

def normalize_value(field: str, raw):
    """필드 타입에 맞춰 값 정규화. 빈 값이면 None."""
    if raw is None:
        return None
    t = field_type(field)
    if t == "int":
        v = clean_amount(raw)
        return v
    if t == "float":
        try:
            return float(str(raw).replace(",", "").strip())
        except (ValueError, TypeError):
            return None
    if t == "date":
        s = str(raw).strip()
        if not s:
            return None
        # 이미 YYYY-MM-DD 면 그대로, 아니면 정규화
        if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
            return s
        norm = normalize_date(s)
        return norm or None
    # str
    s = str(raw).strip()
    return s or None


def normalize_record(fields: dict) -> dict:
    """서류 필드 dict 를 스키마 타입에 맞춰 정규화. 빈 값은 제거."""
    out = {}
    for k, v in (fields or {}).items():
        nv = normalize_value(k, v)
        if nv not in (None, ""):
            out[k] = nv
    return out


def documents_to_records(parsed: dict) -> list:
    """
    parse_vision_json 결과 → 정규화된 서류 레코드 리스트.
    각 레코드: {doc_type, _confidence, ...정규화된 필드}
    """
    records = []
    for doc in parsed.get("documents", []):
        if not isinstance(doc, dict):
            continue
        dt = str(doc.get("doc_type", "")).strip()
        rec = normalize_record(doc.get("fields", {}))
        rec["doc_type"] = dt
        try:
            rec["_confidence"] = float(doc.get("confidence", 0) or 0)
        except (ValueError, TypeError):
            rec["_confidence"] = 0.0
        records.append(rec)
    return records


# ══════════════════════════════════════════════════════════════════════
#  4. 이미지 렌더링 + Vision 호출 (API 필요)
# ══════════════════════════════════════════════════════════════════════

def _pdf_to_image_blocks(pdf_path: str, dpi: int = 200, max_pages: int = 8) -> list:
    """PDF → base64 PNG 이미지 블록 리스트 (Anthropic content 형식)."""
    import base64, io
    from pdf2image import convert_from_path
    images = convert_from_path(pdf_path, dpi=dpi)[:max_pages]
    blocks = []
    for img in images:
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.standard_b64encode(buf.getvalue()).decode()
        blocks.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/png", "data": b64},
        })
    return blocks


def extract_unit(pdf_path: str, doc_types=None, dpi: int = 200,
                 max_pages: int = 8) -> dict:
    """
    한 세대의 결합 PDF 를 Vision 으로 구조화 추출.

    반환:
      {"records": [정규화된 서류 레코드...], "_source": "vision"}  성공 시
      None                                                        API 키 없음/실패

    호출측(engine)은 None 이면 정규식 경로로 폴백한다.
    """
    from core.appconfig import get_api_key, get_model
    key = get_api_key()
    if not key:
        return None  # → 정규식 폴백

    try:
        import anthropic
        blocks = _pdf_to_image_blocks(pdf_path, dpi=dpi, max_pages=max_pages)
        if not blocks:
            return None
        prompt = build_extraction_prompt(doc_types)
        content = blocks + [{"type": "text", "text": prompt}]
        client = anthropic.Anthropic(api_key=key)
        resp = client.messages.create(
            model=get_model(),
            max_tokens=4000,
            messages=[{"role": "user", "content": content}],
        )
        text = resp.content[0].text if resp.content else ""
        parsed = parse_vision_json(text)
        records = documents_to_records(parsed)
        return {"records": records, "_source": "vision", "_raw": text[:2000]}
    except Exception as e:
        # 크레딧 부족/네트워크 등 → 폴백 유도 (조용히 None 대신 마커)
        return {"records": [], "_source": "vision_error", "_error": str(e)[:300]}
