"""
기본명단 실제 템플릿에 데이터 입력 모듈
- 기존 엑셀 파일을 그대로 열어서 값만 써넣음 (서식 100% 보존)
- 시트: 기본명단(음성아이파크)
- 헤더: 1행, 데이터: 2행~
"""

import re
import openpyxl
from copy import copy
from pathlib import Path


def clean_address(addr):
    if not addr:
        return addr
    addr = re.sub(r'^[\s\-]*[\*#]+[\s\*#\-]*', '', str(addr))  # 앞 마스킹 제거
    addr = addr.strip(' |')                                      # 뒤 | 제거
    return addr.strip()

# ─── 실제 열 번호 매핑 (헤더 분석 결과 기준) ──────────────────────────────────
# col 번호 = openpyxl column index (1-based)
COL = {
    "연번":            1,   # A
    "서류수령일":       4,   # D
    "미비서류":        22,  # V
    "초본":            26,  # Z
    "인감":            27,  # AA
    "권리의무승계여부": 24,  # X
    "승계일자":        25,  # Y
    "동":              30,  # AD
    "층":              31,  # AE
    "호수":            32,  # AF
    "성명":            33,  # AG
    "연락처1":         34,  # AH
    "주민등록번호":     36,  # AJ
    "주소":            37,  # AK
    "전용면적":        42,  # AP
    "대지권면적":      43,  # AQ
    "계약일":          44,  # AR
    "분양가격":        45,  # AS
    "건물부가세":      46,  # AT
    "옵션1가격":       50,  # AX  (발코니)
    "옵션2가격":       55,  # BC  (시스템에어컨 등)
    "실거래일련번호":  61,  # BI  (거래신고필증번호)
    "거래가액":        62,  # BJ
    "대출은행1":       84,  # CF
    "취급지점1":       85,  # CG
    "채권최고액1":     93,  # CO
    "설정계약일":      96,  # CR
    # 등기비용 — 이전
    "채권매입금액_이전":  69,  # BQ
    "채권할인금액_이전":  70,  # BR
    "인지대_이전":        71,  # BS
    "증지대_이전":        72,  # BT
    "교통비":             73,  # BU
    "제증명료":           74,  # BV
    "보수료":             76,  # BX
    "부가세_이전":        79,  # CA
    "설정비용합계":       80,  # CB  (설정채권 청구)
    "신탁말소비용":        81,  # CC
    "송달료":             82,  # CD
    "등기비용총합계":     83,  # CE  (이전+설정 합계)
    "등기비용합계_AL":    38,  # AL  (동일값 이중입력)
    # 설정 — 1순위
    "등록세_설정":        97,  # CS
    "교육세_설정":        98,  # CT
    "채권매입금액_설정":  99,  # CU
    "채권할인금액_설정": 100,  # CV
    "증지대_설정":       101,  # CW
    "보수료_설정":       107,  # DC
    "부가세_설정":       110,  # DF
    "설정비용1순위":     113,  # DI
    # 취득세 관련
    "분양대금과표":     49,  # AW
    "옵션1과표":       54,  # BB
    "옵션2과표":       59,  # BG
    "취득세과표":      64,  # BL
    "취득세":         65,  # BM
    "교육세":         66,  # BN
    "농특세":         67,  # BO
    "취득세합계":      68,  # BP
    "주택수":         12,  # L
    "감면여부열":      11,  # K
}

# 추출 데이터 키 → 엑셀 열 매핑
FIELD_TO_COL = {
    "동":               COL["동"],
    "호":               COL["호수"],
    "성명":             COL["성명"],
    "전화번호":          COL["연락처1"],
    "주민등록번호":       COL["주민등록번호"],
    "주소":             COL["주소"],
    "전용면적":          COL["전용면적"],
    "분양계약일":        COL["계약일"],
    "분양대금":          COL["분양가격"],
    "부가세":            COL["건물부가세"],
    "발코니금액":        COL["옵션1가격"],
    "옵션금액":          COL["옵션2가격"],
    "승계여부":          COL["권리의무승계여부"],
    "승계일":            COL["승계일자"],
    "거래신고필증번호":   COL["실거래일련번호"],
    "거래가액":          COL["거래가액"],
    "대출은행":          COL["대출은행1"],
    "대출지점":          COL["취급지점1"],
    "채권최고액":        COL["채권최고액1"],
    "근저당설정계약일":   COL["설정계약일"],
    "서류수령일":        COL["서류수령일"],
    "초본발행일":        COL["초본"],
    "인감발행일":        COL["인감"],
    # 등기비용
    "채권매입금액_이전":  COL["채권매입금액_이전"],
    "채권할인금액_이전":  COL["채권할인금액_이전"],
    "인지대_이전":        COL["인지대_이전"],
    "증지대_이전":        COL["증지대_이전"],
    "교통비":             COL["교통비"],
    "제증명료":           COL["제증명료"],
    "보수료":             COL["보수료"],
    "부가세_이전":        COL["부가세_이전"],
    "설정비용합계":       COL["설정비용합계"],
    "신탁말소비용":        COL["신탁말소비용"],
    "송달료":             COL["송달료"],
    "등기비용총합계":     COL["등기비용총합계"],
    "등기비용합계_AL":    COL["등기비용합계_AL"],
    "등록세_설정":        COL["등록세_설정"],
    "교육세_설정":        COL["교육세_설정"],
    "채권매입금액_설정":  COL["채권매입금액_설정"],
    "채권할인금액_설정":  COL["채권할인금액_설정"],
    "증지대_설정":        COL["증지대_설정"],
    "보수료_설정":        COL["보수료_설정"],
    "부가세_설정":        COL["부가세_설정"],
    "설정비용1순위":      COL["설정비용1순위"],
    # 취득세
    "취득세과표":        COL["취득세과표"],
    "취득세":           COL["취득세"],
    "교육세":           COL["교육세"],
    "농특세":           COL["농특세"],
    "취득세합계":        COL["취득세합계"],
    "미비서류":          COL["미비서류"],
}

