"""
분양전환 계약서 처리 엔진
=========================
• PDF(이미지) → Claude Vision → 구조화 추출
• 기본명단에서 동/호 매칭 → 해당 행에만 입력
• 연번(A), 단지명(B) 보존
• 일시납/분할납부 자동 감지
"""
import re, json, base64, io, configparser
from pathlib import Path


def clean_address(addr):
    if not addr:
        return addr
    addr = re.sub(r'^[\s\-]*[\*#]+[\s\*#\-]*', '', str(addr))  # 앞 마스킹 제거
    addr = addr.strip(' |')                                      # 뒤 | 제거
    return addr.strip()


def _cfg():
    c = configparser.ConfigParser()
    c.read(str(Path(__file__).parent.parent / "config.ini"), encoding="utf-8")
    return c


def _api_key():
    c = _cfg()
    k = c.get("claude", "api_key", fallback="").strip()
    if not k or "여기에" in k:
        k = c.get("api", "api_key", fallback="").strip()
    return k if k and "여기에" not in k else ""


def extract_from_contract(pdf_path: str) -> dict:
    """
    분양전환계약서 PDF → 구조화 데이터 추출
    1. pdfplumber (텍스트 PDF → 무료)
    2. Clova OCR  (이미지 PDF, 키 있으면 Claude보다 먼저 — 저렴)
    3. Claude Vision (Clova 없거나 실패 시에만)
    """
    fname = Path(pdf_path).name

    # 1. pdfplumber
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            text = "\n".join(p.extract_text(x_tolerance=2, y_tolerance=2) or "" for p in pdf.pages)
        if len(re.findall(r"[가-힣]", text)) >= 30:
            return _parse_contract_text(text, fname)
    except Exception:
        pass

    # 2. Clova OCR
    try:
        c = _cfg()
        invoke_url = c.get("clova", "invoke_url", fallback="").strip()
        client_id  = c.get("clova", "client_id",  fallback="").strip()
        if invoke_url or client_id:
            from core.clova_ocr import ClovaOCR
            clova = ClovaOCR(str(Path(__file__).parent.parent / "config.ini"))
            text = clova.ocr_pdf(pdf_path)
            if len(re.findall(r"[가-힣]", text)) >= 30:
                return _parse_contract_text(text, fname)
    except Exception:
        pass

    # 3. Tesseract OCR (로컬 무료 — Claude보다 먼저)
    try:
        import pytesseract
        from pdf2image import convert_from_path
        c = _cfg()
        tess_path = c.get("tesseract", "path", fallback="").strip()
        if tess_path:
            pytesseract.pytesseract.tesseract_cmd = tess_path
        images = convert_from_path(pdf_path, dpi=200)
        text = "\n".join(
            pytesseract.image_to_string(img.convert("L"), lang="kor+eng", config="--psm 6 --oem 3")
            for img in images[:6]
        )
        if len(re.findall(r"[가-힣]", text)) >= 30:
            r = _parse_contract_text(text, fname)
            r["_엔진"] = "Tesseract"
            return r
    except Exception:
        pass

    # 4. Claude Vision (마지막 수단)
    return _extract_with_claude(pdf_path)


