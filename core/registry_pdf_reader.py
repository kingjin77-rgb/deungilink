"""
등기부등본 파서 — 실제 PDF 테스트 기반 최종버전
동탄파크릭스 실제 등기부등본 구조 완전 대응
"""
import re
from pathlib import Path


def extract_pdf_text(pdf_path: str) -> str:
    """
    대법원 텍스트 PDF: pdfplumber로 추출 (한글 50자 이상이면 API 호출 없음).
    이미지 PDF fallback: Claude Vision → Tesseract.
    """
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            pages = [p.extract_text(x_tolerance=2, y_tolerance=2) or "" for p in pdf.pages]
        text = "\n".join(pages)
        if len(re.findall(r"[가-힣]", text)) >= 50:
            return text  # 충분한 텍스트 추출 → API 미사용
    except Exception:
        pass
    # 이미지 PDF 또는 pdfplumber 실패 시에만 Claude 호출
    try:
        from core.vision_ocr import _api_key
        if _api_key():
            from core.claude_ocr import ocr_text_with_claude
            return ocr_text_with_claude(pdf_path)
    except Exception:
        pass
    try:
        from core.vision_ocr import ocr_pdf_tesseract
        return ocr_pdf_tesseract(pdf_path)
    except Exception as e:
        raise RuntimeError(f"추출 실패: {e}")


def _split(text: str):
    # OCR 오인식 허용: 갑→감, 】→J/]/j, 공백 다수 허용
    # 1순위: 【...갑/감...구...】/J 패턴 (같은 줄, 공백 최대 12자)
    갑_m = re.search(r"(?:^|\n)[^\n]*【[^\n]{0,12}[갑감][^\n]{0,12}구[^\n]{0,10}[】J\]j][^\n]*(?:\n|$)", text)
    if not 갑_m:
        갑_m = re.search(r"(?:^|\n)[^\n]*【\s*갑\s*구\s*】[^\n]*(?:\n|$)", text)
    if not 갑_m:
        갑_m = re.search(r"(?:^|\n)\s*갑\s*구\s*(?:\n|$)", text)
    을_m = re.search(r"(?:^|\n)[^\n]*【[^\n]{0,12}을[^\n]{0,12}구[^\n]{0,10}[】J\]j][^\n]*(?:\n|$)", text)
    if not 을_m:
        을_m = re.search(r"(?:^|\n)[^\n]*【\s*을\s*구\s*】[^\n]*(?:\n|$)", text)
    if not 을_m:
        을_m = re.search(r"(?:^|\n)\s*을\s*구\s*(?:\n|$)", text)
    갑s = 갑_m.start() if 갑_m else len(text)
    을s = 을_m.start() if 을_m else len(text)
    # 을구가 갑구보다 먼저 나오면 비정상 — 전체를 표제부로 처리
    if 을s <= 갑s:
        을s = len(text)
    return text[:갑s], text[갑s:을s], text[을s:]


def _date(s: str) -> str:
    m = re.search(r"(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일", s)
    if m: return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    m = re.search(r"(\d{4})[.\-](\d{1,2})[.\-](\d{1,2})", s)
    if m: return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    return ""


