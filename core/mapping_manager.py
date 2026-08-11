"""
사무소별 매핑 파일 관리 모듈
mappings/*.json → 열 매핑 로드 → 엑셀 입력
"""

import json
from pathlib import Path
from copy import copy
import openpyxl

MAPPINGS_DIR = Path(__file__).parent.parent / "mappings"


# ─── 매핑 파일 목록 ───────────────────────────────────────────────────────────

def _write_cell(ws, row, col, val, is_amount=False):
    """셀에 값 쓰기 (날짜 변환 포함)"""
    from datetime import date, datetime
    import re
    if isinstance(val, str):
        # 날짜 변환
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})$", val)
        if m:
            try:
                val = date(int(m.group(1)),int(m.group(2)),int(m.group(3)))
            except ValueError:
                pass
    ws.cell(row=row, column=col).value = val


def _clear_data_rows(ws, data_start: int, formula_cols: set = None):
    """
    데이터 시작행부터 마지막 데이터행까지 비수식 셀을 클리어.
    수식(=로 시작)과 formula_cols는 보존.
    중복 저장 방지 목적.
    """
    formula_cols = formula_cols or set()
    for r in range(data_start, min(ws.max_row + 1, data_start + 1000)):
        # 이 행에 데이터가 있는지 확인
        row_has_data = False
        for c in range(1, ws.max_column + 1):
            cell = ws.cell(r, c)
            if cell.value is not None and cell.value != "":
                if not (isinstance(cell.value, str) and cell.value.startswith("=")):
                    row_has_data = True
                    break
        if not row_has_data:
            break  # 빈 행이면 그 이하도 비어있으므로 종료
        # 비수식 셀만 클리어
        for c in range(1, ws.max_column + 1):
            if c in formula_cols:
                continue
            cell = ws.cell(r, c)
            if isinstance(cell.value, str) and cell.value.startswith("="):
                continue  # 수식 보존
            cell.value = None


def get_mapping_list() -> list[str]:
    """사무소 이름 목록 반환 (_presets 제외)"""
    files = sorted(MAPPINGS_DIR.glob("*.json"))
    return [f.stem for f in files if not f.stem.startswith("_")]


