"""
세대 단위 통합 처리기
여러 PDF → 서류별 OCR → 병합 → 기본명단 1행 데이터
"""

import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from core.tax_calculator import calc_취득세
from core.cost_calculator import calc_등기비용
from core.vision_ocr import extract_pdf


# ─── 서류 우선순위 (같은 필드 중복시 어떤 서류 값 우선) ────────────────────

FIELD_SOURCE_PRIORITY = {
    "성명":         ["명의변경계약서", "증여계약서", "주민등록초본",
                     "주민등록등본", "인감증명서", "분양계약서"],
    "주민등록번호": ["주민등록초본", "주민등록등본", "인감증명서", "분양계약서"],
    "주소":         ["주민등록초본", "주민등록등본"],
    "전화번호":     ["분양계약서", "근저당설정계약서", "명의변경계약서"],
    "분양대금":     ["분양계약서"],
    "채권최고액":   ["근저당설정계약서"],
    "초본발행일":   ["주민등록초본"],
    "인감발행일":   ["인감증명서"],
    "등본발행일":   ["주민등록등본"],
    "세대원수":     ["주민등록등본"],
}

# 승계 서류 타입
TRANSFER_DOC_TYPES = {"증여계약서", "명의변경계약서"}

# 필수 서류 체크
REQUIRED_DOC_TYPES = {
    "분양계약서", "선택품목계약서", "근저당설정계약서", "주민등록초본"
}


def merge_unit_records(records: list[dict]) -> dict:
    """
    여러 서류의 추출 결과를 하나의 기본명단 행으로 병합.
    - 승계 서류 여러 건: 날짜 최신 1건만
    - 나머지: 필드별 우선순위 + 후순위 덮어쓰기 방식
    """
    transfer_records = []   # 승계 서류만 별도 수집
    other_records = []

    for r in records:
        doc_type = r.get("doc_type", "")
        if doc_type in TRANSFER_DOC_TYPES:
            transfer_records.append(r)
        else:
            other_records.append(r)

    # 일반 서류 병합 (먼저 들어온 값 보존, 빈 값이면 채움)
    merged = {}
    for rec in other_records:
        for k, v in rec.items():
            if k.startswith("_"):
                continue
            if v in (None, "", 0) and k in merged:
                continue  # 기존 값 보존
            if v not in (None, ""):
                merged[k] = v

    # ── 승계 횟수 + 유형 자동 분석 ────────────────────────────────────────
    from core.extractor import count_and_classify_successions, detect_succession_type

    succession_result = count_and_classify_successions(transfer_records)
    merged["승계여부"]  = succession_result["승계여부"]
    merged["승계일"]    = succession_result["승계일"]
    merged["승계횟수"]  = succession_result["승계횟수"]

    # 매매 승계일 때만 거래신고필증/거래가액 입력, 증여는 공란
    if "매매" in merged.get("승계여부", ""):
        # 거래신고필증번호/거래가액은 기존 병합값 유지
        pass
    else:
        merged["거래신고필증번호"] = ""
        merged["거래가액"] = ""

    # ── 미비서류 자동 체크 (단일 계산) ──────────────────────────────────
    from core.extractor import check_missing_docs
    found_types = [r.get("doc_type","") for r in records if r.get("doc_type")]
    has_loan       = "근저당설정계약서" in found_types or bool(merged.get("채권최고액"))
    has_succession = succession_result["승계횟수"] > 0
    succession_type = "증여" if "증여" in merged.get("승계여부","") else "매매"

    미비 = check_missing_docs(found_types, has_loan, has_succession, succession_type)
    merged["미비서류"] = "" if 미비 == "없음" else 미비

    # 근저당 없으면 대출 관련 공란
    if not merged.get("채권최고액"):
        for f in ["대출은행", "대출지점", "채권최고액", "근저당설정계약일"]:
            merged.setdefault(f, "")

    # 취득세 자동 계산
    tax = calc_취득세(merged)
    merged["취득세과표"]  = tax["취득세과표"]
    merged["취득세"]     = tax["취득세"]
    merged["교육세"]     = tax["교육세"]
    merged["농특세"]     = tax["농특세"]
    merged["취득세합계"] = tax["취득세합계"]
    merged["_적용세율"]  = tax["적용세율"]
    merged["_감면액"]    = tax["감면액"]

    # 등기비용 자동 계산
    cost = calc_등기비용(merged)
    for k, v in cost.items():
        merged[k] = v
    # AL열(등기비용합계) = CE열과 동일
    merged["등기비용합계_AL"] = cost["등기비용총합계"]
    merged["설정비용1순위"]   = cost.get("설정비용합계", 0)

    # ── 추가 자동계산 항목 ─────────────────────────────────
    # 동-호수 합치기 (AC열)
    동 = str(merged.get("동","")).strip()
    호 = str(merged.get("호","")).strip()
    merged["동호수"] = f"{동}동 {호}호" if 동 and 호 else ""

    # 층 계산 (호수 앞 두자리, 예: 2302 → 23층)
    try:
        merged["층"] = str(int(호[:2])) + "층" if 호 and len(호) >= 4 else ""
    except:
        merged["층"] = ""

    # 감면여부 기본값
    merged.setdefault("감면여부", "해당없음")

    # 주택수 기본값
    merged.setdefault("주택수", 1)

    # 분양대금과표 (AW) = 분양대금 + 부가세
    분양대금 = int(merged.get("분양대금", 0) or 0)
    부가세   = int(merged.get("부가세", 0) or 0)
    merged["분양대금과표"] = 분양대금 + 부가세

    # 옵션 과표 (BB, BG) — VAT포함 금액 그대로
    merged["옵션1과표"] = int(merged.get("발코니금액", 0) or 0)
    merged["옵션2과표"] = int(merged.get("옵션금액", 0) or 0)

    # 비용요약 (FJ~FQ)
    bq = int(cost.get("채권매입금액_이전", 0) or 0)
    br = int(cost.get("채권할인금액_이전", 0) or 0)
    cu = int(cost.get("채권매입금액_설정", 0) or 0)
    cv = int(cost.get("채권할인금액_설정", 0) or 0)
    merged["비용요약_등기비용합계"] = cost["등기비용총합계"]
    merged["비용요약_취득세"]      = int(merged.get("취득세합계", 0) or 0)
    merged["비용요약_인지대"]      = int(cost.get("인지대_이전", 0) or 0)
    merged["비용요약_이전채권비"]  = bq - br
    merged["비용요약_설정채권비"]  = cu - cv
    merged["비용요약_수수료"]      = int(cost.get("보수료", 0) or 0) + int(cost.get("보수료_설정", 0) or 0)
    merged["비용요약_부가세"]      = int(cost.get("부가세_이전", 0) or 0) + int(cost.get("부가세_설정", 0) or 0)

    # 이폼용 (GF~GI)
    주민번호 = str(merged.get("주민등록번호",""))
    merged["주민번호앞자리"] = 주민번호[:6] if len(주민번호) >= 6 else ""
    merged["명의자1"]       = merged.get("성명", "")
    merged["주민번호1"]     = 주민번호

    # 서류수령일 = 시스템 처리 당일 자동 입력
    merged.setdefault("서류수령일", date.today().strftime("%Y-%m-%d"))

    # 처리된 서류 목록
    merged["_처리서류"] = [r.get("doc_type", "미분류") for r in records]

    return merged