def _parse_contract_text(text: str, fname: str) -> dict:
    """텍스트에서 분양전환 정보 파싱"""
    r = {"_파일명": fname}

    # 계약유형 (일시납/분할납부)
    if re.search(r"일시\s*납", text):
        r["계약유형"] = "일시납"
    elif re.search(r"분할\s*납부", text):
        r["계약유형"] = "분할납부"

    # 동/호 — 2~5자리 동 번호 모두 처리
    m = re.search(r"제\s*(\d{1,5})\s*동\s*제\s*(\d{1,5})\s*호", text)
    if not m:
        m = re.search(r"(\d{1,5})\s*동\s*(\d{3,5})\s*호", text)
    if m:
        r["동"] = m.group(1)
        r["호"] = m.group(2)

    # 성명
    for pat in [r"수\s*분\s*양\s*자[^\n]*성\s*명\s*[:：]?\s*([가-힣]{2,5})",
                r"성\s*명\s*[:：]?\s*([가-힣]{2,5})\s*(?:\(인\)|인)"]:
        m2 = re.search(pat, text)
        if m2:
            r["성명"] = m2.group(1)
            break

    # 주민등록번호
    m3 = re.search(r"(\d{6}[-–]\d{7})", text)
    if m3:
        r["주민등록번호"] = m3.group(1)

    # 주소
    for city in ["경기도","서울","인천","부산","대구","광주","대전","울산","세종"]:
        m4 = re.search(rf"({city}[^\n]{{10,60}}(?:동|로|길)[^\n]{{0,30}}호)", text)
        if m4:
            r["주소"] = m4.group(1).strip()
            break

    # 전화
    m5 = re.search(r"연\s*락\s*처\s*[:：]?\s*(0\d{1,2}[-–]\d{3,4}[-–]\d{4})", text)
    if m5:
        r["전화번호"] = m5.group(1)

    # 분양가
    m6 = re.search(r"주\s*택\s*가\s*격\s*(?:합\s*계)?\s*[:：]?\s*([\d,]+)\s*원", text)
    if m6:
        r["분양가"] = int(m6.group(1).replace(",", ""))

    # 대지지분
    m7 = re.search(r"대\s*지\s*지\s*분[^\d]*(\d{1,3}[.]\d{2,6})", text)
    if m7:
        r["대지지분"] = m7.group(1)

    # 전용면적
    m8 = re.search(r"전\s*용\s*면\s*적[^\d]*(\d{2,3}[.]\d{2,6})", text)
    if m8:
        r["전용면적"] = m8.group(1)

    return r


def _extract_with_claude(pdf_path: str) -> dict:
    """Claude Vision으로 분양전환계약서 구조화 추출"""
    key = _api_key()
    if not key:
        return {"_파일명": Path(pdf_path).name, "_오류": "API 키 없음"}

    try:
        import anthropic
        from pdf2image import convert_from_path

        c = _cfg()
        model = c.get("claude", "model", fallback="claude-sonnet-4-6")
        # 합본PDF 대응: 전체 페이지 로드 후 핵심 페이지 선택
        from PIL import Image as PILImage
        all_images = convert_from_path(pdf_path, dpi=120)
        total = len(all_images)

        # 핵심 페이지 최대 커버리지로 선택
        if total <= 8:
            sel = list(range(total))
        else:
            # 앞 2장 + 중반부 전체 + 뒤 전체 커버
            sel = [0, 1]                            # 초본/등본
            # 중간: 근저당계약서, 인감 영역
            third = total // 3
            sel += list(range(third-1, third+2))    # 1/3 지점 ±1
            # 뒤쪽 절반: 공급계약서, 발코니, 선택품목
            back_start = total * 2 // 3
            sel += list(range(back_start, total))   # 뒤 1/3 전체
            sel = sorted(set(s for s in sel if 0 <= s < total))

        def _to_b64(img, max_size=1600, quality=70):
            w,h = img.size
            if max(w,h) > max_size:
                r = max_size/max(w,h)
                img = img.resize((int(w*r),int(h*r)), PILImage.LANCZOS)
            buf = io.BytesIO()
            img.convert("RGB").save(buf, "JPEG", quality=quality)
            return base64.standard_b64encode(buf.getvalue()).decode()

        content = []
        for i in sel:
            b64 = _to_b64(all_images[i])
            sz = len(b64)*3//4
            if sz < 4_500_000:  # 4.5MB 이하만 포함
                content.append({"type": "image",
                                "source": {"type": "base64",
                                           "media_type": "image/jpeg", "data": b64}})

        content.append({"type": "text", "text": """분양전환계약서에서 아래 항목을 추출하여 JSON으로만 답하세요.
없으면 빈 문자열. 숫자만 있는 필드는 숫자만.

{
  "계약유형": "일시납 또는 분할납부",
  "동": "동 숫자만 (예: 5306)",
  "호": "호 숫자만 (예: 903)",
  "성명": "수분양자 성명",
  "주민등록번호": "000000-0000000",
  "주소": "수분양자 주소 전체",
  "전화번호": "000-0000-0000",
  "전용면적": "숫자만 (예: 59.9806)",
  "대지지분": "숫자만 (예: 38.6481)",
  "분양가": "숫자만 (예: 521500000)",
  "대출여부": "현재 대출 잔액이 있으면 대출, 없거나 완제면 무대출"
}"""})

        client = anthropic.Anthropic(api_key=key)
        r = client.messages.create(model=model, max_tokens=1200,
                                   messages=[{"role": "user", "content": content}])
        raw = r.content[0].text
        # JSON 블록 추출 (```json ... ``` 또는 { ... })
        clean = re.sub(r"```(?:json)?", "", raw).strip().replace("```", "").strip()
        # 쉼표 있는 숫자 정리 (예: "576,100,000" → "576100000")
        try:
            result = json.loads(clean)
        except json.JSONDecodeError:
            # { ... } 패턴으로 재시도
            m = re.search(r"\{[\s\S]+\}", clean)
            if m:
                result = json.loads(m.group(0))
            else:
                raise ValueError("JSON 추출 실패")
        # 숫자 필드 쉼표 제거
        num_fields = ["분양대금","부가세","발코니금액","옵션금액","채권최고액","거래가액","프리미엄"]
        for f in num_fields:
            if f in result and isinstance(result[f], str):
                result[f] = result[f].replace(",","").strip()
        # 호수 선행0 제거
        if "호" in result:
            result["호"] = str(result["호"]).lstrip("0") or str(result["호"])
        result["_파일명"] = Path(pdf_path).name
        result["_엔진"] = "Claude"
        return result

    except Exception as e:
        err_str = str(e)
        is_credit = "credit" in err_str.lower() or "balance" in err_str.lower()
        if is_credit:
            # 크레딧 부족 → 빈 결과 (앞 단계 로컬 결과 없을 때)
            return {"_파일명": Path(pdf_path).name, "_오류": "API 크레딧 부족 — pdfplumber/Tesseract 결과로 처리됨"}
        return {"_파일명": Path(pdf_path).name, "_오류": err_str[:80]}


