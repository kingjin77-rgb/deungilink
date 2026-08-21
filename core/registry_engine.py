"""
개별 + 집단 등기 통합 엔진 (registry_engine)
============================================
개별등기(1건)와 집단등기(단지 n건)를 하나의 코어로 처리한다.
  • 개별등기 = 집단등기의 n=1 케이스.
  • 추출: Claude Vision(vision_extract) 우선 → 실패 시 정규식(extractor) 폴백.
  • 병합: 신뢰도 우선순위(core/merge) → 세금·비용·파생필드(processor.merge_unit_records).
  • 신탁: 세대별 등기부등본 기준(단지 전체 획일 적용 아님).

진입점:
  process_documents(doc_records, meta)      — 이미 추출된 서류 레코드 → 세대 1행
  process_pdf_files(pdf_paths, meta)        — PDF 파일들 → 세대 1행
  process_individual(path, meta)            — 개별등기 1세대 (파일 또는 폴더)
  process_group(root, meta, workers)        — 집단등기 (세대별 하위폴더 n개)
"""

from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from core.processor import merge_unit_records

# 서류로 인식하는 PDF 확장자
_PDF_EXTS = {".pdf"}


# ══════════════════════════════════════════════════════════════════════
#  메타(세대 공통 입력) 처리
# ══════════════════════════════════════════════════════════════════════

def _meta_record(meta: dict) -> dict:
    """
    세대 공통 입력(아파트유형·감면여부·주택수·조정대상지역)을 병합용
    가상 레코드로 변환. 병합 시 실제 서류값과 함께 반영된다.
    """
    meta = meta or {}
    rec = {"doc_type": "_meta", "_confidence": 0.0}
    for k in ("아파트유형", "감면여부", "주택수", "조정대상지역"):
        if meta.get(k) not in (None, ""):
            rec[k] = meta[k]
    rec.setdefault("아파트유형", "분양")
    return rec


# ══════════════════════════════════════════════════════════════════════
#  1. 서류 레코드 → 세대 1행
# ══════════════════════════════════════════════════════════════════════

def process_documents(doc_records: list, meta: dict = None) -> dict:
    """
    추출된 서류 레코드 리스트 → 병합·계산된 세대 1행 dict.
    meta: {"아파트유형","감면여부","주택수","조정대상지역"} (선택)
    """
    records = list(doc_records or [])
    records.append(_meta_record(meta))
    unit = merge_unit_records(records)

    # 판독 신뢰도 요약 (Vision confidence 최소값)
    confs = [r.get("_confidence", 0) for r in doc_records or []
             if r.get("_confidence") is not None]
    if confs:
        unit["_신뢰도"] = round(min(confs), 2)
    return unit


# ══════════════════════════════════════════════════════════════════════
#  2. PDF 파일들 → 서류 레코드 (Vision 우선, 정규식 폴백)
# ══════════════════════════════════════════════════════════════════════

def extract_pdf_records(pdf_path: str, use_vision: bool = True) -> list:
    """
    PDF 1개 → 서류 레코드 리스트.
    Vision 성공 시 그 결과(여러 서류 가능), 아니면 정규식 extract_pdf 1건.
    """
    if use_vision:
        try:
            from core.vision_extract import extract_unit
            r = extract_unit(pdf_path)
            if r and r.get("_source") == "vision" and r.get("records"):
                return r["records"]
        except Exception:
            pass  # 정규식 폴백

    # 정규식 폴백
    try:
        from core.vision_ocr import extract_pdf
        doc = extract_pdf(pdf_path)
        return [doc] if doc else []
    except Exception as e:
        return [{"doc_type": "", "_오류": str(e)[:200]}]


def process_pdf_files(pdf_paths: list, meta: dict = None,
                      use_vision: bool = True) -> dict:
    """여러 PDF(한 세대의 서류들) → 세대 1행."""
    all_records = []
    for p in pdf_paths:
        all_records.extend(extract_pdf_records(str(p), use_vision=use_vision))
    return process_documents(all_records, meta)


# ══════════════════════════════════════════════════════════════════════
#  3. 개별등기 (파일 또는 폴더 = 1세대)
# ══════════════════════════════════════════════════════════════════════

def _pdfs_in(path: Path) -> list:
    if path.is_file() and path.suffix.lower() in _PDF_EXTS:
        return [path]
    if path.is_dir():
        return sorted(p for p in path.iterdir()
                      if p.is_file() and p.suffix.lower() in _PDF_EXTS)
    return []


def process_individual(path: str, meta: dict = None,
                       use_vision: bool = True) -> dict:
    """
    개별등기 1세대 처리.
    path: 단일 PDF 파일, 또는 그 세대의 서류들이 든 폴더.
    """
    p = Path(path)
    pdfs = _pdfs_in(p)
    unit = process_pdf_files(pdfs, meta, use_vision=use_vision)
    unit.setdefault("_세대", p.stem if p.is_file() else p.name)
    return unit


# ══════════════════════════════════════════════════════════════════════
#  4. 집단등기 (세대별 하위폴더 n개)
# ══════════════════════════════════════════════════════════════════════

def _unit_folders(root: Path) -> list:
    subs = sorted(d for d in root.iterdir() if d.is_dir())
    return subs if subs else [root]


def process_group(root: str, meta: dict = None, workers: int = 5,
                  use_vision: bool = True, progress_cb=None) -> list:
    """
    집단등기 처리. root 하위의 세대 폴더들을 병렬 처리해 세대 행 리스트 반환.
    progress_cb(done, total, unit_name) 로 진행 상황 콜백(선택).
    """
    root_p = Path(root)
    units = _unit_folders(root_p)
    total = len(units)
    results = [None] * total
    workers = max(1, min(workers, total))

    with ThreadPoolExecutor(max_workers=workers) as ex:
        fut_to_idx = {
            ex.submit(process_individual, str(u), meta, use_vision): i
            for i, u in enumerate(units)
        }
        done = 0
        for fut in as_completed(fut_to_idx):
            i = fut_to_idx[fut]
            u = units[i]
            try:
                results[i] = fut.result()
            except Exception as e:
                results[i] = {"_세대": u.name, "_오류": str(e)[:200]}
            done += 1
            if progress_cb:
                try:
                    progress_cb(done, total, u.name)
                except Exception:
                    pass

    return [r for r in results if r]


# ══════════════════════════════════════════════════════════════════════
#  5. 세대별 재처리 (오류/부분 세대만 다시)
# ══════════════════════════════════════════════════════════════════════

def _unit_key(u: dict) -> tuple:
    return (str(u.get("동", "")).strip(), str(u.get("호", "")).strip())


def reprocess_into(results: list, path: str, meta: dict = None,
                   use_vision: bool = True) -> list:
    """
    한 세대를 재처리하여 기존 결과 리스트에서 같은 동/호 항목을 교체.
    같은 동/호가 없으면 추가. 검토 필요 세대를 다시 돌릴 때 사용.
    """
    new_unit = process_individual(path, meta, use_vision=use_vision)
    key = _unit_key(new_unit)
    replaced = False
    out = []
    for u in results:
        if key != ("", "") and _unit_key(u) == key:
            out.append(new_unit)
            replaced = True
        else:
            out.append(u)
    if not replaced:
        out.append(new_unit)
    return out