def _pick_latest_transfer(records: list[dict]) -> dict | None:
    """승계 서류 중 날짜가 가장 늦은 1건 반환"""
    if not records:
        return None
    def sort_key(r):
        return r.get("승계일", "0000-00-00") or "0000-00-00"
    return max(records, key=sort_key)


# ─── 세대 폴더 처리 ──────────────────────────────────────────────────────────

def process_unit_folder(folder_path: str, progress_cb=None) -> dict:
    """
    한 세대 폴더의 모든 PDF를 OCR 처리 후 병합.
    progress_cb: (current, total, filename) 콜백
    """
    folder = Path(folder_path)
    pdf_files = sorted(
        list(folder.glob("*.pdf")) + list(folder.glob("*.PDF"))
    )

    if not pdf_files:
        return {"_세대": folder.name, "_오류": "PDF 없음"}

    records = []
    for i, pdf_path in enumerate(pdf_files):
        if progress_cb:
            progress_cb(i, len(pdf_files), pdf_path.name)
        try:
            result = extract_pdf(str(pdf_path))
            result["_파일명"] = pdf_path.name
            records.append(result)
        except Exception as e:
            records.append({"_파일명": pdf_path.name, "_오류": str(e), "doc_type": ""})

    merged = merge_unit_records(records)
    merged["_세대"] = folder.name
    merged["_원본서류수"] = len(pdf_files)
    return merged


# ─── 병렬 배치 처리 (200건+) ─────────────────────────────────────────────────