def parse_registry(text: str) -> dict:
    result = {}
    표제부, 갑구, 을구 = _split(text)

    # ── 신탁 ──────────────────────────────────────────────────────────────────
    n = len(re.findall(r"신탁\s*(?:등기|원부|말소)", text))
    result["신탁건수"] = min(n, 10)
    result["신탁유무"] = "있음" if n else "없음"

    # ── 아파트명칭 ─────────────────────────────────────────────────────────────
    apt = ""
    # 0순위: [집합건물] 헤더에서 아파트명칭 추출
    # 예: "62블록 호반써밋동탄 제4101동" → "호반써밋동탄"
    for hl in text.splitlines():
        if "집합건물" in hl:
            bm = re.search(r"블록\s+([가-힣A-Za-z0-9\-]+)\s+제?\d+동", hl)
            if bm:
                cand = bm.group(1).strip()
                if 3 <= len(cand) <= 25:
                    apt = cand
                    break
            bm2 = re.search(r"([가-힣A-Za-z0-9\-]{4,20})\s+제\d{3,4}동", hl)
            if bm2:
                cand2 = bm2.group(1)
                if not re.search(r"(?:특별시|광역시|시$|구$|동$|읍$|면$)", cand2):
                    apt = cand2
                    break

    # 1순위: 건물명칭 전용 필드 (0순위 결과 없을 때만)
    if not apt:
        m = re.search(r"건\s*물\s*명\s*칭\s+([^,\n]+)$", 표제부, re.MULTILINE)
        if m:
            cand = re.sub(r"\s{2,}", " ", m.group(1)).strip()
            if "건물내역" not in cand and "기타사항" not in cand and len(cand) >= 3:
                apt = cand
    # 2순위: 소재지번/헤더 텍스트에서 아파트명 추출
    # 패턴: "동탄파크릭스에이51-2블록아파트" 처럼 아파트 키워드 포함 단어
    if not apt:
        APT_KW = ["아파트","힐스","자이","래미안","이편한","이안","푸르지오",
                  "파크릭스","파크","르엘","타운","트리지움","캐슬","아이파크",
                  "더샵","아크로","디에이치","센트럴","단지"]
        # 소재지번 라인 전체 텍스트에서 탐색
        for line in (표제부 + "\n" + text[:200]).splitlines():
            line = line.strip()
            if any(kw in line for kw in APT_KW) and len(line) < 60:
                # 앞 노이즈 제거
                cand = re.sub(r"^.*?(?=동탄|잠실|음성|화성|광교|판교|위례)", "", line).strip()
                if not cand: cand = line
                cand = re.sub(r"\|.*$", "", cand).strip()  # 다단 OCR 구분선 이후 제거
                # "제X동" 이후 제거
                cand = re.sub(r"\s*제\s*\d+\s*동.*$", "", cand).strip()
                cand = re.sub(r"\s+", "", cand)  # 공백 제거
                if 4 <= len(cand) <= 30:
                    apt = cand
                    break

    # 3순위: 주소 괄호 안에서 추출 "(신동, 동탄파크릭스에이51-2블록아파트)"
    if not apt:
        BANK_KW = ["지점","은행","금융","저축","보험","투자","증권","카드","캐피탈"]
        for pm in re.findall(r"\(([^)]{4,30})\)", text):
            parts = [p.strip() for p in pm.split(",")]
            for part in reversed(parts):
                part = re.sub(r"\s+", "", part)
                if any(k in part for k in BANK_KW): continue
                if re.search(r"(?:동|읍|면|가|리)$", part) and len(part) <= 5: continue
                if any(kw in part for kw in APT_KW) and 4 <= len(part) <= 30:
                    apt = part
                    break
            if apt: break

    result["아파트명칭"] = apt

    # ── 동·호수 ───────────────────────────────────────────────────────────────
    dong, ho = "", ""

    # 0순위: [집합건물] 헤더 라인 — 층 정보 포함된 포맷 "제1101동 제2층 제201호"
    for line in text.splitlines():
        if "집합건물" in line:
            # 층 정보를 건너뛰는 패턴: 동과 호 사이에 층 정보가 있을 수 있음
            m = re.search(r"제\s*(\d{3,5})\s*동[^\n호]{0,30}제\s*(\d{2,5})\s*호", line)
            if m:
                dong = m.group(1).lstrip("0") or m.group(1)
                ho   = m.group(2).lstrip("0") or m.group(2)
                break
            # 동/호가 같은 줄에 없는 경우 동만 추출
            m = re.search(r"제\s*(\d{3,5})\s*동", line)
            if m and not dong:
                dong = m.group(1).lstrip("0") or m.group(1)
            m = re.search(r"제\s*(\d{2,5})\s*호", line)
            if m and not ho:
                ho = m.group(1).lstrip("0") or m.group(1)
        if dong and ho:
            break

    # 1순위: 표제부 검색 (기존 방식, 0순위 실패 시)
    search_zones = [표제부[:2000], 표제부, text[:3000]]
    for zone in search_zones:
        if dong and ho:
            break
        for pat in [
            r"제\s*(\d{1,5})\s*동\s*제\s*(\d{1,5})\s*호",
            r"(\d{3,5})\s*동\s*(\d{2,5})\s*호",  # 3자리 이상 동번호만 (1동708호 오매칭 방지)
        ]:
            m = re.search(pat, zone)
            if m:
                dong = m.group(1).lstrip("0") or m.group(1)
                ho   = m.group(2).lstrip("0") or m.group(2)
                break
        if not dong:
            m = re.search(r"(\d{2,5})[ \t]*동", zone)  # \s*→[ \t]*: 줄바꿈 매칭 방지
            if m:
                dong = m.group(1).lstrip("0") or m.group(1)
        if not ho:
            for pat in [r"제\s*(\d{2,5})\s*호", r"(\d{3,5})\s*호"]:
                m = re.search(pat, zone)
                if m:
                    ho = m.group(1).lstrip("0") or m.group(1)
                    break
    # 항상 키를 설정해야 formula/writer 에서 빈값 처리가 가능
    result["동"] = dong
    result["호"] = ho

    # ── 건물면적 ───────────────────────────────────────────────────────────────
    건물면적 = ""
    # ㎡ OCR 변형 포함 (변수명에 특수문자 불가 — sqm_pat 사용)
    sqm_pat = r"(?:㎡|m2|m²|m㎡)"
    area_pat = r"(\d{2,3}[.]\d{2,6})\s*(?:㎡|m2|m²|m(?![\d²2]))"

    # 1순위: 전유부분 섹션 — {0,1500}으로 확장
    전유_m = re.search(r"전\s*유\s*부\s*분([\s\S]{0,1500}?)(?=대지권의\s*표시|【|갑\s*구|\Z)", 표제부)
    if 전유_m:
        for v in re.findall(area_pat, 전유_m.group(0)):
            try:
                if 20 < float(v) < 300:
                    건물면적 = v
                    break
            except ValueError:
                pass
    # 1.5순위: 전유부분 섹션에서 단위 없는 면적 (OCR이 ㎡/m 완전히 누락한 경우)
    if not 건물면적 and 전유_m:
        for v in re.findall(r"(\d{2,3}\.\d{2,6})", 전유_m.group(0)):
            try:
                if 20 < float(v) < 200:
                    건물면적 = v
                    break
            except ValueError:
                pass
    # 1.6순위: 전유_m이 None일 때(표제부 분리 실패 등) 전체 텍스트에서 전유부분 탐색
    if not 건물면적 and not 전유_m:
        전유_m2 = re.search(r"전\s*유\s*부\s*분([\s\S]{0,1500}?)(?=대지권의\s*표시|【|갑\s*구|\Z)", text)
        if 전유_m2:
            for v in re.findall(area_pat, 전유_m2.group(0)):
                try:
                    if 20 < float(v) < 200:
                        건물면적 = v
                        break
                except ValueError:
                    pass
            if not 건물면적:
                for v in re.findall(r"(\d{2,3}\.\d{2,6})", 전유_m2.group(0)):
                    try:
                        if 20 < float(v) < 200:
                            건물면적 = v
                            break
                    except ValueError:
                        pass
    # 2순위: 구조/층 기반 패턴
    if not 건물면적:
        for pat in [
            r"(?:철근|목조|조적|RC)[^\n]{0,150}?(\d{2,3}[.]\d{2,6})\s*(?:㎡|m2)",
            r"\d+\s*층\s+(\d{2,3}[.]\d{2,6})\s*(?:㎡|m2)",
        ]:
            m = re.search(pat, 표제부, re.DOTALL)
            if m:
                try:
                    if 20 < float(m.group(1)) < 300:
                        건물면적 = m.group(1)
                        break
                except ValueError:
                    pass
    # 3순위: 표제부 전체 스캔
    if not 건물면적:
        for v in re.findall(area_pat, 표제부):
            try:
                if 20 < float(v) < 300:
                    건물면적 = v
                    break
            except ValueError:
                pass
    # 4순위: 전체 텍스트에서 재탐색 (표제부 분리 실패 대비)
    if not 건물면적:
        for v in re.findall(area_pat, text[:3000]):
            try:
                if 20 < float(v) < 300:
                    건물면적 = v
                    break
            except ValueError:
                pass
    # 5순위: ㎡ 없이 단독 줄에 있는 소수점 면적 (OCR에서 ㎡ 미인식)
    if not 건물면적:
        for line in (표제부 + "\n" + text[:3000]).splitlines():
            stripped = line.strip()
            m = re.match(r"^(\d{2,3}\.\d{2,6})0*$", stripped)
            if m:
                try:
                    v = float(m.group(1))
                    if 20 < v < 300:
                        건물면적 = m.group(1).rstrip("0").rstrip(".")
                        if "." not in 건물면적:
                            건물면적 = m.group(1)
                        break
                except ValueError:
                    pass
    if 건물면적:
        result["전용면적"] = 건물면적

    # ── 건물등기 접수일자 ──────────────────────────────────────────────────────
    # "이전" 키워드를 포함한 모든 등기목적에서 날짜 추출
    # 실제 포맷: "1번현대건설...일부이전 2025년10월23일 제5525551호"
    이전_dates = []

    # 패턴A: "이전" 또는 "소유권이전" 뒤 날짜 (한 줄에 병합된 형식)
    for line in 갑구.splitlines():
        if "이전" in line:
            d = _date(line)
            if d: 이전_dates.append(d)

    # 패턴B: 갑구 블록 내 이전 섹션
    for blk in re.finditer(r"이전([\s\S]{0,400}?)(?=\d+\s+\d+번|\d+\s+소유권|을\s*구|\Z)", 갑구):
        d = _date(blk.group(0))
        if d and d not in 이전_dates: 이전_dates.append(d)

    if 이전_dates:
        result["건물등기접수일자"] = sorted(이전_dates)[-1]  # 최신일
    else:
        # fallback: 보존등기
        for line in 갑구.splitlines():
            if "보존" in line:
                d = _date(line)
                if d: result["건물등기접수일자"] = d; break

    # ── 소유자 성명 ────────────────────────────────────────────────────────────
    # "소유자" OR "공유자" 키워드 (공동명의 = 공유자)
    owners = []
    _CORP_KW  = ["건설","주택","개발","공사","부영","대우","현대","삼성","주식","유한","토지"]
    _NON_NAME = {"열람일시","열람일","기록사항","이하여백","소유자","공유자","합유자","채무자","거래가액","소유권"}
    def _valid_name(n):
        return n not in _NON_NAME and not any(k in n for k in _CORP_KW)

    for pat in [
        # ★0순위: 한글이름 + 6자리 생년월일 + 마스킹(*,%,×,~ 등 OCR 변형 포함)
        #   개인 주민번호 뒷자리는 항상 마스킹됨 → 가장 안정적.
        #   이름·번호 사이 OCR 노이즈(_, 공백) 허용. 뒷자리에 마스킹문자 1개↑ 필수.
        #   법인등록번호(110111-0007909)는 뒷자리가 순수숫자라 자동 제외됨.
        r"([가-힣]{2,4})[\s_]+\d{6}\s*[-–][\d~]*[\*%×xX][\d~%\*×xX]*",
        # 외국인(미국인 등) 접두사 허용, 대시 없이도 4~7자리 ID로 매칭 (OCR 오인식 대비)
        r"(?:소유자|공유자)\s+(?:[가-힣]+인\s+)?([가-힣]{2,5})\s+\d{4,7}",
        r"(?:소유자|공유자)\s+(?:지분\s+\S+\s+)?([가-힣]{2,5})\s+\d{6}",
        # | 구분자 뒤 패턴: OCR이 '소유자'를 노이즈(AAR 등)로 치환한 경우 대비
        # [|｜]: ASCII 파이프 + 전각 파이프(U+FF5C) 모두 허용
        r"[|｜]\s*[A-Za-z]*\s*(?:소유자|공유자)?\s*(?:[가-힣]+인\s+)?([가-힣]{2,5})\s+\d{4,6}[-–*×]",
        # 지분 패턴: ID 필수 요구, 줄바꿈 허용([ \t\n])하되 이름과 ID 는 같은 줄
        r"지분[ \t]+\d+분[ \t]*의[ \t]*\d+[ \t\n]+([가-힣]{2,5})[ \t]+\d{6}",
        r"(?:소유자|공유자)\s+([가-힣]{2,5})\s*(?:\n|$)",
    ]:
        found = re.findall(pat, 갑구, re.MULTILINE)
        if found:
            owners = [n for n in found if _valid_name(n)]
            if owners: break

    if owners:
        result["성명"] = owners[-1]
        if len(owners) >= 2:
            result["공동명의자"] = owners[-2]

    # ── 소유자 주소 ────────────────────────────────────────────────────────────
    CITY = ["서울","경기","인천","부산","대구","광주","대전","울산","세종",
            "강원","제주","충북","충남","전북","전남","경북","경남"]
    SKIP = ["소유자","공유자","등기목적","등기원인","매매","증여","상속",
            "보존","이전","철근","콘크리트","슬래브","㎡","근저당","신탁",
            "채권","법인","순위번호","권리자","기타사항","표제","지분"]

    last_pos = 0
    if owners:
        for mm in re.finditer(re.escape(owners[-1]), 갑구):
            last_pos = mm.end()

    search_area = 갑구[last_pos:last_pos+600] if last_pos else 갑구[-600:]

    for line in search_area.splitlines():
        line = line.strip()
        if not line or len(line) < 8: continue
        if any(k in line for k in SKIP): continue
        if re.search(r"\d{6}[-–]\d", line): continue
        if re.search(r"제\s*\d{4,}\s*호", line): continue
        # 등기접수번호+등기원인 형식 줄 제외 (예: "제41663호      매매       경기도...")
        if re.search(r"제\s*\d{4,}\s*호\s+\S+", line): continue
        if any(c in line for c in CITY):
            if any(k in line for k in ["로","길","동","가","번지","구"]):
                addr = re.sub(r"^[가-힣]{2,5}\s+[\d\-*×\s]+\s*", "", line).strip()
                addr = re.sub(r"^[가-힣]{2,5}\s+", "", addr).strip()
                addr = re.sub(r"^\d+\s*", "", addr).strip()
                # [집합건물] 접두어 및 등기접수번호 제거
                addr = re.sub(r"^\[집합건물\]\s*", "", addr).strip()
                addr = re.sub(r"^제\s*\d{4,}\s*호\s+\S+\s+", "", addr).strip()
                # ★도시명 앞에 붙은 노이즈("일부(100분의19),", "중" 등) 제거 → 도시명부터 시작
                city_m = re.search(r"(?:" + "|".join(CITY) + r")", addr)
                if city_m:
                    addr = addr[city_m.start():].strip()
                if len(addr) > 8:
                    result["주소"] = addr; break

    # 주소 못 찾으면: 소유자 블록에서 도시명 포함 행
    if not result.get("주소"):
        for m2 in re.finditer(r"(?:소유자|공유자)[^\n]*\n\s*([^\n]*(?:" + "|".join(CITY) + r")[^\n]*)", 갑구):
            addr_line = m2.group(1).strip()
            addr_line = re.sub(r"^\[집합건물\]\s*", "", addr_line).strip()
            addr_line = re.sub(r"^제\s*\d{4,}\s*호\s+\S+\s+", "", addr_line).strip()
            if any(k in addr_line for k in ["로","길","동"]) and len(addr_line) > 8:
                result["주소"] = addr_line; break

    # ── 국적 ──────────────────────────────────────────────────────────────────
    result["국적"] = "외국인" if any(
        k in text for k in ["외국인등록","여권번호","FOREIGN","外國人"]) else ""

    # ── 미추출 필드 기록 ─────────────────────────────────────────────────────
    missing = [k for k in ["동","호","전용면적","건물등기접수일자","성명","주소"]
               if not result.get(k)]
    if missing: result["_미추출"] = ",".join(missing)

    return result