HEADER_ROW = 1   # 헤더
DATA_START  = 2  # 데이터 시작 행


def find_next_empty_row(ws) -> int:
    """성명(AG) 기준으로 첫 번째 빈 행 찾기"""
    for row in range(DATA_START, ws.max_row + 2):
        if ws.cell(row=row, column=COL["성명"]).value is None:
            return row
    return DATA_START


def _copy_row_style(ws, src_row: int, dst_row: int):
    """src_row의 스타일을 dst_row에 복사 (서식 확장용)"""
    for col in range(1, ws.max_column + 1):
        src_cell = ws.cell(row=src_row, column=col)
        dst_cell = ws.cell(row=dst_row, column=col)
        if src_cell.has_style:
            dst_cell.font      = copy(src_cell.font)
            dst_cell.fill      = copy(src_cell.fill)
            dst_cell.border    = copy(src_cell.border)
            dst_cell.alignment = copy(src_cell.alignment)
            dst_cell.number_format = src_cell.number_format
    # 행 높이 복사
    if ws.row_dimensions[src_row].height:
        ws.row_dimensions[dst_row].height = ws.row_dimensions[src_row].height


def write_to_template(template_path: str, records: list[dict], output_path: str = None):
    """
    실제 기본명단 템플릿에 데이터 입력 후 저장.
    output_path 없으면 template_path 덮어씀.
    서식(폰트/테두리/배경/정렬) 100% 보존.
    """
    output_path = output_path or template_path

    wb = openpyxl.load_workbook(template_path)

    # 기본명단 시트 찾기
    target_sheet = None
    for name in wb.sheetnames:
        if "기본명단" in name:
            target_sheet = name
            break
    if not target_sheet:
        target_sheet = wb.sheetnames[0]

    ws = wb[target_sheet]
    start_row = find_next_empty_row(ws)

    # 서식 복사용 기준 행 (2행 — 템플릿에서 이미 서식 세팅된 행)
    style_ref_row = DATA_START

    # 동/호/성명 모두 공란인 빈 행 제거
    records = [r for r in records
               if r.get("동") or r.get("호") or r.get("성명")]

    for i, record in enumerate(records):
        row = start_row + i

        # 해당 행에 서식이 없으면 위 행에서 복사
        if ws.cell(row=row, column=COL["성명"]).font.name is None:
            _copy_row_style(ws, style_ref_row, row)

        # 연번 자동 입력
        ws.cell(row=row, column=COL["연번"]).value = row - HEADER_ROW

        # 각 필드 입력
        for field, col_idx in FIELD_TO_COL.items():
            value = record.get(field)
            if value in (None, "", 0) and field not in ("부가세", "거래가액"):
                continue
            cell = ws.cell(row=row, column=col_idx)

            # 주소 정제
            if field == "주소":
                cell.value = clean_address(str(value))
                continue

            # 금액 필드: 숫자로
            if field in ("분양대금", "부가세", "발코니금액", "옵션금액",
                         "채권최고액", "거래가액"):
                try:
                    cell.value = int(value) if value else 0
                except (ValueError, TypeError):
                    cell.value = value
            else:
                cell.value = str(value) if value is not None else ""

    wb.save(output_path)
    print(f"✅ 저장 완료: {output_path}  ({len(records)}건 입력, {start_row}행~{start_row+len(records)-1}행)")
    return output_path


# 구버전 호환용 래퍼
def create_기본명단(output_path: str, records: list[dict], template_path: str = None):
    """
    template_path가 있으면 해당 파일에 입력.
    없으면 output_path 자체가 템플릿이라고 가정.
    """
    if template_path:
        write_to_template(template_path, records, output_path)
    else:
        # output_path가 이미 존재하면 거기에 이어 씀
        if Path(output_path).exists():
            write_to_template(output_path, records)
        else:
            raise FileNotFoundError(
                f"기본명단 템플릿 파일이 없습니다: {output_path}\n"
                "--template 옵션으로 원본 파일을 지정해주세요."
            )