def process_batch(root_folder: str, max_workers: int = 5,
                  progress_cb=None) -> list[dict]:
    """
    A방식: 세대별 서브폴더 → 폴더당 여러 PDF 처리
    B방식: 폴더 내 합본 PDF → PDF 1개 = 세대 1건
    자동 감지 후 적절한 방식 선택
    """
    root = Path(root_folder)

    # ── 방식 감지 ──────────────────────────────────────────────────────
    subfolders = sorted([f for f in root.iterdir() if f.is_dir()])
    pdfs_direct = sorted(root.glob("*.pdf"))

    if subfolders and not pdfs_direct:
        mode = "A"  # 세대별 서브폴더
        items = subfolders
    elif pdfs_direct:
        mode = "B"  # 합본 PDF (세대당 1파일)
        items = pdfs_direct
    else:
        return []

    total = len(items)
    print(f"📁 처리 방식: {'A (세대별 폴더)' if mode=='A' else 'B (합본 PDF)'} — 총 {total}건")

    results = [None] * total

    def _process_one(item, idx):
        if mode == "A":
            return process_unit_folder(str(item))
        else:
            return _process_combined_pdf(str(item))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_idx = {
            executor.submit(_process_one, item, i): i
            for i, item in enumerate(items)
        }
        done = 0
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            name = items[idx].name
            try:
                results[idx] = future.result()
                done += 1
                pct = done / total * 100
                print(f"  [{done}/{total}] {pct:.0f}% ✅ {name}")
                if progress_cb:
                    progress_cb(done, total, name)
            except Exception as e:
                results[idx] = {"_세대": name, "_오류": str(e)}
                done += 1
                if progress_cb:
                    progress_cb(done, total, name)
                print(f"  [{done}/{total}] ❌ {name}: {e}")

    return [r for r in results if r is not None]


def _local_extract_bunyang(pdf_path: str) -> tuple:
    """pdfplumber → Clova → Tesseract 순으로 텍스트 추출 후 bunyang_parser로 파싱.
    Returns (engine_name, data_dict). engine_name은 실패 시 빈 문자열."""
    import re, sys, configparser
    from pathlib import Path as _P

    cfg_path = str(_P(__file__).parent.parent / "config.ini")
    ocr_pages = []
    engine = ""

    # 1. pdfplumber
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            ocr_pages = [pg.extract_text(x_tolerance=2, y_tolerance=2) or "" for pg in pdf.pages]
        if sum(len(re.findall(r"[가-힣]", t)) for t in ocr_pages) >= 50:
            engine = "pdfplumber"
        else:
            ocr_pages = []
    except Exception:
        ocr_pages = []

    # 2. Clova OCR
    if not engine:
        try:
            cfg = configparser.ConfigParser()
            cfg.read(cfg_path, encoding="utf-8")
            if cfg.get("clova", "invoke_url", fallback="").strip():
                from core.clova_ocr import ClovaOCR
                full_text = ClovaOCR(cfg_path).ocr_pdf(pdf_path)
                if len(re.findall(r"[가-힣]", full_text)) >= 30:
                    ocr_pages = [full_text]
                    engine = "Clova"
        except Exception:
            pass

    # 3. Tesseract OCR
    if not engine:
        try:
            import pytesseract
            from pdf2image import convert_from_path
            cfg = configparser.ConfigParser()
            cfg.read(cfg_path, encoding="utf-8")
            tess_path = cfg.get("tesseract", "path", fallback="").strip()
            if tess_path:
                pytesseract.pytesseract.tesseract_cmd = tess_path
            images = convert_from_path(pdf_path, dpi=200)
            ocr_pages = [
                pytesseract.image_to_string(img.convert("L"), lang="kor+eng", config="--psm 6 --oem 3")
                for img in images[:8]
            ]
            if sum(len(re.findall(r"[가-힣]", t)) for t in ocr_pages) >= 30:
                engine = "Tesseract"
            else:
                ocr_pages = []
        except Exception:
            pass

    if not engine or not ocr_pages:
        return "", {}

    # bunyang_parser_fix로 파싱
    try:
        sys.path.insert(0, str(_P(__file__).parent.parent))
        from bunyang_parser_fix import parse_bunyang_apt_full
        parsed = parse_bunyang_apt_full(ocr_pages)

        local = {"승계여부": "해당없음", "개별공동": "개별"}
        local["동"]       = parsed.get("동", "")
        local["호"]       = parsed.get("호", "")
        local["전용면적"] = parsed.get("전용면적", "")
        공급가액 = parsed.get("공급가액", "")
        local["분양대금"] = str(공급가액) if 공급가액 else ""

        계약자 = parsed.get("계약자", [])
        if 계약자:
            local["성명"]         = 계약자[0].get("성명", "")
            local["주민등록번호"] = 계약자[0].get("주민번호", "")
        if len(계약자) >= 2:
            local["개별공동"] = "공동"

        근저당 = parsed.get("근저당", {})
        if 근저당:
            local["채권최고액"] = str(근저당.get("채권최고액", ""))
            local["대출은행"]   = 근저당.get("채권자", "")

        # 주민등록초본에서 주소 추출
        try:
            full_text = "\n".join(ocr_pages)
            from core.extractor import extract_주민등록초본
            초본 = extract_주민등록초본(full_text)
            if 초본.get("주소"):
                local["주소"] = 초본["주소"]
            if 초본.get("성명") and not local.get("성명"):
                local["성명"] = 초본["성명"]
            if 초본.get("초본발급일"):
                local["초본발급일"] = 초본["초본발급일"]
        except Exception:
            pass

        return engine, {k: v for k, v in local.items() if v}
    except Exception:
        return engine, {}


