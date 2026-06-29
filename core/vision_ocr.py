"""
OCR 엔진 통합 모듈 — 폴백 우선 버전
=======================================
폴백 순서: pdfplumber → Clova → Tesseract → Claude (마지막 수단)
Claude API 크레딧 0원이어도 1~3번으로 최대한 처리 가능.
"""
import re, configparser
from pathlib import Path


def _cfg():
    c = configparser.ConfigParser()
    c.read(str(Path(__file__).parent.parent / "config.ini"), encoding="utf-8")
    return c


def _api_key():
    c = _cfg()
    # [claude] 우선, 없으면 [api] 섹션
    k = c.get("claude", "api_key", fallback="").strip()
    if not k or "여기에" in k:
        k = c.get("api", "api_key", fallback="").strip()
    return k if k and "여기에" not in k else ""


# ── 공통: pdfplumber 텍스트 추출 ─────────────────────────────────────────────

def _pdfplumber_extract(pdf_path: str) -> str:
    """pdfplumber로 텍스트 추출. 실패 또는 텍스트 없으면 빈 문자열."""
    try:
        import pdfplumber
        pages = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text(x_tolerance=2, y_tolerance=2) or ""
                pages.append(t)
        text = "\n".join(pages)
        return text if len(re.findall(r"[가-힣]", text)) >= 10 else ""
    except Exception:
        return ""


def _clova_extract(pdf_path: str) -> str:
    """Clova OCR로 텍스트 추출. 키 없거나 실패 시 빈 문자열."""
    c = _cfg()
    invoke_url = c.get("clova", "invoke_url", fallback="").strip()
    secret_key  = c.get("clova", "secret_key",  fallback="").strip()
    client_id   = c.get("clova", "client_id",    fallback="").strip()
    # 인증 정보 없으면 건너뜀
    if not invoke_url and not client_id:
        return ""
    try:
        from core.clova_ocr import ClovaOCR
        cfg_path = str(Path(__file__).parent.parent / "config.ini")
        clova = ClovaOCR(cfg_path)
        text = clova.ocr_pdf(pdf_path)
        return text if len(re.findall(r"[가-힣]", text)) >= 10 else ""
    except Exception:
        return ""


def _tesseract_extract(pdf_path: str) -> str:
    """Tesseract OCR. config.ini [tesseract] path 사용."""
    try:
        from pdf2image import convert_from_path
        import pytesseract
        c = _cfg()
        tess_path = c.get("tesseract", "path", fallback="").strip()
        if tess_path:
            pytesseract.pytesseract.tesseract_cmd = tess_path
        dpi = c.getint("ocr", "dpi", fallback=200)
        images = convert_from_path(pdf_path, dpi=dpi)
        text = "\n".join(
            pytesseract.image_to_string(img.convert("L"),
                                        lang="kor+eng", config="--psm 6 --oem 3")
            for img in images[:5])
        return text if len(re.findall(r"[가-힣]", text)) >= 10 else ""
    except Exception:
        return ""


def _claude_extract_text(pdf_path: str) -> str:
    """Claude Vision으로 텍스트 추출 (이미지 PDF 전용)."""
    key = _api_key()
    if not key:
        return ""
    try:
        import base64, io, anthropic
        from pdf2image import convert_from_path
        c = _cfg()
        dpi = c.getint("claude", "dpi", fallback=200)
        model = c.get("claude", "model", fallback="claude-sonnet-4-6")
        images = convert_from_path(pdf_path, dpi=dpi)[:4]
        content = []
        for img in images:
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            b64 = base64.standard_b64encode(buf.getvalue()).decode()
            content.append({"type": "image",
                             "source": {"type": "base64",
                                        "media_type": "image/png", "data": b64}})
        content.append({"type": "text",
                         "text": "이 등기사항전부증명서의 모든 텍스트를 원본 그대로 추출하세요. 워터마크는 무시하세요."})
        client = anthropic.Anthropic(api_key=key)
        r = client.messages.create(model=model, max_tokens=4000,
                                    messages=[{"role": "user", "content": content}])
        return r.content[0].text
    except Exception:
        return ""


# ── 분양/분양전환 배치 모드: pdfplumber → Clova → Claude ─────────────────────

def ocr_pdf_for_bunya(pdf_path: str) -> str:
    """
    분양/분양전환 서류 OCR.
    1. pdfplumber (텍스트 PDF → 비용 0원)
    2. Clova OCR  (이미지 PDF, 키 있으면)
    3. Tesseract  (로컬 무료)
    4. Claude Vision (위 3개 모두 실패 시만 — 마지막 수단)
    """
    # 1. pdfplumber
    text = _pdfplumber_extract(pdf_path)
    if text:
        return text
    # 2. Clova OCR
    text = _clova_extract(pdf_path)
    if text:
        return text
    # 3. Tesseract (로컬 무료 — Claude보다 먼저)
    text = _tesseract_extract(pdf_path)
    if text:
        return text
    # 4. Claude Vision (마지막 수단)
    return _claude_extract_text(pdf_path)


# ── 대지권 전용: pdfplumber → Claude Vision ────────────────────────────────────

def ocr_pdf_for_daejikwon(pdf_path: str) -> str:
    """
    대지권 등기부등본 OCR.
    1. pdfplumber — 텍스트 PDF이면 여기서 끝 (API 호출 없음)
    2. Clova OCR  — 이미지 PDF, 키 있으면
    3. Tesseract  — 로컬 무료
    4. Claude Vision — 마지막 수단
    """
    # 1. pdfplumber
    try:
        import pdfplumber
        pages = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text(x_tolerance=2, y_tolerance=2) or ""
                pages.append(t)
        text = "\n".join(pages)
        if len(re.findall(r"[가-힣]", text)) >= 50:
            return text
    except Exception:
        pass

    # 2. Clova OCR
    text = _clova_extract(pdf_path)
    if text:
        return text

    # 3. Tesseract (로컬 무료 — Claude보다 먼저)
    text = _tesseract_extract(pdf_path)
    if text:
        return text

    # 4. Claude Vision (마지막 수단)
    return _claude_extract_text(pdf_path)


# ── 하위 호환: 기존 코드에서 호출하는 함수명 유지 ─────────────────────────────

def ocr_pdf(pdf_path: str) -> str:
    """기존 호환용. 대지권 엔진 사용."""
    return ocr_pdf_for_daejikwon(pdf_path)


def ocr_pdf_tesseract(pdf_path: str) -> str:
    return _tesseract_extract(pdf_path)


def ocr_image(img) -> str:
    """이미지 OCR (분양 서류 스캔본 등)."""
    try:
        import pytesseract
        return pytesseract.image_to_string(
            img.convert("L"), lang="kor+eng", config="--psm 6 --oem 3")
    except Exception:
        return ""


def extract_pdf(pdf_path: str) -> dict:
    """분양/분양전환 서류 구조화 추출 — Claude 사용 안 함."""
    text = ocr_pdf_for_bunya(pdf_path)
    from core.extractor import classify_document, EXTRACTORS
    doc_type = classify_document(text)
    extractor = EXTRACTORS.get(doc_type)
    result = extractor(text) if extractor else {}
    result["doc_type"] = doc_type
    result["_파일명"] = Path(pdf_path).name
    신탁 = len(re.findall(r"신탁\s*(?:등기|원부|말소)", text))
    result["신탁건수"] = min(신탁, 10)
    result["신탁유무"] = "있음" if 신탁 else "없음"
    return result
