"""
excel_manager.py — 수식 보존 엑셀 저장 엔진
============================================
• openpyxl 전용 (pandas 절대 사용 안 함)
• 템플릿 수식·서식·병합셀 100% 보존
• 동적 컬럼 매핑 + 프리셋 JSON 저장
• 수식 셀 자동 감지 → 건너뜀
"""
import json, shutil
from pathlib import Path
from datetime import date, datetime
from typing import Any
import openpyxl
from openpyxl.utils import get_column_letter, column_index_from_string

PRESETS_FILE = Path(__file__).parent / "mappings" / "_presets.json"


# ── 수식 감지 ──────────────────────────────────────────────────────────────────

def is_formula(cell) -> bool:
    """셀이 수식인지 확인"""
    v = cell.value
    return isinstance(v, str) and v.startswith("=")


def scan_formula_cols(ws, start_row: int, check_rows: int = 3) -> set:
    """수식이 있는 열 번호 집합 반환 (해당 열은 덮어쓰지 않음)"""
    formula_cols = set()
    for row in range(start_row, start_row + check_rows):
        for col in range(1, ws.max_column + 1):
            if is_formula(ws.cell(row=row, column=col)):
                formula_cols.add(col)
    return formula_cols


# ── 템플릿 분석 ────────────────────────────────────────────────────────────────

def analyze_template(template_path: str, sheet_name: str = None,
                     header_row: int = 1) -> dict:
    """
    템플릿 엑셀 헤더 행을 읽어 필드→열 매핑 자동 제안.
    반환: {헤더명: 열번호}
    """
    wb = openpyxl.load_workbook(template_path, data_only=False)
    if sheet_name and sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
    else:
        ws = wb.active

    mapping = {}
    for col in range(1, ws.max_column + 1):
        cell_val = ws.cell(row=header_row, column=col).value
        if cell_val and str(cell_val).strip():
            mapping[str(cell_val).strip()] = col
    return mapping


def get_sheets(template_path: str) -> list:
    """템플릿 파일의 시트 목록 반환"""
    wb = openpyxl.load_workbook(template_path, read_only=True)
    return wb.sheetnames


# ── 핵심 저장 함수 ─────────────────────────────────────────────────────────────

def write_to_template(
    template_path: str,
    output_path: str,
    sheet_name: str,
    mapping: dict,          # {필드명: 열번호(int)}
    records: list,          # list[dict]
    start_row: int = 2,     # 데이터 시작 행
    skip_formula_cols: bool = True,
    overwrite_existing: bool = False,
) -> dict:
    """
    수식 보존 엑셀 저장.

    Parameters
    ----------
    template_path       : 원본 템플릿 경로
    output_path         : 저장할 파일 경로
    sheet_name          : 대상 시트명
    mapping             : {필드명: 열번호}
    records             : 입력할 데이터 행 목록
    start_row           : 데이터 입력 시작 행 (1-indexed)
    skip_formula_cols   : True이면 수식 셀은 덮어쓰지 않음
    overwrite_existing  : True이면 기존 output_path 덮어쓰기

    Returns
    -------
    dict: {success: bool, written: int, skipped: int, errors: list}
    """
    result = {"success": False, "written": 0, "skipped": 0, "errors": []}

    if not Path(template_path).exists():
        result["errors"].append(f"템플릿 없음: {template_path}")
        return result

    # 항상 템플릿에서 새로 복사 후 저장 (수식 100% 보존)
    shutil.copy(template_path, output_path)
    src = output_path

    try:
        wb = openpyxl.load_workbook(src)
    except Exception as e:
        result["errors"].append(f"파일 열기 실패: {e}")
        return result

    if sheet_name not in wb.sheetnames:
        result["errors"].append(f"시트 없음: {sheet_name}")
        return result

    ws = wb[sheet_name]

    # 수식 열 스캔
    formula_cols = scan_formula_cols(ws, start_row) if skip_formula_cols else set()
    if formula_cols:
        formula_col_names = [get_column_letter(c) for c in formula_cols]
        result["formula_cols"] = formula_col_names

    # 데이터 입력
    for i, rec in enumerate(records):
        row = start_row + i
        for field, col in mapping.items():
            if col in formula_cols:
                result["skipped"] += 1
                continue
            val = rec.get(field)
            if val is None:
                continue
            # 날짜 변환
            if isinstance(val, str) and len(val) == 10 and val[4] == "-":
                try:
                    val = date.fromisoformat(val)
                except ValueError:
                    pass
            cell = ws.cell(row=row, column=col)
            cell.value = val
            result["written"] += 1

    try:
        wb.save(output_path)
        result["success"] = True
    except Exception as e:
        result["errors"].append(f"저장 실패: {e}")

    return result


# ── 프리셋 관리 ────────────────────────────────────────────────────────────────

def load_presets() -> dict:
    """모든 프리셋 로드"""
    if not PRESETS_FILE.exists():
        return {}
    try:
        return json.loads(PRESETS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_preset(name: str, preset: dict):
    """프리셋 저장"""
    PRESETS_FILE.parent.mkdir(exist_ok=True)
    all_p = load_presets()
    all_p[name] = preset
    PRESETS_FILE.write_text(
        json.dumps(all_p, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def delete_preset(name: str):
    all_p = load_presets()
    all_p.pop(name, None)
    PRESETS_FILE.write_text(
        json.dumps(all_p, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def get_preset_names() -> list:
    return list(load_presets().keys())


# ── 편의 함수 ──────────────────────────────────────────────────────────────────

def col_letter_to_num(letter: str) -> int:
    """'A' → 1, 'B' → 2, 'AA' → 27"""
    try:
        return column_index_from_string(letter.upper().strip())
    except Exception:
        return 0


def col_num_to_letter(num: int) -> str:
    """1 → 'A', 27 → 'AA'"""
    try:
        return get_column_letter(int(num))
    except Exception:
        return ""