def _process_combined_pdf(pdf_path: str, ai_mode: str = "balanced") -> dict:
    """
    추출 엔진 — 폴백 우선 (pdfplumber→Clova→Tesseract→Claude)
    economy : 빠르고 저렴  (~80원/세대)  정확도 85%
    balanced: 균형형 추천  (~150원/세대) 정확도 92%
    ultimate: 최고 정확도 (~350원/세대) 정확도 95%+
    """
    import base64, re, json, configparser, anthropic
    from pathlib import Path as _P

    MODE_CFG = {
        "economy":  {"max_tokens": 4000, "retry": False},
        "balanced": {"max_tokens": 4000, "retry": True},
        "ultimate": {"max_tokens": 4000, "retry": True},
    }
    mcfg = MODE_CFG.get(ai_mode, MODE_CFG["balanced"])

    p = Path(pdf_path)
    result = {"_세대": p.stem, "_파일명": p.name}

    # ── 로컬 추출 먼저 (pdfplumber → Clova → Tesseract) ──────────────
    engine, local_data = _local_extract_bunyang(pdf_path)
    if local_data:
        result.update(local_data)
        result["_엔진"] = engine

    # ── 파일명 힌트 ───────────────────────────────────────────────────
    stem     = p.stem
    parts    = stem.split("_", 1)
    세대코드 = parts[0] if parts else stem
    성명힌트 = parts[1] if len(parts) > 1 else ""

    try:
        cfg = configparser.ConfigParser()
        cfg.read(str(_P(__file__).parent.parent / "config.ini"), encoding="utf-8")
        key   = cfg.get("claude","api_key",fallback="") or cfg.get("api","api_key",fallback="")
        model = cfg.get("claude","model",fallback="claude-sonnet-4-6")
        if not key:
            raise ValueError("API 키 없음 — config.ini 확인 필요")

        # ── 파일명에서 힌트 추출 ─────────────────────────────────────
        stem      = p.stem                                        # "1-603_이재복"
        parts     = stem.split("_", 1)
        세대코드  = parts[0] if parts else stem                   # "1-603"
        성명힌트  = parts[1] if len(parts) > 1 else ""            # "이재복"

        # ── PDF 원본 base64 변환 ──────────────────────────────────────
        with open(pdf_path, "rb") as f:
            pdf_b64 = base64.standard_b64encode(f.read()).decode()

        client = anthropic.Anthropic(api_key=key)

        # ════════════════════════════════════════════════════════════
        # PASS 1 : Extended Thinking + 전체 추출
        # ════════════════════════════════════════════════════════════
        hint = f"[파일 정보] 파일명: {p.name} / 세대코드: {세대코드}"
        if 성명힌트:
            hint += f"\n※ 수분양자 성명 힌트: 『{성명힌트}』— 서류에서 이 이름과 일치하는지 반드시 교차 확인"
        hint += "\n"

        PROMPT_MAIN = hint + """
이 분양아파트 서류 묶음을 꼼꼼히 분석하여 아래 JSON만 출력하세요.
마크다운·설명·코드블록 절대 금지. 없는 값은 빈 문자열. 금액은 숫자만. 날짜는 YYYY-MM-DD.

[추출 원칙 — 서류별 출처 엄수]
① 성명      : 공급계약서 "을(공급받는자)" 또는 "수분양자" 란의 이름. 파일명 힌트와 교차 확인.
② 동        : 공급계약서의 동번호 (예: 9101, 9102). 주민등록 주소의 동과 혼동 금지.
③ 호        : 공급계약서의 호수 (예: 603, 2304).
④ 분양대금  : 공급계약서(분양계약서)의 "총 공급금액" = 대지비 + 건축비 합산. 4억~8억원대.
               발코니확장계약서·선택품목계약서·중도금 금액과 절대 혼동 금지.
⑤ 부가세    : 공급계약서의 "건물부가세"만 (분양대금의 약 10%).
⑥ 발코니금액: "발코니확장계약서"의 총 공급금액만 (수백만~천만원).
⑦ 옵션금액  : "선택품목계약서"의 최종 합계만.
⑧ 채권최고액: 근저당권설정계약서의 "채권 최고액" 금액만.
               계좌번호(11~14자리), 주민등록번호와 절대 혼동 금지.
               숫자 10자리 이상이면 계좌번호 → 빈 문자열.
⑨ 주소      : 주민등록표(초본)의 마지막 현주소 (이하 여백 직전 행).
               층수와 호수를 혼동하지 말 것 (예: 602동 1202호 → "602동"이 동번호).
⑩ 초본발급일: 주민등록표(초본) 상단의 발급일자.
⑪ 인감발급일: 인감증명서의 발급일자.
⑫ 분양계약일: 공급계약서(분양계약서)의 계약 체결일. 전입일·중도금 납부일과 혼동 금지.
⑬ 서류목록  : 이 PDF에 포함된 모든 서류명을 콤마로 나열.

{"동":"","호":"","성명":"","주민등록번호":"","전화번호":"","전화번호2":"","주소":"","전용면적":"","대지지분":"","분양계약일":"","분양대금":"","부가세":"","발코니금액":"","옵션금액":"","프리미엄":"","거래가액":"","실거래일련번호":"","승계여부":"해당없음","승계일":"","초본발급일":"","인감발급일":"","대출은행":"","대출지점":"","대출은행2":"","대출지점2":"","채권최고액":"","채권최고액2":"","근저당설정계약일":"","개별공동":"개별","서류목록":""}"""

        def _api_call(prompt_text):
            msgs = [{"role": "user", "content": [
                {"type": "document",
                 "source": {"type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_b64}},
                {"type": "text", "text": prompt_text}
            ]}]
            resp = client.messages.create(
                model=model,
                max_tokens=mcfg["max_tokens"],
                messages=msgs
            )
            return next((b.text for b in resp.content if b.type == "text"), "")

        def _parse_json(raw: str) -> dict:
            raw = re.sub(r"```(?:json)?", "", raw).replace("```", "").strip()
            try:
                return json.loads(raw)
            except:
                m = re.search(r"\{[\s\S]+\}", raw)
                return json.loads(m.group(0)) if m else {}

        def _clean(data: dict) -> dict:
            """마크다운 제거 + 숫자 정리 + 이상값 필터"""
            for k, v in list(data.items()):
                if isinstance(v, str):
                    v = re.sub(r"\*+|#+|_{2,}", "", v).strip()
                    v = re.sub(r"^[가-힣A-Za-z]+[:：]\s*", "", v).strip()
                    data[k] = v
            # 금액 쉼표·원 제거
            for f in ["분양대금","부가세","발코니금액","옵션금액",
                      "프리미엄","거래가액","채권최고액","채권최고액2"]:
                if f in data:
                    data[f] = re.sub(r"[,원\s]", "", str(data[f]))
            # 채권최고액: 10자리 이상 → 계좌번호 → 제거
            for f in ["채권최고액", "채권최고액2"]:
                v = str(data.get(f, "")).strip()
                if v and v.isdigit() and len(v) >= 10:
                    data[f] = ""
            # 분양대금 이상값: 5천만 미만 or 15억 초과
            try:
                pd = int(data.get("분양대금", 0) or 0)
                if pd and (pd < 50_000_000 or pd > 1_500_000_000):
                    data["분양대금"] = ""
                    data["부가세"]   = ""
            except: pass
            # 부가세 비율 이상 (분양대금의 0.1%~15% 범위 아니면 제거)
            try:
                pd = int(data.get("분양대금", 0) or 0)
                vt = int(data.get("부가세", 0)   or 0)
                if pd and vt and not (0.001 < vt/pd < 0.15):
                    data["부가세"] = ""
            except: pass
            # 거래가액 단위오류 (분양대금의 5배 초과면 10으로 나누기)
            try:
                pd = int(data.get("분양대금", 0) or 0)
                ga = int(data.get("거래가액", 0) or 0)
                if pd and ga and ga > pd * 5:
                    data["거래가액"] = str(ga // 10)
            except: pass
            # 호수 앞 0 제거
            if "호" in data:
                data["호"] = str(data["호"]).lstrip("0") or str(data.get("호",""))
            return data

        # ── Pass 1 실행 ──────────────────────────────────────────────
        raw1  = _api_call(PROMPT_MAIN)
        data  = _clean(_parse_json(raw1))

        # ── Pass 2 : 실패 필드 재추출 ───────────────────────────────
        retry_needed = {}

        if not data.get("분양대금"):
            retry_needed["분양대금·부가세"] = (
                "공급계약서(분양계약서)의 총 공급금액(대지비+건축비 합산, 4억~8억원대)과 "
                "건물부가세(총 공급금액의 약 10%)를 찾아주세요."
            )
        if not data.get("채권최고액") and not data.get("채권최고액2"):
            retry_needed["채권최고액"] = (
                "근저당권설정계약서에서 '채권 최고액' 항목의 금액(수천만~수억원)을 찾아주세요. "
                "계좌번호(11~14자리 숫자)와 혼동하지 마세요."
            )
        if not data.get("주소"):
            retry_needed["주소"] = (
                "주민등록표(초본)에서 가장 최근 현주소(이하 여백 바로 위 행)를 찾아주세요."
            )
        if not data.get("성명"):
            retry_needed["성명"] = (
                f"공급계약서의 수분양자(을) 성명을 찾아주세요. "
                f"파일명 힌트: '{성명힌트}'"
            )

        if retry_needed and mcfg["retry"]:
            retry_prompt = (
                f"[재추출 요청 — 파일명: {p.name}]\n"
                "Pass 1에서 다음 항목들이 누락되거나 오류입니다. 해당 항목만 정확히 재추출하세요.\n\n"
            )
            for field, desc in retry_needed.items():
                retry_prompt += f"★ {field}: {desc}\n"
            retry_prompt += (
                "\n위 항목들만 포함한 JSON으로 답하세요. "
                "예: {\"분양대금\":\"576100000\",\"부가세\":\"57610000\"}"
            )

            raw2  = _api_call(retry_prompt)
            data2 = _clean(_parse_json(raw2))
            # Pass 2 결과로 빈 필드만 보완 (Pass 1 유효값 덮어쓰지 않음)
            for k, v in data2.items():
                if v and not data.get(k):
                    data[k] = v

        # ── 파일명 힌트로 성명 최종 보완 ─────────────────────────────
        if 성명힌트 and not data.get("성명", "").strip():
            data["성명"] = 성명힌트

        result.update(data)
        result["_엔진"] = "Claude"

        # ── 미비서류 계산 ─────────────────────────────────────────────
        from core.extractor import check_missing_docs
        found_raw  = data.get("서류목록", "")
        kw_map = {
            "분양계약서":       ["공급계약서","분양계약서"],
            "주민등록초본":     ["주민등록표","초본","등본"],
            "인감증명서":       ["인감증명서"],
            "근저당설정계약서": ["근저당권설정계약서","근저당설정"],
            "선택품목계약서":   ["선택품목계약서"],
            "발코니확장계약서": ["발코니확장계약서"],
            "가족관계증명서":   ["가족관계증명서"],
            "위임장":           ["위임장"],
            "운전면허증":       ["운전면허증"],
            "증여계약서":       ["증여계약서"],
            "명의변경계약서":   ["명의변경계약서"],
            "거래신고필증":     ["거래신고필증"],
        }
        found_types     = [dt for dt, kws in kw_map.items() if any(k in found_raw for k in kws)]
        has_loan        = bool(data.get("채권최고액","") or data.get("채권최고액2",""))
        승계여부         = data.get("승계여부","")
        has_succession  = bool(승계여부 and 승계여부 not in ("","해당없음"))
        succession_type = "증여" if "증여" in 승계여부 else "매매"

        미비 = check_missing_docs(found_types, has_loan, has_succession, succession_type)
        result["미비서류"]  = "" if 미비 == "없음" else 미비
        result["_처리서류"] = found_types

    except Exception as e:
        err_str = str(e)
        # 크레딧 부족(400) → 조용히 로컬 결과 사용
        is_credit_err = "credit" in err_str.lower() or "balance" in err_str.lower()
        if not is_credit_err and not local_data:
            result["_오류"] = err_str[:300]

    # 성명힌트 최종 보완 (Claude/로컬 모두)
    if 성명힌트 and not result.get("성명", "").strip():
        result["성명"] = 성명힌트

    return result





# ════════════════════════════════════════════════════════════════════
#  Clova OCR + Claude 하이브리드 엔진
# ════════════════════════════════════════════════════════════════════

def _process_combined_pdf_clova(pdf_path: str, ai_mode: str = "balanced") -> dict:
    """
    Clova OCR → 텍스트 추출 → Claude 텍스트 분석
    ┌──────────────────────────────────────────────────────┐
    │ ① Clova OCR : 페이지별 이미지 → 텍스트 (저렴)        │
    │ ② Claude   : 텍스트만 전송 → 해석 (PDF보다 훨씬 저렴) │
    │ 세대당 비용: ~50~100원 (균형형 기준)                   │
    └──────────────────────────────────────────────────────┘
    """
    import re, json, configparser, anthropic
    from pathlib import Path as _P

    p = Path(pdf_path)
    result = {"_세대": p.stem, "_파일명": p.name, "_엔진": "ClovaOCR+Claude"}

    # ── 파일명 힌트 ─────────────────────────────────────────────────
    stem     = p.stem
    parts    = stem.split("_", 1)
    세대코드 = parts[0]
    성명힌트 = parts[1] if len(parts) > 1 else ""

    try:
        cfg_path = str(_P(__file__).parent.parent / "config.ini")
        cfg = configparser.ConfigParser()
        cfg.read(cfg_path, encoding="utf-8")

        key   = cfg.get("claude", "api_key", fallback="") or cfg.get("api", "api_key", fallback="")
        model = cfg.get("claude", "model", fallback="claude-sonnet-4-6")
        if not key:
            raise ValueError("Claude API 키 없음")

        # ── STEP 1: Clova OCR (→ Tesseract fallback) ─────────────────
        full_text = ""
        result["_상태"] = "OCR 중..."
        try:
            from core.clova_ocr import ClovaOCR
            full_text = ClovaOCR(cfg_path).ocr_pdf(str(pdf_path), dpi=150)
        except Exception:
            pass
        if not full_text or len(re.findall(r"[가-힣]", full_text)) < 30:
            # Clova 실패 → pdfplumber
            try:
                import pdfplumber
                with pdfplumber.open(pdf_path) as pdf:
                    full_text = "\n".join(pg.extract_text(x_tolerance=2, y_tolerance=2) or "" for pg in pdf.pages)
            except Exception:
                pass
        if not full_text or len(re.findall(r"[가-힣]", full_text)) < 30:
            # pdfplumber 실패 → Tesseract
            try:
                import pytesseract
                from pdf2image import convert_from_path
                tess_path = cfg.get("tesseract", "path", fallback="").strip()
                if tess_path:
                    pytesseract.pytesseract.tesseract_cmd = tess_path
                imgs = convert_from_path(pdf_path, dpi=200)
                full_text = "\n".join(
                    pytesseract.image_to_string(img.convert("L"), lang="kor+eng", config="--psm 6 --oem 3")
                    for img in imgs[:8]
                )
                result["_엔진"] = "Tesseract+Claude"
            except Exception:
                pass
        result["_ocr_chars"] = len(full_text)

        # ── STEP 2: Claude 텍스트 분석 (PDF 대신 텍스트 전송) ────────
        hint = f"[파일: {p.name} / 세대: {세대코드}]"
        if 성명힌트:
            hint += f"\n수분양자 성명 힌트: 『{성명힌트}』"

        prompt = f"""{hint}

아래는 Clova OCR로 추출한 분양아파트 서류 묶음의 텍스트입니다.
서류별 페이지 구분(=== 페이지 N ===)을 참고하여 필드를 정확히 추출하세요.
JSON만 출력. 없으면 빈 문자열. 금액 숫자만. 날짜 YYYY-MM-DD.

[추출 규칙]
① 성명     : 공급계약서 "을(수분양자)" 이름. 파일명 힌트 교차확인.
② 동/호    : 공급계약서 동·호수만 (예: 9101동 603호)
③ 분양대금 : 공급계약서 "총 공급금액"(대지비+건축비, 4억~8억원대)
④ 채권최고액: 근저당권설정계약서 "채권 최고액"(10자리 미만, 계좌번호 혼동 금지)
⑤ 주소    : 주민등록초본 마지막 현주소
⑥ 서류목록: 확인된 서류명 콤마 나열

=== OCR 텍스트 (최대 12,000자) ===
{full_text[:12000]}
=== END ===

{{"동":"","호":"","성명":"","주민등록번호":"","전화번호":"","전화번호2":"","주소":"","전용면적":"","대지지분":"","분양계약일":"","분양대금":"","부가세":"","발코니금액":"","옵션금액":"","프리미엄":"","거래가액":"","실거래일련번호":"","승계여부":"해당없음","승계일":"","초본발급일":"","인감발급일":"","대출은행":"","대출지점":"","대출은행2":"","대출지점2":"","채권최고액":"","채권최고액2":"","근저당설정계약일":"","개별공동":"개별","서류목록":""}}"""

        # 모드별 Claude 설정 (텍스트만 전송 → 훨씬 저렴, Extended Thinking 제거)
        MODE_CFG = {
            "economy":  {"max_tokens": 2000},
            "balanced": {"max_tokens": 3000},
            "ultimate": {"max_tokens": 4000},
        }
        mcfg = MODE_CFG.get(ai_mode, MODE_CFG["balanced"])

        client = anthropic.Anthropic(api_key=key)
        msgs   = [{"role": "user", "content": prompt}]

        resp = client.messages.create(
            model=model, max_tokens=mcfg["max_tokens"],
            messages=msgs
        )

        raw = next((b.text for b in resp.content if b.type == "text"), "")
        raw = re.sub(r"```(?:json)?", "", raw).replace("```", "").strip()

        try:
            data = json.loads(raw)
        except:
            m = re.search(r"\{[\s\S]+\}", raw)
            data = json.loads(m.group(0)) if m else {}

        # ── 이상값 필터 ───────────────────────────────────────────────
        for k, v in list(data.items()):
            if isinstance(v, str):
                v = re.sub(r"\*+|#+|_{2,}", "", v).strip()
                data[k] = v
        for f in ["분양대금","부가세","발코니금액","옵션금액","거래가액","채권최고액","채권최고액2"]:
            if f in data:
                data[f] = re.sub(r"[,원\s]", "", str(data[f]))
        for f in ["채권최고액","채권최고액2"]:
            v = str(data.get(f,"")).strip()
            if v and v.isdigit() and len(v) >= 10:
                data[f] = ""
        try:
            pd = int(data.get("분양대금",0) or 0)
            if pd and (pd < 50_000_000 or pd > 1_500_000_000):
                data["분양대금"] = ""; data["부가세"] = ""
        except: pass
        try:
            pd = int(data.get("분양대금",0) or 0)
            vt = int(data.get("부가세",0) or 0)
            if pd and vt and not (0.001 < vt/pd < 0.15):
                data["부가세"] = ""
        except: pass
        try:
            pd = int(data.get("분양대금",0) or 0)
            ga = int(data.get("거래가액",0) or 0)
            if pd and ga and ga > pd * 5:
                data["거래가액"] = str(ga // 10)
        except: pass
        if "호" in data:
            data["호"] = str(data["호"]).lstrip("0") or str(data.get("호",""))
        if 성명힌트 and not data.get("성명","").strip():
            data["성명"] = 성명힌트

        result.update(data)
        result["_엔진"] = result.get("_엔진", "").replace("+Claude", "") + "+Claude" if "Clova" in result.get("_엔진","") or "Tesseract" in result.get("_엔진","") else "Clova+Claude"

        # ── 미비서류 ──────────────────────────────────────────────────
        from core.extractor import check_missing_docs
        found_raw = data.get("서류목록","")
        kw_map = {
            "분양계약서":       ["공급계약서","분양계약서"],
            "주민등록초본":     ["주민등록표","초본"],
            "인감증명서":       ["인감증명서"],
            "근저당설정계약서": ["근저당권설정계약서","근저당설정"],
        }
        found_types    = [dt for dt,kws in kw_map.items() if any(k in found_raw for k in kws)]
        has_loan       = bool(data.get("채권최고액",""))
        승계여부        = data.get("승계여부","")
        has_succession = bool(승계여부 and 승계여부 not in ("","해당없음"))
        미비 = check_missing_docs(found_types, has_loan, has_succession,
                                   "증여" if "증여" in 승계여부 else "매매")
        result["미비서류"] = "" if 미비 == "없음" else 미비
        result["_상태"]    = "완료"

    except Exception as e:
        err_str = str(e)
        is_credit_err = "credit" in err_str.lower() or "balance" in err_str.lower()
        if is_credit_err:
            # 크레딧 부족 → 로컬 추출 시도
            _, local_data = _local_extract_bunyang(pdf_path)
            if local_data:
                result.update(local_data)
                result["_엔진"] = local_data.get("_엔진", engine if engine else "로컬OCR") if hasattr(local_data, 'get') else "로컬OCR"
                result["_상태"] = "완료(로컬)"
            else:
                result["_오류"] = "API 크레딧 부족"
                result["_상태"] = "오류"
        else:
            result["_오류"] = err_str[:200]
            result["_상태"] = "오류"

    # 성명힌트 최종 보완
    if 성명힌트 and not result.get("성명", "").strip():
        result["성명"] = 성명힌트

    return result