def write_to_basic_list(xlsx_path: str, output_path: str,
                         sheet_name: str, records: list,
                         col_map: dict, key_cols: dict,
                         preserve_cols: list = None) -> dict:
    """
    기본명단에 데이터 입력
    - records: [{"동":"5306","호":"903","성명":"배영문",...}, ...]
    - col_map: {"성명": 31, "동": 28, ...}
    - key_cols: {"동": 28, "호": 30}  ← 행 찾기용
    - preserve_cols: [1, 2]  ← 덮어쓰지 않을 열
    """
    import openpyxl, shutil

    shutil.copy(xlsx_path, output_path)
    wb = openpyxl.load_workbook(output_path)
    ws = wb[sheet_name]
    if preserve_cols is None:
        preserve_cols = [1, 2]  # 연번, 단지명

    # 행 인덱스 구성: (동, 호) → 행번호
    dong_col = key_cols.get("동", 28)
    ho_col   = key_cols.get("호", 30)
    row_index = {}
    for row in range(2, ws.max_row + 1):
        d = str(ws.cell(row, dong_col).value or "").strip()
        h = str(ws.cell(row, ho_col).value  or "").strip()
        if d and h:
            row_index[(d, h)] = row

    result = {"success": 0, "notfound": [], "errors": []}

    for rec in records:
        dong = str(rec.get("동", "")).strip()
        ho   = str(rec.get("호", "")).strip()

        if not dong or not ho:
            result["errors"].append(f"{rec.get('_파일명','?')}: 동/호 없음")
            continue

        row = row_index.get((dong, ho))
        if not row:
            result["notfound"].append(f"{dong}동 {ho}호")
            continue

        # 해당 행에 입력
        for field, col in col_map.items():
            if col in preserve_cols:
                continue
            val = rec.get(field)
            if val is None or val == "":
                continue
            cell = ws.cell(row, col)
            # 수식 셀 건너뜀
            if isinstance(cell.value, str) and cell.value.startswith("="):
                continue
            # 주소 정제
            if field == "주소":
                cell.value = clean_address(val)
            else:
                cell.value = val
        result["success"] += 1

    wb.save(output_path)
    return result