def load_mapping(사무소명: str) -> dict:
    """사무소명으로 매핑 로드"""
    path = MAPPINGS_DIR / f"{사무소명}.json"
    if not path.exists():
        raise FileNotFoundError(f"매핑 파일 없음: {path}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_mapping(사무소명: str, mapping: dict):
    """매핑 저장"""
    MAPPINGS_DIR.mkdir(exist_ok=True)
    path = MAPPINGS_DIR / f"{사무소명}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
    print(f"✅ 매핑 저장: {path}")


def delete_mapping(사무소명: str):
    """매핑 삭제"""
    path = MAPPINGS_DIR / f"{사무소명}.json"
    if path.exists():
        path.unlink()


# ─── 엑셀 입력 (매핑 기반) ───────────────────────────────────────────────────

def _atomic_save(wb, output_path: str):
    """임시 파일에 저장 후 원자적 교체 — 저장 중 크래시로 원본이 깨지는 것 방지."""
    import os, tempfile
    d = os.path.dirname(os.path.abspath(output_path)) or "."
    fd, tmp = tempfile.mkstemp(suffix=".xlsx", dir=d)
    os.close(fd)
    try:
        wb.save(tmp)
        os.replace(tmp, output_path)
    except Exception:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
        raise


def _make_backup(path: str):
    """기존 파일을 타임스탬프 백업으로 복사. 없으면 None."""
    import os, shutil
    from datetime import datetime
    if not os.path.exists(path):
        return None
    p = Path(path)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = p.with_name(f"{p.stem}_백업_{stamp}{p.suffix}")
    shutil.copy2(path, bak)
    return str(bak)


def _index_existing_units(ws, dong_col: int, ho_col: int, data_start: int) -> dict:
    """기존 행을 스캔해 (동,호) → 행번호 인덱스 구성 (이어쓰기 upsert용)."""
    idx = {}
    r = data_start
    max_row = min(ws.max_row, 1048575)
    while r <= max_row:
        dv = ws.cell(row=r, column=dong_col).value
        hv = ws.cell(row=r, column=ho_col).value
        if dv not in (None, "") and hv not in (None, ""):
            idx[(str(dv).strip(), str(hv).strip())] = r
        r += 1
    return idx


def write_with_mapping(template_path: str, records: list[dict],
                       사무소명: str, output_path: str = None,
                       append: bool = False, backup: bool = False):
    """
    사무소별 매핑으로 기본명단 엑셀에 데이터 입력.

    append=False (기본): 기존 데이터 클리어 후 처음부터 기입 (단일 실행 저장).
    append=True:         기존 데이터 보존하고 이어서 기입 —
                         순차 모드는 다음 빈 행부터 연번 이어서,
                         동/호 매칭 모드는 같은 동/호는 갱신·새 동/호는 추가(upsert).
    backup=True:         저장 전 기존 output 파일을 타임스탬프 백업.
    저장은 항상 원자적(임시파일 → 교체).
    """
    mapping   = load_mapping(사무소명)
    info      = mapping["_info"]
    col_map   = {k: int(v) for k, v in mapping["_columns"].items()}
    amount_cols = set(mapping.get("_amount_columns", []))
    key_col   = int(mapping.get("_key_column", 1))

    output_path = output_path or template_path

    # 이어쓰기는 기존 output 파일을 기준으로 열어야 데이터가 보존됨
    load_path = output_path if (append and Path(output_path).exists()) else template_path
    if backup:
        _make_backup(output_path)

    wb = openpyxl.load_workbook(load_path)

    # 시트 찾기 (정확한 이름 → 부분일치 → active 순서)
    sheet_name = info.get("시트명", "")
    ws = None
    if sheet_name and sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
    if ws is None:
        for s in wb.sheetnames:
            if "기본명단" in s:
                ws = wb[s]
                break
    if ws is None:
        ws = wb.active

    print(f"  📋 입력 시트: [{ws.title}]  (모드: {'이어쓰기' if append else '새로쓰기'})")

    data_start = int(info.get("데이터시작행", 2))
    serial_col  = col_map.get("연번")

    # ── 동/호 매칭 모드 (검단 기초입력 등) ────────────────────────
    key_match = mapping.get("_key_match", {})  # {"동": 11, "호": 12}
    formula_cols = set(mapping.get("_formula_cols", []))
    preserve_cols = set(mapping.get("_preserve_cols", []))

    if key_match:
        dong_col = int(key_match.get("동", 0))
        ho_col   = int(key_match.get("호", 0))

        if append:
            # 기존 데이터 보존 + 기존 동/호 인덱스 구성 (upsert)
            row_index = _index_existing_units(ws, dong_col, ho_col, data_start)
        else:
            # 새로쓰기: 기존 데이터 클리어
            _clear_data_rows(ws, data_start, formula_cols)
            row_index = {}

        for record in records:
            dong = str(record.get("동", "")).strip()
            ho   = str(record.get("호", "")).strip()
            if not dong or not ho:
                continue
            row = row_index.get((dong, ho))
            if not row:
                row = _find_next_row(ws, dong_col, data_start)
                ws.cell(row=row, column=dong_col).value = dong
                ws.cell(row=row, column=ho_col).value = ho
                row_index[(dong, ho)] = row

            for field, col_idx in col_map.items():
                if col_idx in formula_cols or col_idx in preserve_cols:
                    continue
                val = record.get(field)
                if val is None or val == "":
                    continue
                cell = ws.cell(row=row, column=col_idx)
                if isinstance(cell.value, str) and cell.value.startswith("="):
                    continue
                _write_cell(ws, row, col_idx, val, col_idx in amount_cols)

        _atomic_save(wb, output_path)
        print(f"✅ [{사무소명}] 저장 완료: {output_path}  ({len(records)}건)")
        return output_path

    # ── 순차 모드 ────────────────────────────────────────────────
    if append:
        # 이어쓰기: 기존 데이터 유지, 다음 빈 행부터, 연번 이어서
        start_row   = _find_next_row(ws, serial_col or key_col, data_start)
        last_serial = _get_last_serial(ws, serial_col, data_start) if serial_col else 0
    else:
        # 새로쓰기: 기존 데이터 클리어
        _clear_data_rows(ws, data_start, formula_cols)
        start_row   = data_start
        last_serial = 0

    for i, record in enumerate(records):
        row = start_row + i

        # 위 행 서식 복사 (데이터 있는 마지막 행 기준)
        ref_row = start_row - 1 if start_row > data_start else data_start
        _copy_style(ws, ref_row, row)

        # 연번 — 기존 마지막 연번 이어서 채번
        if serial_col:
            ws.cell(row=row, column=serial_col).value = last_serial + i + 1

        # 데이터 입력
        for field, col_idx in col_map.items():
            if field in ("연번",):
                continue
            value = record.get(field)
            if value is None or value == "":
                continue
            cell = ws.cell(row=row, column=col_idx)
            if col_idx in amount_cols:
                try:
                    cell.value = int(str(value).replace(",", "")) if value else 0
                except:
                    cell.value = value
            else:
                cell.value = str(value) if value is not None else ""

    # 저장 전 기본명단 시트를 활성(첫 화면)으로 설정
    try:
        wb.active = wb.index(ws)
    except Exception:
        try:
            wb.active = list(wb.sheetnames).index(ws.title)
        except:
            pass

    _atomic_save(wb, output_path)
    print(f"✅ [{사무소명}] 저장 완료: {output_path}  ({len(records)}건)")
    return output_path


def _find_next_row(ws, key_col: int, start: int) -> int:
    """마지막 데이터 행 다음 행 반환"""
    last = start - 1
    max_row = min(ws.max_row, 1048575)
    for row in range(start, max_row + 1):
        val = ws.cell(row=row, column=key_col).value
        if val not in (None, ""):
            last = row
    return last + 1


def _get_last_serial(ws, serial_col: int, start: int) -> int:
    """기존 파일의 마지막 연번 반환 (없으면 0)"""
    last = 0
    max_row = min(ws.max_row, 1048575)
    for row in range(start, max_row + 1):
        val = ws.cell(row=row, column=serial_col).value
        try:
            n = int(val)
            last = max(last, n)
        except (TypeError, ValueError):
            pass
    return last


def _copy_style(ws, src: int, dst: int):
    for col in range(1, ws.max_column + 1):
        s = ws.cell(row=src, column=col)
        d = ws.cell(row=dst, column=col)
        if s.has_style:
            d.font      = copy(s.font)
            d.fill      = copy(s.fill)
            d.border    = copy(s.border)
            d.alignment = copy(s.alignment)
            d.number_format = s.number_format
    if ws.row_dimensions[src].height:
        ws.row_dimensions[dst].height = ws.row_dimensions[src].height


# ─── 헤더 자동 분석 (새 사무소 매핑 생성 보조) ──────────────────────────────

# 헤더 키워드 → 필드명 매핑
HEADER_KEYWORDS = {
    # 기본정보
    "연번":            ["연번", "번호", "순번", "no", "번"],
    "서류수령일":      ["수령일", "서류수령", "접수일", "수령"],
    "동":              ["동", "동번호", "동호수", "아파트동"],
    "호":              ["호", "호수", "호번호", "아파트호"],
    "성명":            ["성명", "이름", "수분양자", "매수인", "소유자", "성함",
                        "매수인성명", "수분양자성명"],
    "전화번호":        ["연락처", "전화번호", "전화", "휴대폰", "휴대전화",
                        "핸드폰", "전화(휴대)"],
    "주민등록번호":    ["주민등록번호", "주민번호", "생년월일", "주민"],
    "주소":            ["주소", "현주소", "주소지", "거주지", "거주주소",
                        "현재주소"],
    "전용면적":        ["전용면적", "전용", "건물면적", "면적", "㎡"],
    "대지지분":        ["대지지분", "대지권", "대지면적", "대지"],
    "초본":            ["초본", "주민등록초본", "초본발행"],
    "인감":            ["인감", "인감증명", "인감발행"],
    "등본":            ["등본", "주민등록등본", "등본발행"],
    "미비서류":        ["미비서류", "미비", "미비사항", "미비내용"],
    # 분양정보
    "분양계약일":      ["계약일", "분양계약일", "계약날짜", "분양계약"],
    "분양대금":        ["분양가격", "분양대금", "분양가", "총분양가",
                        "분양금액", "매매대금"],
    "부가세":          ["부가세", "vat", "부가가치세"],
    "발코니금액":      ["발코니", "발코니금액", "발코니확장"],
    "옵션금액":        ["옵션", "유상옵션", "옵션금액", "선택품목"],
    "거래가액":        ["거래가액", "실거래가", "거래금액", "매매가"],
    # 승계
    "승계여부":        ["승계여부", "권리의무승계", "승계", "권리승계"],
    "승계일":          ["승계일", "승계날짜", "권리이전일"],
    "거래신고필증번호": ["신고필증", "거래신고", "필증번호", "신고번호"],
    # 대출/채권
    "대출은행":        ["대출은행", "은행", "금융기관"],
    "대출지점":        ["지점", "대출지점", "은행지점"],
    "채권최고액":      ["채권최고액", "채권액", "최고채권"],
    "근저당설정계약일": ["설정계약일", "근저당설정", "설정일"],
    # 취득세/비용
    "취득세":          ["취득세", "취득세액"],
    "교육세":          ["교육세"],
    "농특세":          ["농특세", "농어촌특별세"],
    "취득세합계":      ["취득세합계", "세금합계", "취득관련세금"],
    "등기비용총합계":  ["등기비용합계", "등기비용", "총등기비용", "비용합계"],
}


def analyze_template(xlsx_path: str, 사무소명: str,
                     header_row: int = None) -> dict:
    """
    템플릿 엑셀의 헤더를 분석해서 매핑 자동 생성.
    header_row=None 이면 1~5행 중 매칭 가장 많은 행 자동 선택.
    """
    wb = openpyxl.load_workbook(xlsx_path)

    # 시트 탐색: 기본명단 포함 > 첫 번째
    ws = next((wb[s] for s in wb.sheetnames
               if any(k in s for k in ["기본명단","명단","APT","아파트","오피"])),
              wb.active)
    sheet_name = ws.title

    # 헤더행 자동 탐지
    if header_row is None:
        best_row, best_count = 1, 0
        for r in range(1, 6):
            count = 0
            for col in range(1, min(ws.max_column+1, 220)):
                v = str(ws.cell(row=r, column=col).value or "").replace("\n","").replace(" ","")
                for kws in HEADER_KEYWORDS.values():
                    for kw in kws:
                        if kw.replace(" ","") in v:
                            count += 1
                            break
            if count > best_count:
                best_count, best_row = count, r
        header_row = best_row

    columns = {}
    for col in range(1, ws.max_column + 1):
        cell_val = str(ws.cell(row=header_row, column=col).value or "").strip()
        cell_val_clean = cell_val.replace("\n", "").replace(" ", "")
        for field, keywords in HEADER_KEYWORDS.items():
            for kw in keywords:
                if kw.replace(" ", "") in cell_val_clean:
                    if field not in columns:
                        columns[field] = col
                    break

    mapping = {
        "_info": {
            "사무소명":   사무소명,
            "템플릿":     Path(xlsx_path).name,
            "시트명":     sheet_name,
            "헤더행":     header_row,
            "데이터시작행": header_row + 1,
        },
        "_columns":        columns,
        "_amount_columns": [],
        "_key_column":     columns.get("성명", 1),
    }
    return mapping
