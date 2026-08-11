"""
Claude Vision API — 등기부등본 이미지 PDF 추출
대법원 인터넷등기소 출력물 (이미지 PDF) 전용
"""
import base64, json, re, configparser
from pathlib import Path
from io import BytesIO


def _cfg():
    c = configparser.ConfigParser()
    c.read(str(Path(__file__).parent.parent / "config.ini"), encoding="utf-8")
    return c


def _key():
    c = _cfg()
    k = c.get("claude", "api_key", fallback="").strip()
    if not k or "여기에" in k:
        k = c.get("api", "api_key", fallback="").strip()
    return k if k and "여기에" not in k else ""


def _model():
    from core.appconfig import get_model
    return get_model()


def _img_to_b64(img) -> str:
    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.standard_b64encode(buf.getvalue()).decode()


def ocr_text_with_claude(pdf_path: str) -> str:
    """이미지 PDF → Claude Vision → 텍스트"""
    import anthropic
    from pdf2image import convert_from_path

    key = _key()
    if not key:
        raise RuntimeError("Claude API 키 미설정 (settings_dialog에서 입력)")

    dpi = _cfg().getint("claude", "dpi", fallback=200)
    images = convert_from_path(pdf_path, dpi=dpi)[:4]

    content = []
    for img in images:
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/png",
                       "data": _img_to_b64(img)}
        })
    content.append({
        "type": "text",
        "text": (
            "이 집합건물 등기사항전부증명서에서 모든 텍스트를 원본 그대로 추출해주세요.\n"
            "표 안의 내용도 빠짐없이, 레이아웃을 최대한 유지하며 추출하세요.\n"
            "열람용 워터마크는 무시하세요."
        )
    })

    client = anthropic.Anthropic(api_key=key)
    r = client.messages.create(
        model=_model(), max_tokens=4000,
        messages=[{"role": "user", "content": content}]
    )
    return r.content[0].text


def extract_registry_structured(pdf_path: str) -> dict:
    """
    이미지 PDF → Claude Vision → 구조화 JSON 추출
    텍스트 추출 + 파싱을 한 번에 처리
    """
    import anthropic
    from pdf2image import convert_from_path

    key = _key()
    if not key:
        raise RuntimeError("Claude API 키 미설정")

    dpi = _cfg().getint("claude", "dpi", fallback=200)
    images = convert_from_path(pdf_path, dpi=dpi)[:4]

    content = []
    for img in images:
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/png",
                       "data": _img_to_b64(img)}
        })
    content.append({
        "type": "text",
        "text": """이 집합건물 등기사항전부증명서에서 아래 항목을 추출해서 JSON으로만 답하세요.
없는 항목은 빈 문자열. 공동명의인 경우 두 명 모두 기재.
소유자가 법인(주식회사 등)이면 성명을 빈 문자열로.

{
  "아파트명칭": "단지명 (예: 동탄파크릭스에이51-2블록아파트)",
  "동": "동 숫자만, 선행0 제거 (예: 3821)",
  "호": "호 숫자만, 선행0 제거 (예: 201)",
  "전용면적": "전유부분 건물면적 숫자만 (예: 84.9419)",
  "건물등기접수일자": "소유권이전 접수일 YYYY-MM-DD (이전 없으면 보존등기일)",
  "소유형태": "개별 또는 공동",
  "성명": "최신 소유자 성명 (개인만, 법인 제외)",
  "공동명의자": "공동소유자 성명 (없으면 빈값)",
  "주소": "소유자 주소 전체",
  "신탁유무": "있음 또는 없음",
  "국적": "외국인이면 외국인, 내국인이면 빈값"
}"""
    })

    client = anthropic.Anthropic(api_key=key)
    r = client.messages.create(
        model=_model(), max_tokens=1000,
        messages=[{"role": "user", "content": content}]
    )
    raw = r.content[0].text
    clean = re.sub(r"```(?:json)?", "", raw).strip().replace("```", "")
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]+\}", clean)
        if m:
            return json.loads(m.group(0))
        return {}
